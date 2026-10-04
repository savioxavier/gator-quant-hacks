"""Robustness diagnostics for the intraday momentum study (no variant selection happens here).

(a) outlier sensitivity: drop 2020-02-20..2020-04-30; drop calendar 2020; winsorise r_LH and predictors at the
    in-sample 0.5/99.5 percentiles.
(b) multiple testing across the strategy definitions: Holm-Bonferroni on in-sample NW t-stats (gross and 1x).
(c) ES breakeven one-way cost by year for S2 and S5, against 2 ticks at that year's average price.
(d) share of in-sample gross P&L from the top 1% of days.
Reads the daily feature files written by study.py.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

OUT = Path(__file__).resolve().parent
IS_END = pd.Timestamp("2024-10-02")
ANN = 252


def nw_lags(n):
    return int(np.floor(4 * (n / 100.0) ** (2.0 / 9.0)))


def reg(d, x, y="lh"):
    d = d[[y, x]].dropna()
    m = sm.OLS(d[y], sm.add_constant(d[[x]])).fit(cov_type="HAC", cov_kwds={"maxlags": nw_lags(len(d))})
    return m.params[x], m.tvalues[x], m.rsquared * 100, len(d)


def sharpe(x):
    x = np.asarray(x, float)
    return x.mean() / x.std(ddof=1) * np.sqrt(ANN)


def nw_t(x):
    x = np.asarray(x, float)
    m = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": nw_lags(len(x))})
    return m.tvalues[0]


rows = []
conc = []
cost = {"ES_1600": 1e-4, "ZN_1600": 1.5e-4, "ZN_1500": 1.5e-4}
for sn in ("ES_1600", "ZN_1600", "ZN_1500"):
    f = pd.read_parquet(OUT / f"daily_{sn}.parquet")
    full = f[f.index <= IS_END]
    e = full[full.eligible].copy()
    lo, hi = {}, {}
    for c in ("lh", "onfh", "rod"):
        lo[c], hi[c] = e[c].quantile([0.005, 0.995])
    cases = {
        "IS_all": e,
        "IS_ex_covid_2020-02-20_to_04-30": e[~((e.index >= "2020-02-20") & (e.index <= "2020-04-30"))],
        "IS_ex_2020": e[e.index.year != 2020],
        "IS_winsor_0.5_99.5": e.assign(**{c: e[c].clip(lo[c], hi[c]) for c in ("lh", "onfh", "rod")}),
    }
    for cn, d in cases.items():
        for pr in ("onfh", "rod"):
            b, t, r2, n = reg(d, pr)
            g = np.sign(d[pr].values) * d.lh.values
            thr = e[pr].abs().median()
            s5 = np.where(np.abs(d[pr].values) > thr, np.sign(d[pr].values), 0.0)
            g5 = s5 * d.lh.values
            rows.append({"spec": sn, "case": cn, "predictor": pr, "n": n, "slope": b, "nw_t": t, "r2_pct": r2,
                         "sign_gross_bp_per_trade": g.mean() * 1e4,
                         "sign_gross_sharpe_traded_days": sharpe(g),
                         "sign_net1x_sharpe_traded_days": sharpe(g - 2 * cost[sn]),
                         "above_med_gross_bp_per_trade": g5[s5 != 0].mean() * 1e4,
                         "above_med_net1x_sharpe_all_eligible_days": sharpe(g5 - np.abs(s5) * 2 * cost[sn])})
    # concentration of S2 (sign of ROD) gross P&L: top / bottom 1% of in-sample eligible days
    g = np.sign(e.rod.values) * e.lh.values
    k = max(1, int(len(g) * 0.01))
    gs = np.sort(g)
    conc.append({"spec": sn, "n_days": len(g), "k_days_1pct": k, "total_bp": g.sum() * 1e4,
                 "top1pct_bp": gs[::-1][:k].sum() * 1e4, "bottom1pct_bp": gs[:k].sum() * 1e4,
                 "middle98pct_bp": gs[k:-k].sum() * 1e4})
rob = pd.DataFrame(rows)
rob.to_csv(OUT / "robustness_outliers.csv", index=False)
pd.DataFrame(conc).to_csv(OUT / "pnl_concentration.csv", index=False)
print(pd.DataFrame(conc).round(1).to_string())

# (b) multiple testing over strategy definitions, in-sample
s = pd.read_csv(OUT / "strategies.csv")
mt = []
for cl in ("gross", "1x"):
    d = s[(s["sample"] == "IS") & (s.cost == cl) & (s.variant != "B0_ALWAYS_LONG")].copy()
    d["p_two_sided"] = 2 * (1 - stats.norm.cdf(np.abs(d.nw_t_mean)))
    d = d.sort_values("p_two_sided").reset_index(drop=True)
    m = len(d)
    d["holm_threshold"] = 0.05 / (m - np.arange(m))
    rej = (d.p_two_sided <= d.holm_threshold).cumprod().astype(bool)
    d["holm_reject_5pct"] = rej
    d["bonferroni_p"] = np.minimum(1, d.p_two_sided * m)
    d["n_tests"] = m
    mt.append(d[["spec", "variant", "cost", "sharpe", "nw_t_mean", "p_two_sided", "bonferroni_p", "holm_reject_5pct",
                 "n_tests"]])
mt = pd.concat(mt)
mt.to_csv(OUT / "multiple_testing.csv", index=False)

# (c) ES breakeven by year vs 2 ticks at the year's average entry price
f = pd.read_parquet(OUT / "daily_ES_1600.parquet")
e = f[f.eligible].copy()
thr = e[e.index <= IS_END].rod.abs().median()
e["g2"] = np.sign(e.rod) * e.lh
e["s5"] = np.where(e.rod.abs() > thr, np.sign(e.rod), 0.0)
e["g5"] = e.s5 * e.lh
by = []
for y, d in e.groupby(e.index.year):
    for part, dd in (("IS", d[d.index <= IS_END]), ("LATER_descriptive", d[d.index > IS_END])):
        if len(dd) < 30:
            continue
        by.append({"year": y, "part": part, "n": len(dd), "avg_entry_px": dd.entry_px.mean(),
                   "two_ticks_one_way_bp": 0.5 / dd.entry_px.mean() * 1e4,
                   "S2_breakeven_one_way_bp": dd.g2.mean() * 1e4 / 2,
                   "S5_breakeven_one_way_bp": dd.g5[dd.s5 != 0].mean() * 1e4 / 2})
pd.DataFrame(by).to_csv(OUT / "es_breakeven_by_year.csv", index=False)

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 20)
print(rob.round(3).to_string())
print(mt.head(12).round(4).to_string())
print(mt[mt.cost == "1x"].head(6).round(4).to_string())
print(pd.DataFrame(by).round(2).to_string())

# (e) volatility interaction robustness: in-sample, all / ex-COVID window / winsorised (moments from in-sample all)
vi = []
for sn in ("ES_1600", "ZN_1600", "ZN_1500"):
    f = pd.read_parquet(OUT / f"daily_{sn}.parquet")
    e = f[f.eligible & (f.index <= IS_END)].copy()
    for vm in ("rv_prev", "vix_lag1", "rv_sameday"):
        z = (e[vm] - e[vm].mean()) / e[vm].std()
        for pr in ("onfh", "rod"):
            base = pd.DataFrame({"lh": e.lh, "x": e[pr], "z": z}, index=e.index)
            lo_, hi_ = base.quantile(0.005), base.quantile(0.995)
            cases = {"IS_all": base,
                     "IS_ex_covid": base[~((base.index >= "2020-02-20") & (base.index <= "2020-04-30"))],
                     "IS_winsor_0.5_99.5": base.clip(lo_, hi_, axis=1)}
            for cn, d in cases.items():
                d = d.dropna().assign(xz=lambda q: q.x * q.z)
                m = sm.OLS(d.lh, sm.add_constant(d[["x", "z", "xz"]])).fit(
                    cov_type="HAC", cov_kwds={"maxlags": nw_lags(len(d))})
                vi.append({"spec": sn, "vol": vm, "predictor": pr, "case": cn, "n": len(d),
                           "b_pred": m.params.x, "t_pred": m.tvalues.x, "b_pred_x_vol": m.params.xz,
                           "t_pred_x_vol": m.tvalues.xz})
vi = pd.DataFrame(vi)
vi.to_csv(OUT / "robustness_vol_interaction.csv", index=False)
print(vi.round(3).to_string())

# (f) ES candidate strategies with and without the COVID window (in-sample thresholds fixed as in study.py)
f = pd.read_parquet(OUT / "daily_ES_1600.parquet")
e = f[f.eligible & (f.index <= IS_END)]
q2 = e.rv_sameday.quantile(2 / 3)
med = e.rod.abs().median()
cands = {
    "S2_SIGN_ROD": np.where(f.eligible, np.sign(f.rod.fillna(0)), 0.0),
    "S5_ROD_ABOVE_MED": np.where(f.eligible & (f.rod.abs() > med), np.sign(f.rod.fillna(0)), 0.0),
    "S6_SIGN_ROD_HIGHVOL_rv_sameday": np.where(f.eligible & (f.rv_sameday > q2), np.sign(f.rod.fillna(0)), 0.0),
}
exc = ~((f.index >= "2020-02-20") & (f.index <= "2020-04-30"))
cr = []
for nm, s in cands.items():
    g = s * f.lh.fillna(0).values
    for smp, m in (("IS", f.index <= IS_END), ("IS_ex_covid", (f.index <= IS_END) & exc),
                   ("LATER_descriptive", f.index > IS_END)):
        for cl, c in (("gross", 0.0), ("1x", 1e-4), ("2x", 2e-4)):
            x = g[m] - np.abs(s[m]) * 2 * c
            cr.append({"variant": nm, "sample": smp, "cost": cl, "sharpe": sharpe(x), "nw_t": nw_t(x),
                       "gross_bp_per_trade": g[m][s[m] != 0].mean() * 1e4, "trade_frac": (s[m] != 0).mean()})
cr = pd.DataFrame(cr)
cr.to_csv(OUT / "es_candidates_ex_covid.csv", index=False)
print(cr.round(3).to_string())
