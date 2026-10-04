"""PLACEBO fedpress output tree for the 75 press conferences (synthetic; NOT features; never a result).

Writes <here>/tree/meetings/<presser_id>/ in the package's layout and schemas, using the package's own code for
everything that shapes a table: fedpress.io (paths, parquet writer, done markers), fedpress.clock (anchor,
known_at stamp), fedpress.stages._chunks (voice and diarize chunking, identity coverage) and
fedpress.stages.face (finish_frames, assign_turns, aggregate). Feature values are random draws from a seeded
generator that never sees market data, so any association with returns is pure chance.

Every parquet file carries {"placebo": true} in its fedpress metadata, every done marker says PLACEBO, and the
tree root holds PLACEBO.json. A second tree <here>/tree_si/ holds placebo 64 kbps re-runs of the voice stage for
the three source-invariance meetings (prereg 3.7).

Planted gate cases (to exercise the exclusions): 2019-07-31 vtt offset 2.6 s (QA fail), 2020-07-29 WAV 3 s longer
than the label video (QA fail), 2021-06-16 diarize failed (voice blocked), 2022-03-16 face enrolment failed.
Meetings without captions get no vtt_check (as in the package) and so fail the QA.
"""
from __future__ import annotations

import json
import math
import sys
import types
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SCR = HERE.parent
PKG = SCR / "team_push" / "hpg" / "fedpress_pkg"
sys.path.insert(0, str(PKG))
# fedpress.config imports PyYAML at module level; the placebo builder never loads a config file, so an empty
# stand-in module lets fedpress.stage / fedpress.stages.face import in this environment.
sys.modules.setdefault("yaml", types.ModuleType("yaml"))
from fedpress import io as fio  # noqa: E402
from fedpress import clock  # noqa: E402
from fedpress.stage import ID_COLUMNS, code_version  # noqa: E402
from fedpress.stages import _chunks  # noqa: E402
from fedpress.stages import _face_models as fm  # noqa: E402
from fedpress.stages import face as face_stage  # noqa: E402

TREE, TREE_SI = HERE / "tree", HERE / "tree_si"
EVENTS = SCR / "presser_bt" / "events" / "events.csv"
ANSWERS = SCR / "presser_bt" / "text_chrono" / "answers.parquet"
SEED = 7_003_2026          # placebo generator seed (independent of the analysis seed)
LATENCY = 30.0
# config.yaml (commit 436a351) values used by the package code called below
FACE_CFG = {"gates": {"min_face_h_px": 80, "max_abs_yaw_deg": 40, "max_abs_pitch_deg": 30, "min_blur": 20.0,
                      "min_det_score": 0.5},
            "masks": {"jaw_open": 0.025, "reading_pitch_deg": -10.0, "eyes_closed": 0.5},
            "track": {"iou_min": 0.3, "max_gap_s": 3.0}, "upper_face_only": True, "blink_min_fps": 10,
            "aggregate": {"windows_s": [30, 60], "min_gated_frames": 3,
                          "mouth_closed_columns": ["ex_valence", "ex_arousal", "ex_happiness", "bs_mouthSmileLeft",
                                                   "bs_mouthSmileRight", "au12", "pf_happy", "pf_valence",
                                                   "pf_arousal"]}}
MODELS = {"voice": {"audeering_msp_dim": "6eba34a2485ea31cb03600241787c3a5edab8626"},
          "diarize": {"ecapa_voxceleb": "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"},
          "face": {"mediapipe_face_landmarker": "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff",
                   "emotiefflib_enet_b0_8_va_mtl": "emotiefflib==1.1.1",
                   "sface_opencv": "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"},
          "turns": {"whisper_turbo_ct2": "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf"}, "text": {}}
PLANT = {"20190731": "vtt_offset", "20200729": "wav_gap", "20210616": "diarize_failed", "20220316": "face_enroll_failed"}
SI_IDS = ("20190130", "20190320", "20190619")
BS_NAMES = sorted(fm._MP_BLEND_SET)
rng = np.random.default_rng(SEED)


