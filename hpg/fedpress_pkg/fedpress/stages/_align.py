"""Transcript words <- timed words (ASR words or caption words): global token alignment, gap filling, quality.

The team plan's clock rule is "PDF = words; ASR = time". Each transcript word takes the times of the timed word
it aligns with (normalised tokens, minimum-edit alignment over the whole meeting). One-to-one substitutions
(e.g. "1/4" vs "quarter") also lend their times. Words without a partner are placed between their timed
neighbours in proportion to their length. The edit counts give a WER proxy against the edited transcript.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

_STRIP = ".,;:!?\"'()[]{}$*"


@dataclass(frozen=True)
class Timed:
    word: str
    start: float
    end: float
    prob: float = float("nan")


@dataclass
class Alignment:
    start: np.ndarray            # per transcript word, media seconds
    end: np.ndarray
    matched: np.ndarray          # every token of the word matched exactly
    timed_by: np.ndarray         # match | sub | interp
    prob: np.ndarray             # mean probability of the partner words (ASR), NaN otherwise
    stats: dict[str, Any] = field(default_factory=dict)


def norm_tokens(word: str) -> list[str]:
    """Lower-case comparison tokens: punctuation stripped, hyphens/dashes split, %, fractions and thousands
    separators normalised."""
    w = word.lower().replace("\u2019", "'").replace("\u2018", "'")
    for a, b in (("%", " percent "), ("\xbc", " 1/4 "), ("\xbd", " 1/2 "), ("\xbe", " 3/4 "), ("&", " and ")):
        w = w.replace(a, b)
    w = re.sub(r"(?<=\d),(?=\d{3})", "", w)
    w = re.sub(r"--+|\u2014|\u2013|(?<=[a-z])-(?=[a-z])", " ", w)
    return [t for t in (x.strip(_STRIP) for x in w.split()) if t]


def _flatten(words: Sequence[str]) -> tuple[list[str], list[int]]:
    toks: list[str] = []
    owner: list[int] = []
    for i, w in enumerate(words):
        for t in norm_tokens(w):
            toks.append(t)
            owner.append(i)
    return toks, owner


def opcodes(a: list[str], b: list[str]) -> list[tuple[str, int, int, int, int]]:
    """Minimum-edit opcodes between two token lists (rapidfuzz; difflib as a slower fallback)."""
    try:
        from rapidfuzz.distance import Levenshtein

        return [(o.tag, o.src_start, o.src_end, o.dest_start, o.dest_end) for o in Levenshtein.opcodes(a, b)]
    except ImportError:
        from difflib import SequenceMatcher

        return list(SequenceMatcher(None, a, b, autojunk=False).get_opcodes())


def align(ref_words: Sequence[str], hyp: Sequence[Timed], max_sub_run: int = 3) -> Alignment:
    """Times for ``ref_words`` from ``hyp``. Untimed words are then filled by :func:`fill`."""
    n = len(ref_words)
    rt, rown = _flatten(ref_words)
    ht, hown = _flatten([h.word for h in hyp])
    start, end = np.full(n, np.nan), np.full(n, np.nan)
    psum, pcnt = np.zeros(n), np.zeros(n)
    tok_total = np.bincount(np.asarray(rown, dtype=int), minlength=n) if rown else np.zeros(n, dtype=int)
    tok_match = np.zeros(n, dtype=int)
    sub = np.zeros(n, dtype=bool)
    n_sub = n_del = n_ins = 0
    for tag, i1, i2, j1, j2 in opcodes(rt, ht) if rt and ht else []:
        if tag == "replace":
            n_sub += min(i2 - i1, j2 - j1)
            n_del += max(0, (i2 - i1) - (j2 - j1))
            n_ins += max(0, (j2 - j1) - (i2 - i1))
        elif tag == "delete":
            n_del += i2 - i1
        elif tag == "insert":
            n_ins += j2 - j1
        if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1 and i2 - i1 <= max_sub_run):
            for i, j in zip(range(i1, i2), range(j1, j2)):
                r, h = rown[i], hyp[hown[j]]
                start[r] = h.start if np.isnan(start[r]) else min(start[r], h.start)
                end[r] = h.end if np.isnan(end[r]) else max(end[r], h.end)
                if not np.isnan(h.prob):
                    psum[r] += h.prob
                    pcnt[r] += 1
                if tag == "equal":
                    tok_match[r] += 1
                else:
                    sub[r] = True
    if not rt:
        n_del = 0
    elif not ht:
        n_del = len(rt)
    matched = (tok_total > 0) & (tok_match == tok_total)
    timed_by = np.where(matched, "match", np.where(~np.isnan(start), "sub", "interp")).astype(object)
    with np.errstate(invalid="ignore", divide="ignore"):
        prob = np.where(pcnt > 0, psum / np.maximum(pcnt, 1), np.nan)
    stats = {"n_ref_words": n, "n_ref_tokens": len(rt), "n_hyp_tokens": len(ht),
             "subs": n_sub, "dels": n_del, "ins": n_ins,
             "wer_proxy": round((n_sub + n_del + n_ins) / max(1, len(rt)), 4),
             "match_frac": round(float(matched.mean()) if n else 0.0, 4),
             "timed_frac": round(float((~np.isnan(start)).mean()) if n else 0.0, 4)}
    return fill(Alignment(start, end, matched, timed_by, prob, stats), ref_words)


def fill(al: Alignment, words: Sequence[str]) -> Alignment:
    """Place untimed words between timed neighbours by character share; extrapolate at the edges with the
    median seconds per character; make starts non-decreasing."""
    s, e = al.start.copy(), al.end.copy()
    n = len(s)
    have = ~np.isnan(s)
    if n == 0 or not have.any():
        raise ValueError("alignment produced no timed words")
    w = np.array([max(1, len(x)) + 1 for x in words], dtype=float)
    spc = float(np.nanmedian((e[have] - s[have]) / w[have])) if have.sum() else 0.06
    spc = spc if np.isfinite(spc) and spc > 0 else 0.06
    idx = np.flatnonzero(have)
    first, last = idx[0], idx[-1]
    t = s[first]
    for i in range(first - 1, -1, -1):  # leading edge
        e[i] = t
        s[i] = t = max(0.0, t - spc * w[i])
    t = e[last]
    for i in range(last + 1, n):  # trailing edge
        s[i] = t
        e[i] = t = t + spc * w[i]
    for a, b in zip(idx[:-1], idx[1:]):  # interior gaps
        if b - a <= 1:
            continue
        lo, hi = e[a], max(e[a], s[b])
        seg = w[a + 1:b]
        cum = np.concatenate([[0.0], np.cumsum(seg)]) / seg.sum()
        s[a + 1:b] = lo + (hi - lo) * cum[:-1]
        e[a + 1:b] = lo + (hi - lo) * cum[1:]
    s = np.maximum.accumulate(s)
    e = np.maximum(e, s)
    return Alignment(s, e, al.matched, al.timed_by, al.prob, al.stats)


def compare(a: Alignment, b: Alignment) -> dict[str, Any]:
    """Start-time agreement of two clocks on words both matched exactly (e.g. ASR vs official captions)."""
    both = a.matched & b.matched
    if not both.any():
        return {"n_words": 0}
    d = a.start[both] - b.start[both]
    return {"n_words": int(both.sum()), "median_offset_s": round(float(np.median(d)), 3),
            "median_abs_s": round(float(np.median(np.abs(d))), 3),
            "p90_abs_s": round(float(np.quantile(np.abs(d), 0.9)), 3)}
