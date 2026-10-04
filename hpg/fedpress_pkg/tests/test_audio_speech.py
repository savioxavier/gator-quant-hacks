"""Self-checks for fetch, audio, turns, diarize and voice on tiny synthetic inputs (no GPU, no model download,
no network: the download test uses a local HTTP server). The ECAPA and audeering models are replaced by small
stand-ins; prosody uses parselmouth when installed, the audio stage uses ffmpeg (or imageio-ffmpeg) when found."""

from __future__ import annotations

import http.server
import json
import math
import threading
import types
import wave
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fedpress import io
from fedpress import manifest as mf
from fedpress.config import load
from fedpress.stage import run_one
from fedpress.stages import _align, _chunks, _http, _transcript, _vtt, diarize, voice

SR = 16000
CHAIR_HZ, OTHER_HZ = 120.0, 220.0


@pytest.fixture()
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("FEDPRESS_ROOT", str(tmp_path / "root"))
    monkeypatch.delenv("FEDPRESS_CONFIG", raising=False)
    monkeypatch.delenv("FEDPRESS_SEED", raising=False)
    return tmp_path / "root"


# ------------------------------------------------------------------ parsers and alignment
def test_vtt_parse_and_timed_words():
    text = ("WEBVTT\r\nX-TIMESTAMP-MAP=LOCAL:00:00:00.000,MPEGTS:0\r\n\r\n00:04.000 --> 00:06.000 align:middle\r\n"
            "CHAIR POWELL.\r\n\r\n1\r\n01:00:01.500 --> 01:00:03.500\r\n<v Chair>Good afternoon.</v>\r\n")
    cues, header = _vtt.parse(text)
    assert header["X-TIMESTAMP-MAP"].endswith("MPEGTS:0")
    assert [(c.start, c.end) for c in cues] == [(4.0, 6.0), (3601.5, 3603.5)]
    assert cues[1].text == "Good afternoon."
    words = _vtt.timed_words(cues)
    assert [w for w, _, _ in words] == ["CHAIR", "POWELL.", "Good", "afternoon."]
    assert words[2][1] == 3601.5 and math.isclose(words[3][2], 3603.5)


def test_transcript_roles_and_kinds():
    text = ("Transcript of Chair Powell\u2019s Press Conference\nJune 15, 2022\nCHAIRIMAN POWELL. Good afternoon. "
            "We raised rates.\nMICHELE SMITH. Howard.\nHOWARD SCHNEIDER. Thank you [inaudible]. Why now?\n"
            "CHAIR POWELL. Because inflation is too high--well above 2 percent.\nQUESTION. A follow-up?\n"
            "CHAIR POWELL. Yes.\nMICHELLE SMITH. Thank you.\nCHAIR POWELL. Thank you.")
    turns = _transcript.classify(_transcript.split_turns(text), "Powell",
                                 r"^(CHAIR|CHAIRMAN|CHAIRWOMAN) (BERNANKE|YELLEN|POWELL|WARSH)$",
                                 r"^(MICHELLE SMITH|MS\. SMITH)$")
    kinds = [(t.speaker, t.role, t.segment_kind, t.qa_idx) for t in turns]
    assert kinds == [("CHAIRIMAN POWELL", "chair", "opening", -1), ("MICHELE SMITH", "moderator", "moderator", -1),
                     ("HOWARD SCHNEIDER", "reporter", "question", 0), ("CHAIR POWELL", "chair", "answer", 0),
                     ("QUESTION", "reporter", "question", 1), ("CHAIR POWELL", "chair", "answer", 1),
                     ("MICHELLE SMITH", "moderator", "moderator", -1), ("CHAIR POWELL", "chair", "closing", -1)]
    assert "inaudible" not in " ".join(turns[2].words) and turns[3].words[-4:] == ["well", "above", "2", "percent."]


def test_align_fill_and_wer():
    ref = "Good afternoon. Today the Committee raised rates by 75 basis points.".split()
    hyp_words = ["good", "afternoon", "um", "today", "the", "committee", "raised", "rate", "by", "75", "basis"]
    hyp = [_align.Timed(w, 10.0 + i, 10.6 + i, 0.9) for i, w in enumerate(hyp_words)]
    al = _align.align(ref, hyp)
    assert al.matched[:2].all() and al.start[0] == 10.0
    assert al.timed_by[6] == "sub" and al.start[6] == 17.0          # "rates" took "rate"
    assert al.timed_by[-1] == "interp" and al.start[-1] >= al.end[-2]  # "points." extrapolated after "basis"
    assert np.all(np.diff(al.start) >= 0)
    assert al.stats["ins"] == 1 and al.stats["dels"] == 1 and al.stats["subs"] == 1
    assert _align.compare(al, al)["median_abs_s"] == 0.0
    assert _align.norm_tokens("29,000\xbd%") == ["29000", "1/2", "percent"]


