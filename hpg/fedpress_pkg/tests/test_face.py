"""frames/face stage tests: slot clock, identity enrolment, causal per-frame logic, aggregation, and one full
stage run with stub models. Needs numpy/pandas/pyarrow; the decode test needs ffmpeg, the full run needs cv2."""

from __future__ import annotations

import math
import subprocess
import zipfile

import numpy as np
import pandas as pd
import pytest

from fedpress import io
from fedpress import manifest as mf
from fedpress.clock import make_anchor, save_anchor, stamp
from fedpress.config import load
from fedpress.stage import run_one
from fedpress.stages import _face_models as fm
from fedpress.stages import _video, face

S = {"identity": {"enroll_min_frames": 3, "enroll_min_cos": 0.5},
     "gates": {"min_face_h_px": 80, "max_abs_yaw_deg": 40, "max_abs_pitch_deg": 30, "min_blur": 0, "min_det_score": 0},
     "masks": {"jaw_open": 0.025, "reading_pitch_deg": -10, "eyes_closed": 0.5}, "track": {"iou_min": 0.3, "max_gap_s": 3},
     "aggregate": {"windows_s": [30], "min_gated_frames": 2, "mouth_closed_columns": ["ex_valence"]},
     "upper_face_only": True, "blink_min_fps": 10}


@pytest.fixture()
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("FEDPRESS_ROOT", str(tmp_path / "root"))
    monkeypatch.delenv("FEDPRESS_CONFIG", raising=False)
    return load(overrides=["text.primary=fomc_roberta"])


def test_slot_grid():
    assert _video.slot_range(0.0, 3.0, 1.0) == (0, 3)
    assert _video.slot_range(17.5, 94.7, 5.0) == (88, 474)      # first slot >= start, last slot < end
    assert _video.merge_ranges([(5, 6), (0, 2), (1.5, 3)]) == [(0, 3), (5, 6)]


def _ffmpeg() -> str:
    try:
        return _video.resolve_ffmpeg("ffmpeg")
    except FileNotFoundError:
        pytest.skip("no ffmpeg")


def test_decoded_slot_never_shows_later_content(tmp_path):
    """Frame n of a 30 fps clip has luma n; slot k (t = k s) must show frame 30k, never a later one."""
    ff = _ffmpeg()
    clip = tmp_path / "count.mkv"
    subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "nullsrc=s=32x32:r=30:d=6,format=gray,geq=lum='N'", "-c:v", "ffv1", "-pix_fmt", "gray",
                    str(clip)], check=True)
    info = _video.probe(clip, ff)
    got = {k: int(img[..., 0].mean().round()) for k, _, img in
           _video.iter_frames(clip, info, 1.0, [(0.0, 2.0), (2.2, 6.0)], max_height=None, hwaccel="none", ffmpeg=ff)}
    assert sorted(got) == [0, 1, 3, 4, 5]
    assert all(v == 30 * k for k, v in got.items()), got


def test_umeyama_and_pose():
    a = math.radians(20)
    m = np.array([[1.5 * math.cos(a), -1.5 * math.sin(a), 4.0], [1.5 * math.sin(a), 1.5 * math.cos(a), -2.0]])
    src = fm.ARC_TEMPLATE / 2
    dst = src @ m[:, :2].T + m[:, 2]
    assert np.allclose(fm.umeyama(src, dst), m, atol=1e-9)
    assert np.allclose(fm.pose_from_matrix(np.eye(4)), 0)
    t = math.radians(15)  # rotation about x by +15 deg tips the head's top toward the camera: looking down
    rx = np.eye(4)
    rx[1:3, 1:3] = [[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]]
    pitch, yaw, roll = fm.pose_from_matrix(rx)
    assert pitch == pytest.approx(-15) and yaw == pytest.approx(0) and roll == pytest.approx(0)


def _cand(emb=None, box=(100, 50, 220, 210)):
    e = None if emb is None else np.asarray(emb, np.float32) / np.linalg.norm(emb)
    return fm.Cand(box=np.array(box, np.float32), emb=e)


def test_enrolment_robust_and_scores():
    rng = np.random.default_rng(0)
    chair = rng.normal(size=128)
    en = face.Enrolment("sface", S)
    for i in range(20):  # opening: the chair, plus two cutaway frames whose largest face is someone else
        e = chair + 0.2 * rng.normal(size=128) if i not in (3, 11) else rng.normal(size=128)
        en.add(960, 540, [_cand(e)])
    out = en.finish()
    assert out["ok"] and out["kept"] == 18 and en.threshold == pytest.approx(0.363)
    assert en.score(_cand(chair + 0.2 * rng.normal(size=128)), 960, 540) > 0.8
    assert en.score(_cand(rng.normal(size=128)), 960, 540) < 0.363
    geo = face.Enrolment("geometry", S)
    for _ in range(5):
        geo.add(960, 540, [_cand(box=(430, 120, 560, 280)), _cand(box=(10, 10, 40, 40))])  # largest face enrols
    geo.finish()
    assert geo.score(_cand(box=(432, 122, 562, 282)), 960, 540) > 0.9
    assert geo.score(_cand(box=(650, 150, 760, 260)), 960, 540) < 0.25
    none = face.Enrolment("sface", S)
    none.finish()
    assert not none.ok and none.score(_cand(chair), 960, 540) == 0.0


