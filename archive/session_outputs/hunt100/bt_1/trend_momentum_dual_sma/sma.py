"""Moving-average trend rules (SPEC.md in this folder)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common as C  # noqa: E402

SID = "trend_momentum_dual_sma"


def sig_cross(P):
    px = P["px"]
    f = px.rolling(50, min_periods=50).mean()
    s = px.rolling(200, min_periods=200).mean()
    return pd.DataFrame(np.where(f > s, 1.0, -1.0), index=px.index, columns=px.columns).where(s.notna())


def sig_10m(P, me):
    mp = P["px"].reindex(me)
    sma = mp.rolling(10, min_periods=10).mean()
    return pd.DataFrame(np.where(mp > sma, 1.0, -1.0), index=me, columns=mp.columns).where(sma.notna())


def sig_channel(P):
    px = P["px"]
    hi = px.rolling(250, min_periods=250).max()
    lo = px.rolling(250, min_periods=250).min()
    mid = (hi + lo) / 2
    return pd.DataFrame(np.where(px > mid, 1.0, -1.0), index=px.index, columns=px.columns).where(mid.notna())


def decisions(P, dates, sig):
    w_dec = pd.DataFrame(np.nan, index=P["cal"], columns=C.TICKERS)
    for t in dates:
        el = P["elig"].loc[t]
        st = sig.loc[t]
        ok = [c for c in C.TICKERS if el[c] and np.isfinite(st[c])]
        w = pd.Series(0.0, index=C.TICKERS)
        if ok:
            w[ok] = st[ok] * 0.40 / P["vol"].loc[t, ok] / len(ok)
            w = C.scale_to_target(w, P["ex"].loc[:t])
        w_dec.loc[t] = w.values
    return w_dec.ffill().fillna(0.0)


def main():
    P = C.panel("FWD")
    cal = P["cal"]
    start = pd.Timestamp("2010-06-01")
    we = C.week_ends(cal)
    we = we[we >= start]
    me = C.month_ends(cal)
    me = me[me >= start]
    specs = {"V1": (we, sig_cross(P)), "V2": (me, sig_10m(P, me)), "V3": (we, sig_channel(P))}
    results, allm = {}, {}
    for v, (dates, sig) in specs.items():
        w = decisions(P, dates, sig)
        res = C.run(w, P)
        m = C.metrics(res)
        results[v], allm[v] = res, m
        print(v, C.fmt(m))
    best = max(allm, key=lambda k: allm[k]["is_net_sharpe_1x"])
    pd.concat({v: results[v]["df"] for v in results}, axis=1).to_parquet(HERE / "variants.parquet")
    with open(HERE / "metrics.json", "w", encoding="utf-8") as fh:
        json.dump({"variants": allm, "headline": best}, fh, indent=2, default=str)
    side = {
        "id": SID, "variant": best,
        "rule": ("Each future s in {+1,-1} on the excess-return index: V1 weekly SMA50 vs SMA200; V2 monthly month-end "
                 "price vs 10-month SMA (incl. current); V3 weekly sign(close - midpoint of 250-session max/min); "
                 "w = s*0.40/sigma_EWMA/N, book to 10% (trailing 252 cov), gross<=3, next_close."),
        "sources": ["https://ideas.repec.org/a/eee/jbfina/v34y2010i2p409-426.html",
                    "https://openaccess.city.ac.uk/id/eprint/17846/1/COMMODITY%20pAPER.pdf",
                    "https://research.cbs.dk/en/publications/which-trend-is-your-friend/"],
        "window": {"is": allm[best]["is_window"], "later": "2024-10-03..2026-10-02"},
        "columns": {"net_1x": "daily excess return net of the realistic cost map", "net_2x": "2x costs",
                    "gross": "before costs"},
        "cost_bps_one_way": C.COST, "metrics": allm[best],
        "all_variants": {k: {kk: allm[k][kk] for kk in ("is_net_sharpe_1x", "is_net_sharpe_2x", "is_gross_sharpe",
                                                        "later_net_sharpe_1x", "turnover")} for k in allm},
    }
    C.save_series(SID, results[best], side)
    print("headline", best)


if __name__ == "__main__":
    main()
