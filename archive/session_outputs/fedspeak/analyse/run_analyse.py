"""Variant A end to end (PREDECLARED.md): full results, rate-momentum control, 2022 dependence, futures version,
portfolio fit. Writes tables to this folder. Read-only use of the engine; nothing is written to the repo."""
from __future__ import annotations

import importlib.util
import json
import math

import numpy as np
import pandas as pd

import fa_lib as L

OUT = L.HERE
EX22 = ("2022-01-01", "2022-12-31")


def windows_ext():
    w = dict(L.WIN)
    for k in ("IS", "HOLDOUT", "FULL"):
        w[f"{k}_ex2022"] = L.WIN[k]
    return w


def run_rows(name: str, run: dict, keys: list[str]) -> list[dict]:
    rows = []
    for wn, (a, b) in windows_ext().items():
        for k in keys:
            if k not in run:
                continue
            r = L.sl(run[k], a, b)
            if wn.endswith("_ex2022"):
                r = r[(r.index < EX22[0]) | (r.index > EX22[1])]
            if r.dropna().shape[0] < 40:
                continue
            tot = L.sl(run["total_net1x"], a, b) if k == "ex_net1x" else None
            st = L.series_stats(r, run["turnover"] if k.endswith("net1x") else None, tot)
            st.update({"strategy": name, "window": wn, "series": k})
            rows.append(st)
    return rows


def yearly_table(name: str, run: dict, sig: pd.DataFrame | None, prefix: str | None, n_docs: pd.Series | None) -> pd.DataFrame:
    a, b = L.WIN["FULL"]
    cols = {}
    futures = name.startswith("fut_")
    for k in ("rf0_net1x", "ex_net1x", "ex_gross", "ex_leg_TLT", "ex_leg_UUP", "ex_leg_F_ZN", "ex_leg_F_ZB", "ex_leg_F_6E"):
        if k in run and not (futures and k.startswith("rf0")):
            cols[f"sharpe_{k}"] = L.yearly_sharpe(L.sl(run[k], a, b))
    cols["ret_ex_net1x"] = L.yearly_sum(L.sl(run["ex_net1x"], a, b))
    if "rf0_net1x" in run and not futures:
        cols["ret_rf0_net1x"] = L.yearly_sum(L.sl(run["rf0_net1x"], a, b))
    if sig is not None and prefix is not None:
        s = sig.loc[a:b]
        zc = {"tone": "z_tone", "ctl": "z_ctl", "orth": "z_orth"}[prefix]
        cols["mean_z"] = s[zc].groupby(s.index.year).mean()
        cols["share_z_pos"] = (s[zc] > 0).groupby(s.index.year).mean()
        cols["mean_w_TLT"] = s[f"{prefix}_TLT"].groupby(s.index.year).mean()
    if n_docs is not None:
        cols["kept_docs"] = n_docs
    t = pd.DataFrame(cols)
    t = t.loc[(t.index >= 2011) & (t.index <= 2026)]
    t.index.name = "year"
    t.insert(0, "strategy", name)
    return t


def win_bounds(wn: str) -> tuple[str, str]:
    return L.WIN[wn.replace("_ex2022", "")]


def series_cagr(r: pd.Series, drop2022: bool = False) -> float:
    r = r.dropna()
    if drop2022:
        r = r[(r.index < EX22[0]) | (r.index > EX22[1])]
    return float((1 + r).prod() ** (252 / len(r)) - 1)


def fwd_ret(o: pd.Series, h: int) -> tuple[pd.Series, pd.Series]:
    r = o.shift(-h) / o - 1.0
    end = pd.Series(o.index, index=o.index).shift(-h)
    return r, end


