"""HTTP helpers for the fetch stage: retries, resumable downloads, and the Brightcove playback lookup.

The federalreserve.gov player is a Brightcove player (account 66043936001). Its public policy key is read from
the player configuration at run time and kept in memory only; it is never written to disk or logs. The MP4 and
caption URLs it returns are signed and expire after about 6 hours, so a retry re-resolves them.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

UA = "fedpress/0.1 (academic research; FOMC press-conference archive)"
BC_PLAYER = "https://players.brightcove.net/{account}/{player}/config.json"
BC_API = "https://edge.api.brightcove.com/playback/v1/accounts/{account}/videos/{video}"
_PK_CACHE: dict[tuple[str, str], str] = {}
_PK_LOCK = threading.Lock()


class DownloadError(RuntimeError):
    pass


def strip_query(url: str) -> str:
    """URL without query/fragment (signed tokens are not worth keeping: they expire)."""
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))


@dataclass
class Http:
    timeout_s: float = 120.0
    retries: int = 3
    backoff_s: float = 2.0
    chunk_bytes: int = 8 << 20
    _session: Any = field(default=None, repr=False)

    @property
    def session(self) -> Any:
        if self._session is None:
            import requests

            self._session = requests.Session()
            self._session.headers["User-Agent"] = UA
        return self._session

    def _sleep(self, attempt: int) -> None:
        time.sleep(self.backoff_s * (2 ** attempt))

    def get(self, url: str, headers: dict[str, str] | None = None) -> bytes:
        """GET with retries on connection errors and 429/5xx."""
        import requests

        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                r = self.session.get(url, headers=headers or {}, timeout=self.timeout_s)
                if r.status_code == 429 or r.status_code >= 500:
                    raise DownloadError(f"HTTP {r.status_code} for {strip_query(url)}")
                r.raise_for_status()
                return r.content
            except (requests.ConnectionError, requests.Timeout, DownloadError) as e:
                last = e
                if attempt < self.retries:
                    self._sleep(attempt)
        raise DownloadError(f"GET failed after {self.retries + 1} attempts: {strip_query(url)}: {last!r}")

    def get_json(self, url: str, headers: dict[str, str] | None = None) -> Any:
        import json

        return json.loads(self.get(url, headers))

    def download(self, url_for: Callable[[int], str], dest: Path, expected_bytes: int | None = None,
                 max_bytes: int | None = None) -> dict[str, Any]:
        """Stream ``url_for(attempt)`` to ``dest`` through ``dest.part``, resuming with HTTP Range after a broken
        connection. ``url_for`` is called again on every retry, so signed URLs can be re-resolved. The final
        size must equal the server's total and, when given, ``expected_bytes``. ``max_bytes`` stops early
        (tests and clip extraction only; the result is then marked partial)."""
        import requests

        part = dest.with_name(dest.name + ".part")
        dest.parent.mkdir(parents=True, exist_ok=True)
        total: int | None = None
        resumed_from = part.stat().st_size if part.exists() else 0
        last: Exception | None = None
        url = ""
        for attempt in range(self.retries + 1):
            have = part.stat().st_size if part.exists() else 0
            if expected_bytes is not None and have > expected_bytes:
                part.unlink()
                have = 0
            goal = max_bytes if max_bytes is not None else expected_bytes
            if goal is not None and have >= goal:
                total = total or expected_bytes
                break
            try:
                url = url_for(attempt)
                headers = {}
                if have or max_bytes is not None:
                    end = "" if max_bytes is None else str(max_bytes - 1)
                    headers["Range"] = f"bytes={have}-{end}"
                with self.session.get(url, headers=headers, stream=True, timeout=self.timeout_s) as r:
                    if r.status_code == 416 and expected_bytes is not None and have == expected_bytes:
                        total = expected_bytes
                        break
                    if r.status_code in (403, 404, 410):
                        raise DownloadError(f"HTTP {r.status_code} (expired or missing URL)")
                    if r.status_code == 429 or r.status_code >= 500:
                        raise DownloadError(f"HTTP {r.status_code}")
                    r.raise_for_status()
                    if r.status_code == 200 and have:  # server ignored Range: start over
                        part.unlink(missing_ok=True)
                        have = 0
                    total = _total_size(r.headers, have) or total
                    mode = "ab" if have else "wb"
                    with part.open(mode) as fh:
                        for block in r.iter_content(self.chunk_bytes):
                            fh.write(block)
                size = part.stat().st_size
                if max_bytes is not None and size >= min(max_bytes, total or max_bytes):
                    break
                if total is not None and size == total:
                    break
                raise DownloadError(f"short read: {size} of {total} bytes")
            except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError,
                    DownloadError) as e:
                last = e
                if attempt < self.retries:
                    self._sleep(attempt)
        else:
            raise DownloadError(f"download failed after {self.retries + 1} attempts: {strip_query(url)}: {last!r}")
        size = part.stat().st_size if part.exists() else 0
        partial = max_bytes is not None and (total is None or size < total)
        if not partial:
            if total is not None and size != total:
                raise DownloadError(f"{dest.name}: {size} bytes, server total {total}")
            if expected_bytes is not None and size != expected_bytes:
                raise DownloadError(f"{dest.name}: {size} bytes, manifest expects {expected_bytes}")
        os.replace(part, dest)
        return {"bytes": size, "server_total": total, "resumed_from": resumed_from, "partial": partial,
                "url": strip_query(url)}


def _total_size(headers: Any, have: int) -> int | None:
    cr = headers.get("Content-Range")  # bytes a-b/total
    if cr and "/" in cr and not cr.endswith("/*"):
        return int(cr.rsplit("/", 1)[1])
    cl = headers.get("Content-Length")
    return int(cl) + have if cl is not None else None


# ------------------------------------------------------------------ Brightcove playback API
@dataclass
class Brightcove:
    http: Http
    account: str
    player: str = "default_default"

    def policy_key(self, refresh: bool = False) -> str:
        key = (self.account, self.player)
        with _PK_LOCK:
            if refresh or key not in _PK_CACHE:
                cfg = self.http.get_json(BC_PLAYER.format(account=self.account, player=self.player))
                _PK_CACHE[key] = cfg["video_cloud"]["policy_key"]
            return _PK_CACHE[key]

    def video(self, video_id: str) -> dict[str, Any]:
        url = BC_API.format(account=self.account, video=video_id)
        try:
            return self.http.get_json(url, {"Accept": f"application/json;pk={self.policy_key()}"})
        except DownloadError:  # a rotated policy key: fetch it again once
            return self.http.get_json(url, {"Accept": f"application/json;pk={self.policy_key(refresh=True)}"})


def pick_mp4(sources: list[dict[str, Any]], rule: str = "max_within_960x540", max_w: int = 960,
             max_h: int = 540) -> tuple[dict[str, Any] | None, str]:
    """The manifest rule: largest pixel area within max_w x max_h (ties: higher bitrate); if every rendition is
    larger, the largest available. ``rule`` 'highest' ignores the cap. HTTPS MP4 sources only."""
    mp4 = [s for s in sources if s.get("container") == "MP4" and str(s.get("src", "")).startswith("https")]
    if not mp4:
        return None, "no_mp4"

    def key(s: dict[str, Any]) -> tuple[int, int]:
        return int(s.get("width") or 0) * int(s.get("height") or 0), int(s.get("avg_bitrate") or 0)

    if rule != "highest":
        inside = [s for s in mp4 if int(s.get("width") or 0) <= max_w and int(s.get("height") or 0) <= max_h]
        if inside:
            return max(inside, key=key), f"max_within_{max_w}x{max_h}"
        return max(mp4, key=key), "above_cap_highest"
    return max(mp4, key=key), "highest"


def caption_src(video: dict[str, Any]) -> str | None:
    """HTTPS source of the first WebVTT captions track, or None when the video has none."""
    for t in video.get("text_tracks") or []:
        if t.get("kind") != "captions":
            continue
        srcs = [s.get("src", "") for s in t.get("sources") or []] + [t.get("src", "")]
        https = [s for s in srcs if s.startswith("https")]
        if https or srcs:
            return (https or srcs)[0] or None
    return None
