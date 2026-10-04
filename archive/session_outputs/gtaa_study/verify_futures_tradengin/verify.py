"""Independent recomputation of the headline numbers of the futures_tradengin study."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

import mylib as M

cal = M.calendar()
rf = M.rf_series(cal)
fp = M.wide("futures_daily.parquet", M.FUT, cal)
ep = M.wide("etf_daily.parquet", M.ETF5, cal)
fc = fp["close"]
ex = fc.pct_change(fill_method=None).sub(rf, axis=0)
ME = M.month_ends(cal)


# ---------------------------------------------------------------- signals (point in time by construction)
def sma_on(level: pd.DataFrame, n=10):
    """At each month-end t: level_t > mean(level at the last n month-ends incl. t). Only rows <= t used."""
    m = level.reindex(ME)
    s = m.rolling(n, min_periods=n).mean()
    valid = s.notna() & m.notna()
    return ((m > s) & valid).astype(float), valid.astype(float)


def to_daily(wme: pd.DataFrame):
    W = pd.DataFrame(np.nan, index=cal, columns=wme.columns)
    W.loc[wme.index] = wme.values
    return W.ffill().fillna(0.0)


# ---------------------------------------------------------------- futures risk parity (own build from the S1 spec)
traded = (fp["volume"].fillna(0) > 0).astype(float).rolling(10, min_periods=1).max() > 0
vol = np.sqrt((ex ** 2).ewm(com=60, min_periods=60).mean() * 252)
cnt = ex.notna().cumsum()


def scale10(w, t, cols_all):
    nz = [c for c in cols_all if w[c] != 0]
    if not nz:
        return w * 0
    cv = ex.loc[:t, nz].tail(252).cov(min_periods=60).fillna(0).to_numpy()
    v = w[nz].to_numpy()
    s = math.sqrt(float(v @ cv @ v) * 252)
    w = w * (0.10 / s)
    g = w.abs().sum()
    return w * 3 / g if g > 3 else w


def rp_book(tick, sig=None, mode="fixed", s1=False):
    rows = {}
    for t in ME:
        el = [c for c in tick if cnt.loc[t, c] >= 300 and np.isfinite(vol.loc[t, c]) and vol.loc[t, c] > 0
              and traded.loc[t, c]]
        w = pd.Series(0.0, index=tick)
        if el:
            base = 0.40 / vol.loc[t, el] / len(el)
            if s1:
                h = ex.loc[:t, el]
                sg = sum(np.sign((1 + h.tail(k).fillna(0)).prod() - 1) for k in (21, 63, 252)) / 3
                w[el] = (sg * base).values
                w = scale10(w, t, tick)
            else:
                w[el] = base.values
                if sig is None:
                    w = scale10(w, t, tick)
                elif mode == "fixed":
                    w = scale10(w, t, tick) * sig.loc[t].reindex(tick).fillna(0)
        rows[t] = w
    return to_daily(pd.DataFrame(rows).T)


on30, val30 = sma_on(fc)
ls30 = val30 * (2 * on30 - 1)

V = {}
V["A1"] = M.sim_next_close(rp_book(M.FUT), fc, rf, M.FCOST, fp["roll"])
V["B1"] = M.sim_next_close(rp_book(M.FUT, on30), fc, rf, M.FCOST, fp["roll"])
V["E1"] = M.sim_next_close(rp_book(M.FUT, ls30), fc, rf, M.FCOST, fp["roll"])
W_S1 = rp_book(M.FUT, s1=True)
V["S1"] = M.sim_next_close(W_S1, fc, rf, M.FCOST, fp["roll"])

# ---------------------------------------------------------------- 3-sleeve futures GTAA (C1/C3/C5)
c6 = fc[["F_ES", "F_ZN", "F_CL", "F_GC", "F_HG", "F_ZC"]].ffill(limit=5)
r6 = c6.pct_change(fill_method=None)
com = ["F_CL", "F_GC", "F_HG", "F_ZC"]
basket = (1 + r6[com].mean(axis=1, skipna=False).fillna(0)).cumprod()
basket[r6[com].notna().all(axis=1).cumsum() == 0] = np.nan
lvl = pd.DataFrame({"ES": c6["F_ES"], "ZN": c6["F_ZN"], "COM": basket})
on3, val3 = sma_on(lvl)


def fut3(sig, slot=0.2):
    w = pd.DataFrame(0.0, index=sig.index, columns=["F_ES", "F_ZN"] + com)
    w["F_ES"] = slot * sig["ES"]
    w["F_ZN"] = slot * sig["ZN"]
    for c in com:
        w[c] = slot / 4 * sig["COM"]
    return to_daily(w)


W_C1 = fut3(on3)
V["C1"] = M.sim_next_close(W_C1, fc, rf, M.FCOST, fp["roll"])
V["C3"] = M.sim_next_close(fut3(val3), fc, rf, M.FCOST, fp["roll"])
V["C5"] = M.sim_next_close(fut3(val3 * (2 * on3 - 1)), fc, rf, M.FCOST, fp["roll"])
# same-close diagnostic (not tradeable): decision held over the return day right after its close
V["C1_sameclose"] = M.sim_next_close(W_C1.shift(-1).ffill(), fc, rf, M.FCOST, fp["roll"])
# stricter execution: one extra day of delay
V["C1_lag1"] = M.sim_next_close(W_C1.shift(1).fillna(0), fc, rf, M.FCOST, fp["roll"])
V["B1_sameclose"] = M.sim_next_close(rp_book(M.FUT, on30).shift(-1).ffill(), fc, rf, M.FCOST, fp["roll"])

# ---------------------------------------------------------------- ETF S3 / BH5 / LS5
eon, eval_ = sma_on(ep["close"])
W_S3 = to_daily(eon * 0.2)
W_BH5 = to_daily(eval_ * 0.2)
W_LS5 = to_daily(eval_ * (2 * eon - 1) * 0.2)
V["S3"] = M.sim_next_open(W_S3, ep["open"], ep["close"], rf, M.ECOST)
V["BH5"] = M.sim_next_open(W_BH5, ep["open"], ep["close"], rf, M.ECOST)
V["LS5"] = M.sim_next_open(W_LS5, ep["open"], ep["close"], rf, M.ECOST)
V["S3_nextclose"] = M.sim_next_close(W_S3, ep["close"], rf, M.ECOST)

rows = []
for k, (net, gross, turn, H) in V.items():
    for wl, w in (("IS_F", M.IS_F), ("OOS", M.OOS)) + ((("IS_E", M.IS_E),) if k.startswith(("S3", "BH5", "LS5")) else ()):
        st = M.stats(net, rf, turn, w)
        stg = M.sharpe((gross - rf).loc[w[0]:w[1]])
        rows.append({"v": k, "win": wl, **st, "sharpe_gross": stg})
tab = pd.DataFrame(rows)
tab.to_csv(M.OUT / "my_variants.csv", index=False)
pd.set_option("display.width", 220)
print(tab.round(3).to_string(index=False))

# ---------------------------------------------------------------- frozen-code cross-checks (repo used ONLY for comparison)
import sys
sys.path.insert(0, r"<solo-repo>")
from src import forward2 as F2
from src import forward as F1mod

chk = {}
for nm, mine in (("S1", "S1"), ("S3", "S3"), ("BH5", "BH5"), ("LONG_ONLY_F", "A1")):
    fr = F2.returns(nm, "FWD")
    a = V[mine][0].reindex(fr.index)
    chk[nm] = {"max_abs_daily_diff": float((a - fr).abs().loc["2005-11-01":].max()),
               "sharpe_frozen_IS": M.sharpe((fr - rf.reindex(fr.index)).loc[M.IS_E[0] if nm in ("S3", "BH5") else M.IS_F[0]:M.IS_F[1]])}
print(json.dumps(chk, indent=1))

# ---------------------------------------------------------------- identity / decomposition
def gx(k, w):
    return (V[k][1] - rf).loc[w[0]:w[1]]

dec = {}
for wl, w in (("IS_F", M.IS_F), ("IS_E", M.IS_E), ("OOS", M.OOS)):
    s3, bh, ls = gx("S3", w), gx("BH5", w), gx("LS5", w)
    dec[wl] = {"S3_gross_ex_ann": s3.mean() * 252, "half_BH": 0.5 * bh.mean() * 252, "half_LS": 0.5 * ls.mean() * 252,
               "share_BH": 0.5 * bh.mean() / s3.mean(), "ident_maxdev": float((s3 - 0.5 * bh - 0.5 * ls).abs().max()),
               "corr_BH_LS": float(bh.corr(ls))}
    # drift vs timing with held weights x close-to-close excess
    H = V["S3"][3].loc[w[0]:w[1]]
    R = ep["close"].pct_change(fill_method=None).sub(rf, axis=0).loc[w[0]:w[1]].fillna(0)
    tot = (H * R).sum(axis=1).mean() * 252
    drift = (H.mean() * R.mean()).sum() * 252
    dec[wl].update({"dt_total": tot, "drift": drift, "timing": tot - drift})
print(json.dumps(dec, indent=1, default=float))

# regression S3 on ES, ZN futures excess (IS_F), HAC
import statsmodels.api as sm
y = (V["S3"][0] - rf).loc[M.IS_F[0]:M.IS_F[1]]
X = pd.DataFrame({"ES": ex["F_ES"], "ZN": ex["F_ZN"]}).loc[y.index]
d = pd.concat([y.rename("y"), X], axis=1).dropna()
fit = sm.OLS(d.y, sm.add_constant(d[["ES", "ZN"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
reg = {"alpha_ann": fit.params["const"] * 252, "alpha_t": fit.tvalues["const"], "bES": fit.params["ES"],
       "bZN": fit.params["ZN"], "r2": fit.rsquared}
print("S3 on ES/ZN", reg)

# rolling 2y Sharpe of S3 before OOS
xs3 = (V["S3"][0] - rf).loc[M.IS_E[0]:M.IS_E[1]]
roll = xs3.rolling(504).mean() / xs3.rolling(504).std() * math.sqrt(252)
roll = roll.dropna()
rr = {"n": len(roll), "median": roll.median(), "p10": roll.quantile(.1), "p90": roll.quantile(.9),
      "frac_ge_070": float((roll >= 0.70).mean()),
      "frac_ge_070_nonoverlap": float((roll.iloc[::504] >= 0.70).mean()), "n_nonoverlap": len(roll.iloc[::504])}
print("rolling", rr)

# ---------------------------------------------------------------- bootstraps
f1 = F1mod.returns("F1", "FWD")
xf1 = (f1 - rf.reindex(f1.index))
boot = {}
for wl, w in (("OOS", M.OOS), ("IS_F", M.IS_F)):
    X = pd.DataFrame({"S3": (V["S3"][0] - rf), "F1": xf1, "C1": V["C1"][0] - rf, "C3": V["C3"][0] - rf,
                      "B1": V["B1"][0] - rf, "E1": V["E1"][0] - rf, "S1": V["S1"][0] - rf,
                      "BH5": V["BH5"][0] - rf}).loc[w[0]:w[1]].dropna()
    pt = X.mean() / X.std() * math.sqrt(252)
    for L in (63, 21):
        S = M.block_boot(X, L=L, B=4000, seed=2026)
        col = {c: i for i, c in enumerate(X.columns)}
        for a, b in (("S3", "F1"), ("C1", "C3"), ("C1", "S3"), ("B1", "E1"), ("B1", "S1"), ("S3", "BH5")):
            dd = S[:, col[a]] - S[:, col[b]]
            boot[f"{wl}|L{L}|{a}-{b}"] = {"diff": float(pt[a] - pt[b]), "lo": float(np.percentile(dd, 2.5)),
                                         "hi": float(np.percentile(dd, 97.5)), "p_le0": float((dd <= 0).mean())}
    boot[f"{wl}|F1_sharpe"] = float(pt["F1"])
print(json.dumps(boot, indent=1))

# ---------------------------------------------------------------- point-in-time truncation test of my C1 / B1 / S3 decisions
def c1_dec_trunc(tcut):
    lv = lvl.loc[:tcut]
    me = ME[ME <= tcut]
    m = lv.reindex(me)
    s = m.rolling(10, min_periods=10).mean()
    return ((m > s) & s.notna()).astype(float).iloc[-1]

bad = 0
tested = 0
for t in ME[(ME > "2011-06-01") & (ME < "2026-09-30")][::7]:
    a = c1_dec_trunc(t)
    b = on3.loc[t]
    bad += int((a != b).sum())
    tested += 1
print("truncation test C1 signal: tested", tested, "mismatches", bad)

# impulse test: a +50% shock to F_ES close on day t only: which return day of C1 held weight sees it?
H = V["C1"][3]
t0 = pd.Timestamp("2020-06-30")
i = cal.get_loc(t0)
print("C1 decision row at", t0, W_C1.loc[t0].round(3).to_dict())
print("held rows t0..t0+2:", H.iloc[i:i + 3]["F_ES"].round(3).tolist(), "W rows t0-2..t0:", W_C1.iloc[i - 2:i + 1]["F_ES"].tolist())

json.dump({"check_vs_frozen": chk, "decomp": dec, "reg": reg, "rolling": rr, "boot": boot},
          open(M.OUT / "verify_summary.json", "w"), indent=1, default=float)
