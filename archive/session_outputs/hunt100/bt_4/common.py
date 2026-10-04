"""Shared helpers for the bt_4 re-backtests (scratch only; never writes to the repo)."""
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
assert os.environ.get("GQH_OOS_UNLOCK") != "1", "never unlock OOS"

from src import config as C  # noqa: E402
from src import engine as E  # noqa: E402
from src import calendar_utils as CU  # noqa: E402

HERE = Path(__file__).resolve().parent
SERIES = HERE.parent / "series"
SERIES.mkdir(parents=True, exist_ok=True)
IS_END = pd.Timestamp(C.IS_END)
LATER_START = pd.Timestamp(C.OOS_START)

EWMA_COM = 60
COV_WINDOW = 252
MIN_HIST = 260
ACTIVE_WINDOW = 10
TARGET_VOL = 0.10

FUT_COST = {
    "F_ES": 1.0, "F_NQ": 1.0, "F_YM": 1.0, "F_RTY": 2.0, "F_ZT": 0.5, "F_ZF": 0.7, "F_ZN": 1.0,
    "F_ZB": 1.5, "F_UB": 1.5, "F_6E": 1.0, "F_6J": 1.0, "F_6B": 1.0, "F_6A": 1.0, "F_6C": 1.0, "F_6S": 1.0,
    "F_CL": 2.0, "F_GC": 2.0, "F_SI": 2.0, "F_HG": 2.0, "F_NG": 3.0, "F_HO": 3.0, "F_RB": 3.0, "F_PL": 3.0,
    "F_ZC": 4.0, "F_ZS": 4.0, "F_ZW": 4.0, "F_ZL": 4.0, "F_ZM": 4.0, "F_LE": 4.0, "F_HE": 4.0,
}


def cost_map(tickers):
    return {t: (FUT_COST[t] if C.is_future(t) else C.cost_bps(t)) for t in tickers}


def panel(tickers, period="FWD"):
    ohlc = E.load_ohlc(tickers, period)
    rf = E.load_rf(period).reindex(ohlc["close"].index).ffill().fillna(0.0)
    ret = ohlc["close"].pct_change(fill_method=None)
    ex = ret.sub(rf, axis=0)
    return ohlc, rf, ex


def ewma_vol(ex):
    return np.sqrt(ex.pow(2).ewm(com=EWMA_COM, min_periods=60).mean() * 252)


def eligibility(ohlc, ex, vol):
    counts = ex.notna().cumsum()
    traded = (ohlc["volume"].fillna(0.0) > 0).astype(float).rolling(ACTIVE_WINDOW, min_periods=1).max() > 0
    has_close = ohlc["close"].notna()
    return (counts >= MIN_HIST) & np.isfinite(vol) & (vol > 0) & traded & has_close


def scale_to_target(w: pd.Series, ex_hist: pd.DataFrame, gross_cap: float, target=TARGET_VOL) -> pd.Series:
    cols = [c for c in w.index if w[c] != 0 and np.isfinite(w[c])]
    if not cols:
        return w * 0.0
    cov = ex_hist[cols].tail(COV_WINDOW).cov(min_periods=60).fillna(0.0).to_numpy()
    v = w[cols].to_numpy()
    var = float(v @ cov @ v) * 252
    if not np.isfinite(var) or var <= 0:
        return w * 0.0
    w = w * (target / math.sqrt(var))
    g = w.abs().sum()
    return w * (gross_cap / g) if g > gross_cap else w


def month_ends(cal):
    mo = CU.month_offsets(cal)
    return mo.index[mo["off_own"] == 0]


def week_ends(cal):
    s = pd.Series(cal, index=cal)
    return pd.DatetimeIndex(s.groupby(s.index.to_period("W-FRI")).max().values)


def run_sim(w_dec, period="FWD", exec_="next_close"):
    """Return dict of daily EXCESS series (net_1x, net_2x, gross), turnover, held, using the realistic cost map."""
    tickers = list(w_dec.columns)
    ohlc = E.load_ohlc(tickers, period)
    rf = E.load_rf(period)
    cm = cost_map(tickers)
    net, gross, to, held, cost = E.simulate(w_dec, ohlc, rf, exec=exec_, cost_bps=cm)
    net2, *_ = E.simulate(w_dec, ohlc, rf, exec=exec_, cost_bps=cm, cost_mult=2.0)
    rfa = rf.reindex(net.index).ffill().fillna(0.0)
    return {"net_1x": net - rfa, "net_2x": net2 - rfa, "gross": gross - rfa, "turnover": to, "held": held,
            "rf": rfa}


def first_live(held: pd.DataFrame) -> pd.Timestamp:
    live = held.abs().sum(axis=1) > 0
    return live[live].index[0]


