"""fetch (net): official MP4, transcript PDF, statement HTML and (optional) WebVTT captions for one meeting.

* MP4: re-resolved from the Brightcove video id (manifest URLs are signed and expired), same rendition rule as
  the manifest (``fetch.mp4_rule``), streamed with HTTP Range resume and retries; the final size must equal the
  manifest ``mp4_bytes`` (``fetch.verify_bytes``). An existing file of the right size is kept.
* Transcript PDF / captions: copied from ``manifest.local_seed_dir`` when a seed copy with the manifest sha256
  exists (captions are compared after CRLF->LF, as the server sends them), otherwise downloaded. Size or hash
  differences from the manifest are recorded as warnings (the Board occasionally re-posts files).
* Statement HTML: downloaded from ``statement_url`` (the text stage needs it).

Writes ``fetch_meta`` raw/fetch.json: per file source (download | seed | existing), URL without its token, bytes,
sha256, expected values and checks. Federal Reserve Board files are public domain; YouTube and C-SPAN are
not used. Run in a CPU job or dev session (outbound HTTPS).
"""

from __future__ import annotations

import hashlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from .. import io
from ..stage import StageContext, StageResult, StageSpec
from ._http import UA, Brightcove, DownloadError, Http, caption_src, pick_mp4, strip_query

SPEC = StageSpec(name="fetch", requires=(), resource="net",
                 outputs=("video", "transcript_pdf", "statement_html", "captions_vtt", "fetch_meta"),
                 config_keys=(), stamped=False)


class _Video:
    """Brightcove playback JSON for this meeting, fetched once and re-fetched on demand (thread-safe)."""

    def __init__(self, bc: Brightcove, video_id: str) -> None:
        self.bc, self.video_id, self._data, self._lock = bc, video_id, None, threading.Lock()

    def get(self, refresh: bool = False) -> dict[str, Any]:
        with self._lock:
            if refresh or self._data is None:
                self._data = self.bc.video(self.video_id)
            return self._data


def run(ctx: StageContext) -> StageResult:
    s, m = ctx.scfg, ctx.meeting

    def http() -> Http:  # one client per thread: requests sessions are not guaranteed thread-safe
        return Http(timeout_s=float(s.get("timeout_s", 120)), retries=int(s.get("retries", 3)))

    video = _Video(Brightcove(http(), str(m.brightcove_account_id or s.get("brightcove_account_id")),
                              str(s.get("brightcove_player", "default_default"))), m.brightcove_video_id)
    seed = str(ctx.cfg.get("manifest.local_seed_dir", "") or "")
    jobs: dict[str, Callable[[], dict[str, Any] | None]] = {}
    if s.get("video", True):
        jobs["video"] = lambda: _video(ctx, http(), video)
    if s.get("transcript_pdf", True):
        jobs["transcript_pdf"] = lambda: _small(ctx, http(), "transcript_pdf", m.transcript_pdf_url, seed,
                                                m.local_pdf_path, m.local_pdf_sha256, m.transcript_pdf_bytes, False)
    if s.get("statement_html", True):
        jobs["statement_html"] = lambda: _small(ctx, http(), "statement_html", m.statement_url, "", "", "", None, False)
    if s.get("captions_vtt", False):
        jobs["captions_vtt"] = lambda: _captions(ctx, http(), video, seed)
    if not jobs:
        raise ValueError("fetch: every file type is switched off")
    t0 = time.perf_counter()
    files: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=max(1, int(s.get("parallel", 4)))) as pool:
        futures = {k: pool.submit(fn) for k, fn in jobs.items()}
        errors = {}
        for k, f in futures.items():
            try:
                files[k] = f.result()
            except Exception as e:  # finish the other downloads first, then fail this meeting
                errors[k] = repr(e)
    if errors:
        raise DownloadError(f"fetch failed: {errors}")
    for k, info in files.items():
        if info is not None:
            ctx.add_output(ctx.out(k))
    meta = {"presser_id": m.presser_id, "user_agent": UA, "elapsed_s": round(time.perf_counter() - t0, 2),
            "created_utc": io.utc_now(), "files": files}
    ctx.add_output(io.atomic_write_json(ctx.out("fetch_meta"), meta))
    warnings = {k: v["warning"] for k, v in files.items() if v and v.get("warning")}
    ctx.result.notes.update({"sources": {k: (v or {}).get("source", "absent") for k, v in files.items()},
                             "video_bytes": (files.get("video") or {}).get("bytes"), "warnings": warnings})
    for k, w in warnings.items():
        ctx.log.warning("fetch.check", file=k, warning=w)
    return ctx.result


