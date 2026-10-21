"""Cautious one-click apply helpers.

This module does NOT automate LinkedIn, Indeed, or other platforms that
explicitly forbid bots. It only pre-fills application data and returns safe
apply URLs. A future Playwright-based flow can be added for ATS platforms that
expose public application forms (Greenhouse, Lever, Ashby) with explicit
consent per-company.
"""

import re
from urllib.parse import urlparse

from app.models.job import Job


def is_safe_auto_apply_url(url: str) -> bool:
    """Return True only for known ATS public application URLs we are comfortable auto-opening."""
    if not url:
        return False
    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path or ""

    # Greenhouse, Lever, Ashby public boards are generally safe to open.
    safe_hosts = (
        "boards.greenhouse.io",
        "boards.eu.greenhouse.io",
        "jobs.lever.co",
        "jobs.ashbyhq.com",
        "careers.ashbyhq.com",
    )
    if any(host.endswith(safe) for safe in safe_hosts):
        return True

    # Greenhouse / Lever embedded paths on custom domains.
    if "/gh/" in path or "/job/" in path:
        return True

    # Embedded Greenhouse boards on custom career sites expose ?gh_jid=...
    query = parsed.query or ""
    if "gh_jid=" in query:
        return True

    return False


def parse_resume_contact(resume_text: str) -> dict:
    """Extract first name, last name, email, phone and LinkedIn from resume text."""
    payload = {
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
        "linkedin_url": "",
    }
    if not resume_text:
        return payload

    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    if lines:
        full_name = re.sub(r"\s+", " ", lines[0]).strip()
        # Avoid capturing a section header like "PROFESSIONAL SUMMARY"; the name is on the first line.
        parts = full_name.split()
        if len(parts) >= 2 and not re.match(r"^[A-Z][a-z]+\s+[A-Z][a-z]+.*$", full_name):
            pass
        if len(parts) >= 2:
            payload["first_name"] = parts[0].title()
            payload["last_name"] = " ".join(parts[1:]).title()
        else:
            payload["first_name"] = full_name.title()

    email_match = re.search(r"[\w.-]+@[\w.-]+\.\w+", resume_text)
    if email_match:
        payload["email"] = email_match.group(0)

    phone_match = re.search(r"\+\d[\d\s-]{6,}", resume_text)
    if phone_match:
        payload["phone"] = re.sub(r"\s+", " ", phone_match.group(0)).strip()

    linkedin_match = re.search(r"linkedin\.com/in/[\w-]+", resume_text)
    if linkedin_match:
        payload["linkedin_url"] = f"https://{linkedin_match.group(0)}"

    return payload


def build_application_payload(job: Job, user: dict, resume: object | None = None, cover_letter: str = "") -> dict:
    """Pre-fill data for a safe public ATS application form."""
    resume_url = user.get("resume_url", "")
    if resume and resume.file_name:
        resume_url = f"{resume.file_name}"

    return {
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "linkedin": user.get("linkedin_url", ""),
        "resume_url": resume_url,
        "resume_file_name": resume.file_name if resume else "",
        "cover_letter": cover_letter,
        "source": "Europe Job Agent",
    }


def apply_intent(job: Job, user: dict | None = None, resume: object | None = None, cover_letter: str = "") -> dict:
    """Record apply intent and return the safe action for the frontend."""
    user = user or parse_resume_contact(resume.content_text if resume else "")

    if not is_safe_auto_apply_url(job.application_url):
        return {
            "status": "manual",
            "message": "This job requires manual application.",
            "url": job.application_url,
            "payload": build_application_payload(job, user, resume, cover_letter),
        }

    return {
        "status": "auto-open",
        "message": "Open the application URL and use the pre-filled payload.",
        "url": job.application_url,
        "payload": build_application_payload(job, user, resume, cover_letter),
    }
