"""V3: headline numbers on our data with independent code: frozen rule as run by 'analyse', lookahead
corrections, truncation (causality) test, OOS breakdown, 2022 split, rate-momentum control."""
import json
import math

import numpy as np
import pandas as pd
import statsmodels.api as sm

import vlib as V

OUT = V.HERE / "out"
OUT.mkdir(exist_ok=True)
res = {}

o, ohlc = V.our_opens()
cal = o.index
comb = pd.read_csv(V.EXT / "speech_scores_2011_2026.csv", parse_dates=["speech_date"])
sc = V.kept_scores(V.EXT / "speech_scores_2011_2026.csv")
tf = V.their_fomc()
sched = V.scheduled_fomc()
sched_post = sched[(sched > V.IS_END) & (sched <= V.END)]
fomc_asrun = tf[tf <= V.IS_END].append(sched_post)
# ex-ante (pre-announced) FOMC calendar 2011+: scheduled list, 2012-07-31 corrected to the 2012-08-01 statement day
s_ex = sched[(sched >= "2011-01-01") & (sched <= V.END)]
fomc_exante = pd.DatetimeIndex([pd.Timestamp("2012-08-01") if d == pd.Timestamp("2012-07-31") else d for d in s_ex])

# release time from the site feed: a speech may not be used before the first open after its feed time
fj = pd.read_csv(OUT / "v2_feed_join.csv", parse_dates=["speech_date", "dt"])
fj = fj.set_index("slug")
sc["feed_dt"] = sc["slug"].map(fj["dt"])
opens_dt = cal + pd.Timedelta(hours=9, minutes=30)
k_rule = V.usable_index(cal, sc["speech_date"])
k_feed = np.searchsorted(opens_dt.values, sc["feed_dt"].values, side="right")   # first open strictly after release
k_feed = np.where(sc["feed_dt"].notna(), k_feed, k_rule)
k_fix = np.maximum(k_rule, k_feed)
moved = sc.loc[k_fix != k_rule, ["slug", "speech_date", "feed_dt", "s"]].copy()
moved["rule_session"] = [str(cal[i].date()) if i < len(cal) else None for i in k_rule[k_fix != k_rule]]
moved["fixed_session"] = [str(cal[i].date()) if i < len(cal) else None for i in k_fix[k_fix != k_rule]]
res["release_time_fix_moved_docs"] = moved.astype(str).values.tolist()
# date to feed into the builder: session before the fixed usable session (builder uses 'first session after date')
sc["date_fix"] = [cal[i - 1] if i < len(cal) else pd.Timestamp("2100-01-01") for i in k_fix]

variants = {
    "asrun": dict(sc=sc, fomc=fomc_asrun, vol_lag=1, date_col="speech_date"),
    "fix_release": dict(sc=sc, fomc=fomc_asrun, vol_lag=1, date_col="date_fix"),
    "fix_release_exante_fomc": dict(sc=sc, fomc=fomc_exante, vol_lag=1, date_col="date_fix"),
    "strict_all": dict(sc=sc, fomc=fomc_exante, vol_lag=2, date_col="date_fix"),
}
builds = {k: V.build(o, v["sc"], v["fomc"], vol_lag=v["vol_lag"], date_col=v["date_col"]) for k, v in variants.items()}

# IS weights of the as-run build must equal the replication run on their own CSVs only up to data differences
rep = pd.read_parquet(V.FS / "analyse" / "signal_session_2010_2026.parquet")
res["analyse_signal_columns"] = list(rep.columns)
for c in ("w_tlt", "w_uup", "w_TLT", "w_UUP"):
    if c in rep.columns:
        mine = builds["asrun"]["w"]["TLT" if c.lower().endswith("tlt") else "UUP"]
        res[f"maxabs_vs_analyse_{c}"] = float((mine.reindex(rep.index) - rep[c]).abs().max())


# ------------------------------------------------------------ causality: truncate every input at X
def truncated(X):
    X = pd.Timestamp(X)
    o_x = o.loc[:X]
    sc_x = sc[sc["speech_date"] <= X]
    f_x = fomc_asrun[fomc_asrun <= X + pd.Timedelta(days=60)]   # schedule is known ahead; keep upcoming dates
    return V.build(o_x, sc_x, f_x)["w"]


cz = {}
for X in ("2013-06-28", "2016-11-08", "2020-03-16", "2022-06-15", "2024-10-02", "2025-04-08", "2026-01-30", "2026-10-02"):
    wx = truncated(X)
    full = builds["asrun"]["w"].loc[:X]
    cz[X] = float((wx - full).abs().max().max())
res["truncation_test_max_abs_weight_diff"] = cz


