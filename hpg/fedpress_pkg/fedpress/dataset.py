"""Dataset builder: concatenate the per-meeting feature tables into <root>/panel/ and add the cross-meeting
columns that need earlier meetings (never later ones).

Written by ``python -m fedpress.cli aggregate --all`` (finalize) or ``aggregate --all --finalize``:

* panel/answers.parquet, panel/windows.parquet, panel/text_units.parquet: all meetings, with
  ``calibration_only`` (2011-2015 calibration pressers, ``sample.calibration_window``) and ``in_study``.
* panel/meetings.parquet: the policy-meeting calendar of the configured windows (88 meetings for 2016-01..2026-10)
  left-joined to the presser features (``has_presser``, ``held`` from manifest/meetings.csv).
* Novelty vs the previous presser (``aggregate.novelty_prev``): ``nov_prev_lex`` per answer (answer vs the
  previous presser's pooled chair answers) and per meeting, ``stmt_nov_prev_lex`` (statement vs the previous
  statement), and ``*_emb`` versions when the text stage stored embeddings. The previous presser is the
  preceding row of the manifest (any chair unless ``same_chair``); if its text outputs are missing the value
  is NaN rather than a comparison with an older meeting.
* panel/answers_causal_z.parquet, panel/meetings_causal_z.parquet (``aggregate.baselines.write_panel``):
  ``z_<col>`` from :func:`fedpress.baselines.causal_z`, ordered by meeting known_at, same chair, burn-in and
  variance floor from ``aggregate.baselines``. Raw values stay in the files above.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from . import io
from . import manifest as mf
from .baselines import causal_z, meeting_order
from .config import Config
from .log import Log
from .nlp import vectors

Z_EXCLUDE = ("_n_", "_state", "n_chunks", "n_frames", "n_total", "dur_s", "_frac", "face_h_px")


def _concat(cfg: Config, meetings: list[mf.Meeting], key: str) -> Any:
    import pandas as pd

    parts = []
    for m in meetings:
        p = io.MeetingPaths.of(cfg, m.presser_id).file(key)
        if p.exists():
            parts.append(io.read_parquet(p))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def _flags(df: Any) -> Any:
    if len(df) and "sample_role" in df.columns:
        df["calibration_only"] = df["sample_role"].eq("calibration")
        df["in_study"] = df["sample_role"].eq("study")
    return df


def _previous(cfg: Config, same_chair: bool) -> dict[str, str | None]:
    rows = mf.load(cfg)
    prev: dict[str, str | None] = {}
    for i, m in enumerate(rows):
        cands = [r for r in rows[:i] if (r.chair == m.chair or not same_chair)]
        prev[m.presser_id] = cands[-1].presser_id if cands else None
    return prev


def _vectors(cfg: Config, pid: str) -> Any:
    p = io.MeetingPaths.of(cfg, pid).file("text_vectors")
    return io.read_parquet(p) if p.exists() else None


def _pooled(vec: Any, unit: str) -> tuple[dict[int, float], list[float] | None]:
    v = vec[vec["unit"] == unit]
    tf = vectors.pool(vectors.from_lists(i, x) for i, x in zip(v["tf_idx"], v["tf_val"]))
    emb = vectors.dense_mean(list(v["emb"])) if "emb" in v.columns else None
    return tf, emb


def novelty_prev(cfg: Config, answers: Any, meetings_df: Any) -> tuple[Any, Any]:
    """Add nov_prev_* columns (answers and meetings) using only the previous presser's text."""
    ncfg = cfg.section("aggregate").get("novelty_prev", {}) or {}
    if not ncfg.get("enabled", True) or not len(answers):
        return answers, meetings_df
    prev = _previous(cfg, bool(ncfg.get("same_chair", False)))
    cache: dict[str, Any] = {}

    def vec(pid: str | None) -> Any:
        if pid is None:
            return None
        if pid not in cache:
            cache[pid] = _vectors(cfg, pid)
        return cache[pid]

    answers = answers.copy()
    meetings_df = meetings_df.copy()
    for col in ("prev_presser_id", "nov_prev_lex", "nov_prev_emb"):
        answers[col] = None if col == "prev_presser_id" else math.nan
    for col in ("prev_presser_id", "nov_prev_lex", "nov_prev_emb", "stmt_nov_prev_lex", "stmt_nov_prev_emb"):
        meetings_df[col] = None if col == "prev_presser_id" else math.nan
    for pid in answers["presser_id"].astype(str).unique():
        cur, pv = vec(pid), vec(prev.get(pid))
        mrow = meetings_df["presser_id"].astype(str) == pid
        arow = answers["presser_id"].astype(str) == pid
        answers.loc[arow, "prev_presser_id"] = prev.get(pid)
        meetings_df.loc[mrow, "prev_presser_id"] = prev.get(pid)
        if cur is None or pv is None:
            continue
        p_tf, p_emb = _pooled(pv, "answer")
        c_tf, c_emb = _pooled(cur, "answer")
        meetings_df.loc[mrow, "nov_prev_lex"] = vectors.novelty(c_tf, p_tf)
        s_cur, s_prev = _pooled(cur, "statement"), _pooled(pv, "statement")
        meetings_df.loc[mrow, "stmt_nov_prev_lex"] = vectors.novelty(s_cur[0], s_prev[0])
        if c_emb is not None and p_emb is not None:
            meetings_df.loc[mrow, "nov_prev_emb"] = 1.0 - vectors.dense_cosine(c_emb, p_emb)
        if s_cur[1] is not None and s_prev[1] is not None:
            meetings_df.loc[mrow, "stmt_nov_prev_emb"] = 1.0 - vectors.dense_cosine(s_cur[1], s_prev[1])
        by_turn = {int(r.turn_idx): r for r in cur[cur["unit"] == "answer"].itertuples(index=False)}
        for i in answers.index[arow]:
            r = by_turn.get(int(answers.at[i, "turn_idx"]))
            if r is None:
                continue
            answers.at[i, "nov_prev_lex"] = vectors.novelty(vectors.from_lists(r.tf_idx, r.tf_val), p_tf)
            if p_emb is not None and getattr(r, "emb", None) is not None:
                answers.at[i, "nov_prev_emb"] = 1.0 - vectors.dense_cosine(r.emb, p_emb)
    return answers, meetings_df


