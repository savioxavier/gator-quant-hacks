"""Step 4: bridge from the stand-alone open-to-open Sharpe (their accounting) to our engine's numbers,
one accounting change at a time, on identical weights and data."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import common as K
import fedsignal as F
from step3_our_data_engine import COST, build_our_signal


def main():
    E = K.engine()
    out = K.HERE / "out"
    sc = F.load_kept_scores(K.THEIR_PROC / "speech_scores.csv", end=K.IS_END)
    cal, sig, r_t, r_u = build_our_signal("IS", K.their_fomc(), sc)
    w = sig[["w_TLT", "w_UUP"]].rename(columns={"w_TLT": "TLT", "w_UUP": "UUP"})
    ohlc = E.load_ohlc(["TLT", "UUP"], "IS")
    o, c = ohlc["open"].loc[cal], ohlc["close"].loc[cal]
    rf = E.load_rf("IS").reindex(cal).ffill().fillna(0.0)
    r_oo = pd.DataFrame({"TLT": r_t, "UUP": r_u})
    r_co = (o / c.shift(1) - 1).fillna(0.0)
    r_oc = (c / o - 1).fillna(0.0)
    bps = pd.Series(COST) / 1e4

    a, b = "2011-12-30", K.IS_END
    rows = []

    def add(label, r, note):
        r = r.loc[a:b].dropna()
        rows.append({"step": label, "n": len(r), "ann_mean": r.mean() * 252, "ann_vol": r.std() * np.sqrt(252),
                     "sharpe": F.sharpe(r), "note": note})

    # 0. stand-alone, their accounting: w[t] * open(t)->open(t+1), sample ends 2024-10-01
    g0 = (w * r_oo).sum(axis=1, min_count=2)
    add("0 standalone gross (open->open, rf=0)", g0, "their definition; reproduces 0.2547")
    # 1. same P&L re-booked on the engine's day boundaries: overnight leg of w[t-1] + intraday leg of w[t]
    g1 = (w.shift(1).fillna(0) * r_co).sum(axis=1) + (w * r_oc).sum(axis=1)
    add("1 re-booked by day: w[t-1]*r_co(t) + w[t]*r_oc(t)", g1, "additive split, adds 2024-10-02")
    # 2. engine compounding of overnight into intraday
    on = (w.shift(1).fillna(0) * r_co).sum(axis=1)
    g2 = on + (1 + on) * (w * r_oc).sum(axis=1)
    add("2 + engine compounding (= engine gross, rf=0)", g2, "")
    # 3. trading costs on |dw| (their cost model) then on drift-adjusted trades (engine)
    dw = w.diff().fillna(w).abs()
    c_their = (dw * bps).sum(axis=1)
    add("3a gross - their |dw| costs", g2 - c_their, "")
    drifted = w.shift(1).fillna(0).mul(1 + r_co).div((1 + on).replace(0, np.nan), axis=0).fillna(0.0)
    c_eng = ((w - drifted).abs() * bps).sum(axis=1)
    add("3b gross - engine drift-adjusted trading costs", g2 - c_eng, "")
    borrow = (w.clip(upper=0).abs() * (E.C.SHORT_BORROW_BPS_PER_YEAR / 1e4 / 252)).sum(axis=1)
    add("4 - short borrow 30 bp/yr (= engine net, rf=0)", g2 - c_eng - borrow, "their-definition Sharpe in our engine")
    # 5. our definition: cash earns T-bill, Sharpe on excess over T-bill
    net_tb = g2 + (1 - w.sum(axis=1)) * rf - c_eng - borrow
    add("5 engine net with T-bill cash, excess over T-bill", net_tb - rf, "our definition = sum w_i (r_i - rf) - costs")

    # cross-check against engine.simulate itself
    w_dec = w.shift(-1)
    net0, gross0, *_ = E.simulate(w_dec, ohlc, pd.Series(0.0, index=rf.index), exec="next_open", cost_bps=COST)
    netT, *_ = E.simulate(w_dec, ohlc, E.load_rf("IS"), exec="next_open", cost_bps=COST)
    chk = {"gross_rf0": float((gross0 - g2).loc[a:b].abs().max()),
           "net_rf0": float((net0 - (g2 - c_eng - borrow)).loc[a:b].abs().max()),
           "net_tbill": float((netT - net_tb).loc[a:b].abs().max())}

    tab = pd.DataFrame(rows)
    tab["delta_sharpe"] = tab["sharpe"].diff()
    print(tab.round(4).to_string(index=False))
    print("max |manual - engine.simulate|:", chk)
    # what drives step 1: correlation of the overnight and intraday legs
    extra = {"turnover_their_def": float(dw.sum(axis=1).loc[a:"2024-10-01"].mean() * 252),
             "turnover_engine_def": float((w - drifted).abs().sum(axis=1).loc[a:b].mean() * 252),
             "share_of_TLT_var_overnight": float(r_co["TLT"].loc[a:b].var() / (r_co["TLT"].loc[a:b].var() + r_oc["TLT"].loc[a:b].var())),
             "mean_rf_ann_IS": float(rf.loc[a:b].mean() * 252),
             "mean_rf_ann_2022_2024": float(rf.loc["2022":b].mean() * 252)}
    print(extra)
    tab.to_csv(out / "step4_bridge.csv", index=False)
    (out / "step4_bridge.json").write_text(json.dumps({"bridge": rows, "engine_crosscheck_max_abs": chk, "extra": extra},
                                                      indent=2, default=float))


if __name__ == "__main__":
    main()
