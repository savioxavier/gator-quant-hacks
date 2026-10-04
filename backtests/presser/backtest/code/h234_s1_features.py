"""H2/H3/H4 step 1 (prereg 3.3-3.7, 4.1-4.4, 9.3): read the fedpress tables, run the feature QA, gates and kill
switches, build answer-level features on the caption clock and the causal per-chair z-scores.

No market data and no return is read here. Outputs: <out>/features/ and <out>/qa/ with sha256 manifests, plus the
sha256 of every package table read (qa/input_hashes.json)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from lib import check_addendum, load_events, sha256
from h234_lib import (BURN_IN, EX_EXPECTED, EXPECTED_MODELS, FACE_GATES, FLOOR, G4_MAX_SHARE, ICC_MIN, JAW_OPEN,
                      LABEL, MAX_VTT_OFFSET_S, MAX_WAV_GAP_S, MIN_CHUNK_S, MIN_CHUNKS, MIN_COVER, MIN_ENROLL_S,
                      MIN_FRAMES_ANSWER, MIN_FRAMES_MEETING, MIN_VOICED, NEG_LABELS, OUT, SFACE_THRESHOLD,
                      SI_MEETINGS, TEXT_CHRONO, causal_feature_z, check_prereg, dump, fedpress_root, g4_share, icc31,
                      load_h1_answers, mdir, powell_baseline_meetings, read_done, read_table, run_mode, si_root,
                      stage_state, table_meta, write_manifest)

check_addendum()
check_prereg()
ROOT = fedpress_root()
SI = si_root()
PLACEBO = run_mode(ROOT, SI)        # real mode refuses placebo paths, trees, stamps and output folders
F, Q = OUT / "features", OUT / "qa"
F.mkdir(parents=True, exist_ok=True)
Q.mkdir(parents=True, exist_ok=True)

ev = load_events()
base = powell_baseline_meetings(ev)
date_of = dict(zip(base.presser_id, base.date))
h1 = load_h1_answers()
lab_m = pd.read_parquet(TEXT_CHRONO / "meetings.parquet")
lab_m["presser_id"] = lab_m.meeting.astype(str)
video_dur = dict(zip(lab_m.presser_id, lab_m.video_duration_s))
input_hashes: dict[str, str] = {}
model_revs: dict[str, set] = {}
ex_labels_seen: dict[str, list] = {}


def note_input(root, pid, rel):
    p = mdir(root, pid) / rel
    if p.exists():
        input_hashes[f"{pid}/{rel}"] = sha256(p)
        for k, v in (table_meta(root, pid, rel).get("models") or {}).items():
            model_revs.setdefault(k, set()).add(str(v))


def caption_answers(pid: str) -> pd.DataFrame:
    """The frozen text label's caption-timed answers of the meeting, with E_k = t_end_video_s + end_cue_dur."""
    a = h1[(h1.presser_id == pid) & (h1.timing_source == "vtt") & h1.t_start_video_s.notna() &
           h1.t_end_video_s.notna() & h1.end_cue_dur.notna()].copy()
    a["E_media_s"] = a.t_end_video_s + a.end_cue_dur
    return a.sort_values("t_start_video_s").reset_index(drop=True)


def assign(t_mid, t_end, kind_ok, ans, half_open=False):
    """Index into ``ans`` of the answer that owns each chunk/frame, or -1 (prereg 3.3 / 4.3)."""
    if len(ans) == 0 or len(t_mid) == 0:
        return np.full(len(t_mid), -1)
    ts, E = ans.t_start_video_s.to_numpy(float), ans.E_media_s.to_numpy(float)
    m, e = np.asarray(t_mid, float)[:, None], np.asarray(t_end, float)[:, None]
    if half_open:                                     # frames: t_s in [start, E)
        inside = (m >= ts[None]) & (m < E[None])
    else:                                             # chunks: midpoint in [start, E] and chunk end <= E
        inside = (m >= ts[None]) & (m <= E[None]) & (e <= E[None] + 1e-9)
    inside &= np.asarray(kind_ok, bool)[:, None]
    best = np.argmax(np.where(inside, ts[None], -np.inf), axis=1)   # latest-starting answer if two overlap
    return np.where(inside.any(1), best, -1)


