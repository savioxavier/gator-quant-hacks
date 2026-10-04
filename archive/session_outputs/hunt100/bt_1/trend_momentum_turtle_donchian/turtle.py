"""Turtle Donchian breakout systems (SPEC.md in this folder)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common as C  # noqa: E402

SID = "trend_momentum_turtle_donchian"


def chan(c, n):
    return c.rolling(n, min_periods=n).max().shift(1).to_numpy(), c.rolling(n, min_periods=n).min().shift(1).to_numpy()


def system2(c: pd.Series, nrel: pd.Series, pyramid: bool):
    """Returns daily units (signed) and the unit size n_entry (N/close at the initial entry)."""
    cv = c.to_numpy()
    nv = nrel.to_numpy()
    hi_e, lo_e = chan(c, 55)
    hi_x, lo_x = chan(c, 20)
    T = len(cv)
    units = np.zeros(T)
    nent = np.full(T, np.nan)
    pos, u, last_ref, nabs, stop, ne = 0, 0, np.nan, np.nan, np.nan, np.nan
    trades = 0
    for t in range(T):
        x = cv[t]
        if not np.isfinite(x):
            continue
        if pos > 0 and ((np.isfinite(lo_x[t]) and x < lo_x[t]) or x <= stop):
            pos, u = 0, 0
        elif pos < 0 and ((np.isfinite(hi_x[t]) and x > hi_x[t]) or x >= stop):
            pos, u = 0, 0
        elif pos != 0 and pyramid:
            while u < 4 and (x - last_ref) * pos >= 0.5 * nabs:
                u += 1
                last_ref += pos * 0.5 * nabs
                stop = last_ref - pos * 2 * nabs
        if pos == 0 and np.isfinite(hi_e[t]) and np.isfinite(nv[t]) and nv[t] > 0:
            if x > hi_e[t]:
                pos = 1
            elif x < lo_e[t]:
                pos = -1
            if pos != 0:
                trades += 1
                u, last_ref, ne = 1, x, nv[t]
                nabs = ne * x
                stop = x - pos * 2 * nabs
        units[t] = pos * u
        nent[t] = ne if pos != 0 else np.nan
    return units, nent, trades


def system1(c: pd.Series, nrel: pd.Series):
    cv = c.to_numpy()
    nv = nrel.to_numpy()
    hi_e, lo_e = chan(c, 20)
    hi_x, lo_x = chan(c, 10)
    hi_f, lo_f = chan(c, 55)
    T = len(cv)
    units = np.zeros(T)
    nent = np.full(T, np.nan)
    hpos, href, hstop = 0, np.nan, np.nan
    rpos, rstop, rn = 0, np.nan, np.nan
    last = None
    stats = {"breakouts": 0, "taken": 0, "skipped": 0, "failsafe": 0, "wins": 0, "losses": 0}
    for t in range(T):
        x = cv[t]
        if not np.isfinite(x):
            continue
        # exits (hypothetical tracker, then the real book)
        if hpos > 0 and (x <= hstop or (np.isfinite(lo_x[t]) and x < lo_x[t])):
            last = "win" if (x > hstop and x > href) else "loss"
            hpos = 0
        elif hpos < 0 and (x >= hstop or (np.isfinite(hi_x[t]) and x > hi_x[t])):
            last = "win" if (x < hstop and x < href) else "loss"
            hpos = 0
        if rpos > 0 and (x <= rstop or (np.isfinite(lo_x[t]) and x < lo_x[t])):
            rpos = 0
        elif rpos < 0 and (x >= rstop or (np.isfinite(hi_x[t]) and x > hi_x[t])):
            rpos = 0
        ok_n = np.isfinite(nv[t]) and nv[t] > 0
        # System 1 breakout
        if ok_n and np.isfinite(hi_e[t]) and hpos == 0:
            d = 1 if x > hi_e[t] else (-1 if x < lo_e[t] else 0)
            if d != 0:
                stats["breakouts"] += 1
                take = last != "win"
                hpos, href = d, x
                hstop = x - d * 2 * nv[t] * x
                if take and rpos == 0:
                    rpos, rn = d, nv[t]
                    rstop = x - d * 2 * rn * x
                    stats["taken"] += 1
                elif not take:
                    stats["skipped"] += 1
        # failsafe 55-day breakout while flat
        if ok_n and rpos == 0 and np.isfinite(hi_f[t]):
            d = 1 if x > hi_f[t] else (-1 if x < lo_f[t] else 0)
            if d != 0:
                rpos, rn = d, nv[t]
                rstop = x - d * 2 * rn * x
                stats["failsafe"] += 1
        units[t] = rpos
        nent[t] = rn if rpos != 0 else np.nan
    return units, nent, stats


def decisions(P, units: pd.DataFrame, nent: pd.DataFrame, start):
    raw = (units * 0.01 / nent).fillna(0.0)
    raw = raw.where(P["elig"], 0.0)
    w_dec = pd.DataFrame(0.0, index=P["cal"], columns=C.TICKERS)
    ex = P["ex"]
    days = [d for d in P["cal"] if d >= start]
    for t in days:
        r = raw.loc[t]
        if (r != 0).any():
            w_dec.loc[t] = C.scale_to_target(r, ex.loc[:t]).values
    return w_dec


def main():
    P = C.panel("FWD")
    raw_ohlc = C.raw_ohlc_nyse(P["cal"])
    nrel = C.wilder_nrel(raw_ohlc, 20)
    px = P["px"]
    start = pd.Timestamp("2011-01-01")
    U = {v: pd.DataFrame(0.0, index=P["cal"], columns=C.TICKERS) for v in ("V1", "V2", "V3")}
    NE = {v: pd.DataFrame(np.nan, index=P["cal"], columns=C.TICKERS) for v in ("V1", "V2", "V3")}
    s1stats = {}
    ntr = {"V1": 0, "V3": 0}
    for c in C.TICKERS:
        u, n, k = system2(px[c], nrel[c], False)
        U["V1"][c], NE["V1"][c] = u, n
        ntr["V1"] += k
        u, n, st = system1(px[c], nrel[c])
        U["V2"][c], NE["V2"][c] = u, n
        s1stats[c] = st
        u, n, k = system2(px[c], nrel[c], True)
        U["V3"][c], NE["V3"][c] = u, n
        ntr["V3"] += k
    agg = pd.DataFrame(s1stats).T.sum()
    print("System 1 stats (all data):", agg.to_dict(), "System 2 trades:", ntr)
    results, allm = {}, {}
    for v in ("V1", "V2", "V3"):
        w = decisions(P, U[v], NE[v], start)
        res = C.run(w, P)
        m = C.metrics(res)
        ins = U[v].loc[res["first"]:C.IS_END].where(P["elig"].loc[res["first"]:C.IS_END])
        m["frac_in_market"] = float((ins.abs() > 0).sum().sum() / ins.notna().sum().sum())
        m["avg_units_when_in"] = float(ins.abs()[ins.abs() > 0].stack().mean())
        results[v], allm[v] = res, m
        print(v, C.fmt(m), f"in_mkt={m['frac_in_market']:.2f} units={m['avg_units_when_in']:.2f}")
    best = max(allm, key=lambda k: allm[k]["is_net_sharpe_1x"])
    pd.concat({v: results[v]["df"] for v in results}, axis=1).to_parquet(HERE / "variants.parquet")
    with open(HERE / "metrics.json", "w", encoding="utf-8") as fh:
        json.dump({"variants": allm, "headline": best, "system1_stats": agg.to_dict(), "system2_trades": ntr}, fh,
                  indent=2, default=str)
    side = {
        "id": SID, "variant": best,
        "rule": ("Daily close-based Donchian breakout on the excess-return index: V1 System 2 (55-session entry, "
                 "20-session exit), V2 System 1 (20/10) with the last-breakout-winner skip filter and 55-session "
                 "failsafe, V3 System 2 with pyramiding (+1 unit per N/2, max 4); 2N stop from the latest unit; "
                 "N = Wilder 20-day ATR/close of the front contract (lagged one session); unit weight 0.01/(N/close) "
                 "at entry; book to 10% ex-ante daily (trailing 252 cov), gross<=3; next_close."),
        "sources": ["https://oxfordstrat.com/coasdfASD32/uploads/2016/01/turtle-rules.pdf",
                    "https://ideas.repec.org/a/eee/jbfina/v34y2010i2p409-426.html",
                    "https://github.com/robcarver17/pysystemtrade"],
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
