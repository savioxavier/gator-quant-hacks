"""ES trend timing: V1 10-month SMA long/flat, V2 MED turning points, V3 12m TSMOM; benchmark always-long."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as K  # noqa: E402

SID = "trend_momentum_es_trend_timing"
OUT = Path(__file__).resolve().parent
T = "F_ES"


def decisions(period, variant):
    ohlc, rf, ex = K.panel([T], period)
    vol = K.ewma_vol(ex)
    elig = K.eligibility(ohlc, ex, vol)
    close = ohlc["close"][T]
    me = K.month_ends(ex.index)
    mclose = close.loc[me]
    sma10 = mclose.rolling(10, min_periods=10).mean()
    w = pd.DataFrame(np.nan, index=ex.index, columns=[T])
    for t in me:
        if not elig.loc[t, T]:
            w.loc[t, T] = 0.0
            continue
        hist = ex[T].loc[:t]
        r252 = (1 + hist.tail(252).fillna(0.0)).prod() - 1
        r21 = (1 + hist.tail(21).fillna(0.0)).prod() - 1
        if variant == "V1":
            if not np.isfinite(sma10.loc[t]):
                w.loc[t, T] = 0.0
                continue
            sig = 1.0 if mclose.loc[t] > sma10.loc[t] else 0.0
        elif variant == "V2":
            a, b = np.sign(r252), np.sign(r21)
            sig = 1.0 if (a > 0 and b > 0) else (-1.0 if (a < 0 and b < 0) else 0.0)
        elif variant == "V3":
            sig = float(np.sign(r252))
        elif variant == "BENCH":
            sig = 1.0
        w.loc[t, T] = sig * min(K.TARGET_VOL / vol.loc[t, T], 3.0)
    # live only once the SMA (10 month-ends) and 260-session history exist, for every variant alike
    return w.ffill().fillna(0.0), sma10.first_valid_index()


def main():
    res, sims, starts = {}, {}, {}
    for v in ("V1", "V2", "V3", "BENCH"):
        w, _ = decisions("FWD", v)
        s = K.run_sim(w, "FWD", "next_close")
        sims[v] = s
        # first day held under the eligibility rule (signal may be 0 then): first day a decision could be non-zero
        elig_dec = w.index[(w.index >= pd.Timestamp("2011-01-01"))]
        starts[v] = None
    # common start: first held day of the always-long benchmark that also has the SMA (V1 needs 10 month-ends)
    wb, sma_start = decisions("FWD", "BENCH")
    live_b = K.first_live(sims["BENCH"]["held"])
    w1, _ = decisions("FWD", "V1")
    # V1 decisions become defined at max(260-session eligibility, 10th month-end)
    first_dec = max(sma_start, wb[wb[T] != 0].index[0])
    held_start = sims["BENCH"]["held"].index[sims["BENCH"]["held"].index.get_loc(first_dec) + 2]
    common = max(live_b, held_start)
    for v, s in sims.items():
        m = K.metrics(s, common)
        res[v] = m
    # point-in-time check: IS-period run equals FWD run over IS
    w_is, _ = decisions("IS", "V1")
    s_is = K.run_sim(w_is, "IS", "next_close")
    diff = float((s_is["net_1x"] - sims["V1"]["net_1x"].loc[: K.IS_END]).abs().max())
    best = max(("V1", "V2", "V3"), key=lambda v: res[v]["is_net_sharpe_1x"])
    meta_common = {
        "id": SID, "sources": ["https://www.trendfollowing.com/whitepaper/CMT-Simple.pdf",
                               "https://benny.aeaweb.org/conference/2021/preliminary/paper/492Ds6fk",
                               "https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Time-Series-Momentum-Factors-Monthly.xlsx"],
        "instruments": [T], "exec": "next_close", "cost_bps_one_way": {"F_ES": 1.0},
    }
    rules = {
        "V1": "month-end: long F_ES at 10%/sigma (EWMA com 60, cap 3x) if index > 10-month SMA of month-end closes, else T-bills",
        "V2": "month-end: MED = +1 if sign(R252) and sign(R21) both >0, -1 if both <0, else 0; times 10%/sigma",
        "V3": "month-end: sign(R252) times 10%/sigma (long/short)",
        "BENCH": "always long F_ES at 10%/sigma, month-end resizing (benchmark, not a variant)",
    }
    paths = {}
    for v in ("V1", "V2", "V3", "BENCH"):
        paths[v] = K.save_series(f"{SID}__{v}", sims[v], common, {**meta_common, "variant": v, "rule": rules[v],
                                 "is_window": res[v]["is_window"]})
    paths["headline"] = K.save_series(SID, sims[best], common, {**meta_common, "variant": best, "rule": rules[best],
                                      "selected_on": "highest in-sample net Sharpe among V1-V3 on the common window",
                                      "is_window": res[best]["is_window"]})
    out = {"variants": res, "selected": best, "common_start": str(common.date()), "pit_check_max_abs_diff": diff,
           "paths": paths}
    K.dump(out, OUT / "results.json")
    for v in res:
        r = res[v]
        print(v, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in r.items() if k != "yearly"})
    print("selected", best, "pit diff", diff)


if __name__ == "__main__":
    main()
