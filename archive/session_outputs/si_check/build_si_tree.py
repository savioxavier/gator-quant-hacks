"""Source-invariance tree (prereg 3.7): for 20190130, 20190320, 20190619 re-encode the meeting's source audio stream
(raw/video.mp4, AAC 48 kHz stereo ~127 kbps) at 64 kbps AAC, decode it with the package's own audio command
(aresample=16000:async=1:first_pts=0, mono, pcm_s16le) into <SI>/meetings/<id>/audio/audio_16k.wav, and copy the
original turns and diarize outputs and done markers unchanged. The original tree <fedpress-root>/meetings is read only.
No feature value is read here; only audio samples are compared (length, lag, SNR) to check the media clock."""
from __future__ import annotations

import hashlib
import json
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ORIG = Path(r"<fedpress-root>\meetings")
SI = Path(r"<fedpress-root>_si\meetings")
FF = Path(__file__).resolve().parent.parent / "localfeat" / "bin" / "ffmpeg.exe"   # imageio-ffmpeg 7.1 copy
MEETINGS = ("20190130", "20190320", "20190619")
BITRATE = "64k"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        while b := fh.read(1 << 22):
            h.update(b)
    return h.hexdigest()


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed rc={r.returncode}: {r.stderr[-2000:]}")
    return r.stderr


def read_wav(p: Path) -> tuple[np.ndarray, int]:
    import wave

    with wave.open(str(p), "rb") as w:
        assert w.getsampwidth() == 2 and w.getnchannels() == 1, (w.getsampwidth(), w.getnchannels())
        sr, n = w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float32) / 32768.0
    return x, sr


def lag_at(a: np.ndarray, b: np.ndarray, start: int, win: int, maxlag: int) -> tuple[int, float]:
    """Lag (samples) of b relative to a around ``start`` by FFT cross-correlation; positive = b is late."""
    seg_a = a[start:start + win]
    seg_b = b[max(0, start - maxlag):start + win + maxlag]
    n = 1 << int(np.ceil(np.log2(len(seg_a) + len(seg_b))))
    c = np.fft.irfft(np.fft.rfft(seg_b, n) * np.conj(np.fft.rfft(seg_a, n)), n)
    k = int(np.argmax(c[:len(seg_b) - len(seg_a) + 1]))
    lag = k - (start - max(0, start - maxlag))
    peak = float(c[k] / (np.linalg.norm(seg_a) * np.linalg.norm(seg_b[k:k + len(seg_a)]) + 1e-12))
    return lag, peak


def copy_stage(pid: str, stage: str) -> list[dict]:
    src, dst = ORIG / pid, SI / pid
    done = json.loads((src / "_done" / f"{stage}.json").read_text(encoding="utf-8"))
    assert done.get("status") == "ok" and not (done.get("notes") or {}).get("max_seconds"), (pid, stage)
    rows = []
    for rel in done["outputs"]:
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, dst / rel)
        a, b = sha(src / rel), sha(dst / rel)
        assert a == b, (pid, rel)
        rows.append({"path": rel, "sha256": a})
    (dst / "_done").mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "_done" / f"{stage}.json", dst / "_done" / f"{stage}.json")
    rows.append({"path": f"_done/{stage}.json", "sha256": sha(dst / "_done" / f"{stage}.json")})
    return rows


