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


def hunt(send_email=True):
    DATA.mkdir(exist_ok=True)
    jobs = {j["id"]: j for j in _load(DATA / "jobs.json", {"jobs": []})["jobs"]}
    meta = _load(DATA / "meta.json", {})
    cache = AccreditationCache(DATA / "accreditation.json")
    first_run = not jobs
    now = _now().isoformat(timespec="seconds")

    found, errors = sources.search_all(first_run)
    log.info("Search returned %d listings (%d source errors)", len(found), len(errors))

    by_key = {_dedup_key(j): j for j in jobs.values()}
    new_ids = []
    for job in found:
        if job["id"] in jobs:
            continue
        if not classify.title_fit(job["title"]):
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

    # Descriptions: new jobs first, then any left over from earlier runs.
    pending = [i for i in new_ids] + [i for i, j in jobs.items() if j.get("needs_detail") and i not in new_ids]
    details = 0
    for jid in pending:
        job = jobs[jid]
        description = ""
        if details < config.MAX_DETAILS_PER_RUN:
            details += 1
            try:
                description, extra = sources.fetch_description(job)
                job.update({k: v for k, v in extra.items() if v})
                job["needs_detail"] = False
            except (FetchError, ValueError, KeyError) as exc:
                log.info("No description for %s: %s", jid, exc)
            time.sleep(1.5 if job["source"] == "LinkedIn" else 0.5)
        classify.analyse(job, description, cache.check(job["company"]))

    # Apply today's rules to everything stored: drop titles now out of scope,
    # re-check employers whose lookup failed, and re-score.
    jobs = {i: j for i, j in jobs.items() if classify.title_fit(j["title"])}
    for job in jobs.values():
        job["recruiter"] = classify.is_recruiter(job)
        if (job.get("accreditation") or {}).get("status") in (None, UNKNOWN):
            job["accreditation"] = cache.check(job["company"])
        classify.score(job)
    cache.save()

    jobs = {i: j for i, j in jobs.items() if not _too_old(j)}
    ordered = sorted(jobs.values(), key=_sort_key)

    # Quota watch.
    status = quota.read_status()
    quota_changed = bool(status and meta.get("quota", {}).get("hash") not in (None, status["hash"]))
    if status:
        meta["quota"] = {**status, "checked_at": now}

    fresh = sorted((jobs[i] for i in new_ids if i in jobs), key=_sort_key)
    to_send = [j for j in fresh if classify.visa_ready(j)]
    held_back = len(fresh) - len(to_send)
    site_url = os.environ.get("SITE_URL", "")

    if send_email and quota_changed:
        body = "<p>The India Skilled Work Visa page changed what it says about places:</p><ul>"
        body += "".join(f"<li>{line}</li>" for line in status["lines"]) + "</ul>"
        body += f"<p><a href='{config.VISA_PAGE}'>{config.VISA_PAGE}</a></p>"
        notify.send("⚠️ India Skilled Work Visa: places update", body, str(DATA / "last_quota_email.html"))

    if send_email and to_send:
        top_a = [j for j in to_send if j["tier"] == "A"]
        lead = to_send[0]
        subject = (
            f"🔥 {len(top_a)} apply-now NZ job(s): {lead['title']} @ {lead['company']}"
            if top_a
            else f"NZ jobs: {len(to_send)} new — {lead['title']} @ {lead['company']}"
        )
        notify.send(subject, notify.render_jobs_email(to_send, site_url, held_back, errors), str(DATA / "last_email.html"))

    meta.update(
        last_run=now,
        first_run_at=meta.get("first_run_at") or now,
        new_this_run=len(fresh),
        visa_ready_this_run=len(to_send),
        emailed_this_run=len(to_send) if send_email else 0,
        totals={t: sum(1 for j in ordered if j["tier"] == t) for t in TIER_ORDER},
        errors=errors,
        accreditation_lookups=cache.lookups,
    )
    (DATA / "jobs.json").write_text(json.dumps({"jobs": ordered}, indent=1))
    (DATA / "meta.json").write_text(json.dumps(meta, indent=1))
    log.info("New: %d (visa-ready %d, held back %d). Total tracked: %d", len(fresh), len(to_send), held_back, len(ordered))
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-email", action="store_true", help="update data without sending email")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    hunt(send_email=not args.no_email)


if __name__ == "__main__":
    main()