def text_scores(root, pid, spans, E):
    """Per chunk: cwf share hawkish - share dovish and cbr mean P(positive) - P(negative) (the package's
    cbr_sentiment definition) over included answer sentences whose word-time midpoint lies in the chunk (3.6).
    A sentence counts only if it ends by the chunk's caption answer end E_k, so no word after E_k enters."""
    nan = np.full(len(spans), np.nan)
    if stage_state(root, pid, "text") != "ok":
        return nan, nan.copy(), "text_not_ok"
    s = read_table(root, pid, "text/text_sentences.parquet")
    note_input(root, pid, "text/text_sentences.parquet")
    need = {"cwf_label", "cbr_p_positive", "cbr_p_negative"}
    if s is None or not need <= set(s.columns):
        return nan, nan.copy(), "text_columns_missing"
    s = s[(s.unit == "answer") & s.included.astype(bool)]
    mid = ((s.t_start_s + s.t_end_s) / 2).to_numpy(float)
    send = s.t_end_s.to_numpy(float)
    lab = s.cwf_label.astype(str).to_numpy()
    sen = (s.cbr_p_positive - s.cbr_p_negative).to_numpy(float)
    cwf, cbr = nan.copy(), nan.copy()
    for i, (a, b) in enumerate(spans):
        if not np.isfinite(E[i]):
            continue
        k = (mid >= a) & (mid < b) & (send <= E[i] + 1e-9)
        n = int(k.sum())
        if n:
            cwf[i] = ((lab[k] == "hawkish").sum() - (lab[k] == "dovish").sum()) / n
            cbr[i] = float(np.nanmean(sen[k]))
    return cwf, cbr, "ok"


def voice_answers(root, pid, turns, ans):
    """Chunk table with gates and answer assignment, and the answer-level medians."""
    v = read_table(root, pid, "voice/voice_chunks.parquet")
    note_input(root, pid, "voice/voice_chunks.parquet")
    if v is None or len(v) == 0:
        return None, "no_voice_chunks"
    if "chair" not in v.columns or not (v.chair.astype(str) == "Powell").all():
        return None, "voice_rows_not_powell"
    v = v.merge(turns[["turn_idx", "segment_kind", "is_chair"]], on="turn_idx", how="left")
    v["t_mid_s"] = (v.t_start_s + v.t_end_s) / 2
    v["ok_identity"] = v.identity_ok.fillna(False).astype(bool) & (v.identity_frac.astype(float) >= 1 - 1e-9)
    v["ok_dur"] = v.dur_s.astype(float) >= MIN_CHUNK_S - 1e-9
    v["ok_voiced"] = v.voiced_frac.astype(float) >= MIN_VOICED
    v["ok_arousal"] = v.arousal.notna()
    v["valid"] = v.ok_identity & v.ok_dur & v.ok_voiced & v.ok_arousal
    kind_ok = (v.segment_kind == "answer") & v.is_chair.fillna(False).astype(bool)
    idx = assign(v.t_mid_s, v.t_end_s, kind_ok, ans)
    v["answer_id"] = np.where(idx >= 0, ans.answer_id.to_numpy()[np.clip(idx, 0, None)] if len(ans) else None, None)
    v["E_media_s"] = np.where(idx >= 0, ans.E_media_s.to_numpy()[np.clip(idx, 0, None)] if len(ans) else np.nan, np.nan)
    cwf, cbr, tstate = text_scores(root, pid, list(zip(v.t_start_s, v.t_end_s)), v.E_media_s.to_numpy(float))
    v["text_cwf_share"], v["text_cbr_sent"] = cwf, cbr
    v["presser_id"] = pid
    keep = ["presser_id", "chunk_idx", "turn_idx", "qa_idx", "segment_kind", "is_chair", "t_start_s", "t_end_s",
            "t_mid_s", "dur_s", "identity_frac", "identity_ok", "identity_source", "voiced_frac", "arousal",
            "dominance", "valence", "ok_identity", "ok_dur", "ok_voiced", "ok_arousal", "valid", "answer_id",
            "E_media_s", "text_cwf_share", "text_cbr_sent", "known_at"]
    v = v[[c for c in keep if c in v.columns]]
    g = v[v.valid & v.answer_id.notna()].groupby("answer_id")
    a = pd.DataFrame({"nV": g.size(), "A_raw": g.arousal.median(), "D_raw": g.dominance.median(),
                      "voice_media_end_s": g.t_end_s.max(), "voice_known_at_pkg_max": g.known_at.max()})
    a.loc[a.nV < MIN_CHUNKS, ["A_raw", "D_raw"]] = np.nan
    return v, a.reset_index()


