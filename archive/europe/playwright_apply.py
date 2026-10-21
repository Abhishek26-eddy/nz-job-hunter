#!/usr/bin/env python3
"""Full auto-apply via Playwright for Greenhouse/Lever/Ashby public forms.

Fills contact info, uploads the correct resume, pastes the cover letter,
detects CAPTCHA and stops for manual solving, then submits.
Run this from the repo root inside the local venv:
    source .venv/bin/activate && python playwright_apply.py
"""

import argparse
import json
import re
import select
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

API_URL = "http://localhost:8002/api"
RESUME_DIR = Path("/Users/abhishek.prajapati/CascadeProjects/resume")


def api_request(method: str, path: str, data: dict | None = None) -> dict:
    url = f"{API_URL}{path}"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    body = json.dumps(data or {}).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_pending_applications(retry_manual: bool = False) -> list[dict]:
    """Return applications that have not yet been confirmed as submitted.

    If retry_manual is True, also include jobs previously paused at a visible
    CAPTCHA (notes contain 'manual_submit_needed') so the user can finish them.
    """
    apps = api_request("GET", "/v1/applications/?limit=200")
    pending = []
    for a in apps.get("items", []):
        notes = (a.get("notes") or "").lower()
        status = a.get("status")
        if status == "saved":
            pending.append(a)
            continue
        if status == "applied":
            if retry_manual and "manual_submit_needed" in notes:
                pending.append(a)
                continue
            if "submitted via playwright" in notes and "manual_submit_needed" not in notes:
                # Already fully submitted; skip.
                continue
            # Fresh auto-opened applications that haven't been Playwrighted yet.
            if "playwright" not in notes and "submitted" not in notes:
                pending.append(a)
    return pending


def determine_resume_file(job: dict) -> Path:
    role = job.get("role_category", "")
    title = job.get("title", "").lower()
    if role == "Platform Engineer" or "platform" in title:
        return RESUME_DIR / "Abhishek_Prajapati_Resume_A_Platform_Engineer.pdf"
    if role == "DevOps Engineer" or "devops" in title:
        return RESUME_DIR / "Abhishek_Prajapati_Resume_B_DevOps_Engineer.pdf"
    return RESUME_DIR / "Abhishek_Prajapati_Resume_C_SRE.pdf"


def has_captcha(page) -> bool:
    """Detect visible reCAPTCHA / hCAPTCHA / Cloudflare turnstile on the page."""
    captcha_selectors = [
        ".g-recaptcha",
        "iframe[src*='recaptcha']",
        "iframe[src*='hcaptcha']",
        "iframe[src*='challenges.cloudflare']",
        "[data-callback='onCaptchaCompleted']",
        ".h-captcha",
    ]
    for sel in captcha_selectors:
        try:
            if page.locator(sel).first.is_visible(timeout=500):
                return True
        except Exception:
            continue
    # Check visible challenge iframes (invisible/0-size ones don't count).
    try:
        for iframe in page.locator("iframe").all():
            src = iframe.get_attribute("src") or ""
            if any(x in src for x in ("recaptcha", "hcaptcha", "turnstile", "cloudflare")):
                box = iframe.bounding_box()
                if box and box.get("width", 0) > 50 and box.get("height", 0) > 20:
                    return True
    except Exception:
        pass
    return False


def hide_cookie_overlays(page):
    """Hide common CMP/cookie banners that intercept clicks."""
    try:
        page.evaluate("""() => {
            const ids = ['usercentrics-root','onetrust-consent-sdk','cmp','cookie-banner','cookie-modal'];
            ids.forEach(id => { const el = document.getElementById(id); if (el) { el.style.display='none'; el.style.pointerEvents='none'; } });
        }""")
    except Exception:
        pass


