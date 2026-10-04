"""Verification extras: V5 intraday, event study (2y, 10y), ZN beta, portfolio test."""
from __future__ import annotations

import importlib.util
import json
import math
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"<scratch>/auction/verify")
import vstrat as S  # noqa: E402
import vdata as V   # noqa: E402

cal, rex, A = S.cal, S.rex, S.A
out = {}


# ------------------------------------------------------------------ V5 intraday
def v5(terms):
    hp = pd.read_parquet(V.SP / "intraday_study" / "data" / "hourly_panel.parquet",
                         columns=["root", "trade_date", "hour_et", "ret_simple", "cme_non_nyse_session"])
    z = hp[(hp.root == "ZN") & ~hp.cme_non_nyse_session]
    ev = A[A.term.isin(terms) & (A.N <= A.A - 1) & A.on].drop_duplicates("auction_date")
    days = pd.DatetimeIndex(ev.auction_date)
    flag = pd.Series(0.0, index=cal)
    flag.loc[flag.index.isin(days)] = 1.0
    f = flag.rolling(252, min_periods=63).mean().shift(1).fillna(len(terms) * 12 / 252).clip(lower=1 / 252)
    sig = S.vol(rex["F_ZN"].dropna()).reindex(cal).shift(1)
    rows = []
    zz = z[z.trade_date.isin(days)]
    for d, g in zz.groupby("trade_date"):
        hrs = set(g.hour_et)
        if 12 not in hrs or 15 not in hrs or d <= cal[0]:
            continue
        rp = np.prod(1 + g.loc[g.hour_et.between(9, 12), "ret_simple"].to_numpy()) - 1
        rq = np.prod(1 + g.loc[g.hour_et.between(13, 15), "ret_simple"].to_numpy()) - 1
        s = sig.get(d, np.nan)
        if not np.isfinite(s):
            continue
        L = min(5.0, 0.10 / (s * math.sqrt(f[d])))
        rows.append((d, rp, rq, L))
    t = pd.DataFrame(rows, columns=["d", "rp", "rq", "L"]).set_index("d")
    unit = t.rq - t.rp
    g = (t.L * unit).reindex(cal).fillna(0.0)
    c = (4 * t.L * 1.0 / 1e4).reindex(cal).fillna(0.0)
    s = {"n1": g - c, "n2": g - 2 * c, "g": g}
    first = t.index[0]
    o = {}
    for wn, (a, b) in S.W.items():
        o[f"{wn}_n1"] = S.sharpe(s["n1"][first:][a:b])
        o[f"{wn}_n2"] = S.sharpe(s["n2"][first:][a:b])
    o["full_g"] = S.sharpe(s["g"][first:]["2010-06-07":"2024-10-02"])
    u = t.loc[:"2024-10-02"]
    o["n_is"] = len(u)
    o["pre_bp"], o["pre_t"] = u.rp.mean() * 1e4, u.rp.mean() / u.rp.std() * math.sqrt(len(u))
    o["post_bp"], o["post_t"] = u.rq.mean() * 1e4, u.rq.mean() / u.rq.std() * math.sqrt(len(u))
    o["unit_bp"] = (u.rq - u.rp).mean() * 1e4
    return o, pd.DataFrame(s), t


for vid, terms in (("V5_ZN_10y_id", [10]), ("V5_ZN_7y10y_id", [7, 10])):
    o, s, t = v5(terms)
    out[vid] = o
    s.to_parquet(V.OUT / f"v_{vid}.parquet")
    print(vid, {k: round(v, 3) for k, v in o.items()})


# ------------------------------------------------------------------ event study (2y on ZT, 10y on ZN, ES around 2y)
def nw(x, lags=5):
    return S.nw_t(x, lags)


