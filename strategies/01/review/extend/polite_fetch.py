"""Polite, cached HTTP GET for federalreserve.gov pages.

One request at a time, a fixed pause between live requests, browser-like
User-Agent, and an on-disk cache so nothing is fetched twice.
"""

from __future__ import annotations

import time
from pathlib import Path

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
PAUSE_S = 1.5

_session = requests.Session()
_session.headers.update(HEADERS)
_last_live = [0.0]
LOG: list[dict] = []


def get(url: str, cache_path: Path, max_tries: int = 3) -> tuple[str | None, int, bool]:
    """Return (text, status, from_cache). text is None when the page could not be fetched."""
    if cache_path.exists() and cache_path.stat().st_size > 500:
        return cache_path.read_text(encoding="utf-8", errors="replace"), 200, True
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    status = -1
    for attempt in range(max_tries):
        wait = PAUSE_S - (time.monotonic() - _last_live[0])
        if wait > 0:
            time.sleep(wait)
        try:
            r = _session.get(url, timeout=45)
            _last_live[0] = time.monotonic()
            status = r.status_code
            LOG.append({"url": url, "status": status, "attempt": attempt + 1, "bytes": len(r.content)})
            if status == 200:
                r.encoding = r.encoding or "utf-8"
                text = r.text
                cache_path.write_text(text, encoding="utf-8")
                return text, status, False
            if status == 404:
                return None, status, False
        except requests.RequestException as exc:  # network hiccup: back off and retry
            _last_live[0] = time.monotonic()
            LOG.append({"url": url, "status": -1, "attempt": attempt + 1, "error": str(exc)[:200]})
        time.sleep(3.0 * (attempt + 1))
    return None, status, False