def get_app_frame(page, timeout: int = 20000):
    """Return the Frame that contains the application form.

    Tries the main page, Greenhouse iframes, and Apply buttons that reveal the form.
    """
    start = time.time()
    while time.time() - start < timeout / 1000:
        hide_cookie_overlays(page)

        # Direct form on the main page.
        try:
            page.locator("form").first.wait_for(state="visible", timeout=3000)
            return page.main_frame
        except PlaywrightTimeout:
            pass

        # Greenhouse iframe embedded in a career site (e.g. N26).
        for frame in page.frames:
            try:
                if "greenhouse" in (frame.url or "").lower() or frame.name == "grnhse_iframe":
                    frame.locator("form").first.wait_for(state="visible", timeout=3000)
                    return frame
            except Exception:
                pass

        # No form yet; try clicking an Apply button/link.
        for sel in ("a[href*='apply']", "button:has-text('Apply')", "a:has-text('Apply')"):
            try:
                link = page.locator(sel).first
                if link.is_visible(timeout=1000):
                    link.click(timeout=3000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except PlaywrightTimeout:
                        pass
                    break
            except Exception:
                pass

        page.wait_for_timeout(1000)

    raise PlaywrightTimeout("No application form found on page or in iframes")


def fill_current_location(page, value: str = "Bangalore, India") -> bool:
    """Fill 'Current location' / 'City' autocomplete fields and select first suggestion."""
    selectors = [
        ("label", [r"current\s*location", r"location", r"city", r"where\s*are\s*you"]),
        ("placeholder", ["current location", "location", "city"]),
    ]
    for kind, patterns in selectors:
        for pat in patterns:
            try:
                if kind == "label":
                    el = page.get_by_label(re.compile(pat, re.I)).first
                else:
                    el = page.get_by_placeholder(re.compile(pat, re.I)).first
                if el.is_visible(timeout=800):
                    el.fill(value, timeout=2000)
                    page.wait_for_timeout(800)
                    # Try to select first autocomplete suggestion.
                    try:
                        el.press("ArrowDown", timeout=1000)
                        el.press("Enter", timeout=1000)
                    except Exception:
                        pass
                    return True
            except Exception:
                continue
    return False


def set_field_by_label(page, label_regex: str, value: str):
    """Best-effort fill of a labelled input/textarea."""
    label = page.locator("label").filter(has_text=re.compile(label_regex, re.I)).first
    try:
        if label.is_visible(timeout=1000):
            # Try to find the input by its associated id.
            input_id = label.get_attribute("for")
            if input_id:
                try:
                    page.locator(f"#{input_id}").first.fill(value)
                    return
                except Exception:
                    pass
    except Exception:
        pass

    # Fallback: find an input/textarea near the label text.
    for tag in ("input", "textarea"):
        try:
            el = page.locator(tag).filter(has=page.locator("xpath=..").locator("*", has_text=re.compile(label_regex, re.I))).first
            if el.is_visible(timeout=1000):
                el.fill(value)
                return
        except Exception:
            pass

    # Try placeholders and aria-labels.
    try:
        page.get_by_placeholder(re.compile(label_regex, re.I)).first.fill(value)
        return
    except Exception:
        pass
    try:
        page.get_by_label(re.compile(label_regex, re.I)).first.fill(value)
        return
    except Exception:
        pass


def fill_application(page, payload: dict, resume_path: Path, cover_letter: str):
    """Fill a generic ATS application form."""
    first = payload.get("first_name", "")
    last = payload.get("last_name", "")
    email = payload.get("email", "")
    phone = payload.get("phone", "")
    linkedin = payload.get("linkedin", "")

    # Standard Greenhouse/Lever ids
    for field_id, value in (
        ("first_name", first),
        ("last_name", last),
        ("email", email),
        ("phone", phone),
    ):
        try:
            page.locator(f"#{field_id}").first.fill(value, timeout=2000)
        except Exception:
            set_field_by_label(page, field_id.replace("_", " "), value)

    # LinkedIn / online profile
    for pattern in (r"linkedin", r"linkedin.*profile", r"online profile", r"website", r"portfolio"):
        try:
            page.get_by_label(re.compile(pattern, re.I)).first.fill(linkedin, timeout=1000)
            break
        except Exception:
            pass
    if linkedin:
        set_field_by_label(page, r"linkedin", linkedin)

    # Cover letter: either file upload or textarea/manual entry.
    cover_set = False

    # 1) Try the Greenhouse file input #cover_letter.
    try:
        cl_file = page.locator("input#cover_letter").first
        if cl_file.count() > 0 and cover_letter:
            tmp = Path("/tmp/cover_letter.txt")
            tmp.write_text(cover_letter, encoding="utf-8")
            cl_file.set_input_files(str(tmp))
            cover_set = True
    except Exception:
        pass

    # 2) Try textarea / label.
    if not cover_set:
        for pattern in (r"cover.?letter", r"cover letter"):
            try:
                page.get_by_label(re.compile(pattern, re.I)).first.fill(cover_letter, timeout=1000)
                cover_set = True
                break
            except Exception:
                pass
        if not cover_set:
            set_field_by_label(page, r"cover.?letter", cover_letter)

    # Resume upload. Greenhouse: input#resume, Ashby: input[type=file], Lever: similar.
    uploaded = False
    for file_input in (
        "input#resume",
        "input[data-qa='resume']",
        "input[aria-label*='Resume' i]",
        "input[name='resume']",
        "input[type='file']",
    ):
        try:
            inp = page.locator(file_input).first
            if inp.is_visible(timeout=1000) or inp.count() > 0:
                inp.set_input_files(str(resume_path))
                uploaded = True
                break
        except Exception:
            continue
    if not uploaded:
        print("Warning: resume upload input not found")

    # Current location autocomplete (common on Greenhouse forms).
    fill_current_location(page, "Bangalore, India")

    # Opt out of EEO/demographic questions when possible.
    for opt_text in ("Prefer not to say", "Decline to self-identify", "I don't wish to answer"):
        try:
            page.get_by_text(opt_text).first.click(timeout=500)
            break
        except Exception:
            pass


def fill_required_custom_questions(page):
    """Best-effort auto-answer of common required yes/no custom application questions."""
    # (label pattern, answer)
    yes_no_answers = [
        (r"public official", "No"),
        (r"close family member", "No"),
        (r"sanction", "No"),
        (r"criminal", "No"),
        (r"felony", "No"),
        (r"convicted", "No"),
        (r"disability", "No"),
        (r"veteran", "No"),
    ]
    for pattern, answer in yes_no_answers:
        try:
            # Use the question label to find the input/combobox.
            inp = page.get_by_label(re.compile(pattern, re.I)).first
            if not inp.is_visible(timeout=500):
                continue
            tag = inp.evaluate("el => el.tagName.toLowerCase()")
            if tag == "select":
                try:
                    inp.select_option(answer)
                    continue
                except Exception:
                    pass
            # For React-Select and similar text inputs.
            inp.fill(answer)
            inp.press("Enter")
            page.wait_for_timeout(300)
        except Exception:
            pass


def is_success_page(page, original_url: str) -> bool:
    """Heuristic: URL changed away from the job form and no form visible."""
    current = page.url
    if current != original_url and ("thank" in current.lower() or "success" in current.lower() or "applied" in current.lower()):
        return True
    for text in ("thank you", "application submitted", "received", "success"):
        try:
            if page.get_by_text(text).first.is_visible(timeout=1000):
                return True
        except Exception:
            continue
    return False


def has_validation_errors(page) -> bool:
    """Heuristic: check for visible validation errors on the form."""
    try:
        if page.locator("[aria-invalid='true']").first.is_visible(timeout=1000):
            return True
    except Exception:
        pass
    for err_text in ("is required", "required field", "can't be blank", "Please enter", "Please select"):
        try:
            if page.get_by_text(err_text).first.is_visible(timeout=500):
                return True
        except Exception:
            pass
    return False


def _screenshot(page_or_frame, path: str, full_page: bool = False):
    """Frame objects don't have screenshot(), so go through the parent page."""
    try:
        if hasattr(page_or_frame, "page"):
            page_or_frame.page.screenshot(path=path, full_page=full_page)
        else:
            page_or_frame.screenshot(path=path, full_page=full_page)
    except Exception:
        pass


def submit_or_pause(page) -> str:
    """Submit if possible; pause with browser open if visible CAPTCHA or validation remains."""
    original_url = page.url

    if has_captcha(page):
        print("\n🛑 Visible CAPTCHA detected. Solve it in the browser and click Submit manually.")
        print("Browser will stay open for 60 seconds, then continue to the next job.")
        _screenshot(page, "/tmp/captcha.png")
        try:
            page.wait_for_timeout(60000)
        except Exception:
            pass
        if is_success_page(page, original_url):
            print("Success page detected after captcha.")
            return "submitted"
        print("No success page detected. Skipping.")
        return "manual_submit_needed"

    # Find submit button / input.
    for selector in (
        "input#submit",
        "button#submit",
        "input[type='submit']",
        "button[type='submit']",
        "button:has-text('Submit Application')",
        "button:has-text('Submit')",
        "input[value*='Submit']",
    ):
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=2000):
                btn.click()
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
                if is_success_page(page, original_url):
                    return "submitted"

                # If we now see a visible captcha, pause.
                if has_captcha(page):
                    print("\n🛑 CAPTCHA appeared after submit. Solve it in the browser and click Submit manually.")
                    _screenshot(page, "/tmp/captcha.png")
                    try:
                        page.wait_for_timeout(60000)
                    except Exception:
                        pass
                    if is_success_page(page, original_url):
                        return "submitted"
                    return "manual_submit_needed"

                # If validation errors remain, pause briefly so the user can fix.
                if has_validation_errors(page):
                    print("\n⚠️ Form validation errors remain. Review and fix in the browser.")
                    _screenshot(page, "/tmp/validation.png")
                    try:
                        page.wait_for_timeout(30000)
                    except Exception:
                        pass
                    if is_success_page(page, original_url):
                        return "submitted"
                    return "manual_submit_needed"

                return "submitted_or_error"
        except Exception:
            continue
    return "manual_submit_needed"


