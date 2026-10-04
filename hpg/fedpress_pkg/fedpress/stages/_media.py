"""ffmpeg/ffprobe helpers and WAV access shared by the audio, asr, turns, diarize and voice stages."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

import numpy as np


def ffmpeg_bin(name: str = "ffmpeg") -> str:
    """Resolve ffmpeg: the configured name/path, else the imageio-ffmpeg binary (laptop smoke tests)."""
    found = shutil.which(name) or (name if Path(name).is_file() else None)
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    raise FileNotFoundError(f"ffmpeg not found ({name!r}): on HiPerGator `module load ffmpeg` or use the conda env")


def ffprobe_bin(ffmpeg: str) -> str | None:
    sibling = Path(ffmpeg).with_name(Path(ffmpeg).name.replace("ffmpeg", "ffprobe"))
    return str(sibling) if sibling.is_file() and sibling != Path(ffmpeg) else shutil.which("ffprobe")


def run(cmd: list[str], timeout: float = 7200.0) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"{Path(cmd[0]).name} exited {p.returncode}: {p.stderr[-2000:]}")
    return p


def version(ffmpeg: str) -> str:
    return run([ffmpeg, "-hide_banner", "-version"], timeout=60).stdout.splitlines()[0].strip()


def probe(path: Path, ffmpeg: str) -> dict[str, Any]:
    """Container/stream facts: codec, bitrate, sample rate, channels, start time, duration (ffprobe if present,
    otherwise parsed from ``ffmpeg -i``)."""
    fp = ffprobe_bin(ffmpeg)
    if fp:
        out = run([fp, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)], 600)
        data = json.loads(out.stdout)
        res: dict[str, Any] = {"tool": "ffprobe", "format": {
            "name": data.get("format", {}).get("format_name"),
            "duration_s": _f(data.get("format", {}).get("duration")),
            "bit_rate": _i(data.get("format", {}).get("bit_rate"))}}
        for s in data.get("streams", []):
            kind = s.get("codec_type")
            if kind in ("audio", "video") and kind not in res:
                res[kind] = {"codec": s.get("codec_name"), "profile": s.get("profile"),
                             "bit_rate": _i(s.get("bit_rate")),
                             "start_s": _f(s.get("start_time")), "duration_s": _f(s.get("duration"))}
                if kind == "audio":
                    res[kind] |= {"sample_rate": _i(s.get("sample_rate")), "channels": s.get("channels"),
                                  "channel_layout": s.get("channel_layout")}
                else:
                    res[kind] |= {"width": s.get("width"), "height": s.get("height"), "fps": s.get("avg_frame_rate")}
        return res
    p = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path)], capture_output=True, text=True, errors="replace")
    return parse_ffmpeg_info(p.stderr)


def parse_ffmpeg_info(text: str) -> dict[str, Any]:
    res: dict[str, Any] = {"tool": "ffmpeg -i", "format": {}}
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+), start: ([\d.\-]+), bitrate: (\d+) kb/s", text)
    if m:
        res["format"] = {"duration_s": int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]), "start_s": float(m[4]),
                         "bit_rate": int(m[5]) * 1000}
    a = re.search(r"Stream #\S+.*?: Audio: (\w+)[^,]*, (\d+) Hz, ([^,]+), [^,]+(?:, (\d+) kb/s)?", text)
    if a:
        res["audio"] = {"codec": a[1], "sample_rate": int(a[2]), "channel_layout": a[3].strip(),
                        "bit_rate": int(a[4]) * 1000 if a[4] else None}
    v = re.search(r"Stream #\S+.*?: Video: (\w+).*?, (\d{2,5})x(\d{2,5})", text)
    if v:
        res["video"] = {"codec": v[1], "width": int(v[2]), "height": int(v[3])}
    return res


def loudness(path: Path, ffmpeg: str) -> dict[str, Any]:
    """EBU R128 measurement (ffmpeg loudnorm analysis pass). Measures only; nothing is applied."""
    p = run([ffmpeg, "-hide_banner", "-nostats", "-nostdin", "-i", str(path), "-af",
             "loudnorm=print_format=json", "-f", "null", "-"])
    blob = p.stderr[p.stderr.rfind("{"):p.stderr.rfind("}") + 1]
    d = json.loads(blob) if blob else {}
    return {"integrated_lufs": _f(d.get("input_i")), "true_peak_dbtp": _f(d.get("input_tp")),
            "lra_lu": _f(d.get("input_lra")), "threshold_lufs": _f(d.get("input_thresh"))}


def wav_info(path: Path) -> tuple[int, int, int]:
    """(sample_rate, n_frames, channels) of a PCM WAV."""
    with wave.open(str(path), "rb") as w:
        return w.getframerate(), w.getnframes(), w.getnchannels()


def read_wav(path: Path, start_s: float | None = None, end_s: float | None = None) -> tuple[np.ndarray, int]:
    """Mono float32 samples in [-1, 1] (optionally a time slice) and the sample rate."""
    try:
        import soundfile as sf

        info = sf.info(str(path))
        sr = info.samplerate
        a = 0 if start_s is None else max(0, int(round(start_s * sr)))
        b = info.frames if end_s is None else min(info.frames, int(round(end_s * sr)))
        x, _ = sf.read(str(path), start=a, stop=max(a, b), dtype="float32", always_2d=True)
        return x.mean(axis=1).astype(np.float32), sr
    except ImportError:
        pass
    with wave.open(str(path), "rb") as w:
        sr, n, ch, width = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        if width != 2:
            raise ValueError(f"{path}: only 16-bit PCM is supported without soundfile")
        a = 0 if start_s is None else max(0, int(round(start_s * sr)))
        b = n if end_s is None else min(n, int(round(end_s * sr)))
        w.setpos(a)
        raw = np.frombuffer(w.readframes(max(0, b - a)), dtype="<i2").reshape(-1, ch)
    return (raw.astype(np.float32).mean(axis=1) / 32768.0).astype(np.float32), sr


def level_stats(x: np.ndarray) -> dict[str, float]:
    """Whole-file peak/RMS/clipping of the decoded WAV (logged only; never fed back into features)."""
    if x.size == 0:
        return {"peak_dbfs": float("nan"), "rms_dbfs": float("nan"), "clipped_frac": float("nan")}
    peak = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(np.square(x, dtype=np.float64))))
    return {"peak_dbfs": round(_db(peak), 2), "rms_dbfs": round(_db(rms), 2),
            "clipped_frac": float(np.mean(np.abs(x) >= 0.999))}


def _db(v: float) -> float:
    return float(20 * np.log10(v)) if v > 0 else float("-inf")


def slice_audio(x: np.ndarray, sr: int, t0: float, t1: float) -> np.ndarray:
    a, b = max(0, int(round(t0 * sr))), min(len(x), int(round(t1 * sr)))
    return x[a:max(a, b)]


def _f(v: Any) -> float | None:
    try:
        return None if v in (None, "", "N/A") else float(v)
    except (TypeError, ValueError):
        return None


def _i(v: Any) -> int | None:
    f = _f(v)
    return None if f is None else int(f)