def face_answers(root, pid, ans):
    f = read_table(root, pid, "face/face_frames.parquet")
    note_input(root, pid, "face/face_frames.parquet")
    if f is None or len(f) == 0:
        return None, {}
    if "chair" not in f.columns or not (f.chair.astype(str) == "Powell").all():
        return None, {"face_rows_not_powell": True}
    ex_labels_seen[pid] = sorted(c[3:] for c in f.columns if c.startswith("ex_") and c not in ("ex_valence", "ex_arousal"))
    for c in ["bs_browDownLeft", "bs_browDownRight", "bs_browInnerUp", "bs_eyeSquintLeft", "bs_eyeSquintRight",
              "bs_browOuterUpLeft", "bs_browOuterUpRight", "bs_eyeWideLeft", "bs_eyeWideRight", "bs_cheekSquintLeft",
              "bs_cheekSquintRight", "ex_valence", "ex_arousal", *[f"ex_{x}" for x in NEG_LABELS]]:
        if c not in f.columns:
            f[c] = np.nan
    gate_pkg = f.gate_ok.fillna(False).astype(bool)
    g = FACE_GATES
    frozen = (f.face_found.fillna(False).astype(bool) & f.identity_ok.fillna(False).astype(bool) &
              (f.face_h_px >= g["min_face_h_px"]) & (f.yaw_deg.abs() <= g["max_abs_yaw_deg"]) &
              (f.pitch_deg.abs() <= g["max_abs_pitch_deg"]) & (f.blur >= g["min_blur"]) &
              (f.det_score >= g["min_det_score"]) & (f.identity_score >= SFACE_THRESHOLD - 1e-12))
    qa = {"face_gate_mismatch_vs_frozen": int((gate_pkg != frozen).sum()),
          "face_identity_mismatch_vs_0363": int(((f.identity_score >= SFACE_THRESHOLD - 1e-12) & f.face_found.fillna(False)
                                                  .astype(bool) != f.identity_ok.fillna(False).astype(bool)).sum()),
          "face_jaw_flag_mismatch": int(((f.mouth_open > JAW_OPEN) != f.mouth_open_flag.fillna(False).astype(bool)).sum())}
    f["gated"] = gate_pkg & frozen                    # fail closed if the run's config differed from the frozen gates
    idx = assign(f.t_s, f.t_s, f.segment_kind == "answer", ans, half_open=True)
    f["answer_id"] = np.where(idx >= 0, ans.answer_id.to_numpy()[np.clip(idx, 0, None)] if len(ans) else None, None)
    f["BD"] = (f.bs_browDownLeft + f.bs_browDownRight) / 2
    f["BI"] = f.bs_browInnerUp
    f["ES"] = (f.bs_eyeSquintLeft + f.bs_eyeSquintRight) / 2
    f["BOU"] = (f.bs_browOuterUpLeft + f.bs_browOuterUpRight) / 2
    f["EW"] = (f.bs_eyeWideLeft + f.bs_eyeWideRight) / 2
    f["CS"] = (f.bs_cheekSquintLeft + f.bs_cheekSquintRight) / 2
    f["NEG"] = f[[f"ex_{x}" for x in NEG_LABELS]].sum(axis=1, min_count=len(NEG_LABELS))
    f["EXV"], f["EXA"] = f.ex_valence, f.ex_arousal
    gf = f[f.gated & f.answer_id.notna()]
    qa["face_gated_frames_in_answers"] = int(len(gf))
    rows = []
    for aid, x in gf.groupby("answer_id"):
        r = {"answer_id": aid, "nF": len(x)}
        ok = len(x) >= MIN_FRAMES_ANSWER
        for c in ["BD", "BI", "ES", "BOU", "EW", "CS"]:
            r[f"{c}_raw"] = float(x[c].mean()) if ok else np.nan
        r["M"] = float(x.mouth_open_flag.astype(bool).mean()) if ok else np.nan
        mc = x[~x.mouth_open_flag.astype(bool)]
        r["nF_mouth_closed"] = len(mc)
        for c in ["NEG", "EXV", "EXA"]:
            r[f"{c}_raw"] = float(mc[c].mean()) if len(mc) >= MIN_FRAMES_ANSWER else np.nan
        nr = x[~x.reading.fillna(False).astype(bool)]
        r["nF_not_reading"] = len(nr)
        for c in ["BD", "BI", "ES"]:
            r[f"{c}nr_raw"] = float(nr[c].mean()) if len(nr) >= MIN_FRAMES_ANSWER else np.nan
        r["face_media_end_s"] = float(x.t_s.max())
        r["face_known_at_pkg_max"] = x.known_at.max()
        rows.append(r)
    return pd.DataFrame(rows), qa


