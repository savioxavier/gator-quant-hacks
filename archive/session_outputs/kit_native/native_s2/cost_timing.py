"""Scratch: is the extra next_close gap at higher costs only the day the trade cost is booked?
backtrader books a Close fill's commission (and the harness its slippage) on the fill bar d+1; the engine charges
that trade on d+2, the first day held. Rolls land on the same day in both. Shift the engine's trade costs one day
earlier and compare again."""
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("<solo-repo>")
sys.path.insert(0, str(ROOT))
from src import engine as E      # noqa: E402
from src import forward2 as F2   # noqa: E402

S = Path(__file__).resolve().parent
ohlc = E.load_ohlc(F2.S1_TICKERS, "FWD")
noroll = dict(ohlc, roll=ohlc["roll"] * 0.0)
rf = E.load_rf("FWD")
rfc = rf.reindex(ohlc["close"].index).ffill().fillna(0.0)
WIN = {"IS": ("2011-09-02", "2024-10-02"), "OOS": ("2024-10-03", "2026-10-02")}


def stats(a, b):
    j = pd.concat([a, b], axis=1, join="inner").dropna()
    return float(j.iloc[:, 0].corr(j.iloc[:, 1])), float((j.iloc[:, 0] - j.iloc[:, 1]).abs().mean() * 1e4)


def sharpe(x):
    return float(x.mean() / x.std(ddof=1) * math.sqrt(252))


for book, fn in (("s2", F2.s2_decisions), ("s1", F2.s1_decisions)):
    w = fn("FWD")
    for tag, bps in (("project", F2.S1_COST_BPS), ("guide", {t: 10.0 for t in F2.S1_TICKERS})):
        net, gross, _, _, cost = E.simulate(w, ohlc, rf, exec="next_close", cost_bps=bps)
        _, _, _, _, trade_cost = E.simulate(w, noroll, rf, exec="next_close", cost_bps=bps)
        shifted = gross - (cost - trade_cost) - trade_cost.shift(-1).fillna(0.0)
        nat = pd.read_csv(S / f"{book}_close_{tag}.csv", index_col=0, parse_dates=True)["excess"]
        for win, (lo, hi) in WIN.items():
            c0, d0 = stats(nat.loc[lo:hi], (net - rfc).loc[lo:hi])
            c1, d1 = stats(nat.loc[lo:hi], (shifted - rfc).loc[lo:hi])
            print(f"{book} {tag:7s} {win:3s} engine as is: corr {c0:.5f} {d0:.3f} bp | trade cost on the fill day: "
                  f"corr {c1:.5f} {d1:.3f} bp | Sharpe native {sharpe(nat.loc[lo:hi]):.4f} engine "
                  f"{sharpe((net - rfc).loc[lo:hi]):.4f} shifted {sharpe((shifted - rfc).loc[lo:hi]):.4f}")
