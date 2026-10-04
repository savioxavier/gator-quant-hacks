"""Shared plumbing for the bt_5 batch (see COMMON_SPEC.md). Read-only use of the repo engine; writes only under
hunt100/bt_5 and hunt100/series. Never logs trials, never unlocks the OOS loader, never writes to results/."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<solo-repo>")
sys.path.insert(0, str(REPO))
from src import engine as E  # noqa: E402
from src import forward2 as F2M  # noqa: E402

SP = Path("<scratch>")
HUNT = SP / "hunt100"
BT = HUNT / "bt_5"
SERIES = HUNT / "series"
CONTRACTS = SP / "edges" / "carry" / "contracts.parquet"

IS_END = pd.Timestamp("2024-10-02")
LATER_START = pd.Timestamp("2024-10-03")

CLASSES = {
    "COM15": ["CL", "HO", "RB", "NG", "GC", "SI", "PL", "HG", "ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE"],
    "FX6": ["6E", "6J", "6B", "6A", "6C", "6S"],
    "EQ4": ["ES", "NQ", "YM", "RTY"],
    "RATES5": ["ZT", "ZF", "ZN", "ZB", "UB"],
}
ROOTS = [r for v in CLASSES.values() for r in v]
COM15 = CLASSES["COM15"]
COST = {"ES": 1.0, "NQ": 1.0, "YM": 1.0, "RTY": 2.0, "ZT": 0.5, "ZF": 0.7, "ZN": 1.0, "ZB": 1.5, "UB": 1.5,
        "6E": 1.0, "6J": 1.0, "6B": 1.0, "6A": 1.0, "6C": 1.0, "6S": 1.0,
        "CL": 2.0, "GC": 2.0, "SI": 2.0, "HG": 2.0, "NG": 3.0, "HO": 3.0, "RB": 3.0, "PL": 3.0,
        "ZC": 4.0, "ZS": 4.0, "ZW": 4.0, "ZL": 4.0, "ZM": 4.0, "LE": 4.0, "HE": 4.0}

EWMA_COM = 60
COV_WINDOW = 252
MIN_HISTORY = 300
ACTIVE_WINDOW = 10
INSTR_VOL = 0.10
TARGET_VOL = 0.10
SCALE_CAP = 4.0
LEG_CAP = 3.0


def tick(r: str) -> str:
    return f"F_{r}"


def leg(r: str, side: str) -> str:
    """side 'N' (near) or 'D' (deferred / far)."""
    return f"F_{r}_{side}"


# ----------------------------------------------------------------------------------------------- base panel

def load_base():
    """Front total-return panel for all 30 roots on the NYSE calendar (FWD = every date through 2026-10-02)."""
    tk = [tick(r) for r in ROOTS]
    ohlc = E.load_ohlc(tk, "FWD")
    cal = ohlc["close"].index
    rf = E.load_rf("FWD").reindex(cal).ffill().fillna(0.0)
    ex = ohlc["close"].pct_change(fill_method=None).sub(rf, axis=0)
    vol = np.sqrt(ex.pow(2).ewm(com=EWMA_COM, min_periods=60).mean() * 252)
    counts = ex.notna().cumsum()
    traded = (ohlc["volume"].fillna(0.0) > 0).astype(float)
    active = traded.rolling(ACTIVE_WINDOW, min_periods=1).max().astype(bool)
    elig = (counts >= MIN_HISTORY) & np.isfinite(vol) & (vol > 0) & active
    return dict(ohlc=ohlc, cal=cal, rf=rf, ex=ex, vol=vol, elig=elig)


def month_ends(cal: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return F2M._month_ends(cal)


# ----------------------------------------------------------------------------------------------- legs

def _root_legs(g: pd.DataFrame) -> pd.DataFrame:
    """Raw-date frame of the STD near/far legs for one root."""
    g = g.drop_duplicates(["date", "rank"], keep="last")
    by_day_id = g.set_index(["date", "instrument_id"])["close"]
    by_day_id = by_day_id[~by_day_id.index.duplicated(keep="last")]
    p = g.pivot(index="date", columns="rank", values=["instrument_id", "close", "month_index"]).sort_index()
    p.columns = [f"{a}{b}" for a, b in p.columns]
    for col in ("instrument_id0", "instrument_id1", "close0", "close1", "month_index0", "month_index1"):
        if col not in p.columns:
            p[col] = np.nan
    dm = p["month_index1"] - p["month_index0"]
    pair = (p["close0"] > 0) & (p["close1"] > 0) & p["month_index0"].notna() & p["month_index1"].notna() \
        & (dm != 0) & (dm.abs() <= 12)
    near0 = p["month_index0"] < p["month_index1"]
    out = pd.DataFrame(index=p.index)
    out["pair"] = pair
    out["near_id"] = np.where(pair, np.where(near0, p["instrument_id0"], p["instrument_id1"]), np.nan)
    out["far_id"] = np.where(pair, np.where(near0, p["instrument_id1"], p["instrument_id0"]), np.nan)
    out["near_close"] = np.where(pair, np.where(near0, p["close0"], p["close1"]), np.nan)
    out["far_close"] = np.where(pair, np.where(near0, p["close1"], p["close0"]), np.nan)
    out["gap_m"] = np.where(pair, dm.abs(), np.nan)
    out["carry"] = (out["near_close"] / out["far_close"]) ** (12.0 / out["gap_m"]) - 1.0
    dates = p.index
    prev = pd.Series(dates).shift(1).values
    rn, rfar = [], []
    for d, pd_, ni, fi, nc, fc in zip(dates, prev, out["near_id"], out["far_id"], out["near_close"],
                                      out["far_close"]):
        if pd.isna(pd_) or not np.isfinite(ni):
            rn.append(np.nan)
            rfar.append(np.nan)
            continue
        a = by_day_id.get((pd_, int(ni)), np.nan)
        b = by_day_id.get((pd_, int(fi)), np.nan)
        rn.append(nc / a - 1.0 if (np.isfinite(a) and a > 0 and nc > 0) else np.nan)
        rfar.append(fc / b - 1.0 if (np.isfinite(b) and b > 0 and fc > 0) else np.nan)
    out["r_near"] = rn
    out["r_far"] = rfar
    out["valid"] = out["r_near"].notna() & out["r_far"].notna()
    out.loc[~out["valid"], ["r_near", "r_far"]] = 0.0
    for side in ("near", "far"):
        idv = out[f"{side}_id"]
        last = idv.ffill().shift(1)
        out[f"roll_{side}"] = (idv.notna() & last.notna() & (idv != last)).astype(float)
    return out


def build_legs(cal: pd.DatetimeIndex, rf: pd.Series, roots=ROOTS) -> dict:
    """NYSE-calendar leg panels: ex_n / ex_d (P&L excess returns, 0 on invalid sessions), est_n / est_d (NaN on
    invalid sessions, for estimation), valid, roll_n / roll_d, carry (last daily obs), near_px (last near close),
    plus diagnostics."""
    c = pd.read_parquet(CONTRACTS)
    c = c[c["date"].dt.dayofweek < 5]
    c = c[c["root"].isin(roots)]
    keys = ("ex_n", "ex_d", "valid", "roll_n", "roll_d", "carry", "near_px", "gap_m")
    panels = {k: {} for k in keys}
    diag = []
    for root, g in c.groupby("root"):
        lg = _root_legs(g)
        pos = cal.searchsorted(lg.index.values, side="left")
        ok = pos < len(cal)
        lg = lg[ok]
        grp = cal[pos[ok]]
        gb = lg.groupby(grp)
        first = grp.min()
        cal_r = cal[cal >= first]
        panels["ex_n"][root] = ((1 + lg["r_near"]).groupby(grp).prod() - 1).reindex(cal_r).fillna(0.0)
        panels["ex_d"][root] = ((1 + lg["r_far"]).groupby(grp).prod() - 1).reindex(cal_r).fillna(0.0)
        panels["valid"][root] = gb["valid"].max().reindex(cal_r).fillna(False).astype(bool)
        panels["roll_n"][root] = gb["roll_near"].max().reindex(cal_r).fillna(0.0)
        panels["roll_d"][root] = gb["roll_far"].max().reindex(cal_r).fillna(0.0)
        panels["carry"][root] = gb["carry"].last().reindex(cal_r)          # last non-NaN in the session
        panels["near_px"][root] = gb["near_close"].last().reindex(cal_r)
        panels["gap_m"][root] = gb["gap_m"].last().reindex(cal_r)
        yrs = len(lg) / 252
        diag.append(dict(root=root, raw_days=len(lg), pair_frac=float(lg["pair"].mean()),
                         valid_frac=float(lg["valid"].mean()), near_rolls_per_yr=float(lg["roll_near"].sum() / yrs),
                         far_rolls_per_yr=float(lg["roll_far"].sum() / yrs), gap_median=float(lg["gap_m"].median())))
    out = {k: pd.DataFrame(v).reindex(index=cal, columns=[r for r in roots if r in v]) for k, v in panels.items()}
    out["valid"] = out["valid"].fillna(False).astype(bool)
    out["est_n"] = out["ex_n"].where(out["valid"])
    out["est_d"] = out["ex_d"].where(out["valid"])
    out["diag"] = pd.DataFrame(diag)
    return out


def leg_ohlc(legs: dict, rf: pd.Series, roots) -> dict:
    """Synthetic engine panels for the leg tickers: fully collateralised index (excess + T-bill)."""
    closes, rolls = {}, {}
    for r in roots:
        for side, key, rk in (("N", "ex_n", "roll_n"), ("D", "ex_d", "roll_d")):
            e = legs[key][r]
            started = e.notna()
            tr = (e.fillna(0.0) + rf).where(started)
            lvl = 100 * (1 + tr.fillna(0.0)).cumprod()
            closes[leg(r, side)] = lvl.where(started)
            rolls[leg(r, side)] = legs[rk][r].fillna(0.0)
    close = pd.DataFrame(closes)
    roll = pd.DataFrame(rolls)
    vol = pd.DataFrame(1.0, index=close.index, columns=close.columns)
    return {"close": close, "open": close, "high": close, "low": close, "volume": vol, "roll": roll}


def leg_cost_map(roots) -> dict:
    return {leg(r, s): COST[r] for r in roots for s in ("N", "D")}


def front_cost_map(roots) -> dict:
    return {tick(r): COST[r] for r in roots}


# ----------------------------------------------------------------------------------------------- books

def ewma_vol(x: pd.DataFrame) -> pd.DataFrame:
    """EWMA (com 60) of squared returns on non-missing observations, annualised; min 60 observations."""
    return np.sqrt(x.pow(2).ewm(com=EWMA_COM, min_periods=60, ignore_na=True).mean() * 252)


def scale_book(w: pd.Series, cov: pd.DataFrame) -> tuple[pd.Series, float]:
    cols = [c for c in w.index if w[c] != 0]
    if not cols:
        return w * 0.0, float("nan")
    m = cov.reindex(index=cols, columns=cols).fillna(0.0).to_numpy()
    v = w[cols].to_numpy()
    var = float(v @ m @ v) * 252
    if not np.isfinite(var) or var <= 0:
        return w * 0.0, float("nan")
    k = min(TARGET_VOL / math.sqrt(var), SCALE_CAP)
    return w * k, k


def cap_legs(w: pd.Series, roots) -> pd.Series:
    w = w.copy()
    for r in roots:
        a, b = leg(r, "N"), leg(r, "D")
        m = max(abs(w.get(a, 0.0)), abs(w.get(b, 0.0)))
        if m > LEG_CAP:
            w[a] *= LEG_CAP / m
            w[b] *= LEG_CAP / m
    return w


def rank_weights(sig: pd.Series) -> pd.Series:
    n = len(sig)
    rk = sig.rank(method="average")
    dev = rk - (n + 1) / 2.0
    pos = dev[dev > 0].sum()
    if pos <= 0:
        return dev * 0.0
    return dev / pos


def frame_from_rows(rows: dict, cal: pd.DatetimeIndex, cols) -> pd.DataFrame:
    """rows: {decision date: pd.Series of weights}; forward-filled decision frame, zeros before the first one."""
    w = pd.DataFrame(np.nan, index=cal, columns=list(cols))
    for d, s in rows.items():
        w.loc[d] = s.reindex(cols).fillna(0.0).values
    return w.ffill().fillna(0.0)


def run(w: pd.DataFrame, ohlc: dict, rf: pd.Series, cost_bps: dict) -> dict:
    """Simulate at 1x and 2x costs, next-close fills. Returns daily excess-return frame and diagnostics."""
    tk = list(w.columns)
    sub = {k: v[tk] for k, v in ohlc.items()}
    res = {}
    for lab, mult in (("net_1x", 1.0), ("net_2x", 2.0)):
        net, gross, turn, held, costs = E.simulate(w, sub, rf, exec="next_close", cost_mult=mult, cost_bps=cost_bps)
        res[lab] = net - rf
        if mult == 1.0:
            res["gross"] = gross - rf
            res["turnover"] = turn
            res["gross_notional"] = held.abs().sum(axis=1)
            res["held"] = held
            res["costs"] = costs
            cb = pd.Series({t: cost_bps[t] for t in tk}) / 1e4
            roll = sub["roll"].reindex(held.index).fillna(0.0)
            res["roll_costs"] = (2.0 * held.abs() * roll * cb).sum(axis=1)
    df = pd.DataFrame({c: res[c] for c in ("net_1x", "net_2x", "gross")})
    live = res["gross_notional"] > 0
    start = live.idxmax() if live.any() else None
    return dict(df=df, start=start, **{k: res[k] for k in ("turnover", "gross_notional", "held", "costs",
                                                           "roll_costs")})


# ----------------------------------------------------------------------------------------------- references & stats

def references(base: dict) -> pd.DataFrame:
    """ES excess, S1 (forward2) and F2 (forward) excess returns, cached."""
    path = BT / "refs.parquet"
    if path.exists():
        return pd.read_parquet(path)
    from src import forward as F1M
    rf = base["rf"]
    es = base["ex"]["F_ES"]
    s1 = F2M.returns("S1", "FWD")
    s1 = s1 - rf.reindex(s1.index).ffill().fillna(0.0)
    f2 = F1M.returns("F2", "FWD")
    f2 = f2 - rf.reindex(f2.index).ffill().fillna(0.0)
    refs = pd.DataFrame({"ES": es, "S1": s1, "F2": f2})
    refs.to_parquet(path)
    return refs


def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(252)) if len(x) > 20 and x.std() > 0 else float("nan")


def max_dd(x: pd.Series) -> float:
    eq = (1 + x.fillna(0.0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


def window_stats(df: pd.DataFrame, turnover: pd.Series, gross_n: pd.Series, costs: pd.Series, roll_costs: pd.Series,
                 refs: pd.DataFrame) -> dict:
    n1 = df["net_1x"]
    yrs = len(n1) / 252
    yearly = (1 + n1).groupby(n1.index.year).prod() - 1
    cnt = n1.groupby(n1.index.year).size()
    yf = yearly[cnt >= 126]
    roll = (n1.rolling(504).mean() / n1.rolling(504).std() * math.sqrt(252)).dropna()
    out = {
        "start": str(n1.index[0].date()), "end": str(n1.index[-1].date()), "years": round(yrs, 2),
        "sharpe_net_1x": sharpe(n1), "sharpe_net_2x": sharpe(df["net_2x"]), "sharpe_gross": sharpe(df["gross"]),
        "ann_mean_excess": float(n1.mean() * 252), "ann_mean_gross": float(df["gross"].mean() * 252),
        "ann_vol": float(n1.std() * math.sqrt(252)), "max_dd": max_dd(n1),
        "worst_year": float(yf.min()) if len(yf) else float("nan"),
        "worst_year_label": int(yf.idxmin()) if len(yf) else None,
        "pct_pos_years": float((yf > 0).mean()) if len(yf) else float("nan"),
        "yearly": {int(k): round(float(v), 4) for k, v in yearly.items()},
        "roll2y_p10": float(roll.quantile(0.10)) if len(roll) else float("nan"),
        "roll2y_p50": float(roll.quantile(0.50)) if len(roll) else float("nan"),
        "turnover_per_year": float(turnover.reindex(n1.index).sum() / yrs) if yrs > 0 else float("nan"),
        "cost_per_year": float(costs.reindex(n1.index).sum() / yrs) if yrs > 0 else float("nan"),
        "roll_cost_per_year": float(roll_costs.reindex(n1.index).sum() / yrs) if yrs > 0 else float("nan"),
        "mean_gross_notional": float(gross_n.reindex(n1.index).mean()),
        "nw_t": E.newey_west_tstat(n1),
        "skew": float(n1.skew()),
    }
    for k in ("ES", "S1", "F2"):
        j = pd.concat([n1, refs[k]], axis=1, join="inner").dropna()
        out[f"corr_{k}"] = float(j.iloc[:, 0].corr(j.iloc[:, 1])) if len(j) > 60 else float("nan")
    return out


def evaluate(name: str, r: dict, refs: pd.DataFrame) -> dict:
    df = r["df"].loc[r["start"]:]
    is_ = df.loc[:IS_END]
    lat = df.loc[LATER_START:]
    args = (r["turnover"], r["gross_notional"], r["costs"], r["roll_costs"], refs)
    return {"variant": name, "IS": window_stats(is_, *args), "LATER": window_stats(lat, *args)}


def deflated(variants: dict, results: dict) -> dict:
    """DSR of each variant's in-sample net 1x series over the declared variants."""
    srs = [results[k]["IS"]["sharpe_net_1x"] for k in variants]
    var_sr = float(np.var(srs, ddof=1)) if len(srs) > 1 else 0.0
    out = {}
    for k in variants:
        x = variants[k]["df"].loc[variants[k]["start"]:IS_END, "net_1x"]
        out[k] = E.deflated_sharpe(x, n_trials=len(srs), var_sr_ann=var_sr)["dsr"]
    return out


def save_series(sid: str, df: pd.DataFrame, side: dict, folder: Path | None = None) -> Path:
    folder = folder or SERIES
    folder.mkdir(parents=True, exist_ok=True)
    d = df.copy()
    d.index.name = "date"
    p = folder / f"{sid}.parquet"
    d.to_parquet(p)
    (folder / f"{sid}.json").write_text(json.dumps(side, indent=2, default=str))
    return p


def jdump(obj, path: Path) -> None:
    path.write_text(json.dumps(obj, indent=2, default=lambda o: float(o) if isinstance(o, (np.floating,)) else str(o)))