def build(pid: str) -> dict:
    t0 = time.perf_counter()
    src, dst = ORIG / pid, SI / pid
    for d in ("audio", "turns", "diarize", "_done", "si"):
        (dst / d).mkdir(parents=True, exist_ok=True)
    copied = copy_stage(pid, "turns") + copy_stage(pid, "diarize")

    video = src / "raw" / "video.mp4"
    m4a = dst / "si" / "audio_aac64k.m4a"
    tmp_m4a = m4a.with_name(f".{m4a.stem}.tmp.m4a")
    enc_cmd = [str(FF), "-hide_banner", "-nostdin", "-nostats", "-y", "-i", str(video), "-map", "0:a:0", "-vn", "-sn",
               "-dn", "-c:a", "aac", "-b:a", BITRATE, "-f", "mp4", str(tmp_m4a)]
    run(enc_cmd)
    tmp_m4a.replace(m4a)
    pr = subprocess.run([str(FF), "-hide_banner", "-nostdin", "-i", str(m4a)], capture_output=True, text=True,
                        errors="replace").stderr
    probe = [l.strip() for l in pr.splitlines() if "Stream #" in l or "Duration:" in l]

    wav = dst / "audio" / "audio_16k.wav"
    tmp_wav = wav.with_name(f".{wav.stem}.tmp.wav")
    filt = "aresample=16000:async=1:first_pts=0"           # the package audio stage's filter, unchanged
    dec_cmd = [str(FF), "-hide_banner", "-nostdin", "-nostats", "-y", "-i", str(m4a), "-map", "0:a:0", "-vn", "-sn",
               "-dn", "-af", filt, "-ac", "1", "-c:a", "pcm_s16le", "-f", "wav", str(tmp_wav)]
    run(dec_cmd)
    tmp_wav.replace(wav)

    # media-clock check against the original package WAV (audio samples only)
    xo, sro = read_wav(src / "audio" / "audio_16k.wav")
    xs, srs = read_wav(wav)
    assert sro == srs == 16000
    n = min(len(xo), len(xs))
    win, maxlag = 30 * sro, int(0.25 * sro)
    lags = []
    for frac in (0.1, 0.3, 0.5, 0.7, 0.9):
        st = int(frac * (n - win - maxlag))
        st = max(st, maxlag)
        lag, peak = lag_at(xo, xs, st, win, maxlag)
        lags.append({"at_s": round(st / sro, 1), "lag_samples": lag, "norm_xcorr_peak": round(peak, 5)})
    err = xs[:n] - xo[:n]
    snr_db = float(10 * np.log10(np.sum(xo[:n] ** 2) / max(np.sum(err ** 2), 1e-20)))
    meta_orig = json.loads((src / "audio" / "audio.json").read_text(encoding="utf-8"))
    out = {
        "what": "source-invariance re-encode (preregistration presser_H2H3H4_EXPLORATORY.md 3.7): 64 kbps AAC",
        "source": "raw/video.mp4 of the original tree (audio stream 0:a:0)",
        "source_path": str(video), "source_sha256": sha(video),
        "source_audio": (meta_orig.get("input") or {}).get("audio"),
        "reencode": {"cmd": ["ffmpeg", *enc_cmd[1:]],"codec": "aac (FFmpeg native, AAC-LC)", "bitrate": BITRATE,
                     "sample_rate_channels": "unchanged from source", "file": "si/audio_aac64k.m4a",
                     "sha256": sha(m4a), "bytes": m4a.stat().st_size, "probe": probe},
        "decode": {"cmd": ["ffmpeg", *dec_cmd[1:]],"filter": filt, "note": "identical to the package audio stage command"},
        "ffmpeg": subprocess.run([str(FF), "-version"], capture_output=True, text=True).stdout.splitlines()[0],
        "output": {"path": "audio/audio_16k.wav", "sample_rate": srs, "channels": 1, "codec": "pcm_s16le",
                   "frames": int(len(xs)), "duration_s": round(len(xs) / srs, 3), "bytes": wav.stat().st_size,
                   "sha256": sha(wav)},
        "original_wav": {"path": str(src / "audio" / "audio_16k.wav"), "frames": int(len(xo)),
                         "sha256": sha(src / "audio" / "audio_16k.wav")},
        "clock_check": {"frames_diff_si_minus_orig": int(len(xs) - len(xo)), "lags": lags,
                        "snr_db_vs_original_wav": round(snr_db, 2)},
        "manifest_duration_s": meta_orig.get("manifest_duration_s"),
        "created_utc": utc(), "host": socket.gethostname(),
    }
    (dst / "audio" / "audio.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    marker = {"stage": "audio", "presser_id": pid, "status": "ok",
              "outputs": ["audio/audio_16k.wav", "audio/audio.json"],
              "outputs_detail": [{"path": "audio/audio_16k.wav", "bytes": wav.stat().st_size, "sha256": sha(wav)},
                                 {"path": "audio/audio.json", "sha256": sha(dst / "audio" / "audio.json")}],
              "notes": {"source_invariance_reencode": True, "bitrate": BITRATE,
                        "duration_s": round(len(xs) / srs, 3),
                        "derived_by": "si_check/build_si_tree.py (not the package audio stage; same decode command)"},
              "finished_utc": utc(), "host": socket.gethostname()}
    (dst / "_done" / "audio.json").write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
    prov = {"presser_id": pid, "copied_unchanged": copied, "audio": out["clock_check"],
            "elapsed_s": round(time.perf_counter() - t0, 1)}
    (dst / "si" / "si_provenance.json").write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8")
    return prov


if __name__ == "__main__":
    SI.mkdir(parents=True, exist_ok=True)
    ids = sys.argv[1:] or list(MEETINGS)
    for pid in ids:
        assert pid in MEETINGS
        print(json.dumps(build(pid), indent=1), flush=True)
