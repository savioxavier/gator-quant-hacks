"""Trends Everywhere on ETF asset classes: V1 ETFs 1/3/12 long/short, V2 equal-risk V1 + S1 futures book, V3 long-or-cash."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as K  # noqa: E402
from src import forward2  # noqa: E402

SID = "trend_momentum_trends_everywhere_etf"
OUT = Path(__file__).resolve().parent
ETFS = ["EEM", "VGK", "EWJ", "VNQ", "HYG", "LQD", "EMB", "TIP",
        "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
LOOKBACKS = (21, 63, 252)


def etf_decisions(period, long_only=False):
    ohlc, rf, ex = K.panel(ETFS, period)
    vol = K.ewma_vol(ex)
    elig = K.eligibility(ohlc, ex, vol)
    w_dec = pd.DataFrame(np.nan, index=ex.index, columns=ETFS)
    for t in K.month_ends(ex.index):
        hist = ex.loc[:t]
        el = [c for c in ETFS if elig.loc[t, c]]
        w = pd.Series(0.0, index=ETFS)
        if el:
            sig = pd.Series(0.0, index=el)
            for k in LOOKBACKS:
                sig += np.sign((1 + hist[el].tail(k).fillna(0.0)).prod() - 1)
            sig /= len(LOOKBACKS)
            if long_only:
                sig = sig.clip(lower=0.0)
            w[el] = sig * (0.40 / vol.loc[t, el]) / len(el)
            w = K.scale_to_target(w, hist, gross_cap=2.0)
        w_dec.loc[t] = w.values
    return w_dec.ffill().fillna(0.0)


def combo_decisions(period):
    """0.5 x V1 (10%) + 0.5 x S1 (10%), rescaled to 10% with the 47-instrument trailing covariance, gross <= 3."""
    wv1 = etf_decisions(period)
    ws1 = forward2.s1_decisions(period)
    tick = ETFS + forward2.S1_TICKERS
    _, _, ex = K.panel(tick, period)
    w_dec = pd.DataFrame(np.nan, index=ex.index, columns=tick)
    s1_live = ws1.abs().sum(axis=1) > 0
    first_s1 = s1_live[s1_live].index[0]
    for t in K.month_ends(ex.index):
        if t < first_s1:
            w_dec.loc[t] = 0.0
            continue
        combo = pd.concat([0.5 * wv1.loc[t], 0.5 * ws1.loc[t]])
        w_dec.loc[t] = K.scale_to_target(combo.reindex(tick).fillna(0.0), ex.loc[:t], gross_cap=3.0).values
    return w_dec.ffill().fillna(0.0)


def sim_combo(w_dec, period):
    """ETF legs next_open (ETF costs/borrow), futures legs next_close (realistic map); net = a + b - rf exactly."""
    a = K.run_sim(w_dec[ETFS], period, "next_open")
    b = K.run_sim(w_dec[forward2.S1_TICKERS], period, "next_close")
    # run_sim returns EXCESS series: (net_a - rf) + (net_b - rf) = net_total - rf
    out = {k: a[k] + b[k] for k in ("net_1x", "net_2x", "gross")}
    out["turnover"] = a["turnover"] + b["turnover"]
    out["held"] = pd.concat([a["held"], b["held"]], axis=1)
    out["rf"] = a["rf"]
    return out


def main():
    sims = {
        "V1": K.run_sim(etf_decisions("FWD"), "FWD", "next_open"),
        "V2": sim_combo(combo_decisions("FWD"), "FWD"),
        "V3": K.run_sim(etf_decisions("FWD", long_only=True), "FWD", "next_open"),
    }
    starts = {v: K.first_live(s["held"]) for v, s in sims.items()}
    common = max(starts.values())
    res_own = {v: K.metrics(sims[v], starts[v]) for v in sims}
    res_common = {v: K.metrics(sims[v], common) for v in sims}
    # point-in-time check: V1 computed with IS-truncated data equals the FWD run over the in-sample window
    s_is = K.run_sim(etf_decisions("IS"), "IS", "next_open")
    diff = float((s_is["net_1x"] - sims["V1"]["net_1x"].loc[: K.IS_END]).abs().max())
    best = max(sims, key=lambda v: res_common[v]["is_net_sharpe_1x"])
    rules = {
        "V1": "month-end: s=mean(sign R21,R63,R252) of excess returns on 17 ETFs, w=s*0.40/sigma/N, book 10% (252d cov), gross<=2, next_open",
        "V2": "0.5*V1 + 0.5*S1 30-futures 1/3/12 book, rescaled to 10% with 47-instrument 252d cov, gross<=3; ETFs next_open, futures next_close",
        "V3": "V1 with s clipped at 0 (long or T-bills), book 10%, gross<=2, next_open",
    }
    meta = {"id": SID, "sources": ["https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-Trends-Everywhere_JOIM.pdf"],
            "instruments": ETFS}
    paths = {}
    for v in sims:
        paths[v] = K.save_series(f"{SID}__{v}", sims[v], starts[v], {**meta, "variant": v, "rule": rules[v],
                                 "is_window": res_own[v]["is_window"]})
    paths["headline"] = K.save_series(SID, sims[best], starts[best], {**meta, "variant": best, "rule": rules[best],
                                      "selected_on": "highest in-sample net Sharpe among V1-V3 on the common window",
                                      "is_window": res_own[best]["is_window"]})
    out = {"variants_own_window": res_own, "variants_common_window": res_common, "selected": best,
           "common_start": str(common.date()), "pit_check_max_abs_diff": diff, "paths": paths}
    K.dump(out, OUT / "results.json")
    for lab, rr in (("own", res_own), ("common", res_common)):
        for v, r in rr.items():
            print(lab, v, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in r.items() if k != "yearly"})
    print("selected", best, "pit diff", diff)


if __name__ == "__main__":
    main()
