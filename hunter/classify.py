"""Decide whether a job is in scope, and how good a shot it is for the visa."""

import re
from datetime import datetime, timezone

from . import config
from .accreditation import ACCREDITED, EXPIRED, NOT_LISTED

_HARD = [(re.compile(p, re.I), why) for p, why in config.HARD_BLOCKERS]
_SOFT = [(re.compile(p, re.I), why) for p, why in config.SOFT_BLOCKERS]
_POS = [(re.compile(p, re.I), why) for p, why in config.POSITIVES]
_SKILLS = {name: re.compile(p, re.I) for name, p in config.SKILLS.items()}


def title_fit(title):
    """'core', 'adjacent' or None (out of scope)."""
    if config.EXCLUDE_TITLE.search(title):
        return None
    if config.CORE_TITLE.search(title):
        return "core"
    if config.ADJACENT_TITLE.search(title):
        return "adjacent"
    return None


def _snippet(text, m, width=90):
    start, end = max(m.start() - width, 0), min(m.end() + width, len(text))
    return ("…" if start else "") + text[start:end].replace("\n", " ").strip() + ("…" if end < len(text) else "")


def _scan(patterns, text):
    hits, seen = [], set()
    for rx, why in patterns:
        m = rx.search(text)
        if m and why not in seen:
            seen.add(why)
            hits.append({"why": why, "quote": _snippet(text, m)})
    return hits


def is_recruiter(job):
    return bool(config.RECRUITERS.search(job.get("advertiser") or job.get("company") or ""))


def analyse(job, description, accreditation):
    """Attach visa-fit findings and a score to the job dict (in place)."""
    text = f"{job.get('title', '')}\n{job.get('teaser', '')}\n{description or ''}"
    job["fit"] = title_fit(job["title"]) or "adjacent"
    job["hard_blockers"] = _scan(_HARD, text)
    job["soft_blockers"] = _scan(_SOFT, text)
    job["positives"] = _scan(_POS, text)
    job["skills"] = sorted(name for name, rx in _SKILLS.items() if rx.search(text))
    job["recruiter"] = is_recruiter(job)
    job["accreditation"] = accreditation
    job["has_description"] = bool(description)
    job["summary"] = (description or job.get("teaser") or "")[:400]
    score(job)
    return job


def visa_ready(job):
    """Worth an email: the employer can sponsor, and the ad does not rule it out.

    Sponsor-capable means on the INZ accredited list, or the ad itself offers
    sponsorship (employers may hide themselves from the public list).
    """
    if job.get("hard_blockers") or job.get("soft_blockers"):
        return False
    if "part" in (job.get("work_type") or "").lower():
        return False
    accredited = (job.get("accreditation") or {}).get("status") == ACCREDITED and not job.get("recruiter")
    offers = any(p["why"] == "Offers visa sponsorship" for p in job.get("positives") or [])
    return accredited or offers


def score(job):
    s, reasons = 0, []
    acc = (job.get("accreditation") or {}).get("status")
    if job.get("recruiter"):
        s += 10
        reasons.append("via agency: ask who the employer is")
    elif acc == ACCREDITED:
        s += 40
        reasons.append("accredited employer")
    elif acc == EXPIRED:
        s -= 10
        reasons.append("accreditation expired")
    elif acc == NOT_LISTED:
        s -= 5
        reasons.append("not on public INZ list")

    if job["fit"] == "core":
        s += 20
    else:
        s += 5
    if config.TOO_SENIOR_TITLE.search(job["title"]):
        s -= 10
        reasons.append("title above your level")

    s += min(len(job.get("skills") or []), 8) * 3

    if job.get("positives"):
        s += 25
        reasons.append(job["positives"][0]["why"].lower())
    if job.get("soft_blockers"):
        s -= 15
    work = (job.get("work_type") or "").lower()
    if "part" in work:
        s -= 30
        reasons.append("part time: the visa needs 30h+ a week")
    elif "contract" in work or "temp" in work:
        s -= 8
        reasons.append("contract: needs to be an employee offer")
    elif "full" in work:
        s += 5

    posted = job.get("posted_at")
    if posted:
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(posted.replace("Z", "+00:00"))
            if age.days < 2:
                s += 10
        except ValueError:
            pass

    if job.get("hard_blockers"):
        tier = "blocked"
    elif s >= config.TIER_A:
        tier = "A"
    elif s >= config.TIER_B:
        tier = "B"
    else:
        tier = "C"
    job["score"], job["tier"], job["reasons"] = s, tier, reasons
    job["visa_ready"] = visa_ready(job)
    return job
