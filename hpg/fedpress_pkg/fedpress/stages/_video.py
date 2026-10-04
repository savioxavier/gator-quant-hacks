"""Video probing and frame decoding with ffmpeg, streamed through a pipe (no temporary image files).

Frame clock. Frames are taken on a fixed grid of slots ``t_k = k / fps`` (media seconds from the start of the
file, the same zero the audio stage uses). ffmpeg's ``fps`` filter runs with ``round=up`` and ``start_time=0``,
so slot ``k`` carries the latest source frame whose timestamp is at or before ``t_k``: a frame never shows
content from after its own time stamp, which keeps per-frame ``known_at`` causal. A range ``[a, b)`` starts at
the first slot ``>= a`` (input seek to that slot time), so frame indices agree across ranges, the frames zip
and the streaming path.

Decoding uses NVDEC (``-hwaccel cuda``) when ``hwaccel`` is ``cuda`` or ``auto`` and the ffmpeg build lists
it; frames are downloaded to host memory and scaled on the CPU (they are small). Any NVDEC failure falls back
to CPU decoding for that range.
"""

from __future__ import annotations

import functools
import json
import math
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

EPS = 1e-6


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    fps: float            # average source frame rate
    duration_s: float
    codec: str
    pix_fmt: str
    bit_rate: int | None
    n_frames: int | None
    stream_start_s: float  # video stream start relative to the file start (normally ~0)

    def out_size(self, max_height: int | None) -> tuple[int, int]:
        """Output (width, height): downscale to ``max_height`` keeping the aspect ratio, even width."""
        if not max_height or self.height <= max_height:
            return self.width, self.height
        h = int(max_height)
        w = int(round(self.width * h / self.height / 2.0)) * 2
        return w, h

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def _ratio(text: str | None) -> float:
    if not text or text in ("0/0", "N/A"):
        return float("nan")
    if "/" in text:
        a, b = text.split("/", 1)
        return float(a) / float(b) if float(b) else float("nan")
    return float(text)


def resolve_ffmpeg(name: str = "ffmpeg") -> str:
    """The configured ffmpeg (name on PATH or a path), else the imageio-ffmpeg binary (laptop smoke tests)."""
    found = shutil.which(name) or (name if Path(name).is_file() else None)
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise FileNotFoundError(f"ffmpeg {name!r} not found: conda env, `module load ffmpeg` or frames.ffmpeg") from None


def find_ffprobe(ffmpeg: str) -> str | None:
    """ffprobe next to the configured ffmpeg, else on PATH (some static ffmpeg builds ship without it)."""
    exe = shutil.which(ffmpeg) or ffmpeg
    sib = Path(exe).with_name(Path(exe).name.replace("ffmpeg", "ffprobe"))
    if sib.name != Path(exe).name and sib.exists():
        return str(sib)
    return shutil.which("ffprobe")


def probe(video: Path, ffmpeg: str = "ffmpeg") -> VideoInfo:
    """Stream geometry, rate and duration (ffprobe JSON; falls back to parsing ``ffmpeg -i``)."""
    ffprobe = find_ffprobe(ffmpeg)
    if ffprobe:
        out = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_streams", "-show_format",
                              "-of", "json", str(video)], capture_output=True, text=True, check=True, timeout=120)
        d = json.loads(out.stdout)
        st, fmt = d["streams"][0], d.get("format", {})
        fmt_start = float(fmt.get("start_time") or 0.0)
        dur = float(st.get("duration") or fmt.get("duration") or "nan")
        nb = st.get("nb_frames")
        return VideoInfo(int(st["width"]), int(st["height"]), _ratio(st.get("avg_frame_rate") or st.get("r_frame_rate")),
                         dur, str(st.get("codec_name", "")), str(st.get("pix_fmt", "")),
                         int(st["bit_rate"]) if st.get("bit_rate") else None, int(nb) if nb else None,
                         float(st.get("start_time") or 0.0) - fmt_start)
    res = subprocess.run([ffmpeg, "-hide_banner", "-i", str(video)], capture_output=True, text=True, timeout=120)
    err = res.stderr
    m_d = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+),\s*start:\s*([-\d.]+)", err)
    m_v = re.search(r"Stream #\S+.*?Video:\s*(\w+).*?,\s*(\w+)(?:\([^)]*\))?,\s*(\d{2,5})x(\d{2,5})", err)
    m_f = re.search(r"([\d.]+)\s*fps", err)
    m_b = re.search(r"Video:.*?(\d+)\s*kb/s", err)
    if not (m_d and m_v):
        raise RuntimeError(f"cannot probe {video}: {err[-400:]}")
    dur = int(m_d.group(1)) * 3600 + int(m_d.group(2)) * 60 + float(m_d.group(3))
    return VideoInfo(int(m_v.group(3)), int(m_v.group(4)), float(m_f.group(1)) if m_f else float("nan"), dur,
                     m_v.group(1), m_v.group(2), int(m_b.group(1)) * 1000 if m_b else None, None, 0.0)


