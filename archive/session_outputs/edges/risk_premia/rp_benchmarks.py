"""Daily excess returns of the yardsticks used for correlations: F_ES (raw), forward2 S1 trend, forward F2."""
from __future__ import annotations

import rp_core as R  # noqa: F401  (disables logging, sets sys.path)
from src import engine as E
from src import forward, forward2

import pandas as pd


def main() -> None:
    R.OUT.mkdir(exist_ok=True)
    rf = E.load_rf("FWD")
    ohlc = E.load_ohlc(["F_ES"], "FWD")
    es = ohlc["close"]["F_ES"].pct_change(fill_method=None) - rf.reindex(ohlc["close"].index).ffill()
    s1 = forward2.returns("S1", "FWD")
    s1 = s1 - rf.reindex(s1.index).ffill()
    f2 = forward.returns("F2", "FWD")
    f2 = f2 - rf.reindex(f2.index).ffill()
    out = pd.DataFrame({"ES": es, "S1": s1, "F2": f2})
    out.to_parquet(R.OUT / "benchmarks.parquet")
    print(out.describe().T)


if __name__ == "__main__":
    main()