def _frames_df(n=12, fps=1.0):
    rows = []
    for k in range(n):
        cut = k in (5, 6)  # camera on a reporter
        rows.append({"frame_idx": k, "t_s": k / fps, "frame_w": 960, "frame_h": 540, "n_faces": 1, "face_found": True,
                     "identity_score": 0.1 if cut else 0.9, "identity_ok": not cut,
                     "box_x": 700.0 if cut else 430.0 + k, "box_y": 120.0, "box_w": 130.0, "box_h": 160.0,
                     "face_h_px": 160.0, "det_score": 1.0, "blur": 100.0, "luma": 120.0,
                     "pitch_deg": -15.0 if k == 8 else -5.0, "yaw_deg": 2.0 * k, "roll_deg": 0.0,
                     "bs_jawOpen": 0.05 if k % 2 else 0.01, "bs_eyeBlinkLeft": 0.7 if k == 9 else 0.1,
                     "bs_eyeBlinkRight": 0.7 if k == 9 else 0.1, "bs_browInnerUp": 0.01 * k, "ex_valence": -0.1 * k})
    return pd.DataFrame(rows)


def test_frame_logic_is_causal():
    full = face.finish_frames(_frames_df(12), 1.0, S)
    part = face.finish_frames(_frames_df(12).iloc[:8], 1.0, S)
    cols = ["track_id", "track_age_s", "head_speed_dps", "gate_ok", "gate_reason", "reading", "eyes_closed",
            "mouth_open_flag"]
    pd.testing.assert_frame_equal(full.loc[:7, cols], part.loc[:7, cols])
    assert list(full["gate_ok"]) == [k not in (5, 6) for k in range(12)]
    assert full.loc[5, "gate_reason"] == "identity"
    assert full.loc[7, "track_id"] == full.loc[4, "track_id"]  # 3 s cutaway, chair box unchanged: same shot
    short = face.finish_frames(_frames_df(12), 1.0, {**S, "track": {"iou_min": 0.3, "max_gap_s": 1.5}})
    assert short.loc[7, "track_id"] == short.loc[4, "track_id"] + 1 and np.isnan(short.loc[7, "head_speed_dps"])
    assert bool(full.loc[8, "reading"]) and np.isnan(full.loc[8, "eyes_closed"]) and full.loc[9, "eyes_closed"] == 1.0
    assert full.loc[1, "head_speed_dps"] == pytest.approx(2.0)  # yaw +2 deg per 1 s frame


def test_aggregate_windows_use_gated_trailing_frames():
    df = face.finish_frames(_frames_df(70), 1.0, S)
    feat = pd.DataFrame({"turn_idx": [4], "qa_idx": [0], "segment_kind": ["answer"], "t_start_s": [0.5],
                         "t_end_s": [65.0]})
    df = face.assign_turns(df, feat)
    assert df.loc[0, "turn_idx"] == -1 and df.loc[1, "turn_idx"] == 4
    agg = face.aggregate(df[df["turn_idx"] >= 0], feat, 1.0, S)
    turn, win = agg[agg["unit"] == "turn"].iloc[0], agg[agg["unit"] == "window"]
    assert list(win["t_end_s"]) == [30.5, 60.5, 65.0] and list(win["t_start_s"]) == [0.5, 30.5, 60.5]
    g = df[(df["t_s"] >= 0.5) & (df["t_s"] < 30.5) & df["gate_ok"]]
    assert win.iloc[0]["bs_browInnerUp"] == pytest.approx(g["bs_browInnerUp"].mean())
    assert win.iloc[0]["n_gated"] == len(g) and turn["n_frames"] == 64
    quiet = g[~g["mouth_open_flag"]]
    assert win.iloc[0]["ex_valence_mc"] == pytest.approx(quiet["ex_valence"].mean())
    assert "ex_valence" not in agg.columns  # upper_face_only: whole-face expression only as mouth-closed means
    assert np.isnan(turn["blink_rate_per_min"])  # 1 fps cannot see blinks