@functools.lru_cache(maxsize=8)
def hwaccels(ffmpeg: str) -> frozenset[str]:
    try:
        out = subprocess.run([ffmpeg, "-hide_banner", "-hwaccels"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    return frozenset(line.strip() for line in out.splitlines()[1:] if line.strip())


def _gpu_visible() -> bool:
    env = os.environ.get("CUDA_VISIBLE_DEVICES")
    if env is not None:
        return bool(env.strip()) and env.strip() != "-1"
    return shutil.which("nvidia-smi") is not None


def choose_hwaccel(requested: str, ffmpeg: str) -> str | None:
    """'cuda' when requested/auto and usable, else None (CPU decoding)."""
    if requested in ("none", "cpu", "", None):
        return None
    if requested == "cuda" or (requested == "auto" and _gpu_visible()):
        return "cuda" if "cuda" in hwaccels(ffmpeg) else None
    return None


def slot_range(a: float, b: float, fps: float) -> tuple[int, int]:
    """Slots k with a <= k/fps < b."""
    return int(math.ceil(a * fps - EPS)), int(math.ceil(b * fps - EPS))


def merge_ranges(ranges: Iterable[tuple[float, float]], gap_s: float = 0.0) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for a, b in sorted((float(a), float(b)) for a, b in ranges if b > a):
        if out and a <= out[-1][1] + gap_s:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _cmd(ffmpeg: str, video: Path, start: float, dur: float, fps: float, out_wh: tuple[int, int],
         src_wh: tuple[int, int], hwaccel: str | None, threads: int) -> list[str]:
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin"]
    if hwaccel:
        cmd += ["-hwaccel", hwaccel]
    if threads:
        cmd += ["-threads", str(threads)]
    if start > 0:
        cmd += ["-ss", f"{start:.6f}"]
    cmd += ["-i", str(video), "-t", f"{dur:.6f}", "-an", "-sn", "-dn"]
    vf = f"fps=fps={fps:g}:start_time=0:round=up"
    if out_wh != src_wh:
        vf += f",scale={out_wh[0]}:{out_wh[1]}:flags=area"
    return cmd + ["-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]


def _read_range(cmd: list[str], frame_bytes: int, max_queue: int) -> Iterator[bytes]:
    """Yield raw frames from one ffmpeg process; a reader thread keeps ffmpeg decoding while the caller works."""
    q: queue.Queue[bytes | None] = queue.Queue(maxsize=max(2, max_queue))
    stop = threading.Event()
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err, stdin=subprocess.DEVNULL, bufsize=0)

        def pump() -> None:
            try:
                assert proc.stdout is not None
                while not stop.is_set():
                    buf = bytearray(frame_bytes)
                    view, got = memoryview(buf), 0
                    while got < frame_bytes:  # a raw pipe read returns at most what is buffered
                        n = proc.stdout.readinto(view[got:])
                        if not n:
                            break
                        got += n
                    if got < frame_bytes:
                        break
                    q.put(bytes(buf))
            finally:
                q.put(None)

        t = threading.Thread(target=pump, daemon=True)
        t.start()
        n = 0
        try:
            while (item := q.get()) is not None:
                n += 1
                yield item
        finally:
            stop.set()
            while t.is_alive():  # unblock the pump if the queue is full
                try:
                    q.get_nowait()
                except queue.Empty:
                    t.join(timeout=0.05)
            if proc.poll() is None:
                proc.kill()
            code = proc.wait()
            err.seek(0)
            msg = err.read().decode(errors="replace")[-2000:]
        if code not in (0, -9, 137) and n == 0:
            raise RuntimeError(f"ffmpeg exited {code}: {msg}")


def iter_frames(video: Path, info: VideoInfo, fps: float, ranges: list[tuple[float, float]], *,
                max_height: int | None, hwaccel: str = "auto", threads: int = 0, ffmpeg: str = "ffmpeg",
                max_queue: int = 64, on_event: Any = None) -> Iterator[tuple[int, float, np.ndarray]]:
    """Yield (slot k, t_s = k/fps, RGB uint8 [H, W, 3]) for every slot inside ``ranges`` (media seconds)."""
    out_w, out_h = info.out_size(max_height)
    frame_bytes = out_w * out_h * 3
    hw = choose_hwaccel(hwaccel, ffmpeg)
    for a, b in merge_ranges(ranges):
        b = min(b, info.duration_s)
        k0, k1 = slot_range(max(0.0, a), b, fps)
        if k1 <= k0:
            continue
        start = k0 / fps
        dur = (k1 - k0) / fps
        for attempt in ([hw, None] if hw else [None]):
            cmd = _cmd(ffmpeg, video, start, dur + 0.5 / fps, fps, (out_w, out_h), (info.width, info.height),
                       attempt, threads)
            k = k0
            try:
                for buf in _read_range(cmd, frame_bytes, max_queue):
                    if k >= k1:
                        break
                    yield k, k / fps, np.frombuffer(buf, np.uint8).reshape(out_h, out_w, 3)
                    k += 1
            except RuntimeError as e:
                if attempt and k == k0:  # NVDEC failed before the first frame: retry on the CPU
                    if on_event:
                        on_event("decode.hwaccel_fallback", error=str(e)[-300:])
                    continue
                raise
            if on_event:
                on_event("decode.range", start_s=start, end_s=k1 / fps, frames=k - k0, hwaccel=attempt or "none")
            break


def batched(it: Iterable[Any], n: int) -> Iterator[list[Any]]:
    batch: list[Any] = []
    for x in it:
        batch.append(x)
        if len(batch) >= n:
            yield batch
            batch = []
    if batch:
        yield batch