class M:
    """The bits of fedpress.manifest.Meeting the writers need."""

    def __init__(self, row):
        self.presser_id = row.date.replace("-", "")
        self.meeting_date = date.fromisoformat(row.date)
        self.chair = row.chair
        self.sample_role = "study"
        self.start_utc = clock.et_to_utc(self.meeting_date, str(row.presser_sched_et)[:5])


def with_ids(df, m):
    out = df.copy()
    for col, val in zip(ID_COLUMNS, (m.presser_id, m.meeting_date.isoformat(), m.chair, m.sample_role)):
        if col not in out.columns:
            out.insert(len(out.columns), col, val)
    return out


def write(root, paths, m, df, key, stage):
    p = paths.file(key)
    fio.write_parquet(with_ids(df, m), p, {"stage": stage, "presser_id": m.presser_id, "run_id": "PLACEBO",
                                           "config_hash": "PLACEBO", "stage_fingerprint": "PLACEBO",
                                           "code_version": code_version(), "models": MODELS[stage],
                                           "created_utc": fio.utc_now(), "latency_s": LATENCY, "placebo": True})
    return p.relative_to(paths.dir).as_posix()


def done(paths, stage, outputs, notes, status="ok"):
    fio.mark_done(paths, stage, {"status": status, "outputs": outputs, "notes": notes, "run_id": "PLACEBO",
                                 "placebo": "PLACEBO: synthetic tree, not package output",
                                 "finished_utc": fio.utc_now()})


def turns_table(row, ans, eps):
    """Transcript turns on a placebo ASR clock = caption time + eps (+ jitter), in the package turns schema."""
    timed = bool(len(ans)) and (ans.timing_source == "vtt").all()
    greet = float(row.greeting_s) if pd.notna(row.greeting_s) else 15.0
    spans = []
    if timed:
        for r in ans.itertuples():
            a = float(r.t_start_video_s) + eps + rng.normal(0, 0.15)
            b = float(r.t_end_video_s) + eps + rng.normal(0, 0.15)
            spans.append((a, max(b, a + 1.0), int(r.n_words)))
    else:
        t = greet + 480.0
        for r in ans.itertuples():
            a = t + 20.0
            b = a + max(5.0, r.n_words / 2.6)
            spans.append((a, b, int(r.n_words)))
            t = b + 2.0
    first_q = spans[0][0] - 25.0 if spans else greet + 300
    rows = [dict(speaker=f"CHAIR {row.chair.upper()}", role="chair", is_chair=True, segment_kind="opening", qa_idx=-1,
                 n_words=int((first_q - greet) * 2.6), t_start_s=greet, t_end_s=first_q - 1.0)]
    prev = first_q - 1.0
    for k, (a, b, nw) in enumerate(spans):
        rows.append(dict(speaker="MICHELLE SMITH", role="moderator", is_chair=False, segment_kind="moderator",
                         qa_idx=-1, n_words=3, t_start_s=prev + 0.2, t_end_s=prev + 0.2))
        qa_, qb = prev + 0.4, a - 0.3
        if qb <= qa_:
            qa_ = qb = prev + 0.4
        rows.append(dict(speaker="REPORTER", role="reporter", is_chair=False, segment_kind="question", qa_idx=k,
                         n_words=int(max(0.0, qb - qa_) * 2.8), t_start_s=qa_, t_end_s=qb))
        rows.append(dict(speaker=f"CHAIR {row.chair.upper()}", role="chair", is_chair=True, segment_kind="answer",
                         qa_idx=k, n_words=nw, t_start_s=a, t_end_s=b))
        prev = b
    rows.append(dict(speaker="MICHELLE SMITH", role="moderator", is_chair=False, segment_kind="moderator", qa_idx=-1,
                     n_words=4, t_start_s=prev + 1.0, t_end_s=prev + 2.0))
    rows.append(dict(speaker=f"CHAIR {row.chair.upper()}", role="chair", is_chair=True, segment_kind="closing",
                     qa_idx=-1, n_words=3, t_start_s=prev + 2.5, t_end_s=prev + 3.5))
    t = pd.DataFrame(rows)
    t.insert(0, "turn_idx", np.arange(len(t)))
    t.insert(6, "text", "PLACEBO")
    t["n_matched"] = (t.n_words * 0.95).astype(int)
    t["clock_source"] = "asr"
    t["match_frac"] = np.where(t.n_words > 0, t.n_matched / t.n_words.clip(lower=1), np.nan)
    t["timing_ok"] = True
    cols = ["turn_idx", "speaker", "role", "is_chair", "segment_kind", "qa_idx", "text", "n_words", "n_matched",
            "t_start_s", "t_end_s", "clock_source", "match_frac", "timing_ok"]
    return t[cols].astype({"t_start_s": "float64", "t_end_s": "float64", "match_frac": "float64"}), timed, greet


