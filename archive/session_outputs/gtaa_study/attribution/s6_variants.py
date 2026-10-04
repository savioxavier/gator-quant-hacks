"""Robustness variants fixed before looking at their results, plus the full variant table of every return series
computed in this study.  Nothing here is used to change S3; any preference must rest on the IS columns only.

  - SMA lookback 6 / 8 / 12 months (10 = S3) for the portfolio and for each ETF sleeve (100 % scale)
  - portfolio with IEF held untimed (time the four risky ETFs only) and with only IEF timed
  - independent long-history check: US market (Ken French Mkt_RF + RF, daily) 10-month SMA filter on month-end
    total-return index, decided at the month-end close, held from the NEXT close (next_close lag), 5 bp per switch;
    1963-07..2004-12 (before our ETF sample) and 2005-01..2024-10 (IS)
Writes out/s6_*.csv and out/variant_table_all.csv."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import lib as L

ohlc, rf = L.data()
close = ohlc["close"][L.TICK]
PER = {"IS": ("2005-11-01", L.IS_END), "OOS": (L.OOS_START, L.OOS_END)}
COMMON_IS_START = "2006-01-03"            # first session at which a 12-month SMA exists for SPY/EFA/IEF/VNQ

rows = []


def add(name, family, net, start=None, note=""):
    net = net.loc[:L.OOS_END]
    if start is not None:
        net = net.loc[start:]
    r = {"variant": name, "family": family, "note": note}
    for p, (lo, hi) in PER.items():
        lo = max(pd.Timestamp(lo), net.index[0])
        st = L.stats(net.loc[lo:hi], rf)
        r.update({f"{p}_start": st["start"], f"{p}_sharpe": st["sharpe"], f"{p}_ann_return": st["ann_return"],
                  f"{p}_ann_vol": st["ann_vol"], f"{p}_max_dd": st["max_drawdown"]})
    rows.append(r)


# ------------------------------------------------ previously computed series (s1, s2) go into the table too
d = pd.read_csv(L.OUT / "s1_daily_net_S3_BH5.csv", index_col=0, parse_dates=True)
add("S3 (frozen, 10m)", "portfolio", d["S3"].dropna())
add("BH5 (frozen)", "portfolio", d["BH5"].dropna())
sl = pd.read_csv(L.OUT / "s3_sleeve_daily_net.csv", index_col=0, parse_dates=True)
for c in sl.columns:
    t, lab, scale = c.split("_")
    add(f"sleeve {t} {lab} 10m x{scale}", "sleeve_10m", sl[c].dropna())

# ------------------------------------------------ lookback grid, portfolio level (same window from 2006-01-03)
for n in (6, 8, 10, 12):
    w = L.sma_decisions(close, n)
    net = L.sim(w, ohlc, rf)
    add(f"portfolio SMA {n}m (window from {COMMON_IS_START})", "portfolio_lookback", net, start=COMMON_IS_START,
        note="10m row = S3 on the shorter window")
add(f"BH5 (window from {COMMON_IS_START})", "portfolio_lookback", d["BH5"].dropna(), start=COMMON_IS_START)

# ------------------------------------------------ lookback grid, per-ETF sleeves at 100 % (same start per ETF)
bh_full = L.sma_decisions(close, 12, timed=set())          # 12-month eligibility = latest of all lookbacks
for t in L.TICK:
    first = bh_full[t].shift(1)
    first = first[first > 0].index[0]
    for n in (6, 8, 10, 12):
        w = L.sma_decisions(close[[t]], n, weight=1.0)
        add(f"sleeve {t} timed {n}m x1.0 (from {first.date()})", "sleeve_lookback", L.sim(w, ohlc, rf), start=first)
    w = L.sma_decisions(close[[t]], 12, timed=set(), weight=1.0)
    add(f"sleeve {t} untimed x1.0 (from {first.date()})", "sleeve_lookback", L.sim(w, ohlc, rf), start=first)

# ------------------------------------------------ partial timing
w = L.sma_decisions(close, 10, timed={"SPY", "EFA", "VNQ", "DBC"})
add("portfolio 10m, IEF untimed (risky four timed)", "portfolio_partial", L.sim(w, ohlc, rf), start="2005-11-01")
w = L.sma_decisions(close, 10, timed={"IEF"})
add("portfolio 10m, only IEF timed", "portfolio_partial", L.sim(w, ohlc, rf), start="2005-11-01")

# ------------------------------------------------ long-history US market check (Ken French daily)
ff = L.E._read_parquet("ff_daily.parquet").set_index("date").sort_index()
ff.index = pd.to_datetime(ff.index)
mkt = ff["Mkt_RF"] + ff["RF"]
idx = (1 + mkt).cumprod()
cal = ff.index
mo = L.CU.month_offsets(cal)
me = mo.index[mo["off_own"] == 0]
mi = idx.loc[me]
sma = mi.rolling(10, min_periods=10).mean()
sig = ((mi > sma) & sma.notna()).astype(float)
elig = sma.notna().astype(float)
lr = []
for lab, s in (("timed", sig), ("untimed", elig)):
    wd = pd.Series(np.nan, index=cal)
    wd.loc[me] = s.values
    wd = wd.ffill().fillna(0.0)
    held = wd.shift(2).fillna(0.0)                # next_close: decided at close d, held from the close of d+1
    trade = held.diff().abs().fillna(0.0)
    net = held * mkt + (1 - held) * ff["RF"] - trade * 5e-4
    ex = net - ff["RF"]
    for plab, lo, hi in (("1964-2004", "1964-05-01", "2004-12-31"), ("2005-2024IS", "2005-11-01", L.IS_END),
                         ("1964-2024IS", "1964-05-01", L.IS_END)):
        e = ex.loc[lo:hi]
        n_ = net.loc[lo:hi]
        lr.append({"sleeve": lab, "window": plab, "sharpe": float(L.sr_of(e.to_numpy())),
                   "ann_return": float((1 + n_).prod() ** (252 / len(n_)) - 1), "ann_vol": float(n_.std() * math.sqrt(252)),
                   "max_dd": L.E.max_drawdown(n_), "frac_invested": float(held.loc[lo:hi].mean()),
                   "switches_per_year": float(trade.loc[lo:hi].sum() / (len(n_) / 252))})
    if lab == "timed":
        ex_t = ex
    else:
        ex_u = ex
lrdf = pd.DataFrame(lr)
boot = []
for plab, lo, hi in (("1964-2004", "1964-05-01", "2004-12-31"), ("1964-2024IS", "1964-05-01", L.IS_END)):
    res = L.paired_bootstrap(ex_t.loc[lo:hi], ex_u.loc[lo:hi], block=63, reps=5000, seed=5)
    boot.append({"window": plab, "d_sr": res["d_sr"], "d_sr_ci95": res["d_sr_ci95"], "p_le_0": res["p_boot_d_sr_le_0"],
                 "d_mean_excess_ann": res["d_mean_excess_ann"], "d_mean_ci95": res["d_mean_excess_ci95"]})
    # concentration: share of the cumulative excess-return difference from the 3 best calendar years
    dd = (ex_t - ex_u).loc[lo:hi]
    yr = dd.groupby(dd.index.year).sum().sort_values(ascending=False)
    boot[-1]["sum_diff"] = float(dd.sum())
    boot[-1]["top3_years"] = {int(k): float(v) for k, v in yr.head(3).items()}
    boot[-1]["sum_diff_ex_top3_years"] = float(yr.iloc[3:].sum())
    boot[-1]["years_timing_helped_frac"] = float((yr > 0).mean())
lrdf.to_csv(L.OUT / "s6_long_history_us_market.csv", index=False)
pd.DataFrame(boot).to_csv(L.OUT / "s6_long_history_bootstrap.csv", index=False)
for lab, s in (("timed", ex_t), ("untimed", ex_u)):
    rows.append({"variant": f"US market (FF) {lab} 10m, next_close, 5bp", "family": "long_history",
                 "note": "IS_* = 1964-05..2004-12, OOS_* = 2005-11..2024-10 (both pre-OOS); see s6_long_history_us_market.csv",
                 "IS_sharpe": float(L.sr_of(s.loc["1964-05-01":"2004-12-31"].to_numpy())),
                 "OOS_sharpe": float(L.sr_of(s.loc["2005-11-01":L.IS_END].to_numpy()))})

table = pd.DataFrame(rows)
table.to_csv(L.OUT / "variant_table_all.csv", index=False)
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_colwidth", 60)
print(table[["variant", "IS_sharpe", "OOS_sharpe", "IS_ann_return", "OOS_ann_return", "IS_max_dd", "OOS_max_dd"]].round(3).to_string(index=False))
print(lrdf.round(3).to_string(index=False))
print(pd.DataFrame(boot).to_string(index=False))
print("variants:", len(table))
