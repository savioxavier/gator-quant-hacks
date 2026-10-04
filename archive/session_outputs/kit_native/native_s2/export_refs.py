"""Scratch: engine references for the native S1/S2 check (period FWD only, nothing logged)."""
import sys
from pathlib import Path

ROOT = Path("<solo-repo>")
sys.path.insert(0, str(ROOT))
from src import engine as E      # noqa: E402
from src import forward2 as F2   # noqa: E402
from src import calendar_utils as CU  # noqa: E402

out = Path(__file__).resolve().parent
ohlc = E.load_ohlc(F2.S1_TICKERS, "FWD")
rf = E.load_rf("FWD")
mo = CU.month_offsets(ohlc["close"].index)
me = mo.index[mo["off_own"] == 0]
for name, fn in (("S2", F2.s2_decisions), ("S1", F2.s1_decisions)):
    w = fn("FWD")
    w.loc[me].rename_axis("date").to_csv(out / f"{name.lower()}_dec.csv")
    official = F2.returns(name, "FWD")
    official.rename("ret").rename_axis("date").to_csv(out / f"{name.lower()}_official.csv")
    for tag, bps in (("guide", 10.0), ("nocost", 0.0)):
        net, *_ = E.simulate(w, ohlc, rf, exec="next_close", cost_bps={t: bps for t in F2.S1_TICKERS})
        net.rename("ret").rename_axis("date").to_csv(out / f"{name.lower()}_engine_{tag}.csv")
    net, _, to, held, cost = E.simulate(w, ohlc, rf, exec="next_close", cost_bps=F2.S1_COST_BPS)
    print(name, "max |official - project sim| =", float((net - official).abs().max()),
          "first held", held.index[held.abs().sum(axis=1) > 0][0].date(), "turnover/yr", float(to.mean() * 252))