def diarize_table(turns):
    opening = turns[turns.segment_kind == "opening"]
    enroll_end = float(opening.t_end_s.max())
    df = _chunks.turn_chunks(turns, 3.0, 3.0, 1.5, not_before=enroll_end, merge_tail=True)
    df["label_is_chair"] = df["role"] == "chair"
    df["method"] = "ecapa_verify"
    thr = 0.38
    df["score"] = np.where(df.label_is_chair, rng.normal(0.60, 0.12, len(df)), rng.normal(0.12, 0.08, len(df)))
    df["threshold"] = thr
    df["ecapa_ok"] = df["score"] >= thr
    df["pyannote_speaker"], df["pyannote_chair_frac"], df["pyannote_ok"] = "", np.nan, True
    df["chair_verified"] = df["label_is_chair"] & df["ecapa_ok"]
    df["agree"] = df["label_is_chair"] == df["ecapa_ok"]
    n_enroll = len([1 for t in opening.itertuples() for _ in _chunks.windows(t.t_start_s, t.t_end_s, 3.0, 3.0, 3.0)])
    notes = {"method": "ecapa_verify", "enroll_end_s": round(enroll_end, 3), "n_chunks": len(df), "threshold": thr,
             "threshold_source": "opening_loo", "enroll_s": n_enroll * 3.0, "n_enroll": n_enroll,
             "answer_verified_frac": round(float(df.loc[df.segment_kind == "answer", "chair_verified"].mean()), 4)}
    return df, notes


def voice_table(turns, cc, mu, noise=None):
    df = _chunks.turn_chunks(turns[turns["is_chair"]], 8.0, 8.0, 3.0, kinds=["answer"], mode="fixed")
    df = df.drop(columns=["role", "segment_kind"])
    ver = cc.loc[cc["chair_verified"].astype(bool), ["t_start_s", "t_end_s"]].to_numpy()
    frac = _chunks.coverage(df[["t_start_s", "t_end_s"]].to_numpy(), ver)
    df["identity_frac"], df["identity_ok"], df["identity_source"] = frac, frac >= 1.0 - 1e-9, "diarize"
    n = len(df)
    df["arousal"] = np.clip(0.55 + mu[0] + rng.normal(0, 0.06, n), 0, 1)
    df["dominance"] = np.clip(0.50 + mu[1] + rng.normal(0, 0.05, n), 0, 1)
    df["valence"] = np.clip(0.45 + mu[2] + rng.normal(0, 0.06, n), 0, 1)
    f0 = rng.normal(6.0, 1.0, n)
    df["f0_median_st"], df["f0_iqr_st"] = f0, np.abs(rng.normal(2.5, 0.6, n))
    df["f0_p10_st"], df["f0_p90_st"] = f0 - 2.5, f0 + 3.0
    df["voiced_frac"] = rng.beta(6, 3, n)
    df["intensity_db"], df["hnr_db"] = rng.normal(64, 3, n), rng.normal(11, 2, n)
    nw = rng.poisson(2.6 * df.dur_s.to_numpy())
    df["n_words"] = nw.astype(float)
    df["speech_rate_wps"] = nw / df.dur_s
    pf = rng.uniform(0.05, 0.25, n)
    df["articulation_rate_wps"] = nw / (df.dur_s * (1 - pf))
    df["pause_frac"], df["n_pauses"] = pf, rng.poisson(2, n).astype(float)
    return df


