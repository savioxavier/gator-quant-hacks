"""Press-conference trades shown as strategy-level daily series (v2 deviation D-3, last section).

Presentation only. Every trade, position, sample and rule comes from the frozen ADDENDUM suite:
  - H1-primary: backtests/results/presser_h1/h1primary_trades.csv (signal H1, primary clock, 16:00 exit)
  - BENCH-R:    backtests/results/presser_h1/tables/benchr_per_meeting_<SYM>.csv (exit at the next 1m open
                after tau_end_upper)
Positions are checked against the frozen backtests/presser/backtest/positions/ (sha256 manifest). No licensed bar is
read: the committed trade logs already carry gross ticks, the measured half-spreads at both fills and $ per tick.

Free source used: <GQH_DATA_DIR>/index_daily.parquet (Yahoo ^GSPC), for the NYSE trading calendar of the daily series
and for the ES notional proxy (50 x S&P 500 close on the trade date). No price level is written to any output.

Run from the repository root:
    PY=<python with pandas, numpy, matplotlib, pyarrow> GQH_DATA_DIR=<gqh cache> \
    $PY backtests/results/presser_strategy/build_presser_strategy.py
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
H1DIR = REPO / "backtests/results/presser_h1"
POSDIR = REPO / "backtests/presser/backtest/positions"
ADDENDUM = REPO / "backtests/presser/ADDENDUM.md"
D3 = REPO / "preregistration/v2_DEVIATION_D3_OOS.md"
DATA = Path(os.environ.get("GQH_DATA_DIR", str(Path.home() / ".cache/gqh")))
OUT = HERE

ADDENDUM_SHA = "1921b2ca1dc6e646b95ee1d1bbc3e3ef7f6a864c06cd724956df7c6569de2dc4"
D3_SHA = "97585d3ca3e7f5764d16e24787486c51ca298dd95ca57ad82d27e1ba30af1c69"

CAPITAL = 10_000_000.0
TARGET_VOL = 0.10
ANN = 252
FEE_SIDE = 2.00  # ADDENDUM 7, A-04: $2.00 per side per contract (UNVERIFIED broker estimate)
IS_END = pd.Timestamp("2024-10-02")
OOS_START, OOS_END = pd.Timestamp("2024-10-03"), pd.Timestamp("2026-10-02")
SYMS = ["ZT", "ZF", "ZN", "ES"]
FACE = {"ZT": 200_000.0, "ZF": 100_000.0, "ZN": 100_000.0}  # CME contract face values
ES_MULT = 50.0
STRATS = {"H1": "H1-primary", "BENCHR": "BENCH-R"}
COSTS = ["gross", "net1x", "net2x", "fixed1x", "fixed2x"]
COST_LABEL = {
    "gross": "gross (trade prints, no cost)",
    "net1x": "net 1x: measured half-spread at each fill + $2/side fee (ZF: 2 ticks/side + fee, no ZF quotes)",
    "net2x": "net 2x: twice the net 1x cost",
    "fixed1x": "fixed-tick 1x: 2 ticks/side + $2/side fee (ADDENDUM C2+F)",
    "fixed2x": "fixed-tick 2x: 4 ticks/side + $4/side fee",
}


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return Path(p).resolve().relative_to(REPO).as_posix()


# ------------------------------------------------------------------------------------------------ checks on inputs
qa: dict = {}
if sha256(ADDENDUM) != ADDENDUM_SHA:
    raise SystemExit("ADDENDUM changed")
if sha256(D3) != D3_SHA:
    raise SystemExit("D-3 changed")
qa["addendum_sha256_ok"] = True
qa["d3_sha256_ok"] = True
def sha256_eol(p: Path) -> tuple[str, str]:
    """The manifest was written on Windows (CRLF); git stores LF. Accept the file as written or in CRLF form."""
    raw = Path(p).read_bytes()
    crlf = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    return hashlib.sha256(raw).hexdigest(), hashlib.sha256(crlf).hexdigest()


eol_forms = {}
for line in (POSDIR / "manifest_sha256.txt").read_text().splitlines():
    h, f = line.split("  ")
    h_raw, h_crlf = sha256_eol(POSDIR / f)
    if h not in (h_raw, h_crlf):
        raise SystemExit(f"frozen positions file changed: {f}")
    eol_forms[f] = "as stored" if h == h_raw else "after LF->CRLF (manifest written on Windows)"
qa["frozen_positions_manifest_ok"] = True
qa["frozen_positions_hash_form"] = sorted(set(eol_forms.values()))

mpos = pd.read_csv(POSDIR / "meetings_positions.csv", dtype={"date": str}).set_index("date")

# ------------------------------------------------------------------------------------------------ per-trade table
rows = []
h1 = pd.read_csv(H1DIR / "h1primary_trades.csv", dtype={"date": str})
h1 = h1[(h1.signal == "H1") & (h1.clock == "primary") & (h1.exit == "exit_1600")].copy()
if h1.duplicated(["date", "sym"]).any():
    raise SystemExit("duplicate H1 trades")
bad = (h1.pos.values != mpos.loc[h1.date, "H1__pos"].values).sum()
qa["h1_positions_match_frozen"] = int(bad) == 0
if bad:
    raise SystemExit("H1 trade positions differ from the frozen positions")
for r in h1.itertuples():
    rows.append(dict(strategy="H1", sym=r.sym, date=r.date, pos=r.pos, entry_ts=r.entry_ts, exit_ts=r.exit_ts,
                     tick_era=r.tick_era, usd_per_tick=r.usd_per_tick, gross_ticks=r.C0_ticks,
                     hs_entry_ticks=r.hs_entry_ticks, hs_exit_ticks=r.hs_exit_ticks, sample=r.sample,
                     chair=r.chair, timing_eligible=1, ref_net1x_usd=r.CMF_usd, ref_fixed1x_usd=r.C2F_usd,
                     ref_gross_usd=r.C0_usd))
for s in SYMS:
    b = pd.read_csv(H1DIR / "tables" / f"benchr_per_meeting_{s}.csv", dtype={"date": str})
    if b.date.duplicated().any():
        raise SystemExit("duplicate BENCH-R trades")
    bad = (b.pos.values != mpos.loc[b.date, f"bench_pos_{s}"].values).sum()
    qa[f"benchr_{s}_positions_match_frozen"] = int(bad) == 0
    if bad:
        raise SystemExit(f"BENCH-R {s} positions differ from the frozen positions")
    for r in b.itertuples():
        rows.append(dict(strategy="BENCHR", sym=s, date=r.date, pos=r.pos, entry_ts=r.entry_ts, exit_ts=r.exit_ts,
                         tick_era=r.tick_era, usd_per_tick=r.usd_per_tick, gross_ticks=r.C0_ticks,
                         hs_entry_ticks=r.hs_entry_ticks, hs_exit_ticks=r.hs_exit_ticks, sample=f"era_{r.era}",
                         chair=r.chair, timing_eligible=int(r.drop_timing == 0),
                         ref_net1x_usd=r.CM_usd - 2 * FEE_SIDE, ref_fixed1x_usd=r.C2F_usd, ref_gross_usd=r.C0_usd))
T = pd.DataFrame(rows)
T["date_ts"] = pd.to_datetime(T.date)
T["window"] = np.where(T.date_ts <= IS_END, "IS", "OOS")
et = lambda c: pd.to_datetime(T[c], utc=True, format="ISO8601").dt.tz_convert("America/New_York")
T["entry_time_et"] = et("entry_ts").dt.strftime("%H:%M")
T["exit_time_et"] = et("exit_ts").dt.strftime("%H:%M")
T["hold_min"] = ((et("exit_ts") - et("entry_ts")).dt.total_seconds() / 60).round(1)
measured = T.hs_entry_ticks.notna() & T.hs_exit_ticks.notna()
if not (measured == (T.sym != "ZF")).all():
    raise SystemExit("measured half-spreads missing outside ZF")
T["cost_basis"] = np.where(measured, "measured half-spread + fee", "2 ticks/side + fee (no ZF quotes)")
T["spread_cost_ticks"] = np.where(measured, T.hs_entry_ticks + T.hs_exit_ticks, 4.0)
T["fee_usd"] = 2 * FEE_SIDE
T["gross_usd"] = T.gross_ticks * T.usd_per_tick
cost1 = T.spread_cost_ticks * T.usd_per_tick + T.fee_usd
T["net1x_usd"] = T.gross_usd - cost1
T["net2x_usd"] = T.gross_usd - 2 * cost1
T["fixed1x_usd"] = T.gross_usd - 4 * T.usd_per_tick - T.fee_usd
T["fixed2x_usd"] = T.gross_usd - 8 * T.usd_per_tick - 2 * T.fee_usd
T["net1x_ticks"] = T.net1x_usd / T.usd_per_tick
T["net2x_ticks"] = T.net2x_usd / T.usd_per_tick
# reconciliation with the committed suite rows
qa["gross_usd_matches_suite_C0"] = bool(np.allclose(T.gross_usd, T.ref_gross_usd, atol=1e-9))
m = measured
qa["net1x_matches_suite_CM_plus_fee"] = bool(np.allclose(T.net1x_usd[m], T.ref_net1x_usd[m], atol=1e-9))
qa["fixed1x_matches_suite_C2F"] = bool(np.allclose(T.fixed1x_usd, T.ref_fixed1x_usd, atol=1e-9))
for k in ["gross_usd_matches_suite_C0", "net1x_matches_suite_CM_plus_fee", "fixed1x_matches_suite_C2F"]:
    if not qa[k]:
        raise SystemExit(f"reconciliation failed: {k}")
g3 = T[(T.strategy == "H1") & (T.sym == "ZT") & (T["sample"] == "confirmation")]
key = json.loads((H1DIR / "key_results.json").read_text())["H1-primary (stance)"]
qa["g3_reproduced"] = dict(n=int(len(g3)), mean_gross_ticks=float(g3.gross_ticks.mean()),
                           committed_n=key["n"], committed_mean=key["mean"],
                           ok=bool(len(g3) == key["n"] and abs(g3.gross_ticks.mean() - key["mean"]) < 1e-12))
if not qa["g3_reproduced"]["ok"]:
    raise SystemExit("G3 sample not reproduced")
S = pd.read_csv(H1DIR / "summary_long.csv")
chk = []
for s in SYMS:
    for era in ["2016-2019", "2020-2026"]:
        ref = S[(S.test == "BENCH-R") & (S.variant == "exit_tau_upper") & (S["sample"] == f"era_{era}") &
                (S.sym == s) & (S.cost == "C0") & (S.unit == "usd")].iloc[0]
        x = T[(T.strategy == "BENCHR") & (T.sym == s) & (T["sample"] == f"era_{era}")]
        chk.append(bool(len(x) == ref.n and abs(x.gross_usd.mean() - ref["mean"]) < 1e-9))
qa["benchr_era_means_reproduced"] = all(chk)
if not all(chk):
    raise SystemExit("BENCH-R era means not reproduced")

# ------------------------------------------------------------------------------------------------ calendar, ES notional
idx = pd.read_parquet(DATA / "index_daily.parquet")
spx = idx[idx.ticker == "^GSPC"].assign(date=lambda d: pd.to_datetime(d.date).dt.normalize()).set_index("date").close
CAL = pd.DatetimeIndex(sorted(spx.index))
missing = sorted(set(T.date_ts) - set(CAL))
qa["trade_dates_in_calendar"] = len(missing) == 0
if missing:
    raise SystemExit(f"trade dates not in the trading calendar: {missing}")
qa["calendar_last_date"] = str(CAL.max().date())
if CAL.max() < OOS_END:
    raise SystemExit("calendar does not reach the end of the out-of-sample window")
T["notional_per_contract"] = np.where(T.sym == "ES", ES_MULT * spx.reindex(T.date_ts).values,
                                      T.sym.map(FACE).fillna(np.nan).values)

# ------------------------------------------------------------------------------------------------ sizing on IS gross
first_trade = T.groupby("strategy").date_ts.min()
N = {}
size_rows = []
for (st, s), g in T.groupby(["strategy", "sym"]):
    days = CAL[(CAL >= first_trade[st]) & (CAL <= IS_END)]
    pnl = g[g.window == "IS"].groupby("date_ts").gross_usd.sum().reindex(days, fill_value=0.0)
    vol1 = (pnl / CAPITAL).std(ddof=1) * np.sqrt(ANN)
    n_exact = TARGET_VOL / vol1
    N[(st, s)] = max(1, int(round(n_exact)))
    size_rows.append(dict(strategy=STRATS[st], sym=s, is_start=str(first_trade[st].date()), is_end=str(IS_END.date()),
                          is_days=len(days), is_ann_vol_one_contract=vol1, N_exact=n_exact, N=N[(st, s)],
                          is_ann_vol_with_N=vol1 * N[(st, s)]))
T["N"] = [N[(a, b)] for a, b in zip(T.strategy, T.sym)]
for c in ["gross", "net1x", "net2x", "fixed1x", "fixed2x"]:
    T[f"{c}_usd_position"] = T[f"{c}_usd"] * T.N

# ------------------------------------------------------------------------------------------------ windows and metrics
WINDOWS = {
    "H1": [("IS", None, IS_END, "headline"), ("OOS", OOS_START, OOS_END, "headline"),
           ("IS: 2016-2022 sample (D1 clean)", None, pd.Timestamp("2022-12-31"), "sub-window"),
           ("G3 confirmation sample 2023-02-01..2026-04-29", pd.Timestamp("2023-02-01"),
            pd.Timestamp("2026-04-29"), "sub-window")],
    "BENCHR": [("IS", None, IS_END, "headline"), ("OOS", OOS_START, OOS_END, "headline"),
               ("IS: era 2016-2019", None, pd.Timestamp("2019-12-31"), "sub-window"),
               ("IS: era 2020-2024-10-02", pd.Timestamp("2020-01-01"), IS_END, "sub-window")],
}
VARIANTS = {"all": lambda g: g, "ex_warsh": lambda g: g[g.chair != "Warsh"]}


def drawdown(r: np.ndarray) -> tuple[float, float]:
    eq = 1.0 + np.cumsum(r)
    peak = np.maximum.accumulate(np.r_[1.0, eq])[1:]
    dd = eq / peak - 1.0
    return float(dd.min()), float((peak - eq).max() * CAPITAL)


met = []
daily_frames = []
for st, wins in WINDOWS.items():
    for s in SYMS:
        g_all = T[(T.strategy == st) & (T.sym == s)]
        n_c = N[(st, s)]
        for vname, vf in VARIANTS.items():
            g = vf(g_all)
            if vname != "all" and len(g) == len(g_all):
                continue  # variant identical to the headline series for this strategy and symbol
            for wname, w0, w1, role in wins:
                w0 = first_trade[st] if w0 is None else w0
                days = CAL[(CAL >= w0) & (CAL <= w1)]
                gw = g[(g.date_ts >= w0) & (g.date_ts <= w1)]
                if vname != "all" and len(gw) == ((g_all.date_ts >= w0) & (g_all.date_ts <= w1)).sum():
                    continue  # no Warsh meeting in this window: identical to the headline row
                years = len(days) / ANN
                for c in COSTS:
                    pnl = gw.groupby("date_ts")[f"{c}_usd_position"].sum().reindex(days, fill_value=0.0)
                    r = (pnl / CAPITAL).values
                    mu, sd = r.mean(), r.std(ddof=1)
                    pt = gw[f"{c}_usd"].values
                    n = len(pt)
                    mdd, mdd_usd = drawdown(r)
                    pts = pt.mean() / pt.std(ddof=1) if n > 1 and pt.std(ddof=1) > 0 else np.nan
                    met.append(dict(
                        strategy=STRATS[st], sym=s, variant=vname, window=wname, role=role, cost=c,
                        start=str(days.min().date()), end=str(days.max().date()), trading_days=len(days),
                        years=years, N_contracts=n_c, n_trades=n,
                        ann_return=mu * ANN, ann_vol=sd * np.sqrt(ANN),
                        sharpe=(mu / sd * np.sqrt(ANN)) if sd > 0 else np.nan,
                        max_drawdown=mdd, max_drawdown_usd=mdd_usd, total_return=r.sum(),
                        total_pnl_usd=pnl.sum(),
                        mean_trade_usd_per_contract=pt.mean() if n else np.nan,
                        sd_trade_usd_per_contract=pt.std(ddof=1) if n > 1 else np.nan,
                        per_trade_sharpe=pts,
                        per_trade_sharpe_annualised=pts * np.sqrt(n / years) if n > 1 else np.nan,
                        t_stat_trades=pts * np.sqrt(n) if n > 1 else np.nan,
                        hit_rate=(pt > 0).mean() if n else np.nan,
                        zero_share=(pt == 0).mean() if n else np.nan,
                        trades_per_year=n / years,
                        contracts_per_year=2 * n_c * n / years,
                        notional_per_year_usd=2 * n_c * gw.notional_per_contract.sum() / years,
                        turnover_x_capital_per_year=2 * n_c * gw.notional_per_contract.sum() / years / CAPITAL,
                        notional_per_trade_x_capital=n_c * gw.notional_per_contract.mean() / CAPITAL if n else np.nan,
                    ))
            if vname == "all":
                days = CAL[(CAL >= first_trade[st]) & (CAL <= OOS_END)]
                d = pd.DataFrame({"date": days})
                d["window"] = np.where(d.date <= IS_END, "IS", "OOS")
                for c in ["gross", "net1x", "net2x"]:
                    p = g.groupby("date_ts")[f"{c}_usd_position"].sum().reindex(days, fill_value=0.0)
                    d[f"ret_{c}"] = (p / CAPITAL).values
                d.insert(0, "sym", s)
                d.insert(0, "strategy", STRATS[st])
                daily_frames.append(d)

M = pd.DataFrame(met)
D = pd.concat(daily_frames, ignore_index=True)
D["date"] = D.date.dt.strftime("%Y-%m-%d")

# ------------------------------------------------------------------------------------------------ write tables
pt_cols = ["strategy", "sym", "date", "window", "sample", "chair", "timing_eligible", "pos", "entry_time_et",
           "exit_time_et", "hold_min", "tick_era", "usd_per_tick", "gross_ticks", "hs_entry_ticks", "hs_exit_ticks",
           "spread_cost_ticks", "fee_usd", "cost_basis", "net1x_ticks", "net2x_ticks", "gross_usd", "net1x_usd",
           "net2x_usd", "fixed1x_usd", "fixed2x_usd", "N", "gross_usd_position", "net1x_usd_position",
           "net2x_usd_position"]
P = T.assign(strategy=T.strategy.map(STRATS)).sort_values(["strategy", "sym", "date"])[pt_cols]
P.to_csv(OUT / "per_trade.csv", index=False, float_format="%.6g")
D.to_csv(OUT / "daily_returns.csv", index=False, float_format="%.8g")
M.to_csv(OUT / "metrics.csv", index=False, float_format="%.6g")
pd.DataFrame(size_rows).to_csv(OUT / "sizing.csv", index=False, float_format="%.6g")


def fmt_pct(x, d=1):
    return "" if pd.isna(x) else f"{100 * x:.{d}f}%"


def fmt(x, d=2):
    return "" if pd.isna(x) else f"{x:.{d}f}"


def md_table(sel: pd.DataFrame) -> str:
    hdr = ("| window | cost | n trades | ann. return | ann. vol | Sharpe (daily) | per-trade Sharpe | max DD | "
           "hit rate | mean $/contract/trade | contracts/yr | notional/yr (x capital) |")
    out = [hdr, "|" + "---|" * 12]
    for r in sel.itertuples():
        out.append(f"| {r.window} | {r.cost} | {r.n_trades} | {fmt_pct(r.ann_return)} | {fmt_pct(r.ann_vol)} | "
                   f"{fmt(r.sharpe)} | {fmt(r.per_trade_sharpe)} | {fmt_pct(r.max_drawdown)} | "
                   f"{fmt_pct(r.hit_rate, 0)} | {fmt(r.mean_trade_usd_per_contract, 1)} | "
                   f"{r.contracts_per_year:,.0f} | {r.turnover_x_capital_per_year:,.0f} |")
    return "\n".join(out)


lines = ["# Tables (generated by build_presser_strategy.py; numbers only, see README.md for conventions)", ""]
lines += ["## Headline: ZT, the pre-registered instrument of both strategies", "",
          "| strategy | window | dates | N | cost | n trades | ann. return | ann. vol | Sharpe (daily) | "
          "per-trade Sharpe | max DD | hit rate | contracts/yr | notional/yr | turnover (x capital/yr) |",
          "|" + "---|" * 15]
for st in ["H1", "BENCHR"]:
    for w in ["IS", "OOS"]:
        for c in ["gross", "net1x", "net2x"]:
            r = M[(M.strategy == STRATS[st]) & (M.sym == "ZT") & (M.variant == "all") & (M.window == w) &
                  (M.cost == c)].iloc[0]
            lines.append(f"| {STRATS[st]} | {w} | {r.start}..{r.end} | {r.N_contracts:,} | {c} | {r.n_trades} | "
                         f"{fmt_pct(r.ann_return)} | {fmt_pct(r.ann_vol)} | {fmt(r.sharpe)} | "
                         f"{fmt(r.per_trade_sharpe)} | {fmt_pct(r.max_drawdown)} | {fmt_pct(r.hit_rate, 0)} | "
                         f"{r.contracts_per_year:,.0f} | ${r.notional_per_year_usd / 1e9:,.1f}bn | "
                         f"{r.turnover_x_capital_per_year:,.0f} |")
lines += ["", "## Sharpe (daily, sqrt 252) by symbol, headline windows", "",
          "| strategy | symbol | N | IS trades | IS gross | IS net 1x | IS net 2x | OOS trades | OOS gross | "
          "OOS net 1x | OOS net 2x | OOS net 1x ex-Warsh |", "|" + "---|" * 12]
for st in ["H1", "BENCHR"]:
    for s_ in SYMS:
        q = M[(M.strategy == STRATS[st]) & (M.sym == s_)]
        v = lambda w, c, var="all": q[(q.variant == var) & (q.window == w) & (q.cost == c)].sharpe.iloc[0]
        nt = lambda w: q[(q.variant == "all") & (q.window == w) & (q.cost == "gross")].n_trades.iloc[0]
        lines.append(f"| {STRATS[st]} | {s_} | {N[(st, s_)]:,} | {nt('IS')} | {fmt(v('IS', 'gross'))} | "
                     f"{fmt(v('IS', 'net1x'))} | {fmt(v('IS', 'net2x'))} | {nt('OOS')} | {fmt(v('OOS', 'gross'))} | "
                     f"{fmt(v('OOS', 'net1x'))} | {fmt(v('OOS', 'net2x'))} | {fmt(v('OOS', 'net1x', 'ex_warsh'))} |")
lines += ["", "## Detail by strategy and symbol", ""]
for st in ["H1", "BENCHR"]:
    for s in SYMS:
        n_c = N[(st, s)]
        lines.append(f"### {STRATS[st]} {s} (N = {n_c:,} contracts per trade)")
        lines.append("")
        sel = M[(M.strategy == STRATS[st]) & (M.sym == s) & (M.variant == "all") &
                (M.cost.isin(["gross", "net1x", "net2x"]))]
        lines.append(md_table(sel))
        lines.append("")
        alt = M[(M.strategy == STRATS[st]) & (M.sym == s) & (M.variant == "all") & (M.role == "headline") &
                (M.cost.isin(["fixed1x", "fixed2x"]))]
        if s == "ZF":
            lines.append("Fixed-tick cost rows: identical to the net rows for ZF (no ZF quotes, so ZF net already "
                         "uses 2 ticks/side + fee).")
        else:
            lines.append("Fixed-tick cost rows (headline windows):")
            lines.append("")
            lines.append(md_table(alt))
        lines.append("")
        exw = M[(M.strategy == STRATS[st]) & (M.sym == s) & (M.variant == "ex_warsh") & (M.window == "OOS") &
                (M.cost.isin(["gross", "net1x", "net2x"]))]
        if len(exw):
            lines.append("Out of sample without the 3 Warsh meetings (sensitivity):")
            lines.append("")
            lines.append(md_table(exw))
            lines.append("")
(OUT / "tables.md").write_text("\n".join(lines), encoding="utf-8")

# ------------------------------------------------------------------------------------------------ key metrics json
key_m = {}
for st in ["H1", "BENCHR"]:
    for s in SYMS:
        for wname in ["IS", "OOS"]:
            for c in ["gross", "net1x", "net2x"]:
                r = M[(M.strategy == STRATS[st]) & (M.sym == s) & (M.variant == "all") & (M.window == wname) &
                      (M.cost == c)].iloc[0]
                key_m[f"{STRATS[st]}|{s}|{wname}|{c}"] = {
                    k: (None if pd.isna(r[k]) else (round(float(r[k]), 6) if isinstance(r[k], (float, np.floating))
                                                    else (int(r[k]) if isinstance(r[k], (np.integer,)) else r[k])))
                    for k in ["start", "end", "N_contracts", "n_trades", "ann_return", "ann_vol", "sharpe",
                              "per_trade_sharpe", "max_drawdown", "hit_rate", "contracts_per_year",
                              "notional_per_year_usd", "turnover_x_capital_per_year"]}
(OUT / "key_metrics.json").write_text(json.dumps(key_m, indent=1), encoding="utf-8")

# ------------------------------------------------------------------------------------------------ equity curves
COL = {"gross": "#2a78d6", "net1x": "#eb6834", "net2x": "#1baf7a"}
LS = {"gross": "-", "net1x": "--", "net2x": ":"}
LBL = {"gross": "gross", "net1x": "net 1x", "net2x": "net 2x"}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titlecolor": INK, "figure.facecolor": SURF, "axes.facecolor": SURF})


def sharpe_of(st, s, w, c):
    r = M[(M.strategy == STRATS[st]) & (M.sym == s) & (M.variant == "all") & (M.window == w) & (M.cost == c)]
    return r.sharpe.iloc[0]


def panel(ax, st, s, labels=True):
    d = D[(D.strategy == STRATS[st]) & (D.sym == s)].copy()
    x = pd.to_datetime(d.date)
    ax.axvspan(OOS_START, x.max(), color="#efeeea", lw=0, zorder=0)
    ax.axvline(OOS_START, color=INK2, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.axhline(0, color=GRID, lw=1, zorder=1)
    for c in ["gross", "net1x", "net2x"]:
        y = 100 * d[f"ret_{c}"].cumsum().values
        ax.plot(x, y, color=COL[c], lw=2, ls=LS[c], label=LBL[c], zorder=3)
        if labels:
            ax.annotate(f"{LBL[c]} {y[-1]:+.1f}%", xy=(x.iloc[-1], y[-1]), xytext=(6, 0),
                        textcoords="offset points", va="center", fontsize=8, color=INK2)
    ax.grid(axis="y", color=GRID, lw=0.6)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.xaxis.set_major_locator(mdates.YearLocator(2 if st == "BENCHR" else 1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_ylabel("cumulative P&L, % of $10m")
    yl = ax.get_ylim()
    ax.text(OOS_START, yl[1], "  out of sample", va="top", ha="left", fontsize=8, color=INK2)


for st in ["H1", "BENCHR"]:
    s = "ZT"
    fig, ax = plt.subplots(figsize=(9, 4.6))
    panel(ax, st, s)
    ax.set_xlim(right=pd.Timestamp(OOS_END) + pd.Timedelta(days=330 if st == "H1" else 520))
    ax.legend(loc="upper left", frameon=False, ncol=3)
    ttl = (f"{STRATS[st]}, {s}: N = {N[(st, s)]:,} contracts per trade on $10m "
           f"(IS vol 10% by construction)")
    ax.set_title(ttl, loc="left", fontsize=10, color=INK)
    sub = (f"Sharpe net 1x: IS {sharpe_of(st, s, 'IS', 'net1x'):.2f}, OOS {sharpe_of(st, s, 'OOS', 'net1x'):.2f}"
           f"   |   presentation of pre-registered trades; G3 stays NO-GO")
    fig.text(0.125, 0.005, sub, fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / f"equity_{'h1primary' if st == 'H1' else 'benchr'}_ZT.png", dpi=150)
    plt.close(fig)
    fig, axs = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
    for ax, s in zip(axs.ravel(), SYMS):
        panel(ax, st, s, labels=False)
        ax.set_title(f"{s}  (N = {N[(st, s)]:,};  net 1x Sharpe IS {sharpe_of(st, s, 'IS', 'net1x'):.2f} / "
                     f"OOS {sharpe_of(st, s, 'OOS', 'net1x'):.2f})", loc="left", fontsize=9)
    hd, lb = axs[0, 0].get_legend_handles_labels()
    fig.legend(hd, lb, loc="upper right", frameon=False, ncol=3, bbox_to_anchor=(0.995, 0.995))
    fig.suptitle(f"{STRATS[st]}: all four symbols, each sized to 10% IS vol on $10m "
                 f"(ZF net = 2 ticks/side + fee; no ZF quotes)", x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(OUT / f"equity_{'h1primary' if st == 'H1' else 'benchr'}_all_symbols.png", dpi=150)
    plt.close(fig)

# ------------------------------------------------------------------------------------------------ meta
inputs = [H1DIR / "h1primary_trades.csv", H1DIR / "key_results.json", H1DIR / "summary_long.csv",
          POSDIR / "meetings_positions.csv", POSDIR / "manifest_sha256.txt", ADDENDUM, D3] + \
         [H1DIR / "tables" / f"benchr_per_meeting_{s}.csv" for s in SYMS]
meta = dict(
    purpose="strategy-level presentation of pre-registered press-conference trades (v2 deviation D-3, last section)",
    inputs={rel(p): sha256(p) for p in inputs},
    free_source={"<GQH_DATA_DIR>/index_daily.parquet (Yahoo ^GSPC)": sha256(DATA / "index_daily.parquet")},
    capital_usd=CAPITAL, target_is_ann_vol=TARGET_VOL, annualisation_days=ANN, fee_usd_per_side=FEE_SIDE,
    is_end=str(IS_END.date()), oos=[str(OOS_START.date()), str(OOS_END.date())],
    first_trade={STRATS[k]: str(v.date()) for k, v in first_trade.items()},
    N_contracts={f"{STRATS[a]}|{b}": v for (a, b), v in N.items()},
    cost_labels=COST_LABEL,
)
(OUT / "run_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
(OUT / "qa.json").write_text(json.dumps(qa, indent=1), encoding="utf-8")
print(json.dumps(qa, indent=1))
print(pd.DataFrame(size_rows).to_string())