def test_check_config():
    on = {"mediapipe": True, "insightface": False, "pyfeat": False, "sface": True, "emotiefflib": True}
    face.check_config("mediapipe", "sface", ["emotiefflib"], on)
    with pytest.raises(ValueError, match="insightface"):
        face.check_config("insightface", "sface", [], on)
    with pytest.raises(ValueError, match="detector=pyfeat"):
        face.check_config("mediapipe", "pyfeat", [], {**on, "pyfeat": True})


class _StubDetector:
    """One face per frame; frames whose top-left pixel is bright are 'reporter' cutaways."""

    def detect(self, frames):
        out = []
        for f in frames:
            rep = f[0, 0, 0] > 128
            e = np.zeros(8, np.float32)
            e[1 if rep else 0] = 1.0
            c = fm.Cand(box=np.array([400, 100, 560, 300], np.float32), emb=e, pose=(-5.0, 3.0, 0.0),
                        blend={"jawOpen": 0.01, "eyeBlinkLeft": 0.1, "eyeBlinkRight": 0.1, "browInnerUp": 0.02})
            out.append([c])
        return out

    def close(self):
        pass


def test_stage_run_with_stub_models(cfg, monkeypatch):
    cv2 = pytest.importorskip("cv2")
    over = ["text.primary=fomc_roberta", "face.gates.min_blur=0"]  # the stub frames are flat grey
    cfg = load(overrides=over)
    m = mf.select(cfg, presser_id="20250917")[0]
    paths = io.MeetingPaths.of(cfg, m.presser_id).ensure()
    paths.file("video").write_bytes(b"")
    io.mark_done(paths, "fetch", {"status": "ok", "outputs": ["raw/video.mp4"]})
    turns = pd.DataFrame({"turn_idx": [0, 1, 2], "speaker": ["CHAIR POWELL", "REPORTER", "CHAIR POWELL"],
                          "role": ["chair", "reporter", "chair"], "is_chair": [True, False, True],
                          "segment_kind": ["opening", "question", "answer"], "qa_idx": [-1, 0, 0],
                          "t_start_s": [2.0, 20.0, 30.0], "t_end_s": [20.0, 30.0, 70.0]})
    a = make_anchor(cfg, m, 2.0)
    save_anchor(paths.dir, a)
    io.write_parquet(stamp(turns, a, 30.0), paths.file("turns"))
    io.mark_done(paths, "turns", {"status": "ok", "outputs": ["turns/turns.parquet", "turns/anchor.json"]})
    zpath, rows = paths.file("frames_zip", fps=1.0), []
    with zipfile.ZipFile(zpath, "w") as zf:
        for k in range(75):
            img = np.full((54, 96, 3), 255 if k in (40, 41) else 0, np.uint8)
            zf.writestr(f"f{k:07d}.jpg", cv2.imencode(".jpg", img)[1].tobytes())
            rows.append({"frame_idx": k, "t_s": float(k), "member": f"f{k:07d}.jpg", "width": 96, "height": 54})
    io.write_parquet(pd.DataFrame(rows), paths.file("frames_index", fps=1.0))
    io.mark_done(paths, "frames", {"status": "ok", "outputs": ["frames/frames_1fps.zip", "frames/frames_1fps.parquet"]})
    monkeypatch.setattr(face, "load_backends", lambda ctx: face.Backends(_StubDetector(), "sface", None, None, None,
                                                                        None, ()))
    assert run_one(cfg, "face", m, run_id="t") == "done"
    f = io.read_parquet(paths.file("face_frames"))
    assert f["t_s"].min() == 30.0 and f["t_s"].max() == 69.0 and len(f) == 40
    assert list(f.loc[f["t_s"].isin([40.0, 41.0]), "identity_ok"]) == [False, False]
    assert f["gate_ok"].sum() == 38
    assert (f["known_at"] == f["t_end_utc"] + pd.Timedelta(seconds=30)).all()
    assert f.loc[0, "t_end_utc"] == pd.Timestamp(a.wall(30.0))
    t = io.read_parquet(paths.file("face_turns"))
    assert set(t["unit"]) == {"turn", "window"} and t.loc[t["unit"] == "turn", "t_end_s"].iloc[0] == 70.0
    enr = io.read_json(paths.file("face_enroll"))
    assert enr["ok"] and enr["faces"] == 18 and enr["enroll_ranges"] == [[2.0, 20.0]]
    # a smoke-test cut is recorded and a later full run redoes the meeting
    cut = load(overrides=[*over, "runtime.max_seconds=50"])
    assert run_one(cut, "face", m, run_id="t2", force=True) == "done"
    assert io.read_done(paths, "face")["notes"]["max_seconds"] == 50.0
    assert len(io.read_parquet(paths.file("face_frames"))) == 20
    assert run_one(cfg, "face", m, run_id="t3") == "done"
    assert len(io.read_parquet(paths.file("face_frames"))) == 40
