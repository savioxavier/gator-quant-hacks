"""Causal per-chair baselines, applied at analysis time (never inside per-meeting outputs).

For meeting m, the baseline of a feature is computed only from meetings that come strictly before m in the
given order (default: meeting-level known_at) and, by default, have the same chair. Rows of m itself are never
in its own baseline. A meeting with fewer than ``burn_in`` earlier same-chair meetings gets NaN (team plan:
4-meeting burn-in). Robust statistics by default: z = (x - median) / max(1.4826 * MAD, sqrt(variance_floor)).

    from fedpress.baselines import causal_z
    z = causal_z(answers, ["voice_arousal", "face_ex_valence"], order=meetings.sort_values("known_at").presser_id)
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np

MAD_TO_SD = 1.4826


def meeting_order(df: Any, meeting_col: str = "presser_id", order_col: str = "known_at") -> list[str]:
    """Meetings sorted by their last ``order_col`` value (ties broken by id)."""
    last = df.groupby(meeting_col)[order_col].max().reset_index()
    return last.sort_values([order_col, meeting_col])[meeting_col].astype(str).tolist()


def _center_scale(values: np.ndarray, robust: bool, variance_floor: float) -> tuple[float, float]:
    v = values[~np.isnan(values)]
    if not len(v):
        return math.nan, math.nan
    floor = math.sqrt(variance_floor)
    if robust:
        med = float(np.median(v))
        return med, max(MAD_TO_SD * float(np.median(np.abs(v - med))), floor)
    return float(v.mean()), max(float(v.std(ddof=1)) if len(v) > 1 else 0.0, floor)


def causal_z(df: Any, cols: Iterable[str], *, order: Sequence[str] | None = None, meeting_col: str = "presser_id",
             group_cols: Sequence[str] = ("chair",), order_col: str = "known_at", burn_in: int = 4,
             variance_floor: float = 1e-6, robust: bool = True, pool: str = "rows", prefix: str = "z_") -> Any:
    """Copy of ``df`` with ``<prefix><col>`` z-scores and ``baseline_n_meetings`` (earlier meetings used).

    order: meeting ids in time order (default: by each meeting's last ``order_col``). Meetings missing from
        ``order`` get NaN.
    pool: ``rows`` (all rows of the earlier meetings form the reference distribution) or ``meeting_means``
        (one mean per earlier meeting).
    """
    if pool not in ("rows", "meeting_means"):
        raise ValueError("pool must be rows or meeting_means")
    cols = [c for c in cols if c in df.columns]
    out = df.copy()
    ids = out[meeting_col].astype(str)
    order = [str(x) for x in (order if order is not None else meeting_order(out, meeting_col, order_col))]
    rank = {m: i for i, m in enumerate(order)}
    for c in cols:
        out[prefix + c] = np.nan
    out["baseline_n_meetings"] = np.nan
    groups = [((), out.index)] if not group_cols else list(out.groupby(list(group_cols), dropna=False).groups.items())
    for _, index in groups:
        sub = out.loc[index]
        sub_ids = ids.loc[index]
        mids = sorted({m for m in sub_ids if m in rank}, key=rank.__getitem__)
        for k, m in enumerate(mids):
            rows_m = sub.index[sub_ids == m]
            out.loc[rows_m, "baseline_n_meetings"] = k
            if k < burn_in:
                continue
            prior = sub[sub_ids.isin(mids[:k])]
            for c in cols:
                vals = prior[c].astype(float)
                ref = (vals.groupby(sub_ids.loc[prior.index]).mean() if pool == "meeting_means" else vals).to_numpy()
                center, scale = _center_scale(ref, robust, variance_floor)
                out.loc[rows_m, prefix + c] = (out.loc[rows_m, c].astype(float) - center) / scale
    return out
