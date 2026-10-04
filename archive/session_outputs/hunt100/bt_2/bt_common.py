"""Shared helpers for the bt_2 re-backtests (read-only use of the repo engine; nothing logged, results/ untouched).

Conventions (hunt100 trend_momentum SPEC common conventions):
* decisions at the close of the last NYSE session of each month with data through that close; filled at the
  next session's close (engine exec="next_close"), so the position earns from the second session on;
* returns are daily excess returns of the F_ total-return index (index return minus 3-month T-bill);
* sigma_i = sqrt(252 * EWMA(r^2, com=60)), min 60 obs; risk unit = 0.40/sigma_i/N_eligible;
* "book to 10%" = rescale the weight vector so its trailing-252-session sample covariance (min 60 obs) gives
  10% annualised ex-ante volatility, gross <= 3;
* eligibility = >= 260 sessions of history, positive sigma, traded (volume > 0) in the last 10 sessions;
* costs: realistic one-way bp map of the hunt task, 2x stress; roll days add one round trip (engine).
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<solo-repo>")
sys.path.insert(0, str(REPO))
os.environ.setdefault("GQH_DATA_DIR", "<home>/.cache/gqh")
assert os.environ.get("GQH_OOS_UNLOCK") != "1", "never unlock OOS"

from src import calendar_utils as CU  # noqa: E402
from src import engine as E  # noqa: E402

BT = Path(__file__).resolve().parent
SERIES = BT.parent / "series"
SERIES.mkdir(parents=True, exist_ok=True)

P = "FWD"
IS_END = pd.Timestamp("2024-10-02")
LATER_START = pd.Timestamp("2024-10-03")
LATER_END = pd.Timestamp("2026-10-02")
TD = 252

ROOTS = ["ES", "NQ", "RTY", "YM", "ZT", "ZF", "ZN", "ZB", "UB", "CL", "HO", "RB", "NG", "GC", "SI", "PL",
         "HG", "ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE", "6E", "6J", "6B", "6A", "6C", "6S"]
TICKERS = [f"F_{r}" for r in ROOTS]
CLASSES = {
    "equity": ["F_ES", "F_NQ", "F_RTY", "F_YM"],
    "rates": ["F_ZT", "F_ZF", "F_ZN", "F_ZB", "F_UB"],
    "fx": ["F_6E", "F_6J", "F_6B", "F_6A", "F_6C", "F_6S"],
    "commodities": ["F_CL", "F_HO", "F_RB", "F_NG", "F_GC", "F_SI", "F_PL", "F_HG", "F_ZC", "F_ZS", "F_ZW",
                    "F_ZL", "F_ZM", "F_LE", "F_HE"],
}

_REAL = {"ES": 1.0, "NQ": 1.0, "YM": 1.0, "RTY": 2.0, "ZT": 0.5, "ZF": 0.7, "ZN": 1.0, "ZB": 1.5, "UB": 1.5,
         "6E": 1.0, "6J": 1.0, "6B": 1.0, "6A": 1.0, "6C": 1.0, "6S": 1.0,
         "CL": 2.0, "GC": 2.0, "SI": 2.0, "HG": 2.0, "NG": 3.0, "HO": 3.0, "RB": 3.0, "PL": 3.0,
         "ZC": 4.0, "ZS": 4.0, "ZW": 4.0, "ZL": 4.0, "ZM": 4.0, "LE": 4.0, "HE": 4.0}
COST_TEXT = ("realistic one-way bp per unit notional: ES/NQ/YM 1, RTY 2, ZT 0.5, ZF 0.7, ZN 1, ZB/UB 1.5, FX 1, "
             "CL/GC/SI/HG 2, NG/HO/RB/PL 3, grains/livestock 4; roll days add one round trip; net_2x doubles every cost")

EWMA_COM = 60
COV_WINDOW = 252
MIN_HISTORY = 260
ACTIVE_WINDOW = 10
RAW_SCALE = 0.40
TARGET_VOL = 0.10
GROSS_CAP = 3.0


def cost_map(tickers, mult=1.0):
    return {t: _REAL[t[2:]] * mult for t in tickers}


def month_ends(cal: pd.DatetimeIndex) -> pd.DatetimeIndex:
    mo = CU.month_offsets(cal)
    return mo.index[mo["off_own"] == 0]


class Panel:
    """Futures panel on the NYSE calendar for the whole FWD data range (strategies use trailing data only)."""

    def __init__(self, tickers=None):
        self.tickers = list(tickers or TICKERS)
        self.ohlc = E.load_ohlc(self.tickers, P)
        self.rf = E.load_rf(P).reindex(self.ohlc["close"].index).ffill().fillna(0.0)
        close = self.ohlc["close"]
        self.close = close
        self.ret = close.pct_change(fill_method=None)
        self.ex = self.ret.sub(self.rf, axis=0)
        self.vol = np.sqrt(self.ex.pow(2).ewm(com=EWMA_COM, min_periods=60).mean() * TD)
        traded = (self.ohlc["volume"].fillna(0.0) > 0).astype(float)
        self.active = traded.rolling(ACTIVE_WINDOW, min_periods=1).max().astype(bool)
        self.counts = self.ex.notna().cumsum()
        self.idx = self.ex.index
        self.me = month_ends(self.idx)

    def eligible(self, t, cols=None) -> list[str]:
        cols = cols or self.tickers
        return [c for c in cols if self.counts.loc[t, c] >= MIN_HISTORY and np.isfinite(self.vol.loc[t, c])
                and self.vol.loc[t, c] > 0 and bool(self.active.loc[t, c])]


def book_to_target(w: pd.Series, ex_hist: pd.DataFrame, target=TARGET_VOL, gross_cap=GROSS_CAP) -> pd.Series:
    cols = [c for c in w.index if w[c] != 0 and np.isfinite(w[c])]
    if not cols:
        return w * 0.0
    cov = ex_hist[cols].tail(COV_WINDOW).cov(min_periods=60).fillna(0.0).to_numpy()
    v = w[cols].to_numpy()
    var = float(v @ cov @ v) * TD
    if not np.isfinite(var) or var <= 0:
        return w * 0.0
    w = w * (target / math.sqrt(var))
    g = w.abs().sum()
    return w * (gross_cap / g) if g > gross_cap else w


def ex_ante_vol(w: pd.Series, ex_hist: pd.DataFrame) -> float:
    cols = [c for c in w.index if w[c] != 0]
    if not cols:
        return 0.0
    cov = ex_hist[cols].tail(COV_WINDOW).cov(min_periods=60).fillna(0.0).to_numpy()
    v = w[cols].to_numpy()
    return math.sqrt(max(float(v @ cov @ v) * TD, 0.0))


def simulate3(w_dec: pd.DataFrame, exec_="next_close"):
    """Return (excess df with net_1x/net_2x/gross, turnover series, held weights) over the FWD range."""
    tick = list(w_dec.columns)
    ohlc = E.load_ohlc(tick, P)
    rf = E.load_rf(P)
    n1, g, to, held, _ = E.simulate(w_dec, ohlc, rf, exec=exec_, cost_bps=cost_map(tick, 1.0))
    n2, *_ = E.simulate(w_dec, ohlc, rf, exec=exec_, cost_bps=cost_map(tick, 2.0))
    rfa = rf.reindex(n1.index).ffill().fillna(0.0)
    df = pd.DataFrame({"net_1x": n1 - rfa, "net_2x": n2 - rfa, "gross": g - rfa})
    live = held.abs().sum(axis=1) > 0
    first = live.idxmax()
    return df.loc[first:], to.loc[first:], held.loc[first:]


# ----------------------------------------------------------------------------------------------- statistics

def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(TD)) if len(x) > 20 and x.std() > 0 else float("nan")


def maxdd(x: pd.Series) -> float:
    eq = (1 + x.fillna(0.0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


def yearly(x: pd.Series) -> pd.Series:
    g = x.groupby(x.index.year)
    y = g.apply(lambda s: (1 + s).prod() - 1)
    n = g.size()
    return y[n >= 126]          # calendar years with at least half a year of data


def corr_d(a: pd.Series, b: pd.Series) -> float:
    df = pd.concat([a, b], axis=1).dropna()
    return float(df.corr().iloc[0, 1]) if len(df) > 60 else float("nan")


_REFS = None


def refs() -> pd.DataFrame:
    """Daily excess returns of ES (F_ES index), S1 (forward2) and F2 (forward), cached in bt_2/refs.parquet."""
    global _REFS
    if _REFS is not None:
        return _REFS
    path = BT / "refs.parquet"
    if path.exists():
        _REFS = pd.read_parquet(path)
        return _REFS
    from src import forward as F
    from src import forward2 as F2
    rf = E.load_rf(P)
    s1 = F2.returns("S1", P)
    f2 = F.returns("F2", P)
    pan = Panel(["F_ES"])
    out = pd.DataFrame({
        "ES": pan.ex["F_ES"],
        "S1": s1 - rf.reindex(s1.index).ffill().fillna(0.0),
        "F2": f2 - rf.reindex(f2.index).ffill().fillna(0.0),
    })
    out.to_parquet(path)
    _REFS = out
    return out


def window_stats(df: pd.DataFrame, turnover: pd.Series, held: pd.DataFrame, start, end) -> dict:
    sl = slice(pd.Timestamp(start), pd.Timestamp(end))
    n1, n2, gr = df["net_1x"].loc[sl], df["net_2x"].loc[sl], df["gross"].loc[sl]
    to, h = turnover.loc[sl], held.loc[sl]
    yrs = len(n1) / TD
    y = yearly(n1)
    roll = (n1.rolling(504).mean() / n1.rolling(504).std() * math.sqrt(TD)).dropna()
    R = refs()
    out = {
        "start": str(n1.index[0].date()), "end": str(n1.index[-1].date()), "years": round(yrs, 2),
        "net_sharpe_1x": sharpe(n1), "net_sharpe_2x": sharpe(n2), "gross_sharpe": sharpe(gr),
        "ann_mean_excess": float(n1.mean() * TD),
        "ann_return_excess_cagr": float((1 + n1).prod() ** (1 / yrs) - 1) if yrs > 0 else float("nan"),
        "ann_vol": float(n1.std() * math.sqrt(TD)),
        "max_dd": maxdd(n1),
        "worst_year": float(y.min()) if len(y) else float("nan"),
        "worst_year_label": int(y.idxmin()) if len(y) else None,
        "pct_positive_years": float((y > 0).mean()) if len(y) else float("nan"),
        "n_years_counted": int(len(y)),
        "rolling2y_p10": float(roll.quantile(0.10)) if len(roll) else float("nan"),
        "turnover_per_year": float(to.sum() / yrs) if yrs > 0 else float("nan"),
        "mean_gross_leverage": float(h.abs().sum(axis=1).mean()),
        "nw_t": E.newey_west_tstat(n1),
        "skew": float(n1.skew()),
        "corr_es": corr_d(n1, R["ES"].loc[sl]),
        "corr_s1": corr_d(n1, R["S1"].loc[sl]),
        "corr_f2": corr_d(n1, R["F2"].loc[sl]),
    }
    return out


def full_report(df, turnover, held) -> dict:
    start = df.index[0]
    return {"IS": window_stats(df, turnover, held, start, IS_END),
            "LATER": window_stats(df, turnover, held, LATER_START, LATER_END)}


def save_series(sid: str, df: pd.DataFrame, meta: dict, folder: Path | None = None, name: str | None = None):
    """Standard series: daily excess returns net_1x, net_2x, gross (+ sidecar JSON)."""
    folder = folder or SERIES
    name = name or sid
    folder.mkdir(parents=True, exist_ok=True)
    df[["net_1x", "net_2x", "gross"]].to_parquet(folder / f"{name}.parquet")
    with open(folder / f"{name}.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, default=str)


def jdump(obj, path: Path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=lambda o: None if (isinstance(o, float) and not np.isfinite(o)) else str(o))


# ----------------------------------------------------------------------------------------------- builders

def risk_unit_book(pan: "Panel", xfun, cols=None, diag: dict | None = None) -> pd.DataFrame:
    """Monthly decisions: x = xfun(t, eligible) (Series over a subset of eligible), w_i = x_i 0.40/sigma_i/N_eligible,
    book to 10% ex-ante vol (trailing 252-session covariance), gross <= 3. Returns forward-filled decision weights."""
    cols = list(cols or pan.tickers)
    w_dec = pd.DataFrame(np.nan, index=pan.idx, columns=cols)
    caps = 0
    nmon = 0
    for t in pan.me:
        elig = pan.eligible(t, cols)
        w = pd.Series(0.0, index=cols)
        if elig:
            x = xfun(t, elig)
            x = x.reindex(elig).fillna(0.0)
            w[elig] = x * (RAW_SCALE / pan.vol.loc[t, elig]) / len(elig)
            w_unc = book_to_target(w, pan.ex.loc[:t], gross_cap=np.inf)
            w = book_to_target(w, pan.ex.loc[:t])
            nmon += 1
            caps += int(w_unc.abs().sum() > GROSS_CAP + 1e-9)
        w_dec.loc[t] = w.values
    if diag is not None:
        diag["months"] = nmon
        diag["gross_cap_binding_frac"] = caps / max(nmon, 1)
    return w_dec.ffill().fillna(0.0)


def excess_index(pan: "Panel") -> pd.DataFrame:
    """Cumulative excess-return index per instrument (NaN before its first close)."""
    ex = pan.ex.copy()
    first = pan.close.apply(lambda s: s.first_valid_index())
    I = (1 + ex.fillna(0.0)).cumprod()
    for c in I.columns:
        I.loc[I.index < first[c], c] = np.nan
    return I
