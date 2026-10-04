"""Step 5: collect steps 1-4 into results.json (headline table) and add monthly-sampled Sharpe checks."""
from __future__ import annotations

import json
import math

import pandas as pd

import common as K
import fedsignal as F
from step3_our_data_engine import COST, build_our_signal


def monthly_sharpe(r: pd.Series) -> float:
    m = r.dropna().resample("ME").sum()
    return float(m.mean() / m.std() * math.sqrt(12))


def main():
    out = K.HERE / "out"
    s1 = pd.read_csv(out / "step1_their_data_vs_published.csv").set_index("metric")
    s2 = json.loads((out / "step2_data_check.json").read_text())
    s3 = json.loads((out / "step3_results.json").read_text())
    s4 = json.loads((out / "step4_bridge.json").read_text())
    pub = json.loads((K.THEIR_OUT / "is_summary.json").read_text())

    E = K.engine()
    sc = F.load_kept_scores(K.THEIR_PROC / "speech_scores.csv", end=K.IS_END)
    cal, sig, r_t, r_u = build_our_signal("IS", K.their_fomc(), sc)
    sim = F.sim_open_to_open(sig, r_t, r_u)
    m = F.eval_mask(sig, sim)
    w_dec = sig[["w_TLT", "w_UUP"]].rename(columns={"w_TLT": "TLT", "w_UUP": "UUP"}).shift(-1)
    ohlc = E.load_ohlc(["TLT", "UUP"], "IS")
    rf = E.load_rf("IS")
    netT, *_ = E.simulate(w_dec, ohlc, rf, exec="next_open", cost_bps=COST)
    ex = (netT - rf.reindex(netT.index).ffill()).loc["2011-12-30":K.IS_END]
    monthly = {"standalone_1x_monthly_sharpe": monthly_sharpe(sim.loc[m, "net1"]),
               "engine_excess_1x_monthly_sharpe": monthly_sharpe(ex),
               "standalone_1x_monthly_sharpe_holdout": monthly_sharpe(sim.loc[m, "net1"].loc[K.HOLDOUT[0]:]),
               "engine_excess_1x_monthly_sharpe_holdout": monthly_sharpe(ex.loc[K.HOLDOUT[0]:])}

    sa = s3["standalone_our_data"]
    eng = s3["engine"]["IS_2012_2024"]
    ho = s3["engine"]["holdout_2021_2024"]
    keys = ["sharpe_gross", "sharpe_1x", "sharpe_2x", "sharpe_tlt_1x", "sharpe_uup_1x", "sharpe_2022_1x", "sharpe_rest_1x"]
    head = []
    for k in keys:
        head.append({"metric": k, "published": pub.get(k), "ours_their_data": float(s1.loc[k, "ours_on_their_data"]),
                     "ours_our_data_standalone": sa[k], "engine_rf0": eng["their_definition_rf0"][k],
                     "engine_excess_tbill": eng["ours_excess_over_tbill"][k]})
    head.append({"metric": "corr_C_DGS2_tminus2", "published": pub["corr_C_DGS2_tminus2"],
                 "ours_their_data": float(s1.loc["corr_C_DGS2_tminus2", "ours_on_their_data"]),
                 "ours_our_data_standalone": sa["corr_C_DGS2_tminus2"], "engine_rf0": None, "engine_excess_tbill": None})
    head.append({"metric": "turnover_ann", "published": pub["turnover_ann"],
                 "ours_their_data": float(s1.loc["turnover_ann", "ours_on_their_data"]),
                 "ours_our_data_standalone": sa["turnover_ann"], "engine_rf0": eng["turnover_ann_engine"],
                 "engine_excess_tbill": eng["turnover_ann_engine"]})
    head.append({"metric": "maxdd_1x", "published": -0.32881453674732,
                 "ours_their_data": float(s1.loc["maxdd_1x", "ours_on_their_data"]),
                 "ours_our_data_standalone": sa["maxdd_1x"], "engine_rf0": eng["their_definition_rf0"]["maxdd_1x"],
                 "engine_excess_tbill": eng["ours_excess_over_tbill"]["perf_stats"]["max_drawdown"]})
    head.append({"metric": "holdout_2021_2024_sharpe_1x", "published": None,
                 "ours_their_data": float(s1.loc["sharpe_holdout_2021_2024_1x", "ours_on_their_data"]),
                 "ours_our_data_standalone": sa["sharpe_holdout_2021_2024_1x"],
                 "engine_rf0": ho["their_definition_rf0"]["sharpe_1x"],
                 "engine_excess_tbill": ho["ours_excess_over_tbill"]["sharpe_1x"]})
    head.append({"metric": "holdout_2021_2024_sharpe_1x_ex2022", "published": None, "ours_their_data": None,
                 "ours_our_data_standalone": None, "engine_rf0": ho["their_definition_rf0"]["sharpe_rest_1x"],
                 "engine_excess_tbill": ho["ours_excess_over_tbill"]["sharpe_rest_1x"]})
    tab = pd.DataFrame(head)
    tab.to_csv(out / "headline_table.csv", index=False)
    print(tab.round(4).to_string(index=False))
    print(json.dumps(monthly, indent=1))

    res = {"headline": head, "monthly_sampled": monthly, "bridge": s4["bridge"],
           "engine_crosscheck": s4["engine_crosscheck_max_abs"], "data_check": s2,
           "signal_match_our_vs_their_data": s3["our_vs_their_data_signal_max_abs_diff"],
           "sensitivities": s3["sensitivities_standalone"], "stale_corpus_warning": s3["stale_corpus_warning"],
           "signal_file": s3["signal_file"], "engine_windows": s3["engine"],
           "oos_2024_10_03_2026_10_02": "not evaluable from their corpus (last kept speech 2024-12-03); needs 2025-2026 "
                                        "Board speeches scored with the frozen lexicon"}
    (K.HERE / "results.json").write_text(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