# ======================================================================== per meeting
qa_rows, chunk_tabs, ans_tabs = [], [], []
for r in base.itertuples():
    pid = r.presser_id
    q = dict(presser_id=pid, date=r.date, drop_timing=int(r.drop_timing), sample_role=r.sample_role)
    q["turns_state"] = stage_state(ROOT, pid, "turns")
    tn = (read_done(ROOT, pid, "turns") or {}).get("notes", {}) or {}
    vtt = tn.get("vtt_check") or {}
    q["clock_source"] = tn.get("clock_source")
    q["vtt_median_offset_s"] = vtt.get("median_offset_s")
    q["vtt_n_words"] = vtt.get("n_words")
    q["vtt_ok"] = q["vtt_median_offset_s"] is not None and abs(float(q["vtt_median_offset_s"])) <= MAX_VTT_OFFSET_S
    am = mdir(ROOT, pid) / "audio" / "audio.json"
    wav = json.loads(am.read_text(encoding="utf-8")).get("duration_s") if am.exists() else \
        ((read_done(ROOT, pid, "audio") or {}).get("notes", {}) or {}).get("duration_s")
    q["wav_duration_s"], q["label_video_duration_s"] = wav, video_dur.get(pid)
    q["wav_gap_s"] = abs(float(wav) - float(q["label_video_duration_s"])) if (wav is not None and pd.notna(
        q["label_video_duration_s"])) else None
    q["wav_ok"] = q["wav_gap_s"] is not None and q["wav_gap_s"] <= MAX_WAV_GAP_S
    q["qa_ok"] = bool(q["turns_state"] == "ok" and q["vtt_ok"] and q["wav_ok"])
    q["diarize_state"] = stage_state(ROOT, pid, "diarize")
    dn = (read_done(ROOT, pid, "diarize") or {}).get("notes", {}) or {}
    for k in ["method", "enroll_s", "threshold", "threshold_source", "answer_verified_frac", "n_chunks"]:
        q[f"diarize_{k}"] = dn.get(k)
    note_input(ROOT, pid, "diarize/chair_check.parquet")
    q["voice_state"] = stage_state(ROOT, pid, "voice")
    q["face_state"] = stage_state(ROOT, pid, "face")
    enr = mdir(ROOT, pid) / "face" / "enroll.json"
    q["face_enroll_ok"] = bool(json.loads(enr.read_text(encoding="utf-8")).get("ok")) if enr.exists() else None
    ans = caption_answers(pid)
    q["n_caption_answers"] = len(ans)
    turns = read_table(ROOT, pid, "turns/turns.parquet")
    note_input(ROOT, pid, "turns/turns.parquet")
    a_tab = ans[["presser_id", "answer_id", "answer_no", "t_start_video_s", "E_media_s"]].copy()
    a_tab["date"] = r.date
    # ---- voice
    reasons_v = []
    if not q["qa_ok"]:
        reasons_v.append("qa_failed")
    if q["diarize_state"] != "ok":
        reasons_v.append(f"diarize_{q['diarize_state']}")
    elif q["diarize_enroll_s"] is None or float(q["diarize_enroll_s"]) < MIN_ENROLL_S:
        reasons_v.append("enrolment_below_60s")
    elif q["diarize_method"] != "ecapa_verify":
        reasons_v.append(f"diarize_method_{q['diarize_method']}")
    elif (q["diarize_threshold_source"] != "opening_loo" or q["diarize_threshold"] is None
          or float(q["diarize_threshold"]) < 0.30 - 1e-9):
        reasons_v.append("ecapa_threshold_not_opening_rule")
    if q["voice_state"] != "ok":
        reasons_v.append(f"voice_{q['voice_state']}")
    if not len(ans):
        reasons_v.append("no_caption_timed_answers")
    vt, va = (voice_answers(ROOT, pid, turns, ans) if (q["voice_state"] == "ok" and turns is not None and len(ans))
              else (None, None))
    if vt is None and isinstance(va, str):
        reasons_v.append(va)
        va = None
    if vt is not None:
        q["voice_n_chunks"] = len(vt)
        q["voice_identity_ok_frac"] = float(vt.ok_identity.mean())
        q["voice_valid_frac"] = float(vt.valid.mean())
        q["voice_valid_cover_s_frac"] = float(vt.loc[vt.valid, "dur_s"].sum() / vt.dur_s.sum())
        q["voice_chunks_in_answers"] = int(vt.answer_id.notna().sum())
        if q["voice_valid_cover_s_frac"] < MIN_COVER:
            reasons_v.append("valid_cover_below_50pct")
        chunk_tabs.append(vt)
        a_tab = a_tab.merge(va, on="answer_id", how="left")
    q["h2_ok"] = not reasons_v
    q["h2_exclusion"] = ";".join(reasons_v)
    # ---- face
    reasons_f = []
    if not q["qa_ok"]:
        reasons_f.append("qa_failed")
    if q["face_state"] != "ok":
        reasons_f.append(f"face_{q['face_state']}")
    elif not q["face_enroll_ok"]:
        reasons_f.append("face_enrolment_failed")
    fa, fqa = face_answers(ROOT, pid, ans) if (q["face_state"] == "ok" and len(ans)) else (None, {})
    q.update(fqa)
    if fqa.get("face_rows_not_powell"):
        reasons_f.append("face_rows_not_powell")
    if not len(ans):
        reasons_f.append("no_caption_timed_answers")
    elif q["face_state"] == "ok" and fqa.get("face_gated_frames_in_answers", 0) < MIN_FRAMES_MEETING:
        reasons_f.append("gated_frames_below_20")
    if fa is not None and len(fa):
        a_tab = a_tab.merge(fa, on="answer_id", how="left")
    q["h3_ok"] = not reasons_f
    q["h3_exclusion"] = ";".join(reasons_f)
    qa_rows.append(q)
    ans_tabs.append(a_tab)