def cover_letter_for_job(job: dict) -> str:
    """Load the best matching local cover letter for a job."""
    cover_dir = RESUME_DIR / "cover_letters"
    company = (job.get("company", {}) or {}).get("name", "").strip()
    title = (job.get("title") or "").lower().replace(",", "").replace("  ", " ")
    company_lower = company.lower().replace(" ", "_")

    if "site reliability" in title or "sre" in title:
        role = "Site Reliability Engineer"
    elif "platform" in title:
        role = "Platform Engineer"
    elif "devops" in title:
        role = "DevOps Engineer"
    else:
        role = job.get("role_category", "")

    specific = None
    if company.lower() == "gitlab" and role == "Site Reliability Engineer":
        specific = cover_dir / "GitLab_SRE.txt"
    elif company.lower() == "doctolib" and role == "Site Reliability Engineer":
        specific = cover_dir / "Doctolib_SRE_Observability.txt"
    elif company.lower() == "n26" and role == "Site Reliability Engineer":
        if "data platform" in title:
            specific = cover_dir / "N26_SRE_Data_Platform.txt"
        else:
            specific = cover_dir / "N26_SRE_Software_Logistics.txt"

    generic_name = "SRE" if role == "Site Reliability Engineer" else role.replace(' ', '_')
    candidates = [specific] if specific else []
    if company_lower:
        candidates.append(cover_dir / f"{company_lower}_{role.replace(' ', '_')}.txt")
    candidates.append(cover_dir / f"Generic_{generic_name}.txt")

    for p in candidates:
        if p and p.exists():
            text = p.read_text()
            text = text.replace("[ROLE]", job.get("title", "the role")).replace("[COMPANY]", company)
            return text
    return ""


