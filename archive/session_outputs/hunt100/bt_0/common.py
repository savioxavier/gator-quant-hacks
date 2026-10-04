"""Shared plumbing for the bt_0 re-backtests (conventions in COMMON_SPEC.md).

Reads only. Never unlocks the OOS loader, never calls run_backtest / log_trial, never writes to the repo.
"""
from __future__ import annotations

import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<solo-repo>")
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from src import engine as E  # noqa: E402
from src import forward2 as F2M  # noqa: E402

BT = Path(__file__).resolve().parent
HUNT = BT.parent
SERIES = HUNT / "series"
IS_END = pd.Timestamp("2024-10-02")
LATER_START = pd.Timestamp("2024-10-03")
LATER_END = pd.Timestamp("2026-10-02")

ROOTS = list(F2M.S1_ROOTS)
TICK = list(F2M.S1_TICKERS)
COST = {"ES": 1.0, "NQ": 1.0, "YM": 1.0, "RTY": 2.0, "ZT": 0.5, "ZF": 0.7, "ZN": 1.0, "ZB": 1.5, "UB": 1.5,
        "6E": 1.0, "6J": 1.0, "6B": 1.0, "6A": 1.0, "6C": 1.0, "6S": 1.0,
        "CL": 2.0, "GC": 2.0, "SI": 2.0, "HG": 2.0, "NG": 3.0, "HO": 3.0, "RB": 3.0, "PL": 3.0,
        "ZC": 4.0, "ZS": 4.0, "ZW": 4.0, "ZL": 4.0, "ZM": 4.0, "LE": 4.0, "HE": 4.0}
COST_BPS = {f"F_{r}": v for r, v in COST.items()}
assert set(COST) == set(ROOTS)

MIN_HISTORY = F2M.MIN_HISTORY      # 300
EWMA_COM = F2M.EWMA_COM            # 60
TARGET_VOL = 0.10
GROSS_CAP = 3.0
COV_WINDOW = 252


@lru_cache(maxsize=1)
def panel():
    ohlc = E.load_ohlc(TICK, "FWD")
    rf = E.load_rf("FWD").reindex(ohlc["close"].index).ffill().fillna(0.0)
    ex = ohlc["close"].pct_change(fill_method=None).sub(rf, axis=0)
    active = F2M._active(ohlc)
    counts = ex.notna().cumsum()
    vol60 = np.sqrt(ex.pow(2).ewm(com=EWMA_COM, min_periods=60).mean() * 252)
    base_elig = (counts >= MIN_HISTORY) & active
    elig60 = base_elig & np.isfinite(vol60) & (vol60 > 0)
    return {"ohlc": ohlc, "rf": rf, "ex": ex, "active": active, "counts": counts, "vol60": vol60,
            "base_elig": base_elig, "elig60": elig60}


