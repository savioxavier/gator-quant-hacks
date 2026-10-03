"""audio (CPU): raw/video.mp4 -> audio/audio_16k.wav (16 kHz mono PCM) + audio/audio.json.

* Media time is preserved: ``aresample=async=1:first_pts=0`` pads any audio start offset with silence, so WAV
  sample 0 is video time 0 and every downstream time is the same media clock as the frames.
* Loudness (EBU R128 integrated/true peak/LRA) and whole-file peak/RMS/clipping are measured and logged only.
  ``audio.loudnorm: true`` applies a single linear gain from those whole-file statistics; it is recorded as
  ``causal: false`` because the gain depends on audio after each chunk (keep it off for features).
* The input audio codec, bitrate, sample rate and channels are recorded (streamed AAC quality varies by year).
* The WAV duration must match the manifest duration within ``audio.max_duration_gap_s``.
"""

from __future__ import annotations

import os
import time
from typing import Any

from .. import io
from ..stage import StageContext, StageResult, StageSpec
from . import _media

SPEC = StageSpec(name="audio", requires=("fetch",), resource="cpu", outputs=("audio_wav", "audio_meta"),
                 config_keys=(), stamped=False)


def run(ctx: StageContext) -> StageResult:
    s, m = ctx.scfg, ctx.meeting
    src = ctx.out("video")
    if not src.exists():
        raise FileNotFoundError(f"{src} missing: run fetch with fetch.video=true")
    ff = _media.ffmpeg_bin(str(s.get("ffmpeg", "ffmpeg")))
    sr, ch = int(s.get("sample_rate", 16000)), int(s.get("channels", 1))
    t0 = time.perf_counter()
    probe = _media.probe(src, ff)
    if "audio" not in probe:
        raise ValueError(f"{src}: no audio stream ({probe.get('tool')})")
    dest = ctx.out("audio_wav")
    tmp = dest.with_name(f".{dest.stem}.{os.getpid()}.tmp.wav")
    filt = f"aresample={sr}:async=1:first_pts=0"
    norm: dict[str, Any] = {"applied": False}
    if s.get("loudnorm", False):
        meas = _media.loudness(src, ff)
        tgt = dict(s.get("loudnorm_target") or {"i": -23.0, "tp": -2.0, "lra": 7.0})
        filt = (f"loudnorm=I={tgt['i']}:TP={tgt['tp']}:LRA={tgt['lra']}:measured_I={meas['integrated_lufs']}:"
                f"measured_TP={meas['true_peak_dbtp']}:measured_LRA={meas['lra_lu']}:"
                f"measured_thresh={meas['threshold_lufs']}:linear=true," + filt)
        norm = {"applied": True, "causal": False, "target": tgt, "measured": meas}
        ctx.log.warning("audio.loudnorm_applied", hint="whole-file gain: not causal; keep audio.loudnorm=false")
    cmd = [ff, "-hide_banner", "-nostdin", "-nostats", "-y", "-i", str(src), "-map", "0:a:0", "-vn", "-sn", "-dn",
           "-af", filt, "-ac", str(ch), "-c:a", str(s.get("codec", "pcm_s16le")), "-f", "wav", str(tmp)]
    try:
        _media.run(cmd)
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)
    rate, frames, chans = _media.wav_info(dest)
    dur = frames / rate
    x, _ = _media.read_wav(dest)
    levels = _media.level_stats(x)
    del x
    loud = _media.loudness(dest, ff) if s.get("analyze_loudness", True) else {}
    expect = m.duration_s or (probe.get("format") or {}).get("duration_s")
    gap = None if expect is None else round(dur - float(expect), 3)
    max_gap = float(s.get("max_duration_gap_s", 5.0))
    meta = {"source": io.FILES["video"], "input": probe, "ffmpeg": _media.version(ff), "filter": filt,
            "output": {"path": io.FILES["audio_wav"], "sample_rate": rate, "channels": chans,
                       "codec": s.get("codec", "pcm_s16le"), "frames": frames, "duration_s": round(dur, 3),
                       "bytes": dest.stat().st_size},
            "manifest_duration_s": m.duration_s, "duration_gap_s": gap, "levels": levels,
            "loudness": {**loud, "measured_on": "output wav", "applied": False}, "normalisation": norm,
            "elapsed_s": round(time.perf_counter() - t0, 2), "created_utc": io.utc_now()}
    ctx.add_output(dest)
    ctx.add_output(io.atomic_write_json(ctx.out("audio_meta"), meta))
    if gap is not None and abs(gap) > max_gap:
        raise ValueError(f"WAV is {dur:.1f} s but the manifest says {expect:.1f} s (gap {gap:+.1f} s > "
                         f"audio.max_duration_gap_s={max_gap:g}): truncated or wrong download?")
    a = probe.get("audio", {})
    ctx.result.notes.update({"input_codec": a.get("codec"), "input_bitrate": a.get("bit_rate"),
                             "input_sample_rate": a.get("sample_rate"), "duration_s": round(dur, 3),
                             "duration_gap_s": gap, "integrated_lufs": loud.get("integrated_lufs"), **levels})
    ctx.log.info("audio.done", duration_s=round(dur, 1), codec=a.get("codec"), bitrate=a.get("bit_rate"),
                 lufs=loud.get("integrated_lufs"))
    return ctx.result
