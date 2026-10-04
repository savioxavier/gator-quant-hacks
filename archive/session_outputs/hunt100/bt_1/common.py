"""Shared helpers for bt_1 (see COMMON_SPEC.md). Run from the repo root with GQH_DATA_DIR set."""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
from src import engine as E  # noqa: E402
from src import forward2 as F2MOD  # noqa: E402

assert os.environ.get("GQH_OOS_UNLOCK") != "1"

BT = Path(__file__).resolve().parent
SERIES = BT.parent / "series"
ROOTS = ["ES", "NQ", "RTY", "YM", "ZT", "ZF", "ZN", "ZB", "UB", "CL", "HO", "RB", "NG", "GC", "SI", "PL",
         "HG", "ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE", "6E", "6J", "6B", "6A", "6C", "6S"]
TICKERS = [f"F_{r}" for r in ROOTS]
_C = {"ES": 1, "NQ": 1, "YM": 1, "RTY": 2, "ZT": 0.5, "ZF": 0.7, "ZN": 1, "ZB": 1.5, "UB": 1.5,
      "CL": 2, "GC": 2, "SI": 2, "HG": 2, "NG": 3, "HO": 3, "RB": 3, "PL": 3}
COST = {f"F_{r}": float(_C.get(r, 1.0 if r.startswith("6") else 4.0)) for r in ROOTS}
IS_END = pd.Timestamp("2024-10-02")
LATER = (pd.Timestamp("2024-10-03"), pd.Timestamp("2026-10-02"))
MIN_HISTORY = 260
ACTIVE_WINDOW = 10
EWMA_COM = 60
TARGET_VOL = 0.10
GROSS_CAP = 3.0
COV_WINDOW = 252


# ----------------------------------------------------------------------------- panel

def panel(period: str = "FWD"):
    ohlc = E.load_ohlc(TICKERS, period)
    rf = E.load_rf(period).reindex(ohlc["close"].index).ffill().fillna(0.0)
    close = ohlc["close"]
    ex = close.pct_change(fill_method=None).sub(rf, axis=0)
    started = close.notna()
    ex = ex.where(started)
    px = (1 + ex.fillna(0.0)).cumprod().where(started)          # excess-return index
    traded = (ohlc["volume"].fillna(0.0) > 0).astype(float)
    active = traded.rolling(ACTIVE_WINDOW, min_periods=1).max().astype(bool)
    vol = np.sqrt(ex.pow(2).ewm(com=EWMA_COM, min_periods=60).mean() * 252)
    counts = ex.notna().cumsum()
    elig = (counts >= MIN_HISTORY) & active & (vol > 0) & np.isfinite(vol)
    return dict(ohlc=ohlc, rf=rf, ex=ex, px=px, vol=vol, elig=elig, cal=close.index)