es = []
periods = {"2010-13": ("2010-06-07", "2013-12-31"), "2014-24": ("2014-01-01", "2024-10-02"), "2024-26": ("2024-10-03", "2026-10-02")}
for lab, term, inst in (("2y", 2, "F_ZT"), ("10y", 10, "F_ZN"), ("ES_2y", 2, "F_ES"), ("5y", 5, "F_ZF"), ("7y", 7, "F_ZN")):
    r = rex[inst].to_numpy() * 1e4
    for pn, (p0, p1) in periods.items():
        M = []
        for e in A[(A.term == term) & (A.auction_date >= p0) & (A.auction_date <= p1)].itertuples():
            lo, hi = e.A - 10, e.A + 10
            if lo < 1 or hi >= len(cal) or cal[hi] > pd.Timestamp(p1) or cal[lo] < pd.Timestamp(p0):
                continue
            v = r[lo:hi + 1]
            if np.isnan(v).any():
                continue
            M.append(v)
        M = np.array(M)
        row = {"series": lab, "period": pn, "n": len(M)}
        for tt in (5, 10):
            pre, post = M[:, 11 - tt:11].sum(1), M[:, 11:11 + tt].sum(1)
            D = post - pre
            row[f"D{tt}"] = D.mean()
            row[f"D{tt}_nwt"] = nw(D)
            row[f"pre{tt}"] = pre.mean()
            row[f"post{tt}"] = post.mean()
        row["day0"] = M[:, 10].mean()
        row["day0_t"] = M[:, 10].mean() / M[:, 10].std(ddof=1) * math.sqrt(len(M))
        es.append(row)
es = pd.DataFrame(es)
es.to_csv(V.OUT / "verify_event_study.csv", index=False)
print(es.round(2).to_string())


# ------------------------------------------------------------------ ZN beta of the chosen variant
ch = pd.read_parquet(V.OUT / "v_V3_all_t10_x.parquet")["n1"]
zn = rex["F_ZN"]
beta = {}
for wn in ("sel", "val", "full"):
    a, b = S.W[wn]
    j = pd.concat([ch, zn], axis=1).loc[a:b].dropna()
    j.columns = ["y", "x"]
    bt = np.cov(j.y, j.x)[0, 1] / j.x.var()
    beta[wn] = {"beta": bt, "zn_sharpe": S.sharpe(j.x), "resid_sharpe": S.sharpe(j.y - bt * j.x), "raw": S.sharpe(j.y)}
# beta estimated on selection only, applied to validation
a, b = S.W["sel"]
bsel = beta["sel"]["beta"]
jv = pd.concat([ch, zn], axis=1).loc[S.W["val"][0]:S.W["val"][1]].dropna()
beta["val_resid_with_sel_beta"] = S.sharpe(jv.iloc[:, 0] - bsel * jv.iloc[:, 1])
out["beta"] = beta
print("beta", json.dumps(beta, indent=1))

