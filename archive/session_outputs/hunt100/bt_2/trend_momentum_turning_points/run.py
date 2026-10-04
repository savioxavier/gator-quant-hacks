"""Momentum turning points (Garg et al.; Goulding-Harvey-Mazzoleni) on 30 CME futures. See SPEC.md (pre-registered)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import bt_common as B  # noqa: E402

SID = "trend_momentum_turning_points"
pan = B.Panel()
I = B.excess_index(pan)
me = pan.me
Im = I.loc[me]
M = Im / Im.shift(1) - 1                       # monthly excess return ending at each month-end (NaN if partial)


def trailing(k):
    """Cumulative excess return over the last k complete months ending at each month-end (NaN if any missing)."""
    lg = np.log1p(M)
    s = lg.rolling(k, min_periods=k).sum()
    return np.expm1(s)


R12 = trailing(12)
SLOW = np.where(R12 >= 0, 1.0, -1.0)
SLOW = pd.DataFrame(SLOW, index=me, columns=pan.tickers).where(R12.notna())


def fast(kf):
    R = trailing(kf)
    return pd.DataFrame(np.where(R >= 0, 1.0, -1.0), index=me, columns=pan.tickers).where(R.notna() & R12.notna())


def state(slow, fst):
    # 0 Bull, 1 Correction, 2 Bear, 3 Rebound
    st = pd.DataFrame(np.nan, index=me, columns=pan.tickers)
    st[(slow == 1) & (fst == 1)] = 0
    st[(slow == 1) & (fst == -1)] = 1
    st[(slow == -1) & (fst == -1)] = 2
    st[(slow == -1) & (fst == 1)] = 3
    return st


def static_x(st):
    def xf(t, elig):
        s = st.loc[t, elig].dropna()
        return s.map({0: 1.0, 1: 0.0, 2: -1.0, 3: 0.0})
    return xf


# ---- V3: pooled dynamic a's (k_f = 2)
ST2 = state(SLOW, fast(2))
# eligibility at each month-end, for building the pooled sample
ELIG = pd.DataFrame(False, index=me, columns=pan.tickers)
for t in me:
    e = pan.eligible(t)
    ELIG.loc[t, e] = True
VOLm = pan.vol.loc[me]
RN = (M.shift(-1) / VOLm)                       # next-month excess return / vol at the state date (row = state month)
obs = []
for i, t in enumerate(me[:-1]):
    for c in pan.tickers:
        s = ST2.loc[t, c]
        r = RN.loc[t, c]
        if ELIG.loc[t, c] and np.isfinite(s) and np.isfinite(r):
            obs.append((t, me[i + 1], int(s), float(r)))
OBS = pd.DataFrame(obs, columns=["state_month", "known_at", "state", "rn"])

a_path = []


def dyn_params(t):
    smp = OBS[OBS["known_at"] <= t]
    n_months = smp["state_month"].nunique()
    cnt = smp["state"].value_counts()
    ok = n_months >= 48 and all(cnt.get(k, 0) >= 12 for k in (0, 1, 2, 3))
    if not ok:
        return 0.5, 0.5, False, n_months, np.nan
    g = smp.groupby("state")["rn"]
    avg = g.mean()
    avg2 = smp.assign(r2=smp["rn"] ** 2).groupby("state")["r2"].mean()
    bb = smp[smp["state"].isin([0, 2])]
    avg2_bb = float((bb["rn"] ** 2).mean())
    n_bu, n_be = cnt.get(0, 0), cnt.get(2, 0)
    C = (n_bu / (n_bu + n_be)) * avg[0] / avg2_bb - (n_be / (n_bu + n_be)) * avg[2] / avg2_bb
    if not np.isfinite(C) or C <= 0:
        return 0.5, 0.5, False, n_months, C
    a_co = 0.5 * (1 - (1 / C) * avg[1] / avg2[1])
    a_re = 0.5 * (1 + (1 / C) * avg[3] / avg2[3])
    return float(np.clip(a_co, 0, 1)), float(np.clip(a_re, 0, 1)), True, n_months, float(C)


def dyn_x(t, elig):
    a_co, a_re, used, nm, C = dyn_params(t)
    a_path.append({"date": str(t.date()), "a_co": a_co, "a_re": a_re, "dynamic": used, "pooled_months": nm, "C": C})
    s = ST2.loc[t, elig].dropna()
    return s.map({0: 1.0, 1: 1 - 2 * a_co, 2: -1.0, 3: 2 * a_re - 1})


def slow_x(t, elig):
    return SLOW.loc[t, elig].dropna()


VARIANTS = {
    "V1": ("static MED a=0.5, k_f=1", static_x(state(SLOW, fast(1)))),
    "V2": ("static MED a=0.5, k_f=2", static_x(ST2)),
    "V3": ("dynamic a_Co/a_Re pooled across futures, k_f=2", dyn_x),
    "DIAG_SLOW": ("diagnostic (not a variant): 12-month sign only", slow_x),
}

results = {}
series = {}
for v, (desc, xf) in VARIANTS.items():
    diag = {}
    w = B.risk_unit_book(pan, xf, diag=diag)
    df, to, held = B.simulate3(w)
    rep = B.full_report(df, to, held)
    rep["desc"] = desc
    rep["diag"] = diag
    results[v] = rep
    series[v] = (df, to, held)
    B.save_series(SID, df, {"variant": v, "desc": desc}, folder=HERE / "variants", name=f"{SID}__{v}")
    print(v, desc, {k: round(rep["IS"][k], 3) for k in ("net_sharpe_1x", "net_sharpe_2x", "gross_sharpe", "max_dd", "turnover_per_year")},
          "LATER", round(rep["LATER"]["net_sharpe_1x"], 3), diag)

pd.DataFrame(a_path).to_csv(HERE / "v3_a_path.csv", index=False)
B.jdump(results, HERE / "results.json")