def test_chunk_windows_and_coverage():
    assert _chunks.windows(0, 10, 4, 4, 3) == [(0, 4), (4, 8)]
    assert _chunks.windows(0, 10, 4, 4, 3, merge_tail=True) == [(0, 4), (4, 10)]
    w = _chunks.word_windows(np.array([0.0, 1.0, 2.0, 5.0, 6.0]), np.array([0.8, 1.8, 2.8, 5.8, 6.8]),
                             target=8, min_len=1.5, max_len=15, pause_s=1.0)
    assert w == [(0.0, 2.8), (5.0, 6.8)]  # cut at the 2.2 s pause
    cov = _chunks.coverage(np.array([[0.0, 10.0], [10.0, 20.0]]), np.array([[0.0, 5.0], [4.0, 10.0], [15.0, 17.5]]))
    assert np.allclose(cov, [1.0, 0.25])


def test_pick_mp4_rule():
    src = [{"container": "MP4", "src": "https://x/a.mp4", "width": 1280, "height": 720, "avg_bitrate": 2},
           {"container": "MP4", "src": "https://x/b.mp4", "width": 960, "height": 540, "avg_bitrate": 1},
           {"container": "MP4", "src": "https://x/c.mp4", "width": 960, "height": 540, "avg_bitrate": 3},
           {"container": "MP4", "src": "http://x/d.mp4", "width": 960, "height": 540, "avg_bitrate": 9},
           {"type": "application/x-mpegURL", "src": "https://x/m.m3u8"}]
    best, rule = _http.pick_mp4(src)
    assert best["src"] == "https://x/c.mp4" and rule == "max_within_960x540"
    assert _http.pick_mp4(src[:1])[1] == "above_cap_highest"
    assert _http.pick_mp4(src, "highest")[0]["src"] == "https://x/a.mp4"
    tracks = {"text_tracks": [{"kind": "captions", "sources": [{"src": "http://v"}, {"src": "https://v"}]}]}
    assert _http.caption_src(tracks) == "https://v"