# ------------------------------------------------------------------ gate diagnostic for the chosen variant (calendar known)
sl = {m: S.sleeve(S.evsel([m], True), S.INST[m], None, 10, 10, False, 30.0 / S.DUR[S.INST[m]]) for m in S.TRADED}
st, _ = S.stats_of(S.combine(sl))
out["V3_all_t10_x_nogate"] = st
print("V3_all_t10_x without gate:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in st.items()})
# post-only leg (long after the auction, flat before) for the chosen variant
sl = {m: S.sleeve(S.evsel([m], True), S.INST[m], None, 0, 10, True, 30.0 / S.DUR[S.INST[m]]) for m in S.TRADED}
st, _ = S.stats_of(S.combine(sl))
out["V3_all_t10_x_postonly"] = st
print("V3_all_t10_x post-only long:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in st.items()})

# ------------------------------------------------------------------ portfolio test (own ER build)
spec = importlib.util.spec_from_file_location("cb", V.SP / "edges" / "combine" / "combine.py")
CB = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CB)
ccal, crf, csl, cgr, ccost, *_ = CB.load()
CORE = ["rpm_ES_MM", "CAL_TSY_ME_ZN", "S1"]


def er_build(sleeves, gr=None, cost=None, cap=None, target=0.06, minobs=126):
    X = pd.DataFrame({n: s["n1"] for n, s in sleeves.items()}).reindex(ccal)
    cnt = X.notna().cumsum()
    me = pd.Series(ccal, index=ccal).groupby(ccal.to_period("M")).max()
    m = pd.DataFrame(np.nan, index=ccal, columns=list(sleeves))
    for d in me:
        live = [n for n in sleeves if cnt.loc[d, n] >= minobs]
        if not live:
            continue
        Sg = X.loc[:d, live].tail(252).cov(min_periods=minobs // 2).fillna(0.0).to_numpy() * 252
        w = np.ones(len(live)) / len(live)
        v = w @ Sg @ w
        if v <= 0:
            continue
        m.loc[d] = 0.0
        m.loc[d, live] = w * target / math.sqrt(v)
    m = m.ffill().shift(2)
    started = m.notna().any(axis=1)
    m = m.fillna(0.0)
    if cap is not None:
        G = sum(m[n].abs() * gr[n].reindex(ccal).fillna(0.0) for n in sleeves)
        cf = (cap / G).clip(upper=1.0).where(G > 0, 1.0)
        m = m.mul(cf, axis=0)
    res = {}
    for col, cm in (("n1", 1.0), ("n2", 2.0)):
        r = sum(m[n] * sleeves[n][col].reindex(ccal).fillna(0.0) for n in sleeves)
        if cost is not None:
            dm = m.diff().abs().fillna(m.abs())
            r = r - cm * sum(dm[n] * gr[n].reindex(ccal).fillna(0.0) * cost[n] / 1e4 for n in sleeves)
        res[col] = r.where(started)
    return pd.DataFrame(res), m


core_sl = {n: csl[n].rename(columns={"net_1x": "n1", "net_2x": "n2"}) for n in CORE}
saved = pd.read_parquet(V.SP / "edges" / "series" / "PORT_core_ER_6.parquet")["net_1x"]
saved.index = pd.to_datetime(saved.index)
nz = saved[saved != 0]
print("saved core first nonzero:", nz.index[0].date())

auc_held = pd.read_parquet(V.OUT / "held_V3_all_t10_x.parquet")
auc = pd.read_parquet(V.OUT / "v_V3_all_t10_x.parquet")
auc_gr = auc_held.abs().sum(axis=1)
auc_cost = float((auc_held.abs() * pd.Series(S.COST)[V.TICK]).sum(axis=1).sum() / auc_gr.sum())
gr4 = dict(cgr)
gr4["AUC"] = auc_gr
cost4 = dict(ccost)
cost4["AUC"] = auc_cost
port = {}
for lab, kw in (("plain", {}), ("cap_cost", {"gr": gr4, "cost": cost4, "cap": 4.0})):
    c, mc = er_build(core_sl, **kw)
    p, mp = er_build({**core_sl, "AUC": auc}, **kw)
    jj = pd.concat([c.n1, saved], axis=1).dropna()
    rows = {"core_vs_saved_corr": float(jj.corr().iloc[0, 1]), "core_vs_saved_maxdiff": float((jj.iloc[:, 0] - jj.iloc[:, 1]).abs().max())}
    starts = {"auc_live": mp["AUC"][mp["AUC"] > 0].index[0], "core_nonzero": nz.index[0]}
    for sname, st0 in starts.items():
        for wn, (a, b) in S.W.items():
            a2 = max(pd.Timestamp(a), st0)
            rows[f"{sname}_{wn}_core"] = S.sharpe(c.n1[a2:b])
            rows[f"{sname}_{wn}_port"] = S.sharpe(p.n1[a2:b])
            rows[f"{sname}_{wn}_core2x"] = S.sharpe(c.n2[a2:b])
            rows[f"{sname}_{wn}_port2x"] = S.sharpe(p.n2[a2:b])
    rows["auc_cost_bp"] = auc_cost
    rows["auc_start"] = str(starts["auc_live"].date())
    rows["mean_auc_mult_val"] = float(mp["AUC"]["2021-01-01":"2024-10-02"].mean())
    port[lab] = rows
    print(lab, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows.items()}, indent=0))
out["portfolio"] = port

# simple fixed blend sanity: core saved + chosen sleeve scaled to the same validation-agnostic vol (selection vol)
cs = saved.loc["2012-05-02":]
aa = auc.n1.reindex(cs.index).fillna(0.0)
k = cs.loc[:"2020-12-31"].std() / aa.loc[:"2020-12-31"].std()
for wgt in (0.25, 0.5):
    bl = (1 - wgt) * cs + wgt * k * aa
    out[f"blend_{wgt}"] = {wn: S.sharpe(bl[max(pd.Timestamp(a), cs.index[0]):b]) for wn, (a, b) in S.W.items()}
    print("blend", wgt, {k_: round(v, 3) for k_, v in out[f"blend_{wgt}"].items()})
out["core_saved"] = {wn: S.sharpe(cs[max(pd.Timestamp(a), cs.index[0]):b]) for wn, (a, b) in S.W.items()}
print("core saved", {k_: round(v, 3) for k_, v in out["core_saved"].items()})

(V.OUT / "verify_extra.json").write_text(json.dumps(out, indent=1, default=str))