def _calendar(cfg: Config) -> Any:
    import pandas as pd

    cal = pd.DataFrame(mf.load_calendar(cfg))
    if not len(cal):
        return cal
    windows = [("study", "study_window")]
    if cfg.get("sample.include_calibration", False):
        windows.append(("calibration", "calibration_window"))
    keep = pd.Series(False, index=cal.index)
    for _, key in windows:
        a, b = str(cfg.get(f"sample.{key}.start")), str(cfg.get(f"sample.{key}.end"))
        keep |= (cal["meeting_date"] >= a) & (cal["meeting_date"] <= b)
    for c in ("has_presser", "held", "sep", "in_default_sample"):
        if c in cal.columns:
            cal[c] = cal[c].astype(str).str.lower().eq("true")
    # scheduled meetings plus unscheduled ones that had a presser (2020-03-02/03 and 2020-03-15): the team's 88
    cal = cal[keep & ((cal["kind"] == "scheduled") | ((cal["kind"] == "unscheduled") & cal["has_presser"]))].copy()
    return cal.rename(columns={"presser_date": "cal_presser_date", "chair": "cal_chair", "sep": "cal_sep",
                               "statement_url": "cal_statement_url"})


def z_columns(df: Any, wanted: Any) -> list[str]:
    """Columns that get causal z-scores: ``auto`` = numeric voice_*/face_* features (no counts/states) plus
    the text levels listed in ``aggregate.baselines.text_columns``."""
    import pandas as pd

    if wanted not in (None, "auto"):
        return [c for c in wanted if c in df.columns]
    return [c for c in df.columns if c.startswith(("voice_", "face_")) and pd.api.types.is_numeric_dtype(df[c])
            and not any(x in c for x in Z_EXCLUDE)]


def build(cfg: Config, meetings: list[mf.Meeting] | None = None, *, log: Log | None = None,
          write: bool = True) -> dict[str, Any]:
    """Panel tables for ``meetings`` (default: the configured sample). Returns the frames and written paths."""
    meetings = mf.sample(cfg) if meetings is None else meetings
    answers = _flags(_concat(cfg, meetings, "answers"))
    meet = _flags(_concat(cfg, meetings, "meeting"))
    windows = _flags(_concat(cfg, meetings, "windows"))
    units = _flags(_concat(cfg, meetings, "text_units"))
    answers, meet = novelty_prev(cfg, answers, meet)
    cal = _calendar(cfg)
    if len(cal) and len(meet):
        panel_meetings = cal.merge(meet, on="meeting_date", how="left", suffixes=("", "_feat"))
    else:
        panel_meetings = meet
    out: dict[str, Any] = {"answers": answers, "meetings": panel_meetings, "windows": windows, "text_units": units,
                           "written": []}
    bcfg = cfg.section("aggregate").get("baselines", {}) or {}
    if bcfg.get("write_panel", True) and len(meet):
        order = meeting_order(meet, "presser_id", "known_at")
        kw = {"order": order, "group_cols": ("chair",) if bcfg.get("same_chair", True) else (),
              "burn_in": int(bcfg.get("burn_in_meetings", 4)), "variance_floor": float(bcfg.get("variance_floor", 1e-6)),
              "robust": bool(bcfg.get("robust", True)), "pool": str(bcfg.get("pool", "rows"))}
        text_cols = list(bcfg.get("text_columns", []))
        out["answers_causal_z"] = causal_z(answers, z_columns(answers, bcfg.get("columns", "auto")) + text_cols, **kw)
        out["meetings_causal_z"] = causal_z(meet, z_columns(meet, bcfg.get("columns", "auto"))
                                            + [c for c in bcfg.get("meeting_text_columns", []) if c in meet.columns],
                                            **{**kw, "pool": "rows"})
    if write:
        root = cfg.root_path("panel")
        meta = {"config_hash": cfg.hash, "created_utc": io.utc_now(), "meetings": len(meetings),
                "with_features": int(meet["presser_id"].nunique()) if len(meet) else 0}
        for name in ("answers", "meetings", "windows", "text_units", "answers_causal_z", "meetings_causal_z"):
            df = out.get(name)
            if df is not None and len(df):
                out["written"].append(io.write_parquet(df, root / f"{name}.parquet", meta))
        missing = sorted({m.presser_id for m in meetings} - set(meet["presser_id"].astype(str) if len(meet) else []))
        out["written"].append(io.atomic_write_json(root / "dataset_meta.json", {**meta, "missing_meetings": missing}))
        if log:
            log.info("dataset.built", answers=len(answers), meetings=len(panel_meetings), missing=len(missing))
    return out


def load_panel(cfg: Config, name: str = "answers") -> Any:
    """Read one panel table (answers, meetings, windows, text_units, answers_causal_z, meetings_causal_z)."""
    return io.read_parquet(cfg.root_path("panel") / f"{name}.parquet")


def paths(cfg: Config) -> list[Path]:
    return sorted(cfg.root_path("panel").glob("*.parquet"))
