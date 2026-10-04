"""aggregate (cpu): per-meeting feature tables that join turns, text, voice and face.

* ``answers`` (features/answers.parquet): one row per chair turn whose segment kind is in
  ``aggregate.segments`` (default: answers; opening remarks are excluded by the team plan). Text scores of the
  turn (``hawk`` and every ``<p>_hawk_*``), the statement score and the gaps, the preceding question's score
  (H1-Q), causal running means over the answers so far (H1-run input), and voice/face statistics over the
  verified chunks/frames inside the turn (``voice_<col>``: median per answer, A-31; ``face_<col>``: mean).
  known_at = turn end + latency.
* ``meeting`` (features/meeting.parquet): one row. ``h1_gap`` = mean answer hawk - statement hawk (H1-primary
  input), the same gap for every stance scorer, question mean, voice/face medians over all verified chunks
  and frames, statement length (A-34) and the turns QA notes. known_at = end of the last answer + latency.
* ``windows`` (features/windows.parquet): trailing windows of ``aggregate.windows_s`` seconds evaluated every
  ``aggregate.window_step_s`` seconds through the Q&A: text (sentences ending in the window), voice (chunks
  ending in it), face (frames in it) and seconds of chair speech. known_at = window end + latency.

Only raw values are stored. Per-chair z-scores come from :func:`fedpress.baselines.causal_z` at analysis
time; ``finalize`` (run after ``aggregate --all``) builds the cross-meeting panel through
:func:`fedpress.dataset.build`.

Voice and face are optional inputs: a meeting outside ``voice.chairs`` / ``face.chairs`` (not applicable), a
disabled stage or a failed one leaves those columns empty. A stage still pending for the meeting stops the
aggregation (rerun it afterwards) unless it is removed from ``aggregate.wait_for``.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .. import io
from ..log import Log
from ..stage import StageContext, StageResult, StageSpec

SPEC = StageSpec(name="aggregate", requires=("turns", "text"), resource="cpu",
                 outputs=("answers", "meeting", "windows"), config_keys=("timing",))

TEXT_SKIP = {"unit", "turn_idx", "qa_idx", "speaker", "role", "segment_kind", "t_start_s", "t_end_s", "n_words",
             "presser_id", "meeting_date", "chair", "sample_role", "t_end_utc", "known_at", "latency_s",
             "anchor_source", "anchor_unc_s", "n_paragraphs"}
FACE_AUTO_PREFIX = ("ex_", "pf_")
FACE_AUTO_COLS = ("yaw_deg", "pitch_deg", "roll_deg", "head_speed_dps", "face_h_px", "mouth_open")


def input_state(ctx: StageContext, stage: str) -> str:
    """ok | not_applicable | disabled | failed | pending for one upstream stage of this meeting."""
    if ctx.cfg.section(stage).get("enabled", True) is False:
        return "disabled"
    info = io.read_done(ctx.paths, stage)
    if info is not None and io.is_done(ctx.paths, stage):
        return str(info.get("status", "ok"))
    if io.failed_path(ctx.paths, stage).exists():
        return "failed"
    return "pending"


def _optional_table(ctx: StageContext, stage: str, key: str) -> tuple[Any, str]:
    state = input_state(ctx, stage)
    path = ctx.out(key)
    return (io.read_parquet(path) if state == "ok" and path.exists() else None), state


def _face_cols(ctx: StageContext, df: Any, wanted: Any) -> list[str]:
    """``auto``: expression probabilities and valence/arousal (ex_*, pf_*), head pose and speed, face size,
    mouth opening (the speaking covariate of A-32) and, with face.upper_face_only, only upper-face
    blendshapes/AUs (the face stage's own list); otherwise every bs_*/au* column."""
    if df is None:
        return []
    if wanted not in (None, "auto"):
        return [c for c in wanted if c in df.columns]
    upper: set[str] | None = None
    if ctx.cfg.get("face.upper_face_only", True):
        from ._face_models import UPPER_FACE_AUS, UPPER_FACE_BLENDS

        upper = {f"bs_{b}" for b in UPPER_FACE_BLENDS} | set(UPPER_FACE_AUS)
    out = []
    for c in df.columns:
        if c.startswith(("bs_", "au")) and (upper is None or c in upper):
            out.append(c)
        elif c.startswith(FACE_AUTO_PREFIX) or c in FACE_AUTO_COLS:
            out.append(c)
    return out


def _filter(df: Any, cols: list[str]) -> Any:
    """Rows where every gate column present in ``df`` is true."""
    if df is None:
        return None
    keep = None
    for c in cols:
        if c in df.columns:
            ok = df[c].fillna(False).astype(bool)
            keep = ok if keep is None else keep & ok
    return df if keep is None else df[keep]


def _stat(values: Any, how: str) -> float:
    v = values.dropna()
    if not len(v):
        return math.nan
    return float(v.median() if how == "median" else v.mean())


def run(ctx: StageContext) -> StageResult:
    import numpy as np
    import pandas as pd

    a = ctx.scfg
    states: dict[str, str] = {}
    for st in a.get("wait_for", ["voice", "face"]):
        states[st] = input_state(ctx, st)
        if states[st] == "pending":
            raise RuntimeError(f"{st} has not finished for {ctx.meeting.presser_id}; run it first or remove it "
                               "from aggregate.wait_for")
    turns = io.read_parquet(ctx.out("turns")).sort_values("turn_idx")
    units = io.read_parquet(ctx.out("text_units"))
    sents = io.read_parquet(ctx.out("text_sentences"))
    vcfg, fcfg = a.get("voice", {}) or {}, a.get("face", {}) or {}
    voice, states["voice"] = _optional_table(ctx, "voice", "voice_chunks")
    face, states["face"] = _optional_table(ctx, "face", "face_frames")
    voice = _filter(voice, list(vcfg.get("gate_cols", ["identity_ok"])))
    face_all = face
    face = _filter(face, list(fcfg.get("gate_cols", ["gate_ok", "identity_ok"])))
    vcols = [c for c in vcfg.get("columns", []) if voice is not None and c in voice.columns]
    fcols = _face_cols(ctx, face, fcfg.get("columns", "auto"))
    vstat, fstat = str(vcfg.get("stat", "median")), str(fcfg.get("stat", "mean"))

    segments = list(a.get("segments", ["answer"]))
    chair = turns[turns["is_chair"] & turns["segment_kind"].isin(segments)]
    if not len(chair):
        raise ValueError(f"no chair turns of kinds {segments}")
    stmt = units[units["unit"] == "statement"]
    hawk_stmt = float(stmt["hawk"].iloc[0]) if len(stmt) else math.nan
    stmt_vals = stmt.iloc[0].to_dict() if len(stmt) else {}
    qs = units[units["unit"] == "question"]
    tcols = [c for c in units.columns if c not in TEXT_SKIP]
    gap_cols = [c for c in tcols if c.endswith(("_hawk_share", "_hawk_prob"))] + ["hawk"]
    by_turn = {int(r["turn_idx"]): r for r in units[units["unit"].isin(segments)].to_dict("records")}
    min_h1 = int(a.get("h1_answer_min_words", 40))

    rows = []
    for t in chair.itertuples(index=False):
        ti = int(t.turn_idx)
        r: dict[str, Any] = {"turn_idx": ti, "qa_idx": int(t.qa_idx), "segment_kind": t.segment_kind,
                             "speaker": t.speaker, "t_start_s": float(t.t_start_s), "t_end_s": float(t.t_end_s),
                             "n_words": int(t.n_words), "h1_answer_eligible": int(t.n_words) >= min_h1}
        for c in ("timing_ok", "match_frac", "clock_source"):
            if c in turns.columns:
                r[c] = getattr(t, c)
        u = by_turn.get(ti, {})
        r.update({c: u.get(c, math.nan) for c in tcols})
        r["hawk_statement"] = hawk_stmt
        for c in gap_cols:
            r[f"{c}_gap"] = r.get(c, math.nan) - stmt_vals.get(c, math.nan) if stmt_vals else math.nan
        q = qs[(qs["qa_idx"] == t.qa_idx) & (qs["turn_idx"] < ti)] if t.qa_idx >= 0 else qs.iloc[0:0]
        r["question_turn_idx"] = int(q["turn_idx"].max()) if len(q) else -1
        r["hawk_question"] = float(q["hawk"].mean()) if len(q) else math.nan
        if voice is not None:
            v = voice[voice["turn_idx"] == ti]
            for c in vcols:
                r[f"voice_{c}"] = _stat(v[c], vstat)
            r["voice_n_chunks"] = len(v)
            r["voice_dur_s"] = float(v["dur_s"].sum()) if "dur_s" in v.columns else math.nan
        if face is not None:
            f = face[face["turn_idx"] == ti]
            n_all = int((face_all["turn_idx"] == ti).sum())
            for c in fcols:
                r[f"face_{c}"] = _stat(f[c], fstat)
            r["face_n_frames"], r["face_n_total"] = len(f), n_all
            r["face_ok_frac"] = len(f) / n_all if n_all else math.nan
        r["voice_state"], r["face_state"] = states["voice"], states["face"]
        rows.append(r)
    ans = pd.DataFrame(rows).sort_values("t_end_s").reset_index(drop=True)
    weighting = str(a.get("h1_weighting", "sentence"))
    if weighting not in ("sentence", "answer"):
        raise ValueError("aggregate.h1_weighting must be sentence or answer")
    method = str(units["hawk_method"].dropna().iloc[0]) if units["hawk_method"].notna().any() else "share"
    pp = _primary_prefix(ctx, units)
    inc = sents[sents["unit"].isin(segments) & sents["included"]]
    if weighting == "sentence" and pp:   # A-10: equal sentence weights over the answers that have ended
        sums = {int(k): _sums(g, pp) for k, g in inc.groupby("turn_idx")}
        per = np.array([sums.get(int(k), (0, 0.0, 0.0)) for k in ans["turn_idx"]], dtype=float).reshape(-1, 3)
        num = np.cumsum(per[:, 1] if method == "share" else per[:, 2])
        den = np.cumsum(per[:, 0])
        running = pd.Series(np.where(den > 0, num / np.where(den > 0, den, 1), np.nan))
    else:
        running = ans["hawk"].expanding().mean()   # NaN answers are skipped; only answers ended so far
    ans["hawk_qa_running"] = running
    ans["hawk_gap_running"] = running - hawk_stmt
    ans["n_answers_so_far"] = np.arange(1, len(ans) + 1)
    for c in [c for c in ans.columns if c.endswith("_in_train") or c == "in_classifier_train"]:
        ans[c] = pd.array([None if (isinstance(x, float) and math.isnan(x)) else x for x in ans[c]], dtype="boolean")
    ctx.write_table(ctx.stamp(ans), "answers")

    # ---- meeting row
    m = ctx.meeting
    qa = ans[ans["segment_kind"] == "answer"] if (ans["segment_kind"] == "answer").any() else ans
    notes = (io.read_done(ctx.paths, "turns") or {}).get("notes", {}) or {}
    mr: dict[str, Any] = {
        "t_start_s": float(qa["t_start_s"].min()), "t_end_s": float(qa["t_end_s"].max()),
        "scheduled": m.scheduled, "sep": m.sep, "statement_time_et": m.statement_time_et,
        "presser_start_et": m.presser_start_et, "statement_utc": pd.Timestamp(m.statement_utc),
        "presser_start_utc": pd.Timestamp(m.presser_start_utc), "presser_date": m.presser_date.isoformat(),
        "n_answers": len(qa), "n_answers_h1_eligible": int(qa["h1_answer_eligible"].sum()),
        "n_words_qa": int(qa["n_words"].sum()), "hawk_statement": hawk_stmt,
        "hawk_qa_mean": float(qa["hawk"].mean()), "hawk_question_mean": float(qs["hawk"].mean()) if len(qs) else math.nan,
        "statement_words": int(stmt_vals.get("n_words", 0)) if stmt_vals else None,
        "statement_sentences": int(stmt_vals.get("n_sentences", 0)) if stmt_vals else None,
        "nov_stmt_lex_mean": float(qa["nov_stmt_lex"].mean()) if "nov_stmt_lex" in qa else math.nan,
        "hawk_model": stmt_vals.get("hawk_model") or (qa["hawk_model"].iloc[0] if "hawk_model" in qa else None),
        "stance_model_id": stmt_vals.get("stance_model_id") or (qa["stance_model_id"].iloc[0] if "stance_model_id" in qa else None),
        "voice_state": states["voice"], "face_state": states["face"],
    }
    qa_inc = inc[inc["turn_idx"].isin(set(qa["turn_idx"]))]
    for p in _stance_prefixes(sents):
        n, d_share, d_prob = _sums(qa_inc, p)
        mr[f"{p}_hawk_share_qa_sent"] = d_share / n if n else math.nan
        mr[f"{p}_hawk_prob_qa_sent"] = d_prob / n if n else math.nan
    mr["hawk_qa_answer_mean"] = mr.pop("hawk_qa_mean")
    mr["hawk_qa_sent"] = mr.get(f"{pp}_hawk_{method}_qa_sent", math.nan) if pp else math.nan
    mr["n_sentences_qa"] = len(qa_inc)
    mr["h1_weighting"] = weighting
    mr["hawk_qa_mean"] = mr["hawk_qa_sent"] if weighting == "sentence" else mr["hawk_qa_answer_mean"]
    mr["h1_gap"] = mr["hawk_qa_mean"] - hawk_stmt
    for c in gap_cols:
        if c != "hawk" and c in qa.columns:
            mr[f"{c}_qa_mean"] = float(qa[c].mean())
            level = mr.get(f"{c}_qa_sent", math.nan) if weighting == "sentence" else mr[f"{c}_qa_mean"]
            mr[f"{c}_gap"] = level - stmt_vals.get(c, math.nan) if stmt_vals else math.nan
    for c in ("timing_ok", "match_frac", "wer_proxy", "greeting_media_s", "clock_source"):
        if c in notes:
            mr[f"turns_{c}"] = notes[c]
    if "in_classifier_train" in qa.columns:
        mr["in_classifier_train"] = bool(qa["in_classifier_train"].fillna(False).any())
    qa_turns = set(qa["turn_idx"])
    if voice is not None:
        vq = voice[voice["turn_idx"].isin(qa_turns)]
        for c in vcols:
            mr[f"voice_{c}"] = _stat(vq[c], vstat)
        mr["voice_n_chunks"] = len(vq)
    if face is not None:
        fq = face[face["turn_idx"].isin(qa_turns)]
        for c in fcols:
            mr[f"face_{c}"] = _stat(fq[c], fstat)
        mr["face_n_frames"] = len(fq)
    meet = pd.DataFrame([mr])
    for c in ("statement_utc", "presser_start_utc"):
        meet[c] = meet[c].astype("datetime64[us, UTC]")
    ctx.write_table(ctx.stamp(meet), "meeting")

    # ---- trailing windows
    wins = [float(w) for w in a.get("windows_s", []) or []]
    nwin = 0
    if wins:
        win = _windows(ctx, qa, sents, voice, face, vcols, fcols, vstat, fstat, wins, float(a.get("window_step_s", 10.0)),
                       segments)
        ctx.write_table(ctx.stamp(win), "windows")
        nwin = len(win)
    ctx.result.notes.update({"inputs": states, "n_answers": len(ans), "n_windows": nwin, "voice_columns": vcols,
                             "face_columns": len(fcols), "h1_gap": mr["h1_gap"], "hawk_statement": hawk_stmt})
    return ctx.result


def _stance_prefixes(sents: Any) -> list[str]:
    return [c[: -len("_p_hawkish")] for c in sents.columns if c.endswith("_p_hawkish")]


def _primary_prefix(ctx: StageContext, units: Any) -> str | None:
    if "hawk_model" not in units or not units["hawk_model"].notna().any():
        return None
    key = str(units["hawk_model"].dropna().iloc[0])
    return str(ctx.cfg.model(key).get("prefix") or key)


def _sums(g: Any, p: str) -> tuple[int, float, float]:
    """(sentences, n_hawkish - n_dovish, sum of P(hawkish) - P(dovish)) for included sentences ``g``."""
    if not len(g) or f"{p}_label" not in g:
        return 0, 0.0, 0.0
    lab = g[f"{p}_label"]
    return len(g), float((lab == "hawkish").sum() - (lab == "dovish").sum()), float((g[f"{p}_p_hawkish"] - g[f"{p}_p_dovish"]).sum())


def _windows(ctx: StageContext, qa: Any, sents: Any, voice: Any, face: Any, vcols: list[str], fcols: list[str],
             vstat: str, fstat: str, wins: list[float], step: float, segments: list[str]) -> Any:
    import numpy as np
    import pandas as pd

    t0, t1 = float(qa["t_start_s"].min()), float(qa["t_end_s"].max())
    grid = t0 + step * np.arange(1, int(math.floor((t1 - t0) / step)) + 1)
    hk = str(qa["hawk_model"].dropna().iloc[0]) if "hawk_model" in qa and qa["hawk_model"].notna().any() else None
    p = str(ctx.cfg.model(hk).get("prefix") or hk) if hk else None
    s = sents[sents["unit"].isin(segments) & sents["included"]].sort_values("t_end_s")
    s_end = s["t_end_s"].to_numpy(float)
    v = voice.sort_values("t_end_s") if voice is not None else None
    v_end = v["t_end_s"].to_numpy(float) if v is not None else None
    f = face.sort_values("t_end_s") if face is not None else None
    f_end = f["t_end_s"].to_numpy(float) if f is not None else None
    spans = qa[["t_start_s", "t_end_s"]].to_numpy(float)
    rows = []
    for w in wins:
        for t in grid:
            lo = t - w
            r: dict[str, Any] = {"window_s": w, "t_start_s": lo, "t_end_s": float(t)}
            r["chair_speech_s"] = float(np.clip(np.minimum(spans[:, 1], t) - np.maximum(spans[:, 0], lo), 0, None).sum())
            a, b = np.searchsorted(s_end, lo, side="right"), np.searchsorted(s_end, t, side="right")
            g = s.iloc[a:b]
            r["n_sentences"] = len(g)
            if p and len(g) and f"{p}_label" in g:
                r["hawk_share"] = float(((g[f"{p}_label"] == "hawkish").sum() - (g[f"{p}_label"] == "dovish").sum()) / len(g))
                r["hawk_prob"] = float((g[f"{p}_p_hawkish"] - g[f"{p}_p_dovish"]).mean())
            else:
                r["hawk_share"] = r["hawk_prob"] = math.nan
            if v is not None:
                a, b = np.searchsorted(v_end, lo, side="right"), np.searchsorted(v_end, t, side="right")
                vg = v.iloc[a:b]
                r["voice_n_chunks"] = len(vg)
                for c in vcols:
                    r[f"voice_{c}"] = _stat(vg[c], vstat)
            if f is not None:
                a, b = np.searchsorted(f_end, lo, side="right"), np.searchsorted(f_end, t, side="right")
                fg = f.iloc[a:b]
                r["face_n_frames"] = len(fg)
                for c in fcols:
                    r[f"face_{c}"] = _stat(fg[c], fstat)
            rows.append(r)
    return pd.DataFrame(rows)


def finalize(cfg: Any, meetings: list[Any], log: Log) -> list[Path]:
    """Cross-meeting panel (study and calibration flags, novelty vs the previous presser, causal z files)."""
    from ..dataset import build

    return build(cfg, meetings, log=log)["written"]