def face_tables(turns, enroll_ok, mu):
    feat = turns[turns.is_chair & (turns.segment_kind == "answer")].reset_index(drop=True)
    rows = []
    for t in feat.itertuples():
        ua = rng.normal(0, 0.012, 6)                       # answer-level random effects (placebo)
        for k in range(int(math.ceil(t.t_start_s)), int(math.ceil(t.t_end_s))):
            r = {"frame_idx": k, "t_s": float(k), "frame_w": 960, "frame_h": 540}
            cut = rng.random() < 0.15                      # camera on a reporter
            found = rng.random() < 0.95
            r["n_faces"] = int(found) + int(cut)
            r["face_found"] = bool(found or cut)
            if not r["face_found"]:
                r["identity_ok"] = False
                rows.append(r)
                continue
            score = rng.normal(0.08, 0.06) if cut else rng.normal(0.72, 0.09)
            score = score if enroll_ok else 0.0
            r["identity_score"] = float(score)
            r["identity_ok"] = bool(enroll_ok and score >= 0.363)
            h = max(30.0, rng.normal(150, 30))
            x, y = rng.normal(400, 20), rng.normal(120, 10)
            r.update(box_x=x, box_y=y, box_w=h * 0.8, box_h=h, face_h_px=h, det_score=float(rng.uniform(0.45, 1.0)),
                     blur=float(max(1.0, rng.normal(80, 35))), luma=float(rng.normal(120, 10)))
            r.update(zip(face_stage.POSE, (float(rng.normal(-3, 9)), float(rng.normal(0, 16)), float(rng.normal(0, 5)))))
            r["mp_mouth_open"] = float(rng.uniform(0, 0.08))
            bs = {n: float(np.clip(rng.beta(1.2, 12), 0, 1)) for n in BS_NAMES}
            for i, n in enumerate([("browDownLeft", "browDownRight"), ("browInnerUp",), ("eyeSquintLeft", "eyeSquintRight"),
                                   ("browOuterUpLeft", "browOuterUpRight"), ("eyeWideLeft", "eyeWideRight"),
                                   ("cheekSquintLeft", "cheekSquintRight")]):
                base = [0.06, 0.10, 0.20, 0.05, 0.04, 0.03][i] + mu[i] + ua[i]
                for nn in n:
                    bs[nn] = float(np.clip(base + rng.normal(0, 0.03), 0, 1))
            bs["jawOpen"] = float(rng.uniform(0.0, 0.06))
            r.update({f"bs_{fm._bs_name(n)}": v for n, v in bs.items()})
            p = rng.dirichlet(np.ones(8) * 1.5)
            r.update({f"ex_{lab}": float(v) for lab, v in zip(fm.EMOTIEFF_8, p)})
            r["ex_valence"], r["ex_arousal"] = float(rng.normal(0.0, 0.3)), float(rng.normal(0.3, 0.2))
            rows.append(r)
    df = pd.DataFrame(rows)
    df = face_stage.assign_turns(face_stage.finish_frames(df, 1.0, FACE_CFG), feat)
    df = df[df["turn_idx"] >= 0]
    agg = face_stage.aggregate(df, feat, 1.0, FACE_CFG)
    lead = ["frame_idx", "t_s", "turn_idx", "qa_idx", "segment_kind", "frame_w", "frame_h", "n_faces", "face_found",
            "box_x", "box_y", "box_w", "box_h", "face_h_px", "det_score", "identity_score", "identity_ok",
            *face_stage.POSE, "blur", "luma", "mouth_open", "mouth_open_flag", "reading", "eye_blink", "eyes_closed",
            "track_id", "track_age_s", "head_speed_dps", "gate_ok", "gate_reason"]
    df = df[[c for c in lead if c in df.columns] + sorted(c for c in df.columns if c not in lead)]
    return df, agg, feat


