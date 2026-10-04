"""Descriptive diagnostics, NOT part of PREDECLARED.md and not used for any verdict:
(a) OOS sub-periods; (b) speech-volume decomposition of the consensus; (c) ETF legs under the futures timing,
to separate the timing effect from the instrument effect in the futures result."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from scipy.signal import lfilter

import fa_lib as L

OUT = L.HERE


def main():
    B = L.build_all()
    sig, ohlc, rf, cal = B["sig"], B["ohlc"], B["rf"], B["cal"]
    daily = pd.read_parquet(OUT / "daily_returns.parquet")
    res = {}

    # (a) OOS sub-periods
    subs = {"2024Q4 (10-03..12-31)": ("2024-10-03", "2024-12-31"), "2025": ("2025-01-01", "2025-12-31"),
            "2026 (to 10-02)": ("2026-01-01", "2026-10-02"), "OOS": L.WIN["OOS"]}
    tlt_tr = ohlc["close"]["TLT"]
    rows = []
    for lab, (a, b) in subs.items():
        row = {"period": lab}
        for c in ("tone_ex_net1x", "tone_rf0_net1x", "ctl_dgs2_ex_net1x", "tone_orth_ex_net1x", "fut_F_ZN_ex_net1x", "fut_F_ZB_ex_net1x"):
            r = daily[c].loc[a:b]
            row[f"sharpe_{c}"] = L.sharpe(r)
            row[f"ret_{c}"] = float((1 + r).prod() - 1)
        s = sig.loc[a:b]
        px = tlt_tr.loc[:b]
        p0 = tlt_tr.loc[:pd.Timestamp(a) - pd.Timedelta(days=1)].iloc[-1]
        row.update({"TLT_total_return": float(px.iloc[-1] / p0 - 1), "mean_w_TLT": float(s.tone_TLT.mean()),
                    "mean_w_UUP": float(s.tone_UUP.mean()), "mean_z_tone": float(s.z_tone.mean()),
                    "DGS2_change_bp": float((sig.dgs2.loc[:b].iloc[-1] - sig.dgs2.loc[:a].iloc[-2]) * 100)})
        rows.append(row)
    sub = pd.DataFrame(rows)
    sub.to_csv(OUT / "x1_oos_subperiods.csv", index=False)

    # (b) speech volume: consensus = decayed SUM of scores, so more speeches push C further from 0
    sc = B["scores"]
    pos = L.F.first_session_after(cal, sc["speech_date"])
    ok = pos < len(cal)
    cnt = np.zeros(len(cal))
    np.add.at(cnt, pos[ok], 1.0)
    N = pd.Series(lfilter([1.0], [1.0, -L.LAM], cnt), index=cal)
    C = sig["C_tone"]
    mean_tone = (C / N).where(N > 0.5)
    vrows = []
    for wn in ("IS", "HOLDOUT", "OOS"):
        a, b = L.WIN[wn]
        vrows.append({"window": wn, "mean_C": float(C.loc[a:b].mean()), "mean_decayed_count_N": float(N.loc[a:b].mean()),
                      "mean_C_over_N": float(mean_tone.loc[a:b].mean()),
                      "corr_C_N": float(C.loc[a:b].corr(N.loc[a:b])),
                      "kept_docs_per_year": float(((sc["speech_date"] >= a) & (sc["speech_date"] <= b)).sum() / ((pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25)),
                      "mean_s_kept": float(sc.loc[(sc["speech_date"] >= a) & (sc["speech_date"] <= b), "s"].mean()),
                      "mean_z_tone": float(sig["z_tone"].loc[a:b].mean())})
    # counterfactual for the OOS signal level: C rescaled to the IS average speech count
    a, b = L.WIN["OOS"]
    n_is = float(N.loc[L.WIN["IS"][0]:L.IS_END].mean())
    z_hist = L.F.expanding_z(C, L.CLOCK, L.SPEC.z_min_obs)
    m_is = C.loc[L.CLOCK:L.IS_END]
    c_scaled = (mean_tone * n_is).loc[a:b]
    res["volume_counterfactual_OOS"] = {
        "mean_z_actual_OOS": float(z_hist.loc[a:b].mean()),
        "mean_z_actual_C_with_IS_moments": float(((C.loc[a:b] - m_is.mean()) / m_is.std()).mean()),
        "mean_z_if_C_used_IS_avg_count_with_IS_moments": float(((c_scaled - m_is.mean()) / m_is.std()).mean()),
        "note": "C/N x IS-mean N, standardised with IS mean/std of C: the OOS level the frozen z would have had at IS speech volume; compare with mean_z_actual_C_with_IS_moments (same standardisation)"}
    vol_tab = pd.DataFrame(vrows)
    vol_tab.to_csv(OUT / "x2_speech_volume.csv", index=False)
    yr = sc.groupby(sc["speech_date"].dt.year).agg(kept_docs=("s", "size"), mean_s=("s", "mean"))
    yr.to_csv(OUT / "x2_kept_docs_by_year.csv")

    # (c) ETF legs under the futures timing (decision at close d with z of session d, fill at close d+1)
    rfc = rf.reindex(cal).ffill().fillna(0.0)
    close = ohlc["close"].reindex(cal)
    r_ex = close.pct_change(fill_method=None).sub(rfc, axis=0)
    mix = -L.SPEC.w_tlt * r_ex["TLT"] + L.SPEC.w_uup * r_ex["UUP"]
    a_ = math.sqrt(252)
    vol_dec = (0.5 * mix.rolling(20, min_periods=20).std() * a_ + 0.5 * mix.rolling(60, min_periods=60).std() * a_).clip(lower=0.04)
    w = L.size(sig["z_tone"].shift(2), vol_dec.shift(2), sig["fomc_day"], sig["fomc_next"])
    w_hold = pd.DataFrame({"TLT": w["w_TLT"], "UUP": w["w_UUP"]}, index=cal)
    run_nc = L.run_engine(w_hold, ohlc, rf, L.COST_ETF, exec="next_close", legs=False)
    trows = []
    for lab, ser in (("ETF next_open (frozen rule)", daily["tone_ex_net1x"]), ("ETF next_close, futures timing", run_nc["ex_net1x"]),
                     ("F_ZB next_close", daily["fut_F_ZB_ex_net1x"]), ("F_ZN next_close", daily["fut_F_ZN_ex_net1x"])):
        row = {"variant": lab}
        for wn in ("IS", "HOLDOUT", "OOS", "FULL"):
            row[f"sharpe_ex_1x_{wn}"] = L.sharpe(L.sl(ser, *L.WIN[wn]))
        r = L.sl(ser, *L.WIN["IS"])
        row["sharpe_ex_1x_IS_ex2022"] = L.sharpe(r[(r.index < "2022-01-01") | (r.index > "2022-12-31")])
        trows.append(row)
    tim = pd.DataFrame(trows)
    tim.to_csv(OUT / "x3_timing_vs_instrument.csv", index=False)

    (OUT / "extras.json").write_text(json.dumps(res, indent=2))
    pd.set_option("display.width", 250, "display.max_columns", 40)
    print(sub.round(3).T.to_string())
    print(vol_tab.round(3).to_string())
    print(yr.round(3).to_string())
    print(json.dumps(res, indent=1))
    print(tim.round(3).to_string())


if __name__ == "__main__":
    main()
