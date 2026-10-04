"""Independent re-implementation of the value_reversal SPEC (verification only).
Own data loading (parquet directly), own month-end calendar, own signals, own simulator.
No repo writes, no logging, no OOS unlock."""
import math
from pathlib import Path

import numpy as np
import pandas as pd

D = Path("<home>/.cache/gqh")
OUT = Path(__file__).resolve().parent
IS_END = pd.Timestamp("2024-10-02")
LAT0 = pd.Timestamp("2024-10-03")
LAT1 = pd.Timestamp("2026-10-02")
COM = ["CL", "HO", "RB", "NG", "GC", "SI", "PL", "HG", "ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE"]
FX = ["6E", "6J", "6B", "6A", "6C", "6S"]
EQ = ["ES", "NQ", "YM", "RTY"]
CLS = {"COM": COM, "FX": FX, "EQ": EQ}
ALL = COM + FX + EQ + ["ZN"]
COST = {**{r: 0.75 for r in ["ES", "NQ", "YM"] + FX}, "RTY": 1.0, "ZN": 1.0,
        **{r: 1.5 for r in ["CL", "GC", "SI", "HG"]}, **{r: 2.5 for r in ["NG", "HO", "RB", "PL"]},
        **{r: 4.0 for r in ["ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE"]}}

fu = pd.read_parquet(D / "futures_daily.parquet")
fu["date"] = pd.to_datetime(fu["date"])
fu = fu[fu.date <= LAT1].copy()
fu["r"] = fu.ticker.str[2:]
close = fu.pivot(index="date", columns="r", values="close")[ALL].sort_index()
volu = fu.pivot(index="date", columns="r", values="volume")[ALL].reindex(close.index)
roll = fu.pivot(index="date", columns="r", values="roll")[ALL].reindex(close.index).fillna(0.0)
cal = close.index
rfd = pd.read_parquet(D / "rf_daily.parquet")
if "date" in rfd.columns:
    rfd = rfd.set_index(pd.to_datetime(rfd["date"]))
rf = rfd["rf"].reindex(cal).ffill().fillna(0.0)
ex = close.ffill(limit=5).pct_change(fill_method=None).sub(rf, axis=0)
first = close.apply(lambda s: s.first_valid_index())
xr = (1 + ex.fillna(0)).cumprod()
for c in ALL:
    xr.loc[xr.index < first[c], c] = np.nan
vol = np.sqrt((ex ** 2).ewm(com=60, min_periods=60).mean() * 252)
act = (volu.fillna(0) > 0).astype(float).rolling(10, min_periods=1).max().astype(bool)

me = pd.DatetimeIndex(pd.Series(cal, index=cal).groupby([cal.year, cal.month]).max().values)

raw = pd.read_parquet(D / "databento_raw/glbx_ohlcv1d_v01.parquet", columns=["ts_event", "close", "symbol"])
raw["d"] = raw.ts_event.dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()
raw["root"] = raw.symbol.str.split(".").str[0]


def spot_from(suffix):
    x = raw[raw.symbol.str.endswith(suffix)]
    p = x.pivot_table(index="d", columns="root", values="close", aggfunc="last").sort_index()
    return p.reindex(cal, method="ffill", tolerance=pd.Timedelta("7D"))


spot0 = spot_from(".v.0")
spot1 = spot_from(".v.1")


def levels(spot):
    L = pd.DataFrame(index=me)
    for c in COM:
        L[c] = spot.loc[me, c].values
    for c in FX + EQ + ["ZN"]:
        L[c] = xr.loc[me, c].values
    return L


L0 = levels(spot0)
L1 = levels(spot1)


def vsig(L, k):
    lg = np.log(L)
    if k == "VW1":
        return np.log(L.rolling(13, min_periods=13).mean().shift(54)) - lg
    if k == "VW2":
        return lg.shift(60) - lg
    if k == "VW3":
        return lg.shift(66) - lg.shift(6)


LX = xr.loc[me, ALL]
MOM = np.log(LX).shift(1) - np.log(LX).shift(12)

fred = pd.read_parquet(D / "fred_daily.parquet")
fred = fred.set_index(pd.to_datetime(fred["date"])).sort_index()


