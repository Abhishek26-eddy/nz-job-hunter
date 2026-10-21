"""Tiny HTTP layer: stdlib only, polite retries, no crash on a bad source."""

import json
import logging
import random
import time
import urllib.error
import urllib.request
import uuid

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


class FetchError(Exception):
    def __init__(self, message, code=None, body=""):
        super().__init__(message)
        self.code = code
        self.body = body


def request(url, *, data=None, headers=None, method=None, retries=4, timeout=30):
    """Return the response body as text. Backs off on 429/5xx."""
    hdrs = {"User-Agent": USER_AGENT, "Accept-Language": "en-NZ,en;q=0.9"}
    hdrs.update(headers or {})
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                wait = (2 ** attempt) * 3 + random.uniform(0, 2)
                log.info("HTTP %s from %s, retrying in %.0fs", exc.code, url[:80], wait)
                time.sleep(wait)
                continue
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise FetchError(f"HTTP {exc.code} for {url[:120]}", exc.code, body) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < retries - 1:
                time.sleep(3 + attempt * 3)
                continue
            raise FetchError(f"{exc} for {url[:120]}") from exc
    raise FetchError(f"gave up on {url[:120]}")


def get_json(url, **kw):
    return json.loads(request(url, **kw))


def post_json(url, payload, headers=None):
    hdrs = {"Content-Type": "application/json"}
    hdrs.update(headers or {})
    return json.loads(request(url, data=json.dumps(payload).encode(), headers=hdrs, method="POST"))


def post_multipart(url, fields):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
        )
    body = ("".join(parts) + f"--{boundary}--\r\n").encode()
    hdrs = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    return json.loads(request(url, data=body, headers=hdrs, method="POST"))
