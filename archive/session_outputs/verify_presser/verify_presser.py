"""Independent recomputation of backtests/results/presser_strategy metrics.

Two independent paths:
  (a) metrics recomputed from the saved daily_returns.csv (gross/net1x/net2x, variant 'all');
  (b) per-trade P&L rebuilt from the committed suite trade logs (h1primary_trades.csv,
      tables/benchr_per_meeting_<SYM>.csv), own daily series on the Yahoo ^GSPC calendar, own sizing,
      then every metrics.csv row (all variants, windows, costs incl. fixed-tick).
Compared against metrics.csv (6 significant digits stored), key_metrics.json (6 decimals),
sizing.csv, per_trade.csv, daily_returns.csv and the tables in tables.md / README.md.
Writes only into this directory. Prints no price level.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(sys.argv[1])
OUTD = Path(__file__).resolve().parent
RES = REPO / "backtests/results/presser_strategy"
SRC = REPO / "backtests/results/presser_h1"
DATA = Path(os.environ.get("GQH_DATA_DIR", r"<home>/.cache/gqh"))

CAP = 1e7
ANN = 252
FEE_RT = 4.0
IS_END = pd.Timestamp("2024-10-02")
OOS0, OOS1 = pd.Timestamp("2024-10-03"), pd.Timestamp("2026-10-02")
SYMS = ["ZT", "ZF", "ZN", "ES"]
FACE = {"ZT": 2e5, "ZF": 1e5, "ZN": 1e5}
REL = 1e-6

problems: list[str] = []
notes: list[str] = []

# ------------------------------------------------------------------ (b) rebuild trades from committed logs
h = pd.read_csv(SRC / "h1primary_trades.csv")
h = h[(h.signal == "H1") & (h.clock == "primary") & (h.exit == "exit_1600")].copy()
trades = []
for r in h.itertuples():
    trades.append(dict(strategy="H1-primary", sym=r.sym, date=pd.Timestamp(str(r.date)[:10]), chair=r.chair,
                       sample=r.sample, gticks=r.C0_ticks, upt=r.usd_per_tick, hse=r.hs_entry_ticks,
                       hsx=r.hs_exit_ticks, ref_c0=r.C0_usd, ref_c2f=r.C2F_usd, ref_cmf=r.CMF_usd))
for s in SYMS:
    b = pd.read_csv(SRC / "tables" / f"benchr_per_meeting_{s}.csv")
    for r in b.itertuples():
        trades.append(dict(strategy="BENCH-R", sym=s, date=pd.Timestamp(str(r.date)[:10]), chair=r.chair,
                           sample=f"era_{r.era}", gticks=r.C0_ticks, upt=r.usd_per_tick, hse=r.hs_entry_ticks,
                           hsx=r.hs_exit_ticks, ref_c0=r.C0_usd, ref_c2f=r.C2F_usd, ref_cmf=r.CM_usd - FEE_RT))
T = pd.DataFrame(trades)
meas = T.hse.notna() & T.hsx.notna()
T["gross"] = T["gticks"] * T["upt"]
c1 = np.where(meas, (T.hse + T.hsx) * T.upt, 4 * T.upt) + FEE_RT
T["net1x"] = T.gross - c1
T["net2x"] = T.gross - 2 * c1
T["fixed1x"] = T.gross - 4 * T.upt - FEE_RT
T["fixed2x"] = T.gross - 8 * T.upt - 2 * FEE_RT
T["spread_ticks"] = np.where(meas, T.hse + T.hsx, 4.0)
chk = {
    "gross_vs_C0_usd": np.abs(T.gross - T.ref_c0).max(),
    "fixed1x_vs_C2F_usd": np.abs(T.fixed1x - T.ref_c2f).max(),
    "net1x_vs_CM(F)_usd_measured": np.abs((T.net1x - T.ref_cmf)[meas]).max(),
}
for k, v in chk.items():
    if v > 1e-9:
        problems.append(f"trade reconstruction {k}: max abs diff {v}")
if (~meas & (T.sym != "ZF")).any():
    problems.append("missing measured half-spread outside ZF")
if (meas & (T.sym == "ZF")).any():
    notes.append("ZF has measured half-spreads for some rows (unexpected)")

T["window"] = np.where(T.date <= IS_END, "IS", "OOS")

# calendar (free Yahoo ^GSPC dates); ES notional proxy used only in aggregates
idx = pd.read_parquet(DATA / "index_daily.parquet")
spx = idx[idx.ticker == "^GSPC"].copy()
spx["date"] = pd.to_datetime(spx.date).dt.normalize()
spx = spx.drop_duplicates("date").set_index("date").close.sort_index()
CAL = spx.index
miss = set(T.date) - set(CAL)
if miss:
    problems.append(f"{len(miss)} trade dates not on calendar")
T["notional"] = np.where(T.sym == "ES", 50.0 * spx.reindex(T.date).values, T.sym.map(FACE).values)

first = T.groupby("strategy").date.min()

# sizing
size = {}
siz_rows = []
for (st, s), g in T.groupby(["strategy", "sym"]):
    days = CAL[(CAL >= first[st]) & (CAL <= IS_END)]
    p = g[g.window == "IS"].groupby("date").gross.sum().reindex(days, fill_value=0.0) / CAP
    v1 = p.std(ddof=1) * math.sqrt(ANN)
    size[(st, s)] = int(round(0.10 / v1))
    siz_rows.append(dict(strategy=st, sym=s, is_days=len(days), vol1=v1, N_exact=0.10 / v1, N=size[(st, s)],
                         vol_N=v1 * size[(st, s)]))
SZ = pd.DataFrame(siz_rows)
sz_ref = pd.read_csv(RES / "sizing.csv")
m = SZ.merge(sz_ref, on=["strategy", "sym"])
for r in m.itertuples():
    if r.N_x != r.N_y:
        problems.append(f"sizing N mismatch {r.strategy} {r.sym}: mine {r.N_x} vs {r.N_y}")
    if r.is_days_x != r.is_days_y:
        problems.append(f"sizing is_days mismatch {r.strategy} {r.sym}")
    for a, bb, nm in [(r.vol1, r.is_ann_vol_one_contract, "vol1"), (r.N_exact_x, r.N_exact_y, "N_exact"),
                      (r.vol_N, r.is_ann_vol_with_N, "vol_N")]:
        tol = max(REL * abs(bb), 0.5 * 10 ** (math.floor(math.log10(abs(bb))) - 5))
        if abs(a - bb) > tol:
            problems.append(f"sizing {nm} {r.strategy} {r.sym}: mine {a:.9g} vs {bb}")
T["N"] = [size[(a, b)] for a, b in zip(T.strategy, T.sym)]

# ------------------------------------------------------------------ daily series (own) and saved daily
D_saved = pd.read_csv(RES / "daily_returns.csv", parse_dates=["date"])
COSTS = ["gross", "net1x", "net2x", "fixed1x", "fixed2x"]


def own_daily(g: pd.DataFrame, days: pd.DatetimeIndex, cost: str, n: int) -> np.ndarray:
    return (g.groupby("date")[cost].sum().reindex(days, fill_value=0.0) * n / CAP).values


dmax = 0.0
dmax_rel = 0.0
for (st, s), g in T.groupby(["strategy", "sym"]):
    days = CAL[(CAL >= first[st]) & (CAL <= OOS1)]
    ds = D_saved[(D_saved.strategy == st) & (D_saved.sym == s)].set_index("date")
    if not ds.index.equals(days):
        problems.append(f"daily_returns calendar differs {st} {s}")
        continue
    win = np.where(days <= IS_END, "IS", "OOS")
    if not (ds.window.values == win).all():
        problems.append(f"daily_returns window labels differ {st} {s}")
    for c in ["gross", "net1x", "net2x"]:
        mine = own_daily(g, days, c, size[(st, s)])
        sv = ds[f"ret_{c}"].values
        diff = np.abs(mine - sv)
        dmax = max(dmax, diff.max())
        nz = np.abs(mine) > 0
        if nz.any():
            dmax_rel = max(dmax_rel, (diff[nz] / np.abs(mine[nz])).max())
        with np.errstate(divide="ignore"):
            half_ulp8 = np.where(mine != 0, 0.5 * 10.0 ** (np.floor(np.log10(np.abs(mine) + (mine == 0))) - 7), 0.0)
        if (diff > half_ulp8 * 1.000001 + 1e-15).any():  # saved with %.8g: half unit in the 8th digit
            problems.append(f"daily_returns {st} {s} {c}: max abs diff {diff.max():.3g} beyond %.8g precision")
notes.append(f"daily_returns.csv vs own rebuild: max abs diff {dmax:.3g}, max rel diff {dmax_rel:.3g} "
             f"(file stored at 8 significant digits)")

# ------------------------------------------------------------------ metric definitions (own implementation)


def mdd(r: np.ndarray) -> tuple[float, float]:
    eq = pd.Series(np.concatenate([[1.0], 1.0 + np.cumsum(r)]))
    pk = eq.cummax()
    dd = (eq / pk - 1.0).iloc[1:]
    return float(dd.min()), float((pk - eq).iloc[1:].max() * CAP)


def series_metrics(r: np.ndarray) -> dict:
    mu, sd = float(np.mean(r)), float(np.std(r, ddof=1))
    a, b = mdd(r)
    return dict(ann_return=mu * ANN, ann_vol=sd * math.sqrt(ANN), sharpe=mu / sd * math.sqrt(ANN) if sd > 0 else np.nan,
                max_drawdown=a, max_drawdown_usd=b, total_return=float(np.sum(r)), total_pnl_usd=float(np.sum(r)) * CAP)


def trade_metrics(gw: pd.DataFrame, cost: str, n_c: int, years: float) -> dict:
    pt = gw[cost].values.astype(float)
    n = len(pt)
    sd = pt.std(ddof=1) if n > 1 else np.nan
    pts = pt.mean() / sd if n > 1 and sd > 0 else np.nan
    return dict(n_trades=n, mean_trade_usd_per_contract=pt.mean() if n else np.nan,
                sd_trade_usd_per_contract=sd, per_trade_sharpe=pts,
                per_trade_sharpe_annualised=pts * math.sqrt(n / years) if n > 1 else np.nan,
                t_stat_trades=pts * math.sqrt(n) if n > 1 else np.nan,
                hit_rate=float((pt > 0).mean()) if n else np.nan, zero_share=float((pt == 0).mean()) if n else np.nan,
                trades_per_year=n / years, contracts_per_year=2 * n_c * n / years,
                notional_per_year_usd=2 * n_c * gw.notional.sum() / years,
                turnover_x_capital_per_year=2 * n_c * gw.notional.sum() / years / CAP,
                notional_per_trade_x_capital=n_c * gw.notional.mean() / CAP if n else np.nan)


def window_bounds(st: str, wname: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    f = first[st]
    table = {"IS": (f, IS_END), "OOS": (OOS0, OOS1),
             "IS: 2016-2022 sample (D1 clean)": (f, pd.Timestamp("2022-12-31")),
             "G3 confirmation sample 2023-02-01..2026-04-29": (pd.Timestamp("2023-02-01"), pd.Timestamp("2026-04-29")),
             "IS: era 2016-2019": (f, pd.Timestamp("2019-12-31")),
             "IS: era 2020-2024-10-02": (pd.Timestamp("2020-01-01"), IS_END)}
    return table[wname]


M = pd.read_csv(RES / "metrics.csv")
NUM = ["trading_days", "years", "N_contracts", "n_trades", "ann_return", "ann_vol", "sharpe", "max_drawdown",
       "max_drawdown_usd", "total_return", "total_pnl_usd", "mean_trade_usd_per_contract", "sd_trade_usd_per_contract",
       "per_trade_sharpe", "per_trade_sharpe_annualised", "t_stat_trades", "hit_rate", "zero_share", "trades_per_year",
       "contracts_per_year", "notional_per_year_usd", "turnover_x_capital_per_year", "notional_per_trade_x_capital"]


def tol6(ref: float) -> float:
    """Tolerance for a value stored with %.6g: max(1e-6 relative, half unit in the 6th significant digit)."""
    if ref == 0 or not np.isfinite(ref):
        return 1e-12
    return max(REL * abs(ref), 0.5 * 10 ** (math.floor(math.log10(abs(ref))) - 5) * 1.0000001)


SAVED_VS_FULL = [0.0, None]
BOUNDARY: list[str] = []
cmp_rows = []
mine_full = {}
n_cmp = 0
worst_rel = 0.0
worst_key = None
for r in M.itertuples(index=False):
    st, s, var, wname, cost = r.strategy, r.sym, r.variant, r.window, r.cost
    w0, w1 = window_bounds(st, wname)
    days = CAL[(CAL >= w0) & (CAL <= w1)]
    g = T[(T.strategy == st) & (T.sym == s)]
    if var == "ex_warsh":
        g = g[g.chair != "Warsh"]
    gw = g[(g.date >= w0) & (g.date <= w1)]
    n_c = size[(st, s)]
    years = len(days) / ANN
    rr = own_daily(gw, days, cost, n_c)
    mine = dict(trading_days=len(days), years=years, N_contracts=n_c)
    mine.update(series_metrics(rr))
    mine.update(trade_metrics(gw, cost, n_c, years))
    mine_full[(st, s, var, wname, cost)] = mine
    if str(days.min().date()) != r.start or str(days.max().date()) != r.end:
        problems.append(f"start/end mismatch {st} {s} {var} {wname} {cost}")
    # path (a): from saved daily series where available
    if var == "all" and cost in ("gross", "net1x", "net2x"):
        ds = D_saved[(D_saved.strategy == st) & (D_saved.sym == s) & (D_saved.date >= w0) & (D_saved.date <= w1)]
        sm = series_metrics(ds[f"ret_{cost}"].values)
        for k, v in sm.items():
            ref_full = mine[k]
            rel = abs(v - ref_full) / max(abs(ref_full), 1e-300)
            if rel > SAVED_VS_FULL[0]:
                SAVED_VS_FULL[0], SAVED_VS_FULL[1] = rel, (st, s, wname, cost, k)
            if rel > REL and abs(v - ref_full) > 1e-12:
                problems.append(f"saved-daily vs rebuild {st} {s} {wname} {cost} {k}: {v:.10g} vs {ref_full:.10g} "
                                f"(rel {rel:.2g})")
        for k, v in sm.items():
            ref = getattr(r, k)
            n_cmp += 1
            if abs(v - ref) > tol6(ref):
                if abs(v - ref) <= tol6(ref) + abs(v - mine[k]) * 1.000001:
                    BOUNDARY.append(f"{st} {s} {wname} {cost} {k}: stored {ref}, from saved daily {v:.10g}, "
                                    f"full-precision rebuild {mine[k]:.12g}")
                else:
                    problems.append(f"metrics.csv (from saved daily) {st} {s} {var} {wname} {cost} {k}: "
                                    f"stored {ref} vs recomputed {v:.9g}")
    for k in NUM:
        ref = getattr(r, k)
        v = mine[k]
        n_cmp += 1
        if (pd.isna(ref) and pd.isna(v)):
            continue
        if pd.isna(ref) != pd.isna(v):
            problems.append(f"NaN mismatch {st} {s} {var} {wname} {cost} {k}: stored {ref} vs {v}")
            continue
        rel = abs(v - ref) / max(abs(ref), 1e-300) if ref != 0 else abs(v)
        if rel > worst_rel and ref != 0:
            worst_rel, worst_key = rel, (st, s, var, wname, cost, k, ref, v)
        if abs(v - ref) > tol6(ref):
            problems.append(f"metrics.csv {st} {s} {var} {wname} {cost} {k}: stored {ref} vs recomputed {v:.9g}")
    cmp_rows.append(dict(strategy=st, sym=s, variant=var, window=wname, cost=cost,
                         **{k: mine[k] for k in NUM}))

# completeness: expected metric rows
exp = set()
for st in ["H1-primary", "BENCH-R"]:
    wins = (["IS", "OOS", "IS: 2016-2022 sample (D1 clean)", "G3 confirmation sample 2023-02-01..2026-04-29"]
            if st == "H1-primary" else ["IS", "OOS", "IS: era 2016-2019", "IS: era 2020-2024-10-02"])
    for s in SYMS:
        g = T[(T.strategy == st) & (T.sym == s)]
        for w in wins:
            w0, w1 = window_bounds(st, w)
            gw = g[(g.date >= w0) & (g.date <= w1)]
            for c in COSTS:
                exp.add((st, s, "all", w, c))
                if (gw.chair == "Warsh").any():
                    exp.add((st, s, "ex_warsh", w, c))
got = set(zip(M.strategy, M.sym, M.variant, M.window, M.cost))
if exp != got:
    problems.append(f"metrics.csv row set differs: missing {sorted(exp - got)[:6]}, extra {sorted(got - exp)[:6]}")

pd.DataFrame(cmp_rows).to_csv(OUTD / "recomputed_metrics.csv", index=False, float_format="%.12g")

# ------------------------------------------------------------------ key_metrics.json (round 6 decimals)
K = json.loads((RES / "key_metrics.json").read_text())
nk = 0
for key, d in K.items():
    st, s, w, c = key.split("|")
    mine = mine_full[(st, s, "all", w, c)]
    for k, v in d.items():
        if k in ("start", "end"):
            continue
        nk += 1
        mv = mine[k]
        if abs(mv - v) > max(5.01e-7, REL * abs(v)):
            problems.append(f"key_metrics.json {key} {k}: stored {v} vs recomputed {mv:.9g}")

# ------------------------------------------------------------------ per_trade.csv
P = pd.read_csv(RES / "per_trade.csv", parse_dates=["date"])
mm = P.merge(T, on=["strategy", "sym", "date"], suffixes=("_f", ""))
if len(mm) != len(T) or len(P) != len(T):
    problems.append(f"per_trade.csv rows {len(P)} vs rebuilt {len(T)}")
for c in ["gross", "net1x", "net2x", "fixed1x", "fixed2x"]:
    d = np.abs(mm[f"{c}_usd"] - mm[c])
    bad = d > np.maximum(np.abs(mm[c]) * 5.01e-6, 1e-9)
    if bad.any():
        problems.append(f"per_trade.csv {c}_usd differs on {int(bad.sum())} rows")
for c in ["gross", "net1x", "net2x"]:
    v = mm[c] * mm["N"]
    d = np.abs(mm[f"{c}_usd_position"] - v)
    bad = d > np.maximum(np.abs(v) * 5.01e-6, 1e-9)
    if bad.any():
        problems.append(f"per_trade.csv {c}_usd_position differs on {int(bad.sum())} rows")
if (mm.N_f != mm.N).any():
    problems.append("per_trade.csv N differs")
if (mm.window_f != mm.window).any():
    problems.append("per_trade.csv window differs")

# ------------------------------------------------------------------ tables.md and README.md (displayed precision)


def pct(x, d=1):
    return f"{x * 100:.{d}f}%"


def f2(x):
    return f"{x:.2f}"


tmd = (RES / "tables.md").read_text(encoding="utf-8")
rmd = (RES / "README.md").read_text(encoding="utf-8")
hl_missing = []
for st in ["H1-primary", "BENCH-R"]:
    for w in ["IS", "OOS"]:
        for c in ["gross", "net1x", "net2x"]:
            x = mine_full[(st, "ZT", "all", w, c)]
            row = (f"| {st} | {w} | ")
            tail = (f"| {c} | {x['n_trades']} | {pct(x['ann_return'])} | {pct(x['ann_vol'])} | {f2(x['sharpe'])} | "
                    f"{f2(x['per_trade_sharpe'])} | {pct(x['max_drawdown'])} | {pct(x['hit_rate'], 0)} | "
                    f"{x['contracts_per_year']:,.0f} | ${x['notional_per_year_usd'] / 1e9:,.1f}bn | "
                    f"{x['turnover_x_capital_per_year']:,.0f} |")
            for name, txt in [("tables.md", tmd), ("README.md", rmd)]:
                if tail not in txt:
                    hl_missing.append(f"{name}: {st} {w} {c} -> expected '{tail}'")
problems += [f"headline table text mismatch: {x}" for x in hl_missing]

# Sharpe-by-symbol table
for st in ["H1-primary", "BENCH-R"]:
    for s in SYMS:
        g = lambda w, c, v="all": mine_full[(st, s, v, w, c)]
        ex = mine_full.get((st, s, "ex_warsh", "OOS", "net1x"), g("OOS", "net1x"))
        line = (f"| {st} | {s} | {size[(st, s)]:,} | {g('IS', 'gross')['n_trades']} | {f2(g('IS', 'gross')['sharpe'])} | "
                f"{f2(g('IS', 'net1x')['sharpe'])} | {f2(g('IS', 'net2x')['sharpe'])} | {g('OOS', 'gross')['n_trades']} | "
                f"{f2(g('OOS', 'gross')['sharpe'])} | {f2(g('OOS', 'net1x')['sharpe'])} | {f2(g('OOS', 'net2x')['sharpe'])} | "
                f"{f2(ex['sharpe'])} |")
        if line not in tmd:
            problems.append(f"tables.md Sharpe-by-symbol row mismatch: expected '{line}'")

# detail rows in tables.md: every window/cost row per strategy/symbol (all variant)
det_bad = 0
det_n = 0
for (st, s, var, w, c), x in mine_full.items():
    if var != "all":
        continue
    if c.startswith("fixed") and (w not in ("IS", "OOS") or s == "ZF"):
        continue  # tables.md shows fixed-tick rows for headline windows only, and none for ZF (identical to net)
    det_n += 1
    line = (f"| {w} | {c} | {x['n_trades']} | {pct(x['ann_return'])} | {pct(x['ann_vol'])} | {f2(x['sharpe'])} | "
            f"{f2(x['per_trade_sharpe'])} | {pct(x['max_drawdown'])} | {pct(x['hit_rate'], 0)} | "
            f"{x['mean_trade_usd_per_contract']:.1f} | {x['contracts_per_year']:,.0f} | "
            f"{x['turnover_x_capital_per_year']:,.0f} |")
    if line not in tmd:
        det_bad += 1
        problems.append(f"tables.md detail row not found: {st} {s} -> '{line}'")
notes.append(f"tables.md detail rows checked: {det_n}, not found: {det_bad}")
# ZF: fixed-tick rows claimed identical to net rows
zf = T[T.sym == "ZF"]
if not (np.allclose(zf.fixed1x, zf.net1x, atol=1e-9) and np.allclose(zf.fixed2x, zf.net2x, atol=1e-9)):
    problems.append("ZF fixed-tick rows are not identical to net rows (tables.md says they are)")
# README tables: every table line must appear in tables.md
tlines = set(l.strip() for l in tmd.splitlines() if l.strip().startswith("|"))
rlines = [l.strip() for l in rmd.splitlines() if l.strip().startswith("|") and not l.strip().startswith("|---")]
r_missing = [l for l in rlines if l not in tlines]
notes.append(f"README.md table lines: {len(rlines)}, not present in tables.md: {len(r_missing)}")
for l in r_missing[:10]:
    notes.append(f"README-only table line: {l}")

# ------------------------------------------------------------------ claims in the build report
claims = {}
zt = T[(T.strategy == "H1-primary") & (T.sym == "ZT")]
g3 = zt[zt["sample"] == "confirmation"]
claims["G3 n=20 mean +0.50 ticks"] = (len(g3) == 20 and abs(g3.gticks.mean() - 0.5) < 1e-12, len(g3), g3.gticks.mean())
g3w = zt[(zt.date >= pd.Timestamp("2023-02-01")) & (zt.date <= pd.Timestamp("2026-04-29"))]
claims["G3 date window == confirmation sample"] = (set(g3w.date) == set(g3.date), len(g3w), len(g3))
claims["IS vol with N in [9.98%,10.01%]"] = (bool(((SZ.vol_N >= 0.0998) & (SZ.vol_N <= 0.10011)).all()),
                                           float(SZ.vol_N.min()), float(SZ.vol_N.max()))
z = T[T.sym == "ZT"]
claims["ZT measured spread = 1 tick on every trade"] = (bool((z.spread_ticks == 1).all()),
                                                       sorted(z.spread_ticks.unique().tolist()))
zn = T[T.sym == "ZN"]
claims["ZN measured spread = 1 tick on every trade"] = (bool((zn.spread_ticks == 1).all()),
                                                       sorted(zn.spread_ticks.unique().tolist()))
es = T[T.sym == "ES"]
claims["ES spread 1..2.5 ticks"] = (bool(es.spread_ticks.between(1, 2.5).all()), sorted(es.spread_ticks.unique().tolist()))
claims["ZT cost per contract RT values"] = (None, sorted((z.gross - z.net1x).round(6).unique().tolist()))
claims["H1 ZT face notional per trade x capital = 95.76"] = (abs(size[("H1-primary", "ZT")] * 2e5 / CAP - 95.76) < 1e-9,
                                                           size[("H1-primary", "ZT")] * 2e5 / CAP)
warsh = T[(T.chair == "Warsh")]
claims["Warsh meetings in OOS (per strategy/sym)"] = (None, warsh.groupby(["strategy", "sym"]).size().to_dict())
cap = pd.read_csv(RES / "capacity_top_of_book.csv")
c1r = cap[(cap.strategy == "H1-primary") & (cap.sym == "ZT") & (cap.window == "all") & (cap.leg == "entry")]
c2r = cap[(cap.strategy == "H1-primary") & (cap.sym == "ES") & (cap.window == "all") & (cap.leg == "entry")]
claims["capacity H1 ZT median entry size 518"] = (float(c1r.median_displayed_size.iloc[0]) == 518,
                                                  float(c1r.median_displayed_size.iloc[0]))
claims["capacity H1 ES median entry ~22"] = (abs(float(c2r.median_displayed_size.iloc[0]) - 22) <= 1,
                                             float(c2r.median_displayed_size.iloc[0]))
capn = cap.merge(pd.DataFrame([dict(strategy=a, sym=b, Nm=v) for (a, b), v in size.items()]), on=["strategy", "sym"])
claims["capacity N_contracts == sizing N"] = (bool((capn.N_contracts == capn.Nm).all()), None)
# median and ratio are stored with 4 significant digits: allow the median's display rounding (+-0.5 unit, 4th digit)
med = capn.median_displayed_size.values
hu = 0.5 * 10.0 ** (np.floor(np.log10(med)) - 3)
lo, hi = capn.N_contracts / (med + hu), capn.N_contracts / (med - hu)
rq = capn.N_over_median.values
rhu = 0.5 * 10.0 ** (np.floor(np.log10(rq)) - 3)
ratio_ok = bool(((rq + rhu >= lo - 1e-12) & (rq - rhu <= hi + 1e-12)).all())
claims["capacity N_over_median == N/median"] = (ratio_ok, None)
cnt = cap.groupby(["strategy", "sym", "window", "leg"]).n_trades.first()
nt_ok = True
for (st, s, w, leg), n in cnt.items():
    g = T[(T.strategy == st) & (T.sym == s)]
    if w != "all":
        g = g[g.window == w]
    nt_ok &= (len(g) == n)
claims["capacity n_trades consistent with trade logs"] = (nt_ok, None)
for k, v in claims.items():
    if v[0] is False:
        problems.append(f"claim not reproduced: {k}: {v[1:]}")

# report-text Sharpe claims at 2 dp
txt_claims = {
    ("H1-primary", "ZT", "IS", "net1x"): -0.17, ("H1-primary", "ZT", "OOS", "net1x"): -1.33,
    ("H1-primary", "ZT", "IS", "gross"): 0.19, ("H1-primary", "ZT", "OOS", "gross"): -0.79,
    ("BENCH-R", "ZT", "IS", "net1x"): -0.51, ("BENCH-R", "ZT", "OOS", "net1x"): 0.18,
    ("BENCH-R", "ZT", "OOS", "net2x"): -0.02, ("BENCH-R", "ES", "IS", "net1x"): 0.12,
    ("BENCH-R", "ES", "OOS", "net1x"): 0.71,
    ("BENCH-R", "ZT", "IS: era 2016-2019", "net1x"): 0.20, ("BENCH-R", "ZT", "IS: era 2020-2024-10-02", "net1x"): -0.81,
    ("H1-primary", "ZT", "IS: 2016-2022 sample (D1 clean)", "gross"): 0.11,
    ("H1-primary", "ZT", "IS: 2016-2022 sample (D1 clean)", "net1x"): -0.45,
    ("H1-primary", "ZT", "IS: 2016-2022 sample (D1 clean)", "net2x"): -0.95,
    ("H1-primary", "ZT", "G3 confirmation sample 2023-02-01..2026-04-29", "gross"): 0.10,
    ("H1-primary", "ZT", "G3 confirmation sample 2023-02-01..2026-04-29", "net1x"): -0.20,
    ("H1-primary", "ZT", "G3 confirmation sample 2023-02-01..2026-04-29", "net2x"): -0.48,
    ("BENCH-R", "ZT", "IS: era 2016-2019", "gross"): 0.48, ("BENCH-R", "ZT", "IS: era 2016-2019", "net2x"): -0.09,
    ("BENCH-R", "ZT", "IS: era 2020-2024-10-02", "gross"): -0.69,
    ("BENCH-R", "ZT", "IS: era 2020-2024-10-02", "net2x"): -0.93,
}
for (st, s, w, c), v in txt_claims.items():
    x = mine_full[(st, s, "all", w, c)]["sharpe"]
    if f"{x:.2f}" != f"{v:.2f}":
        problems.append(f"report Sharpe claim {st} {s} {w} {c}: report {v:.2f} vs recomputed {x:.4f}")

out = dict(n_metric_rows=len(M), n_values_compared_metrics_csv=n_cmp, n_values_compared_key_metrics=nk,
           worst_rel_diff_vs_metrics_csv=dict(rel=worst_rel, key=[str(a) for a in worst_key] if worst_key else None),
           checks_trade_reconstruction=chk, claims={k: [str(a) for a in v] for k, v in claims.items()},
           saved_daily_vs_full_rebuild_max_rel=SAVED_VS_FULL, rounding_boundary_cases=BOUNDARY,
           notes=notes, problems=problems)
(OUTD / "verify_result.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out, indent=1, default=str))