def month_ends(cal: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return F2MOD._month_ends(cal)


def week_ends(cal: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(cal, index=cal)
    iso = cal.isocalendar()
    key = iso["year"].astype(str) + "-" + iso["week"].astype(str)
    last = s.groupby(key.values).max()
    return pd.DatetimeIndex(sorted(last.values))


def scale_to_target(w: pd.Series, ex_hist: pd.DataFrame, target: float = TARGET_VOL) -> pd.Series:
    cols = [c for c in w.index if w[c] != 0]
    if not cols:
        return w * 0.0
    cov = ex_hist[cols].tail(COV_WINDOW).cov(min_periods=60).fillna(0.0).to_numpy()
    v = w[cols].to_numpy()
    var = float(v @ cov @ v) * 252
    if not np.isfinite(var) or var <= 0:
        return w * 0.0
    w = w * (target / math.sqrt(var))
    g = w.abs().sum()
    return w * (GROSS_CAP / g) if g > GROSS_CAP else w


def cap_gross(w: pd.Series) -> pd.Series:
    g = w.abs().sum()
    return w * (GROSS_CAP / g) if g > GROSS_CAP else w


# ----------------------------------------------------------------------------- raw OHLC (front contract)

def raw_ohlc_nyse(cal: pd.DatetimeIndex) -> dict[str, pd.DataFrame]:
    """Front-contract OHLC aggregated onto the NYSE calendar, per root: columns open, high, low, close, prev_close
    (same instrument, previous NYSE group). Not lagged here."""
    path = E.C.DATA_DIR / "databento_raw" / "glbx_ohlcv1d_v01.parquet"
    d = pd.read_parquet(path)
    d["date"] = d["ts_event"].dt.tz_localize(None).dt.normalize()
    d["root"] = d["symbol"].str.split(".").str[0]
    d["rank"] = d["symbol"].str.split(".").str[2].astype(int)
    out = {}
    for r in ROOTS:
        x = d[d["root"] == r].copy()
        pos = cal.searchsorted(x["date"].values, side="left")
        ok = pos < len(cal)
        x = x[ok]
        x["nyse"] = cal[pos[ok]]
        # front instrument on the last CME date of each NYSE group
        f = x[x["rank"] == 0].sort_values("date")
        front = f.groupby("nyse").last()["instrument_id"]
        # aggregate every instrument within the group
        x = x.sort_values(["date", "rank"]).drop_duplicates(["date", "instrument_id"], keep="first")
        g = x.groupby(["nyse", "instrument_id"]).agg(open=("open", "first"), high=("high", "max"),
                                                      low=("low", "min"), close=("close", "last"))
        g = g.reset_index()
        close_by = g.set_index(["nyse", "instrument_id"])["close"]
        sel = g.merge(front.rename("instrument_id").reset_index(), on=["nyse", "instrument_id"], how="inner")
        sel = sel.set_index("nyse").sort_index()
        days = list(sel.index)
        prev_day = pd.Series([None] + days[:-1], index=sel.index)
        pc = []
        for dd, pdte, iid in zip(sel.index, prev_day.values, sel["instrument_id"].values):
            if pdte is None:
                pc.append(np.nan)
            else:
                pc.append(close_by.get((pdte, iid), np.nan))
        sel["prev_close"] = pc
        out[r] = sel[["open", "high", "low", "close", "prev_close", "instrument_id"]].reindex(cal)
    return out


def yang_zhang(raw: dict[str, pd.DataFrame], window: int = 63, min_obs: int = 40) -> pd.DataFrame:
    """Annualised Yang-Zhang vol per F_ ticker on the NYSE calendar, LAGGED one session."""
    res = {}
    k = 0.34 / (1.34 + (window + 1) / (window - 1))
    for r, x in raw.items():
        o = np.log(x["open"] / x["prev_close"])
        c = np.log(x["close"] / x["open"])
        u = np.log(x["high"] / x["open"])
        dn = np.log(x["low"] / x["open"])
        rs = u * (u - c) + dn * (dn - c)
        valid = o.notna() & c.notna() & rs.notna()
        o, c, rs = o.where(valid), c.where(valid), rs.where(valid)
        vo = o.rolling(window, min_periods=min_obs).var()
        vc = c.rolling(window, min_periods=min_obs).var()
        vrs = rs.rolling(window, min_periods=min_obs).mean()
        yz = np.sqrt((vo + k * vc + (1 - k) * vrs) * 252)
        res[f"F_{r}"] = yz.shift(1)
    return pd.DataFrame(res)


def wilder_nrel(raw: dict[str, pd.DataFrame], n: int = 20) -> pd.DataFrame:
    """Turtle N / close (Wilder 20-day EMA of true range, relative to the close), LAGGED one session."""
    res = {}
    for r, x in raw.items():
        h, l, c, pc = x["high"], x["low"], x["close"], x["prev_close"]
        tr = pd.concat([h, pc], axis=1).max(axis=1) - pd.concat([l, pc], axis=1).min(axis=1)
        tr = tr.where(h.notna() & l.notna())
        # relative TR so that rolls (price-level jumps) do not distort N
        trr = (tr / c).dropna()
        nn = pd.Series(np.nan, index=trr.index)
        vals = trr.to_numpy()
        if len(vals) > n:
            cur = vals[:n].mean()
            nn.iloc[n - 1] = cur
            for i in range(n, len(vals)):
                cur = (cur * (n - 1) + vals[i]) / n
                nn.iloc[i] = cur
        res[f"F_{r}"] = nn.reindex(x.index).ffill(limit=5).shift(1)
    return pd.DataFrame(res)


# ----------------------------------------------------------------------------- simulation + metrics

def run(w_dec: pd.DataFrame, P) -> dict:
    w_dec = w_dec.reindex(columns=TICKERS).fillna(0.0)
    out = {}
    for m in (1.0, 2.0):
        net, gross, to, held, cost = E.simulate(w_dec, P["ohlc"], P["rf"], exec="next_close", cost_mult=m,
                                                cost_bps=COST)
        rf = P["rf"].reindex(net.index).ffill().fillna(0.0)
        out[f"net_{int(m)}x"] = net - rf
        if m == 1.0:
            out["gross"] = gross - rf
            out["turnover"] = to
            out["held"] = held
    live = out["held"].abs().sum(axis=1) > 0
    first = live.idxmax()
    out["first"] = first
    df = pd.DataFrame({k: out[k] for k in ("net_1x", "net_2x", "gross")}).loc[first:]
    out["df"] = df
    return out


def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(252)) if x.std() > 0 else float("nan")


def mdd(x: pd.Series) -> float:
    eq = (1 + x.fillna(0.0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


_REF = None


def refs() -> pd.DataFrame:
    """Daily excess returns of ES (F_ES index), S1 and F2 over the FWD range (cached)."""
    global _REF
    if _REF is not None:
        return _REF
    p = BT / "_refs.parquet"
    if p.exists():
        _REF = pd.read_parquet(p)
        return _REF
    from src import forward as F1MOD
    rf = E.load_rf("FWD")
    s1 = F2MOD.returns("S1", "FWD")
    f2 = F1MOD.returns("F2", "FWD")
    es = E.load_ohlc(["F_ES"], "FWD")["close"]["F_ES"].pct_change(fill_method=None)
    df = pd.DataFrame({"S1": s1, "F2": f2, "ES": es})
    df = df.sub(rf.reindex(df.index).ffill(), axis=0)
    df.to_parquet(p)
    _REF = df
    return df


def metrics(res: dict) -> dict:
    df = res["df"]
    ins = df.loc[:IS_END]
    lat = df.loc[LATER[0]:LATER[1]]
    n = ins["net_1x"]
    yrs = (1 + n).groupby(n.index.year).prod() - 1
    roll = n.rolling(504).apply(lambda a: a.mean() / a.std() * math.sqrt(252) if a.std() > 0 else np.nan, raw=True)
    to = res["turnover"].loc[ins.index]
    R = refs().reindex(ins.index)
    return {
        "is_window": f"{ins.index[0].date()}..{ins.index[-1].date()}",
        "is_net_sharpe_1x": sharpe(n),
        "is_net_sharpe_2x": sharpe(ins["net_2x"]),
        "is_gross_sharpe": sharpe(ins["gross"]),
        "ann_return": float(n.mean() * 252),
        "ann_vol": float(n.std() * math.sqrt(252)),
        "max_dd": mdd(n),
        "worst_year": float(yrs.min()),
        "worst_year_label": int(yrs.idxmin()),
        "pct_positive_years": float((yrs > 0).mean()),
        "rolling2y_p10": float(np.nanpercentile(roll.dropna(), 10)) if roll.notna().any() else float("nan"),
        "turnover": float(to.sum() / (len(to) / 252)),
        "nw_t": E.newey_west_tstat(n),
        "corr_es": float(n.corr(R["ES"])),
        "corr_s1": float(n.corr(R["S1"])),
        "corr_f2": float(n.corr(R["F2"])),
        "later_net_sharpe_1x": sharpe(lat["net_1x"]),
        "later_net_sharpe_2x": sharpe(lat["net_2x"]),
        "later_max_dd": mdd(lat["net_1x"]),
        "later_ann_return": float(lat["net_1x"].mean() * 252),
        "full_net_sharpe_1x": sharpe(df["net_1x"]),
        "yearly": {int(k): float(v) for k, v in yrs.items()},
        "avg_gross_leverage": float(res["held"].loc[ins.index].abs().sum(axis=1).mean()),
    }


def save_series(sid: str, res: dict, sidecar: dict) -> None:
    SERIES.mkdir(parents=True, exist_ok=True)
    res["df"].to_parquet(SERIES / f"{sid}.parquet")
    with open(SERIES / f"{sid}.json", "w", encoding="utf-8") as fh:
        json.dump(sidecar, fh, indent=2, default=str)


def fmt(m: dict) -> str:
    keys = ["is_window", "is_net_sharpe_1x", "is_net_sharpe_2x", "is_gross_sharpe", "ann_return", "ann_vol", "max_dd",
            "worst_year", "pct_positive_years", "rolling2y_p10", "turnover", "nw_t", "corr_es", "corr_s1", "corr_f2",
            "later_net_sharpe_1x", "later_max_dd", "avg_gross_leverage"]
    return " | ".join(f"{k}={m[k]:.3f}" if isinstance(m[k], float) else f"{k}={m[k]}" for k in keys)