qa = pd.DataFrame(qa_rows)
A = pd.concat(ans_tabs, ignore_index=True)
for c in ["nV", "A_raw", "D_raw", "nF", "BD_raw", "BI_raw", "ES_raw", "BOU_raw", "EW_raw", "CS_raw", "M", "NEG_raw",
          "EXV_raw", "EXA_raw", "BDnr_raw", "BInr_raw", "ESnr_raw", "voice_media_end_s", "face_media_end_s"]:
    if c not in A.columns:
        A[c] = np.nan
for c in ["voice_known_at_pkg_max", "face_known_at_pkg_max"]:
    if c not in A.columns:
        A[c] = pd.NaT
CH = pd.concat(chunk_tabs, ignore_index=True) if chunk_tabs else pd.DataFrame()
h2_ok = set(qa.loc[qa.h2_ok, "presser_id"])
h3_ok = set(qa.loc[qa.h3_ok, "presser_id"])
A.loc[~A.presser_id.isin(h2_ok), ["A_raw", "D_raw"]] = np.nan
fcols = ["BD_raw", "BI_raw", "ES_raw", "BOU_raw", "EW_raw", "CS_raw", "M", "NEG_raw", "EXV_raw", "EXA_raw",
         "BDnr_raw", "BInr_raw", "ESnr_raw"]
A.loc[~A.presser_id.isin(h3_ok), fcols] = np.nan