def text_table(turns):
    rows = []
    for t in turns[(turns.segment_kind == "answer") & turns.is_chair].itertuples():
        k_n = max(1, int(t.n_words / 22))
        edges = np.linspace(t.t_start_s, t.t_end_s, k_n + 1)
        for k in range(k_n):
            nw = int(rng.integers(3, 40))
            rows.append({"unit": "answer", "turn_idx": t.turn_idx, "qa_idx": t.qa_idx, "sent_idx": k, "text": "PLACEBO",
                         "n_words": nw, "included": nw >= 4, "tdw_filter": bool(rng.random() < 0.3),
                         "t_start_s": edges[k], "t_end_s": edges[k + 1], "time_method": "words",
                         "splitter": "fedpress-regex-1", "hedge_count": int(rng.poisson(0.3)), "in_tdw_labels": None})
    s = pd.DataFrame(rows)
    for c in ["Uncertainty", "WeakModal", "StrongModal", "Negative", "Positive", "Constraining"]:
        s[f"lm_{c}"] = np.nan
    p = rng.dirichlet(np.ones(3), len(s))
    s["cwf_p_dovish"], s["cwf_p_hawkish"], s["cwf_p_neutral"] = p[:, 0], p[:, 1], p[:, 2]
    s["cwf_label"] = np.array(["dovish", "hawkish", "neutral"], dtype=object)[p.argmax(1)]
    s["cwf_truncated"] = False
    q = rng.dirichlet(np.ones(2), len(s))
    s["cbr_p_negative"], s["cbr_p_positive"] = q[:, 0], q[:, 1]
    s["cbr_label"] = np.array(["negative", "positive"], dtype=object)[q.argmax(1)]
    s["cbr_truncated"] = False
    return s


