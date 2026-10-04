"""value_reversal: cross-asset value (5-year reversal), time-series bond value, and value + momentum (AMP 2013).

Implements SPEC.md exactly (rules fixed before results). Point-in-time: every decision at month-end close t uses
data up to t only (FRED yields up to t-1); fills at the close of t+1 (engine next_close).
Writes only under the scratchpad edges/value_reversal and edges/series folders.
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
assert os.environ.get("GQH_OOS_UNLOCK") != "1", "never unlock"

from src import calendar_utils as CU  # noqa: E402
from src import engine as E  # noqa: E402

OUT = Path(__file__).resolve().parent
SER = OUT.parent / "series"
SER.mkdir(parents=True, exist_ok=True)
RAW = Path("<home>/.cache/gqh/databento_raw/glbx_ohlcv1d_v01.parquet")

IS_END = pd.Timestamp("2024-10-02")
LATER_START = pd.Timestamp("2024-10-03")
LATER_END = pd.Timestamp("2026-10-02")

COM = ["CL", "HO", "RB", "NG", "GC", "SI", "PL", "HG", "ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE"]
FX = ["6E", "6J", "6B", "6A", "6C", "6S"]
EQ = ["ES", "NQ", "YM", "RTY"]
CLASSES = {"COM": [f"F_{r}" for r in COM], "FX": [f"F_{r}" for r in FX], "EQ": [f"F_{r}" for r in EQ]}
ZN = "F_ZN"
TICK = CLASSES["COM"] + CLASSES["FX"] + CLASSES["EQ"] + [ZN]

COST = {}
for r in ("ES", "NQ", "YM"):
    COST[f"F_{r}"] = 0.75
COST["F_RTY"] = 1.0
COST.update({"F_ZT": 0.3, "F_ZF": 0.5, "F_ZN": 1.0, "F_ZB": 1.25, "F_UB": 1.25})
for r in FX:
    COST[f"F_{r}"] = 0.75
for r in ("CL", "GC", "SI", "HG"):
    COST[f"F_{r}"] = 1.5
for r in ("NG", "HO", "RB", "PL"):
    COST[f"F_{r}"] = 2.5
for r in ("ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE"):
    COST[f"F_{r}"] = 4.0
COST["IEF"] = 3.0

TARGET = 0.10
COV_WINDOW = 252
COV_MIN = 60
EWMA_COM = 60
ACTIVE_WINDOW = 10
GROSS_CAP = 5.0
MIN_CLASS = 3
TD = 252

# ----------------------------------------------------------------------------------------------- data
ohlc = E.load_ohlc(TICK, "FWD")
cal = ohlc["close"].index
rf = E.load_rf("FWD").reindex(cal).ffill().fillna(0.0)
close = ohlc["close"]
ex = close.pct_change(fill_method=None).sub(rf, axis=0)
first_valid = {c: close[c].first_valid_index() for c in TICK}
xr = (1 + ex.fillna(0.0)).cumprod()
for c in TICK:
    xr.loc[xr.index < first_valid[c], c] = np.nan
vol = np.sqrt(ex.pow(2).ewm(com=EWMA_COM, min_periods=60).mean() * TD)
active = (ohlc["volume"].fillna(0.0) > 0).astype(float).rolling(ACTIVE_WINDOW, min_periods=1).max().astype(bool)

raw = pd.read_parquet(RAW, columns=["ts_event", "close", "symbol"])
raw = raw[raw["symbol"].str.endswith(".v.0")].copy()
raw["date"] = raw["ts_event"].dt.tz_convert(None).dt.normalize()
raw["root"] = raw["symbol"].str.split(".").str[0]
spot_raw = raw.pivot_table(index="date", columns="root", values="close", aggfunc="last").sort_index()
spot = spot_raw.reindex(cal, method="ffill", tolerance=pd.Timedelta("7D"))
spot = spot.rename(columns=lambda r: f"F_{r}")

mo = CU.month_offsets(cal)
me = mo.index[(mo["off_own"] == 0)]
me = me[me >= pd.Timestamp("2010-06-30")]

# month-end levels: commodities use the front-contract ("spot") price, FX/equity the excess-return index
L = pd.DataFrame(index=me)
for c in CLASSES["COM"]:
    L[c] = spot.loc[me, c]
for c in CLASSES["FX"] + CLASSES["EQ"] + [ZN]:
    L[c] = xr.loc[me, c]
LXR = xr.loc[me, TICK]


def value_signal(Lv: pd.DataFrame, kind: str) -> pd.DataFrame:
    lg = np.log(Lv)
    if kind == "VW1":
        avg = Lv.rolling(13, min_periods=13).mean().shift(54)       # month-end levels t-66 .. t-54
        return np.log(avg) - lg
    if kind == "VW2":
        return lg.shift(60) - lg
    if kind == "VW3":
        return lg.shift(66) - lg.shift(6)
    raise ValueError(kind)


SIG = {k: value_signal(L, k) for k in ("VW1", "VW2", "VW3")}
MOM = np.log(LXR).shift(1) - np.log(LXR).shift(12)                 # MOM2-12 on the excess-return index

fred = E.load_series("fred_daily.parquet", "FWD")


def fred_dev(series: pd.Series) -> pd.Series:
    """Deviation from the trailing 1,260-observation mean, as known at the close of each NYSE date (obs < date)."""
    s = series.dropna()
    dev = s - s.rolling(1260, min_periods=1260).mean()
    out = dev.reindex(cal - pd.Timedelta(days=1), method="ffill")
    out.index = cal
    return out


BOND_DEV = {"B1": fred_dev(fred["DGS10"]), "B2": fred_dev(fred["DGS10"] - fred["DGS2"])}


# ----------------------------------------------------------------------------------------------- construction
def scale(w: pd.Series, t: pd.Timestamp, exr: pd.DataFrame, target: float = TARGET, cap: float | None = None):
    cols = [c for c in w.index if w[c] != 0 and np.isfinite(w[c])]
    if not cols:
        return None
    cov = exr.loc[:t, cols].tail(COV_WINDOW).cov(min_periods=COV_MIN).fillna(0.0).to_numpy()
    v = w[cols].to_numpy()
    var = float(v @ cov @ v) * TD
    if not np.isfinite(var) or var <= 0:
        return None
    out = w.fillna(0.0) * (target / math.sqrt(var))
    if cap is not None:
        g = out.abs().sum()
        if g > cap:
            out = out * (cap / g)
    return out


def eligible(t, cols):
    return [c for c in cols if np.isfinite(vol.at[t, c]) and vol.at[t, c] > 0 and bool(active.at[t, c])]


def xs_sleeve(sig_row: pd.Series, cols: list[str], t) -> pd.Series | None:
    el = [c for c in eligible(t, cols) if np.isfinite(sig_row.get(c, np.nan))]
    if len(el) < MIN_CLASS:
        return None
    rk = sig_row[el].rank()
    raw_w = (rk - rk.mean()) / vol.loc[t, el]
    w = pd.Series(0.0, index=TICK)
    w[el] = raw_w
    return scale(w, t, ex)


def ts_sleeve(sign: float, col: str, t) -> pd.Series | None:
    if not np.isfinite(sign) or sign == 0 or not eligible(t, [col]):
        return None
    w = pd.Series(0.0, index=TICK)
    w[col] = float(np.sign(sign))
    return scale(w, t, ex)


def combine(sleeves: list[pd.Series | None], t) -> pd.Series | None:
    s = [x for x in sleeves if x is not None]
    if not s:
        return None
    tot = sum(s)
    return scale(tot, t, ex, cap=GROSS_CAP)


def mix(a, b, t):
    """0.5 a + 0.5 b inside a class, rescaled to 10 %; if one is missing the other is used."""
    if a is None and b is None:
        return None
    if a is None or b is None:
        return a if b is None else b
    return scale(0.5 * a + 0.5 * b, t, ex)


VW1_START = SIG["VW1"].dropna(how="all").index.min()
print("first VW1 decision", VW1_START.date())

dec = {}          # name -> {t: Series}
diag = {}         # per-class diagnostic sleeves
names_xs = ["VAL_XS_VW1", "VAL_XS_VW2", "VAL_XS_VW3", "MOM_XS", "COMBO_XS", "VAL_ALL", "COMBO_ALL", "MOM_XS_FULL"]
for n in names_xs + ["BOND_B1", "BOND_B2"]:
    dec[n] = {}
for k in CLASSES:
    for kind in ("VAL", "MOM", "COMBO"):
        diag[f"{kind}_{k}"] = {}
for kind in ("BOND_B1", "BOND_TSMOM"):
    diag[kind] = {}

for t in me:
    i = me.get_loc(t)
    # bonds (available from 2010)
    b = {}
    for bk in ("B1", "B2"):
        b[bk] = ts_sleeve(BOND_DEV[bk].at[t], ZN, t)
        if b[bk] is not None:
            dec[f"BOND_{bk}"][t] = scale(b[bk], t, ex, cap=GROSS_CAP)
    tsm = ts_sleeve(MOM.at[t, ZN], ZN, t)
    if b["B1"] is not None:
        diag["BOND_B1"][t] = b["B1"]
    if tsm is not None:
        diag["BOND_TSMOM"][t] = tsm
    # momentum over its own full history (descriptive)
    mom_cls = {k: xs_sleeve(MOM.loc[t], cols, t) for k, cols in CLASSES.items()}
    m_full = combine(list(mom_cls.values()), t)
    if m_full is not None:
        dec["MOM_XS_FULL"][t] = m_full
    if t < VW1_START:
        continue
    val_cls = {kind: {k: xs_sleeve(SIG[kind].loc[t], cols, t) for k, cols in CLASSES.items()}
               for kind in ("VW1", "VW2", "VW3")}
    for kind in ("VW1", "VW2", "VW3"):
        w = combine(list(val_cls[kind].values()), t)
        if w is not None:
            dec[f"VAL_XS_{kind}"][t] = w
    if m_full is not None:
        dec["MOM_XS"][t] = m_full
    combo_cls = {k: mix(val_cls["VW1"][k], mom_cls[k], t) for k in CLASSES}
    w = combine(list(combo_cls.values()), t)
    if w is not None:
        dec["COMBO_XS"][t] = w
    w = combine(list(val_cls["VW1"].values()) + [b["B1"]], t)
    if w is not None:
        dec["VAL_ALL"][t] = w
    bond_combo = mix(b["B1"], tsm, t)
    w = combine(list(combo_cls.values()) + [bond_combo], t)
    if w is not None:
        dec["COMBO_ALL"][t] = w
    for k in CLASSES:
        for kind, src in (("VAL", val_cls["VW1"]), ("MOM", mom_cls), ("COMBO", combo_cls)):
            if src[k] is not None:
                diag[f"{kind}_{k}"][t] = src[k]


def to_wdec(d: dict) -> pd.DataFrame:
    """Month-end decisions -> daily decision frame on the NYSE calendar. A month-end without a valid
    decision (after the first one) is flat."""
    w = pd.DataFrame(np.nan, index=cal, columns=TICK)
    if not d:
        return w.fillna(0.0)
    first = min(d)
    for t in me[me >= first]:
        w.loc[t] = d[t].reindex(TICK).fillna(0.0).values if t in d else 0.0
    return w.ffill().fillna(0.0)


def run(d: dict, tickers=TICK, ohlc_=None, rf_=None):
    w = to_wdec(d)
    ohlc_ = ohlc if ohlc_ is None else ohlc_
    rf_ = rf if rf_ is None else rf_
    out = {}
    for lab, cm in (("net_1x", 1.0), ("net_2x", 2.0)):
        net, gross, turn, held, cost = E.simulate(w[tickers], ohlc_, rf_, exec="next_close", cost_mult=cm,
                                                  cost_bps=COST)
        out[lab] = net - rf_.reindex(net.index).fillna(0.0)
        if lab == "net_1x":
            out["gross"] = gross - rf_.reindex(gross.index).fillna(0.0)
            out["turnover"] = turn
            out["held"] = held
    return out


# ----------------------------------------------------------------------------------------------- IEF long-history bond check
ief = E.load_ohlc(["IEF"], "FWD")
ief_cal = ief["close"].index
ief_rf = E.load_rf("FWD").reindex(ief_cal).ffill().fillna(0.0)
ief_ex = ief["close"]["IEF"].pct_change(fill_method=None) - ief_rf
ief_ex_df = ief_ex.to_frame("IEF")
ief_vol = np.sqrt(ief_ex.pow(2).ewm(com=EWMA_COM, min_periods=60).mean() * TD)
ief_me = CU.month_offsets(ief_cal)
ief_me = ief_me.index[ief_me["off_own"] == 0]
d_ief = {}
for t in ief_me:
    s = BOND_DEV["B1"].get(t, np.nan)
    if not np.isfinite(s) or s == 0 or not (np.isfinite(ief_vol.get(t, np.nan)) and ief_vol[t] > 0):
        continue
    w = pd.Series({"IEF": float(np.sign(s))})
    w = scale(w, t, ief_ex_df, cap=GROSS_CAP)
    if w is not None:
        d_ief[t] = w


def run_ief(d):
    w = pd.DataFrame(np.nan, index=ief_cal, columns=["IEF"])
    first = min(d)
    for t in ief_me[ief_me >= first]:
        w.loc[t, "IEF"] = d[t]["IEF"] if t in d else 0.0
    w = w.ffill().fillna(0.0)
    out = {}
    for lab, cm in (("net_1x", 1.0), ("net_2x", 2.0)):
        net, gross, turn, held, cost = E.simulate(w, ief, ief_rf, exec="next_close", cost_mult=cm, cost_bps=COST)
        out[lab] = net - ief_rf
        if lab == "net_1x":
            out["gross"] = gross - ief_rf
            out["turnover"] = turn
            out["held"] = held
    return out


# ----------------------------------------------------------------------------------------------- run everything
results = {}
for n, d in dec.items():
    results[n] = run(d)
    print("ran", n, len(d), "decisions")
results["BOND_B1_IEF"] = run_ief(d_ief)
diag_res = {n: run(d) for n, d in diag.items()}
print("ran diagnostics")

pd.to_pickle({"results": results, "diag": diag_res, "VW1_START": VW1_START, "dec_counts": {k: len(v) for k, v in dec.items()}},
             OUT / "results.pkl")
print("saved", OUT / "results.pkl")
