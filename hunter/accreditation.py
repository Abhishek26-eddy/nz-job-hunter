"""Check employers against the INZ accredited employer list.

INZ has no bulk download, only a search box backed by a JSON endpoint. We
look each employer up once and cache the answer. Employers can opt out of the
public list, so "not listed" means "ask them", not "rejected".
"""

import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone

from . import config
from .http import FetchError, post_multipart

log = logging.getLogger(__name__)

ACCREDITED = "accredited"
NOT_LISTED = "not_listed"
EXPIRED = "expired"
UNKNOWN = "unknown"  # lookup failed; retried next run

_SUFFIXES = re.compile(
    r"\b(limited|ltd|llc|inc|incorporated|pty|plc|co|company|corporation|corp|group|holdings|"
    r"the|nz|new zealand|aotearoa|services|solutions|technologies|technology)\b"
)


def normalise(name):
    name = name.lower().replace("&", " and ")
    name = re.sub(r"\(.*?\)", " ", name)
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    return " ".join(_SUFFIXES.sub(" ", name).split())


def _query_for(name):
    alias = config.EMPLOYER_ALIASES.get(name.lower().strip())
    if alias:
        return alias
    words = re.sub(r"[^A-Za-z0-9& ]", " ", name).split()
    # The search matches whole words; the first two words are enough to find it.
    return " ".join(words[:2]) if words else name


def _rows(query):
    out, page = [], 1
    while page <= 3:
        try:
            data = post_multipart(
                config.INZ_EMPLOYER_API,
                {"query": query, "collection": config.INZ_EMPLOYER_COLLECTION, "page": page},
            )
        except FetchError as exc:
            # INZ answers an empty search with HTTP 400 "No Results".
            if exc.code == 400 and "No Results" in exc.body:
                return out
            raise
        for item in json.loads(data.get("results") or "[]"):
            out.append({f["APIColumn"]: f.get("Value") for f in item["field_schema"]["raw"]})
        if page >= int(data.get("totalPages") or 1):
            break
        page += 1
    return out


def _match(name, rows):
    """Pick the listed employer that is clearly the same company."""
    target = normalise(config.EMPLOYER_ALIASES.get(name.lower().strip(), name))
    if not target:
        return None
    tset = set(target.split())
    best, best_score = None, 0.0
    for row in rows:
        for field in ("employerName", "tradingName"):
            cand = normalise(row.get(field) or "")
            if not cand:
                continue
            if cand == target:
                return row
            cset = set(cand.split())
            overlap = len(tset & cset) / max(len(tset | cset), 1)
            if overlap > best_score:
                best, best_score = row, overlap
    return best if best_score >= 0.6 else None


class AccreditationCache:
    def __init__(self, path):
        self.path = path
        try:
            with open(path) as fh:
                self.data = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {}
        self.lookups = 0

    def save(self):
        with open(self.path, "w") as fh:
            json.dump(self.data, fh, indent=1, sort_keys=True)

    def check(self, name, max_lookups=150):
        key = normalise(name)
        if not key or len(key) < 3:
            return {"status": UNKNOWN}
        now = datetime.now(timezone.utc)
        hit = self.data.get(key)
        if hit and hit["status"] != UNKNOWN:
            ttl = timedelta(days=7 if hit["status"] == ACCREDITED else 3)
            if now - datetime.fromisoformat(hit["checked_at"]) < ttl:
                return hit
        if self.lookups >= max_lookups:
            return hit or {"status": UNKNOWN}

        self.lookups += 1
        time.sleep(0.4)
        try:
            row = _match(name, _rows(_query_for(name)))
        except (FetchError, ValueError, KeyError) as exc:
            log.warning("INZ lookup failed for %s: %s", name, exc)
            return hit or {"status": UNKNOWN}

        result = {"status": NOT_LISTED, "checked_at": now.isoformat()}
        if row:
            expiry = (row.get("expiryDateOfAccreditation") or "")[:10]
            status = ACCREDITED
            if expiry and expiry < now.date().isoformat():
                status = EXPIRED
            result.update(
                status=status,
                legal_name=row.get("employerName"),
                nzbn=row.get("nzbn"),
                expiry=expiry,
            )
        self.data[key] = result
        return result
