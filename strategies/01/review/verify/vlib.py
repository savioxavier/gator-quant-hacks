"""Independent re-implementation of the frozen Variant A rule for adversarial verification.

Written from the published spec (HYPOTHESIS.md, config.py, backtest.py read as text). Shares no code
with replicate/ or analyse/. Consensus is computed as an explicit sum over speeches (not a recursion),
the expanding z from cumulative sums, the vol from explicit window loops.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

assert os.environ.get("GQH_OOS_UNLOCK") != "1"
REPO = Path(os.environ["GQH_REPO"]) if os.environ.get("GQH_REPO") else Path(__file__).resolve().parents[5] / "gqh-flow-clock"  # clone of github.com/minh-stakc/gqh-flow-clock
sys.path.insert(0, str(REPO))
from src import engine as E  # noqa: E402

HERE = Path(__file__).resolve().parent
FS = HERE.parent
SCR = FS.parent  # strategies/01
THEIR = SCR
TP = THEIR / "data" / "processed"
EXT = FS / "extend"
EDGES = Path(os.environ.get("GQH_EDGES_DIR", FS / "edges"))  # edge-search artifacts, needed only for the portfolio test

IS_END = pd.Timestamp("2024-10-02")
OOS_START = pd.Timestamp("2024-10-03")
END = pd.Timestamp("2026-10-02")
CLOCK = pd.Timestamp("2011-01-03")
HL, ZMIN, CLIP = 20, 252, 2.0
VT, VFLOOR, GCAP = 0.10, 0.04, 1.5
WT, WU = 0.75, 0.25
BAND = 0.10
COST = {"TLT": 1.5, "UUP": 5.0}
LAM = 0.5 ** (1.0 / HL)
WINDOWS = {"IS": ("2011-12-30", "2024-10-02"), "HOLDOUT": ("2021-01-01", "2024-10-02"),
           "OOS": ("2024-10-03", "2026-10-02"), "FULL": ("2011-12-30", "2026-10-02")}


# ------------------------------------------------------------------ inputs
def kept_scores(path: Path, end=END) -> pd.DataFrame:
    sc = pd.read_csv(path, parse_dates=["speech_date"])
    k = sc["kept"].astype(str).str.lower().eq("true")
    sc = sc[k & sc["speech_date"].notna() & (sc["speech_date"] <= pd.Timestamp(end))].copy()
    return sc


def their_fomc() -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.read_csv(TP / "fomc_dates.csv", parse_dates=["fomc_date"])["fomc_date"])


def scheduled_fomc() -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.read_csv(EDGES / "calendar" / "fomc_scheduled.csv", parse_dates=["day0"])["day0"])


def our_opens(end=END) -> tuple[pd.DataFrame, dict]:
    ohlc = E.load_ohlc(["TLT", "UUP"], "FWD")
    ohlc = {k: v.loc[:pd.Timestamp(end)] for k, v in ohlc.items()}
    o = ohlc["open"].loc["2010-01-01":]
    return o, ohlc


def their_opens() -> pd.DataFrame:
    px = pd.read_csv(TP / "markets.csv", index_col=0, parse_dates=True)
    return pd.DataFrame({"TLT": px["TLT_adjopen"], "UUP": px["UUP_adjopen"]})


# ------------------------------------------------------------------ signal
def usable_index(cal: pd.DatetimeIndex, dates: pd.Series) -> np.ndarray:
    """Position in cal of the first session strictly after each date (len(cal) if none)."""
    return np.searchsorted(cal.values, pd.DatetimeIndex(dates).values, side="right")


def consensus(cal: pd.DatetimeIndex, dates: pd.Series, s: np.ndarray) -> pd.Series:
    u = usable_index(cal, dates)
    ok = u < len(cal)
    u, s = u[ok], np.asarray(s, float)[ok]
    k = np.arange(len(cal))
    C = np.zeros(len(cal))
    # explicit sum of decayed injections, chunked to bound memory
    for a in range(0, len(u), 200):
        uu, ss = u[a:a + 200], s[a:a + 200]
        lagm = k[:, None] - uu[None, :]
        C += np.where(lagm >= 0, ss[None, :] * np.power(LAM, np.clip(lagm, 0, None)), 0.0).sum(axis=1)
    return pd.Series(C, index=cal)


def expanding_z(C: pd.Series, clock=CLOCK, zmin=ZMIN) -> pd.Series:
    x = C.loc[C.index >= clock].to_numpy()
    x0 = x - x[0]
    n = np.arange(1, len(x) + 1, dtype=float)
    s1 = np.cumsum(x0)
    s2 = np.cumsum(x0 * x0)
    mu = s1 / n
    var = (s2 - s1 * s1 / n) / np.maximum(n - 1, 1)
    sd = np.sqrt(np.maximum(var, 0))
    z = (x0 - mu) / sd
    z[n < zmin] = np.nan
    z[~np.isfinite(z)] = np.nan
    return pd.Series(z, index=C.index[C.index >= clock]).reindex(C.index)


def oo_returns(o: pd.Series) -> pd.Series:
    """Open(t+1)/Open(t)-1, labelled t."""
    v = o.to_numpy()
    r = np.full(len(v), np.nan)
    r[:-1] = v[1:] / v[:-1] - 1
    return pd.Series(r, index=o.index)


def mix_vol(r_t: pd.Series, r_u: pd.Series, lag: int = 1) -> pd.Series:
    mix = (-WT * r_t + WU * r_u).to_numpy()
    n = len(mix)
    out = np.full(n, np.nan)
    for i in range(n):
        vals = []
        for w in (20, 60):
            a, b = i - lag - w + 1, i - lag + 1   # window ends at mix[i-lag]
            if a < 0:
                vals.append(np.nan)
                continue
            seg = mix[a:b]
            vals.append(np.std(seg, ddof=1) * math.sqrt(252) if np.all(np.isfinite(seg)) else np.nan)
        out[i] = 0.5 * vals[0] + 0.5 * vals[1]
    v = pd.Series(out, index=r_t.index)
    return v.where(v.isna(), np.maximum(v, VFLOOR))


def fomc_sessions(cal: pd.DatetimeIndex, dates) -> tuple[set, set]:
    days = set()
    for d in pd.DatetimeIndex(dates):
        i = np.searchsorted(cal.values, np.datetime64(d), side="left")   # first session >= d
        if i < len(cal):
            days.add(cal[i])
    nxt = set()
    for d in days:
        i = cal.get_loc(d)
        if i + 1 < len(cal):
            nxt.add(cal[i + 1])
    return days, nxt


def weights(cal, z: pd.Series, vol: pd.Series, fomc_dates) -> pd.DataFrame:
    fd, fn = fomc_sessions(cal, fomc_dates)
    pos = z.clip(-CLIP, CLIP).to_numpy()
    vv = vol.reindex(cal).to_numpy()
    wt_o, wu_o = np.zeros(len(cal)), np.zeros(len(cal))
    pt = pu = 0.0
    for i, t in enumerate(cal):
        if not (np.isfinite(pos[i]) and np.isfinite(vv[i])):
            wt_o[i], wu_o[i] = pt, pu
            continue
        k = VT / vv[i]
        a, b = -WT * pos[i] * k, WU * pos[i] * k
        g = abs(a) + abs(b)
        if g > GCAP:
            a, b = a * GCAP / g, b * GCAP / g
        if t in fd:
            a *= 0.5
        cur = abs(pt) + abs(pu)
        forced = (t in fd) or (t in fn) or (cur == 0.0 and abs(a) + abs(b) > 0)
        if not forced and cur > 0 and abs(a - pt) + abs(b - pu) < BAND * cur:
            wt_o[i], wu_o[i] = pt, pu
            continue
        wt_o[i], wu_o[i] = a, b
        pt, pu = a, b
    return pd.DataFrame({"TLT": wt_o, "UUP": wu_o}, index=cal)


def build(o: pd.DataFrame, sc: pd.DataFrame, fomc, vol_lag: int = 1, C: pd.Series | None = None,
          date_col: str = "speech_date") -> dict:
    cal = o.index
    if C is None:
        C = consensus(cal, sc[date_col], sc["s"].to_numpy())
    z = expanding_z(C)
    r_t, r_u = oo_returns(o["TLT"]), oo_returns(o["UUP"])
    vol = mix_vol(r_t, r_u, lag=vol_lag)
    w = weights(cal, z, vol, fomc)
    return {"C": C, "z": z, "vol": vol, "w": w, "r_t": r_t, "r_u": r_u}


# ------------------------------------------------------------------ stand-alone accounting (theirs)
def standalone(b: dict, cost_mult: float = 1.0) -> pd.DataFrame:
    w, r_t, r_u = b["w"], b["r_t"], b["r_u"]
    dw = w.diff()
    dw.iloc[0] = w.iloc[0]
    cost = dw["TLT"].abs() * COST["TLT"] / 1e4 + dw["UUP"].abs() * COST["UUP"] / 1e4
    g = w["TLT"] * r_t + w["UUP"] * r_u
    return pd.DataFrame({"gross": g, "net1": g - cost, "net2": g - 2 * cost,
                         "tlt": w["TLT"] * r_t - dw["TLT"].abs() * COST["TLT"] / 1e4,
                         "uup": w["UUP"] * r_u - dw["UUP"].abs() * COST["UUP"] / 1e4,
                         "l1": dw.abs().sum(axis=1)})


# ------------------------------------------------------------------ engine accounting (ours)
def to_dec(w: pd.DataFrame) -> pd.DataFrame:
    """Engine convention: decision at close d holds the weight of the session after d."""
    return w.shift(-1)


def engine_run(w: pd.DataFrame, ohlc: dict, tbill: bool, cost_mult=1.0, cost=COST, exec_="next_open"):
    idx = ohlc["close"].index
    rf = E.load_rf("FWD").reindex(idx).ffill().fillna(0.0)
    rf_used = rf if tbill else rf * 0.0
    wd = to_dec(w).reindex(idx).fillna(0.0) if exec_ == "next_open" else w.reindex(idx).fillna(0.0)
    net, gross, to, held, c = E.simulate(wd, ohlc, rf_used, exec=exec_, cost_mult=cost_mult, cost_bps=cost)
    return {"net": net, "gross": gross, "ex": net - rf_used, "exg": gross - rf_used, "to": to, "held": held, "rf": rf}


# ------------------------------------------------------------------ stats
def sharpe(x: pd.Series) -> float:
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std(ddof=1) * math.sqrt(252)) if len(x) > 2 and x.std() > 0 else float("nan")


def win(x: pd.Series, name: str) -> pd.Series:
    a, b = WINDOWS[name]
    return x.loc[a:b]


def maxdd(x: pd.Series) -> float:
    eq = (1 + x.fillna(0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


def nw_t(x, lags=5):
    return E.newey_west_tstat(pd.Series(x).dropna(), lags)
