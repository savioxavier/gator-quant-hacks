"""Baltas-Kosowski TREND / YZ / CF (SPEC.md in this folder)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common as C  # noqa: E402

SID = "trend_momentum_bk_trend_tstat_cf"
NW_LAG = 21
WIN = 252
CORR_WIN = 126


def nw_t_slope(y: np.ndarray, lag: int = NW_LAG) -> float:
    n = len(y)
    t = np.arange(n, dtype=float)
    X = np.column_stack([np.ones(n), t])
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    Xe = X * e[:, None]
    S = Xe.T @ Xe
    for j in range(1, lag + 1):
        G = Xe[j:].T @ Xe[:-j]
        S += (1 - j / (lag + 1)) * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    return float(beta[1] / np.sqrt(V[1, 1])) if V[1, 1] > 0 else 0.0


def signals(P, me):
    """TREND (NW t of the log-price slope) and SIGN(12m) at every month-end."""
    logp = np.log(P["px"])
    trend = pd.DataFrame(0.0, index=me, columns=C.TICKERS)
    tstat = pd.DataFrame(np.nan, index=me, columns=C.TICKERS)
    sign12 = pd.DataFrame(0.0, index=me, columns=C.TICKERS)
    for t in me:
        hist = logp.loc[:t]
        exh = P["ex"].loc[:t]
        for c in C.TICKERS:
            y = hist[c].dropna().tail(WIN).to_numpy()
            if len(y) < WIN:
                continue
            ts = nw_t_slope(y)
            tstat.loc[t, c] = ts
            trend.loc[t, c] = 1.0 if ts > 2 else (-1.0 if ts < -2 else 0.0)
            cum = (1 + exh[c].tail(WIN).fillna(0.0)).prod() - 1
            sign12.loc[t, c] = 1.0 if cum > 0 else -1.0
    return trend, sign12, tstat


def cf_factor(X: pd.Series, ex_hist: pd.DataFrame, n_t: int) -> tuple[float, float]:
    act = [c for c in X.index if X[c] != 0]
    if len(act) < 2:
        rho = 0.0
    else:
        sr = ex_hist[act].tail(CORR_WIN).mul(X[act], axis=1)
        cm = sr.corr(min_periods=60).to_numpy()
        iu = np.triu_indices(len(act), 1)
        vals = cm[iu]
        vals = vals[np.isfinite(vals)]
        rho = float(vals.mean()) if len(vals) else 0.0
    denom = max(1 + (n_t - 1) * rho, 1e-6)
    return float(np.sqrt(n_t / denom)), rho


def decisions(P, variant, sig, yz, me):
    trend, sign12, _ = sig
    w_dec = pd.DataFrame(np.nan, index=P["cal"], columns=C.TICKERS)
    diag = []
    for t in me:
        el = P["elig"].loc[t]
        if variant in ("V1", "V2"):
            vol = yz.loc[t]
            X = trend.loc[t]
        else:
            vol = P["vol"].loc[t]
            X = sign12.loc[t]
        ok = [c for c in C.TICKERS if el[c] and np.isfinite(vol[c]) and vol[c] > 0]
        w = pd.Series(0.0, index=C.TICKERS)
        if ok:
            n_t = len(ok)
            Xo = X[ok]
            if variant == "V2":
                cf, rho = 1.0, np.nan
            else:
                cf, rho = cf_factor(Xo, P["ex"].loc[:t], n_t)
            w[ok] = Xo * (C.TARGET_VOL * cf) / vol[ok] / n_t
            if variant == "V2":
                w = C.scale_to_target(w, P["ex"].loc[:t])
            else:
                w = C.cap_gross(w)
            diag.append({"date": t, "n": n_t, "n_active": int((Xo != 0).sum()), "cf": cf, "rho": rho,
                         "gross": float(w.abs().sum())})
        w_dec.loc[t] = w.values
    return w_dec.ffill().fillna(0.0), pd.DataFrame(diag)


def main():
    P = C.panel("FWD")
    raw = C.raw_ohlc_nyse(P["cal"])
    yz = C.yang_zhang(raw, 63, 40)
    me = C.month_ends(P["cal"])
    me = me[me >= pd.Timestamp("2011-01-01")]
    sig = signals(P, me)
    trend, sign12, tstat = sig
    results, allm = {}, {}
    for v in ("V1", "V2", "V3"):
        w, diag = decisions(P, v, sig, yz, me)
        res = C.run(w, P)
        m = C.metrics(res)
        d_is = diag[diag["date"] <= C.IS_END]
        m["avg_cf"] = float(d_is["cf"].mean())
        m["avg_rho"] = float(d_is["rho"].mean()) if d_is["rho"].notna().any() else None
        m["avg_n_active_frac"] = float((d_is["n_active"] / d_is["n"]).mean())
        m["avg_decision_gross"] = float(d_is["gross"].mean())
        results[v] = res
        allm[v] = m
        diag.to_csv(HERE / f"diag_{v}.csv", index=False)
        print(v, C.fmt(m), f"avg_cf={m['avg_cf']:.2f} rho={m['avg_rho']} act={m['avg_n_active_frac']:.2f}")
    # TREND diagnostics: share of zeros and agreement with SIGN (paper Fig. 6)
    el_me = P["elig"].reindex(me)
    zero_frac = ((trend == 0) & el_me).sum(axis=1) / el_me.sum(axis=1).replace(0, np.nan)
    agree = ((trend == sign12) & el_me).sum(axis=1) / el_me.sum(axis=1).replace(0, np.nan)
    tdiag = {"trend_zero_frac_is": float(zero_frac.loc[:C.IS_END].mean()),
             "trend_sign_agree_is": float(agree.loc[:C.IS_END].mean())}
    print(tdiag)
    # turnover comparison V1 vs V3 (paper: TREND+YZ cuts turnover)
    best = max(allm, key=lambda k: allm[k]["is_net_sharpe_1x"])
    pd.concat({v: results[v]["df"] for v in results}, axis=1).to_parquet(HERE / "variants.parquet")
    with open(HERE / "metrics.json", "w", encoding="utf-8") as fh:
        json.dump({"variants": allm, "headline": best, "trend_diag": tdiag}, fh, indent=2, default=str)
    side = {
        "id": SID, "variant": best,
        "rule": ("Month-end; X = sign of the Newey-West (lag 21) t-stat of the 252-session log-price time-trend slope "
                 "if |t| > 2 else 0 (V1/V2) or sign of the 12-month excess return (V3); vol = Yang-Zhang 63 sessions "
                 "(V1/V2) or EWMA com 60 (V3); w = X * 0.10 * CF / vol / N_t with CF = sqrt(N/(1+(N-1)rho)), rho = mean "
                 "pairwise corr of signed returns of active futures over 126 sessions (V1/V3); V2: CF = 1 then book to "
                 "10%; gross <= 3; next_close."),
        "sources": ["https://spiral.imperial.ac.uk/handle/10044/1/41472", "https://papers.ssrn.com/abstract=2140091",
                    "https://www.quantconnect.com/learning/articles/investment-strategy-library/improved-momentum-strategy-on-commodities-futures"],
        "window": {"is": allm[best]["is_window"], "later": "2024-10-03..2026-10-02"},
        "columns": {"net_1x": "daily excess return net of the realistic cost map", "net_2x": "2x costs",
                    "gross": "before costs"},
        "cost_bps_one_way": C.COST, "metrics": allm[best], "all_variants": {k: {kk: allm[k][kk] for kk in (
            "is_net_sharpe_1x", "is_net_sharpe_2x", "is_gross_sharpe", "later_net_sharpe_1x", "turnover")} for k in allm},
    }
    C.save_series(SID, results[best], side)
    print("headline", best)


if __name__ == "__main__":
    main()