# ---- residualised valence (3.6): expanding OLS of chunk valence on the chunk's text scores, earlier meetings only
A["Vres_raw"] = np.nan
vres_log = []
if len(CH):
    pool = CH[CH.valid & CH.answer_id.notna() & CH.presser_id.isin(h2_ok) & CH.valence.notna() &
              CH.text_cwf_share.notna() & CH.text_cbr_sent.notna()].copy()
    order = sorted(pool.presser_id.unique(), key=lambda p: date_of[p])
    pool["resid"] = np.nan
    for k, pid in enumerate(order):
        if k < BURN_IN:
            vres_log.append(dict(presser_id=pid, k=k, status="burn_in"))
            continue
        fit = pool[pool.presser_id.isin(order[:k])]
        X = np.column_stack([np.ones(len(fit)), fit.text_cwf_share, fit.text_cbr_sent])
        b = np.linalg.lstsq(X, fit.valence.to_numpy(float), rcond=None)[0]
        cur = pool.presser_id == pid
        Xc = np.column_stack([np.ones(cur.sum()), pool.loc[cur, "text_cwf_share"], pool.loc[cur, "text_cbr_sent"]])
        pool.loc[cur, "resid"] = pool.loc[cur, "valence"].to_numpy(float) - Xc @ b
        vres_log.append(dict(presser_id=pid, k=k, status="fitted", n_fit=len(fit), b0=b[0], b_cwf=b[1], b_cbr=b[2]))
    g = pool[pool.resid.notna()].groupby("answer_id").resid
    vr = pd.DataFrame({"nVres": g.size(), "Vres_raw": g.median()})
    vr.loc[vr.nVres < MIN_CHUNKS, "Vres_raw"] = np.nan
    A = A.drop(columns=["Vres_raw"]).merge(vr.reset_index(), on="answer_id", how="left")
    CH = CH.merge(pool[["presser_id", "chunk_idx", "resid"]].rename(columns={"resid": "valence_resid"}),
                  on=["presser_id", "chunk_idx"], how="left")

# ---- causal z (3.5, 4.3, 4.4)
stats = []
for name, okset in [("A", h2_ok), ("D", h2_ok), ("Vres", h2_ok), ("BD", h3_ok), ("BI", h3_ok), ("ES", h3_ok),
                    ("BOU", h3_ok), ("EW", h3_ok), ("CS", h3_ok), ("NEG", h3_ok), ("EXV", h3_ok), ("EXA", h3_ok),
                    ("BDnr", h3_ok), ("BInr", h3_ok), ("ESnr", h3_ok)]:
    z, st = causal_feature_z(A, f"{name}_raw", FLOOR[name], okset, date_of)
    A[f"z{name}"] = z
    st["feature"] = name
    stats.append(st)
stats = pd.concat(stats, ignore_index=True)
A["U"] = A[["zBD", "zBI", "zES"]].mean(axis=1, skipna=False)
A["Unr"] = A[["zBDnr", "zBInr", "zESnr"]].mean(axis=1, skipna=False)
A["zA_burnin_k"] = A.presser_id.map(stats[stats.feature == "A"].set_index("presser_id").baseline_k)

# ---- meeting features
mfeat = (A.groupby("presser_id")
         .agg(zA_m=("zA", "mean"), zD_m=("zD", "mean"), zVres_m=("zVres", "mean"), U_m=("U", "mean"),
              Unr_m=("Unr", "mean"), M_m=("M", "mean"), n_answers_zA=("zA", "count"), n_answers_U=("U", "count"),
              **{f"z{c}_m": (f"z{c}", "mean") for c in ["BD", "BI", "ES", "BOU", "EW", "CS", "NEG", "EXV", "EXA"]})
         .reset_index())
mfeat = qa[["presser_id", "date", "drop_timing", "sample_role", "h2_ok", "h3_ok"]].merge(mfeat, on="presser_id", how="left")

# ---- kill switches: G4 variance gate and source invariance (3.7, 4.3)
kill = {}
sA, nA = g4_share(stats[stats.feature == "A"])
sD, nD = g4_share(stats[stats.feature == "D"])
si = {"status": "source invariance not checked", "icc31": None}
if SI is not None:
    pairs = []
    missing = []
    for pid in SI_MEETINGS:
        if pid not in h2_ok or stage_state(SI, pid, "voice") != "ok":
            missing.append(pid)
            continue
        turns = read_table(ROOT, pid, "turns/turns.parquet")
        _, va2 = voice_answers(SI, pid, turns, caption_answers(pid))
        a1 = A[A.presser_id == pid][["answer_id", "A_raw"]]
        if va2 is None or isinstance(va2, str):
            missing.append(pid)
            continue
        pairs.append(a1.merge(va2[["answer_id", "A_raw"]], on="answer_id", suffixes=("_orig", "_64k")))
    if missing:
        si.update(status=f"source invariance not checked (missing re-runs: {missing})")
    else:
        P = pd.concat(pairs).dropna()
        icc = icc31(P.A_raw_orig.to_numpy(), P.A_raw_64k.to_numpy())
        si.update(status="checked", icc31=icc, n_answers=len(P), meetings=list(SI_MEETINGS), si_root=str(SI))
