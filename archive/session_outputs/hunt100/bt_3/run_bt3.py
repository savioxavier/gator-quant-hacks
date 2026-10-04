"""bt_3: re-backtest four momentum strategies exactly as their SPEC.md files declare.

Run from the repo root:  python <this file> [commodity|basis|fx|sector|all]
Reads only from the repo / data cache; writes only under hunt100/bt_3 and hunt100/series.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as K  # noqa: E402

RAW = Path("<home>/.cache/gqh/databento_raw/glbx_ohlcv1d_v01.parquet")
CONTRACTS = Path("<scratch>/"
                 "scratchpad/edges/carry/contracts.parquet")


# ----------------------------------------------------------------------------------------------- commodity XSMOM

def commodity_xsmom(refs):
    sid = "trend_momentum_commodity_xsmom"
    tk = [f"F_{r}" for r in K.COMM]
    P = K.futures_panel(tk)
    ex, sigma, elig = P["ex"], P["sigma"], P["elig"]
    dates = K.month_ends(P["cal"])
    specs = {"V1_12m_EW": (252, "ew"), "V2_12m_IV": (252, "iv"), "V3_6m_EW": (126, "ew")}
    variants = {}
    for name, (win, wt) in specs.items():
        W = pd.DataFrame(0.0, index=dates, columns=tk)
        for t in dates:
            el = [c for c in tk if bool(elig.loc[t, c])]
            if len(el) < 6:
                continue
            cum = (1 + ex.loc[:t, el].tail(win).fillna(0.0)).prod() - 1
            top, bot = K.rank_pick(cum, 3)
            w = pd.Series(0.0, index=tk)
            if wt == "ew":
                w[top] = 1 / 3
                w[bot] = -1 / 3
            else:
                w[top] = 0.40 / sigma.loc[t, top] / 6
                w[bot] = -0.40 / sigma.loc[t, bot] / 6
            W.loc[t] = K.book(w, ex.loc[:t], gross_cap=3.0).values
        df, turn, held = K.run_sim(W, P["ohlc"], P["rf"], "next_close", K.COST_BPS)
        variants[name] = (df, turn, held)
        print(name, "built", flush=True)
    return sid, variants, None, {}


# ----------------------------------------------------------------------------------------------- basis momentum

def _rank_returns(px: pd.DataFrame, rank: int) -> pd.Series:
    """Within-contract daily returns of the rank-k continuous series (CME dates). See SPEC.md."""
    pk = px[px["rank"] == rank].set_index("date").sort_index()
    by_day_id = px.set_index(["date", "instrument_id"])["close"]
    by_day_id = by_day_id[~by_day_id.index.duplicated(keep="last")]
    dates = pk.index
    prev_dates = pd.Series(dates).shift(1).values
    rets = []
    stats = {"n": 0, "roll": 0, "roll_found": 0, "missing": 0}
    prev_id = None
    for d, pdte, cid, c in zip(dates, prev_dates, pk["instrument_id"], pk["close"]):
        if pd.isna(pdte):
            rets.append(0.0)
            prev_id = cid
            continue
        stats["n"] += 1
        rolled = cid != prev_id
        prev = by_day_id.get((pdte, cid), np.nan)
        if rolled:
            stats["roll"] += 1
        if np.isfinite(prev) and prev > 0 and c > 0:
            rets.append(c / prev - 1.0)
            if rolled:
                stats["roll_found"] += 1
        else:
            rets.append(0.0)
            stats["missing"] += 1
        prev_id = cid
    return pd.Series(rets, index=dates), stats


def _to_nyse(r: pd.Series, cal: pd.DatetimeIndex) -> pd.Series:
    pos = cal.searchsorted(r.index, side="left")
    ok = pos < len(cal)
    comp = (1 + r[ok]).groupby(cal[pos[ok]]).prod() - 1
    first = r.index.min()
    return comp.reindex(cal[cal >= first]).fillna(0.0).reindex(cal)


def basis_returns(cal: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    raw = pd.read_parquet(RAW)
    raw["date"] = pd.to_datetime(raw["ts_event"]).dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()
    raw = raw[raw["date"].dt.dayofweek < 5]
    raw["root"] = raw["symbol"].str.split(".").str[0]
    raw["rank"] = raw["symbol"].str.split(".").str[2].astype(int)
    r1, r2, diag = {}, {}, {}
    for root in K.COMM:
        px = raw[raw["root"] == root][["date", "rank", "instrument_id", "close", "volume"]]
        px = px.drop_duplicates(["date", "rank"], keep="last")
        a, sa = _rank_returns(px, 0)
        b, sb = _rank_returns(px, 1)
        r1[f"F_{root}"] = _to_nyse(a, cal)
        r2[f"F_{root}"] = _to_nyse(b, cal)
        diag[root] = {"r1": sa, "r2": sb}
    return pd.DataFrame(r1), pd.DataFrame(r2), diag


def basis_momentum(refs):
    sid = "trend_momentum_basis_momentum"
    tk = [f"F_{r}" for r in K.COMM]
    P = K.futures_panel(tk)
    ex, sigma, elig, cal = P["ex"], P["sigma"], P["elig"], P["cal"]
    r1, r2, rdiag = basis_returns(cal)
    # sanity: r1 should reproduce the F_ index excess return (same builder logic on rank 0)
    fx_ex = ex.add(P["rf"], axis=0)
    chk = {c: float(pd.concat([r1[c], fx_ex[c]], axis=1).dropna().corr().iloc[0, 1]) for c in tk}
    dates = K.month_ends(cal)
    bm = pd.DataFrame(np.nan, index=dates, columns=tk)
    for t in dates:
        a = (1 + r1.loc[:t].tail(252)).prod()
        b = (1 + r2.loc[:t].tail(252)).prod()
        n_obs = r1.loc[:t].notna().sum()
        v = a - b
        v[n_obs < 252] = np.nan
        bm.loc[t] = v.values
    bm.to_parquet(Path(__file__).resolve().parent / sid / "bm_signal.parquet")
    specs = {"V1_H4L4_EW": "ew", "V2_H4L4_IV": "iv", "V3_TS_sign": "ts"}
    variants = {}
    for name, wt in specs.items():
        W = pd.DataFrame(0.0, index=dates, columns=tk)
        for t in dates:
            el = [c for c in tk if bool(elig.loc[t, c]) and np.isfinite(bm.loc[t, c])]
            w = pd.Series(0.0, index=tk)
            if wt in ("ew", "iv"):
                if len(el) < 8:
                    continue
                top, bot = K.rank_pick(bm.loc[t, el], 4)
                if wt == "ew":
                    w[top] = 0.25
                    w[bot] = -0.25
                else:
                    w[top] = 0.40 / sigma.loc[t, top] / 8
                    w[bot] = -0.40 / sigma.loc[t, bot] / 8
            else:
                if not el:
                    continue
                s = np.sign(bm.loc[t, el].astype(float))
                w[el] = s * 0.40 / sigma.loc[t, el] / len(el)
            W.loc[t] = K.book(w, ex.loc[:t], gross_cap=3.0).values
        df, turn, held = K.run_sim(W, P["ohlc"], P["rf"], "next_close", K.COST_BPS)
        variants[name] = (df, turn, held)
        print(name, "built", flush=True)
    # diagnostic: share of days on which .v.1 expires before .v.0 (volume-rank inversion)
    c = pd.read_parquet(CONTRACTS)
    c = c[c["root"].isin(K.COMM)]
    p = c.pivot_table(index=["root", "date"], columns="rank", values="month_index", aggfunc="first").dropna()
    inv = (p[1] < p[0]).groupby(level=0).mean()
    gap = (p[1] - p[0]).groupby(level=0).median()
    extra = {"r1_vs_F_index_corr": chk, "share_days_v1_expires_before_v0": inv.round(4).to_dict(),
             "median_month_gap_v1_minus_v0": gap.to_dict(),
             "roll_stats": rdiag,
             "mean_abs_bm_cross_section": float(bm.abs().mean(axis=1).mean())}
    return sid, variants, None, extra


# ----------------------------------------------------------------------------------------------- FX XSMOM

def fx_xsmom(refs):
    sid = "trend_momentum_fx_xsmom"
    tk = [f"F_{r}" for r in K.FX]
    P = K.futures_panel(tk)
    ex, sigma, elig = P["ex"], P["sigma"], P["elig"]
    dates = K.month_ends(P["cal"])
    specs = {"V1_1m": 21, "V2_3m": 63, "V3_12m": 252}
    variants = {}
    for name, win in specs.items():
        W = pd.DataFrame(0.0, index=dates, columns=tk)
        for t in dates:
            el = [c for c in tk if bool(elig.loc[t, c])]
            if len(el) < 4:
                continue
            cum = (1 + ex.loc[:t, el].tail(win).fillna(0.0)).prod() - 1
            top, bot = K.rank_pick(cum, 2)
            w = pd.Series(0.0, index=tk)
            w[top] = 0.40 / sigma.loc[t, top] / 4
            w[bot] = -0.40 / sigma.loc[t, bot] / 4
            W.loc[t] = K.book(w, ex.loc[:t], gross_cap=3.0).values
        df, turn, held = K.run_sim(W, P["ohlc"], P["rf"], "next_close", K.COST_BPS)
        variants[name] = (df, turn, held)
        print(name, "built", flush=True)
    return sid, variants, None, {}


# ----------------------------------------------------------------------------------------------- sector RS

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]


def sector_rs(refs):
    sid = "trend_momentum_sector_rs"
    P = K.etf_panel(SECTORS + ["SPY"])
    close, ex, cal = P["ohlc"]["close"], P["ex"], P["cal"]
    me = K.month_ends(cal)
    mclose = close.loc[me]
    variants = {}
    W = {n: pd.DataFrame(0.0, index=me, columns=SECTORS) for n in ("V1_top3", "V2_top3_SMA10", "V3_top3_minus_bot3")}
    ew = pd.DataFrame(0.0, index=me, columns=SECTORS)
    filt_log = []
    for m, t in enumerate(me):
        if m < 12:
            continue
        sc = pd.Series(0.0, index=SECTORS)
        for k in (1, 3, 6, 9, 12):
            sc += mclose.iloc[m][SECTORS] / mclose.iloc[m - k][SECTORS] - 1
        sc /= 5
        if sc.isna().any():
            continue
        top, bot = K.rank_pick(sc, 3)
        w1 = pd.Series(0.0, index=SECTORS)
        w1[top] = 1 / 3
        W["V1_top3"].loc[t] = w1.values
        spy_sma = mclose["SPY"].iloc[m - 9:m + 1].mean()
        risk_on = bool(mclose["SPY"].iloc[m] >= spy_sma)
        filt_log.append((t, risk_on))
        W["V2_top3_SMA10"].loc[t] = (w1 if risk_on else w1 * 0.0).values
        w3 = pd.Series(0.0, index=SECTORS)
        w3[top] = 1 / 3
        w3[bot] = -1 / 3
        W["V3_top3_minus_bot3"].loc[t] = K.book(w3, ex.loc[:t, SECTORS], gross_cap=2.0).values
        ew.loc[t] = 1 / 9
    for name, w in W.items():
        df, turn, held = K.run_sim(w, P["ohlc"], P["rf"], "next_open", None)
        variants[name] = (df, turn, held)
        print(name, "built", flush=True)
    # diagnostics (not variants): equal-weight 9-sector basket and SPY buy-and-hold on the same machinery
    ew_df, ew_turn, _ = K.run_sim(ew, P["ohlc"], P["rf"], "next_open", None)
    spy_w = pd.DataFrame(0.0, index=me, columns=["SPY"])
    spy_w.loc[me[12]:] = 1.0
    spy_df, _, _ = K.run_sim(spy_w, P["ohlc"], P["rf"], "next_open", None)
    fl = pd.Series(dict(filt_log))
    extra = {"diag_frames": {"EW9": ew_df, "SPY": spy_df},
             "risk_off_share_IS": float((~fl.loc[:K.IS_END]).mean()),
             "risk_off_share_LATER": float((~fl.loc[K.LATER_START:]).mean()) if len(fl.loc[K.LATER_START:]) else None}
    return sid, variants, ["V1_top3", "V3_top3_minus_bot3"], extra


# ----------------------------------------------------------------------------------------------- driver

SIDECAR = {
    "trend_momentum_commodity_xsmom": {
        "rule": "Month-end, 15 CME commodities: rank on cumulative excess return of the F_ index over the formation "
                "window (no skip); long top 3, short bottom 3; V1 12m equal notional, V2 12m 1/sigma (equal risk), "
                "V3 6m equal notional; book to 10% ex-ante (252d cov, gross<=3); hold one month; next_close.",
        "sources": ["https://risk.edhec.edu/publications/momentum-strategies-commodity-futures",
                    "Hollstein, Prokopczuk & Tharann 2021, QJF 11(4), SSRN 3567629",
                    "https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Value-and-Momentum-Everywhere-Factors-Monthly.xlsx",
                    "https://ideas.repec.org/a/eme/rbfpps/rbf-05-2019-0067.html"],
        "universe": [f"F_{r}" for r in K.COMM],
    },
    "trend_momentum_basis_momentum": {
        "rule": "Month-end, 15 CME commodities: BM = prod(1+r1) - prod(1+r2) over 252 sessions, r1/r2 = within-"
                "contract daily returns of Databento .v.0/.v.1 (roll day: new contract's own previous close, else 0); "
                "V1 High4-Low4 equal notional, V2 High4-Low4 1/sigma, V3 time-series sign(BM) risk units; positions in "
                "the F_ index; book to 10% (252d cov, gross<=3); next_close.",
        "sources": ["https://ideas.repec.org/a/bla/jfinan/v74y2019i1p239-279.html",
                    "https://4nations.albertjmenkveld.com/papers/boonsprado17.pdf"],
        "universe": [f"F_{r}" for r in K.COMM],
    },
    "trend_momentum_fx_xsmom": {
        "rule": "Month-end, 6 FX futures: rank on cumulative excess return over 21 (V1) / 63 (V2) / 252 (V3) sessions; "
                "long top 2, short bottom 2, equal risk 1/sigma; book to 10% (252d cov, gross<=3); next_close.",
        "sources": ["https://www.bis.org/publ/work366.pdf",
                    "https://www.cxoadvisory.com/momentum-investing/momentum-investing-for-currencies",
                    "https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Value-and-Momentum-Everywhere-Factors-Monthly.xlsx"],
        "universe": [f"F_{r}" for r in K.FX],
    },
    "trend_momentum_sector_rs": {
        "rule": "Month-end, 9 SPDR sector ETFs: score = mean of 1/3/6/9/12-month returns on month-end adjusted closes; "
                "V1 long top 3 at 1/3 (natural sizing); V2 V1 but T-bills when SPY month-end close < 10-month SMA; V3 top 3 "
                "minus bottom 3, book to 10% (252d cov, gross<=2), short borrow 30 bp/yr; next_open; ETF cost map (5 bp).",
        "sources": ["https://c.mql5.com/forextsd/forum/213/Relative%20Strength%20Strategies%20for%20Investing.pdf",
                    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/10_Industry_Portfolios_CSV.zip"],
        "universe": SECTORS,
    },
}

FUNCS = {"commodity": commodity_xsmom, "basis": basis_momentum, "fx": fx_xsmom, "sector": sector_rs}


def main(which: list[str]) -> None:
    refs = K.references()
    for w in which:
        sid, variants, start_keys, extra = FUNCS[w](refs)
        folder = K.HERE / sid
        start, table, full = K.evaluate(variants, refs, start_keys)
        side = dict(SIDECAR[sid])
        cost = {t: K.COST_BPS.get(t) for t in side["universe"]} if w != "sector" else "config.cost_bps (sector SPDRs 5 bp)"
        side["cost_bps_one_way"] = cost
        side["vol_scaling"] = ("10% annualised ex-ante, trailing 252-session sample covariance (min 60), gross cap 3"
                               if w != "sector" else "V1/V2 natural (100% invested); V3 10% ex-ante, gross cap 2")
        head = K.save_outputs(sid, folder, variants, start, table, full, side)
        diag = {}
        if "diag_frames" in extra:
            for dn, ddf in extra.pop("diag_frames").items():
                d = ddf.loc[start:]
                diag[dn] = {wn: {"sharpe_net_1x": K.sharpe(x["net_1x"]), "ann_return": float(x["net_1x"].mean() * 252),
                                 "ann_vol": float(x["net_1x"].std() * np.sqrt(252)), "max_dd": K.max_dd(x["net_1x"])}
                            for wn, x in (("IS", d.loc[:K.IS_END]), ("LATER", d.loc[K.LATER_START:]))}
                # relative: headline minus diagnostic
                hv = variants[head][0].loc[start:]
                rel = hv["net_1x"] - d["net_1x"]
                diag[dn]["headline_minus_this_IS_sharpe"] = K.sharpe(rel.loc[:K.IS_END])
                diag[dn]["headline_minus_this_LATER_sharpe"] = K.sharpe(rel.loc[K.LATER_START:])
        extra["diagnostics"] = diag
        (folder / "extra.json").write_text(json.dumps(extra, indent=2, default=str))
        cols = ["variant", "window", "start", "end", "sharpe_net_1x", "sharpe_net_2x", "sharpe_gross", "ann_return",
                "ann_vol", "max_dd", "worst_year", "pct_pos_years", "roll2y_p10", "turnover_per_year", "nw_t",
                "corr_ES", "corr_S1", "corr_F2"]
        print("=" * 100)
        print(sid, "common start", start.date(), "headline", head)
        with pd.option_context("display.width", 250, "display.max_columns", 30, "display.float_format", "{:.3f}".format):
            print(table[cols].to_string(index=False))
        if diag:
            print(json.dumps(diag, indent=1, default=float))


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    main(list(FUNCS) if arg == "all" else arg.split(","))
