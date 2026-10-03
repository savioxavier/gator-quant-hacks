"""Step 2: check their market data (markets.csv), DGS2 and FOMC dates against our caches."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import common as K
import fedsignal as F

# Policy decisions (scheduled meetings plus the two 2020 emergency cuts) are every date in their file
# except these monetary-policy press releases that carried no rate/statement decision of a meeting.
NON_DECISION = ["2012-10-23", "2019-10-11", "2020-03-19", "2020-03-23", "2020-03-31", "2020-08-27"]


def main():
    out = K.HERE / "out"
    out.mkdir(exist_ok=True)
    px = K.their_markets()
    cal_ours, o, c = K.our_opens("IS")
    res: dict = {}

    # calendar
    a, b = px.index, cal_ours[(cal_ours >= px.index.min()) & (cal_ours <= px.index.max())]
    res["calendar"] = {"their_n": int(len(a)), "our_n": int(len(b)),
                       "only_theirs": [str(d.date()) for d in a.difference(b)],
                       "only_ours": [str(d.date()) for d in b.difference(a)]}

    for t in ["TLT", "UUP"]:
        r = {}
        # internal consistency of their adjusted open
        implied = px[f"{t}_open"] * px[f"{t}_adjclose"] / px[f"{t}_close"]
        r["their_adjopen_vs_open_x_adjfactor_max_rel"] = float((px[f"{t}_adjopen"] / implied - 1).abs().max())
        # their returns are built from adjusted opens
        rr = K.open_to_open(px[f"{t}_adjopen"])
        r["their_ret_equals_adjopen_o2o_max_abs"] = float((rr - px[f"{t}_ret"]).abs().max())
        # adjusted vs unadjusted: distribution drag
        adj_factor = px[f"{t}_adjclose"] / px[f"{t}_close"]
        r["their_adj_factor_first_last"] = [float(adj_factor.iloc[0]), float(adj_factor.iloc[-1])]
        unadj = K.open_to_open(px[f"{t}_open"])
        r["ann_total_minus_price_return_o2o"] = float((rr - unadj).mean() * 252)
        # against our cache (yfinance auto_adjust=True OHLC)
        j = pd.concat([px[f"{t}_adjclose"], c[t], px[f"{t}_adjopen"], o[t]], axis=1, keys=["tc", "oc", "to", "oo"]).dropna()
        ratio_c = j["tc"] / j["oc"]
        ratio_o = j["to"] / j["oo"]
        r["n_common"] = int(len(j))
        r["close_ratio_theirs_over_ours_median"] = float(ratio_c.median())
        r["close_ratio_max_dev_bp"] = float(((ratio_c / ratio_c.median()) - 1).abs().max() * 1e4)
        r["open_ratio_max_dev_bp"] = float(((ratio_o / ratio_o.median()) - 1).abs().max() * 1e4)
        r["unadjusted_close_vs_ours_last_day"] = [float(px[f"{t}_close"].iloc[-1]), float(c[t].loc[px.index[-1]])]
        ro = K.open_to_open(o[t]).reindex(px.index)
        d = (px[f"{t}_ret"] - ro).dropna()
        r["o2o_ret_diff_max_abs_bp"] = float(d.abs().max() * 1e4)
        r["o2o_ret_diff_n_gt_0p5bp"] = int((d.abs() > 0.5e-4).sum())
        r["o2o_ret_diff_mean_bp_per_year"] = float(d.mean() * 252 * 1e4)
        r["o2o_ret_corr"] = float(px[f"{t}_ret"].corr(ro))
        big = d.abs().sort_values(ascending=False).head(5)
        r["largest_diffs_bp"] = {str(k.date()): float(v * 1e4) for k, v in big.items()}
        res[t] = r

    # what a strategy run on UNADJUSTED opens would show (the construction error HYPOTHESIS.md warns about)
    sc = F.load_kept_scores(K.THEIR_PROC / "speech_scores.csv", end=K.IS_END)
    fomc = K.their_fomc()
    cal = px.index
    for label, rt, ru in [("adjusted_opens", px["TLT_ret"], px["UUP_ret"]),
                          ("UNADJUSTED_opens", K.open_to_open(px["TLT_open"]), K.open_to_open(px["UUP_open"]))]:
        sig = F.build(cal, sc, fomc, rt, ru)
        sim = F.sim_open_to_open(sig, rt, ru)
        m = F.eval_mask(sig, sim)
        res.setdefault("what_if_price_basis", {})[label] = {"sharpe_1x": F.sharpe(sim.loc[m, "net1"]),
                                                           "sharpe_tlt_1x": F.sharpe(sim.loc[m, "tlt1"])}

    # DGS2
    d_t = K.their_dgs2()
    d_o = K.our_dgs2("IS")
    j = pd.concat([d_t, d_o], axis=1, keys=["theirs", "ours"]).dropna()
    res["DGS2"] = {"their_range": [str(d_t.index.min().date()), str(d_t.index.max().date())], "n_common": int(len(j)),
                   "max_abs_diff_pct_pts": float((j["theirs"] - j["ours"]).abs().max()),
                   "n_diff_gt_0": int(((j["theirs"] - j["ours"]).abs() > 1e-9).sum()),
                   "their_nan": int(d_t.isna().sum())}

    # FOMC
    fd = pd.to_datetime(fomc)
    res["FOMC"] = {"n_dates": int(len(fd)), "per_year": {int(k): int(v) for k, v in fd.dt.year.value_counts().sort_index().items()},
                   "non_decision_press_release_dates_in_file": NON_DECISION,
                   "non_session_dates": [str(x.date()) for x in fd if x not in set(cal)]}

    # speech file
    allsc = pd.read_csv(K.THEIR_PROC / "speech_scores.csv", parse_dates=["speech_date"])
    kept = allsc[allsc["kept"].astype(bool)]
    res["speeches"] = {"n_docs": int(len(allsc)), "n_kept": int(len(kept)),
                       "n_kept_is": int((kept["speech_date"] <= K.IS_END).sum()),
                       "n_kept_after_is": int((kept["speech_date"] > K.IS_END).sum()),
                       "last_kept_date": str(kept["speech_date"].max().date()),
                       "last_doc_date": str(allsc["speech_date"].max().date()),
                       "HD_median_all_docs": float(allsc["HD"].median()),
                       "s_recomputed_from_H_D_max_abs_diff": float((((kept["H"] - kept["D"]) / (kept["HD"] + 1.0)) - kept["s"]).abs().max()),
                       "kept_mean_s_by_year": {int(k): round(float(v), 3) for k, v in kept.groupby(kept["speech_date"].dt.year)["s"].mean().items()},
                       "kept_n_by_year": {int(k): int(v) for k, v in kept.groupby(kept["speech_date"].dt.year).size().items()},
                       "same_date_multi_docs": int(kept["speech_date"].duplicated().sum()),
                       "weekend_dated_kept": int((kept["speech_date"].dt.dayofweek >= 5).sum())}

    (out / "step2_data_check.json").write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