def month_ends(cal: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return F2M._month_ends(cal)


def week_ends(cal: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(cal, index=cal)
    return pd.DatetimeIndex(s.groupby(cal.to_period("W-FRI")).max().values)


def scale_to_target(w: pd.Series, ex_hist: pd.DataFrame) -> pd.Series:
    return F2M._scale_to_target(w, ex_hist)


# ------------------------------------------------------------------------------------------- simulation

def simulate_all(w_dec: pd.DataFrame, exec: str = "next_close") -> dict:
    """net_1x / net_2x / gross daily EXCESS returns from the first held session to the end of data."""
    P = panel()
    ohlc, rf = P["ohlc"], P["rf"]
    w_dec = w_dec.reindex(columns=TICK).fillna(0.0)
    n1, g, to, held, _ = E.simulate(w_dec, ohlc, rf, exec=exec, cost_bps=COST_BPS)
    n2, *_ = E.simulate(w_dec, ohlc, rf, exec=exec, cost_bps=COST_BPS, cost_mult=2.0)
    r = rf.reindex(n1.index).ffill().fillna(0.0)
    live = held.abs().sum(axis=1) > 0
    first = live.idxmax()
    df = pd.DataFrame({"net_1x": n1 - r, "net_2x": n2 - r, "gross": g - r}).loc[first:LATER_END]
    return {"df": df, "turnover": to.loc[first:LATER_END], "held": held.loc[first:LATER_END], "start": first}


# ------------------------------------------------------------------------------------------- comparison

@lru_cache(maxsize=1)
def compare_series() -> pd.DataFrame:
    path = BT / "compare_series.parquet"
    if path.exists():
        return pd.read_parquet(path)
    from src import forward as F1M
    P = panel()
    rf = E.load_rf("FWD")
    s1 = F2M.returns("S1", "FWD")
    f2 = F1M.returns("F2", "FWD")
    out = pd.DataFrame({
        "ES": P["ex"]["F_ES"],
        "S1": s1 - rf.reindex(s1.index).ffill().fillna(0.0),
        "F2": f2 - rf.reindex(f2.index).ffill().fillna(0.0),
    })
    out.to_parquet(path)
    return out


# ------------------------------------------------------------------------------------------- metrics

def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(252)) if len(x) > 2 and x.std() > 0 else float("nan")


def excess_mdd(x: pd.Series) -> float:
    return E.max_drawdown(x.fillna(0.0))


def metrics(res: dict) -> dict:
    df, to, held = res["df"], res["turnover"], res["held"]
    start = res["start"]
    isd = df.loc[start:IS_END]
    lat = df.loc[LATER_START:LATER_END]
    x = isd["net_1x"]
    n = len(x)
    yrs = n / 252
    yearly = (1 + x).groupby(x.index.year).prod() - 1
    rm = x.rolling(504).mean()
    rs = x.rolling(504).std()
    roll = (rm / rs * math.sqrt(252)).dropna()
    cmp_ = compare_series()
    j = pd.concat([x.rename("s"), cmp_], axis=1, join="inner").loc[start:IS_END].dropna()
    out = {
        "is_window": f"{start.date()}..{IS_END.date()}",
        "is_net_sharpe_1x": sharpe(x),
        "is_net_sharpe_2x": sharpe(isd["net_2x"]),
        "is_gross_sharpe": sharpe(isd["gross"]),
        "ann_return": float(x.mean() * 252),
        "cagr_excess": float((1 + x).prod() ** (1 / yrs) - 1),
        "ann_vol": float(x.std() * math.sqrt(252)),
        "max_dd": excess_mdd(x),
        "worst_year": float(yearly.min()),
        "worst_year_label": int(yearly.idxmin()),
        "pct_positive_years": float((yearly > 0).mean()),
        "yearly_is": {int(k): round(float(v), 4) for k, v in yearly.items()},
        "rolling2y_p10": float(roll.quantile(0.10)) if len(roll) else float("nan"),
        "rolling2y_p50": float(roll.quantile(0.50)) if len(roll) else float("nan"),
        "turnover": float(to.loc[start:IS_END].sum() / yrs),
        "mean_gross_notional": float(held.loc[start:IS_END].abs().sum(axis=1).mean()),
        "nw_t": E.newey_west_tstat(x),
        "corr_es": float(j["s"].corr(j["ES"])),
        "corr_s1": float(j["s"].corr(j["S1"])),
        "corr_f2": float(j["s"].corr(j["F2"])),
        "later_net_sharpe_1x": sharpe(lat["net_1x"]),
        "later_net_sharpe_2x": sharpe(lat["net_2x"]),
        "later_gross_sharpe": sharpe(lat["gross"]),
        "later_max_dd": excess_mdd(lat["net_1x"]),
        "later_ann_return": float(lat["net_1x"].mean() * 252),
        "later_ann_vol": float(lat["net_1x"].std() * math.sqrt(252)),
        "full_net_sharpe_1x": sharpe(df["net_1x"]),
    }
    return out


def save_variant(folder: Path, name: str, res: dict) -> Path:
    vd = folder / "variants"
    vd.mkdir(parents=True, exist_ok=True)
    p = vd / f"{name}.parquet"
    res["df"].to_parquet(p)
    return p


def save_headline(sid: str, res: dict, sidecar: dict) -> Path:
    SERIES.mkdir(parents=True, exist_ok=True)
    p = SERIES / f"{sid}.parquet"
    res["df"][["net_1x", "net_2x", "gross"]].to_parquet(p)
    (SERIES / f"{sid}.json").write_text(json.dumps(sidecar, indent=2, default=str))
    return p


def fmt(m: dict) -> str:
    return (f"IS {m['is_window']}: net1x {m['is_net_sharpe_1x']:.3f} net2x {m['is_net_sharpe_2x']:.3f} "
            f"gross {m['is_gross_sharpe']:.3f} | ret {m['ann_return']:.3%} vol {m['ann_vol']:.3%} "
            f"MDD {m['max_dd']:.1%} worst yr {m['worst_year']:.1%} ({m['worst_year_label']}) "
            f"pos yrs {m['pct_positive_years']:.0%} roll2y p10 {m['rolling2y_p10']:.2f} TO {m['turnover']:.1f}x "
            f"gross notional {m['mean_gross_notional']:.2f} NW t {m['nw_t']:.2f} | corr ES {m['corr_es']:.2f} "
            f"S1 {m['corr_s1']:.2f} F2 {m['corr_f2']:.2f} | later net1x {m['later_net_sharpe_1x']:.3f} "
            f"MDD {m['later_max_dd']:.1%}")


# ------------------------------------------------------------------------------------------- AQR TSMOM factor

def aqr_tsmom_monthly() -> pd.Series | None:
    """AQR TSMOM factor (monthly, gross excess) from the hunt's downloaded file, if readable."""
    path = HUNT.parent / "tsmom.xlsx"
    if not path.exists():
        return None
    try:
        raw = pd.read_excel(path, sheet_name="TSMOM Factors", header=None)
    except Exception:
        return None
    hdr_row = None
    for i in range(min(len(raw), 60)):
        vals = [str(v) for v in raw.iloc[i].tolist()]
        if any(v.strip() == "TSMOM" for v in vals):
            hdr_row = i
            break
    if hdr_row is None:
        return None
    hdr = [str(v).strip() for v in raw.iloc[hdr_row].tolist()]
    col = hdr.index("TSMOM")
    d = raw.iloc[hdr_row + 1:, [0, col]].dropna()
    d.columns = ["date", "tsmom"]
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna()
    s = pd.to_numeric(d.set_index("date")["tsmom"], errors="coerce").dropna()
    s.index = s.index.to_period("M")
    return s
