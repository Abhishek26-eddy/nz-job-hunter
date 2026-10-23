"""Email alerts over SMTP (Gmail app password by default)."""

import html
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

log = logging.getLogger(__name__)

MAX_ROWS = 60
TIER_LABEL = {"A": "Apply now", "B": "Good", "C": "Maybe", "blocked": "Blocked"}
ROUTE_LABEL = {
    "iswv": "🇮🇳 India Skilled Work Visa or AEWV",
    "aewv": "AEWV only (not an India Skilled Work Visa job)",
}
ACC_LABEL = {
    "accredited": "✅ Accredited",
    "expired": "⚠️ Accreditation expired",
    "not_listed": "❔ Not on public list",
    "unknown": "❔ Not checked",
}


def _acc(job):
    acc = job.get("accreditation") or {}
    label = ACC_LABEL.get(acc.get("status"), "❔")
    if acc.get("status") == "accredited" and acc.get("expiry"):
        label += f" (to {acc['expiry']})"
    if job.get("recruiter") and acc.get("status") != "accredited":
        label = "🕵️ Agency: ask the employer's name"
    return label


def _row(job, person):
    e = html.escape
    mine = job["for"][person]
    warn = "; ".join(b["why"] for b in job.get("soft_blockers") or [])
    good = "; ".join(p["why"] for p in job.get("positives") or [])
    route = ROUTE_LABEL.get(mine.get("route"), "")
    notes = " · ".join(x for x in [route, good and f"👍 {good}", warn and f"⚠️ {warn}"] if x)
    return (
        "<tr>"
        f"<td style='padding:6px;border-bottom:1px solid #eee'><b>{e(TIER_LABEL[mine['tier']])}</b><br>"
        f"<small>{mine['score']}</small></td>"
        f"<td style='padding:6px;border-bottom:1px solid #eee'><a href='{e(job['url'])}'><b>{e(job['title'])}</b></a><br>"
        f"{e(job['company'])} · {e(job.get('location') or '')} · {e(job['source'])}"
        f"{' · ' + e(job['work_type']) if job.get('work_type') else ''}"
        f"{' · ' + e(job['salary']) if job.get('salary') else ''}<br>"
        f"<small>{e(notes)}</small></td>"
        f"<td style='padding:6px;border-bottom:1px solid #eee'><small>{e(_acc(job))}</small></td>"
        "</tr>"
    )


def render_jobs_email(jobs, person, site_url, held_back, errors, intro=None):
    head = intro or (
        f"<p>{len(jobs)} new NZ job(s) where the employer is accredited to sponsor a work visa."
        f"{f' {held_back} other new match(es) are on the dashboard only (employer not accredited, agency ad, or the ad rules out visa holders).' if held_back else ''}</p>"
    )
    if site_url:
        head += f"<p><a href='{html.escape(site_url)}#{person}'>Open the dashboard</a></p>"
    rows = "".join(_row(j, person) for j in jobs[:MAX_ROWS])
    more = f"<p>…and {len(jobs) - MAX_ROWS} more on the dashboard.</p>" if len(jobs) > MAX_ROWS else ""
    errs = ""
    if errors:
        errs = "<p style='color:#a00'><small>Some sources failed this run: " + html.escape("; ".join(errors[:5])) + "</small></p>"
    tip = (
        "<p><small>Before you apply: the offer must be full time (30h+) from an accredited employer. "
        "For the India Skilled Work Visa it must be described as Software Engineer, Software and "
        "Applications Programmer or ICT Project Manager; other roles need the regular AEWV. "
        "Never pay anyone for a job offer.</small></p>"
    )
    return (
        "<div style='font-family:-apple-system,Segoe UI,sans-serif;font-size:14px'>"
        f"{head}<table style='border-collapse:collapse;width:100%'>{rows}</table>{more}{tip}{errs}</div>"
    )


def send(subject, html_body, out_path=None, to=None, cc=None):
    """Send the email. Without SMTP settings, write it to out_path instead."""
    if out_path:
        with open(out_path, "w") as fh:
            fh.write(f"<h3>{html.escape(subject)}</h3>{html_body}")
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    to = to or os.environ.get("ALERT_TO") or user
    if not (user and password and to):
        missing = [n for n, v in (("SMTP_USER", user), ("SMTP_PASSWORD", password)) if not v]
        log.warning("Email not sent, missing: %s (saved to %s)", ", ".join(missing), out_path)
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    if cc and cc != to:
        msg["Cc"] = cc
    msg.set_content("Open this email in an HTML-capable client.")
    msg.add_alternative(html_body, subtype="html")
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)
    log.info("Emailed %s: %s", to, subject)
    return True
