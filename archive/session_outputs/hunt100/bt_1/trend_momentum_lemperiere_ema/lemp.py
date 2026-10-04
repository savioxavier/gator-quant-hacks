"""Lemperiere et al. EMA-deviation trend (SPEC.md in this folder)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common as C  # noqa: E402

SID = "trend_momentum_lemperiere_ema"


def signal(P, me, n):
    mp = P["px"].reindex(me)
    out = pd.DataFrame(np.nan, index=me, columns=C.TICKERS)
    for c in C.TICKERS:
        p = mp[c].dropna()
        if len(p) < 6:
            continue
        pbar = p.ewm(alpha=1.0 / n, adjust=True).mean().shift(1)          # excludes the current month
        sig = p.diff().abs().ewm(alpha=1.0 / n, adjust=True).mean()       # includes the current change
        s = (p - pbar) / sig
        s[np.arange(len(p)) < 5] = np.nan                                  # >= 6 month-end prices
        out.loc[s.index, c] = s
    return out


def decisions(P, me, s, saturate=False):
    w_dec = pd.DataFrame(np.nan, index=P["cal"], columns=C.TICKERS)
    for t in me:
        el = P["elig"].loc[t]
        st = s.loc[t]
        ok = [c for c in C.TICKERS if el[c] and np.isfinite(st[c])]
        w = pd.Series(0.0, index=C.TICKERS)
        if ok:
            x = np.tanh(st[ok]) if saturate else np.sign(st[ok])
            w[ok] = x * 0.40 / P["vol"].loc[t, ok] / len(ok)
            w = C.scale_to_target(w, P["ex"].loc[:t])
        w_dec.loc[t] = w.values
    return w_dec.ffill().fillna(0.0)


def main():
    P = C.panel("FWD")
    me = C.month_ends(P["cal"])
    me = me[me >= pd.Timestamp("2010-06-01")]
    s5, s10 = signal(P, me, 5), signal(P, me, 10)
    specs = {"V1": (s5, False), "V2": (s10, False), "V3": (s5, True)}
    results, allm = {}, {}
    for v, (s, sat) in specs.items():
        w = decisions(P, me, s, sat)
        res = C.run(w, P)
        m = C.metrics(res)
        results[v], allm[v] = res, m
        print(v, C.fmt(m))
    # paper-style fictitious P&L check (no costs, sign(s) / sigma_n in price units, monthly) on our data, n=5
    mp = P["px"].reindex(me)
    pnl = []
    for c in C.TICKERS:
        p = mp[c].dropna()
        pbar = p.ewm(alpha=0.2, adjust=True).mean().shift(1)
        sg = p.diff().abs().ewm(alpha=0.2, adjust=True).mean()
        sv = (p - pbar) / sg
        q = (np.sign(sv) / sg * p.diff().shift(-1)).rename(c)
        pnl.append(q)
    pnl = pd.concat(pnl, axis=1)
    el_me = P["elig"].reindex(me).reindex(columns=pnl.columns)
    pnl = pnl.where(el_me)
    agg = pnl.sum(axis=1).loc["2011-07-01":C.IS_END]
    paper_style = float(agg.mean() / agg.std() * np.sqrt(12))
    print("paper-style fictitious P&L Sharpe (monthly, gross, n=5, IS):", round(paper_style, 3))
    best = max(allm, key=lambda k: allm[k]["is_net_sharpe_1x"])
    pd.concat({v: results[v]["df"] for v in results}, axis=1).to_parquet(HERE / "variants.parquet")
    with open(HERE / "metrics.json", "w", encoding="utf-8") as fh:
        json.dump({"variants": allm, "headline": best, "paper_style_gross_sharpe_n5_is": paper_style}, fh,
                  indent=2, default=str)
    side = {
        "id": SID, "variant": best,
        "rule": ("Month-end p = excess-return index; pbar = EWM(alpha=1/n) of past month-end prices excluding the "
                 "current; sigma_n = EWM(alpha=1/n) of |monthly changes|; s = (p - pbar)/sigma_n; w = sign(s) (V1 n=5, "
                 "V2 n=10) or tanh(s) (V3 n=5) * 0.40/sigma_EWMA/N, book to 10% (trailing 252 cov), gross<=3, "
                 "next_close, monthly."),
        "sources": ["https://arxiv.org/abs/1404.3274"],
        "window": {"is": allm[best]["is_window"], "later": "2024-10-03..2026-10-02"},
        "columns": {"net_1x": "daily excess return net of the realistic cost map", "net_2x": "2x costs",
                    "gross": "before costs"},
        "cost_bps_one_way": C.COST, "metrics": allm[best],
        "all_variants": {k: {kk: allm[k][kk] for kk in ("is_net_sharpe_1x", "is_net_sharpe_2x", "is_gross_sharpe",
                                                        "later_net_sharpe_1x", "turnover")} for k in allm},
        "paper_style_gross_sharpe_n5_is": paper_style,
    }
    C.save_series(SID, results[best], side)
    print("headline", best)


if __name__ == "__main__":
    main()
