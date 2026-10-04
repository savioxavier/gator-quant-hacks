"""Existing strategies re-simulated at the realistic cost map (SPEC section 2).

Writes combine/existing.parquet (long table: sleeve x column) and combine/existing_gross.parquet
(held instrument gross per sleeve) plus comparators. Read-only use of the repo code; nothing logged.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<solo-repo>")
sys.path.insert(0, str(REPO))
assert os.environ.get("GQH_OOS_UNLOCK") != "1"

from src import engine as E          # noqa: E402
from src import forward as F         # noqa: E402
from src import forward2 as F2       # noqa: E402

OUT = Path(__file__).resolve().parent
P = "FWD"

REAL = {"ES": 0.75, "NQ": 0.75, "YM": 0.75, "RTY": 1.0, "ZT": 0.3, "ZF": 0.5, "ZN": 1.0, "ZB": 1.25, "UB": 1.5,
        "6E": 0.5, "6J": 0.75, "6B": 0.75, "6A": 0.75, "6C": 0.75, "6S": 1.0,
        "CL": 1.5, "GC": 1.5, "SI": 1.5, "HG": 1.5, "NG": 2.5, "HO": 2.5, "RB": 2.5, "PL": 2.5,
        "ZC": 4.0, "ZS": 4.0, "ZW": 4.0, "ZL": 4.0, "ZM": 4.0, "LE": 4.0, "HE": 4.0}


def cmap(tickers, mult=1.0):
    out = {}
    for t in tickers:
        if t == "ES16":
            out[t] = 0.75 * mult
        elif t == "ZN16":
            out[t] = 1.0 * mult
        else:
            out[t] = REAL[t[2:]] * mult
    return out


def sim3(w, ex_conv="next_close"):
    """net_1x, net_2x, gross excess returns + held gross + gross-weighted average cost (bp)."""
    tick = list(w.columns)
    ohlc = E.load_ohlc(tick, P)
    rf = E.load_rf(P)
    n1, g, to, held, _ = E.simulate(w, ohlc, rf, exec=ex_conv, cost_bps=cmap(tick))
    n2, *_ = E.simulate(w, ohlc, rf, exec=ex_conv, cost_bps=cmap(tick, 2.0))
    rfa = rf.reindex(n1.index).ffill().fillna(0.0)
    df = pd.DataFrame({"net_1x": n1 - rfa, "net_2x": n2 - rfa, "gross": g - rfa})
    gr = held.abs().sum(axis=1)
    c = pd.Series(cmap(tick))
    avgc = float((held.abs() * c).sum().sum() / max(held.abs().sum().sum(), 1e-12))
    return df, gr, avgc, float(to.sum() / (len(to) / 252))


def month_end_dec(idx):
    return F2._month_ends(idx)


def scale_stream(df, gr, avgc, target=0.10, cap=4.0):
    """Sleeve scaler of SPEC s.2: k_d = min(cap, target/sigma_252) at month-ends, applied from d+2."""
    base = df["net_1x"]
    k_dec = pd.Series(np.nan, index=df.index)
    for d in month_end_dec(df.index):
        h = base.loc[:d].dropna().tail(252)
        if len(h) >= 126 and h.std() > 0:
            k_dec.loc[d] = min(cap, target / (h.std() * math.sqrt(252)))
    k_dec = k_dec.ffill()
    k = k_dec.shift(2)                      # applied to return days from d+2
    live = k.notna()
    k = k.fillna(0.0)
    dk = k.diff().abs().fillna(k.abs())
    out = {}
    for col, mult in (("net_1x", 1.0), ("net_2x", 2.0), ("gross", 0.0)):
        ov = dk * gr.reindex(df.index).fillna(0.0) * avgc * mult / 1e4
        out[col] = (k * df[col] - ov).where(live)
    return pd.DataFrame(out), k


def main():
    res, grs, meta = {}, {}, {}
    # S1 (natively 10% ex-ante)
    w = F2.s1_decisions(P)
    df, gr, avgc, to = sim3(w)
    first = w.abs().sum(axis=1).gt(0).idxmax()
    df = df.loc[df.index >= first]  # returns start once a decision exists (+2 sessions are zero anyway)
    df = df.iloc[2:]
    res["S1"], grs["S1"] = df, gr
    meta["S1"] = {"avg_cost_bp": avgc, "turnover": to, "scaled": False, "start": str(df.index[0].date())}

    # TSMOM_F (forward test 1 benchmark decisions, realistic costs), then sleeve scaler
    from src.strategies import pct
    p = {k: v for k, v in pct.BASE_PARAMS.items() if k != "cost_mult"}
    p.update({"measure": "none", "tickers": F.FUT_TICKERS})
    w = pct.decision_weights(period=P, **p)
    df, gr, avgc, to = sim3(w)
    sdf, k = scale_stream(df, gr, avgc)
    res["TSMOM_F"], grs["TSMOM_F"] = sdf.dropna(how="all"), (gr * k)
    meta["TSMOM_F"] = {"avg_cost_bp": avgc, "turnover_unscaled": to, "scaled": True, "k_median": float(k[k > 0].median())}

    # F2 streams A_F and C_F at realistic costs, then sleeve scaler
    specs = F._stream_specs("F2")
    for lab in ("A_F", "C_F"):
        mod, params, ex_conv, _ = specs[lab]
        w = mod.decision_weights(period=P, **params)
        df, gr, avgc, to = sim3(w, ex_conv)
        sdf, k = scale_stream(df, gr, avgc)
        res[lab], grs[lab] = sdf.dropna(how="all"), (gr * k)
        meta[lab] = {"avg_cost_bp": avgc, "turnover_unscaled": to, "scaled": True, "k_median": float(k[k > 0].median()),
                     "instruments": list(w.columns)}

    # ES_10VOL and S2 at the realistic map (comparators)
    for name, fn, tick in (("ES_10VOL_real", F2.es_sleeve_decisions, ["F_ES"]), ("S2_real", F2.s2_decisions, F2.S1_TICKERS)):
        w = fn(P)
        df, gr, avgc, to = sim3(w)
        first = w.abs().sum(axis=1).gt(0).idxmax()
        df = df.loc[df.index >= first].iloc[2:]
        res[name], grs[name] = df, gr
        meta[name] = {"avg_cost_bp": avgc, "turnover": to}

    # native frozen comparators (forward test 2 costs) and F2
    rf = E.load_rf(P)
    nat = {}
    for name in ("S1", "S2", "S3", "ES_10VOL", "TSMOM_F"):
        r = F2.returns(name, P)
        nat[name] = r - rf.reindex(r.index).ffill().fillna(0.0)
    r = F.returns("F2", P)
    nat["F2"] = r - rf.reindex(r.index).ffill().fillna(0.0)
    # S3 at 2x project costs
    w = F2.s3_decisions(P)
    ohlc = E.load_ohlc(F2.S3_TICKERS, P)
    n2, g3, *_ = E.simulate(w, ohlc, rf, exec="next_open", cost_mult=2.0)
    rfa = rf.reindex(n2.index).ffill().fillna(0.0)
    nat["S3_2x"] = n2 - rfa
    nat["S3_gross"] = g3 - rfa
    nat = pd.DataFrame(nat)

    # F2 scaled to 10% (no gross info for the overlay cost; charged 0 - stated)
    f2 = pd.DataFrame({"net_1x": nat["F2"], "net_2x": nat["F2"], "gross": nat["F2"]})
    sdf, _ = scale_stream(f2, pd.Series(0.0, index=f2.index), 0.0)
    res["F2_scaled"] = sdf.dropna(how="all")

    long = pd.concat({k: v for k, v in res.items()}, axis=1)
    long.to_parquet(OUT / "existing.parquet")
    pd.DataFrame(grs).to_parquet(OUT / "existing_gross.parquet")
    nat.to_parquet(OUT / "comparators_native.parquet")
    (OUT / "existing_meta.json").write_text(json.dumps(meta, indent=2))
    for k, v in res.items():
        is_ = v.loc[:"2024-10-02", "net_1x"].dropna()
        lt = v.loc["2024-10-03":, "net_1x"].dropna()
        sr = lambda x: x.mean() / x.std() * math.sqrt(252)
        print(f"{k:14s} start {is_.index[0].date()} IS {sr(is_):6.3f} later {sr(lt):6.3f} vol {is_.std()*math.sqrt(252):.3f}")
    for c in nat:
        x = nat[c].dropna()
        print(c, round(x.loc[:"2024-10-02"].mean() / x.loc[:"2024-10-02"].std() * 252 ** .5, 3),
              round(x.loc["2024-10-03":].mean() / x.loc["2024-10-03":].std() * 252 ** .5, 3), x.index[0].date())


if __name__ == "__main__":
    main()
