"""frames (cpu): sample video frames on the slot grid t_k = k / frames.fps for the face stage.

store: zip (default, team plan 1 fps)
    JPEG frames in one zip per meeting (Lustre prefers one big file to thousands of small ones) plus an index
    parquet: frames/frames_<fps>fps.zip and frames/frames_<fps>fps.parquet (frame_idx, t_s, member, width, height).
store: index (for the 2-5 fps options)
    No JPEGs at frames.fps: the index lists the slots only and the face stage decodes the video itself, in
    batches, inside the GPU job (NVDEC when available). A small JPEG sample at frames.qa_sample_fps (default 1)
    is kept for checking the face stage by eye.

Both write frames/frames_meta.json (probe, output size, decode settings, timing). Frames are downscaled to
frames.max_height (2015-12-16 is 1280x720), so features see one frame size per era. ``runtime.max_seconds``
(CLI --max-seconds) limits decoding to the first N media seconds for smoke tests; the done-marker then
records the cut and a full run redoes the meeting.
"""

from __future__ import annotations

import os
import time
import zipfile
from pathlib import Path

from .. import io
from ..stage import StageContext, StageResult, StageSpec, max_seconds
from . import _video

SPEC = StageSpec(name="frames", requires=("fetch",), resource="cpu",
                 outputs=("frames_zip", "frames_index", "frames_meta"), config_keys=(), stamped=False)


def _chairs(ctx: StageContext) -> list[str] | None:
    chairs = ctx.scfg.get("chairs")
    if chairs is None and ctx.cfg.section("face").get("enabled", True):
        chairs = ctx.cfg.get("face.chairs", None)
    return list(chairs) if chairs else None


def applies(ctx: StageContext) -> str | None:
    chairs = _chairs(ctx)
    if chairs and ctx.meeting.chair not in chairs:
        return f"chair {ctx.meeting.chair} not in frames.chairs/face.chairs {chairs}"
    return None


def _write_zip(ctx: StageContext, video: Path, info: _video.VideoInfo, fps: float, stop_s: float) -> tuple[int, dict]:
    """Decode [0, stop_s) at ``fps`` into frames_<fps>fps.zip + index. Returns (frames, decode stats)."""
    import cv2
    import pandas as pd

    s = ctx.scfg
    zpath = ctx.out("frames_zip", fps=fps)
    tmp = zpath.with_name(f".{zpath.name}.{os.getpid()}.tmp")
    rows, events = [], []
    quality = [int(cv2.IMWRITE_JPEG_QUALITY), int(s.get("jpeg_quality", 90))]
    t0 = time.perf_counter()
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_STORED) as zf:
        for k, t, rgb in _video.iter_frames(video, info, fps, [(0.0, stop_s)], max_height=s.get("max_height"),
                                            hwaccel=str(s.get("hwaccel", "none")), threads=int(s.get("threads", 0)),
                                            ffmpeg=_video.resolve_ffmpeg(str(s.get("ffmpeg", "ffmpeg"))),
                                            on_event=lambda e, **f: events.append({"event": e, **f})):
            ok, jpg = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), quality)
            if not ok:
                raise RuntimeError(f"JPEG encode failed at slot {k}")
            member = f"f{k:07d}.jpg"
            zf.writestr(member, jpg.tobytes())
            rows.append({"frame_idx": k, "t_s": t, "member": member, "width": rgb.shape[1], "height": rgb.shape[0]})
    os.replace(tmp, zpath)
    ctx.write_table(pd.DataFrame(rows), "frames_index", fps=fps)
    ctx.add_output(zpath)
    for e in events:
        ctx.log.info(e.pop("event"), **e)
    return len(rows), {"decode_s": round(time.perf_counter() - t0, 2), "ranges": events}


def run(ctx: StageContext) -> StageResult:
    import pandas as pd

    s = ctx.scfg
    video = ctx.out("video")
    ffmpeg = _video.resolve_ffmpeg(str(s.get("ffmpeg", "ffmpeg")))
    info = _video.probe(video, ffmpeg)
    fps = float(s.get("fps", 1.0))
    store = str(s.get("store", "zip"))
    cut = max_seconds(ctx.cfg)
    stop_s = min(info.duration_s, cut) if cut else info.duration_s
    out_w, out_h = info.out_size(s.get("max_height"))
    expected = _video.slot_range(0.0, stop_s, fps)[1]
    meta: dict = {"probe": info.to_json(), "fps": fps, "store": store, "out_width": out_w, "out_height": out_h,
                  "stop_s": stop_s, "max_seconds": cut, "slot_rule": "t_k = k/fps; latest source frame <= t_k",
                  "hwaccel_requested": s.get("hwaccel", "none"),
                  "hwaccel_available": sorted(_video.hwaccels(ffmpeg))}
    qa_fps = float(s.get("qa_sample_fps", 0) or 0)
    if store == "zip" or (store == "index" and qa_fps == fps):
        n, stats = _write_zip(ctx, video, info, fps, stop_s)
        meta.update(n_frames=n, members=True, **stats)
    elif store == "index":
        k1 = expected
        idx = pd.DataFrame({"frame_idx": range(k1), "t_s": [k / fps for k in range(k1)], "member": "",
                            "width": out_w, "height": out_h})
        ctx.write_table(idx, "frames_index", fps=fps)
        meta.update(n_frames=k1, members=False)
        if qa_fps > 0:
            n_qa, stats = _write_zip(ctx, video, info, qa_fps, stop_s)
            meta.update(qa_sample_fps=qa_fps, qa_frames=n_qa, qa=stats)
    else:
        raise ValueError(f"frames.store must be zip or index, got {store!r}")
    if meta["n_frames"] < expected - 1:
        raise RuntimeError(f"decoded {meta['n_frames']} frames, expected {expected} for {stop_s:.1f} s at {fps} fps")
    io.atomic_write_json(ctx.out("frames_meta"), meta)
    ctx.add_output(ctx.out("frames_meta"))
    ctx.result.notes.update(fps=fps, store=store, n_frames=meta["n_frames"], width=out_w, height=out_h,
                            src_width=info.width, src_height=info.height, duration_s=info.duration_s,
                            decode_s=meta.get("decode_s"), max_seconds=cut)
    return ctx.result
