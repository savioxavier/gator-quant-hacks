"""Benchmark daily excess returns used for correlations: ES16 / F_ES excess, S1 (forward2), F2 (forward).

Writes bench.parquet next to this file. Uses the frozen repository code read-only (no logging, no results/ writes).
Run from the repository root with GQH_DATA_DIR set.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO = Path("<solo-repo>")
sys.path.insert(0, str(REPO))
from src import engine as E  # noqa: E402
from src import forward, forward2  # noqa: E402

OUT = Path(__file__).resolve().parent / "bench.parquet"


def main() -> None:
    rf = E.load_rf("FWD")
    ohlc = E.load_ohlc(["ES16", "F_ES", "ZN16", "F_ZN"], "FWD")
    close = ohlc["close"]
    rfi = rf.reindex(close.index).ffill().fillna(0.0)
    ex = close.pct_change(fill_method=None).sub(rfi, axis=0)
    out = pd.DataFrame({"ES16": ex["ES16"], "F_ES": ex["F_ES"], "ZN16": ex["ZN16"], "F_ZN": ex["F_ZN"]})
    s1 = forward2.returns("S1", "FWD")
    out["S1"] = s1 - rf.reindex(s1.index).ffill().fillna(0.0)
    f2 = forward.returns("F2", "FWD")
    out["F2"] = f2 - rf.reindex(f2.index).ffill().fillna(0.0)
    out.to_parquet(OUT)
    print(out.dropna(how="all").describe().T.to_string())
    print("->", OUT)


if __name__ == "__main__":
    main()