def _video(ctx: StageContext, http: Http, video: _Video) -> dict[str, Any]:
    s, m = ctx.scfg, ctx.meeting
    dest = ctx.out("video")
    expected = m.mp4_bytes if s.get("verify_bytes", True) else None
    if dest.exists() and expected is not None and dest.stat().st_size == expected and not s.get("redownload", False):
        return {"source": "existing", "bytes": expected, "expected_bytes": expected,
                "sha256": io.sha256_file(dest) if s.get("hash_video", True) else None}
    rule = str(s.get("mp4_rule", "max_within_960x540"))
    mw, mh = int(s.get("max_width", 960)), int(s.get("max_height", 540))
    src, chosen = pick_mp4(video.get().get("sources", []), rule, mw, mh)
    if src is None:
        raise DownloadError(f"no HTTPS MP4 rendition for Brightcove video {m.brightcove_video_id}")
    if (int(src.get("width") or 0), int(src.get("height") or 0)) != (m.mp4_width, m.mp4_height):
        ctx.log.warning("fetch.rendition_changed", manifest=f"{m.mp4_width}x{m.mp4_height}",
                        now=f"{src.get('width')}x{src.get('height')}")

    def url_for(attempt: int) -> str:
        if attempt == 0:
            return str(src["src"])
        fresh, _ = pick_mp4(video.get(refresh=True).get("sources", []), rule, mw, mh)  # signed URL may have expired
        return str((fresh or src)["src"])

    ctx.log.info("fetch.video_start", width=src.get("width"), height=src.get("height"), expected_bytes=expected)
    info = http.download(url_for, dest, expected_bytes=expected)
    return {"source": "download", **info, "expected_bytes": expected, "rule": chosen,
            "width": src.get("width"), "height": src.get("height"), "avg_bitrate": src.get("avg_bitrate"),
            "api_size": src.get("size"), "sha256": io.sha256_file(dest) if s.get("hash_video", True) else None}


def _captions(ctx: StageContext, http: Http, video: _Video, seed: str) -> dict[str, Any] | None:
    m = ctx.meeting
    if not m.has_vtt:
        return None  # 12 videos have no caption track (7 in the default sample)
    got = _from_seed(ctx, "captions_vtt", seed, m.local_vtt_path, m.local_vtt_sha256, True)
    if got:
        return got
    url = caption_src(video.get())
    if not url:
        ctx.log.warning("fetch.no_captions", video_id=m.brightcove_video_id)
        return None
    return _small(ctx, http, "captions_vtt", url, "", "", m.local_vtt_sha256, m.vtt_bytes, True)


def _from_seed(ctx: StageContext, key: str, seed: str, rel: str, sha: str, text: bool) -> dict[str, Any] | None:
    if not (seed and rel):
        return None
    p = Path(seed) / rel
    if not p.is_file():
        return None
    data = _served(p.read_bytes(), text)
    digest = hashlib.sha256(data).hexdigest()
    if sha and digest != sha:
        ctx.log.warning("fetch.seed_hash_mismatch", file=str(p))
        return None
    io.atomic_write_bytes(ctx.out(key), data)
    return {"source": "seed", "path": str(p), "bytes": len(data), "sha256": digest}


def _small(ctx: StageContext, http: Http, key: str, url: str, seed: str, seed_rel: str, sha: str,
           expected: int | None, text: bool) -> dict[str, Any]:
    """A small file (PDF, HTML, VTT): seed copy, existing file with the manifest hash, or a download."""
    got = _from_seed(ctx, key, seed, seed_rel, sha, text)
    if got:
        return got
    dest = ctx.out(key)
    if dest.exists() and sha and io.sha256_file(dest) == sha:
        return {"source": "existing", "bytes": dest.stat().st_size, "sha256": sha}
    if not url:
        raise DownloadError(f"{key}: no URL in the manifest")
    data = _served(http.get(url), text)
    digest = hashlib.sha256(data).hexdigest()
    io.atomic_write_bytes(dest, data)
    warn = []
    if expected is not None and len(data) != expected:
        warn.append(f"size {len(data)} != manifest {expected}")
    if sha and digest != sha:
        warn.append("sha256 differs from the manifest's local copy")
    return {"source": "download", "url": strip_query(url), "bytes": len(data), "expected_bytes": expected,
            "sha256": digest, "warning": "; ".join(warn) or None}


def _served(data: bytes, text: bool) -> bytes:
    return data.replace(b"\r\n", b"\n") if text else data