def resolve_application_url(job: dict) -> str | None:
    """Return the best URL to use for the application form."""
    url = job.get("application_url") or job.get("platform_url")
    if not url:
        return None
    # N26 career pages embed the Greenhouse form; use the direct board URL.
    if "n26.com" in url:
        match = re.search(r"[?&]gh_jid=(\d+)", url)
        if match:
            jid = match.group(1)
            return f"https://job-boards.greenhouse.io/n26/jobs/{jid}?gh_jid={jid}"
    return url


def process_application(page, app: dict, open_only: bool = False):
    job = app.get("job", {})
    url = resolve_application_url(job)
    if not url:
        print(f"Skipping app {app.get('id', 0)}: no URL")
        return

    action = "Opening for manual apply" if open_only else "Applying to"
    print(f"\n{action}: {job.get('company',{}).get('name')} — {job.get('title')}")
    print(f"URL: {url}")

    try:
        page.goto(url, wait_until="networkidle", timeout=45000)
        frame = get_app_frame(page)
        page.wait_for_timeout(1000)
    except Exception as exc:
        print(f"Could not load form: {exc}")
        return

    try:
        oneclick = api_request(
            "POST",
            f"/v1/apply/jobs/{job['id']}",
            data={"resume_id": app.get("resume_id"), "cover_letter": ""},
        )
        payload = oneclick.get("data", {}).get("payload", {})
    except Exception as exc:
        print(f"Could not get oneclick payload: {exc}")
        payload = {}

    cover_letter = cover_letter_for_job(job)
    resume_path = determine_resume_file(job)

    try:
        fill_application(frame, payload, resume_path, cover_letter)
        fill_required_custom_questions(frame)
    except Exception as exc:
        print(f"Error filling form: {exc}")

    if open_only:
        print("Form prefilled. Submit this tab manually when ready.")
        return

    result = submit_or_pause(frame)
    print(f"Result: {result}")

    # Update application notes.
    if app.get("id"):
        try:
            api_request(
                "PATCH",
                f"/v1/applications/{app['id']}/status",
                data={"status": "applied", "notes": f"Submitted via Playwright. Result: {result}. Resume: {resume_path.name}"},
            )
        except Exception as exc:
            print(f"Could not update application: {exc}")


