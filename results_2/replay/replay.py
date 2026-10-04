"""Saved-result replay: recompute the headline tables and figures from committed derived artifacts only.

    python results_2/replay/replay.py [--out results_2/replay/replay_out]

Run from the repository root of a checkout (no licensed data, no market data, no price levels, no network, no
strategy is re-run). Every item recomputes numbers from committed daily series, per-trade rows or per-answer rows and
compares them with the committed tables. It prints PASS or FAIL per item and exits

  0  every item passed;
  1  at least one recomputed number differs from its committed value beyond the item's tolerance;
  2  at least one input is missing (named on stderr).

Items:
  v2_oos_metrics          backtests/results/v2_oos/metrics.csv, every row, from the frozen D-3 run's daily files
  v2_is_selection         the selection table (backtests/results/v2/windows_all.csv net 1x columns, selection.csv,
                          the chosen combination) from the in-sample daily excess returns of the ten combinations
  v2_d4_metrics           backtests/results/v2_d4/metrics.csv, every row, from its daily_returns.parquet
  presser_strategy        backtests/results/presser_strategy/metrics.csv and sizing.csv from per_trade.csv and the
                          trading calendar of daily_returns.csv
  presser_g3_headline     the G3 confirmation sample (backtests/results/presser_h1/key_results.json) from
                          h1primary_trades.csv
  h234_family_holm        backtests/presser/backtest_h234/results/family_holm.json and the H4 frozen-fit block of
                          h4_results.json from h4_answer_rows.csv and answer_summary.csv
  results_2_v2_metrics    results_2/metrics/v2_metrics.csv, recomputed by results_2/metrics/compute_metrics.py
Figures (written, not compared pixel by pixel): v2 and portfolio equity curves, press-conference ZT equity curves.

What cannot be recomputed from committed files is listed per item as SKIP with the reason (the D-4 portfolio's
v2-sleeve multiplier path, contract notionals that need index levels, answer-level P&L that needs prices); a SKIP is
not a pass of that number. Outputs go to --out only; writing into a frozen folder is refused.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.cwd()
HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True                       # leave no cache files in the working tree
sys.path.insert(0, str(HERE.parent / "metrics"))
import compute_metrics as CM  # noqa: E402

ANN = 252
FROZEN_PREFIXES = ("backtests/", "preregistration/", "hpg/", "data/", "archive/", "backtest_snapshot/",
                   "results_2/metrics/")


class Missing(Exception):
    pass


def need(*paths: str) -> list[Path]:
    miss = [p for p in paths if not (ROOT / p).is_file()]
    if miss:
        for p in miss:
            print(f"MISSING INPUT: {p}", file=sys.stderr)
        raise Missing(", ".join(miss))
    return [ROOT / p for p in paths]


class Cmp:
    """Collects comparisons of recomputed and committed values."""

    def __init__(self, abs_tol: float, rel_tol: float = 0.0):
        self.abs_tol, self.rel_tol = abs_tol, rel_tol
        self.n, self.worst, self.worst_rel, self.bad, self.skips = 0, 0.0, 0.0, [], []

    def eq(self, key: str, ours, theirs) -> None:
        self.n += 1
        if isinstance(ours, str) or isinstance(theirs, str) or ours is None or theirs is None:
            if str(ours) != str(theirs):
                self.bad.append((key, str(ours), str(theirs)))
            return
        o, t = float(ours), float(theirs)
        ours, theirs = o, t
        if math.isnan(o) and math.isnan(t):
            return
        d = abs(o - t)
        if not math.isfinite(d):
            self.bad.append((key, ours, theirs))
            return
        self.worst = max(self.worst, d)
        if t != 0.0:
            self.worst_rel = max(self.worst_rel, d / abs(t))
        if d > self.abs_tol + self.rel_tol * abs(t):
            self.bad.append((key, ours, theirs))

    def skip(self, what: str, why: str) -> None:
        self.skips.append({"what": what, "why": why})


def nw_t(x) -> float:
    return CM.newey_west_t(x)[0]


# ----------------------------------------------------------------------------- v2, D-3 (frozen) metrics
D3_RUN = "backtests/results/v2_oos/run"
WINDOWS = CM.WINDOWS
BASES = ("net_1x", "net_2x", "gross")


def load_d3() -> dict:
    t4, va, pf = need(f"{D3_RUN}/daily_T4xE1_full.parquet", f"{D3_RUN}/daily_VariantA_frozen_T0fxE1_full.parquet",
                      f"{D3_RUN}/daily_portfolio_full.parquet")
    out = {}
    for name, f in (("T4xE1", t4), ("VariantA_frozen(T0fxE1)", va)):
        s = pd.read_parquet(f)
        first = s.index[s["gross_exposure"] > 0][0]
        out[name] = pd.DataFrame({"net_1x": s["ex1"], "net_2x": s["ex2"], "gross": s["exg"],
                                  "turnover": s["turnover"], "rf": s["rf"]}).loc[first:]
    rf = out["T4xE1"]["rf"]
    p = pd.read_parquet(pf)
    for name in ("core_ER_6", "core_ER_6+T4xE1"):
        df = pd.DataFrame({b: p[f"{name}|{b}"] for b in BASES})
        df["turnover"] = p[f"{name}|overlay_turnover"]
        df = df.dropna(subset=["net_1x"])
        if name != "core_ER_6":
            m = p[f"{name}|m_FED_T4xE1"].reindex(df.index).fillna(0.0)
            df["fed_turnover"] = m * out["T4xE1"]["turnover"].reindex(df.index).fillna(0.0)
        df["rf"] = rf.reindex(df.index.union(rf.index)).sort_index().ffill().reindex(df.index).fillna(0.0)
        out[name] = df
    return out


def d3_row(df: pd.DataFrame, basis: str, a: str, b: str) -> dict:
    x = df[basis].loc[a:b].dropna()
    yrs = len(x) / ANN
    rf = df["rf"].reindex(x.index).fillna(0.0)
    row = {"start": str(x.index[0].date()), "end": str(x.index[-1].date()), "n_days": int(len(x)),
           "ann_return_arith": float(x.mean() * ANN), "ann_return_geo": float((1 + x).prod() ** (1 / yrs) - 1),
           "ann_total_return_geo": float((1 + x + rf).prod() ** (1 / yrs) - 1),
           "ann_vol": float(x.std(ddof=1) * math.sqrt(ANN)), "sharpe": CM.sharpe(x.to_numpy()),
           "max_drawdown": CM.max_dd_from_first_close(x.to_numpy()), "hit_rate": float((x > 0).mean()),
           "turnover_per_year": float(df["turnover"].loc[x.index].sum() / yrs), "nw_t": nw_t(x.to_numpy())}
    if "fed_turnover" in df:
        row["fed_sleeve_turnover_per_year"] = float(df["fed_turnover"].loc[x.index].sum() / yrs)
    return row


def item_v2_oos_metrics(out: Path) -> Cmp:
    (mpath, dpath) = need("backtests/results/v2_oos/metrics.csv", "backtests/results/v2_oos/daily_returns.parquet")
    ser = load_d3()
    rows = [{"series": n, "window": w, "basis": b, **d3_row(df, b, a, e)}
            for n, df in ser.items() for w, a, e in WINDOWS for b in BASES]
    ours = pd.DataFrame(rows)
    ours.to_csv(out / "v2_oos_metrics_replay.csv", index=False, float_format="%.15g")
    com = pd.read_csv(mpath)
    c = Cmp(1e-9)
    keys = ["series", "window", "basis"]
    o, t = ours.set_index(keys), com.set_index(keys)
    c.eq("row set", ",".join(sorted("|".join(k) for k in o.index)), ",".join(sorted("|".join(k) for k in t.index)))
    for k in t.index.intersection(o.index):
        for col in t.columns:
            if col == "fed_sleeve_turnover_per_year" and pd.isna(t.loc[k, col]):
                continue
            c.eq(f"{'|'.join(k)}|{col}", o.loc[k, col], t.loc[k, col])
    # the published daily file is the same series
    d = pd.read_parquet(dpath)
    for n in ser:
        for b in BASES:
            x = ser[n][b].reindex(d.index)
            c.eq(f"daily {n}|{b} vs daily_returns.parquet", float((x - d[f"{n}|{b}"]).abs().max()), 0.0)
    return c


# ----------------------------------------------------------------------------- v2, in-sample selection table
def item_v2_is_selection(out: Path) -> Cmp:
    dpath, wpath, spath = need(f"{D3_RUN}/daily_excess_all_combos_is.parquet", "backtests/results/v2/windows_all.csv",
                               "backtests/results/v2/selection.csv")
    d = pd.read_parquet(dpath)
    wa = pd.read_csv(wpath).set_index(["combo", "window"])
    sel = pd.read_csv(spath).set_index("combo")
    c = Cmp(1e-9)
    rows = []
    for combo in d.columns:
        for wn, a, b in WINDOWS[:3]:
            x = d[combo].loc[a:b].dropna()
            yrs = len(x) / ANN
            rows.append({"combo": combo, "window": wn, "start": str(x.index[0].date()),
                         "end": str(x.index[-1].date()), "n_days": len(x),
                         "sharpe_net1x": CM.sharpe(x.to_numpy()), "ann_excess_arith": float(x.mean() * ANN),
                         "ann_excess_geo": float((1 + x).prod() ** (1 / yrs) - 1),
                         "vol": float(x.std(ddof=1) * math.sqrt(ANN)),
                         "max_dd_excess": CM.max_dd_from_first_close(x.to_numpy()), "nw_t": nw_t(x.to_numpy())})
    ours = pd.DataFrame(rows)
    cand = [k for k in sel.index]                                  # the eight registered combinations
    s = ours[(ours.window == "selection") & ours.combo.isin(cand)].set_index("combo")["sharpe_net1x"]
    chosen = s.idxmax()
    ours["chosen"] = ours.combo == chosen
    ours.to_csv(out / "v2_is_windows_replay.csv", index=False, float_format="%.15g")
    for r in ours.itertuples():
        k = (r.combo, r.window)
        for col in ("start", "end", "n_days", "sharpe_net1x", "ann_excess_arith", "ann_excess_geo", "vol",
                    "max_dd_excess", "nw_t"):
            c.eq(f"{r.combo}|{r.window}|{col}", getattr(r, col), wa.loc[k, col])
        c.eq(f"{r.combo}|{r.window}|chosen", bool(r.chosen), bool(wa.loc[k, "chosen"]))
    for combo in cand:
        c.eq(f"selection.csv {combo} sharpe_net1x", s[combo], sel.loc[combo, "sharpe_net1x"])
    c.eq("chosen combination", chosen, "T4xE1")
    c.skip("windows_all.csv net 2x, gross and turnover columns",
           "the committed all-combination in-sample daily file holds net 1x excess returns only")
    return c


# ----------------------------------------------------------------------------- v2, D-4 metrics
D4_GROUP = {"T4xE1": "strategy", "T0fxE1": "strategy", "LEXALLxE1": "matched_benchmark",
            "T2xE1": "matched_benchmark", "T0v2xE1": "matched_benchmark", "MxE1": "simple_benchmark",
            "BH7525volxE1": "simple_benchmark", "BH7525hold": "simple_benchmark", "core_ER_6": "portfolio",
            "core_ER_6+T4xE1": "portfolio"}
WF_WINDOWS = [("wf_is", "2021-01-01", "2024-10-02"), ("oos", "2024-10-03", "2026-10-02"),
              ("wf_all", "2021-01-01", "2026-10-02")]


def d4_row(d: pd.DataFrame, prefix: str, a: str, b: str) -> dict:
    x1 = d[f"{prefix}|net_1x"].loc[a:b].dropna()
    x2 = d[f"{prefix}|net_2x"].loc[a:b].dropna()
    xg = d[f"{prefix}|gross"].loc[a:b].dropna()
    tv = d[f"{prefix}|turnover"].fillna(0.0).loc[x1.index]
    yrs = len(x1) / ANN
    return {"start": str(x1.index[0].date()), "end": str(x1.index[-1].date()), "n_days": int(len(x1)),
            "ann_excess_arith": float(x1.mean() * ANN), "ann_excess_geo": float((1 + x1).prod() ** (1 / yrs) - 1),
            "vol": float(x1.std(ddof=1) * math.sqrt(ANN)), "sharpe_net1x": CM.sharpe(x1.to_numpy()),
            "sharpe_net2x": CM.sharpe(x2.to_numpy()), "sharpe_gross": CM.sharpe(xg.to_numpy()),
            "max_dd_excess": CM.max_dd_from_first_close(x1.to_numpy()), "turnover_per_year": float(tv.sum() / yrs),
            "nw_t": nw_t(x1.to_numpy())}


def item_v2_d4_metrics(out: Path) -> Cmp:
    dpath, mpath = need("backtests/results/v2_d4/daily_returns.parquet", "backtests/results/v2_d4/metrics.csv")
    d = pd.read_parquet(dpath)
    prefixes = sorted({c.rsplit("|", 1)[0] for c in d.columns if c != "window"})
    rows = []
    for p in prefixes:
        series, variant = p.split("|")
        if series == "WF_max_trailing_sharpe":
            for wn, a, b in WF_WINDOWS:
                rows.append({"group": "walk_forward", "series": series, "variant": variant, "window": wn,
                             **d4_row(d, p, a, b)})
            continue
        for wn, a, b in WINDOWS:
            rows.append({"group": D4_GROUP[series], "series": series, "variant": variant, "window": wn,
                         **d4_row(d, p, a, b)})
        if series == "T4xE1" and variant in ("original", "both"):
            for wn, a, b in WF_WINDOWS:
                rows.append({"group": "walk_forward", "series": "T4xE1_registered_choice", "variant": variant,
                             "window": wn, **d4_row(d, p, a, b)})
    ours = pd.DataFrame(rows)
    # the original portfolio's v2-sleeve turnover from the frozen D-3 multiplier path
    ser = load_d3()
    fed = ser["core_ER_6+T4xE1"]
    for i, r in ours[(ours.series == "core_ER_6+T4xE1") & (ours.variant == "original")].iterrows():
        idx = fed["net_1x"].loc[r.start:r.end].dropna().index
        ours.loc[i, "fed_sleeve_turnover_per_year"] = float(fed["fed_turnover"].loc[idx].sum() / (len(idx) / ANN))
    ours.to_csv(out / "v2_d4_metrics_replay.csv", index=False, float_format="%.15g")
    com = pd.read_csv(mpath)
    keys = ["group", "series", "variant", "window"]
    o, t = ours.set_index(keys), com.set_index(keys)
    c = Cmp(1e-9)
    c.eq("row set", ",".join(sorted("|".join(k) for k in o.index)), ",".join(sorted("|".join(k) for k in t.index)))
    for k in t.index.intersection(o.index):
        for col in t.columns:
            if col == "fed_sleeve_turnover_per_year":
                if pd.isna(t.loc[k, col]):
                    continue
                if k[2] != "original":
                    continue
            c.eq(f"{'|'.join(k)}|{col}", o.loc[k, col], t.loc[k, col])
    c.skip("fed_sleeve_turnover_per_year of the fix1 / fix2 / both portfolio rows (12 values)",
           "the D-4 portfolio's T4xE1 multiplier path is not a committed file; the original rows are recomputed")
    return c


# ----------------------------------------------------------------------------- press-conference strategy series
PS = "backtests/results/presser_strategy"
CAPITAL, TARGET_VOL = 10_000_000.0, 0.10
IS_END, OOS_START, OOS_END = pd.Timestamp("2024-10-02"), pd.Timestamp("2024-10-03"), pd.Timestamp("2026-10-02")
FACE = {"ZT": 200_000.0, "ZF": 100_000.0, "ZN": 100_000.0}          # CME contract face values (no prices)
PS_WINDOWS = {
    "H1-primary": [("IS", None, IS_END, "headline"), ("OOS", OOS_START, OOS_END, "headline"),
                   ("IS: 2016-2022 sample (D1 clean)", None, pd.Timestamp("2022-12-31"), "sub-window"),
                   ("G3 confirmation sample 2023-02-01..2026-04-29", pd.Timestamp("2023-02-01"),
                    pd.Timestamp("2026-04-29"), "sub-window")],
    "BENCH-R": [("IS", None, IS_END, "headline"), ("OOS", OOS_START, OOS_END, "headline"),
                ("IS: era 2016-2019", None, pd.Timestamp("2019-12-31"), "sub-window"),
                ("IS: era 2020-2024-10-02", pd.Timestamp("2020-01-01"), IS_END, "sub-window")],
}
PS_COSTS = ["gross", "net1x", "net2x", "fixed1x", "fixed2x"]


def presser_drawdown(r: np.ndarray) -> tuple[float, float]:
    eq = 1.0 + np.cumsum(r)
    peak = np.maximum.accumulate(np.r_[1.0, eq])[1:]
    return float((eq / peak - 1.0).min()), float((peak - eq).max() * CAPITAL)


def presser_metrics() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tpath, dpath = need(f"{PS}/per_trade.csv", f"{PS}/daily_returns.csv")
    T = pd.read_csv(tpath)
    T["date_ts"] = pd.to_datetime(T["date"])
    # per-contract P&L rebuilt from its exact components (ticks, $ per tick, half-spreads, fees), as the builder
    # does; the *_usd columns of per_trade.csv are rounded to 6 significant digits and are checked against these
    T["csv_usd"] = [dict(zip(PS_COSTS, v)) for v in T[[f"{c}_usd" for c in PS_COSTS]].to_numpy()]
    gross = T.gross_ticks * T.usd_per_tick
    cost1 = T.spread_cost_ticks * T.usd_per_tick + T.fee_usd
    T["gross_usd"], T["net1x_usd"], T["net2x_usd"] = gross, gross - cost1, gross - 2 * cost1
    T["fixed1x_usd"] = gross - 4 * T.usd_per_tick - T.fee_usd
    T["fixed2x_usd"] = gross - 8 * T.usd_per_tick - 2 * T.fee_usd
    D = pd.read_csv(dpath, parse_dates=["date"])
    CAL = pd.DatetimeIndex(sorted(D["date"].unique()))
    first_trade = T.groupby("strategy").date_ts.min()
    # sizing on the in-sample gross series of one contract
    size, N = [], {}
    for (st, s), g in T.groupby(["strategy", "sym"]):
        days = CAL[(CAL >= first_trade[st]) & (CAL <= IS_END)]
        pnl = g[g.window == "IS"].groupby("date_ts").gross_usd.sum().reindex(days, fill_value=0.0)
        vol1 = (pnl / CAPITAL).std(ddof=1) * np.sqrt(ANN)
        N[(st, s)] = max(1, int(round(TARGET_VOL / vol1)))
        size.append({"strategy": st, "sym": s, "is_days": len(days), "is_ann_vol_one_contract": vol1,
                     "N_exact": TARGET_VOL / vol1, "N": N[(st, s)], "is_ann_vol_with_N": vol1 * N[(st, s)]})
    met, daily = [], []
    for st, wins in PS_WINDOWS.items():
        for s in ["ZT", "ZF", "ZN", "ES"]:
            g_all = T[(T.strategy == st) & (T.sym == s)]
            n_c = N[(st, s)]
            for vname in ("all", "ex_warsh"):
                g = g_all if vname == "all" else g_all[g_all.chair != "Warsh"]
                if vname != "all" and len(g) == len(g_all):
                    continue
                for wname, w0, w1, role in wins:
                    w0 = first_trade[st] if w0 is None else w0
                    days = CAL[(CAL >= w0) & (CAL <= w1)]
                    gw = g[(g.date_ts >= w0) & (g.date_ts <= w1)]
                    if vname != "all" and len(gw) == ((g_all.date_ts >= w0) & (g_all.date_ts <= w1)).sum():
                        continue
                    years = len(days) / ANN
                    for cst in PS_COSTS:
                        pnl = (gw[f"{cst}_usd"] * n_c).groupby(gw.date_ts).sum().reindex(days, fill_value=0.0)
                        r = (pnl / CAPITAL).to_numpy()
                        mu, sd = r.mean(), r.std(ddof=1)
                        pt = gw[f"{cst}_usd"].to_numpy()
                        n = len(pt)
                        mdd, mdd_usd = presser_drawdown(r)
                        pts = pt.mean() / pt.std(ddof=1) if n > 1 and pt.std(ddof=1) > 0 else np.nan
                        row = dict(strategy=st, sym=s, variant=vname, window=wname, role=role, cost=cst,
                                   start=str(days.min().date()), end=str(days.max().date()), trading_days=len(days),
                                   years=years, N_contracts=n_c, n_trades=n, ann_return=mu * ANN,
                                   ann_vol=sd * np.sqrt(ANN), sharpe=(mu / sd * np.sqrt(ANN)) if sd > 0 else np.nan,
                                   max_drawdown=mdd, max_drawdown_usd=mdd_usd, total_return=r.sum(),
                                   total_pnl_usd=pnl.sum(), mean_trade_usd_per_contract=pt.mean() if n else np.nan,
                                   sd_trade_usd_per_contract=pt.std(ddof=1) if n > 1 else np.nan,
                                   per_trade_sharpe=pts,
                                   per_trade_sharpe_annualised=pts * np.sqrt(n / years) if n > 1 else np.nan,
                                   t_stat_trades=pts * np.sqrt(n) if n > 1 else np.nan,
                                   hit_rate=(pt > 0).mean() if n else np.nan,
                                   zero_share=(pt == 0).mean() if n else np.nan, trades_per_year=n / years,
                                   contracts_per_year=2 * n_c * n / years)
                        if s in FACE:
                            row["notional_per_year_usd"] = 2 * n_c * FACE[s] * n / years
                            row["turnover_x_capital_per_year"] = row["notional_per_year_usd"] / CAPITAL
                            row["notional_per_trade_x_capital"] = n_c * FACE[s] / CAPITAL if n else np.nan
                        met.append(row)
            days = CAL[(CAL >= first_trade[st]) & (CAL <= OOS_END)]
            dd = pd.DataFrame({"strategy": st, "sym": s, "date": days})
            for cst in ("gross", "net1x", "net2x"):
                dd[f"ret_{cst}"] = ((g_all[f"{cst}_usd"] * n_c).groupby(g_all.date_ts).sum()
                                    .reindex(days, fill_value=0.0) / CAPITAL).to_numpy()
            daily.append(dd)
    return pd.DataFrame(met), pd.DataFrame(size), pd.concat(daily, ignore_index=True), D, T


def item_presser_strategy(out: Path) -> Cmp:
    mpath, spath = need(f"{PS}/metrics.csv", f"{PS}/sizing.csv")
    ours, size, daily, D, T = presser_metrics()
    ours.to_csv(out / "presser_strategy_metrics_replay.csv", index=False, float_format="%.10g")
    size.to_csv(out / "presser_sizing_replay.csv", index=False, float_format="%.10g")
    c = Cmp(1e-9, 6e-6)            # metrics.csv and sizing.csv are written with 6 significant digits (<= 5e-6 relative)
    com = pd.read_csv(mpath)
    keys = ["strategy", "sym", "variant", "window", "cost"]
    o, t = ours.set_index(keys), com.set_index(keys)
    c.eq("row set", ",".join(sorted("|".join(k) for k in o.index)), ",".join(sorted("|".join(k) for k in t.index)))
    for k in t.index.intersection(o.index):
        for col in t.columns:
            if col in ("notional_per_year_usd", "turnover_x_capital_per_year", "notional_per_trade_x_capital") \
                    and k[1] == "ES":
                continue
            c.eq(f"{'|'.join(k)}|{col}", o.loc[k, col], t.loc[k, col])
    c.skip("ES notional_per_year_usd, turnover_x_capital_per_year, notional_per_trade_x_capital",
           "the ES contract notional needs the S&P 500 index level on each trade date, which is not committed")
    sz = pd.read_csv(spath).set_index(["strategy", "sym"])
    sm = {"H1-primary": "H1-primary", "BENCH-R": "BENCH-R"}
    for r in size.itertuples():
        k = (sm[r.strategy], r.sym)
        for col in ("is_days", "is_ann_vol_one_contract", "N_exact", "N", "is_ann_vol_with_N"):
            c.eq(f"sizing {k}|{col}", getattr(r, col), sz.loc[k, col])
    # the rebuilt per-contract P&L against the rounded per_trade.csv columns (6 significant digits)
    for cst in PS_COSTS:
        csv = np.array([d[cst] for d in T["csv_usd"]])
        excess = np.abs(T[f"{cst}_usd"].to_numpy() - csv) - (5e-6 * np.abs(csv) + 1e-9)
        c.eq(f"per_trade {cst}_usd rebuilt vs file (beyond 6-digit rounding)", float(max(excess.max(), 0.0)), 0.0)
    # the published daily series are the trade P&L on the trading calendar (file written with 8 digits)
    m = daily.merge(D, on=["strategy", "sym", "date"], suffixes=("", "_committed"), how="outer", indicator=True)
    c.eq("daily rows matched", int((m["_merge"] != "both").sum()), 0)
    for cst in ("gross", "net1x", "net2x"):
        diff = (m[f"ret_{cst}"] - m[f"ret_{cst}_committed"]).abs()
        c.eq(f"daily ret_{cst} beyond 8-digit rounding",
             float((diff - 6e-8 * m[f"ret_{cst}_committed"].abs() - 1e-12).clip(lower=0).max()), 0.0)
    return c


# ----------------------------------------------------------------------------- G3 headline
def item_presser_g3(out: Path) -> Cmp:
    tpath, kpath = need("backtests/results/presser_h1/h1primary_trades.csv", "backtests/results/presser_h1/key_results.json")
    T = pd.read_csv(tpath)
    g = T[(T.signal == "H1") & (T.clock == "primary") & (T.exit == "exit_1600") & (T.sym == "ZT")
          & (T["sample"] == "confirmation")]
    x = g["C0_ticks"].to_numpy()
    n = len(x)
    ours = {"n": n, "mean": float(x.mean()), "sd": float(x.std(ddof=1)), "median": float(np.median(x)),
            "hit": float((x > 0).mean()), "t": float(x.mean() / (x.std(ddof=1) / math.sqrt(n))),
            "mean_usd": float(g["C0_usd"].mean())}
    (out / "g3_headline_replay.json").write_text(json.dumps(ours, indent=1) + "\n", encoding="utf-8")
    key = json.loads(kpath.read_text(encoding="utf-8"))["H1-primary (stance)"]
    c = Cmp(1e-12)
    for k, v in ours.items():
        c.eq(k, v, key[k])
    c.skip("wild-bootstrap, block-bootstrap and permutation p-values of G3",
           "they come from the press-conference suite's own seeded resampling code; not recomputed here")
    return c


# ----------------------------------------------------------------------------- H2/H3/H4 family
H234 = "backtests/presser/backtest_h234"
SEED, B = 20261003, 9999
WEBB = np.array([-math.sqrt(1.5), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(1.5)])


def clark_west(y, yT, yC, g) -> dict:
    """As h234_s4_pnl.cw with CR1 meeting clusters, a t(G-1) reference and the Webb wild cluster bootstrap."""
    from scipy import stats as sps
    f = (y - yT) ** 2 - ((y - yC) ** 2 - (yT - yC) ** 2)
    codes, gi = np.unique(g, return_inverse=True)
    G, n = len(codes), len(f)
    m = f.mean()
    S = np.bincount(gi, weights=f - m, minlength=G)
    se = math.sqrt((G / (G - 1)) * np.sum(S ** 2) / n ** 2)
    t = m / se
    out = dict(n=n, mean_f=float(m), se=se, t=t, n_clusters=G, df=G - 1, p_one=float(1 - sps.t.cdf(t, G - 1)),
               p_two=float(2 * (1 - sps.t.cdf(abs(t), G - 1))))
    rng = np.random.default_rng(SEED)
    w = rng.choice(WEBB, size=(B, G))
    ys = w[:, gi] * (f - m)[None, :]
    ms = ys.mean(1)
    Sb = np.zeros((B, G))
    for j in range(G):
        Sb[:, j] = (ys[:, gi == j] - ms[:, None]).sum(1)
    ts = ms / np.sqrt((G / (G - 1)) * (Sb ** 2).sum(1) / n ** 2)
    out.update(wcb_p_one=float((1 + np.sum(ts >= t)) / (B + 1)), wcb_p_two=float((1 + np.sum(np.abs(ts) >= abs(t))) / (B + 1)))
    out["oos_r2_C_vs_T"] = float(1 - np.sum((y - yC) ** 2) / np.sum((y - yT) ** 2))
    out["oos_r2_C_vs_zero"] = float(1 - np.sum((y - yC) ** 2) / np.sum(y ** 2))
    out["oos_r2_T_vs_zero"] = float(1 - np.sum((y - yT) ** 2) / np.sum(y ** 2))
    nz = y != 0
    out["sign_hit_C"] = float(np.mean(np.sign(yC[nz]) == np.sign(y[nz])))
    out["sign_hit_T"] = float(np.mean(np.sign(yT[nz]) == np.sign(y[nz])))
    return out


def holm(p: dict) -> dict:
    keys = sorted(p, key=lambda k: p[k])
    adj, run = {}, 0.0
    for i, k in enumerate(keys):
        run = max(run, min(1.0, (len(keys) - i) * p[k]))
        adj[k] = run
    return adj


def item_h234(out: Path) -> Cmp:
    rpath, spath, kpath, fpath, hpath = need(f"{H234}/results/h4_answer_rows.csv", f"{H234}/results/answer_summary.csv",
                                             f"{H234}/qa/kill_switches.json", f"{H234}/results/family_holm.json",
                                             f"{H234}/results/h4_results.json")
    R = pd.read_csv(rpath)
    te = R[(R.sym == "ZT") & (R["sample"] == "primary_2023_2026")]
    h4 = clark_west(te.y.to_numpy(), te.yT.to_numpy(), te.yC.to_numpy(), te.meeting.to_numpy())
    AS = pd.read_csv(spath)
    kill = json.loads(kpath.read_text(encoding="utf-8"))
    fam = {}
    for k in ("H2", "H3"):
        row = AS[(AS.designated_primary == True) & (AS.key == k)]  # noqa: E712
        p_raw = float(row.wcb_p_two.iloc[0]) if len(row) and pd.notna(row.wcb_p_two.iloc[0]) else None
        killed = bool(kill[k]["killed"])
        status = "killed" if killed else ("unrunnable" if p_raw is None else "run")
        fam[k] = dict(status=status, p_raw=p_raw if status == "run" else None,
                      p_used=p_raw if status == "run" else 1.0, n_answers=int(row.n_answers.iloc[0]),
                      n_meetings=int(row.n_meetings.iloc[0]), mean_ticks=float(row["mean"].iloc[0]),
                      bb_ci90=[float(row.bb_ci90_lo.iloc[0]), float(row.bb_ci90_hi.iloc[0])])
    fam["H4"] = dict(status="run", p_raw=h4["p_one"], p_used=h4["p_one"], n_answers=h4["n"],
                     n_meetings=h4["n_clusters"])
    adj = holm({k: v["p_used"] for k, v in fam.items()})
    for k in fam:
        fam[k]["p_holm"] = adj[k]
        fam[k]["holm_significant_at_0.05"] = bool(adj[k] <= 0.05)
    (out / "family_holm_replay.json").write_text(json.dumps(fam, indent=1) + "\n", encoding="utf-8")
    (out / "h4_frozen_fit_replay.json").write_text(json.dumps(h4, indent=1) + "\n", encoding="utf-8")
    c = Cmp(1e-12)
    com_fam = json.loads(fpath.read_text(encoding="utf-8"))
    for k in ("H2", "H3", "H4"):
        for col, v in fam[k].items():
            theirs = com_fam[k][col]
            if isinstance(v, list):
                for i, (a, b) in enumerate(zip(v, theirs)):
                    c.eq(f"{k}|{col}[{i}]", a, b)
            else:
                c.eq(f"{k}|{col}", v, theirs)
    ff = json.loads(hpath.read_text(encoding="utf-8"))["answer_ZT"]["frozen_fit"]
    for col, v in h4.items():
        c.eq(f"H4 frozen_fit|{col}", v, ff[col])
    c.skip("H2 p_raw itself (taken from answer_summary.csv) and the H3 kill decision (kill_switches.json)",
           "the answer-level P&L behind them needs futures prices (answer_trades.csv is not committed); the Holm "
           "step and the H4 Clark-West test are recomputed")
    return c


# ----------------------------------------------------------------------------- results_2 metrics table
def item_results_2(out: Path) -> Cmp:
    (cpath,) = need("results_2/metrics/v2_metrics.csv")
    try:
        tab, cons = CM.compute(ROOT, out / "metrics", with_figures=True)
    except SystemExit as e:                          # compute_metrics names a missing input on stderr and exits 2
        if e.code == 2:
            raise Missing("an input of results_2/metrics/compute_metrics.py (named above)") from None
        raise RuntimeError(f"compute_metrics.py stopped: {e.code}") from None
    com = pd.read_csv(cpath)
    ours = pd.read_csv(out / "metrics" / "v2_metrics.csv")
    c = Cmp(1e-11)
    keys = ["series", "variant", "window"]
    o, t = ours.set_index(keys), com.set_index(keys)
    c.eq("row set", ",".join(sorted("|".join(k) for k in o.index)), ",".join(sorted("|".join(k) for k in t.index)))
    for k in t.index.intersection(o.index):
        for col in t.columns:
            a, b = o.loc[k, col], t.loc[k, col]
            if pd.isna(a) and pd.isna(b):
                continue
            c.eq(f"{'|'.join(k)}|{col}", a, b)
    c.eq("compute_metrics consistency with committed v2 files (max abs diff <= 1e-9)",
         float(max(cons["abs_diff"].max() - CM.TOL, 0.0)), 0.0)
    return c


# ----------------------------------------------------------------------------- figures
def presser_figure(out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    (dpath,) = need(f"{PS}/daily_returns.csv")
    D = pd.read_csv(dpath, parse_dates=["date"])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=CM.SURF, sharey=False)
    for ax, st in zip(axes, ("H1-primary", "BENCH-R")):
        g = D[(D.strategy == st) & (D.sym == "ZT")].set_index("date")
        ax.set_facecolor(CM.SURF)
        ax.axvspan(OOS_START, OOS_END, color="#fbe3d6", lw=0, zorder=0)
        for col, color, lab in (("ret_gross", CM.C3, "gross"), ("ret_net1x", CM.C1, "net 1x"),
                                ("ret_net2x", CM.C2, "net 2x")):
            eq = 1 + g[col].cumsum()
            ax.plot(eq.index, eq.to_numpy(), color=color, lw=1.8, label=lab)
        ax.axhline(1.0, color=CM.INK2, lw=0.6)
        ax.grid(axis="y", color="#e4e3df", lw=0.6)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.set_title(f"{st}, ZT: cumulative return on $10m (simple sum), OOS shaded", loc="left", fontsize=9.5)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[0].legend(frameon=False, fontsize=8.5, loc="lower left")
    fig.tight_layout()
    fig.savefig(out / "presser_equity_ZT.png", dpi=140, facecolor=CM.SURF)
    plt.close(fig)


# ----------------------------------------------------------------------------- main
ITEMS = [("v2_oos_metrics", item_v2_oos_metrics), ("v2_is_selection", item_v2_is_selection),
         ("v2_d4_metrics", item_v2_d4_metrics), ("presser_strategy", item_presser_strategy),
         ("presser_g3_headline", item_presser_g3), ("h234_family_holm", item_h234),
         ("results_2_v2_metrics", item_results_2)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="results_2/replay/replay_out")
    a = ap.parse_args()
    out = Path(a.out)
    out = out if out.is_absolute() else ROOT / out
    try:
        rel = out.resolve().relative_to(ROOT.resolve()).as_posix() + "/"
        if rel.startswith(FROZEN_PREFIXES):
            print(f"refusing to write into a frozen or compared folder: {rel}", file=sys.stderr)
            return 2
    except ValueError:
        pass
    out.mkdir(parents=True, exist_ok=True)
    figs = ["metrics/equity_v2.png", "metrics/equity_portfolio.png", "presser_equity_ZT.png"]
    for f in figs + ["replay_report.json"]:              # never report a file left by an earlier run
        (out / f).unlink(missing_ok=True)
    report, missing, failed = [], False, False
    for name, fn in ITEMS:
        try:
            c = fn(out)
            ok = not c.bad
            status = "PASS" if ok else "FAIL"
            failed |= not ok
            line = f"{status} {name}: {c.n} comparisons, max abs diff {c.worst:.3g}"
            if c.rel_tol:
                line += f", max rel diff {c.worst_rel:.3g} (tolerance {c.abs_tol:g} + {c.rel_tol:g} x |value|)"
            else:
                line += f" (tolerance {c.abs_tol:g})"
            if c.bad:
                line += f", {len(c.bad)} mismatches; first: {c.bad[:3]}"
            report.append({"item": name, "status": status, "comparisons": c.n, "max_abs_diff": c.worst,
                           "max_rel_diff": c.worst_rel, "abs_tol": c.abs_tol, "rel_tol": c.rel_tol,
                           "mismatches": [list(map(str, b)) for b in c.bad[:50]], "skipped": c.skips})
        except Missing as e:
            missing = True
            line = f"FAIL {name}: missing input ({e})"
            report.append({"item": name, "status": "FAIL (missing input)", "missing": str(e)})
        except Exception as e:  # noqa: BLE001  (any error fails the item loudly)
            failed = True
            line = f"FAIL {name}: error {type(e).__name__}: {e}"
            traceback.print_exc()
            report.append({"item": name, "status": "FAIL (error)", "error": f"{type(e).__name__}: {e}"})
        print(line)
        for s in report[-1].get("skipped", []):
            print(f"     SKIP {s['what']}: {s['why']}")
    try:
        presser_figure(out)
    except Missing as e:
        missing = True
        print(f"FAIL figures: missing input ({e})")
    made = [f for f in figs if (out / f).is_file()]
    print(f"{'PASS' if len(made) == len(figs) else 'FAIL'} figures: written {', '.join(made) or 'none'}")
    if len(made) != len(figs):
        failed = True
    (out / "replay_report.json").write_text(json.dumps(report, indent=1, default=str) + "\n", encoding="utf-8")
    code = 2 if missing else (1 if failed else 0)
    print(f"replay {'PASSED' if code == 0 else 'FAILED'} (exit {code}); outputs in {out.relative_to(ROOT).as_posix() if out.is_relative_to(ROOT) else 'the --out folder'}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
