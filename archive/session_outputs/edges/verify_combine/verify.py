"""Independent check of the combine portfolios (core_ER_6, core_IV_6, core_ER_10, broad_IV_6).

Reads edges/series/*.parquet (sleeves + PORT_*), recomputes S1 from repo decisions at the realistic map,
rebuilds the core with an independent implementation (two sleeve-scaling estimators), runs lookahead
probes, recomputes stats, DSR and bootstraps. Writes only to edges/verify_combine/.
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
assert os.environ.get("GQH_OOS_UNLOCK") != "1"
from src import engine as E      # noqa: E402
from src import forward as F     # noqa: E402
from src import forward2 as F2   # noqa: E402

OUT = Path(__file__).resolve().parent
ED = OUT.parent
SER = ED / "series"
IS_END = pd.Timestamp("2024-10-02")
LATER = pd.Timestamp("2024-10-03")
START = pd.Timestamp("2012-05-02")
P = "FWD"
REAL = {"ES": 0.75, "NQ": 0.75, "YM": 0.75, "RTY": 1.0, "ZT": 0.3, "ZF": 0.5, "ZN": 1.0, "ZB": 1.25, "UB": 1.5,
        "6E": 0.5, "6J": 0.75, "6B": 0.75, "6A": 0.75, "6C": 0.75, "6S": 1.0,
        "CL": 1.5, "GC": 1.5, "SI": 1.5, "HG": 1.5, "NG": 2.5, "HO": 2.5, "RB": 2.5, "PL": 2.5,
        "ZC": 4.0, "ZS": 4.0, "ZW": 4.0, "ZL": 4.0, "ZM": 4.0, "LE": 4.0, "HE": 4.0}


def sr(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * math.sqrt(252)) if len(x) > 20 and x.std() > 0 else float("nan")


def stats(ex, es=None, s1=None, f2=None):
    ex = ex.dropna()
    eq = (1 + ex).cumprod()
    dd = eq / eq.cummax() - 1
    yr = (1 + ex).groupby(ex.index.year).prod() - 1
    n = ex.groupby(ex.index.year).size()
    full = yr[n >= 240]
    r = ex.rolling(504).apply(lambda v: v.mean() / v.std() * math.sqrt(252), raw=True).dropna()
    d = {"start": str(ex.index[0].date()), "end": str(ex.index[-1].date()), "sharpe": sr(ex),
         "ann_ex_geo": float(eq.iloc[-1] ** (252 / len(ex)) - 1), "vol": float(ex.std() * math.sqrt(252)),
         "mdd_ex": float(dd.min()), "mdd_date": str(dd.idxmin().date()),
         "worst_full_year": float(full.min()) if len(full) else np.nan,
         "worst_year_lbl": int(full.idxmin()) if len(full) else -1,
         "pos_years": f"{int((full > 0).sum())}/{len(full)}",
         "r2_p10": float(r.quantile(.1)) if len(r) else np.nan, "r2_p50": float(r.quantile(.5)) if len(r) else np.nan,
         "r2_p90": float(r.quantile(.9)) if len(r) else np.nan, "nw_t": E.newey_west_tstat(ex)}
    for lab, s in (("c_es", es), ("c_s1", s1), ("c_f2", f2)):
        if s is not None:
            j = pd.concat([ex, s], axis=1, join="inner").dropna()
            d[lab] = float(j.corr().iloc[0, 1])
    return d


def boot(a, b, block=63, n=5000, seed=7):
    j = pd.concat([a, b], axis=1, join="inner").dropna().to_numpy()
    T = len(j)
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(T / block))
    diffs = np.empty(n)
    for i in range(n):
        st = rng.integers(0, T - block, nb)          # non-circular blocks
        idx = (st[:, None] + np.arange(block)[None, :]).ravel()[:T]
        x = j[idx]
        diffs[i] = (x[:, 0].mean() / x[:, 0].std() - x[:, 1].mean() / x[:, 1].std()) * math.sqrt(252)
    obs = sr(pd.Series(j[:, 0])) - sr(pd.Series(j[:, 1]))
    return {"diff": round(obs, 3), "p2": round(float(2 * min((diffs <= 0).mean(), (diffs >= 0).mean())), 4),
            "ci90": [round(float(np.quantile(diffs, .05)), 3), round(float(np.quantile(diffs, .95)), 3)]}


def month_ends(cal):
    s = pd.Series(cal, index=cal)
    me = s.groupby(cal.to_period("M")).max()
    me = me[me < cal[-1]]          # last month incomplete -> drop (data ends 2026-10-02)
    return pd.DatetimeIndex(me.values)


def main():
    res = {}
    rf = E.load_rf(P)
    ohlc = E.load_ohlc(["F_ES", "F_ZN", "ZN16"], P)
    cal = ohlc["close"]["F_ES"].dropna().index
    rf = rf.reindex(cal).ffill().fillna(0.0)
    inst_ex = ohlc["close"].pct_change(fill_method=None).sub(rf, axis=0)
    es_ex = inst_ex["F_ES"]

    # ---------------- 1. S1 independent re-simulation
    w = F2.s1_decisions(P)
    tick = list(w.columns)
    o = E.load_ohlc(tick, P)
    rf_s = E.load_rf(P)
    c1 = {t: REAL[t[2:]] for t in tick}
    c2 = {t: 2 * REAL[t[2:]] for t in tick}
    n1, g, to, held, _ = E.simulate(w, o, rf_s, exec="next_close", cost_bps=c1)
    n2, *_ = E.simulate(w, o, rf_s, exec="next_close", cost_bps=c2)
    rfa = rf_s.reindex(n1.index).ffill().fillna(0.0)
    s1 = pd.DataFrame({"net_1x": n1 - rfa, "net_2x": n2 - rfa, "gross": g - rfa}).reindex(cal)
    first = w.abs().sum(axis=1).gt(0).idxmax()
    s1 = s1.loc[s1.index > first].iloc[1:]
    s1 = s1.reindex(cal)
    s1_gross = held.abs().sum(axis=1).reindex(cal).fillna(0.0)
    ex_an = pd.read_parquet(ED / "combine" / "existing.parquet")["S1"]
    ex_an.index = pd.to_datetime(ex_an.index)
    j = pd.concat([s1["net_1x"], ex_an["net_1x"].reindex(cal)], axis=1).dropna()
    res["S1_check"] = {"corr_with_analyst": float(j.corr().iloc[0, 1]), "max_abs_diff": float((j.iloc[:, 0] - j.iloc[:, 1]).abs().max()),
                       "mine_IS_sharpe": sr(s1["net_1x"].loc[START:IS_END]), "analyst_IS_sharpe": sr(ex_an["net_1x"].loc[START:IS_END]),
                       "mine_later": sr(s1["net_1x"].loc[LATER:]), "mine_IS_vol": float(s1["net_1x"].loc[START:IS_END].std() * math.sqrt(252)),
                       "native_frozen_IS": sr((F2.returns("S1", P) - rf_s.reindex(F2.returns("S1", P).index).ffill()).loc[START:IS_END])}

    # ---------------- 2. sleeves
    sl = {}
    for n in ("rpm_ES_MM", "CAL_TSY_ME_ZN"):
        d = pd.read_parquet(SER / f"{n}.parquet")
        d.index = pd.to_datetime(d.index)
        sl[n] = d.reindex(cal)
    sl["S1"] = s1
    # point-in-time sanity of the single-instrument sleeves: implied position from gross/instrument excess
    pos_es = (sl["rpm_ES_MM"]["gross"] / inst_ex["F_ES"]).where(inst_ex["F_ES"].abs() > 2e-3)
    chg = pos_es.dropna().diff().abs() > 0.02
    chg_days = pos_es.dropna().index[chg]
    off = pd.Series(np.arange(len(cal)), index=cal)
    me = month_ends(cal)
    me_i = off.reindex(me).to_numpy()
    rel = [int(off[d] - me_i[me_i < off[d]].max()) if (me_i < off[d]).any() else -1 for d in chg_days]
    res["ES_MM_position_change_offsets_after_month_end"] = pd.Series(rel).value_counts().sort_index().to_dict()
    pos_t = (sl["CAL_TSY_ME_ZN"]["gross"] / inst_ex["ZN16"]).where(inst_ex["ZN16"].abs() > 1e-3)
    active = sl["CAL_TSY_ME_ZN"]["gross"].abs() > 1e-9
    act_days = cal[active.reindex(cal).fillna(False).to_numpy()]
    rel2 = []
    for d in act_days:
        later_me = me_i[me_i >= off[d]]
        rel2.append(int(off[d] - later_me.min()) if len(later_me) else 99)
    res["TSY_active_day_offsets_vs_month_end_T"] = pd.Series(rel2).value_counts().sort_index().to_dict()
    res["TSY_mean_pos_in_window"] = float(pos_t.abs().median())

    # ---------------- 3. independent rebuild of the core
    names = ["rpm_ES_MM", "CAL_TSY_ME_ZN", "S1"]
    gr = {}
    for n, inst in (("rpm_ES_MM", "F_ES"), ("CAL_TSY_ME_ZN", "ZN16")):
        ie = inst_ex[inst]
        ratio = (sl[n]["gross"] / ie).where(ie.abs() > 1e-6).abs()
        gr[n] = ratio.ffill().fillna(0.0).where(sl[n]["gross"].notna(), 0.0).clip(upper=10)
    gr["S1"] = s1_gross
    cost = {"rpm_ES_MM": 0.75, "CAL_TSY_ME_ZN": 1.0, "S1": float((held.abs() * pd.Series(c1)).sum().sum() / held.abs().sum().sum())}
    res["S1_avg_cost_bp"] = cost["S1"]

    def build(names, scheme, target, cov="sample", extra_lag=0, cap=4.0, cap_lag=0, rescale_sleeves=None):
        X = pd.DataFrame({n: sl[n]["net_1x"] for n in names})
        # optional own sleeve rescaling to 10% (trailing EWMA, month-end, applied d+2)
        k_s = pd.DataFrame(1.0, index=cal, columns=names)
        if rescale_sleeves == "ewma":
            v = X.pow(2).ewm(halflife=63, min_periods=126).mean()
            kd = (0.10 / np.sqrt(252 * v)).clip(upper=4.0)
            kk = pd.DataFrame(np.nan, index=cal, columns=names)
            kk.loc[me] = kd.loc[me]
            k_s = kk.ffill().shift(2)
            X = X * k_s
        cnt = X.notna().cumsum()
        m_dec = pd.DataFrame(np.nan, index=cal, columns=names)
        for d in me:
            live = [n for n in names if cnt.loc[d, n] >= 126]
            if not live:
                continue
            H = X.loc[:d, live]
            if cov == "sample":
                S = H.tail(252).cov(min_periods=63).fillna(0.0).to_numpy() * 252
            else:   # EWMA covariance, halflife 63
                Hc = H.tail(756).fillna(0.0)
                wts = 0.5 ** (np.arange(len(Hc))[::-1] / 63.0)
                wts /= wts.sum()
                A = Hc.to_numpy()
                S = (A * wts[:, None]).T @ A * 252
            sd = np.sqrt(np.diag(S))
            if scheme == "ER":
                wv = np.full(len(live), 1.0 / len(live))
            else:
                iv = 1 / sd
                wv = iv / iv.sum()
            k = target / math.sqrt(wv @ S @ wv)
            m_dec.loc[d, live] = wv * k
            m_dec.loc[d, [n for n in names if n not in live]] = 0.0
        m = m_dec.ffill().shift(2 + extra_lag)
        started = m.notna().any(axis=1)
        m = m.fillna(0.0)
        if rescale_sleeves == "ewma":
            m_eff = m * k_s.fillna(0.0)        # effective multiplier on the original sleeve
        else:
            m_eff = m
        G = sum(m_eff[n].abs() * gr[n].shift(cap_lag).fillna(0.0) for n in names)
        capf = (cap / G).clip(upper=1.0).where(G > 0, 1.0) if cap else pd.Series(1.0, index=cal)
        m_eff = m_eff.mul(capf, axis=0)
        dm = m_eff.diff().abs().fillna(m_eff.abs())
        ov = sum(dm[n] * gr[n].fillna(0.0) * cost[n] / 1e4 for n in names)
        out = {}
        for col, mult in (("net_1x", 1), ("net_2x", 2), ("gross", 0)):
            out[col] = (sum(m_eff[n] * sl[n][col].fillna(0.0) for n in names) - mult * ov).where(started)
        return pd.DataFrame(out), float((capf < 1).loc[START:IS_END].mean()), m_eff

    F2n = F.returns("F2", P)
    f2 = (F2n - rf_s.reindex(F2n.index).ffill()).reindex(cal)
    s1n = s1["net_1x"]
    rows = []
    built = {}
    variants = {
        "core_ER_6_replica": (names, "ER", 0.06, dict()),
        "core_IV_6_replica": (names, "IV", 0.06, dict()),
        "core_ER_10_replica": (names, "ER", 0.10, dict()),
        "core_ER_6_ewmaSleeve_ewmaCov": (names, "ER", 0.06, dict(cov="ewma", rescale_sleeves="ewma")),
        "core_ER_10_ewmaSleeve_ewmaCov": (names, "ER", 0.10, dict(cov="ewma", rescale_sleeves="ewma")),
        "core_ER_6_extraLag1": (names, "ER", 0.06, dict(extra_lag=1)),
        "core_ER_10_extraLag1": (names, "ER", 0.10, dict(extra_lag=1)),
        "core_ER_10_capLag1": (names, "ER", 0.10, dict(cap_lag=1)),
        "core_ER_10_noCap": (names, "ER", 0.10, dict(cap=None)),
        "core_ER_6_noCap": (names, "ER", 0.06, dict(cap=None)),
        "noTrend_ER_6": (["rpm_ES_MM", "CAL_TSY_ME_ZN"], "ER", 0.06, dict()),
        "ES_TSY_static_half_half_10": None,
    }
    for k, v in variants.items():
        if v is None:
            continue
        R, cb, m = build(v[0], v[1], v[2], **v[3])
        built[k] = R
        for win, (a, z) in (("IS", (START, IS_END)), ("later", (LATER, cal[-1])), ("h1", (START, "2017-12-31")), ("h2", ("2018-01-01", IS_END))):
            x = R.loc[a:z]
            st = stats(x["net_1x"], es_ex, s1n, f2)
            st.update({"variant": k, "window": win, "sharpe_2x": sr(x["net_2x"]), "sharpe_gross": sr(x["gross"]),
                       "cap_bind_IS": cb})
            rows.append(st)
    # analyst's published series, recomputed stats
    for k in ("core_ER_6", "core_IV_6", "core_ER_10", "core_IV_10", "broad_IV_6", "broad_ER_6", "broad_ER_10"):
        d = pd.read_parquet(SER / f"PORT_{k}.parquet")
        d.index = pd.to_datetime(d.index)
        d = d.reindex(cal)
        built["AN_" + k] = d
        for win, (a, z) in (("IS", (START, IS_END)), ("later", (LATER, cal[-1])), ("h1", (START, "2017-12-31")), ("h2", ("2018-01-01", IS_END))):
            x = d.loc[a:z]
            st = stats(x["net_1x"], es_ex, s1n, f2)
            st.update({"variant": "ANALYST_" + k, "window": win, "sharpe_2x": sr(x["net_2x"]), "sharpe_gross": sr(x["gross"])})
            rows.append(st)
    tab = pd.DataFrame(rows)
    front = ["variant", "window", "sharpe", "sharpe_2x", "sharpe_gross", "ann_ex_geo", "vol", "mdd_ex", "mdd_date", "worst_full_year",
             "worst_year_lbl", "pos_years", "r2_p10", "r2_p50", "r2_p90", "nw_t", "c_es", "c_s1", "c_f2"]
    tab = tab[front + [c for c in tab.columns if c not in front]]
    tab.to_csv(OUT / "verify_table.csv", index=False)
    pd.set_option("display.width", 260, "display.max_columns", 30)
    print(tab[tab.window.isin(["IS", "later"])][front].round(3).to_string())
    print(tab[tab.window.isin(["h1", "h2"])][["variant", "window", "sharpe"]].round(3).to_string())

    # replica vs analyst series
    for a, b in (("core_ER_6_replica", "AN_core_ER_6"), ("core_ER_10_replica", "AN_core_ER_10"), ("core_IV_6_replica", "AN_core_IV_6")):
        j = pd.concat([built[a]["net_1x"], built[b]["net_1x"]], axis=1).loc[START:].dropna()
        res[f"{a}_vs_analyst"] = {"corr": float(j.corr().iloc[0, 1]), "mean_abs_diff_bp": float((j.iloc[:, 0] - j.iloc[:, 1]).abs().mean() * 1e4)}

    # sleeve correlations and sleeve stats IS
    M = pd.DataFrame({n: sl[n]["net_1x"] for n in names}).loc[START:IS_END]
    res["sleeve_corr_IS"] = M.corr().round(3).to_dict()
    res["sleeve_IS_sharpe"] = {n: sr(M[n]) for n in names}
    res["sleeve_IS_vol"] = {n: float(M[n].std() * math.sqrt(252)) for n in names}
    res["sleeve_later_sharpe"] = {n: sr(sl[n]["net_1x"].loc[LATER:]) for n in names}

    # ---------------- 4. bootstraps for core_ER_6 (summary quoted core_ER_10 numbers)
    an6 = built["AN_core_ER_6"]["net_1x"].loc[START:IS_END]
    es10 = F2.returns("ES_10VOL", P)
    es10 = (es10 - rf_s.reindex(es10.index).ffill()).reindex(cal).loc[START:IS_END]
    s2 = F2.returns("S2", P)
    s2 = (s2 - rf_s.reindex(s2.index).ffill()).reindex(cal).loc[START:IS_END]
    res["boot_core_ER_6"] = {"vs_ES_10VOL": boot(an6, es10), "vs_rpm_ES_MM": boot(an6, sl["rpm_ES_MM"]["net_1x"].loc[START:IS_END]),
                             "vs_S2": boot(an6, s2), "vs_F2": boot(an6, f2.loc[START:IS_END]),
                             "vs_noTrend_ER_6": boot(an6, built["noTrend_ER_6"]["net_1x"].loc[START:IS_END])}
    res["comparator_IS_sharpe"] = {"ES_10VOL": sr(es10), "S2": sr(s2), "F2": sr(f2.loc[START:IS_END]),
                                   "F2_later": sr(f2.loc[LATER:]), "ES_10VOL_mdd": float(((1 + es10.dropna()).cumprod() / (1 + es10.dropna()).cumprod().cummax() - 1).min())}

    # ---------------- 5. DSR at fuller trial counts
    t = pd.read_csv(REPO / "results" / "trials.csv")
    tu = t[(t.period == "IS") & (t.cost_mult == 1.0)].drop_duplicates("params_hash")
    n_ifc = int(tu.family.str.startswith("IFC").sum())
    n_all_repo = len(tu)
    dsr = {}
    for k in ("core_ER_6", "core_IV_6", "core_ER_10", "broad_IV_6"):
        x = built["AN_" + k]["net_1x"].loc[START:IS_END].dropna()
        dsr[k] = {"sr": sr(x)}
        for N in (17, 117, 117 + n_ifc, 117 + n_all_repo):
            for var in (0.209, 0.10, float(tu.sharpe.var())):
                dsr[k][f"N{N}_var{var:.3f}"] = round(E.deflated_sharpe(x, N, var)["dsr"], 3)
    res["dsr"] = dsr
    res["repo_trials_unique_IS_1x"] = {"all": n_all_repo, "IFC_families": n_ifc, "var_sr": float(tu.sharpe.var())}

    # ---------------- 6. long-run equity Sharpe vs the in-sample window
    try:
        ff = pd.read_parquet(Path(os.environ["GQH_DATA_DIR"]) / "ff_daily.parquet")
        col = [c for c in ff.columns if "mkt" in c.lower()][0]
        mk = ff[col]
        if mk.abs().mean() > 0.05:
            mk = mk / 100
        res["mkt_rf_sharpe"] = {"1963_2024": sr(mk.loc[:"2024-10-02"]), "2012-05_2024-10": sr(mk.loc[START:IS_END]),
                                "es_futures_2012_2024": sr(es_ex.loc[START:IS_END])}
    except Exception as e:   # noqa: BLE001
        res["mkt_rf_sharpe"] = str(e)

    (OUT / "verify_summary.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