def get_master_resume_id() -> int | None:
    try:
        resumes = api_request("GET", "/v1/resumes/")
        for r in resumes:
            if r.get("is_master"):
                return r.get("id")
        return resumes[0]["id"] if resumes else None
    except Exception:
        return None


def is_remote_or_india(job: dict) -> bool:
    """Heuristic filter for remote, work-from-home or India-based roles."""
    wt = (job.get("workplace_type") or "").lower()
    loc = (job.get("location") or "").lower()
    title = (job.get("title") or "").lower()
    return (
        wt in ("remote", "hybrid", "work from home", "distributed")
        or "remote" in loc
        or "india" in loc
        or "work from home" in title
    )


def get_should_apply_jobs(remote_only: bool = False) -> list[dict]:
    """Fetch jobs flagged should_apply by the AI matcher."""
    try:
        data = api_request("GET", "/v1/jobs/?should_apply=true&limit=200")
        jobs = data.get("items", [])
    except Exception as exc:
        print(f"Could not fetch should_apply jobs: {exc}")
        return []
    if remote_only:
        return [j for j in jobs if is_remote_or_india(j)]
    return jobs


def build_open_list(retry_manual: bool = False, remote_only: bool = False) -> list[dict]:
    """Build a deduplicated list of jobs to open, including pending apps and should_apply jobs.

    Skip jobs that are already confirmed as successfully submitted.
    """
    apps = get_pending_applications(retry_manual=retry_manual)
    # Collect successfully-submitted job ids so we don't reopen them.
    try:
        all_apps = api_request("GET", "/v1/applications/?limit=500").get("items", [])
    except Exception:
        all_apps = []
    skip_ids = set()
    for a in all_apps:
        notes = (a.get("notes") or "").lower()
        status = a.get("status")
        if status == "applied" and "manual_submit_needed" not in notes:
            skip_ids.add(a.get("job", {}).get("id"))

    seen = {a.get("job", {}).get("id") for a in apps}
    seen.update(skip_ids)
    master_id = get_master_resume_id()
    jobs = get_should_apply_jobs(remote_only=remote_only)
    for j in jobs:
        if j.get("id") in seen:
            continue
        seen.add(j["id"])
        apps.append({"id": 0, "job": j, "resume_id": master_id})
    return apps