def main():
    B = L.build_all()
    sig, ohlc, rf, cal = B["sig"], B["ohlc"], B["rf"], B["cal"]
    res: dict = {"inputs": {"kept_docs_total": int(len(B["scores"])),
                            "kept_docs_post_cut": int((B["scores"]["speech_date"] > L.IS_END).sum()),
                            "last_doc": str(B["scores"]["speech_date"].max().date()),
                            "fomc_post_cut": [str(x.date()) for x in B["fomc"][B["fomc"] > L.IS_END]]}}
    # in-sample weights must equal the replication's
    rep = pd.read_parquet(L.REP / "signal_session_full.parquet")
    res["check_is_weights_vs_replicate_max_abs"] = float(
        (sig[["tone_TLT", "tone_UUP"]].to_numpy() - rep[["w_TLT", "w_UUP"]].reindex(sig.index).to_numpy())[sig.index <= L.IS_END].__abs__().max())

    # ------------------------------------------------------------------ 1. ETF runs: tone, control, orthogonalised
    runs = {}
    for name, prefix in (("tone", "tone"), ("ctl_dgs2", "ctl"), ("tone_orth", "orth")):
        w = L.weights_of(sig, prefix)
        runs[name] = L.run_engine(w, ohlc, rf, L.COST_ETF)
        held = runs[name]["held"]
        res[f"check_held_eq_session_weight_{name}"] = float((held - w.reindex(held.index).fillna(0)).loc["2011-12-30":].abs().max().max())
    keys = ["rf0_gross", "rf0_net1x", "rf0_net2x", "ex_gross", "ex_net1x", "ex_net2x",
            "rf0_leg_TLT", "ex_leg_TLT", "rf0_leg_UUP", "ex_leg_UUP"]
    rows = []
    for name in runs:
        rows += run_rows(name, runs[name], keys)

    # ------------------------------------------------------------------ 4. futures version
    fut = {}
    for bond in ("F_ZN", "F_ZB"):
        w_hold, fo, vol_dec = L.futures_weights(sig, bond, rf)
        r = L.run_engine(w_hold, fo, rf, L.COST_FUT, exec="next_close")
        res[f"check_futures_held_eq_{bond}"] = float((r["held"] - w_hold.reindex(r["held"].index).fillna(0)).loc["2011-12-30":].abs().max().max())
        g = w_hold.abs().sum(axis=1)
        a, b = L.WIN["FULL"]
        res[f"futures_{bond}_diag"] = {
            "mean_gross_IS": float(g.loc[L.WIN["IS"][0]:L.IS_END].mean()), "mean_gross_OOS": float(g.loc[L.WIN["OOS"][0]:].mean()),
            "share_days_gross_at_cap_IS": float((g.loc[L.WIN["IS"][0]:L.IS_END] >= 1.5 - 1e-9).mean()),
            "share_days_vol_at_floor_IS": float((vol_dec.loc[L.WIN["IS"][0]:L.IS_END] <= 0.04 + 1e-12).mean()),
            "median_vol_mix_IS": float(vol_dec.loc[L.WIN["IS"][0]:L.IS_END].median()),
            "corr_daily_ex_with_etf_tone": float(pd.concat([L.sl(r["ex_net1x"], a, b), L.sl(runs["tone"]["ex_net1x"], a, b)], axis=1).corr().iloc[0, 1])}
        fut[bond] = r
        runs[f"fut_{bond}"] = r
        rows += run_rows(f"fut_{bond}", r, ["ex_gross", "ex_net1x", "ex_net2x", f"ex_leg_{bond}", "ex_leg_F_6E"])
    g_etf = L.weights_of(sig, "tone").abs().sum(axis=1)
    res["etf_tone_diag"] = {"mean_gross_IS": float(g_etf.loc[L.WIN["IS"][0]:L.IS_END].mean()),
                            "mean_gross_OOS": float(g_etf.loc[L.WIN["OOS"][0]:].mean()),
                            "share_days_gross_at_cap_IS": float((g_etf.loc[L.WIN["IS"][0]:L.IS_END] >= 1.5 - 1e-9).mean())}

    tab = pd.DataFrame(rows)
    front = ["strategy", "window", "series", "start", "end", "n_days", "sharpe", "ann_mean", "cagr", "vol", "max_dd", "max_dd_total",
             "nw_t", "turnover_per_year", "skew", "hit_rate"]
    tab = tab[front + [c for c in tab.columns if c not in front]]
    tab.to_csv(OUT / "t1_results_all.csv", index=False)

    # compact headline (tone)
    hl = []
    for wn in ("IS", "HOLDOUT", "OOS", "FULL", "IS_ex2022", "HOLDOUT_ex2022", "FULL_ex2022"):
        row = {"window": wn}
        for k, lab in (("rf0_gross", "rf0_gross"), ("rf0_net1x", "rf0_1x"), ("rf0_net2x", "rf0_2x"),
                       ("ex_gross", "ex_gross"), ("ex_net1x", "ex_1x"), ("ex_net2x", "ex_2x"),
                       ("rf0_leg_TLT", "rf0_TLT_1x"), ("rf0_leg_UUP", "rf0_UUP_1x"), ("ex_leg_TLT", "ex_TLT_1x"), ("ex_leg_UUP", "ex_UUP_1x")):
            q = tab[(tab.strategy == "tone") & (tab.window == wn) & (tab.series == k)]
            row[f"sharpe_{lab}"] = float(q["sharpe"].iloc[0]) if len(q) else np.nan
        q = tab[(tab.strategy == "tone") & (tab.window == wn) & (tab.series == "ex_net1x")].iloc[0]
        q0 = tab[(tab.strategy == "tone") & (tab.window == wn) & (tab.series == "rf0_net1x")].iloc[0]
        row.update({"ann_mean_ex_1x": q["ann_mean"], "ann_mean_rf0_1x": q0["ann_mean"], "cagr_ex_1x": q["cagr"], "cagr_rf0_1x": q0["cagr"],
                    "cagr_total_1x": series_cagr(L.sl(runs["tone"]["total_net1x"], *win_bounds(wn)), wn.endswith("_ex2022")),
                    "vol_ex_1x": q["vol"], "max_dd_ex_1x": q["max_dd"], "max_dd_total_1x": q["max_dd_total"],
                    "max_dd_rf0_1x": q0["max_dd"], "nw_t_ex_1x": q["nw_t"], "turnover_per_year": q["turnover_per_year"],
                    "n_days": q["n_days"], "start": q["start"], "end": q["end"]})
        hl.append(row)
    hl = pd.DataFrame(hl)
    hl.to_csv(OUT / "t1_headline_tone.csv", index=False)

    n_docs = B["scores"].groupby(B["scores"]["speech_date"].dt.year).size()
    yt = pd.concat([yearly_table("tone", runs["tone"], sig, "tone", n_docs),
                    yearly_table("ctl_dgs2", runs["ctl_dgs2"], sig, "ctl", None),
                    yearly_table("tone_orth", runs["tone_orth"], sig, "orth", None),
                    yearly_table("fut_F_ZN", fut["F_ZN"], None, None, None),
                    yearly_table("fut_F_ZB", fut["F_ZB"], None, None, None)])
    yt.to_csv(OUT / "t1_yearly.csv")

    # OOS behaviour of the signal
    o_ = sig.loc[L.WIN["OOS"][0]:]
    i_ = sig.loc[L.WIN["IS"][0]:L.IS_END]
    res["signal_behaviour"] = {
        "OOS": {"mean_z_tone": float(o_.z_tone.mean()), "share_z_pos": float((o_.z_tone > 0).mean()),
                "mean_w_TLT": float(o_.tone_TLT.mean()), "mean_abs_w_TLT": float(o_.tone_TLT.abs().mean()),
                "mean_C_tone": float(o_.C_tone.mean())},
        "IS": {"mean_z_tone": float(i_.z_tone.mean()), "share_z_pos": float((i_.z_tone > 0).mean()),
               "mean_w_TLT": float(i_.tone_TLT.mean()), "mean_abs_w_TLT": float(i_.tone_TLT.abs().mean()),
               "mean_C_tone": float(i_.C_tone.mean())}}

    # ------------------------------------------------------------------ 2. more than rate momentum?
    reg_rows = []
    tlt_cc = ohlc["close"]["TLT"].pct_change(fill_method=None) - rf.reindex(ohlc["close"].index).ffill().fillna(0.0)
    for wn, (a, b) in L.WIN.items():
        y = L.sl(runs["tone"]["ex_net1x"], a, b)
        x = L.sl(runs["ctl_dgs2"]["ex_net1x"], a, b).rename("ctl")
        f = L.ols_hac(y, x.to_frame(), 5)
        alpha_series = y - f["b_ctl"] * x
        reg_rows.append({"window": wn, "model": "tone_on_ctl (pre-declared)", "n": f["n"], "alpha_ann": f["b_const"] * 252,
                         "t_alpha": f["t_const"], "beta_ctl": f["b_ctl"], "t_beta_ctl": f["t_ctl"], "r2": f["r2"],
                         "corr": float(pd.concat([y, x], axis=1).corr().iloc[0, 1]),
                         "alpha_ir": f["b_const"] * 252 / (f["resid_std"] * math.sqrt(252)),
                         "sharpe_tone": L.sharpe(y), "sharpe_ctl": L.sharpe(x), "sharpe_tone_minus_beta_ctl": L.sharpe(alpha_series)})
        X2 = pd.concat([x, L.sl(tlt_cc, a, b).rename("tlt")], axis=1)
        f2 = L.ols_hac(y, X2, 5)
        reg_rows.append({"window": wn, "model": "tone_on_ctl_and_TLT (descriptive extra)", "n": f2["n"], "alpha_ann": f2["b_const"] * 252,
                         "t_alpha": f2["t_const"], "beta_ctl": f2["b_ctl"], "t_beta_ctl": f2["t_ctl"], "beta_tlt": f2["b_tlt"],
                         "t_beta_tlt": f2["t_tlt"], "r2": f2["r2"]})
        y3 = L.sl(runs["tone_orth"]["ex_net1x"], a, b)
        f3 = L.ols_hac(y3, x.to_frame(), 5)
        reg_rows.append({"window": wn, "model": "orth_on_ctl (descriptive)", "n": f3["n"], "alpha_ann": f3["b_const"] * 252,
                         "t_alpha": f3["t_const"], "beta_ctl": f3["b_ctl"], "t_beta_ctl": f3["t_ctl"], "r2": f3["r2"],
                         "corr": float(pd.concat([y3, x], axis=1).corr().iloc[0, 1])})
    pd.DataFrame(reg_rows).to_csv(OUT / "t2_regression_on_control.csv", index=False)

    # partial correlations with future TLT open-to-open returns
    o_tlt = B["open"]["TLT"]
    dg = sig["dgs2"]
    ctrlB = pd.DataFrame({"z_ctl": sig["z_ctl"], "d5": dg.shift(2) - dg.shift(7), "d60": dg.shift(2) - dg.shift(62)})
    pc_rows = []
    for wn in ("IS", "HOLDOUT", "OOS", "FULL"):
        a, b = L.WIN[wn]
        for h, nonover in ((1, False), (5, False), (20, False), (20, True)):
            r_h, end = fwd_ret(o_tlt, h)
            m = (sig.index >= pd.Timestamp(a)) & (end <= pd.Timestamp(b)).to_numpy() & sig["z_tone"].notna().to_numpy()
            idx = sig.index[m]
            if nonover:
                idx = idx[::h]
            zt, zc, rr = sig.loc[idx, "z_tone"], sig.loc[idx, "z_ctl"], r_h.loc[idx].rename("r")
            lags = 0 if nonover else h + 4
            fa = L.ols_hac(rr, pd.DataFrame({"z_tone": zt, "z_ctl": zc}), lags)
            fb = L.ols_hac(rr, pd.concat([zt.rename("z_tone"), ctrlB.loc[idx]], axis=1), lags)
            f0 = L.ols_hac(rr, zt.rename("z_tone").to_frame(), lags)
            pc_rows.append({"window": wn, "h_sessions": h, "sampling": "non-overlapping" if nonover else "daily overlapping",
                            "n": len(idx), "corr_ztone_r": float(zt.corr(rr)), "corr_zctl_r": float(zc.corr(rr)),
                            "corr_ztone_zctl": float(zt.corr(zc)),
                            "pcorr_ztone_r_given_zctl": L.partial_corr(zt, rr, zc.to_frame()),
                            "pcorr_ztone_r_given_specB": L.partial_corr(zt, rr, ctrlB.loc[idx]),
                            "t_ztone_alone": f0["t_z_tone"], "b_ztone_alone_bp": f0["b_z_tone"] * 1e4,
                            "t_ztone_specA": fa["t_z_tone"], "t_zctl_specA": fa["t_z_ctl"], "b_ztone_specA_bp": fa["b_z_tone"] * 1e4,
                            "t_ztone_specB": fb["t_z_tone"], "b_ztone_specB_bp": fb["b_z_tone"] * 1e4, "hac_lags": lags})
    pd.DataFrame(pc_rows).to_csv(OUT / "t2_partial_corr.csv", index=False)

    # level and signal correlations (the 0.53 diagnostic, IS and OOS)
    dcor = {}
    for wn in ("IS", "OOS", "FULL"):
        a, b = L.WIN[wn]
        s = sig.loc[a:b]
        dcor[wn] = {"corr_Ctone_DGS2level_t-2": float(s.C_tone.corr(sig.dgs2.shift(2).loc[a:b])),
                    "corr_Ctone_Cctl": float(s.C_tone.corr(s.C_ctl)), "corr_ztone_zctl": float(s.z_tone.corr(s.z_ctl)),
                    "corr_ztone_zorth": float(s.z_tone.corr(s.z_orth)),
                    "corr_wTLT_tone_ctl": float(s.tone_TLT.corr(s.ctl_TLT)),
                    "corr_daily_ret_tone_ctl": float(pd.concat([L.sl(runs["tone"]["ex_net1x"], a, b), L.sl(runs["ctl_dgs2"]["ex_net1x"], a, b)], axis=1).corr().iloc[0, 1])}
    res["signal_correlations"] = dcor
    pd.DataFrame(dcor).T.to_csv(OUT / "t2_signal_correlations.csv")

    # ------------------------------------------------------------------ 3. 2022 dependence
    d_rows = []
    boot_rows = []
    for k in ("ex_net1x", "rf0_net1x"):
        r_full = runs["tone"][k]
        for wn in ("IS", "FULL"):
            a, b = L.WIN[wn]
            r = L.sl(r_full, a, b).dropna()
            top = r.nlargest(10)
            top1 = r.nlargest(int(round(0.01 * len(r))))
            y22 = r[(r.index >= EX22[0]) & (r.index <= EX22[1])]
            d_rows.append({"series": k, "window": wn, "n": len(r), "sharpe": L.sharpe(r),
                           "sharpe_ex2022": L.sharpe(r[(r.index < EX22[0]) | (r.index > EX22[1])]),
                           "sum_daily_ret": float(r.sum()), "sum_2022": float(y22.sum()), "share_pnl_2022": float(y22.sum() / r.sum()),
                           "sum_top10_days": float(top.sum()), "share_pnl_top10_days": float(top.sum() / r.sum()),
                           "sharpe_without_top10_days": L.sharpe(r.drop(top.index)),
                           "top10_days_in_2022": int(((top.index >= EX22[0]) & (top.index <= EX22[1])).sum()),
                           "top10_dates": ";".join(str(x.date()) for x in top.index),
                           "share_pnl_top1pct_days": float(top1.sum() / r.sum()), "sharpe_without_top1pct_days": L.sharpe(r.drop(top1.index))})
        for blk in (63, 21, 126):
            bs = L.block_boot_sharpe(L.sl(r_full, *L.WIN["IS"]), block=blk, n=10_000, seed=7)
            bs.update({"series": k, "window": "IS"})
            boot_rows.append(bs)
        for wn in ("HOLDOUT", "OOS"):
            bs = L.block_boot_sharpe(L.sl(r_full, *L.WIN[wn]), block=63, n=10_000, seed=7)
            bs.update({"series": k, "window": wn})
            boot_rows.append(bs)
    pd.DataFrame(d_rows).to_csv(OUT / "t3_2022_topdays.csv", index=False)
    pd.DataFrame(boot_rows).to_csv(OUT / "t3_bootstrap.csv", index=False)

    # ------------------------------------------------------------------ 5. portfolio fit
    port = portfolio_fit(runs, sig, res)

    # ------------------------------------------------------------------ save series
    daily = pd.DataFrame({f"{n}_{k}": runs[n][k] for n in runs for k in ("ex_net1x", "ex_net2x", "ex_gross", "rf0_net1x")
                          if k in runs[n]})
    daily = daily.loc[L.WIN["FULL"][0]:L.END]
    daily.index.name = "date"
    daily.to_parquet(OUT / "daily_returns.parquet")
    s_out = sig.copy()
    s_out.index.name = "entry_session"
    s_out.to_parquet(OUT / "signal_session_2010_2026.parquet")
    (OUT / "results.json").write_text(json.dumps(res, indent=2, default=str))

    pd.set_option("display.width", 250, "display.max_columns", 40)
    print(hl.round(3).to_string())
    show = tab[(tab.series == "ex_net1x")][["strategy", "window", "sharpe", "ann_mean", "vol", "max_dd", "nw_t", "turnover_per_year"]]
    print(show.round(3).to_string())
    print(yt.round(2).to_string())
    print(pd.DataFrame(reg_rows).round(3).to_string())
    print(pd.DataFrame(pc_rows).round(3).to_string())
    print(pd.DataFrame(d_rows).drop(columns=["top10_dates"]).round(3).to_string())
    print(pd.DataFrame(boot_rows).round(3).to_string())
    print(port.round(3).to_string())
    print(json.dumps(res, indent=1, default=str))


