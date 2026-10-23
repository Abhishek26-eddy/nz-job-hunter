"""One hunting pass: search, filter, check accreditation, score, email, save.

    python -m hunter.run              # normal run (emails if SMTP is set)
    python -m hunter.run --no-email   # update data only
"""

import argparse
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import classify, config, notify, quota, sources
from .accreditation import UNKNOWN, AccreditationCache, normalise
from .http import FetchError

log = logging.getLogger("hunter")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TIER_ORDER = {"A": 0, "B": 1, "C": 2, "blocked": 3}


def _now():
    return datetime.now(timezone.utc)


def _load(path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _dedup_key(job):
    return f"{normalise(job['company'])}|{normalise(job['title'])}"


def _too_old(job):
    posted = job.get("posted_at") or job.get("first_seen")
    try:
        when = datetime.fromisoformat(posted.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return False
    return _now() - when > timedelta(days=config.DROP_AFTER_DAYS)


def _sort_key(job):
    return (TIER_ORDER[job["tier"]], -job["score"], job.get("posted_at") or "")


def _sort_key_for(job, person):
    mine = job["for"][person]
    return (TIER_ORDER[mine["tier"]], -mine["score"], job.get("posted_at") or "")


def hunt(send_email=True, max_details=config.MAX_DETAILS_PER_RUN, backfill=False):
    DATA.mkdir(exist_ok=True)
    jobs = {j["id"]: j for j in _load(DATA / "jobs.json", {"jobs": []})["jobs"]}
    descriptions = _load(DATA / "descriptions.json", {})
    meta = _load(DATA / "meta.json", {})
    cache = AccreditationCache(DATA / "accreditation.json")
    # A person added to PROFILES gets a 31-day backfill on their first run.
    first_run = backfill or not jobs or bool(set(config.PROFILES) - set(meta.get("profiles", [])))
    now = _now().isoformat(timespec="seconds")

    found, errors = sources.search_all(first_run)
    log.info("Search returned %d listings (%d source errors)", len(found), len(errors))

    by_key = {_dedup_key(j): j for j in jobs.values()}
    new_ids = []
    for job in found:
        if job["id"] in jobs or not classify.fits_anyone(job["title"]):
            continue
        twin = by_key.get(_dedup_key(job))
        if twin:
            also = twin.setdefault("also_on", [])
            if not any(a["url"] == job["url"] for a in also):
                also.append({"source": job["source"], "url": job["url"]})
            continue
        job.update(first_seen=now, needs_detail=True)
        jobs[job["id"]] = job
        by_key[_dedup_key(job)] = job
        new_ids.append(job["id"])

    # Descriptions: new jobs first, then any still missing from earlier runs.
    pending = new_ids + [i for i, j in jobs.items() if i not in new_ids and (j.get("needs_detail") or i not in descriptions)]
    for n, jid in enumerate(pending):
        if n >= max_details:
            break
        job = jobs[jid]
        try:
            descriptions[jid], extra = sources.fetch_description(job)
            job.update({k: v for k, v in extra.items() if v})
            job["needs_detail"] = False
        except (FetchError, ValueError, KeyError) as exc:
            log.info("No description for %s: %s", jid, exc)
        time.sleep(1.5 if job["source"] == "LinkedIn" else 0.5)

    # Re-analyse everything with today's rules, so a rule change applies to old jobs too.
    for jid, job in list(jobs.items()):
        if (job.get("accreditation") or {}).get("status") in (None, UNKNOWN) or jid in new_ids:
            job["accreditation"] = cache.check(job["company"])
        classify.analyse(job, descriptions.get(jid, ""), job["accreditation"])
        if not job["for"] or _too_old(job):
            del jobs[jid]
            descriptions.pop(jid, None)
    cache.save()
    ordered = sorted(jobs.values(), key=_sort_key)

    # Quota watch.
    status = quota.read_status()
    quota_changed = bool(status and meta.get("quota", {}).get("hash") not in (None, status["hash"]))
    if status:
        meta["quota"] = {**status, "checked_at": now}

    unsent = []
    if send_email and quota_changed:
        body = "<p>The India Skilled Work Visa page changed what it says about places:</p><ul>"
        body += "".join(f"<li>{line}</li>" for line in status["lines"]) + "</ul>"
        body += f"<p><a href='{config.VISA_PAGE}'>{config.VISA_PAGE}</a></p>"
        if not notify.send("⚠️ India Skilled Work Visa: places update", body, str(DATA / "last_quota_email.html")):
            unsent.append("visa places update")

    # One email per person, only jobs whose employer can sponsor.
    fresh = [jobs[i] for i in new_ids if i in jobs]
    site_url = os.environ.get("SITE_URL", "")
    sent = {}
    for key, prof in config.PROFILES.items():
        theirs = sorted((j for j in fresh if key in j["for"]), key=lambda j: _sort_key_for(j, key))
        ready = [j for j in theirs if j["visa_ready"]]
        sent[key] = len(ready)
        if not (send_email and ready):
            continue
        lead = ready[0]
        top_a = sum(1 for j in ready if j["for"][key]["tier"] == "A")
        subject = (
            f"🔥 {prof['label']}: {top_a} apply-now NZ job(s) — {lead['title']} @ {lead['company']}"
            if top_a
            else f"{prof['label']}: {len(ready)} new NZ job(s) — {lead['title']} @ {lead['company']}"
        )
        to, cc = _recipients(prof)
        html_body = notify.render_jobs_email(ready, key, site_url, len(theirs) - len(ready), errors)
        if not notify.send(subject, html_body, str(DATA / f"last_email_{key}.html"), to=to, cc=cc):
            unsent.append(f"{len(ready)} job(s) for {prof['label']}")

    if unsent:
        # Fail before saving, so these jobs stay "new" and are emailed once SMTP works.
        raise SystemExit(
            "Could not email: " + ", ".join(unsent) + ". Set the SMTP_USER and SMTP_PASSWORD "
            "repository secrets (Settings > Secrets and variables > Actions)."
        )

    meta.update(
        last_run=now,
        first_run_at=meta.get("first_run_at") or now,
        profiles=sorted(config.PROFILES),
        new_this_run=len(fresh),
        visa_ready_this_run=sum(sent.values()),
        visa_ready_by_person=sent,
        totals={t: sum(1 for j in ordered if j["tier"] == t) for t in TIER_ORDER},
        errors=errors,
        accreditation_lookups=cache.lookups,
    )
    (DATA / "jobs.json").write_text(json.dumps({"jobs": ordered}, indent=1))
    (DATA / "descriptions.json").write_text(json.dumps(descriptions, sort_keys=True))
    (DATA / "meta.json").write_text(json.dumps(meta, indent=1))
    log.info("New: %d, visa-ready by person: %s. Total tracked: %d", len(fresh), sent, len(ordered))
    return meta


def _recipients(prof):
    to = os.environ.get(prof["email_env"]) or os.environ.get("ALERT_TO")
    cc = os.environ.get(prof["cc_env"]) if prof.get("cc_env") else None
    return to, cc


def send_digest():
    """Email each person their full current list of visa-ready jobs."""
    jobs = _load(DATA / "jobs.json", {"jobs": []})["jobs"]
    site_url = os.environ.get("SITE_URL", "")
    for key, prof in config.PROFILES.items():
        ready = sorted((j for j in jobs if key in j["for"] and j["visa_ready"]), key=lambda j: _sort_key_for(j, key))
        if not ready:
            log.info("No visa-ready jobs for %s", prof["label"])
            continue
        iswv = sum(1 for j in ready if j["for"][key].get("route") == "iswv")
        intro = (
            f"<p>All {len(ready)} NZ jobs open right now for <b>{prof['label']}</b> ({prof['role']}) "
            f"where the employer is accredited and the ad does not rule out visa holders.</p>"
            f"<p>{iswv} can go through the India Skilled Work Visa; the other {len(ready) - iswv} need the "
            "regular AEWV. New ones are emailed as they appear.</p>"
        )
        to, cc = _recipients(prof)
        html_body = notify.render_jobs_email(ready, key, site_url, 0, [], intro=intro)
        subject = f"📋 {prof['label']}: all {len(ready)} visa-ready NZ jobs right now"
        if not notify.send(subject, html_body, to=to, cc=cc):
            raise SystemExit("SMTP_USER and SMTP_PASSWORD are not set; digest not sent.")
        log.info("Digest for %s: %d jobs to %s%s", prof["label"], len(ready), to, f" (cc {cc})" if cc and cc != to else "")


def send_test_email():
    """Send one test message per person so you can check the SMTP secrets."""
    for key, prof in config.PROFILES.items():
        to, cc = _recipients(prof)
        body = (
            f"<p>✅ NZ job hunter email works for <b>{prof['label']}</b> ({prof['role']}).</p>"
            "<p>You will get an email like this whenever a new visa-ready job is found.</p>"
        )
        if not notify.send(f"✅ NZ job hunter: test email for {prof['label']}", body, to=to, cc=cc):
            raise SystemExit("SMTP_USER and SMTP_PASSWORD are not set; no test email sent.")
        log.info("Test email for %s sent to %s", prof["label"], to)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-email", action="store_true", help="update data without sending email")
    parser.add_argument("--max-details", type=int, default=config.MAX_DETAILS_PER_RUN,
                        help="job descriptions to fetch this run")
    parser.add_argument("--test-email", action="store_true", help="send a test email to each person and exit")
    parser.add_argument("--digest", action="store_true", help="email each person their full visa-ready list and exit")
    parser.add_argument("--backfill", action="store_true", help="search the last 31 days, not 7 (after adding searches)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.test_email:
        send_test_email()
        return
    if args.digest:
        send_digest()
        return
    hunt(send_email=not args.no_email, max_details=args.max_details, backfill=args.backfill)


if __name__ == "__main__":
    main()
