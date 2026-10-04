"""Rule-based portfolios of the edge sleeves (SPEC.md). Reads edges/series/*.parquet and combine/existing.parquet.

Outputs (combine/): portfolios.parquet, portfolio_table.csv, sleeve_table.csv, comparators_table.csv,
corr_core_is.csv, corr_broad_is.csv, corr_broad_later.csv, yearly.csv, summary.json; edges/series/PORT_*.parquet.
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
from src import engine as E           # noqa: E402
from src import forward2 as F2        # noqa: E402
from src.pbo import cscv_pbo, effective_trials  # noqa: E402

OUT = Path(__file__).resolve().parent
SER = OUT.parent / "series"
P = "FWD"
IS_END = pd.Timestamp("2024-10-02")
LATER = pd.Timestamp("2024-10-03")
HALF = pd.Timestamp("2018-01-01")
COLS = ("net_1x", "net_2x", "gross")
CMULT = {"net_1x": 1.0, "net_2x": 2.0, "gross": 0.0}
LEV_CAP = 4.0
MIN_OBS = 126

CORE = {"rpm_ES_MM": "equity", "CAL_TSY_ME_ZN": "calendar", "S1": "trend"}
BROAD_EXTRA = {"rpm_ZN_FB": "bonds", "carry_xs_rates": "carry", "carry_xs_comm": "carry", "carry_ts_comm": "carry",
               "carry_ts_eq": "carry", "CAL_PREHOL_ES": "calendar", "TSMOM_F": "trend", "A_F": "calendar"}
FAMILY = {**CORE, **BROAD_EXTRA, "rpm_ES_CV": "equity"}
COST = {"rpm_ES_MM": 0.75, "rpm_ES_CV": 0.75, "CAL_TSY_ME_ZN": 1.0, "rpm_ZN_FB": 1.0, "CAL_PREHOL_ES": 0.75,
        "carry_xs_rates": 0.6, "carry_xs_comm": 2.9, "carry_ts_comm": 2.9, "carry_ts_eq": 0.8}
CARRY_GROSS = {"carry_xs_rates": 10.073, "carry_xs_comm": 1.1723, "carry_ts_comm": 1.1301, "carry_ts_eq": 0.5391}
SINGLE = {"rpm_ES_MM": "F_ES", "rpm_ES_CV": "F_ES", "rpm_ZN_FB": "F_ZN", "CAL_TSY_ME_ZN": "ZN16", "CAL_PREHOL_ES": "ES16"}


# ----------------------------------------------------------------------------------------- data
def load():
    rf = E.load_rf(P)
    ohlc = E.load_ohlc(["F_ES", "F_ZN", "ES16", "ZN16"], P)
    cal = ohlc["close"]["F_ES"].dropna().index
    rf = rf.reindex(cal).ffill().fillna(0.0)
    inst_ex = ohlc["close"].pct_change(fill_method=None).sub(rf, axis=0).reindex(cal)
    ex_all = pd.read_parquet(OUT / "existing.parquet")
    ex_gross = pd.read_parquet(OUT / "existing_gross.parquet")
    meta = json.loads((OUT / "existing_meta.json").read_text())
    sl, gr, cost = {}, {}, {}
    names = list(FAMILY)
    for n in names:
        if (SER / f"{n}.parquet").exists():
            df = pd.read_parquet(SER / f"{n}.parquet")[list(COLS)]
        else:
            df = ex_all[n][list(COLS)]
        df.index = pd.to_datetime(df.index)
        df = df.reindex(cal)
        sl[n] = df
        if n in SINGLE:
            ie = inst_ex[SINGLE[n]]
            ratio = (df["gross"] / ie).where(ie.abs() > 1e-6).abs()
            g = ratio.ffill().fillna(0.0).where(df["gross"].notna(), 0.0)
            # flat days inside position-free stretches: sleeve gross return 0 -> ratio 0, keeps 0
            gr[n] = g.clip(upper=10.0)
            cost[n] = COST[n]
        elif n in CARRY_GROSS:
            gr[n] = pd.Series(CARRY_GROSS[n], index=cal).where(df["gross"].notna(), 0.0)
            cost[n] = COST[n]
        else:
            gr[n] = ex_gross[n].reindex(cal).fillna(0.0)
            cost[n] = meta[n]["avg_cost_bp"]
    nat = pd.read_parquet(OUT / "comparators_native.parquet").reindex(cal)
    for c in nat:   # drop the zero padding before each comparator's first live day
        nz = nat[c].fillna(0.0).ne(0.0)
        first = nz.idxmax()
        nat.loc[nat.index < first, c] = np.nan
    es_ex = inst_ex["F_ES"]
    s1 = sl["S1"]["net_1x"]
    f2 = nat["F2"]
    extra = {k: ex_all[k] for k in ("ES_10VOL_real", "S2_real", "F2_scaled", "C_F")}
    return cal, rf, sl, gr, cost, nat, es_ex, s1, f2, extra


# ----------------------------------------------------------------------------------------- portfolio
def month_ends(cal):
    return F2._month_ends(cal)


def build(names, scheme, target, cal, sl, gr, cost):
    """Return dict col -> excess series, multipliers (after cap), gross G, overlay turnover, ex-ante DR."""
    X = pd.DataFrame({n: sl[n]["net_1x"] for n in names})
    cnt = X.notna().cumsum()
    m_dec = pd.DataFrame(np.nan, index=cal, columns=names)
    dr_ex = {}
    for d in month_ends(cal):
        live = [n for n in names if cnt.loc[d, n] >= MIN_OBS]
        if not live:
            continue
        H = X.loc[:d, live].tail(252)
        S = H.cov(min_periods=MIN_OBS // 2).fillna(0.0) * 252
        sd = np.sqrt(np.diag(S.to_numpy()))
        if scheme == "ER":
            w = pd.Series(1.0 / len(live), index=live)
        elif scheme == "IV":
            iv = 1.0 / np.where(sd > 0, sd, np.nan)
            w = pd.Series(iv / np.nansum(iv), index=live).fillna(0.0)
        elif scheme == "FAM":
            fams = sorted({FAMILY[n] for n in live})
            w = pd.Series(0.0, index=live)
            for f in fams:
                mem = [n for n in live if FAMILY[n] == f]
                v = pd.Series(1.0 / len(mem), index=mem)
                Sf = S.loc[mem, mem].to_numpy()
                vol = math.sqrt(max(float(v.to_numpy() @ Sf @ v.to_numpy()), 1e-12))
                w[mem] = v * min(3.0, 0.10 / vol) / len(fams)
        else:
            raise ValueError(scheme)
        var = float(w.to_numpy() @ S.to_numpy() @ w.to_numpy())
        if var <= 0:
            continue
        k = target / math.sqrt(var)
        m_dec.loc[d, live] = (w * k).values
        m_dec.loc[d, [n for n in names if n not in live]] = 0.0
        dr_ex[d] = float((w.to_numpy() * sd).sum() / math.sqrt(var))
    m = m_dec.ffill().shift(2)               # applied from the second session after the decision
    started = m.notna().any(axis=1)
    m = m.fillna(0.0)
    G_raw = sum(m[n].abs() * gr[n].reindex(cal).fillna(0.0) for n in names)
    capf = (LEV_CAP / G_raw).clip(upper=1.0).where(G_raw > 0, 1.0)
    m = m.mul(capf, axis=0)
    G = G_raw * capf
    dm = m.diff().abs().fillna(m.abs())
    ov_to = sum(dm[n] * gr[n].reindex(cal).fillna(0.0) for n in names)
    ov_cost_1x = sum(dm[n] * gr[n].reindex(cal).fillna(0.0) * cost[n] / 1e4 for n in names)
    out = {}
    for col in COLS:
        r = sum(m[n] * sl[n][col].reindex(cal).fillna(0.0) for n in names) - ov_cost_1x * CMULT[col]
        out[col] = r.where(started)
    return {"ret": pd.DataFrame(out), "m": m, "G": G.where(started), "capbind": (capf < 1.0).where(started),
            "ov_to": ov_to.where(started), "dr_ex": pd.Series(dr_ex), "first": started.idxmax()}


# ----------------------------------------------------------------------------------------- stats
def sharpe(x):
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(252)) if len(x) > 20 and x.std() > 0 else float("nan")


def dd_stats(ex, rf):
    tot = (ex + rf.reindex(ex.index).fillna(0.0))
    mdd_tot = E.max_drawdown(tot)
    eq = (1 + ex).cumprod()
    peak = eq.cummax()
    mdd_ex = float((eq / peak - 1).min())
    under = eq < peak - 1e-12
    longest, cur = 0, 0
    for u in under.to_numpy():
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    return mdd_tot, mdd_ex, longest


def window_stats(ex, rf, ret2=None, gross=None, es=None, s1=None, f2=None):
    ex = ex.dropna()
    if len(ex) < 40:
        return {}
    yrs = len(ex) / 252
    tot = ex + rf.reindex(ex.index).fillna(0.0)
    ann_tot = float((1 + tot).prod() ** (1 / yrs) - 1)
    ann_ex = float((1 + ex).prod() ** (1 / yrs) - 1)
    mdd_tot, mdd_ex, longest = dd_stats(ex, rf)
    yr = (1 + ex).groupby(ex.index.year).prod() - 1
    ndays = ex.groupby(ex.index.year).size()
    full = yr[ndays >= 240]
    roll = ex.rolling(504).apply(lambda v: v.mean() / v.std() * math.sqrt(252) if v.std() > 0 else np.nan, raw=True).dropna()
    d = {"start": str(ex.index[0].date()), "end": str(ex.index[-1].date()), "years": round(yrs, 2),
         "sharpe_net1x": sharpe(ex), "ann_excess": ann_ex, "ann_total": ann_tot,
         "vol": float(ex.std() * math.sqrt(252)), "max_dd_total": mdd_tot, "max_dd_excess": mdd_ex,
         "longest_dd_sessions": longest,
         "worst_year": float(full.min()) if len(full) else float(yr.min()),
         "worst_year_label": int(full.idxmin()) if len(full) else int(yr.idxmin()),
         "pct_pos_years": float((full > 0).mean()) if len(full) else float("nan"), "n_full_years": int(len(full)),
         "roll2y_p10": float(roll.quantile(0.1)) if len(roll) else float("nan"),
         "roll2y_p50": float(roll.quantile(0.5)) if len(roll) else float("nan"),
         "roll2y_p90": float(roll.quantile(0.9)) if len(roll) else float("nan"),
         "nw_t": E.newey_west_tstat(ex), "skew": float(ex.skew()), "worst_day": float(ex.min())}
    if ret2 is not None:
        d["sharpe_net2x"] = sharpe(ret2.reindex(ex.index))
    if gross is not None:
        d["sharpe_gross"] = sharpe(gross.reindex(ex.index))
    for lab, s in (("corr_es", es), ("corr_s1", s1), ("corr_f2", f2)):
        if s is not None:
            j = pd.concat([ex, s], axis=1, join="inner").dropna()
            d[lab] = float(j.corr().iloc[0, 1]) if len(j) > 40 else float("nan")
    return d


def block_boot_diff(a, b, block=63, n=5000, seed=11):
    j = pd.concat([a, b], axis=1, join="inner").dropna().to_numpy()
    T = len(j)
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(T / block))
    obs = sharpe(pd.Series(j[:, 0])) - sharpe(pd.Series(j[:, 1]))
    diffs = np.empty(n)
    for i in range(n):
        st = rng.integers(0, T, nb)
        idx = (st[:, None] + np.arange(block)[None, :]).ravel()[:T] % T
        x = j[idx]
        sa = x[:, 0].mean() / x[:, 0].std() * math.sqrt(252)
        sb = x[:, 1].mean() / x[:, 1].std() * math.sqrt(252)
        diffs[i] = sa - sb
    p = 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())
    return {"diff": obs, "p_two_sided": float(min(1.0, p)), "ci90": [float(np.quantile(diffs, 0.05)), float(np.quantile(diffs, 0.95))]}


# ----------------------------------------------------------------------------------------- main
def main():
    cal, rf, sl, gr, cost, nat, es_ex, s1, f2, extra = load()
    core = list(CORE)
    broad = core + list(BROAD_EXTRA)
    variants = {}
    for uni, names in (("core", core), ("broad", broad)):
        for sch in ("ER", "IV", "FAM"):
            for tv in (0.06, 0.10):
                variants[f"{uni}_{sch}_{int(tv*100)}"] = (names, sch, tv)
    diag = {"diag_core_noTrend_ER_10": (["rpm_ES_MM", "CAL_TSY_ME_ZN"], "ER", 0.10),
            "diag_core_noTSY_ER_10": (["rpm_ES_MM", "S1"], "ER", 0.10),
            "diag_core_noEQ_ER_10": (["CAL_TSY_ME_ZN", "S1"], "ER", 0.10),
            "diag_core_ESCV_ER_10": (["rpm_ES_CV", "CAL_TSY_ME_ZN", "S1"], "ER", 0.10),
            "diag_core_TSMOMF_ER_10": (["rpm_ES_MM", "CAL_TSY_ME_ZN", "TSMOM_F"], "ER", 0.10)}
    variants.update(diag)
    built = {k: build(*v, cal, sl, gr, cost) for k, v in variants.items()}

    # common start: first return day where every core+broad sleeve is live and the broad portfolio is started
    cnt = pd.DataFrame({n: sl[n]["net_1x"] for n in broad}).notna().cumsum()
    all_live = cnt.ge(MIN_OBS).all(axis=1)
    first_dec = [d for d in month_ends(cal) if all_live.loc[d]][0]
    start = cal[cal.get_loc(first_dec) + 2]
    print("common start", start.date(), "decision", first_dec.date())

    rows, ports = [], {}
    for k, b in built.items():
        R = b["ret"]
        ports[k] = R
        for win, (a, z) in (("IS", (start, IS_END)), ("later", (LATER, cal[-1])), ("IS_h1", (start, HALF - pd.Timedelta(days=1))),
                            ("IS_h2", (HALF, IS_END))):
            x = R.loc[a:z]
            st = window_stats(x["net_1x"], rf, x["net_2x"], x["gross"], es_ex, s1, f2)
            if not st:
                continue
            st.update({"portfolio": k, "window": win,
                       "median_gross": float(b["G"].loc[a:z].median()), "p95_gross": float(b["G"].loc[a:z].quantile(0.95)),
                       "cap_bind_share": float(b["capbind"].loc[a:z].mean()),
                       "overlay_turnover_per_year": float(b["ov_to"].loc[a:z].sum() / (len(x) / 252)),
                       "dr_exante_median": float(b["dr_ex"].loc[a:z].median()) if len(b["dr_ex"].loc[a:z]) else float("nan")})
            if win == "IS":
                names = variants[k][0]
                mx = pd.DataFrame({n: b["m"][n] * sl[n]["net_1x"].reindex(cal).fillna(0.0) for n in names}).loc[a:z]
                st["dr_realised"] = float(mx.std().sum() / x["net_1x"].std())
                st["mean_mult"] = json.dumps({n: round(float(b["m"][n].loc[a:z].mean()), 3) for n in names})
            rows.append(st)
    tab = pd.DataFrame(rows)
    front = ["portfolio", "window", "start", "end", "sharpe_net1x", "sharpe_net2x", "sharpe_gross", "ann_excess", "ann_total", "vol",
             "max_dd_total", "max_dd_excess", "worst_year", "worst_year_label", "pct_pos_years", "roll2y_p10", "roll2y_p50", "roll2y_p90",
             "longest_dd_sessions", "nw_t", "corr_es", "corr_s1", "corr_f2"]
    tab = tab[front + [c for c in tab.columns if c not in front]]
    tab.to_csv(OUT / "portfolio_table.csv", index=False)

    # sleeves and comparators on the same windows
    srows = []
    for n in broad + ["rpm_ES_CV"]:
        for win, (a, z) in (("IS", (start, IS_END)), ("later", (LATER, cal[-1]))):
            x = sl[n].loc[a:z]
            st = window_stats(x["net_1x"], rf, x["net_2x"], x["gross"], es_ex, s1, f2)
            st.update({"sleeve": n, "family": FAMILY[n], "window": win})
            srows.append(st)
    for n, s in (("S2_native", nat["S2"]), ("S3_native", nat["S3"]), ("ES_10VOL_native", nat["ES_10VOL"]),
                 ("S1_native", nat["S1"]), ("TSMOM_F_native", nat["TSMOM_F"]), ("F2_native", nat["F2"]),
                 ("S2_real", extra["S2_real"]["net_1x"]), ("ES_10VOL_real", extra["ES_10VOL_real"]["net_1x"]),
                 ("F2_scaled10", extra["F2_scaled"]["net_1x"]), ("C_F_real_scaled", extra["C_F"]["net_1x"])):
        for win, (a, z) in (("IS", (start, IS_END)), ("later", (LATER, cal[-1]))):
            s2x = None
            if n == "S3_native":
                s2x = nat["S3_2x"]
            elif n in ("S2_real", "ES_10VOL_real"):
                s2x = extra[n]["net_2x"]
            st = window_stats(s.reindex(cal).loc[a:z], rf, None if s2x is None else s2x.reindex(cal).loc[a:z], None, es_ex, s1, f2)
            st.update({"sleeve": n, "family": "comparator", "window": win})
            srows.append(st)
    stab = pd.DataFrame(srows)
    stab = stab[["sleeve", "family", "window"] + [c for c in stab.columns if c not in ("sleeve", "family", "window")]]
    stab.to_csv(OUT / "sleeve_and_comparator_table.csv", index=False)

    # correlation matrices
    M = pd.DataFrame({n: sl[n]["net_1x"] for n in broad})
    M["ES"] = es_ex
    M["F2"] = f2
    M.loc[start:IS_END, core + ["ES", "F2"]].corr().round(3).to_csv(OUT / "corr_core_is.csv")
    M.loc[start:IS_END].corr().round(3).to_csv(OUT / "corr_broad_is.csv")
    M.loc[LATER:].corr().round(3).to_csv(OUT / "corr_broad_later.csv")

    # yearly excess returns of main portfolios + sleeves
    Y = {}
    for k in list(variants)[:12]:
        x = ports[k]["net_1x"].loc[start:].dropna()
        Y[k] = (1 + x).groupby(x.index.year).prod() - 1
    for n in core:
        x = sl[n]["net_1x"].loc[start:].dropna()
        Y[n] = (1 + x).groupby(x.index.year).prod() - 1
    pd.DataFrame(Y).round(4).to_csv(OUT / "yearly_excess.csv")

    # PBO
    main12 = list(variants)[:12]
    R12 = pd.DataFrame({k: ports[k]["net_1x"] for k in main12}).loc[start:IS_END]
    R17 = pd.DataFrame({k: ports[k]["net_1x"] for k in variants}).loc[start:IS_END]
    R6 = pd.DataFrame({k: ports[k]["net_1x"] for k in main12 if k.endswith("_10")}).loc[start:IS_END]
    pbo = {"main12": cscv_pbo(R12, 16), "all17": cscv_pbo(R17, 16), "main6_at10pct": cscv_pbo(R6, 16),
           "eff_trials_main12": effective_trials(R12), "eff_trials_all17": effective_trials(R17)}

    # DSR for the best main-grid portfolio
    is_tab = tab[(tab.window == "IS") & tab.portfolio.isin(main12)].set_index("portfolio")
    best = is_tab["sharpe_net1x"].idxmax()
    srs = []
    for f in sorted(SER.glob("*.parquet")):
        if f.name.startswith("PORT_"):
            continue
        x = pd.read_parquet(f)["net_1x"].loc[:IS_END].dropna()
        x = x.loc[x.ne(0).idxmax():]
        srs.append(sharpe(x))
    srs += list(tab[(tab.window == "IS")]["sharpe_net1x"])
    var_sr = float(np.nanvar(srs, ddof=1))
    xb = ports[best]["net_1x"].loc[start:IS_END].dropna()
    dsr = {"best": best, "is_sharpe": sharpe(xb), "n_trials": 117, "var_sr_ann": var_sr, "n_sr_in_var": len(srs),
           **E.deflated_sharpe(xb, 117, var_sr)}
    dsr["sens_var_0.10"] = E.deflated_sharpe(xb, 117, 0.10)
    dsr["sens_trials_17_portfolios_only"] = E.deflated_sharpe(xb, 17, var_sr)
    dsr["psr_vs_0"] = E.deflated_sharpe(xb, 1, var_sr)

    # bootstrap comparisons (IS)
    boots = {}
    cmp = {"ES_10VOL_native": nat["ES_10VOL"], "ES_10VOL_real": extra["ES_10VOL_real"]["net_1x"], "rpm_ES_MM": sl["rpm_ES_MM"]["net_1x"],
           "S2_native": nat["S2"], "S2_real": extra["S2_real"]["net_1x"], "S3_native": nat["S3"], "F2_native": nat["F2"]}
    for tgt in sorted({best, "core_ER_10", "broad_ER_10"}):
        for lab, s in cmp.items():
            boots[f"{tgt}_vs_{lab}"] = block_boot_diff(ports[tgt]["net_1x"].loc[start:IS_END], s.reindex(cal).loc[start:IS_END])
    boots["core_ER_10_vs_broad_ER_10"] = block_boot_diff(ports["core_ER_10"]["net_1x"].loc[start:IS_END],
                                                         ports["broad_ER_10"]["net_1x"].loc[start:IS_END])
    boots["core_ER_10_vs_diag_core_noTrend"] = block_boot_diff(ports["core_ER_10"]["net_1x"].loc[start:IS_END],
                                                               ports["diag_core_noTrend_ER_10"]["net_1x"].loc[start:IS_END])

    # save portfolio series
    pall = pd.concat({k: v for k, v in ports.items()}, axis=1)
    pall.to_parquet(OUT / "portfolios.parquet")
    for k in main12:
        df = ports[k].loc[built[k]["first"]:].copy()
        df.index.name = "date"
        df.to_parquet(SER / f"PORT_{k}.parquet")
        names, sch, tv = variants[k]
        (SER / f"PORT_{k}.json").write_text(json.dumps({
            "candidate": f"PORT_{k}", "task_label": "combine", "sleeves": {n: FAMILY[n] for n in names}, "weighting": sch,
            "target_vol": tv, "columns": {"net_1x": "daily excess return over T-bill, realistic costs (sleeve + overlay)",
                                          "net_2x": "2x costs", "gross": "no costs"},
            "rule": "month-end decisions from trailing sleeve returns (252-day covariance, min 126 obs), applied from d+2; "
                    "leverage cap 4 on summed sleeve instrument gross; overlay costs on multiplier changes",
            "in_sample": [str(start.date()), str(IS_END.date())], "later_descriptive": [str(LATER.date()), str(cal[-1].date())],
            "spec": "edges/combine/SPEC.md", "script": "edges/combine/combine.py"}, indent=2))

    summary = {"common_start": str(start.date()), "first_decision": str(first_dec.date()), "pbo": pbo, "dsr": dsr,
               "bootstrap": boots, "variants": {k: {"sleeves": v[0], "scheme": v[1], "target": v[2]} for k, v in variants.items()}}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str))

    pd.set_option("display.width", 250, "display.max_columns", 40)
    show = ["portfolio", "window", "sharpe_net1x", "sharpe_net2x", "sharpe_gross", "ann_excess", "vol", "max_dd_total", "worst_year",
            "pct_pos_years", "roll2y_p10", "roll2y_p50", "longest_dd_sessions", "nw_t", "corr_es", "median_gross", "cap_bind_share"]
    print(tab[tab.window.isin(["IS", "later"])][show].round(3).to_string())
    print(tab[tab.window.isin(["IS_h1", "IS_h2"])][["portfolio", "window", "sharpe_net1x"]].round(3).to_string())
    print(stab[["sleeve", "window", "sharpe_net1x", "sharpe_net2x", "vol", "max_dd_total", "nw_t", "corr_es", "corr_s1", "corr_f2"]].round(3).to_string())
    print(json.dumps({"pbo": pbo, "dsr": dsr}, indent=1, default=str))
    print(json.dumps(boots, indent=1))


if __name__ == "__main__":
    main()
