"""Independent data layer for the auction-cycle verification (no repo strategy code)."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

D = Path("<home>/.cache/gqh")
SP = Path("<scratch>")
OUT = SP / "auction" / "verify"
TICK = ["F_ZT", "F_ZF", "F_ZN", "F_ZB", "F_UB", "F_ES"]
STD = [2, 3, 5, 7, 10, 20, 30]


def calendar():
    e = pd.read_parquet(D / "etf_daily.parquet", columns=["date", "ticker"])
    return pd.DatetimeIndex(sorted(e.loc[e.ticker == "SPY", "date"].unique()))


def returns():
    cal = calendar()
    f = pd.read_parquet(D / "futures_daily.parquet")
    f = f[f.ticker.isin(TICK)]
    close = f.pivot(index="date", columns="ticker", values="close").reindex(cal)[TICK]
    roll = f.pivot(index="date", columns="ticker", values="roll").reindex(cal)[TICK].fillna(0.0)
    rf = pd.read_parquet(D / "rf_daily.parquet")
    if "date" in rf.columns:
        rf = rf.set_index("date")
    rf.index = pd.to_datetime(rf.index)
    rf = rf["rf"].reindex(cal).ffill().fillna(0.0)
    first = close["F_ZN"].first_valid_index()
    cal = cal[cal >= first]
    close, roll, rf = close.loc[cal], roll.loc[cal], rf.loc[cal]
    rex = close.pct_change(fill_method=None).sub(rf, axis=0)
    rex.iloc[0] = np.nan
    return cal, rex, roll, rf


def term_years(s):
    y = re.search(r"(\d+)-Year", s)
    m = re.search(r"(\d+)-Month", s)
    return (int(y.group(1)) if y else 0) + (int(m.group(1)) / 12 if m else 0)


def auctions():
    a = pd.read_parquet(D / "treasury_auctions.parquet")
    a = a[a.security_type.isin(["Note", "Bond"]) & a.high_yield.notna()].copy()   # FRNs have no high yield
    a["yrs"] = a.security_term.map(term_years)
    a["term"] = a.yrs.map(lambda y: min(STD, key=lambda t: abs(t - y)))
    a["oterm"] = a.original_security_term.map(term_years).map(lambda y: min(STD, key=lambda t: abs(t - y)))
    # TIPS: auction yield well below the FRED nominal curve at the same remaining maturity (median per CUSIP)
    fr = pd.read_parquet(D / "fred_daily.parquet").set_index("date")[["DGS2", "DGS10", "DGS30"]].ffill().dropna()
    fr.index = pd.to_datetime(fr.index)
    lv = fr.reindex(a.auction_date, method="ffill").to_numpy()
    mat = (a.maturity_date - a.auction_date).dt.days.to_numpy() / 365.25
    a["gap"] = [np.interp(m, [2, 10, 30], c) - y for m, c, y in zip(mat, lv, a.high_yield)]
    a["tips"] = a.groupby("cusip")["gap"].transform("median") > 0.6
    a = a[~a.tips].drop_duplicates(["term", "auction_date"]).sort_values("auction_date").reset_index(drop=True)
    return a


def index_events(a, cal):
    tail = pd.bdate_range(cal[-1] + pd.Timedelta(days=1), periods=30)
    calx = cal.append(tail)
    a = a.copy()
    a["A"] = calx.searchsorted(a.auction_date.values)
    a["on"] = calx[np.clip(a.A, 0, len(calx) - 1)].values == a.auction_date.values
    a["N"] = calx.searchsorted(a.announcemt_date.values)          # first session on/after announcement
    a["dom"] = a.auction_date.dt.day
    a["tom"] = (a.dom >= 25) | (a.dom <= 5)
    return a, calx