def dev_asof(s):
    s = s.dropna()
    dv = (s - s.rolling(1260, min_periods=1260).mean()).dropna()
    pos = np.searchsorted(dv.index.values, cal.values, side="left") - 1   # strictly before d
    return pd.Series(np.where(pos >= 0, dv.values[np.clip(pos, 0, None)], np.nan), index=cal)


BD = {"B1": dev_asof(fred["DGS10"]), "B2": dev_asof(fred["DGS10"] - fred["DGS2"])}


def scale(w, t, cap=None):
    w = w[(w != 0) & np.isfinite(w)]
    if w.empty:
        return None
    sub = ex.loc[:t, w.index].tail(252)
    cov = sub.cov(min_periods=60).fillna(0.0).values
    var = float(w.values @ cov @ w.values) * 252
    if not np.isfinite(var) or var <= 0:
        return None
    o = w * (0.10 / math.sqrt(var))
    if cap is not None and o.abs().sum() > cap:
        o = o * (cap / o.abs().sum())
    return o


def elig(t, cols):
    return [c for c in cols if np.isfinite(vol.at[t, c]) and vol.at[t, c] > 0 and act.at[t, c]]


def xs(row, cols, t, risk_units=True):
    el = [c for c in elig(t, cols) if np.isfinite(row.get(c, np.nan))]
    if len(el) < 3:
        return None
    rk = row[el].rank()
    w = rk - rk.mean()
    if risk_units:
        w = w / vol.loc[t, el]
    return scale(w, t)


def ts(sg, c, t):
    if not np.isfinite(sg) or sg == 0 or not elig(t, [c]):
        return None
    return scale(pd.Series({c: float(np.sign(sg))}), t)


def add(sl):
    sl = [s for s in sl if s is not None]
    if not sl:
        return None
    return pd.concat(sl, axis=1).fillna(0).sum(axis=1)


def comb(sl, t):
    s = add(sl)
    return None if s is None else scale(s, t, cap=5.0)


def mix(a, b, t):
    if a is None:
        return b
    if b is None:
        return a
    return scale(add([0.5 * a, 0.5 * b]), t)


def build(L, risk_units=True):
    S = {k: vsig(L, k) for k in ("VW1", "VW2", "VW3")}
    start = S["VW1"].dropna(how="all").index.min()
    names = ["VW1", "VW2", "VW3", "MOM_XS", "COMBO_XS", "VAL_ALL", "COMBO_ALL", "B1", "B2",
             "VAL_COM", "VAL_FX", "VAL_EQ"]
    dec = {n: {} for n in names}
    for t in me:
        b = {k: ts(BD[k].at[t], "ZN", t) for k in ("B1", "B2")}
        for k in b:
            if b[k] is not None:
                dec[k][t] = b[k]
        if t < start:
            continue
        tsm = ts(MOM.at[t, "ZN"], "ZN", t)
        vc = {k: {c: xs(S[k].loc[t], cols, t, risk_units) for c, cols in CLS.items()} for k in S}
        mc = {c: xs(MOM.loc[t], cols, t, risk_units) for c, cols in CLS.items()}
        for k in S:
            w = comb(list(vc[k].values()), t)
            if w is not None:
                dec[k][t] = w
        for c in CLS:
            if vc["VW1"][c] is not None:
                dec[f"VAL_{c}"][t] = vc["VW1"][c]
        w = comb(list(mc.values()), t)
        if w is not None:
            dec["MOM_XS"][t] = w
        cc = {c: mix(vc["VW1"][c], mc[c], t) for c in CLS}
        w = comb(list(cc.values()), t)
        if w is not None:
            dec["COMBO_XS"][t] = w
        w = comb(list(vc["VW1"].values()) + [b["B1"]], t)
        if w is not None:
            dec["VAL_ALL"][t] = w
        w = comb(list(cc.values()) + [mix(b["B1"], tsm, t)], t)
        if w is not None:
            dec["COMBO_ALL"][t] = w
    return dec, start


