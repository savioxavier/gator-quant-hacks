"""Step 1: rebuild their in-sample run from their own processed CSVs and diff it day by day
against their published outputs/equity_is.csv and is_summary.json."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import common as K
import fedsignal as F


def run(z_clock_start: str | None = None):
    px = K.their_markets()
    cal = px.index.sort_values()
    sc = F.load_kept_scores(K.THEIR_PROC / "speech_scores.csv", end=K.IS_END)
    r_t, r_u = px["TLT_ret"], px["UUP_ret"]
    sig = F.build(cal, sc, K.their_fomc()[lambda s: s <= K.IS_END], r_t, r_u, z_clock_start=z_clock_start)
    sim = F.sim_open_to_open(sig, r_t, r_u)
    m = F.eval_mask(sig, sim)
    return px, cal, sc, sig, sim, m


def summary(cal, sc, sig, sim, m, dgs2) -> dict:
    s = sim.loc[m]
    y22 = (s.index >= "2022-01-01") & (s.index <= "2022-12-31")
    ho = (s.index >= K.HOLDOUT[0]) & (s.index <= K.HOLDOUT[1])
    return {
        "first_z": str(s.index[0].date()), "last_ret": str(s.index[-1].date()), "n_is_days": int(len(s)),
        "n_docs_kept": int(len(sc)), "n_fomc": int(sig["fomc_day"].sum()),
        "sharpe_gross": F.sharpe(s["gross"]), "sharpe_1x": F.sharpe(s["net1"]), "sharpe_2x": F.sharpe(s["net2"]),
        "sharpe_tlt_1x": F.sharpe(s["tlt1"]), "sharpe_uup_1x": F.sharpe(s["uup1"]),
        "sharpe_2022_1x": F.sharpe(s.loc[y22, "net1"]), "sharpe_rest_1x": F.sharpe(s.loc[~y22, "net1"]),
        "sharpe_holdout_2021_2024_1x": F.sharpe(s.loc[ho, "net1"]),
        "corr_C_DGS2_tminus2": K.corr_c_dgs2(sig["consensus"], dgs2, s.index, cal),
        "turnover_ann": float(s["turn"].mean() * 252),
        "maxdd_1x": F.max_dd(s["net1"]), "ann_mean_1x": float(s["net1"].mean() * 252),
        "vol_1x": float(s["net1"].std() * np.sqrt(252)),
    }


def main():
    out = K.HERE / "out"
    out.mkdir(exist_ok=True)
    px, cal, sc, sig, sim, m = run()
    mine = summary(cal, sc, sig, sim, m, K.their_dgs2())
    theirs = json.loads((K.THEIR_OUT / "is_summary.json").read_text())
    rows = []
    for k, v in mine.items():
        t = theirs.get(k)
        rows.append({"metric": k, "ours_on_their_data": v, "their_published": t,
                     "abs_diff": (abs(v - t) if isinstance(v, float) and isinstance(t, (int, float)) else None)})
    tab = pd.DataFrame(rows)
    print(tab.to_string(index=False))

    # day-by-day diff against their equity file
    eq = pd.read_csv(K.THEIR_OUT / "equity_is.csv", index_col=0, parse_dates=True)
    s = sim.loc[m]
    assert s.index.equals(eq.index), "evaluation calendars differ"
    pairs = {"C": sig["consensus"], "z": sig["z"], "pos": sig["pos"], "vol_mix": sig["vol"],
             "w_tlt": sig["w_TLT"], "w_uup": sig["w_UUP"], "r_gross": s["gross"], "r_1x": s["net1"],
             "r_2x": s["net2"], "fomc_derisk": sig["fomc_day"].astype(float)}
    diff = {k: float((v.reindex(eq.index).astype(float) - eq[k].astype(float)).abs().max()) for k, v in pairs.items()}
    print("max |ours - their equity_is.csv| per column:", json.dumps(diff, indent=1))

    # trial 1 (z clock from the first market session, i.e. 2010 zero padding) as a second check
    _, cal1, sc1, sig1, sim1, m1 = run(z_clock_start=K.MARKET_START)
    t1 = summary(cal1, sc1, sig1, sim1, m1, K.their_dgs2())
    log = pd.read_csv(K.THEIRS / "trials" / "log.csv")
    t1_pub = log.iloc[0].to_dict()
    t1_cmp = {k: (t1[k], t1_pub.get(k)) for k in ["sharpe_gross", "sharpe_1x", "sharpe_2x", "sharpe_tlt_1x",
                                                    "sharpe_uup_1x", "sharpe_2022_1x", "sharpe_rest_1x",
                                                    "corr_C_DGS2_tminus2", "turnover_ann", "n_is_days", "first_z"]}
    print("trial-1 (z clock 2010-01-04) ours vs their log row 1:", json.dumps(t1_cmp, indent=1, default=str))

    tab.to_csv(out / "step1_their_data_vs_published.csv", index=False)
    (out / "step1_daily_maxdiff.json").write_text(json.dumps({"max_abs_diff_vs_equity_is": diff,
                                                              "trial1_ours_vs_log": t1_cmp}, indent=2, default=str))
    sig.to_parquet(out / "signal_their_data_session_index.parquet")
    return mine


if __name__ == "__main__":
    main()