# ------------------------------------------------------------ stats per variant
def stats_block(b, label):
    w = b["w"]
    sa = V.standalone(b)
    e0 = V.engine_run(w, ohlc, tbill=False)
    e1 = V.engine_run(w, ohlc, tbill=True)
    e2 = V.engine_run(w, ohlc, tbill=True, cost_mult=2.0)
    eg = V.engine_run(w, ohlc, tbill=True, cost_mult=0.0)
    legs = {}
    for leg in ("TLT", "UUP"):
        wl = w.copy()
        wl[[c for c in wl.columns if c != leg]] = 0.0
        legs[leg] = V.engine_run(wl, ohlc, tbill=True)
    rows = []
    for wn in V.WINDOWS:
        sa_n = sa["net1"].iloc[:-1]                # last session has no next open
        sa_g = sa["gross"].iloc[:-1]
        if V.WINDOWS[wn][1] == "2024-10-02":      # the 2024-10-02 open-to-open return needs the 2024-10-03 open
            sa_n, sa_g = sa_n.loc[:"2024-10-01"], sa_g.loc[:"2024-10-01"]
        sa_w = V.win(sa_n, wn)
        x1 = V.win(e1["ex"], wn)
        row = {"variant": label, "window": wn, "n_days": len(x1),
               "standalone_rf0_1x": V.sharpe(sa_w), "standalone_rf0_gross": V.sharpe(V.win(sa_g, wn)),
               "engine_rf0_1x": V.sharpe(V.win(e0["net"], wn)),
               "engine_ex_gross": V.sharpe(V.win(eg["ex"], wn)), "engine_ex_1x": V.sharpe(x1), "engine_ex_2x": V.sharpe(V.win(e2["ex"], wn)),
               "engine_ex_tlt": V.sharpe(V.win(legs["TLT"]["ex"], wn)), "engine_ex_uup": V.sharpe(V.win(legs["UUP"]["ex"], wn)),
               "ann_ex_mean": float(x1.mean() * 252), "ann_vol": float(x1.std() * math.sqrt(252)), "maxdd_ex": V.maxdd(x1),
               "nw_t": V.nw_t(x1), "turnover_yr": float(V.win(e1["to"], wn).sum() / (len(x1) / 252)),
               "mean_w_tlt": float(V.win(w["TLT"], wn).mean()), "mean_z": float(V.win(b["z"], wn).mean()),
               "frac_z_pos": float((V.win(b["z"], wn) > 0).mean())}
        if wn in ("IS", "HOLDOUT", "FULL"):
            no22 = x1[x1.index.year != 2022]
            row["engine_ex_1x_ex2022"] = V.sharpe(no22)
            row["engine_rf0_1x_ex2022"] = V.sharpe(V.win(e0["net"], wn)[lambda s: s.index.year != 2022])
            row["standalone_1x_ex2022"] = V.sharpe(sa_w[sa_w.index.year != 2022])
            row["engine_ex_1x_2022"] = V.sharpe(x1[x1.index.year == 2022])
            row["share_pnl_2022"] = float(x1[x1.index.year == 2022].sum() / x1.sum())
        rows.append(row)
    return rows, {"sa": sa, "e0": e0, "e1": e1, "e2": e2, "eg": eg}


tab, runs = [], {}
for k, b in builds.items():
    r, rr = stats_block(b, k)
    tab += r
    runs[k] = rr
T = pd.DataFrame(tab)
T.to_csv(OUT / "v3_headline.csv", index=False)

# OOS sub-periods and yearly (as-run, engine excess)
x = runs["asrun"]["e1"]["ex"]
sub = {}
for nm, (a, z) in {"2024Q4": ("2024-10-03", "2024-12-31"), "2025": ("2025-01-01", "2025-12-31"),
                   "2026_to_Oct2": ("2026-01-01", "2026-10-02"), "OOS_ex_2024Q4": ("2025-01-01", "2026-10-02")}.items():
    s = x.loc[a:z]
    sub[nm] = {"cum_ex": float((1 + s).prod() - 1), "sharpe_ex": V.sharpe(s), "mean_w_tlt": float(builds["asrun"]["w"]["TLT"].loc[a:z].mean())}
res["oos_subperiods_asrun"] = sub
yr = pd.DataFrame({k: (1 + runs[k]["e1"]["ex"].loc["2011-12-30":]).groupby(lambda d: d.year).prod() - 1 for k in runs})
yr.to_csv(OUT / "v3_yearly_excess.csv")
dg = V.E.load_series("fred_daily.parquet", "FWD")["DGS2"].dropna()
dgc = dg.reindex(dg.index.union(cal)).ffill().reindex(cal)
res["dgs2_change_2024Q4_bp"] = float((dgc.loc["2024-12-31"] - dgc.loc["2024-10-02"]) * 100)
res["corr_C_DGS2_t2"] = {wn: float(pd.concat([V.win(builds["asrun"]["C"], wn), V.win(dgc.shift(2), wn)], axis=1).dropna().corr().iloc[0, 1])
                         for wn in ("IS", "OOS")}

