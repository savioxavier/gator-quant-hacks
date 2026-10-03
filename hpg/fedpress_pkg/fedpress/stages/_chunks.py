"""Causal chunking of turns into analysis windows, and interval coverage.

Every window lies inside one turn and is defined only by times up to its own end, so a window's features never
depend on later audio.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

import numpy as np

if TYPE_CHECKING:
    import pandas as pd

CHUNK_COLUMNS = ("chunk_idx", "turn_idx", "qa_idx", "role", "segment_kind", "t_start_s", "t_end_s", "dur_s")


def windows(t0: float, t1: float, size: float, hop: float, min_len: float,
            merge_tail: bool = False) -> list[tuple[float, float]]:
    """Consecutive windows of ``size`` every ``hop`` seconds within [t0, t1]. A final window shorter than
    ``min_len`` is dropped, or with ``merge_tail`` (non-overlapping windows) joined to the previous window so
    the windows tile the whole span."""
    out: list[tuple[float, float]] = []
    a = float(t0)
    while a < t1 - 1e-9:
        b = min(a + size, float(t1))
        if b - a >= min_len - 1e-9:
            out.append((a, b))
        elif merge_tail and out and hop >= size:
            out[-1] = (out[-1][0], b)
        if b >= t1:
            break
        a += hop
    return out


def word_windows(starts: np.ndarray, ends: np.ndarray, target: float, min_len: float, max_len: float,
                 pause_s: float) -> list[tuple[float, float]]:
    """Windows cut at word boundaries: close a window at a pause >= ``pause_s`` once it is ``min_len`` long, or at
    the first word end past ``target``; never longer than ``max_len`` (a long word run is split by time)."""
    out: list[tuple[float, float]] = []
    if len(starts) == 0:
        return out
    a = float(starts[0])
    for i in range(len(starts)):
        b = float(ends[i])
        gap = float(starts[i + 1]) - b if i + 1 < len(starts) else np.inf
        dur = b - a
        if dur >= max_len:
            out.extend(windows(a, b, max_len, max_len, min_len))
            a = float(starts[i + 1]) if i + 1 < len(starts) else b
        elif (dur >= min_len and gap >= pause_s) or dur >= target or i + 1 == len(starts):
            if dur >= min_len:
                out.append((a, b))
            if i + 1 < len(starts):
                a = float(starts[i + 1])
    return out


def turn_chunks(turns: "pd.DataFrame", size: float, hop: float, min_len: float, kinds: Iterable[str] | None = None,
                not_before: float | None = None, words: "pd.DataFrame | None" = None, mode: str = "fixed",
                max_len: float = 15.0, pause_s: float = 0.6, merge_tail: bool = False) -> "pd.DataFrame":
    """Chunk table for the selected turns (``kinds`` = segment kinds; ``not_before`` drops windows that start
    earlier, e.g. before enrolment ends). mode 'fixed' = time windows, 'words' = word-boundary windows."""
    import pandas as pd

    sel = turns if kinds is None else turns[turns["segment_kind"].isin(list(kinds))]
    rows = []
    for t in sel.itertuples(index=False):
        if mode == "words" and words is not None:
            w = words[words["turn_idx"] == t.turn_idx].sort_values("t_start_s")
            spans = word_windows(w["t_start_s"].to_numpy(), w["t_end_s"].to_numpy(), size, min_len, max_len, pause_s)
        else:
            spans = windows(t.t_start_s, t.t_end_s, size, hop, min_len, merge_tail)
        for a, b in spans:
            if not_before is not None and a < not_before - 1e-6:
                continue
            rows.append((int(t.turn_idx), int(t.qa_idx), t.role, t.segment_kind, a, b, b - a))
    df = pd.DataFrame(rows, columns=list(CHUNK_COLUMNS[1:]))
    df.insert(0, "chunk_idx", np.arange(len(df), dtype=int))
    return df.astype({"t_start_s": "float64", "t_end_s": "float64", "dur_s": "float64"})


def coverage(spans: np.ndarray, cover: np.ndarray) -> np.ndarray:
    """Fraction of each [a, b] row of ``spans`` covered by the union of the ``cover`` intervals."""
    out = np.zeros(len(spans))
    if len(cover) == 0 or len(spans) == 0:
        return out
    cover = cover[np.argsort(cover[:, 0])]
    merged: list[list[float]] = []
    for a, b in cover:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([float(a), float(b)])
    m = np.asarray(merged)
    for k, (a, b) in enumerate(spans):
        if b <= a:
            continue
        lo, hi = np.maximum(m[:, 0], a), np.minimum(m[:, 1], b)
        out[k] = float(np.clip(hi - lo, 0, None).sum() / (b - a))
    return out
