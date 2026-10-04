"""Boundary runs of run_forward2.evaluate on SYNTHETIC data (1, 2, 3, 63 forward days) and a live test of
_weekly_corr on a random series (proves the yfinance path returns a number when data exist)."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, sys.argv[1])
sys.path.insert(0, os.path.join(sys.argv[1], "scripts"))
import numpy as np
import pandas as pd

from src import config as C
from src import engine as E
import run_forward2 as R2

assert "synth" in str(C.DATA_DIR)
tmp = Path(tempfile.mkdtemp(prefix="ft2_boundary_", dir=sys.argv[2]))
C.FWD_DIR = tmp
R2.LOG = tmp / "forward2_log.csv"
_orig = E.data_end
cal = E.trading_calendar("FWD")
fwd = cal[cal >= pd.Timestamp(C.FWD_START)]
for n in (0, 1, 2, 3, 62, 63):
    D = str(cal[cal < pd.Timestamp(C.FWD_START)][-1].date()) if n == 0 else str(fwd[n - 1].date())
    E.data_end = lambda p, D=D: D if p == "FWD" else _orig(p)
    try:
        R2.evaluate()
        print(f"n={n} D={D}: OK, files {sorted(x.name for x in tmp.iterdir())}")
    except Exception as exc:
        print(f"n={n} D={D}: CRASH {type(exc).__name__}: {exc}")
E.data_end = _orig
print(open(R2.LOG).read()[:600])

idx = pd.bdate_range("2025-01-02", "2025-12-31")
a = pd.Series(np.random.default_rng(1).normal(0, 0.01, len(idx)), index=idx)
print("weekly corr random vs DBMF:", R2._weekly_corr(a, "DBMF"), "| AQMIX:", R2._weekly_corr(a, "AQMIX"))
