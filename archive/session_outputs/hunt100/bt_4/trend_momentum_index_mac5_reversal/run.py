"""Equity index short-term reversal against MAC(5) (Baltussen-van Bekkum-Da). V1 futures next_close (daily),
V2 ETF proxies next_open (daily), V3 weekly -sign(5-session return) futures next_close."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as K  # noqa: E402

SID = "trend_momentum_index_mac5_reversal"
OUT = Path(__file__).resolve().parent
FUT = ["F_ES", "F_NQ", "F_RTY", "F_YM"]
ETF = ["SPY", "QQQ", "IWM", "DIA"]


def daily_decisions(tickers, period, gross_cap):
    ohlc, rf, ex = K.panel(tickers, period)
    vol = K.ewma_vol(ex)
    elig = K.eligibility(ohlc, ex, vol)
    r = ex.fillna(0.0)
    wsum = 4 * r + 3 * r.shift(1) + 2 * r.shift(2) + 1 * r.shift(3)
    sig_d = vol / np.sqrt(252)
    x = -(wsum / (10 * sig_d))
    raw = x.clip(-2, 2) * 0.10 / vol
    raw = raw.where(elig, 0.0).fillna(0.0)
    n = elig.sum(axis=1).replace(0, np.nan)
    raw = raw.div(n, axis=0).fillna(0.0)
    exv = ex.to_numpy()
    w = np.zeros_like(raw.to_numpy())
    rv = raw.to_numpy()
    for i in range(len(raw)):
        v = rv[i]
        nz = np.flatnonzero(v != 0)
        if len(nz) == 0:
            continue
        hist = exv[max(0, i - K.COV_WINDOW + 1): i + 1][:, nz]
        cov = pd.DataFrame(hist).cov(min_periods=60).fillna(0.0).to_numpy()
        var = float(v[nz] @ cov @ v[nz]) * 252
        if not np.isfinite(var) or var <= 0:
            continue
        ww = v * (K.TARGET_VOL / np.sqrt(var))
        g = np.abs(ww).sum()
        if g > gross_cap:
            ww = ww * gross_cap / g
        w[i] = ww
    return pd.DataFrame(w, index=raw.index, columns=tickers)


def weekly_decisions(tickers, period, gross_cap):
    ohlc, rf, ex = K.panel(tickers, period)
    vol = K.ewma_vol(ex)
    elig = K.eligibility(ohlc, ex, vol)
    w_dec = pd.DataFrame(np.nan, index=ex.index, columns=tickers)
    for t in K.week_ends(ex.index):
        el = [c for c in tickers if elig.loc[t, c]]
        w = pd.Series(0.0, index=tickers)
        if el:
            hist = ex.loc[:t]
            r5 = (1 + hist[el].tail(5).fillna(0.0)).prod() - 1
            w[el] = -np.sign(r5) * 0.10 / vol.loc[t, el] / len(el)
            w = K.scale_to_target(w, hist, gross_cap=gross_cap)
        w_dec.loc[t] = w.values
    return w_dec.ffill().fillna(0.0)


def main():
    sims = {
        "V1": K.run_sim(daily_decisions(FUT, "FWD", 3.0), "FWD", "next_close"),
        "V2": K.run_sim(daily_decisions(ETF, "FWD", 2.0), "FWD", "next_open"),
        "V3": K.run_sim(weekly_decisions(FUT, "FWD", 3.0), "FWD", "next_close"),
    }
    starts = {v: K.first_live(s["held"]) for v, s in sims.items()}
    common = max(starts.values())
    res_own = {v: K.metrics(sims[v], starts[v]) for v in sims}
    res_common = {v: K.metrics(sims[v], common) for v in sims}
    # diagnostics: V2 signal on ETFs filled at next close (isolates the fill-timing effect), and gross Sharpe by subperiod
    s_v2c = K.run_sim(daily_decisions(ETF, "FWD", 2.0), "FWD", "next_close")
    diag = {
        "V2_etf_next_close_common_net": K.sharpe_window(s_v2c, common),
        "V2_etf_next_close_common_gross": K.sharpe_window(s_v2c, common, col="gross"),
        "V2_etf_next_open_2005_2010_gross": K.sharpe_window(sims["V2"], starts["V2"], "2010-12-31", col="gross"),
        "V1_mean_gross_exposure": float(sims["V1"]["held"].abs().sum(axis=1).loc[common:K.IS_END].mean()),
        "V2_mean_gross_exposure": float(sims["V2"]["held"].abs().sum(axis=1).loc[common:K.IS_END].mean()),
    }
    # point-in-time check
    s_is = K.run_sim(daily_decisions(FUT, "IS", 3.0), "IS", "next_close")
    diff = float((s_is["net_1x"] - sims["V1"]["net_1x"].loc[: K.IS_END]).abs().max())
    best = max(sims, key=lambda v: res_common[v]["is_net_sharpe_1x"])
    rules = {
        "V1": "daily: x=-(4r_t+3r_t-1+2r_t-2+r_t-3)/(10 sigma_d); w=clip(x,-2,2)*0.10/sigma/N on ES NQ RTY YM futures; book 10% (252d cov), gross<=3; next_close",
        "V2": "V1 signal on ETF proxies SPY QQQ IWM DIA, book 10%, gross<=2, next_open (true NYSE open), ETF costs + borrow",
        "V3": "weekly (last session of week): w=-sign(R5)*0.10/sigma/N on the 4 index futures, book 10%, gross<=3; next_close",
    }
    meta = {"id": SID, "sources": ["https://www3.nd.edu/~zda/Indexing.pdf"]}
    paths = {}
    for v in sims:
        paths[v] = K.save_series(f"{SID}__{v}", sims[v], starts[v], {**meta, "variant": v, "rule": rules[v],
                                 "is_window": res_own[v]["is_window"]})
    paths["headline"] = K.save_series(SID, sims[best], starts[best], {**meta, "variant": best, "rule": rules[best],
                                      "selected_on": "highest in-sample net Sharpe among V1-V3 on the common window",
                                      "is_window": res_own[best]["is_window"]})
    out = {"variants_own_window": res_own, "variants_common_window": res_common, "selected": best,
           "common_start": str(common.date()), "diagnostics": diag, "pit_check_max_abs_diff": diff, "paths": paths}
    K.dump(out, OUT / "results.json")
    for lab, rr in (("own", res_own), ("common", res_common)):
        for v, r in rr.items():
            print(lab, v, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in r.items() if k != "yearly"})
    print("diag", diag)
    print("selected", best, "pit diff", diff)


if __name__ == "__main__":
    main()
