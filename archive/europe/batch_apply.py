#!/usr/bin/env python3
"""Batch one-click apply for matched Europe jobs.

Opens safe public ATS application forms (Greenhouse, Lever, Ashby) and records
an application entry for each. It does NOT click "Submit" automatically; the
final submit is left to the user, as the bot cannot reliably handle custom
forms, CAPTCHAs, or login-gated ATSs.
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

API_URL = "http://localhost:8002/api"
RESUME_DIR = Path("/Users/abhishek.prajapati/CascadeProjects/resume")
COVER_DIR = RESUME_DIR / "cover_letters"


ROLE_RESUME_FILES = {
    "Site Reliability Engineer": RESUME_DIR / "Abhishek_Prajapati_Resume_C_SRE.pdf",
    "Platform Engineer": RESUME_DIR / "Abhishek_Prajapati_Resume_A_Platform_Engineer.pdf",
    "DevOps Engineer": RESUME_DIR / "Abhishek_Prajapati_Resume_B_DevOps_Engineer.pdf",
}

ROLE_COVER_TEMPLATES = {
    "Site Reliability Engineer": COVER_DIR / "Generic_SRE.txt",
    "Platform Engineer": COVER_DIR / "Generic_Platform_Engineer.txt",
    "DevOps Engineer": COVER_DIR / "Generic_DevOps_Engineer.txt",
}


def api_request(method: str, path: str, data: dict | None = None, params: dict | None = None) -> dict:
    url = f"{API_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    body = json.dumps(data or {}).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_upload_resume(path: Path, is_master: bool = False) -> dict:
    """Upload a resume using multipart/form-data and return the record."""
    import io
    import mimetypes

    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode())
    body.write(f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode())
    content_type = mimetypes.guess_type(path.name)[0] or "application/pdf"
    body.write(f"Content-Type: {content_type}\r\n\r\n".encode())
    body.write(path.read_bytes())
    body.write(f"\r\n--{boundary}--\r\n".encode())

    url = f"{API_URL}/v1/resumes/upload"
    if is_master:
        url += "?is_master=true"
    req = urllib.request.Request(
        url,
        data=body.getvalue(),
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_or_upload_resumes() -> dict:
    """Ensure the three targeted resumes exist in the DB and return role -> id mapping."""
    existing = api_request("GET", "/v1/resumes/")
    by_name = {r.get("file_name"): r["id"] for r in existing}

    role_ids = {}
    for role, file_path in ROLE_RESUME_FILES.items():
        if file_path.name in by_name:
            role_ids[role] = by_name[file_path.name]
            continue
        print(f"Uploading {file_path.name} ...")
        result = api_upload_resume(file_path)
        role_ids[role] = result["id"]
        by_name[file_path.name] = result["id"]
    return role_ids


def get_jobs(title_filter: str | None, only_should_apply: bool, limit: int, offset: int, min_score: float, skip_applied: bool = True) -> list[dict]:
    params: dict = {"limit": 200, "sort": "score_desc"}
    data = api_request("GET", "/v1/jobs/", params=params)
    jobs = data.get("items", [])

    applied_job_ids = set()
    if skip_applied:
        try:
            apps = api_request("GET", "/v1/applications/", params={"limit": 200})
            terminal = {"applied", "oa", "recruiter_call", "interview", "final_round", "offer", "rejected", "withdrawn"}
            applied_job_ids = {
                a["job_id"]
                for a in apps.get("items", [])
                if a.get("job_id") and a.get("status") in terminal
            }
        except Exception:
            pass

    filtered = []
    for j in jobs:
        if j.get("match_score", 0) < min_score:
            continue
        if only_should_apply and not j.get("should_apply"):
            continue
        if title_filter and title_filter.lower() not in j.get("title", "").lower():
            continue
        if not title_filter:
            # Default: target roles matching the user's tailored resumes.
            role = j.get("role_category", "")
            if role not in ROLE_RESUME_FILES:
                continue
        if skip_applied and j["id"] in applied_job_ids:
            continue
        filtered.append(j)
    return filtered[offset:offset+limit]


def cover_letter_for_job(job: dict) -> str:
    company = job.get("company", {}).get("name", "").strip()
    title = job.get("title", "").lower().replace(",", "").replace("  ", " ")
    company_lower = company.lower().replace(" ", "_")

    if "site reliability" in title or "sre" in title:
        role = "Site Reliability Engineer"
    elif "platform" in title:
        role = "Platform Engineer"
    elif "devops" in title:
        role = "DevOps Engineer"
    else:
        role = job.get("role_category", "")

    # Specific cover letters for top matched roles.
    specific = None
    if company.lower() == "gitlab" and role == "Site Reliability Engineer":
        specific = COVER_DIR / "GitLab_SRE.txt"
    elif company.lower() == "doctolib" and role == "Site Reliability Engineer":
        if "observability" in title:
            specific = COVER_DIR / "Doctolib_SRE_Observability.txt"
        else:
            specific = COVER_DIR / "Doctolib_SRE_Observability.txt"
    elif company.lower() == "n26" and role == "Site Reliability Engineer":
        if "data platform" in title:
            specific = COVER_DIR / "N26_SRE_Data_Platform.txt"
        elif "software logistics" in title:
            specific = COVER_DIR / "N26_SRE_Software_Logistics.txt"
        else:
            specific = COVER_DIR / "N26_SRE_Software_Logistics.txt"

    candidates = [specific] if specific else []
    if company_lower:
        candidates.append(COVER_DIR / f"{company_lower}_{role.replace(' ', '_')}.txt")
    candidates.append(ROLE_COVER_TEMPLATES.get(role, COVER_DIR / "Generic_DevOps_Engineer.txt"))

    for p in candidates:
        if p and p.exists():
            text = p.read_text()
            text = text.replace("[ROLE]", job.get("title", "the role")).replace("[COMPANY]", company)
            return text
    return ""


def oneclick_apply(job_id: int, resume_id: int, cover_letter: str) -> dict:
    return api_request(
        "POST",
        f"/v1/apply/jobs/{job_id}",
        data={"resume_id": resume_id, "cover_letter": cover_letter},
    )


def record_application(job_id: int, resume_id: int, status: str = "applied", notes: str = "") -> dict:
    return api_request(
        "POST",
        "/v1/applications/",
        data={"job_id": job_id, "resume_id": resume_id, "status": status, "notes": notes},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch one-click apply")
    parser.add_argument("--title", default=None, help="Filter jobs by title substring")
    parser.add_argument("--only-should-apply", action="store_true", default=True, help="Only apply to jobs the AI recommends")
    parser.add_argument("--all-matches", dest="only_should_apply", action="store_false", help="Apply to all title/role matches above min score")
    parser.add_argument("--min-score", type=float, default=70.0, help="Minimum match score")
    parser.add_argument("--limit", type=int, default=10, help="Max number of applications")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N matching jobs")
    parser.add_argument("--no-skip-applied", action="store_true", default=False, help="Do not skip jobs already in applications list")
    parser.add_argument("--open", action="store_true", default=False, help="Open application URLs in browser")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between opened tabs")
    args = parser.parse_args()

    print("Uploading/ensuring targeted resumes in the system...")
    role_resume_ids = find_or_upload_resumes()
    print(f"Resume IDs: {role_resume_ids}")

    print(f"\nFetching jobs (title={args.title!r}, should_apply={args.only_should_apply}, min_score={args.min_score})...")
    jobs = get_jobs(
        args.title,
        args.only_should_apply,
        args.limit,
        args.offset,
        args.min_score,
        skip_applied=not args.no_skip_applied,
    )
    print(f"Found {len(jobs)} matching jobs.")

    if not jobs:
        print("No jobs matched. Exiting.")
        return 0

    opened = 0
    recorded = 0
    skipped = 0

    for job in jobs:
        role = job.get("role_category", "")
        if role not in role_resume_ids:
            # Fallback to title keywords.
            title = job.get("title", "").lower()
            if "site reliability" in title or "sre" in title:
                role = "Site Reliability Engineer"
            elif "platform" in title:
                role = "Platform Engineer"
            elif "devops" in title:
                role = "DevOps Engineer"
            else:
                print(f"Skipping {job['title']} — no matching resume for role {role!r}")
                skipped += 1
                continue

        resume_id = role_resume_ids[role]
        cover_letter = cover_letter_for_job(job)

        try:
            action = oneclick_apply(job["id"], resume_id, cover_letter)
            status = action["data"]["status"]
            url = action["data"]["url"]
            payload = action["data"].get("payload", {})
        except Exception as exc:
            print(f"Error getting apply action for {job['title']}: {exc}")
            continue

        safe = status == "auto-open"
        app_status = "applied" if safe else "saved"
        notes = f"Auto-opened via batch apply. Status: {status}. Resume: {resume_id}. Cover: {len(cover_letter)} chars."
        try:
            record_application(job["id"], resume_id, status=app_status, notes=notes)
            recorded += 1
        except Exception as exc:
            print(f"Error recording application for {job['title']}: {exc}")

        print(f"\n{job['company']['name']} — {job['title']}")
        print(f"  Match: {job['match_score']:.1f} | URL: {url} | Status: {status}")
        print(f"  Payload: {json.dumps(payload, indent=2)}")

        if safe and args.open:
            try:
                webbrowser.open(url)
                opened += 1
                time.sleep(args.delay)
            except Exception as exc:
                print(f"Could not open browser for {url}: {exc}")

    print(f"\nDone. Recorded {recorded} applications, opened {opened} URLs, skipped {skipped}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
