"""Dictionary features: Loughran-McDonald category counts, hedge phrases and the TDW keyword filter.

* Loughran-McDonald Master Dictionary: free for academic use, downloaded by hand (no redistribution here).
  The CSV has a ``Word`` column and one column per category whose value is the year the word was added
  (> 0 = member; 0 or negative = not a member).
* Hedge phrases come from ``text.hedges.phrases`` (config), matched on lower-case word sequences.
* TDW filter: the keyword rule Shah, Paturi and Chava (ACL 2023) applied before labelling (dictionaries A1/B1).
  Amendment A-10 keeps it as a labelled robustness column, not as the default inclusion rule.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")
TDW_FILTER_TERMS: tuple[str, ...] = (
    "inflation expectation", "interest rate", "bank rate", "fund rate", "price", "economic activity", "inflation",
    "employment", "unemployment", "growth", "exchange rate", "productivity", "deficit", "demand", "job market",
    "monetary policy",
)


def words(text: str) -> list[str]:
    return WORD.findall(text.lower())


def tdw_filter(text: str) -> bool:
    """True when the sentence contains one of the TDW A1/B1 keywords (substring match, as in the paper)."""
    low = text.lower()
    return any(t in low for t in TDW_FILTER_TERMS)


def category_key(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


@dataclass
class LMDictionary:
    """Word sets per Loughran-McDonald category (keys normalised: 'StrongModal' == 'Strong_Modal')."""

    path: Path
    categories: dict[str, frozenset[str]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path, wanted: Sequence[str]) -> "LMDictionary":
        p = Path(path)
        with p.open(encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            cols = {category_key(c): c for c in reader.fieldnames or []}
            if "word" not in cols:
                raise ValueError(f"{p}: no 'Word' column; is this the Loughran-McDonald master dictionary CSV?")
            missing = [w for w in wanted if category_key(w) not in cols]
            if missing:
                raise ValueError(f"{p}: categories {missing} not in columns {list(cols.values())}")
            sets: dict[str, set[str]] = {category_key(w): set() for w in wanted}
            for row in reader:
                word = (row[cols["word"]] or "").strip().lower()
                if not word:
                    continue
                for k in sets:
                    try:
                        if float(row[cols[k]] or 0) > 0:
                            sets[k].add(word)
                    except ValueError:
                        continue
        return cls(p, {k: frozenset(v) for k, v in sets.items()})

    def counts(self, toks: Iterable[str]) -> dict[str, int]:
        toks = list(toks)
        return {k: sum(t in s for t in toks) for k, s in self.categories.items()}


class HedgeMatcher:
    """Counts non-overlapping occurrences of multi-word hedge phrases in a token sequence."""

    def __init__(self, phrases: Sequence[str]) -> None:
        pats = sorted({tuple(words(p)) for p in phrases if words(p)}, key=len, reverse=True)
        self.phrases: tuple[tuple[str, ...], ...] = tuple(pats)

    def count(self, toks: Sequence[str]) -> int:
        n, i = 0, 0
        while i < len(toks):
            for p in self.phrases:
                if tuple(toks[i : i + len(p)]) == p:
                    n += 1
                    i += len(p)
                    break
            else:
                i += 1
        return n
