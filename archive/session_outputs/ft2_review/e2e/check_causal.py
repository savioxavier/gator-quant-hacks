"""Truncation test on SYNTHETIC data: decisions (and returns, compared only as equality) for dates <= D
must not change when the data after D are removed. Nothing is printed except max abs differences."""
import sys

sys.path.insert(0, sys.argv[1])
import pandas as pd

from src import config as C
from src import engine as E
from src import forward2 as F2

assert "synth" in str(C.DATA_DIR), C.DATA_DIR
_orig = E.data_end
full = {n: F2.SPECS[n][0]("FWD") for n in F2.SPECS}
full_ret = {n: F2.returns(n, "FWD") for n in F2.SPECS}
for D in ["2026-10-30", "2026-11-25", "2026-11-30", "2026-12-31", "2027-01-04"]:
    E.data_end = lambda p, D=D: D if p == "FWD" else _orig(p)
    out = []
    for n in F2.SPECS:
        w = F2.SPECS[n][0]("FWD")
        dw = float((w - full[n].loc[:D]).abs().max().max())
        r = F2.returns(n, "FWD")
        dr = float((r - full_ret[n].loc[:D]).abs().max())
        out.append(f"{n}: dec {dw:.1e} ret {dr:.1e} last {w.index[-1].date()}")
    print(D, " | ".join(out))
E.data_end = _orig