# --------------------------------------------------------------------------- references

_REFS = HERE / "refs.parquet"


def refs() -> pd.DataFrame:
    if _REFS.exists():
        return pd.read_parquet(_REFS)
    from src import forward, forward2
    rf = E.load_rf("FWD")
    s1 = forward2.returns("S1", "FWD")
    f2 = forward.returns("F2", "FWD")
    _, _, ex = panel(["F_ES"], "FWD")
    df = pd.DataFrame({
        "S1": s1 - rf.reindex(s1.index).ffill().fillna(0.0),
        "F2": f2 - rf.reindex(f2.index).ffill().fillna(0.0),
        "ES": ex["F_ES"],
    })
    for c in ("S1", "F2"):                       # leading pre-live zeros -> NaN (correlations on live days only)
        nz = df[c].fillna(0.0).abs() > 0
        df.loc[: nz[nz].index[0] - pd.Timedelta(days=1), c] = np.nan
    df.to_parquet(_REFS)
    return df


# --------------------------------------------------------------------------- metrics

def _sharpe(x):
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(252)) if len(x) > 2 and x.std() > 0 else float("nan")


def _mdd(x):
    eq = (1 + x.fillna(0.0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


def metrics(s: dict, start: pd.Timestamp, ref: pd.DataFrame | None = None) -> dict:
    """s: dict from run_sim (daily excess series). In-sample = [start, IS_END]; later = [LATER_START, end]."""
    ref = refs() if ref is None else ref
    n1 = s["net_1x"].loc[start:IS_END]
    n2 = s["net_2x"].loc[start:IS_END]
    g = s["gross"].loc[start:IS_END]
    to = s["turnover"].loc[start:IS_END]
    yrs = len(n1) / 252
    yearly = (1 + n1).groupby(n1.index.year).prod() - 1
    ycount = n1.groupby(n1.index.year).size()
    yearly = yearly[ycount >= 120]
    roll = n1.rolling(504).apply(lambda x: x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else np.nan, raw=True)
    later = s["net_1x"].loc[LATER_START:]
    j = pd.concat([n1.rename("x"), ref], axis=1, join="inner").dropna(subset=["x"])
    out = {
        "is_window": f"{n1.index[0].date()}..{n1.index[-1].date()}",
        "is_net_sharpe_1x": _sharpe(n1),
        "is_net_sharpe_2x": _sharpe(n2),
        "is_gross_sharpe": _sharpe(g),
        "ann_return": float(n1.mean() * 252),
        "ann_vol": float(n1.std() * math.sqrt(252)),
        "max_dd": _mdd(n1),
        "worst_year": float(yearly.min()) if len(yearly) else float("nan"),
        "pct_positive_years": float((yearly > 0).mean()) if len(yearly) else float("nan"),
        "rolling2y_p10": float(np.nanpercentile(roll.dropna(), 10)) if roll.notna().any() else float("nan"),
        "turnover": float(to.sum() / yrs) if yrs > 0 else float("nan"),
        "nw_t": E.newey_west_tstat(n1),
        "corr_es": float(j["x"].corr(j["ES"])),
        "corr_s1": float(j["x"].corr(j["S1"])),
        "corr_f2": float(j["x"].corr(j["F2"])),
        "later_net_sharpe_1x": _sharpe(later),
        "later_net_sharpe_2x": _sharpe(s["net_2x"].loc[LATER_START:]),
        "later_max_dd": _mdd(later),
        "later_window": f"{later.index[0].date()}..{later.index[-1].date()}" if len(later) else "",
        "yearly": {int(k): round(float(v), 4) for k, v in yearly.items()},
    }
    return out


def sharpe_window(s: dict, a, b=IS_END, col="net_1x"):
    return _sharpe(s[col].loc[a:b])


def save_series(sid: str, s: dict, start: pd.Timestamp, meta: dict):
    df = pd.DataFrame({k: s[k] for k in ("net_1x", "net_2x", "gross")}).loc[start:]
    df.index.name = "date"
    df.to_parquet(SERIES / f"{sid}.parquet")
    meta = dict(meta)
    meta.update({"series_start": str(df.index[0].date()), "series_end": str(df.index[-1].date()),
                 "columns": "daily excess returns over T-bill: net_1x (realistic costs), net_2x (2x costs), gross",
                 "in_sample_end": str(IS_END.date())})
    (SERIES / f"{sid}.json").write_text(json.dumps(meta, indent=2, default=str))
    return str(SERIES / f"{sid}.parquet")


def dump(obj, path):
    Path(path).write_text(json.dumps(obj, indent=2, default=str))
