"""Benchmark excess-return series used for correlations: ES (F_ES excess), S1 (forward test 2 broad trend),
F2 (forward test 1 futures ensemble). Read-only use of the frozen repo code; nothing is logged or written to the repo."""
import os
import sys
from pathlib import Path

import pandas as pd

REPO = Path("<solo-repo>")
sys.path.insert(0, str(REPO))
os.environ.setdefault("GQH_DATA_DIR", "<home>/.cache/gqh")
assert os.environ.get("GQH_OOS_UNLOCK") != "1"

from src import engine as E  # noqa: E402
from src import forward, forward2  # noqa: E402

OUT = Path(__file__).resolve().parent

rf = E.load_rf("FWD")
s1 = forward2.returns("S1", "FWD")
f2 = forward.returns("F2", "FWD")
es = E.load_ohlc(["F_ES"], "FWD")["close"]["F_ES"].pct_change(fill_method=None)
idx = s1.index
rf = rf.reindex(idx).ffill().fillna(0.0)
df = pd.DataFrame({
    "ES": es.reindex(idx) - rf,
    "S1": s1 - rf,
    "F2": f2.reindex(idx) - rf,
})
df.to_parquet(OUT / "bench_excess.parquet")
print(df.describe().T)
print(df.dropna().index.min(), df.index.max())
