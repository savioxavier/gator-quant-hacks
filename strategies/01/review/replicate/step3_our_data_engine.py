"""Step 3: the same rule on our data (etf_daily, fred_daily), in the stand-alone open-to-open simulator
(their accounting, rf = 0) and in our engine.simulate (exec="next_open", cost_bps TLT 1.5 / UUP 5.0).
Writes signal.parquet (decision-date index, engine convention) for reuse."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

import common as K
import fedsignal as F
from step2_data_check import NON_DECISION

COST = {"TLT": 1.5, "UUP": 5.0}
WINDOWS = {"IS_2012_2024": ("2011-12-30", K.IS_END), "holdout_2021_2024": K.HOLDOUT,
           "y2022": ("2022-01-01", "2022-12-31")}


def build_our_signal(period: str, fomc, scores, spec=F.Spec(), lag_signal: int = 0, lag_vol: int = 0):
    cal, o, _ = K.our_opens(period)
    r_t, r_u = K.open_to_open(o["TLT"]), K.open_to_open(o["UUP"])
    c = F.consensus(cal, scores, spec.half_life).shift(lag_signal).fillna(0.0)
    z = F.expanding_z(c, spec.z_clock_start, spec.z_min_obs)
    vol = F.mix_vol(r_t, r_u, spec).shift(lag_vol)
    fd, fn = F.fomc_flags(cal, fomc)
    w = F.size_positions(z, vol, fd, fn, spec)
    sig = pd.concat([c, z, vol, fd, fn, w], axis=1)
    return cal, sig, r_t, r_u


def standalone_metrics(sig, sim, cal, dgs2) -> dict:
    m = F.eval_mask(sig, sim)
    s = sim.loc[m]
    y22 = (s.index >= "2022-01-01") & (s.index <= "2022-12-31")
    ho = (s.index >= K.HOLDOUT[0]) & (s.index <= K.HOLDOUT[1])
    return {"window": [str(s.index[0].date()), str(s.index[-1].date())], "n": int(len(s)),
            "sharpe_gross": F.sharpe(s["gross"]), "sharpe_1x": F.sharpe(s["net1"]), "sharpe_2x": F.sharpe(s["net2"]),
            "sharpe_tlt_1x": F.sharpe(s["tlt1"]), "sharpe_uup_1x": F.sharpe(s["uup1"]),
            "sharpe_2022_1x": F.sharpe(s.loc[y22, "net1"]), "sharpe_rest_1x": F.sharpe(s.loc[~y22, "net1"]),
            "sharpe_holdout_2021_2024_1x": F.sharpe(s.loc[ho, "net1"]),
            "corr_C_DGS2_tminus2": K.corr_c_dgs2(sig["consensus"], dgs2, s.index, cal),
            "turnover_ann": float(s["turn"].mean() * 252), "maxdd_1x": F.max_dd(s["net1"]),
            "ann_mean_1x": float(s["net1"].mean() * 252), "vol_1x": float(s["net1"].std() * math.sqrt(252)),
            "cost_drag_ann": float(s["cost"].mean() * 252)}, s


def engine_runs(E, w_dec: pd.DataFrame, period: str = "IS"):
    ohlc = E.load_ohlc(["TLT", "UUP"], period)
    rf = E.load_rf(period)
    zero = pd.Series(0.0, index=rf.index)
    out = {}
    for name, rate in [("rf0", zero), ("tbill", rf)]:
        for mult in (1.0, 2.0):
            net, gross, turn, held, cost = E.simulate(w_dec, ohlc, rate, exec="next_open", cost_mult=mult, cost_bps=COST)
            out[(name, mult)] = dict(net=net, gross=gross, turn=turn, held=held, cost=cost)
    for leg in ("TLT", "UUP"):
        net, gross, turn, held, cost = E.simulate(w_dec[[leg]], ohlc, zero, exec="next_open", cost_bps=COST)
        out[("leg", leg)] = dict(net=net, gross=gross, turn=turn, held=held, cost=cost)
        net, gross, turn, held, cost = E.simulate(w_dec[[leg]], ohlc, rf, exec="next_open", cost_bps=COST)
        out[("leg_tbill", leg)] = dict(net=net, gross=gross, turn=turn, held=held, cost=cost)
    return out, rf


def engine_metrics(E, runs, rf, a: str, b: str) -> dict:
    sl = slice(pd.Timestamp(a), pd.Timestamp(b))
    r0, r2, rt = runs[("rf0", 1.0)], runs[("rf0", 2.0)], runs[("tbill", 1.0)]
    rf_ = rf.reindex(rt["net"].index).ffill().fillna(0.0)
    held = r0["held"].loc[sl]
    borrow = (held.clip(upper=0).abs() * (E.C.SHORT_BORROW_BPS_PER_YEAR / 1e4 / 252)).sum(axis=1)
    ex = (rt["net"] - rf_).loc[sl]
    ex2 = (runs[("tbill", 2.0)]["net"] - rf_).loc[sl]
    gross_ex = (rt["gross"] - rf_).loc[sl]
    y22 = (ex.index >= "2022-01-01") & (ex.index <= "2022-12-31")
    ps = E.perf_stats(rt["net"].loc[sl], ex, rt["turn"].loc[sl])
    legs0 = {leg: F.sharpe(runs[("leg", leg)]["net"].loc[sl]) for leg in ("TLT", "UUP")}
    legs_ex = {leg: F.sharpe((runs[("leg_tbill", leg)]["net"] - rf_).loc[sl]) for leg in ("TLT", "UUP")}
    n0 = r0["net"].loc[sl]
    return {
        "window": [str(n0.index[0].date()), str(n0.index[-1].date())], "n": int(len(n0)),
        "their_definition_rf0": {
            "sharpe_gross": F.sharpe(r0["gross"].loc[sl]), "sharpe_1x": F.sharpe(n0), "sharpe_2x": F.sharpe(r2["net"].loc[sl]),
            "sharpe_1x_ex_borrow": F.sharpe(n0 + borrow),
            "sharpe_tlt_1x": legs0["TLT"], "sharpe_uup_1x": legs0["UUP"],
            "sharpe_2022_1x": F.sharpe(n0[y22]), "sharpe_rest_1x": F.sharpe(n0[~y22]),
            "maxdd_1x": F.max_dd(n0), "ann_mean_1x": float(n0.mean() * 252)},
        "ours_excess_over_tbill": {
            "sharpe_gross": F.sharpe(gross_ex), "sharpe_1x": F.sharpe(ex), "sharpe_2x": F.sharpe(ex2),
            "sharpe_tlt_1x": legs_ex["TLT"], "sharpe_uup_1x": legs_ex["UUP"],
            "sharpe_2022_1x": F.sharpe(ex[y22]), "sharpe_rest_1x": F.sharpe(ex[~y22]),
            "perf_stats": ps},
        "turnover_ann_engine": float(r0["turn"].loc[sl].sum() / (len(n0) / 252)),
        "trading_cost_drag_ann": float((r0["cost"].loc[sl] - borrow).mean() * 252),
        "borrow_drag_ann": float(borrow.mean() * 252),
        "mean_net_weight_sum": float(held.sum(axis=1).mean()),
        "tbill_on_net_weight_drag_ann": float((-(held.sum(axis=1)) * rf_.loc[sl]).mean() * 252),
    }


def main():
    E = K.engine()
    out = K.HERE / "out"
    out.mkdir(exist_ok=True)
    scores_is = F.load_kept_scores(K.THEIR_PROC / "speech_scores.csv", end=K.IS_END)
    scores_all = F.load_kept_scores(K.THEIR_PROC / "speech_scores.csv")
    fomc = K.their_fomc()
    dgs2 = K.our_dgs2("IS")
    res = {}

    # ---- A. stand-alone simulator, our data
    cal, sig, r_t, r_u = build_our_signal("IS", fomc, scores_is)
    sim = F.sim_open_to_open(sig, r_t, r_u)
    res["standalone_our_data"], s_main = standalone_metrics(sig, sim, cal, dgs2)

    # compare to the run on their data
    sig_theirs = pd.read_parquet(out / "signal_their_data_session_index.parquet")
    res["our_vs_their_data_signal_max_abs_diff"] = {
        k: float((sig[k] - sig_theirs[k].reindex(sig.index)).abs().max()) for k in ["consensus", "z", "vol", "w_TLT", "w_UUP"]}

    # ---- B. sensitivities (descriptive only, stand-alone simulator, our data)
    sens = {}
    fomc_decisions = fomc[~fomc.isin(pd.to_datetime(NON_DECISION))]
    # dates not on the pre-announced calendar (de-risking at that open would use hindsight)
    unscheduled = pd.to_datetime(["2019-10-11", "2020-03-03", "2020-03-15", "2020-03-19", "2020-03-23", "2020-03-31"])
    fomc_scheduled = fomc[~fomc.isin(unscheduled)]
    for label, kw in [("vol_lagged_one_more_session", dict(lag_vol=1)),
                      ("signal_lagged_one_more_session", dict(lag_signal=1)),
                      ("fomc_policy_decisions_only", dict(fomc=fomc_decisions)),
                      ("fomc_preannounced_dates_only", dict(fomc=fomc_scheduled)),
                      ("no_fomc_derisk", dict(fomc=pd.Series([], dtype="datetime64[ns]"))),
                      ("no_trade_band_off", dict(spec=F.Spec(no_trade_band=0.0)))]:
        kw = dict(kw)
        f = kw.pop("fomc", fomc)
        c2, sg2, rt2, ru2 = build_our_signal("IS", f, scores_is, **kw)
        sp = kw.get("spec", F.Spec())
        sm2 = F.sim_open_to_open(sg2, rt2, ru2, sp)
        mt, _ = standalone_metrics(sg2, sm2, c2, dgs2)
        sens[label] = {k: mt[k] for k in ["sharpe_gross", "sharpe_1x", "sharpe_2x", "sharpe_2022_1x", "sharpe_rest_1x",
                                          "sharpe_holdout_2021_2024_1x", "turnover_ann"]}
    res["sensitivities_standalone"] = sens

    # ---- C. our engine. w_dec[d] = weights entered at the open of the session after d.
    w_sess = sig[["w_TLT", "w_UUP"]].rename(columns={"w_TLT": "TLT", "w_UUP": "UUP"})
    w_dec = w_sess.shift(-1)
    runs, rf = engine_runs(E, w_dec, "IS")
    res["engine"] = {k: engine_metrics(E, runs, rf, *v) for k, v in WINDOWS.items()}

    # engine attribution check: held weight on day t must equal the session weight entered at open t
    held = runs[("rf0", 1.0)]["held"]
    res["engine_held_equals_session_weight_max_abs"] = float((held - w_sess.reindex(held.index).fillna(0)).loc["2011-12-30":].abs().max().max())

    # ---- D. yearly Sharpe table
    rf0n = runs[("rf0", 1.0)]["net"].loc["2011-12-30":K.IS_END]
    rfe = (runs[("tbill", 1.0)]["net"] - rf.reindex(runs[("tbill", 1.0)]["net"].index).ffill()).loc["2011-12-30":K.IS_END]
    yt = pd.DataFrame({"standalone_gross": F.yearly_sharpe(s_main["gross"]), "standalone_1x": F.yearly_sharpe(s_main["net1"]),
                       "engine_rf0_1x": F.yearly_sharpe(rf0n), "engine_excess_1x": F.yearly_sharpe(rfe),
                       "standalone_ret_1x": s_main["net1"].groupby(s_main.index.year).sum(),
                       "mean_w_TLT": sig["w_TLT"].loc[s_main.index].groupby(s_main.index.year).mean(),
                       "mean_z": sig["z"].loc[s_main.index].groupby(s_main.index.year).mean()})
    yt.index.name = "year"
    yt.to_csv(out / "step3_yearly.csv")
    print(yt.round(3).to_string())

    # ---- E. signal.parquet: decision-date index (engine convention), through the end of their corpus
    # their fomc_dates.csv stops at the IS cut; add the two scheduled 2024 decisions after it (Fed calendar)
    fomc_ext = pd.concat([fomc, pd.Series(pd.to_datetime(["2024-11-07", "2024-12-18"]))], ignore_index=True)
    calF, sigF, _, _ = build_our_signal("FWD", fomc_ext, scores_all)
    corpus_end = pd.Timestamp("2024-12-31")
    # IS values must not depend on whether later data were loaded (causality check)
    chk = sigF.loc[:K.IS_END, ["consensus", "z", "w_TLT", "w_UUP"]]
    base = build_our_signal("FWD", fomc, scores_is)[1].loc[:K.IS_END, ["consensus", "z", "w_TLT", "w_UUP"]]
    res["signal_causality_check_max_abs"] = float((chk - base).abs().max().max())
    dec = sigF[["consensus", "z", "w_TLT", "w_UUP"]].shift(-1)        # value for the session after d, stored at d
    dec = dec.loc[(dec.index >= pd.Timestamp(K.MARKET_START)) & (dec.index <= corpus_end)]
    dec.index.name = "date"
    dec.to_parquet(K.HERE / "signal.parquet")
    full = sigF.copy()
    full.index.name = "session"
    full["decision_date"] = full.index.to_series().shift(1)
    full.loc[full.index <= corpus_end + pd.Timedelta(days=7)].to_parquet(K.HERE / "signal_session_full.parquet")
    # stale-corpus artifact if someone extends past the last speech without new documents
    stale = sigF.loc["2025-01-02":, "z"]
    res["stale_corpus_warning"] = {"z_mean_2025_onwards_without_new_speeches": float(stale.mean()),
                                   "share_days_z_gt_0": float((stale > 0).mean()),
                                   "mean_w_TLT_2025_onwards": float(sigF.loc["2025-01-02":, "w_TLT"].mean())}
    res["signal_file"] = {"rows": int(len(dec)), "first": str(dec.index[0].date()), "last": str(dec.index[-1].date()),
                          "first_nonzero_weight_decision_date": str(dec.index[(dec["w_TLT"].abs() > 0).to_numpy()][0].date())}

    (out / "step3_results.json").write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
