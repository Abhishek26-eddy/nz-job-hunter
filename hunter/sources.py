"""Job sources. Each search returns plain dicts; details are fetched only for
jobs that pass the title filter, to keep request counts low."""

import html
import logging
import re
import time
import urllib.parse

from . import config
from .http import FetchError, get_json, post_json, request

log = logging.getLogger(__name__)


def strip_html(text):
    text = re.sub(r"<(br|/p|/li|/h\d)\s*/?>", "\n", text or "", flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


# --- Seek NZ ----------------------------------------------------------------

SEEK_SEARCH = "https://nz.seek.com/api/jobsearch/v5/search"
SEEK_GRAPHQL = "https://nz.seek.com/graphql"
SEEK_DETAIL_QUERY = (
    "query jobDetails($jobId: ID!, $locale: Locale!) { jobDetails(id: $jobId) { job { "
    "title content(platform: WEB) advertiser { name(locale: $locale) } } } }"
)


def seek_search(keyword, days, classification=None, max_pages=3):
    jobs = []
    for page in range(1, max_pages + 1):
        params = {
            "siteKey": "NZ-Main",
            "where": "All New Zealand",
            "keywords": keyword,
            "page": page,
            "pageSize": 100,
            "sortmode": "ListedDate",
            "daterange": days,
        }
        if classification:
            params["classification"] = classification
        data = get_json(f"{SEEK_SEARCH}?{urllib.parse.urlencode(params)}")
        rows = data.get("data") or []
        for row in rows:
            loc = (row.get("locations") or [{}])[0]
            jobs.append({
                "id": f"seek:{row['id']}",
                "source": "Seek",
                "title": row.get("title", "").strip(),
                "company": (row.get("companyName") or (row.get("advertiser") or {}).get("description") or "").strip(),
                "advertiser": ((row.get("advertiser") or {}).get("description") or "").strip(),
                "location": loc.get("label", "New Zealand"),
                "url": f"https://www.seek.co.nz/job/{row['id']}",
                "posted_at": row.get("listingDate"),
                "work_type": ", ".join(row.get("workTypes") or []),
                "salary": row.get("salaryLabel") or "",
                "teaser": " ".join([row.get("teaser") or ""] + (row.get("bulletPoints") or [])).strip(),
                "seek_class": [str((c.get("classification") or {}).get("id", "")) for c in row.get("classifications") or []],
            })
        if len(rows) < 100:
            break
        time.sleep(1)
    return jobs


def seek_description(job):
    sid = job["id"].split(":", 1)[1]
    data = post_json(
        SEEK_GRAPHQL,
        {"operationName": "jobDetails", "variables": {"jobId": sid, "locale": "en-NZ"}, "query": SEEK_DETAIL_QUERY},
        headers={"seek-request-brand": "seek", "seek-request-country": "NZ"},
    )
    detail = ((data.get("data") or {}).get("jobDetails") or {}).get("job") or {}
    return strip_html(detail.get("content", "")), {}


# --- LinkedIn (public guest pages, no login) --------------------------------

LI_SEARCH = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
LI_DETAIL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
NZ_GEO_ID = "105490917"

_LI_CARD = re.compile(
    r'data-entity-urn="urn:li:jobPosting:(?P<id>\d+)".*?'
    r'base-search-card__title">\s*(?P<title>.*?)\s*</h3>.*?'
    r'base-search-card__subtitle">(?P<company>.*?)</h4>.*?'
    r'job-search-card__location">\s*(?P<location>.*?)\s*</span>'
    r'(?:.*?datetime="(?P<date>[\d-]+)")?',
    re.S,
)


def linkedin_search(query, seconds, max_pages=6):
    jobs = []
    for page in range(max_pages):
        params = {
            "keywords": query,
            "location": "New Zealand",
            "geoId": NZ_GEO_ID,
            "f_TPR": f"r{seconds}",
            "start": page * 10,
        }
        body = request(f"{LI_SEARCH}?{urllib.parse.urlencode(params)}")
        cards = body.split("<li>")[1:]
        for card in cards:
            m = _LI_CARD.search(card)
            if not m:
                continue
            jid = m["id"]
            jobs.append({
                "id": f"linkedin:{jid}",
                "source": "LinkedIn",
                "title": strip_html(m["title"]),
                "company": strip_html(m["company"]),
                "advertiser": strip_html(m["company"]),
                "location": strip_html(m["location"]),
                "url": f"https://www.linkedin.com/jobs/view/{jid}/",
                "posted_at": f"{m['date']}T00:00:00Z" if m["date"] else None,
                "work_type": "",
                "salary": "",
                "teaser": "",
            })
        if len(cards) < 10:
            break
        time.sleep(2.5)
    return jobs


def linkedin_description(job):
    jid = job["id"].split(":", 1)[1]
    body = request(LI_DETAIL.format(jid))
    m = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', body, re.S)
    extra = {}
    for label, value in re.findall(
        r'description__job-criteria-subheader">\s*(.*?)\s*</h3>.*?description__job-criteria-text[^>]*>\s*(.*?)\s*</span>',
        body,
        re.S,
    ):
        if "employment type" in label.lower():
            extra["work_type"] = strip_html(value)
    return strip_html(m.group(1) if m else ""), extra


# --- Orchestration ----------------------------------------------------------


def search_all(first_run):
    """Run every search. A failing query is logged and skipped, never fatal."""
    days = 31 if first_run else 7
    found, errors = {}, []

    seek = dict.fromkeys(s for p in config.PROFILES.values() for s in p["seek"])
    linkedin = dict.fromkeys(q for p in config.PROFILES.values() for q in p["linkedin"])

    for kw, classification in seek:
        try:
            for job in seek_search(kw, days, classification):
                found.setdefault(job["id"], job)
        except (FetchError, ValueError, KeyError) as exc:
            errors.append(f"Seek '{kw}': {exc}")
        time.sleep(1)

    for q in linkedin:
        try:
            for job in linkedin_search(q, days * 86400):
                found.setdefault(job["id"], job)
        except FetchError as exc:
            errors.append(f"LinkedIn '{q[:30]}': {exc}")
        time.sleep(3)

    return list(found.values()), errors


def fetch_description(job):
    if job["source"] == "Seek":
        return seek_description(job)
    return linkedin_description(job)