def main():
    parser = argparse.ArgumentParser(description="Full Playwright auto-apply")
    parser.add_argument("--limit", type=int, default=0, help="Max applications to process (0=all)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (no captcha support)")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between jobs")
    parser.add_argument("--company", type=str, default=None, help="Filter by company name")
    parser.add_argument("--job-id", type=int, default=0, help="Apply to a specific job id")
    parser.add_argument("--retry", action="store_true", help="Re-process previous CAPTCHA/manual jobs")
    parser.add_argument("--open-only", action="store_true", help="Open each job in a tab, prefill the form, and leave it for manual submit")
    parser.add_argument("--open-should-apply", action="store_true", help="In open-only mode, also include AI-matched should_apply jobs")
    parser.add_argument("--browser", type=str, default="chrome", choices=["chrome", "comet", "edge"], help="Browser executable to use")
    parser.add_argument("--remote-only", action="store_true", help="In open mode, only include remote/hybrid/India roles")
    args = parser.parse_args()

    if args.open_only or args.open_should_apply:
        apps = build_open_list(retry_manual=args.retry, remote_only=args.remote_only)
    else:
        apps = get_pending_applications(retry_manual=args.retry)

    if args.company:
        apps = [a for a in apps if args.company.lower() in (a.get("job", {}).get("company", {}).get("name") or "").lower()]
    if args.job_id:
        apps = [a for a in apps if a.get("job", {}).get("id") == args.job_id]
    if args.limit:
        apps = apps[:args.limit]
    print(f"Found {len(apps)} applications to submit.")
    if not apps:
        return 0

    browser_paths = {
        "chrome": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "comet": "/Applications/Comet.app/Contents/MacOS/Comet",
        "edge": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    }
    executable_path = browser_paths.get(args.browser)
    if executable_path and not Path(executable_path).exists():
        print(f"Warning: {args.browser} not found at {executable_path}; falling back to bundled Chromium.")
        executable_path = None

    with sync_playwright() as p:
        launch_kwargs = {"headless": args.headless, "slow_mo": 100}
        if executable_path:
            launch_kwargs["executable_path"] = executable_path
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
        )

        if args.open_only or args.open_should_apply:
            for i, app in enumerate(apps, 1):
                print(f"\n[{i}/{len(apps)}]")
                page = context.new_page()
                try:
                    process_application(page, app, open_only=True)
                except Exception as exc:
                    print(f"Failed to open app {app.get('id')}: {exc}")
                time.sleep(args.delay)
            print("\nAll tabs opened with forms prefilled. Browser will stay open for 60 minutes so you can apply manually.")
            try:
                time.sleep(3600)
            except KeyboardInterrupt:
                pass
        else:
            page = context.new_page()
            for i, app in enumerate(apps, 1):
                print(f"\n[{i}/{len(apps)}]")
                try:
                    process_application(page, app)
                except Exception as exc:
                    print(f"Failed to process app {app.get('id')}: {exc}")
                time.sleep(args.delay)

        browser.close()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
