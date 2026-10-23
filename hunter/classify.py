"""Decide whether a job is in scope for each person, and how good a shot it is.

Visa checks (accreditation, blockers) belong to the job. Title fit, skills and
score belong to each person in config.PROFILES.
"""

import re
from datetime import datetime, timezone

from . import config
from .accreditation import ACCREDITED, EXPIRED, NOT_LISTED

_HARD = [(re.compile(p, re.I), why) for p, why in config.HARD_BLOCKERS]
_SOFT = [(re.compile(p, re.I), why) for p, why in config.SOFT_BLOCKERS]
_POS = [(re.compile(p, re.I), why) for p, why in config.POSITIVES]
_SKILLS = {
    key: {name: re.compile(p, re.I) for name, p in prof["skills"].items()}
    for key, prof in config.PROFILES.items()
}


def title_fit(title, profile):
    """'core', 'adjacent' or None (out of scope) for one person."""
    if profile["exclude"].search(title):
        return None
    if profile["core"].search(title):
        return "core"
    if profile["adjacent"].search(title):
        return "adjacent"
    return None


def fits_anyone(title):
    return any(title_fit(title, p) for p in config.PROFILES.values())


def _is_ict(job, text, strict=False):
    """Does the ad read as IT work? strict: ignore the title, need a clear IT term."""
    if config.SEEK_ICT in (job.get("seek_class") or []) and not strict:
        return True
    if not strict and config.ICT_TITLE_WORDS.search(job.get("title", "")) and not config.NON_ICT.search(job["title"]):
        return True

    def distinct(rx):
        return len({m.group(0).lower() for m in rx.finditer(text)})

    strong = distinct(config.ICT_STRONG)
    if strict and not strong:
        return False
    return 2 * strong + distinct(config.ICT_WEAK) - 2 * distinct(config.NON_ICT) >= 4


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
    """Attach visa findings and per-person scores to the job (in place).

    Leaves job["for"] empty when the job suits nobody; the caller drops it.
    """
    text = f"{job.get('title', '')}\n{job.get('teaser', '')}\n{description or ''}"
    job["hard_blockers"] = _scan(_HARD, text)
    job["soft_blockers"] = _scan(_SOFT, text)
    job["positives"] = _scan(_POS, text)
    job["recruiter"] = is_recruiter(job)
    job["accreditation"] = accreditation
    job["has_description"] = bool(description)
    job["summary"] = (description or job.get("teaser") or "")[:400]

    job["for"] = {}
    for key, prof in config.PROFILES.items():
        fit = title_fit(job["title"], prof)
        if not fit:
            continue
        if prof["needs_ict"] and not _is_ict(job, text):
            continue
        if fit == "adjacent" and prof.get("adjacent_needs_ict") and not _is_ict(job, text, strict=True):
            continue
        skills = sorted(name for name, rx in _SKILLS[key].items() if rx.search(text))
        job["for"][key] = {"fit": fit, "skills": skills}
    score(job)
    return job


def visa_ready(job):
    """Worth an email: the employer can sponsor, and the ad does not rule it out.

    Sponsor-capable means on the INZ accredited list, or the ad itself offers
    sponsorship (employers may hide themselves from the public list). An
    agency's own accreditation says nothing about its client.
    """
    if job.get("hard_blockers") or job.get("soft_blockers"):
        return False
    if "part" in (job.get("work_type") or "").lower():
        return False
    accredited = (job.get("accreditation") or {}).get("status") == ACCREDITED and not job.get("recruiter")
    offers = any(p["why"] == "Offers visa sponsorship" for p in job.get("positives") or [])
    return accredited or offers


def _visa_points(job):
    """The part of the score that is the same for everyone."""
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
    return s, reasons


def score(job):
    base, base_reasons = _visa_points(job)
    job["visa_ready"] = visa_ready(job)
    best = None
    for key, mine in job.get("for", {}).items():
        prof = config.PROFILES[key]
        s, reasons = base, list(base_reasons)
        s += 20 if mine["fit"] == "core" else 5
        if prof["too_senior"].search(job["title"]):
            s -= 10
            reasons.append("title above current level")
        s += min(len(mine["skills"]), 8) * 3
        if job.get("hard_blockers"):
            tier = "blocked"
        elif s >= config.TIER_A:
            tier = "A"
        elif s >= config.TIER_B:
            tier = "B"
        else:
            tier = "C"
        mine.update(score=s, tier=tier, reasons=reasons)
        if best is None or s > best["score"]:
            best = mine
    # Best across people, used for ordering.
    job["score"] = best["score"] if best else 0
    job["tier"] = best["tier"] if best else "C"
    return job
