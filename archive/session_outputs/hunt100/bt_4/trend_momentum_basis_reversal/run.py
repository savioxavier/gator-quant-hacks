"""Short-term basis reversal (Rossi-Zhang-Zhu 2025; QuantReturns replication): weekly F1-F2 spread return reversal.
V1 15 commodities 4/4 cross-section, V2 + 4 equity index futures, V3 time series -sign(S) on commodities.
We trade the F_ front total-return index (adaptation). Diagnostic: next-week SPREAD returns of Low4 - High4."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as K  # noqa: E402

SID = "trend_momentum_basis_reversal"
OUT = Path(__file__).resolve().parent
COMM = ["CL", "HO", "RB", "NG", "GC", "SI", "PL", "HG", "ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE"]
EQ = ["ES", "NQ", "RTY", "YM"]
RAW = K.C.DATA_DIR / "databento_raw" / "glbx_ohlcv1d_v01.parquet"
NSIDE = 4


def load_raw(roots):
    raw = pd.read_parquet(RAW)
    raw["root"] = raw["symbol"].str.split(".").str[0]
    raw["rank"] = raw["symbol"].str.split(".").str[2].astype(int)
    raw = raw[raw["root"].isin(roots)].copy()
    raw["date"] = pd.to_datetime(raw["ts_event"]).dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()
    raw = raw[raw["date"].dt.dayofweek < 5]
    return raw


def spread_tables(roots, dec_dates, cal):
    """For each root and weekly decision date t: S(t) = r_F1 - r_F2 over (t_prev, t] with the ids ranked 0/1 at t;
    also the next-week spread return with those ids over (t, t_next] (no lag) and (t+1, t_next+1] (one-day lag)."""
    raw = load_raw(roots)
    S = pd.DataFrame(np.nan, index=dec_dates, columns=[f"F_{r}" for r in roots])
    NX0 = S.copy()
    NX1 = S.copy()
    cal = pd.DatetimeIndex(cal)
    nxt_day = pd.Series(cal[1:].append(pd.DatetimeIndex([cal[-1] + pd.Timedelta(days=1)])), index=cal)
    for r in roots:
        g = raw[raw["root"] == r]
        px = g.drop_duplicates(["date", "instrument_id"], keep="last").pivot(index="date", columns="instrument_id",
                                                                              values="close").sort_index()
        rk = g.drop_duplicates(["date", "rank"], keep="last").pivot(index="date", columns="rank",
                                                                    values="instrument_id").sort_index()
        cme = px.index

        def asof(d):
            i = cme.searchsorted(d, side="right") - 1
            if i < 0:
                return None
            c = cme[i]
            return c if (d - c).days <= 5 else None

        def ret(iid, a, b):
            if a is None or b is None or iid not in px.columns:
                return np.nan
            pa, pb = px.at[a, iid], px.at[b, iid]
            return pb / pa - 1 if (np.isfinite(pa) and np.isfinite(pb) and pa > 0) else np.nan

        for k in range(1, len(dec_dates)):
            t0, t = dec_dates[k - 1], dec_dates[k]
            ct0, ct = asof(t0), asof(t)
            if ct is None or ct not in rk.index:
                continue
            f, s = rk.at[ct, 0], rk.at[ct, 1] if 1 in rk.columns else np.nan
            if not (np.isfinite(f) and np.isfinite(s)):
                continue
            f, s = int(f), int(s)
            S.at[t, f"F_{r}"] = ret(f, ct0, ct) - ret(s, ct0, ct)
            if k + 1 < len(dec_dates):
                tn = dec_dates[k + 1]
                ctn = asof(tn)
                NX0.at[t, f"F_{r}"] = ret(f, ct, ctn) - ret(s, ct, ctn)
                c1, cn1 = asof(nxt_day[t]), asof(nxt_day[tn]) if tn in nxt_day.index else None
                NX1.at[t, f"F_{r}"] = ret(f, c1, cn1) - ret(s, c1, cn1)
    return S, NX0, NX1


def decisions(roots, period, S, mode):
    tick = [f"F_{r}" for r in roots]
    ohlc, rf, ex = K.panel(tick, period)
    vol = K.ewma_vol(ex)
    elig = K.eligibility(ohlc, ex, vol)
    w_dec = pd.DataFrame(np.nan, index=ex.index, columns=tick)
    for t in S.index:
        if t not in ex.index or t > ex.index[-1]:
            continue
        st = S.loc[t, tick]
        el = [c for c in tick if elig.loc[t, c] and np.isfinite(st[c])]
        w = pd.Series(0.0, index=tick)
        if mode == "xs" and len(el) >= 2 * NSIDE:
            srt = st[el].sort_values()
            lo, hi = list(srt.index[:NSIDE]), list(srt.index[-NSIDE:])
            w[lo] = 0.40 / vol.loc[t, lo] / (2 * NSIDE)
            w[hi] = -0.40 / vol.loc[t, hi] / (2 * NSIDE)
        elif mode == "ts" and el:
            w[el] = -np.sign(st[el]) * 0.40 / vol.loc[t, el] / len(el)
        w = K.scale_to_target(w, ex.loc[:t], gross_cap=3.0)
        w_dec.loc[t] = w.values
    return w_dec.ffill().fillna(0.0)


def main():
    cal = K.E.trading_calendar("FWD")
    dec = K.week_ends(cal)
    dec = dec[dec >= pd.Timestamp("2010-06-01")]
    S, NX0, NX1 = spread_tables(COMM + EQ, dec, cal)
    S.to_parquet(OUT / "weekly_spread_S.parquet")
    comm = [f"F_{r}" for r in COMM]
    cover = S[comm].notna().mean().round(3).to_dict()

    sims = {
        "V1": K.run_sim(decisions(COMM, "FWD", S, "xs"), "FWD", "next_close"),
        "V2": K.run_sim(decisions(COMM + EQ, "FWD", S, "xs"), "FWD", "next_close"),
        "V3": K.run_sim(decisions(COMM, "FWD", S, "ts"), "FWD", "next_close"),
    }
    starts = {v: K.first_live(s["held"]) for v, s in sims.items()}
    common = max(starts.values())
    res_own = {v: K.metrics(sims[v], starts[v]) for v in sims}
    res_common = {v: K.metrics(sims[v], common) for v in sims}

    # diagnostic edge test (spread returns, equal weight, gross), V1 universe, decisions up to IS_END / later
    def edge(NX):
        rows = []
        for t in S.index:
            st = S.loc[t, comm].dropna()
            nx = NX.loc[t, comm]
            ok = [c for c in st.index if np.isfinite(nx[c])]
            if len(ok) < 2 * NSIDE:
                continue
            srt = st[ok].sort_values()
            rows.append((t, nx[list(srt.index[:NSIDE])].mean() - nx[list(srt.index[-NSIDE:])].mean()))
        e = pd.Series(dict(rows))
        out = {}
        for lab, a, b in (("is", "2010-01-01", K.IS_END), ("later", K.LATER_START, "2027-01-01")):
            x = e.loc[a:b]
            out[lab] = {"weeks": int(len(x)), "ann_mean": float(x.mean() * 52), "ann_vol": float(x.std() * np.sqrt(52)),
                        "sharpe": float(x.mean() / x.std() * np.sqrt(52)), "t": float(x.mean() / x.std() * np.sqrt(len(x)))}
        return out

    # spread vs outright volatility (front index), weekly, commodities: dilution factor of the front-only adaptation
    ohlc, rf, ex = K.panel(comm, "FWD")
    wk = (1 + ex.fillna(0.0)).groupby(ex.index.to_period("W-FRI")).prod() - 1
    sp_vol = float(NX0[comm].loc[:K.IS_END].std().mean() * np.sqrt(52))
    out_vol = float(wk.loc[:str(K.IS_END.date())].loc["2010-06":].std().mean() * np.sqrt(52))
    # autocorrelation of weekly S (pooled), in-sample
    ac = pd.concat([S[comm].loc[:K.IS_END].stack().rename("s"),
                    S[comm].shift(-1).loc[:K.IS_END].stack().rename("s_next")], axis=1).dropna()
    diag = {"edge_no_lag": edge(NX0), "edge_one_day_lag": edge(NX1),
            "avg_weekly_spread_vol_ann": sp_vol, "avg_weekly_front_vol_ann": out_vol,
            "pooled_weekly_S_autocorr_is": float(ac["s"].corr(ac["s_next"])), "S_coverage_share": cover}
    best = max(sims, key=lambda v: res_common[v]["is_net_sharpe_1x"])
    s_is_w = decisions(COMM, "IS", S.loc[:K.IS_END], "xs")
    s_is = K.run_sim(s_is_w, "IS", "next_close")
    diff = float((s_is["net_1x"] - sims["V1"]["net_1x"].loc[: K.IS_END]).abs().max())
    rules = {
        "V1": "weekly (last session): S=r_F1-r_F2 over the week (same instrument ids, Databento .v.0/.v.1); long F_ front of 4 lowest S, short 4 highest, 0.40/sigma weights, book 10%, gross<=3, next_close; 15 commodities",
        "V2": "V1 rule on 15 commodities + ES NQ RTY YM",
        "V3": "weekly time series on 15 commodities: w=-sign(S)*0.40/sigma/N, book 10%, gross<=3, next_close",
    }
    meta = {"id": SID, "sources": ["https://www.cxoadvisory.com/commodity-futures/commodity-futures-term-structure-reversals",
                                   "https://quantreturns.substack.com/p/when-futures-overreact-a-weekly-edge"]}
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