# bootstrap interval for the OOS and IS Sharpe (circular 63-day blocks)
def boot(xs, block=63, n=5000, seed=3):
    v = xs.dropna().to_numpy()
    T_ = len(v)
    rng = np.random.default_rng(seed)
    nb = math.ceil(T_ / block)
    out = np.empty(n)
    for i in range(n):
        st = rng.integers(0, T_, nb)
        idx = (st[:, None] + np.arange(block)[None, :]).ravel()[:T_] % T_
        y = v[idx]
        out[i] = y.mean() / y.std(ddof=1) * math.sqrt(252)
    return [float(np.quantile(out, 0.05)), float(np.quantile(out, 0.95)), float((out <= 0).mean())]


res["boot90_IS_ex_1x"] = boot(V.win(x, "IS"))
res["boot90_OOS_ex_1x"] = boot(V.win(x, "OOS"))

# ------------------------------------------------------------ control: decayed 2-day-lagged DGS2 change
inj = (dgc.shift(2) - dgc.shift(3)).fillna(0.0).to_numpy()
Cc = np.zeros(len(cal))
acc = 0.0
for i, v in enumerate(inj):
    acc = V.LAM * acc + v
    Cc[i] = acc
Cc = pd.Series(Cc, index=cal)
bctl = V.build(o, sc, fomc_asrun, C=Cc)
ctl1 = V.engine_run(bctl["w"], ohlc, tbill=True)
ctl0 = V.engine_run(bctl["w"], ohlc, tbill=False)
ctl_rows = []
for vk in ("asrun", "strict_all"):
    y_all = runs[vk]["e1"]["ex"]
    for wn in V.WINDOWS:
        y, xx = V.win(y_all, wn), V.win(ctl1["ex"], wn)
        df = pd.concat([y.rename("y"), xx.rename("x")], axis=1).dropna()
        fit = sm.OLS(df["y"], sm.add_constant(df["x"])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
        ctl_rows.append({"strategy": vk, "window": wn, "ctl_sharpe_ex_1x": V.sharpe(xx), "ctl_sharpe_rf0_1x": V.sharpe(V.win(ctl0["net"], wn)),
                         "ctl_ex2022": V.sharpe(xx[xx.index.year != 2022]) if wn != "OOS" else np.nan,
                         "strat_sharpe_ex_1x": V.sharpe(y), "corr_daily": float(df.corr().iloc[0, 1]),
                         "beta": float(fit.params["x"]), "beta_t": float(fit.tvalues["x"]),
                         "alpha_ann": float(fit.params["const"] * 252), "alpha_t": float(fit.tvalues["const"]), "r2": float(fit.rsquared)})
res["corr_C_tone_C_ctl_IS"] = float(pd.concat([V.win(builds["asrun"]["C"], "IS"), V.win(Cc, "IS")], axis=1).corr().iloc[0, 1])
CT = pd.DataFrame(ctl_rows)
CT.to_csv(OUT / "v3_control.csv", index=False)

# tone predictive content: corr of z with the next 20-session open-to-open TLT return, raw and partial on z_ctl
lo = np.log(o["TLT"])
f20 = (lo.shift(-20) - lo)
zz = pd.concat([builds["asrun"]["z"].rename("z"), bctl["z"].rename("zc"), f20.rename("f")], axis=1)
pc = {}
for wn in ("IS", "OOS"):
    d = V.win(zz, wn).dropna()
    rz = d["z"] - sm.OLS(d["z"], sm.add_constant(d["zc"])).fit().fittedvalues
    rf_ = d["f"] - sm.OLS(d["f"], sm.add_constant(d["zc"])).fit().fittedvalues
    pc[wn] = {"corr_z_f20": float(d["z"].corr(d["f"])), "partial_corr_given_zctl": float(rz.corr(rf_)), "n": len(d)}
res["tone_vs_fwd20_TLT"] = pc

# save daily series for the portfolio step
daily = pd.DataFrame({f"{k}_{c}": runs[k][r_]["ex" if c != "rf0" else "net"] for k in runs for c, r_ in
                      (("ex1", "e1"), ("ex2", "e2"), ("exg", "eg"), ("rf0", "e0"))})
for k in runs:
    h = runs[k]["e1"]["held"]
    daily[f"{k}_gross_lev"] = h.abs().sum(axis=1)
    daily[f"{k}_cost_bp"] = float((h.loc["2011-12-30":"2024-10-02"].abs().mean() * pd.Series(V.COST)).sum()
                                  / h.loc["2011-12-30":"2024-10-02"].abs().mean().sum())
daily["ctl_ex1"] = ctl1["ex"]
daily.to_parquet(OUT / "v3_daily.parquet")
pd.DataFrame({k: builds[k]["w"]["TLT"] for k in builds}).join(
    pd.DataFrame({k + "_uup": builds[k]["w"]["UUP"] for k in builds})).join(
    pd.DataFrame({k + "_z": builds[k]["z"] for k in builds})).to_parquet(OUT / "v3_weights_session.parquet")

pd.set_option("display.width", 250, "display.max_columns", 40)
print(T.round(3).to_string())
print(CT.round(3).to_string())
print(json.dumps(res, indent=1, default=str))
(OUT / "v3_main.json").write_text(json.dumps(res, indent=1, default=str))
