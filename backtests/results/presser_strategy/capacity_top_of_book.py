"""Capacity check: displayed top-of-book size at each fill second, compared with the N contracts of the sizing rule.

Reads the licensed bbo-1s file (GQH_MARKET_DIR) for sizes only, with the suite's quote rule (ADDENDUM 1.3: last record
with ts_recv <= t, skipping crossed, locked or one-sided records). Writes sizes in contracts and ratios; no price is
written. Changes no position, trade or P&L. Run after build_presser_strategy.py, from the repository root:
    PY=<python> GQH_MARKET_DIR=<folder with bbo-1s__all_2016_2026.parquet> \
    $PY backtests/results/presser_strategy/capacity_top_of_book.py
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
H1DIR = REPO / "backtests/results/presser_h1"
MARKET = Path(os.environ.get("GQH_MARKET_DIR", str(Path(os.environ.get("GQH_DATA_DIR", Path.home() / ".cache/gqh"))
                                                     / "presser")))
TZ = "America/New_York"
IS_END = "2024-10-02"

q = pd.read_parquet(MARKET / "bbo-1s__all_2016_2026.parquet",
                    columns=["ts_recv", "bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00", "symbol"])
ok = (q.bid_px_00 > 0) & (q.ask_px_00 > 0) & (q.ask_px_00 > q.bid_px_00) & (q.bid_sz_00 > 0) & (q.ask_sz_00 > 0)
q = q[ok].drop(columns=["bid_px_00", "ask_px_00"])
q["sym"] = q.symbol.str[:2]
q["date"] = q.ts_recv.dt.tz_convert(TZ).dt.strftime("%Y-%m-%d")
G = {}
for k, v in q.groupby(["date", "sym"]):
    v = v.sort_values("ts_recv")
    G[k] = (v.ts_recv.values.astype("datetime64[ns]").astype(np.int64), v.bid_sz_00.values, v.ask_sz_00.values)


def size_at(date, sym, t):
    k = (date, sym)
    if k not in G:
        return np.nan, np.nan
    ts, bs, as_ = G[k]
    i = int(np.searchsorted(ts, t.tz_convert("UTC").value, "right")) - 1
    return (np.nan, np.nan) if i < 0 else (float(bs[i]), float(as_[i]))


trades = []
h1 = pd.read_csv(H1DIR / "h1primary_trades.csv", dtype={"date": str})
h1 = h1[(h1.signal == "H1") & (h1.clock == "primary") & (h1.exit == "exit_1600")]
for r in h1.itertuples():
    trades.append(("H1-primary", r.sym, r.date, r.pos, r.entry_ts, r.exit_ts, 60))
for s in ["ZT", "ZN", "ES"]:
    b = pd.read_csv(H1DIR / "tables" / f"benchr_per_meeting_{s}.csv", dtype={"date": str})
    for r in b.itertuples():
        trades.append(("BENCH-R", s, r.date, r.pos, r.entry_ts, r.exit_ts, 0))
rows = []
for st, s, d, pos, e, x, xoff in trades:
    if s == "ZF":
        continue
    te = pd.Timestamp(e)
    tx = pd.Timestamp(x) + pd.Timedelta(seconds=xoff)  # suite rule: a 1m close fills at bar start + 60 s
    be, ae = size_at(d, s, te)
    bx, ax = size_at(d, s, tx)
    rows.append(dict(strategy=st, sym=s, date=d, window="IS" if d <= IS_END else "OOS",
                     entry_size_taken=ae if pos > 0 else be, exit_size_taken=bx if pos > 0 else ax))
C = pd.DataFrame(rows)
N = pd.read_csv(HERE / "sizing.csv").set_index(["strategy", "sym"]).N
out = []
for (st, s, w), g in pd.concat([C, C.assign(window="all")]).groupby(["strategy", "sym", "window"]):
    n_c = int(N.loc[(st, s)])
    for leg in ["entry", "exit"]:
        v = g[f"{leg}_size_taken"].dropna()
        out.append(dict(strategy=st, sym=s, window=w, leg=leg, n_trades=len(v), N_contracts=n_c,
                        median_displayed_size=v.median(), p10=v.quantile(0.1), p90=v.quantile(0.9),
                        N_over_median=n_c / v.median(), share_fills_with_size_ge_N=(v >= n_c).mean()))
pd.DataFrame(out).to_csv(HERE / "capacity_top_of_book.csv", index=False, float_format="%.4g")
print(pd.DataFrame(out).to_string())
