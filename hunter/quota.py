"""Watch the India Skilled Work Visa page for changes to places available.

Places are first come, first served (1,000 for the ICT sector). If INZ says
places are running out, you want to know the same hour.
"""

import hashlib
import logging
import re

from . import config
from .http import FetchError, request
from .sources import strip_html

log = logging.getLogger(__name__)


def read_status():
    """Return the sentences on the page that talk about places, or None."""
    try:
        text = strip_html(request(config.VISA_PAGE))
    except FetchError as exc:
        log.warning("Visa page fetch failed: %s", exc)
        return None
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    hits = []
    for s in sentences:
        s = " ".join(s.split())
        if re.search(r"\bplaces\b", s, re.I) and len(s) < 300 and s not in hits:
            hits.append(s)
    if not hits:
        return None
    return {"lines": hits, "hash": hashlib.sha256("\n".join(hits).encode()).hexdigest()}