def main():
    ev = pd.read_csv(EVENTS, dtype={"date": str})
    ans_all = pd.read_parquet(ANSWERS)
    for root in (TREE, TREE_SI):
        (root / "meetings").mkdir(parents=True, exist_ok=True)
        (root / "PLACEBO.json").write_text(json.dumps({
            "placebo": True, "what": "synthetic fedpress-schema tables for pipeline testing; NOT features",
            "generator": "placebo_features/make_placebo_tree.py", "seed": SEED, "planted": PLANT,
            "market_data_used": False}, indent=2) + "\n")
    log = []
    for row in ev.itertuples():
        m = M(row)
        paths = fio.MeetingPaths(TREE / "meetings" / m.presser_id).ensure()
        ans = ans_all[ans_all.meeting == m.presser_id].sort_values("answer_no")
        eps = float(rng.uniform(-0.4, 0.4))
        turns, timed, greet = turns_table(row, ans, eps)
        anchor = clock.Anchor(greet, m.start_utc, "scheduled_start", float("nan"), "greeting_at_scheduled")
        clock.save_anchor(paths.dir, anchor)
        o = [write(TREE, paths, m, clock.stamp(turns, anchor, LATENCY), "turns", "turns"), "turns/anchor.json"]
        notes = {"clock_source": "asr", "base_clock": "asr", "align_method": "text_match", "timing_ok": True,
                 "greeting_media_s": round(greet, 3), "anchor": anchor.to_json(), "n_turns": len(turns),
                 "n_answers": int((turns.segment_kind == "answer").sum())}
        if int(row.has_captions) == 1:
            off = 2.6 if PLANT.get(m.presser_id) == "vtt_offset" else round(eps, 3)
            notes["vtt_check"] = {"n_words": int(rng.integers(3000, 6000)), "median_offset_s": off,
                                  "median_abs_s": abs(off) + 0.05, "p90_abs_s": abs(off) + 0.4}
        done(paths, "turns", o, notes)
        wav = float(row.video_duration_s) + (3.0 if PLANT.get(m.presser_id) == "wav_gap" else float(rng.normal(0, 0.3)))
        fio.atomic_write_json(paths.file("audio_meta"), {"duration_s": round(wav, 3), "placebo": True})
        done(paths, "audio", ["audio/audio.json"], {"duration_s": round(wav, 3)})
        # diarize
        if PLANT.get(m.presser_id) == "diarize_failed":
            fio.mark_failed(paths, "diarize", {"error": "PLACEBO planted failure", "run_id": "PLACEBO"})
            cc = None
        else:
            cc, dn = diarize_table(turns)
            done(paths, "diarize", [write(TREE, paths, m, clock.stamp(cc, anchor, LATENCY), "chair_check", "diarize")], dn)
        powell = m.chair == "Powell"
        mu_v = rng.normal(0, 0.03, 3)
        # voice (requires diarize; Powell only)
        if not powell:
            for st in ("voice", "face"):
                fio.mark_done(paths, st, {"status": "not_applicable", "outputs": [], "run_id": "PLACEBO",
                                          "reason": f"chair {m.chair} not in {st}.chairs ['Powell']",
                                          "placebo": "PLACEBO: synthetic tree, not package output"})
        elif cc is not None:
            vc = voice_table(turns, cc, mu_v)
            done(paths, "voice", [write(TREE, paths, m, clock.stamp(vc, anchor, LATENCY), "voice_chunks", "voice")],
                 {"n_chunks": len(vc), "n_identity_ok": int(vc.identity_ok.sum())})
            if m.presser_id in SI_IDS:                  # placebo 64 kbps re-run: same chunks, small re-encode noise
                p2 = fio.MeetingPaths(TREE_SI / "meetings" / m.presser_id).ensure()
                vc2 = vc.copy()
                vc2["arousal"] = np.clip(vc2.arousal + rng.normal(0, 0.01, len(vc2)), 0, 1)
                done(p2, "voice", [write(TREE_SI, p2, m, clock.stamp(vc2, anchor, LATENCY), "voice_chunks", "voice")],
                     {"n_chunks": len(vc2), "reencode": "aac 64 kbps (PLACEBO)"})
        # face (Powell only)
        if powell:
            enroll_ok = PLANT.get(m.presser_id) != "face_enroll_failed"
            ff, ft, feat = face_tables(turns, enroll_ok, rng.normal(0, 0.01, 6))
            o = [write(TREE, paths, m, clock.stamp(ff, anchor, LATENCY), "face_frames", "face"),
                 write(TREE, paths, m, clock.stamp(ft, anchor, LATENCY), "face_turns", "face")]
            emb = rng.normal(size=128)
            emb /= np.linalg.norm(emb)
            enr = {"method": "sface", "threshold": 0.363, "enroll_frames": 180, "faces": 175 if enroll_ok else 3,
                   "kept": 170 if enroll_ok else 3, "self_cos_median": 0.8, "self_cos_p05": 0.62,
                   "embedding": [round(float(v), 6) for v in emb] if enroll_ok else None, "ok": enroll_ok,
                   "enroll_ranges": [[greet, greet + 180.0]], "fps": 1.0, "source": "zip",
                   "models": list(MODELS["face"]), "placebo": True}
            fio.atomic_write_json(paths.file("face_enroll"), enr)
            o.append("face/enroll.json")
            done(paths, "face", o, {"fps": 1.0, "enroll_ok": enroll_ok, "identity_method": "sface",
                                    "identity_threshold": 0.363, "gated_frac": float(ff.gate_ok.mean())})
        # text (sentences only; used by the descriptive valence row)
        ts = text_table(turns)
        done(paths, "text", [write(TREE, paths, m, clock.stamp(ts, anchor, LATENCY), "text_sentences", "text")],
             {"primary": "chrono_wf"})
        log.append(dict(presser_id=m.presser_id, chair=m.chair, timed=timed, eps=eps, plant=PLANT.get(m.presser_id, "")))
    pd.DataFrame(log).to_csv(HERE / "placebo_tree_log.csv", index=False)
    print(f"placebo tree: {len(log)} meetings under {TREE}")


if __name__ == "__main__":
    main()