def portfolio_fit(runs: dict, sig: pd.DataFrame, res: dict) -> pd.DataFrame:
    spec = importlib.util.spec_from_file_location("combine", L.EDGES / "combine" / "combine.py")
    CB = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(CB)
    cal, rf, slv, gr, cost, nat, es_ex, s1, f2, extra = CB.load()
    core = ["rpm_ES_MM", "CAL_TSY_ME_ZN", "S1"]
    saved = pd.read_parquet(L.EDGES / "series" / "PORT_core_ER_6.parquet")
    base = CB.build(core, "ER", 0.06, cal, slv, gr, cost)
    res["check_core_ER_6_rebuild_max_abs"] = float((base["ret"]["net_1x"].reindex(saved.index) - saved["net_1x"]).abs().max())

    first = pd.Timestamp(L.WIN["IS"][0])
    for nm, run, legs, cmap in (("FED", runs["tone"], ["TLT", "UUP"], L.COST_ETF), ("FEDF", runs["fut_F_ZN"], ["F_ZN", "F_6E"], L.COST_FUT)):
        df = pd.DataFrame({"net_1x": run["ex_net1x"], "net_2x": run["ex_net2x"], "gross": run["ex_gross"]})
        df.loc[df.index < first] = np.nan
        slv[nm] = df.reindex(cal)
        held = run["held"].reindex(cal).fillna(0.0)
        gr[nm] = held.abs().sum(axis=1).where(slv[nm]["net_1x"].notna(), 0.0)
        mabs = held.loc[first:L.IS_END].abs().mean()
        cost[nm] = float(sum(mabs[t] * cmap[t] for t in legs) / mabs.sum())
    res["portfolio_sleeve_cost_bp"] = {"FED": cost["FED"], "FEDF": cost["FEDF"]}

    variants = {"core_ER_6 (base)": core, "core+FED_ER_6": core + ["FED"], "core+FEDF_ZN_ER_6": core + ["FEDF"]}
    built = {k: (base if k.startswith("core_ER_6") else CB.build(v, "ER", 0.06, cal, slv, gr, cost)) for k, v in variants.items()}
    p_start = pd.Timestamp("2012-05-02")
    pwin = {"IS": (p_start, pd.Timestamp(L.IS_END)), "HOLDOUT": (pd.Timestamp("2021-01-01"), pd.Timestamp(L.IS_END)),
            "OOS": (pd.Timestamp(L.WIN["OOS"][0]), pd.Timestamp(L.END)), "FULL": (p_start, pd.Timestamp(L.END)),
            "IS_h1": (p_start, pd.Timestamp("2017-12-31")), "IS_h2": (pd.Timestamp("2018-01-01"), pd.Timestamp(L.IS_END))}
    rows = []
    b1 = built["core_ER_6 (base)"]["ret"]
    for k, bld in built.items():
        R = bld["ret"]
        for wn, (a, z) in pwin.items():
            x = R.loc[a:z]
            ex = x["net_1x"].dropna()
            row = {"portfolio": k, "window": wn, "start": str(ex.index[0].date()), "end": str(ex.index[-1].date()),
                   "sharpe_1x": L.sharpe(ex), "sharpe_2x": L.sharpe(x["net_2x"]), "sharpe_gross": L.sharpe(x["gross"]),
                   "ann_excess_mean": float(ex.mean() * 252), "vol": float(ex.std() * math.sqrt(252)), "max_dd_excess": L.max_dd(ex),
                   "nw_t": L.E.newey_west_tstat(ex, 5)}
            if not k.startswith("core_ER_6"):
                bb = CB.block_boot_diff(ex, b1["net_1x"].loc[a:z], block=63, n=5000, seed=11)
                row.update({"d_sharpe_vs_base": bb["diff"], "boot_p_two_sided": bb["p_two_sided"],
                            "boot_ci90_lo": bb["ci90"][0], "boot_ci90_hi": bb["ci90"][1],
                            "corr_with_base": float(pd.concat([ex, b1["net_1x"].loc[a:z]], axis=1).corr().iloc[0, 1])})
                nm = variants[k][-1]
                row["mean_mult_new_sleeve"] = float(bld["m"][nm].loc[a:z].mean())
                row["mean_mult_core"] = json.dumps({n: round(float(bld["m"][n].loc[a:z].mean()), 3) for n in core})
            rows.append(row)
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "t5_portfolio_test.csv", index=False)

    # correlations with the portfolio and its sleeves
    c_rows = []
    others = {"PORT_core_ER_6": saved["net_1x"], "rpm_ES_MM": slv["rpm_ES_MM"]["net_1x"],
              "CAL_TSY_ME_ZN": slv["CAL_TSY_ME_ZN"]["net_1x"], "S1": slv["S1"]["net_1x"], "ES_excess": es_ex}
    zn = L.E.load_ohlc(["F_ZN"], "FWD")["close"]["F_ZN"].loc[:L.END]
    others["F_ZN_excess"] = zn.pct_change(fill_method=None) - rf.reindex(zn.index).ffill().fillna(0.0)
    for strat, s in (("tone_ETF", runs["tone"]["ex_net1x"]), ("tone_fut_ZN", runs["fut_F_ZN"]["ex_net1x"]),
                     ("ctl_dgs2_ETF", runs["ctl_dgs2"]["ex_net1x"])):
        for wn, (a, z) in (("IS", pwin["IS"]), ("OOS", pwin["OOS"]), ("FULL", pwin["FULL"])):
            for on, o in others.items():
                j = pd.concat([s.loc[a:z].rename("a"), o.reindex(cal).loc[a:z].rename("b")], axis=1).dropna()
                mj = j.groupby(j.index.to_period("M")).sum()
                c_rows.append({"strategy": strat, "window": wn, "vs": on, "n_days": len(j), "corr_daily": float(j.corr().iloc[0, 1]),
                               "corr_monthly": float(mj.corr().iloc[0, 1]), "n_months": len(mj)})
    pd.DataFrame(c_rows).to_csv(OUT / "t5_correlations.csv", index=False)
    print(pd.DataFrame(c_rows).round(3).to_string())
    return tab


if __name__ == "__main__":
    main()