# ------------------------------------------------------------------ resumable download
class _RangeHandler(http.server.BaseHTTPRequestHandler):
    data = bytes(range(256)) * 4000      # 1,024,000 bytes
    calls: list[str] = []

    def log_message(self, *args):        # keep pytest output quiet
        pass

    def do_GET(self):
        rng = self.headers.get("Range")
        self.calls.append(rng or "")
        start = int(rng.split("=")[1].split("-")[0]) if rng else 0
        body = self.data[start:]
        self.send_response(206 if rng else 200)
        self.send_header("Content-Length", str(len(body)))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{len(self.data) - 1}/{len(self.data)}")
        self.end_headers()
        if len(self.calls) == 1:          # first response breaks off half way
            self.wfile.write(body[: len(body) // 2])
            self.wfile.flush()
            self.close_connection = True
            return
        self.wfile.write(body)


def test_download_resumes_after_broken_connection(tmp_path):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _RangeHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}/video.mp4"
        client = _http.Http(timeout_s=10, retries=3, backoff_s=0.0, chunk_bytes=1 << 16)
        info = client.download(lambda a: url, tmp_path / "v.mp4", expected_bytes=len(_RangeHandler.data))
    finally:
        srv.shutdown()
    assert (tmp_path / "v.mp4").read_bytes() == _RangeHandler.data
    assert info["bytes"] == len(_RangeHandler.data) and not info["partial"]
    assert _RangeHandler.calls[0] == "" and int(_RangeHandler.calls[1][6:].rstrip("-")) > 0  # resumed, not restarted
    assert not (tmp_path / "v.mp4.part").exists()


# ------------------------------------------------------------------ synthetic meeting: turns -> diarize -> voice
OPENING = "Good afternoon. " + " ".join(f"opening{i}" for i in range(138))
QUESTION = "Thank you. Why did the Committee move now and by how much?"
ANSWER = " ".join(f"answer{i}" for i in range(68))
SCRIPT = [  # (label, text, start, end) in media seconds; the title cue is not speech
    (None, "Transcript of Chair Powell's Press Conference June 15, 2022", 0.0, 4.0),
    ("CHAIR POWELL.", OPENING, 6.0, 76.0),
    ("MICHELLE SMITH.", "Thank you. Howard.", 77.0, 80.0),
    ("HOWARD SCHNEIDER.", QUESTION, 81.0, 95.0),
    ("CHAIR POWELL.", ANSWER, 96.0, 130.0),
    ("MICHELLE SMITH.", "Thank you very much.", 131.0, 133.0),
    ("CHAIR POWELL.", "Thank you.", 134.0, 135.0),
]


def _write_inputs(paths: io.MeetingPaths) -> None:
    paths.ensure()
    cues, lines = [], []
    for label, text, a, b in SCRIPT:
        if label:
            cues.append((a - 1.0, a - 0.2, label))
            lines.append(f"{label} {text}")
        words = text.split()
        step = (b - a) / len(words)
        for k in range(0, len(words), 6):  # cues of six words, like the Fed captions
            cues.append((a + k * step, a + min(len(words), k + 6) * step, " ".join(words[k:k + 6])))
    vtt = "WEBVTT\n\n" + "\n\n".join(f"{_ts(a)} --> {_ts(b)}\n{t}" for a, b, t in cues) + "\n"
    paths.file("captions_vtt").write_text(vtt, encoding="utf-8")
    paths.file("transcript_pdf").write_text("\n".join(lines), encoding="utf-8")  # read through the patched pdf_text
    t = np.arange(int(136 * SR)) / SR
    x = 0.01 * np.random.default_rng(0).standard_normal(len(t))
    for label, _, a, b in SCRIPT:
        if label:
            hz = CHAIR_HZ if label.startswith("CHAIR") else OTHER_HZ
            m = (t >= a) & (t < b)
            x[m] += 0.3 * np.sin(2 * np.pi * hz * t[m]) + 0.15 * np.sin(4 * np.pi * hz * t[m])
    with wave.open(str(paths.file("audio_wav")), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    for stage in ("fetch", "audio"):
        io.mark_done(paths, stage, {"status": "ok", "outputs": []})


def _ts(s: float) -> str:
    return f"{int(s // 60):02d}:{s % 60:06.3f}"


class _FakeEcapa:
    """Stand-in speaker embedding: the angle of the dominant frequency (chair 120 Hz vs others 220 Hz)."""

    def __init__(self, *args, **kwargs):
        pass

    def embed(self, clips, batch_size=64):
        out = []
        for c in clips:
            f = np.fft.rfftfreq(len(c), 1 / SR)[np.argmax(np.abs(np.fft.rfft(c))[1:]) + 1]
            out.append([math.cos(f / 100), math.sin(f / 100)])
        return diarize._unit(np.asarray(out))


def _fake_adv(cfg, key, clips, sr, dev, batch, dtype="float32"):
    return pd.DataFrame({c: [0.5] * len(clips) for c in voice.ADV_DEFAULT}), np.zeros((len(clips), 4))


def test_turns_diarize_voice_synthetic(root, monkeypatch):
    pytest.importorskip("parselmouth")
    monkeypatch.setattr(_transcript, "pdf_text", lambda path: Path(path).read_text(encoding="utf-8"))
    monkeypatch.setattr(diarize, "Ecapa", _FakeEcapa)
    monkeypatch.setattr(voice, "audeering_adv", _fake_adv)
    cfg = load(overrides=["turns.clock_source=vtt", "asr.enabled=false", "diarize.ecapa.min_enroll_s=30"])
    m = mf.select(cfg, presser_id="20220615")[0]
    paths = io.MeetingPaths.of(cfg, m.presser_id)
    _write_inputs(paths)

    assert run_one(cfg, "turns", m, run_id="t") == "done"
    turns = io.read_parquet(paths.file("turns"))
    assert list(turns["segment_kind"]) == ["opening", "moderator", "question", "answer", "moderator", "closing"]
    anchor = json.loads(paths.file("anchor").read_text())
    assert abs(anchor["media_s"] - 6.0) < 0.01 and anchor["wall_utc"].startswith("2022-06-15T18:30:00")
    ans = turns[turns["segment_kind"] == "answer"].iloc[0]
    assert abs(ans["t_end_s"] - 130.0) < 0.05
    expect = pd.Timestamp("2022-06-15T18:30:00Z") + pd.to_timedelta(ans["t_end_s"] - 6.0 + 30.0, unit="s")
    assert abs((ans["known_at"] - expect).total_seconds()) < 1e-3
    notes = io.read_done(paths, "turns")["notes"]
    assert notes["timing_ok"] and notes["match_frac"] > 0.99

    assert run_one(cfg, "diarize", m, run_id="t") == "done"
    cc = io.read_parquet(paths.file("chair_check"))
    assert cc["t_start_s"].min() >= 76.0 - 1e-6                      # nothing scored before enrolment ends
    assert cc.loc[cc["role"] == "chair", "chair_verified"].all()
    assert not cc.loc[cc["role"] != "chair", "chair_verified"].any() and cc["agree"].all()
    assert (cc["known_at"] > pd.Timestamp("2022-06-15T18:31:10Z")).all()

    assert run_one(cfg, "voice", m, run_id="t") == "done"
    vc = io.read_parquet(paths.file("voice_chunks"))
    assert list(vc["t_start_s"].round(2)) == [96.0, 104.0, 112.0, 120.0]  # 2 s tail < min_chunk_s dropped
    assert vc["identity_ok"].all() and (vc["dur_s"] == 8.0).all()
    assert np.allclose(vc["f0_median_st"], 12 * math.log2(CHAIR_HZ / 100.0), atol=0.3)
    assert (vc["speech_rate_wps"].between(1.5, 2.5)).all()
    assert (vc["known_at"] == vc["t_end_utc"] + pd.Timedelta(seconds=30)).all()

    warsh = types.SimpleNamespace(scfg=cfg.section("voice"), meeting=mf.select(cfg, presser_id="20260916")[0])
    assert "Warsh" in voice.applies(warsh)


def test_diarize_enrolment_calibration():
    rng = np.random.default_rng(1)
    chair = diarize._unit(np.array([1.0, 0.0, 0.0]) + 0.05 * rng.standard_normal((40, 3)))
    noisy = diarize._unit(np.array([[0.0, 1.0, 0.0]] * 3))  # applause windows inside the opening
    centroid, loo = diarize.enroll(np.vstack([chair, noisy]), outlier_mad=4.0)
    assert len(loo) == 40 and centroid[0] > 0.99
    thr = diarize.calibrate(loo, 0.02, 0.10, 0.30)
    assert 0.80 < thr < 1.0


def test_word_timing_rates():
    w = pd.DataFrame({"t_start_s": [0.0, 0.5, 1.0, 3.0, 3.5], "t_end_s": [0.4, 0.9, 1.4, 3.4, 3.9],
                      "matched": [True] * 5})
    out = voice.word_timing(w, 0.0, 4.0, pause_min=0.25)
    assert out["n_words"] == 5 and out["speech_rate_wps"] == 1.25 and out["n_pauses"] == 1
    assert math.isclose(out["pause_frac"], 1.6 / 4.0) and math.isclose(out["articulation_rate_wps"], 5 / 2.4)


def test_audio_stage_synthetic(root):
    from fedpress.stages import _media

    try:
        ff = _media.ffmpeg_bin("ffmpeg")
    except FileNotFoundError:
        pytest.skip("no ffmpeg")
    cfg = load(overrides=["audio.max_duration_gap_s=100000"])
    m = mf.select(cfg, presser_id="20220615")[0]
    paths = io.MeetingPaths.of(cfg, m.presser_id).ensure()
    src = paths.dir / "raw" / "tone.wav"
    t = np.arange(3 * 44100) / 44100
    with wave.open(str(src), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        tone = (0.2 * np.sin(2 * np.pi * 440 * t) * 32767).astype("<i2")
        w.writeframes(np.repeat(tone, 2).tobytes())
    _media.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-c:a", "aac", "-b:a", "96k",
                str(paths.file("video"))])
    io.mark_done(paths, "fetch", {"status": "ok", "outputs": []})
    assert run_one(cfg, "audio", m, run_id="t") == "done"
    rate, frames, ch = _media.wav_info(paths.file("audio_wav"))
    assert (rate, ch) == (16000, 1) and abs(frames / rate - 3.0) < 0.1
    meta = io.read_json(paths.file("audio_meta"))
    assert meta["input"]["audio"]["codec"] == "aac" and meta["loudness"]["applied"] is False
    assert meta["loudness"]["integrated_lufs"] is not None


def test_forced_refine_maps_aligner_words(monkeypatch):
    from fedpress.stages import _forced

    words = "Good afternoon everyone today we decided to raise rates".split()
    owner = np.array([0, 0, 0, 1, 1, 1, 1, 1, 1])
    base = _align.align(words, [_align.Timed(w, float(i), i + 0.8) for i, w in enumerate(words)])
    segs = _forced.segments(owner, base, max_seg_s=3.5, pad_s=0.5, total_s=20.0)
    assert [(lo, hi) for lo, hi, _, _ in segs] == [(0, 3), (3, 6), (6, 9)]  # split by turn, then at 3.5 s
    shifted = [_align.Timed(w.lower(), i + 0.25, i + 0.9) for i, w in enumerate(words) if w != "rates"]
    monkeypatch.setattr(_forced, "_whisperx", lambda *a, **k: shifted)
    monkeypatch.setattr(_forced.gpu, "preload_cuda_libs", lambda: None)
    cfg = load()
    audio = np.zeros(20 * SR, np.float32)
    out, notes = _forced.refine("whisperx", cfg, {"device": "cpu"}, audio, SR, words, owner, base)
    assert list(out.timed_by[:8]) == ["forced"] * 8 and out.timed_by[8] == "match"  # "rates" keeps the base time
    assert np.allclose(out.start[:8], np.arange(8) + 0.25) and out.start[8] == 8.0
    assert notes["refined_frac"] == round(8 / 9, 4)
