"""Scratch: independent agreement numbers for native S1/S2 from the harness series and freshly simulated engine refs."""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<solo-repo>")
sys.path.insert(0, str(ROOT))
from src import engine as E
from src import forward2 as F2

NS = Path(__file__).resolve().parents[1] / "native_s2"
V = Path(__file__).resolve().parent
ohlc = E.load_ohlc(F2.S1_TICKERS, "FWD")
rf = E.load_rf("FWD").reindex(ohlc["close"].index).ffill().fillna(0.0)
W = {"IS": ("2011-09-02", "2024-10-02"), "OOS": ("2024-10-03", "2026-10-02")}


def sh(x, ddof):
    return x.mean() / x.std(ddof=ddof) * math.sqrt(252)


refs = {}
for name, fn in (("S2", F2.s2_decisions), ("S1", F2.s1_decisions)):
    w = fn("FWD")
    off = F2.returns(name, "FWD")
    g, *_ = E.simulate(w, ohlc, rf, exec="next_close", cost_bps={t: 10.0 for t in F2.S1_TICKERS})
    z, *_ = E.simulate(w, ohlc, rf, exec="next_close", cost_bps={t: 0.0 for t in F2.S1_TICKERS})
    refs[name] = {"project": off, "guide": g, "none": z}
    for k, r in refs[name].items():
        for win, (a, b) in W.items():
            x = r.loc[a:b]
            print(f"engine {name} {k:7s} {win}: ours {sh(x - rf.loc[x.index], 1):.4f} kit-on-total {sh(x, 0):.4f}")

rows = []
for b in ("s2", "s1"):
    for run, ref in (("close_project", "project"), ("close_guide", "guide"), ("close_guide_literal", "project"),
                     ("close_none", "none"), ("coc_project", "project"), ("coc_guide", "guide")):
        s = pd.read_csv(NS / f"{b}_{run}.csv", index_col=0, parse_dates=True)
        ex_mine = s["ret"] - s["net_weight"] * rf.reindex(s.index)
        assert float((ex_mine - s["excess"]).abs().max()) < 1e-15
        R = refs[b.upper()][ref]
        for win, (lo, hi) in W.items():
            x = s.loc[lo:hi]
            e = ex_mine.loc[lo:hi]
            re = (R - rf).loc[x.index]
            d = e - re
            rows.append(dict(run=f"{b}_{run}", ref=ref, win=win, n=len(x), kit=sh(x["ret"], 0), ours=sh(e, 1),
                             ref_ours=sh(re, 1), corr=e.corr(re), mad_bp=d.abs().mean() * 1e4,
                             ann=(1 + x["ret"]).prod() ** (252 / len(x)) - 1,
                             mdd=float(((1 + x["ret"]).cumprod() / (1 + x["ret"]).cumprod().cummax() - 1).min())))
df = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(df.round(4).to_string(index=False))

# cost-day shift diagnostic (S2 project): engine trade costs moved one day earlier
w = F2.s2_decisions("FWD")
net, gross, to, held, cost = E.simulate(w, ohlc, rf, exec="next_close", cost_bps=F2.S1_COST_BPS)
s = pd.read_csv(NS / "s2_close_project.csv", index_col=0, parse_dates=True)
e = s["ret"] - s["net_weight"] * rf.reindex(s.index)
roll = ohlc["roll"][F2.S1_TICKERS].fillna(0.0)
cb = pd.Series(F2.S1_COST_BPS) / 1e4
roll_cost = (2 * held.abs() * roll * cb).sum(axis=1)
trade_cost = cost - roll_cost
shifted = gross - roll_cost - trade_cost.shift(-1).fillna(0.0)
for win, (lo, hi) in W.items():
    a, r = e.loc[lo:hi], (shifted - rf).loc[lo:hi]
    print(f"S2 project cost-shifted {win}: corr {a.corr(r):.5f} mad {((a - r).abs().mean() * 1e4):.3f} bp ref ours {sh(r, 1):.4f}")