h2_reasons = []
if np.isfinite(sA) and sA > G4_MAX_SHARE:
    h2_reasons.append(f"G4: floor binds in {sA:.0%} of post-burn-in meetings (no usable within-chair variation)")
if si["status"] == "checked" and not (si["icc31"] >= ICC_MIN):
    h2_reasons.append(f"source invariance ICC(3,1) = {si['icc31']:.3f} < 0.8")
kill["H2"] = dict(killed=bool(h2_reasons), reasons=h2_reasons, g4_share_arousal=sA, g4_n_post_burnin=nA,
                  g4_share_dominance_descriptive=sD, source_invariance=si,
                  labels=[LABEL] + ([si["status"]] if si["status"] != "checked" else []))
h3_reasons, g4f = [], {}
for c in ["BD", "BI", "ES"]:
    s_, n_ = g4_share(stats[stats.feature == c])
    g4f[c] = dict(share=s_, n_post_burnin=n_)
    if np.isfinite(s_) and s_ > G4_MAX_SHARE:
        h3_reasons.append(f"G4: floor binds for {c} in {s_:.0%} of post-burn-in meetings")
kill["H3"] = dict(killed=bool(h3_reasons), reasons=h3_reasons, g4=g4f,
                  av_skew="not estimated, not corrected (A-33; cannot break causality)", labels=[LABEL])
kill["placebo_tree"] = PLACEBO

# ---- QA records (old feature tables are removed first so no stale table enters the manifest)
for old in F.glob("*.parquet"):
    old.unlink()
models = {k: sorted(v) for k, v in model_revs.items()}
model_check = {k: dict(expected_prefix=v, seen=models.get(k, []),
                       ok=bool(models.get(k)) and all(str(s).startswith(v) for s in models.get(k, [])))
               for k, v in EXPECTED_MODELS.items()}
bad_models = {k: v for k, v in model_check.items() if not v["ok"]}
if bad_models:
    raise SystemExit(f"model revisions differ from the pre-registration (write a dated deviation note first): {bad_models}")
ex_lists = sorted({tuple(v) for v in ex_labels_seen.values()})
realised = dict(ex_labels_realised=[list(x) for x in ex_lists], ex_labels_expected=list(EX_EXPECTED),
                ex_labels_match=(ex_lists == [tuple(sorted(EX_EXPECTED))]), model_revisions_seen=models,
                model_check=model_check, fedpress_root=str(ROOT), placebo_tree=PLACEBO,
                face_gates_frozen=FACE_GATES, sface_threshold=SFACE_THRESHOLD)
qa.to_csv(Q / "meeting_qa.csv", index=False)
stats.to_csv(Q / "baseline_stats.csv", index=False)
pd.DataFrame(vres_log).to_csv(Q / "valence_resid_fits.csv", index=False)
dump(Q / "kill_switches.json", kill)
dump(Q / "realised_models.json", realised)
dump(Q / "input_hashes.json", input_hashes)
dump(Q / "provenance.json", dict(placebo=PLACEBO, fedpress_root=str(ROOT), si_root=str(SI) if SI else None,
                                 out=str(OUT), label=LABEL))
write_manifest(Q, [p for p in Q.glob("*") if p.name != "manifest_sha256.txt"])

A.to_parquet(F / "answers_h234.parquet", index=False)
mfeat.to_parquet(F / "meetings_h234.parquet", index=False)
if len(CH):
    CH.to_parquet(F / "voice_chunks_assigned.parquet", index=False)
write_manifest(F, [p for p in F.glob("*.parquet")])
summary = dict(placebo_tree=PLACEBO, n_meetings=len(qa), h2_ok=len(h2_ok), h3_ok=len(h3_ok),
               h2_excluded=qa.loc[~qa.h2_ok, ["date", "h2_exclusion"]].values.tolist(),
               h3_excluded=qa.loc[~qa.h3_ok, ["date", "h3_exclusion"]].values.tolist(),
               answers_with_zA=int(A.zA.notna().sum()), answers_with_U=int(A.U.notna().sum()),
               pkg_causal_z_match=bool(stats["pkg_match"].dropna().all()) if "pkg_match" in stats else None,
               kill=kill)
print(json.dumps(summary, indent=1, default=str))