def sim(d, mult=1.0, drift=False):
    """Decision at month-end t, filled at the close of the next session, earns from the session after."""
    t0 = min(d)
    tgt = pd.DataFrame(np.nan, index=cal, columns=ALL)
    for t in me[me >= t0]:
        tgt.loc[t] = d[t].reindex(ALL).fillna(0).values if t in d else 0.0
    tgt = tgt.ffill().fillna(0.0)
    fill = tgt.shift(1).fillna(0.0)        # target after trading at the close of each session
    r = ex.fillna(0.0)
    cb = pd.Series(COST).reindex(ALL) * mult / 1e4
    if not drift:
        held = fill.shift(1).fillna(0.0)
        port = (held * r).sum(axis=1)
        drifted = (held * (1 + r)).div(1 + port, axis=0)
        trade = (fill - drifted).abs()
        cost = (trade * cb).sum(axis=1) + (2 * held.abs() * roll * cb).sum(axis=1)
        return port - cost, port
    rv, fv, rl, cbv = r.values, fill.values, roll.values, cb.values
    chg = (fill.diff().abs().sum(axis=1) > 0).values
    h = np.zeros(len(ALL))
    n = len(cal)
    pr = np.zeros(n)
    cs = np.zeros(n)
    for i in range(n):
        pr[i] = h @ rv[i]
        hd = h * (1 + rv[i]) / (1 + pr[i])
        cs[i] = (2 * np.abs(h) * rl[i] * cbv).sum()
        if chg[i]:
            cs[i] += (np.abs(fv[i] - hd) * cbv).sum()
            h = fv[i].copy()
        else:
            h = hd
    return pd.Series(pr - cs, index=cal), pd.Series(pr, index=cal)


def sr(x):
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(252)) if x.std() > 0 else np.nan


def mdd(x):
    e = (1 + x).cumprod()
    return float((e / e.cummax() - 1).min())


def nwt(x):
    x = x.dropna().values
    n = len(x)
    L = int(4 * (n / 100) ** (2 / 9))
    e = x - x.mean()
    s = e @ e / n
    for k in range(1, L + 1):
        s += 2 * (1 - k / (L + 1)) * (e[k:] @ e[:-k]) / n
    return float(x.mean() / math.sqrt(s / n))


res = {}
rows = []


def report(name, d, tag, live0=None):
    n1, g = sim(d, 1.0)
    n2, _ = sim(d, 2.0)
    nd, _ = sim(d, 1.0, drift=True)
    live = live0 if live0 is not None else min(d)
    s0 = cal[cal.get_loc(live) + 2]
    res[(tag, name)] = pd.DataFrame({"net_1x": n1, "net_2x": n2, "gross": g, "net_1x_drift": nd})
    for win, a, b in (("IS", s0, IS_END), ("LATER", LAT0, LAT1)):
        x1 = n1.loc[a:b]
        y = x1.groupby(x1.index.year).apply(lambda s: (1 + s).prod() - 1)
        rows.append(dict(tag=tag, cand=name, win=win, start=str(x1.index[0].date()), yrs=round(len(x1) / 252, 2),
                         sr1=sr(x1), sr2=sr(n2.loc[a:b]), srg=sr(g.loc[a:b]), sr_drift=sr(nd.loc[a:b]),
                         vol=float(x1.std() * math.sqrt(252)), mdd=mdd(x1), nwt=nwt(x1), worst_y=float(y.min())))


dec0, start = build(L0)
print("first VW1 decision", start.date())
for n in ["VW1", "VW2", "VW3", "MOM_XS", "COMBO_XS", "VAL_ALL", "COMBO_ALL", "VAL_COM", "VAL_FX", "VAL_EQ"]:
    report(n, dec0[n], "spec_v0", start)
for n in ["B1", "B2"]:
    report(n, dec0[n], "spec_v0")
# robustness rows (verification only, not candidates)
dec1, _ = build(L1)
for n in ["VW1", "COMBO_XS", "COMBO_ALL", "VAL_COM"]:
    report(n, dec1[n], "spot_v1", start)
decd, _ = build(L0, risk_units=False)
for n in ["VW1", "MOM_XS", "COMBO_XS", "COMBO_ALL", "VAL_COM"]:
    report(n, decd[n], "dollar_rank", start)
tab = pd.DataFrame(rows)
tab.to_csv(OUT / "indep_table.csv", index=False, float_format="%.4f")
pd.to_pickle(res, OUT / "indep_series.pkl")
pd.to_pickle({"dec0": dec0, "start": start}, OUT / "indep_dec.pkl")
pd.set_option("display.width", 250)
print(tab.round(3).to_string(index=False))
