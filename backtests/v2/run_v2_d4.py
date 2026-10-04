"""Deviation D-4 (preregistration/v2_DEVIATION_D4_FIXES.md): the two implementation fixes, the matched and simple
benchmarks and the walk-forward selection, computed descriptively beside the committed v2 results.

    cd <GQH_REPO>
    GQH_REPO=<gqh-flow-clock> GQH_DATA_DIR=<data cache> V2_WORK_ROOT=<v2 work root> \
      V2_D4_NOTE=<team repo>/preregistration/v2_DEVIATION_D4_FIXES.md PYTHONIOENCODING=utf-8 \
      <python> <team repo>/backtests/v2/run_v2_d4.py

Runs only when V2_D4_NOTE names preregistration/v2_DEVIATION_D4_FIXES.md and that file has the pinned sha256 (the
note was committed before anything it authorises was computed). Refuses V2_OOS_DEVIATION, GQH_OOS_UNLOCK and
V2_FIX_SIZING (fix 1 is set explicitly for every row here). Writes only to backtests/results/v2_d4 and never a decision
record: nothing is chosen, the registered verdict (decision rule FAILED) stands, and the committed results in
backtests/results/v2 and backtests/results/v2_oos stay the first, reported results.

Fixes (switches; both off = the committed code path):
  fix 1  v2lib.weights_E1(..., fix_sizing=True): the vol for the position entered at the open of session t uses
         open-to-open returns ending at open t-1 (one more session of lag), never the open-t fill price.
  fix 2  sim_fixed.simulate: holdings carried as shares and cash through the intraday and overnight moves; the next
         open's trade and cost are measured from the drifted holdings (E1, exec next_open). E2 (next_close) already
         carries the drift and is unchanged; fix 1 does not apply to E2 either (its vol ends at the decision close).

Computed (in-sample windows from the in-sample run, as committed; the out-of-sample window from the full-period run):
  * T4xE1 and Variant A (T0fxE1): original, fix1, fix2, both; selection, validation, full in-sample, out-of-sample;
  * the portfolio test core_ER_6 + T4xE1 with each T4xE1 variant (the core sleeves are the committed ones);
  * matched benchmarks LEXALLxE1 (T4's lexicon leg alone), T2xE1 (its stance-model leg alone), T0v2xE1;
  * simple benchmarks: rate momentum M (T3's regressor) traded alone, the long 75/25 TLT/UUP mix with E1 sizing and
    costs, and an unlevered buy-and-hold of 75/25 TLT/UUP (entry cost only);
  * walk-forward selection among the registered eight combinations (original; and fixed = both fixes on E1).
With the switches off every comparable number is checked against the committed files (consistency.json).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent                  # backtests/v2
BTS = HERE.parent
TEAM = BTS.parent
D4_NOTE = TEAM / "preregistration" / "v2_DEVIATION_D4_FIXES.md"
D4_SHA = "0edbf18962dac25534d49b47db8a7d02e08a1948217889e94b8ef9ae0371cd23"
OUT = BTS / "results" / "v2_d4"
COMMITTED_IS = BTS / "results" / "v2"
COMMITTED_RUN = BTS / "results" / "v2_oos" / "run"
DECISION_RECORDS = {"oos_chosen.json", "oos_not_evaluated.json", "oos_reproduced.json",
                    "oos_not_evaluated_reproduced.json"}
R = L = SF = None                                       # run_v2, v2lib, sim_fixed (imported after the gate)


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def d4_authorised() -> bool:
    p = os.environ.get("V2_D4_NOTE")
    return bool(p) and Path(p).resolve() == D4_NOTE.resolve() and D4_NOTE.is_file() and sha256(D4_NOTE) == D4_SHA


def gate() -> None:
    if not d4_authorised():
        raise SystemExit(f"refusing: V2_D4_NOTE must name {D4_NOTE.relative_to(TEAM).as_posix()} at sha256 {D4_SHA} "
                         f"(V2_D4_NOTE={os.environ.get('V2_D4_NOTE')!r}). Nothing computed.")
    for var in ("V2_OOS_DEVIATION", "GQH_OOS_UNLOCK", "V2_FIX_SIZING"):
        if var in os.environ:
            raise SystemExit(f"refusing: unset {var} (D-4 never uses the D-3 unlock or the engine's OOS unlock, and "
                             "sets fix 1 explicitly per row). Nothing computed.")


def out_path(name: str) -> Path:
    """The only way this script writes: a plain file name inside backtests/results/v2_d4, never a decision record."""
    p = (OUT / name).resolve()
    if name in DECISION_RECORDS or Path(name).name != name or p.parent != OUT.resolve():
        raise SystemExit(f"refusing to write {name}: D-4 writes only plain files in {OUT} and no decision record")
    return p


def jdump(obj, name: str) -> None:
    out_path(name).write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


# ----------------------------------------------------------------------------- definitions
VARIANTS = [("original", False, False), ("fix1", True, False), ("fix2", False, True), ("both", True, True)]
SERIES = {  # name -> (group, description)
    "T4xE1": ("strategy", "the chosen combination: 0.5 x (z lexicon + z stance model) on all documents, E1"),
    "T0fxE1": ("strategy", "Variant A as frozen (strategy 01 corpus and z clock from 2011), the reference"),
    "LEXALLxE1": ("matched_benchmark", "T4's lexicon leg alone: z of the all-document lexicon consensus, E1"),
    "T2xE1": ("matched_benchmark", "T4's stance-model leg alone: z of the all-document stance consensus, E1"),
    "T0v2xE1": ("matched_benchmark", "Variant A's lexicon on speeches with the v2 2015 warm-up, E1"),
    "MxE1": ("simple_benchmark", "rate momentum M (T3's regressor: 20-session decayed DGS2 change, lag 2) alone, "
                                 "expanding z, E1"),
    "BH7525volxE1": ("simple_benchmark", "long 75% TLT + 25% UUP held constantly, E1 sizing (10% vol target, floor, "
                                         "cap, band, FOMC rule) and costs"),
}
BH_HOLD = "BH7525hold"
BH_HOLD_DESC = "buy-and-hold 75% TLT + 25% UUP, unlevered, bought at the open of the first E1 position, never rebalanced"
WINDOWS_IS = (("selection", "SEL"), ("validation", "VAL"), ("full_is", "FULL_IS"))
YEAR_ENDS = (2020, 2021, 2022, 2023, 2024, 2025)


def expr_long_mix():
    """E1 instruments and costs with fx_sign -1: with a constant signal of -1, v2lib.size gives +0.75k TLT and
    +0.25k UUP (long both), and the vol is that of the long 75/25 mix (the sign of the mix does not change its sd)."""
    e1 = L.EXPRS["E1"]
    return L.Expr("E1_long_mix", e1.rate, e1.fx, -1.0, e1.exec, dict(e1.cost_bps))


def frame(n1, g, t1, held, c1, n2, rf, ex) -> pd.DataFrame:
    """The columns of run_v2.simulate."""
    r = rf.reindex(n1.index).fillna(0.0)
    out = pd.DataFrame({"net": n1, "gross": g, "rf": r, "ex1": n1 - r, "ex2": n2 - r, "exg": g - r,
                        "turnover": t1, "cost": c1, "w_rate": held[ex.rate], "w_fx": held[ex.fx]})
    out["gross_exposure"] = held.abs().sum(axis=1)
    return out


def sim_e1(w: pd.DataFrame, ohlc: dict, rf: pd.Series, fix2: bool) -> pd.DataFrame:
    if not fix2:
        return R.simulate(w, "E1", ohlc, rf)            # the committed path: the shared engine
    ex = L.EXPRS["E1"]
    n1, g, t1, held, c1 = SF.simulate(w, ohlc, rf, exec=ex.exec, cost_bps=ex.cost_bps)
    n2, _, _, _, _ = SF.simulate(w, ohlc, rf, exec=ex.exec, cost_bps=ex.cost_bps, cost_mult=2.0)
    return frame(n1, g, t1, held, c1, n2, rf, ex)


def weights_e1(z: pd.Series, ohlc: dict, fomc: pd.Series, fix1: bool, ex=None):
    ex = ex or L.EXPRS["E1"]
    fs = L.fomc_day_s(z.index, fomc)
    return L.weights_E1(z, ohlc["open"][[ex.rate, ex.fx]], fs, ex, fix_sizing=fix1)


def bh_hold(ohlc: dict, rf: pd.Series, start: pd.Timestamp) -> pd.DataFrame:
    """Unlevered buy-and-hold: 75% TLT / 25% UUP bought at the open of `start` (NAV 1), never rebalanced; the entry
    costs 0.75 x 1.5 + 0.25 x 5 bp once (x2 for 2x); no cash, so the excess return is the return minus the T-bill."""
    e1 = L.EXPRS["E1"]
    t = [e1.rate, e1.fx]
    w = np.array([0.75, 0.25])
    cb = np.array([e1.cost_bps[x] for x in t]) / 1e4
    close, open_ = ohlc["close"][t].ffill(limit=5), ohlc["open"][t].ffill(limit=5)
    idx = close.index
    rf = rf.reindex(idx).ffill().fillna(0.0)
    i0 = idx.get_loc(start)
    sh = w / open_.iloc[i0].to_numpy(float)
    hv = close.iloc[i0:].to_numpy(float) * sh          # holding values (NAV units), from the start session
    val = hv.sum(axis=1)
    g = np.zeros(len(idx))
    g[i0] = val[0] - 1.0
    g[i0 + 1:] = val[1:] / val[:-1] - 1.0
    cost = np.zeros(len(idx))
    cost[i0] = float(w @ cb)
    turn = np.zeros(len(idx))
    turn[i0] = 1.0
    wts = np.zeros((len(idx), 2))
    wts[i0:] = hv / val[:, None]
    g, cost = pd.Series(g, index=idx), pd.Series(cost, index=idx)
    out = pd.DataFrame({"net": g - cost, "gross": g, "rf": rf, "ex1": g - cost - rf, "ex2": g - 2 * cost - rf,
                        "exg": g - rf, "turnover": turn, "cost": cost, "w_rate": wts[:, 0], "w_fx": wts[:, 1]},
                       index=idx)
    out["gross_exposure"] = np.abs(wts).sum(axis=1)
    return out


# ----------------------------------------------------------------------------- one period (IS or FWD)
def build_period(period: str, docs: pd.DataFrame, ext: pd.DataFrame, fomc: pd.Series) -> dict:
    ohlc, rf, dgs2, cal = R.market(period)
    if period == "IS":                                  # as run_v2.pipeline_is
        docs = docs[docs["date"] <= R.IS_END]
        ext = ext[ext["speech_date"] <= R.IS_END]
    sig = R.build_signals(docs, ext, cal, dgs2)
    start = sig["Z"]["T4"].first_valid_index()          # 2015-12-31: first valid v2 z, first E1 position
    z = {"T4xE1": sig["Z"]["T4"], "T0fxE1": sig["Z"]["T0f"], "LEXALLxE1": sig["z_lexall"], "T2xE1": sig["Z"]["T2"],
         "T0v2xE1": sig["Z"]["T0v2"], "MxE1": L.expanding_z(sig["M"], R.V2_CLOCK),
         "BH7525volxE1": pd.Series(np.where(cal >= start, -1.0, np.nan), index=cal)}
    sims = {}
    for name, zz in z.items():
        ex = expr_long_mix() if name == "BH7525volxE1" else None
        for v, f1, f2 in VARIANTS:
            w, _ = weights_e1(zz, ohlc, fomc, f1, ex)
            sims[(name, v)] = sim_e1(w, ohlc, rf, f2)
    wts = {}                                            # decision-date weights of the registered eight
    for t in R.SIGNALS:                                 # the registered eight (walk-forward and consistency checks)
        for v, f1, f2 in (("original", False, False), ("both", True, True)):
            w, _ = weights_e1(sig["Z"][t], ohlc, fomc, f1)
            wts[(f"{t}xE1", v)] = w
            if (f"{t}xE1", v) not in sims:
                sims[(f"{t}xE1", v)] = sim_e1(w, ohlc, rf, f2)
        w, _ = R.combo_weights(sig["Z"][t], "E2", ohlc, fomc)
        wts[(f"{t}xE2", "original")] = w
        sims[(f"{t}xE2", "original")] = R.simulate(w, "E2", ohlc, rf)
    sims[(BH_HOLD, "hold")] = bh_hold(ohlc, rf, start)
    return {"sims": sims, "start": start, "z": z, "first_valid_z_M": z["MxE1"].first_valid_index(),
            "wts": wts, "ohlc": ohlc, "rf": rf}


# ----------------------------------------------------------------------------- metrics
def strat_row(sim: pd.DataFrame, win) -> dict:
    return R.stats_row(sim, win)                        # never includes days before the first held position


def port_row(ret: pd.DataFrame, ov_to: pd.Series, fed_to: pd.Series | None, win) -> dict:
    s = slice(pd.Timestamp(win[0]), pd.Timestamp(win[1]))
    x1 = ret["net_1x"].loc[s].dropna()
    if len(x1) < 21:
        return {}
    yrs = len(x1) / L.ANN
    row = L.window_stats(ret["net_1x"], ret["net_2x"], ret["gross"], ov_to.fillna(0.0), x1.index[0], x1.index[-1])
    if fed_to is not None:
        row["fed_sleeve_turnover_per_year"] = float(fed_to.reindex(x1.index).fillna(0.0).sum() / yrs)
    return row


def windows():
    return [(wn, getattr(R, attr)) for wn, attr in WINDOWS_IS] + [("oos", R.OOS)]


# ----------------------------------------------------------------------------- portfolio
def portfolios(is_sims: dict, fwd_sims: dict):
    e1 = L.EXPRS["E1"]
    cbp = 0.75 * e1.cost_bps["TLT"] + 0.25 * e1.cost_bps["UUP"]   # 2.375 bp, as run_v2.pipeline_is
    rows, daily, info = [], {}, {}
    for v, _, _ in VARIANTS:
        for per, sims, end, wins in (("IS", is_sims, R.IS_END, windows()[:3]), ("FWD", fwd_sims, R.OOS[1],
                                                                                  windows()[3:])):
            sl = sims[("T4xE1", v)]
            base, aug, pinfo = R.portfolio(sl, cbp, end, "T4xE1")
            info[f"{v}|{per}"] = pinfo
            fed_to = aug["m"]["FED_T4xE1"] * sl["turnover"].reindex(aug["m"].index).fillna(0.0)
            for wn, win in wins:
                if v == "original":
                    rows.append({"group": "portfolio", "series": "core_ER_6", "variant": "as_committed", "window": wn,
                                 **port_row(base["ret"], base["ov_to"], None, win)})
                rows.append({"group": "portfolio", "series": "core_ER_6+T4xE1", "variant": v, "window": wn,
                             **port_row(aug["ret"], aug["ov_to"], fed_to, win)})
            if per == "FWD":
                for c in ("net_1x", "net_2x", "gross"):
                    if v == "original":
                        daily[f"core_ER_6|as_committed|{c}"] = base["ret"][c]
                    daily[f"core_ER_6+T4xE1|{v}|{c}"] = aug["ret"][c]
                if v == "original":
                    daily["core_ER_6|as_committed|turnover"] = base["ov_to"]
                daily[f"core_ER_6+T4xE1|{v}|turnover"] = aug["ov_to"]
    return rows, daily, info


# ----------------------------------------------------------------------------- walk-forward
def walk_forward(p: dict, universe: str):
    """At each year-end Y from 2020, pick the registered combination with the highest net 1x Sharpe from 2016-01-04 to
    Y-12-31 (as run_v2.stats_row: from its first held position); its decision-date weights apply to the decisions
    made from the last session of Y to the session before the last session of Y+1 (to 2026-10-02). The chain is two
    weight paths, one per expression (E1 weights where an E1 pick is in force, E2 weights where an E2 pick is, zero
    elsewhere), each simulated once with its own registered execution (E1 at the next open, E2 at the next close), so
    a switch is filled and charged when that expression can trade and the old holdings earn their returns until
    then; the daily result is the sum of the two books. The first year opens from flat. universe 'fixed': E1 weights
    with fix 1 simulated with fix 2, E2 unchanged."""
    sims, wts, ohlc, rf = p["sims"], p["wts"], p["ohlc"], p["rf"]
    var = {c: ("both" if universe == "fixed" and c.endswith("E1") else "original") for c in R.COMBOS}
    cal = sims[(R.COMBOS[0], "original")].index
    picks, sched = [], pd.Series(index=cal, dtype=object)
    for y in YEAR_ENDS:
        trail = (R.FULL_IS[0], f"{y}-12-31")
        srs = {c: strat_row(sims[(c, var[c])], trail).get("sharpe_net1x", float("nan")) for c in R.COMBOS}
        pick = max(R.COMBOS, key=lambda c: (srs[c] if np.isfinite(srs[c]) else -np.inf, -R.COMBOS.index(c)))
        d_dec = cal[cal <= pd.Timestamp(f"{y}-12-31")][-1]           # last session of Y: the decision close
        sched.loc[d_dec:] = pick
        for c in R.COMBOS:
            picks.append({"universe": universe, "year_end": f"{y}-12-31", "decision_session": str(d_dec.date()),
                          "combo": c, "variant": var[c], "trailing_sharpe_net1x": srs[c], "picked": c == pick})
    books = []
    for e in ("E1", "E2"):
        cols = None
        w = None
        for c in R.COMBOS:
            if not c.endswith(e):
                continue
            wc = wts[(c, var[c])].reindex(cal)
            if w is None:
                cols = list(wc.columns)
                w = pd.DataFrame(0.0, index=cal, columns=cols)
            m = (sched == c).to_numpy()
            w.loc[m, cols] = wc.loc[m, cols].to_numpy()
        if e == "E1":
            books.append(sim_e1(w, ohlc, rf, universe == "fixed"))
        else:
            books.append(R.simulate(w, "E2", ohlc, rf))
    ch = sum(b[["ex1", "ex2", "exg", "turnover"]] for b in books)
    return ch, picks


# ----------------------------------------------------------------------------- consistency (switches off)
def max_abs(a, b) -> float:
    a, b = np.atleast_1d(np.asarray(a, float)), np.atleast_1d(np.asarray(b, float))
    d = np.abs(a - b)
    d[np.isnan(a) & np.isnan(b)] = 0.0
    d[np.isnan(d)] = np.inf
    return float(d.max()) if d.size else 0.0


def frame_diff(x: pd.DataFrame, y: pd.DataFrame) -> float:
    if not x.index.equals(y.index):
        return float("inf")
    cols = [c for c in y.columns if c in x.columns and pd.api.types.is_numeric_dtype(y[c])]
    return max([max_abs(x[c].to_numpy(float), y[c].to_numpy(float)) for c in cols] or [float("inf")])


STAT_KEYS = ("n_days", "sharpe_net1x", "sharpe_net2x", "sharpe_gross", "ann_excess_arith", "ann_excess_geo", "vol",
             "max_dd_excess", "nw_t", "turnover_per_year")


def consistency(is_p: dict, fwd_p: dict, prow: list) -> dict:
    out = {}
    wa = pd.read_csv(COMMITTED_IS / "windows_all.csv", float_precision="round_trip").set_index(["combo", "window"])
    d = []
    for c in R.COMBOS + ["T0fxE1", "T0v2xE1"]:
        for wn, win in windows()[:3]:
            st = strat_row(is_p["sims"][(c, "original")], win)
            d += [max_abs(st[k], wa.loc[(c, wn), k]) for k in STAT_KEYS]
    out["is_windows_all_10_series_vs_committed_windows_all_csv"] = max(d)
    ce = pd.read_parquet(COMMITTED_RUN / "daily_excess_all_combos_is.parquet")
    mine = pd.DataFrame({c: is_p["sims"][(c, "original")]["ex1"] for c in ce.columns}).loc[ce.index[0]:]
    out["is_daily_excess_all_combos_vs_committed"] = frame_diff(mine, ce)
    out["is_daily_T4xE1_vs_committed_daily_T4xE1_is"] = frame_diff(
        is_p["sims"][("T4xE1", "original")], pd.read_parquet(COMMITTED_RUN / "daily_T4xE1_is.parquet"))
    out["fwd_daily_T4xE1_vs_committed_daily_T4xE1_full"] = frame_diff(
        fwd_p["sims"][("T4xE1", "original")], pd.read_parquet(COMMITTED_RUN / "daily_T4xE1_full.parquet"))
    out["fwd_daily_T0fxE1_vs_committed_daily_VariantA_frozen_T0fxE1_full"] = frame_diff(
        fwd_p["sims"][("T0fxE1", "original")],
        pd.read_parquet(COMMITTED_RUN / "daily_VariantA_frozen_T0fxE1_full.parquet"))
    rec = json.loads((COMMITTED_RUN / "oos_chosen.json").read_text(encoding="utf-8"))
    st = strat_row(fwd_p["sims"][("T4xE1", "original")], R.OOS)
    out["oos_T4xE1_vs_committed_oos_chosen_json"] = max(max_abs(st[k], rec[k]) for k in STAT_KEYS)
    pr = pd.DataFrame(prow).set_index(["series", "variant", "window"])
    keys = ("n_days", "sharpe_net1x", "sharpe_net2x", "ann_excess_geo", "vol", "max_dd_excess")
    d = []
    for f, wins in (("portfolio.csv", ("selection", "validation", "full_is")), ("portfolio_oos.csv", ("oos",))):
        cp = pd.read_csv(COMMITTED_IS / f if f == "portfolio.csv" else COMMITTED_RUN / f, float_precision="round_trip").set_index(["portfolio", "window"])
        for name, var in (("core_ER_6", "as_committed"), ("core_ER_6+T4xE1", "original")):
            for wn in wins:
                d += [max_abs(pr.loc[(name, var, wn), k], cp.loc[(name, wn), k]) for k in keys]
    out["portfolio_original_vs_committed_portfolio_csv_and_portfolio_oos_csv"] = max(d)
    out["switches_off_max_abs_diff_vs_committed"] = max(out.values())
    # the in-sample part of every full-period series equals the in-sample run (both runs are point in time)
    cols = ["ex1", "ex2", "exg", "turnover"]
    d = {}
    for key, s in is_p["sims"].items():
        f = fwd_p["sims"][key]
        d["|".join(key)] = max_abs(f.loc[s.index, cols].to_numpy(float), s[cols].to_numpy(float))
    out["fwd_vs_is_run_on_is_dates_max_abs_diff_by_series"] = d
    out["fwd_vs_is_run_on_is_dates_max_abs_diff"] = max(d.values())
    return out


# ----------------------------------------------------------------------------- report writers
def fmt(x, pct=False, nd=3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    return f"{100 * x:.2f}%" if pct else f"{x:.{nd}f}"


def md_rows(df: pd.DataFrame) -> str:
    head = ("| series | variant | window | Sharpe net 1x | net 2x | gross | ann. return (arith) | ann. return (geo) | "
            "vol | max DD | turnover/yr | NW t |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    lines = [f"| {r['series']} | {r['variant']} | {r['window']} | {fmt(r['sharpe_net1x'])} | {fmt(r['sharpe_net2x'])} "
             f"| {fmt(r['sharpe_gross'])} | {fmt(r['ann_excess_arith'], True)} | {fmt(r['ann_excess_geo'], True)} | "
             f"{fmt(r['vol'], True)} | {fmt(r['max_dd_excess'], True)} | {fmt(r['turnover_per_year'], nd=1)} | "
             f"{fmt(r['nw_t'], nd=2)} |" for _, r in df.iterrows()]
    return head + "\n".join(lines) + "\n"


def sharpe_grid(m: pd.DataFrame, series: list, variants: list, wins: list, col="sharpe_net1x") -> str:
    g = m.set_index(["series", "variant", "window"])[col]
    head = "| series | " + " | ".join(f"{v}: {w}" for v in variants for w in wins) + " |\n"
    head += "|---|" + "---|" * (len(variants) * len(wins)) + "\n"
    lines = []
    for s in series:
        cells = [fmt(g.get((s, v, w), float("nan"))) for v in variants for w in wins]
        lines.append(f"| {s} | " + " | ".join(cells) + " |")
    return head + "\n".join(lines) + "\n"


def main() -> None:
    gate()
    global R, L, SF
    sys.path.insert(0, str(HERE))
    import run_v2 as R  # noqa: E402  (imports gqh-flow-clock's src.engine; run mode and stage_oos are never called)
    import v2lib as L  # noqa: E402
    import sim_fixed as SF  # noqa: E402
    import test_sim_fixed as T  # noqa: E402
    if R.REPO.resolve() != Path(os.environ.get("GQH_REPO", R.REPO)).resolve():
        raise SystemExit("refusing: GQH_REPO mismatch")
    t_start = pd.Timestamp.now("UTC").isoformat()
    used = {json.loads((d / "summary_is.json").read_text(encoding="utf-8")).get("doc_scores_sha256")
            for d in (COMMITTED_IS, COMMITTED_RUN)}
    if used != {sha256(R.DOC_SCORES)}:
        raise SystemExit(f"refusing: {R.DOC_SCORES} is not the document-score file the committed runs used")
    OUT.mkdir(parents=True, exist_ok=True)

    # unit tests of the simulators (the reviewer's example among them)
    tests = {}
    for f in (T.test_reviewer_example, T.test_equals_engine_without_intraday_moves_rates_or_costs,
              T.test_equals_explicit_share_ledger, T.test_fix1_switch):
        f()
        tests[f.__name__] = "PASS"
    example = T.reviewer_example()

    docs, ext, fomc = R.load_docs("run"), R.load_ext_speeches("run"), R.load_fomc()
    is_p = build_period("IS", docs, ext, fomc)
    fwd_p = build_period("FWD", docs, ext, fomc)

    # strategies and benchmarks
    rows = []
    for name, (group, _desc) in list(SERIES.items()) + [(BH_HOLD, ("simple_benchmark", BH_HOLD_DESC))]:
        vs = [("hold",)] if name == BH_HOLD else VARIANTS
        for vt in vs:
            v = vt[0]
            for wn, win in windows():
                sim = (fwd_p if wn == "oos" else is_p)["sims"][(name, v)]
                rows.append({"group": group, "series": name, "variant": v, "window": wn, **strat_row(sim, win)})
    prow, pdaily, pinfo = portfolios(is_p["sims"], fwd_p["sims"])
    rows += prow

    # walk-forward (full-period run)
    wf_rows, wf_daily, wf_picks = [], {}, []
    wf_windows = (("wf_is", ("2021-01-01", R.IS_END)), ("oos", R.OOS), ("wf_all", ("2021-01-01", R.OOS[1])))
    for u in ("original", "fixed"):
        ch, picks = walk_forward(fwd_p, u)
        wf_picks += picks
        for wn, (a, b) in wf_windows:
            wf_rows.append({"group": "walk_forward", "series": "WF_max_trailing_sharpe", "variant": u, "window": wn,
                            **L.window_stats(ch["ex1"], ch["ex2"], ch["exg"], ch["turnover"], a, b)})
        for c, col in (("net_1x", "ex1"), ("net_2x", "ex2"), ("gross", "exg"), ("turnover", "turnover")):
            wf_daily[f"WF_max_trailing_sharpe|{u}|{c}"] = ch[col]
    # the registered choice over the same walk-forward windows, for comparison
    for v in ("original", "both"):
        for wn, (a, b) in wf_windows:
            s = fwd_p["sims"][("T4xE1", v)]
            wf_rows.append({"group": "walk_forward", "series": "T4xE1_registered_choice", "variant": v,
                            "window": wn, **L.window_stats(s["ex1"], s["ex2"], s["exg"], s["turnover"], a, b)})
    rows += wf_rows

    cols = ["group", "series", "variant", "window", "start", "end", "n_days", "ann_excess_arith", "ann_excess_geo",
            "vol", "sharpe_net1x", "sharpe_net2x", "sharpe_gross", "max_dd_excess", "turnover_per_year", "nw_t",
            "fed_sleeve_turnover_per_year"]
    m = pd.DataFrame(rows).reindex(columns=cols)
    m.to_csv(out_path("metrics.csv"), index=False)
    pd.DataFrame(wf_picks).to_csv(out_path("walk_forward_picks.csv"), index=False)

    cons = consistency(is_p, fwd_p, prow)
    cons["portfolio_info"] = pinfo
    jdump(cons, "consistency.json")

    # daily returns (excess of the T-bill; no prices), full-period run, from the first E1 position to 2026-10-02
    start = fwd_p["start"]
    dcols = {}
    for name in list(SERIES) + [BH_HOLD]:
        for vt in ([("hold",)] if name == BH_HOLD else VARIANTS):
            s = fwd_p["sims"][(name, vt[0])]
            for c, col in (("net_1x", "ex1"), ("net_2x", "ex2"), ("gross", "exg"), ("turnover", "turnover")):
                dcols[f"{name}|{vt[0]}|{c}"] = s[col]
    dcols.update(pdaily)
    dcols.update(wf_daily)
    daily = pd.DataFrame(dcols).sort_index().loc[start:R.OOS[1]]
    lab = pd.Series("pre_selection", index=daily.index)
    for wn, (a, b) in (("selection", R.SEL), ("validation", R.VAL), ("oos", R.OOS)):
        lab[(daily.index >= pd.Timestamp(a)) & (daily.index <= pd.Timestamp(b))] = wn
    daily.insert(0, "window", lab)
    daily.index.name = "date"
    daily.to_parquet(out_path("daily_returns.parquet"))
    net1 = ["window"] + [c for c in daily.columns if c.endswith("|net_1x")]
    daily[net1].to_csv(out_path("daily_returns_net1x.csv"), float_format="%.10g")

    jdump({"reviewer_example": example, "unit_tests": tests,
           "note": "$100, $50 in an asset, +10% open to close, then +10% close to open: held as shares the account is "
                   "worth $110.50 at the next open (corrected simulator); the shared engine gives $110.25"},
          "sim_fixed_unit_test.json")

    t_end = pd.Timestamp.now("UTC").isoformat()
    code = {p: sha256(HERE / p) for p in ("run_v2_d4.py", "sim_fixed.py", "v2lib.py", "run_v2.py",
                                          "test_sim_fixed.py")}
    code["gqh-flow-clock src/engine.py"] = sha256(Path(R.E.__file__))
    inputs = {"backtests/v2/score/doc_scores.parquet": sha256(R.DOC_SCORES)}
    for n in ("etf_daily.parquet", "futures_daily.parquet", "futures_1600.parquet", "fred_daily.parquet",
              "rf_daily.parquet"):
        p = Path(R.E.C.DATA_DIR) / n
        if p.is_file():
            inputs[f"data cache {n}"] = sha256(p)
    for p in (R.FOMC_VA, R.FOMC_S01, R.EXT_SPEECH, R.COMBINE_PY, R.CORE6):
        inputs[f"<v2 work root>/{p.relative_to(R.WORK).as_posix()}"] = sha256(p)
    info = {"deviation": f"{D4_NOTE.relative_to(TEAM).as_posix()} sha256 {D4_SHA}",
            "start_utc": t_start, "end_utc": t_end, "code_sha256": code, "inputs_sha256": inputs,
            "first_e1_position": str(start.date()), "first_valid_z_M": str(fwd_p["first_valid_z_M"].date()),
            "windows": {"selection": R.SEL, "validation": R.VAL, "full_is": R.FULL_IS, "oos": R.OOS},
            "decision_records_written": [], "reproduce_check": reproduce_check(code["v2lib.py"])}
    write_reports(m, pd.DataFrame(wf_picks), cons, example, info)
    info["outputs"] = sorted({p.name for p in OUT.iterdir()} | {"run_info.json"})
    jdump(info, "run_info.json")
    print(json.dumps({k: v for k, v in cons.items() if not isinstance(v, dict)}, indent=1))
    print(out_path("metrics.md").read_text(encoding="utf-8")[:6000])


def reproduce_check(v2lib_sha: str) -> dict:
    """Optional: V2_D4_REPRODUCE_REPORT names the reproduce_report.json of a `run_v2_chrono.py --reproduce` run made
    with the current code (switches off). Its verdict and per-comparison differences are quoted; the run must have
    used this v2lib.py (sha256 in its code list)."""
    p = os.environ.get("V2_D4_REPRODUCE_REPORT")
    if not p:
        return {"given": False}
    rep = json.loads(Path(p).read_text(encoding="utf-8"))
    used = (rep.get("code_and_inputs_vs_run_log") or {}).get("backtests/v2/v2lib.py", {}).get("now")
    return {"given": True, "verdict": rep.get("verdict"), "reproduced_utc": rep.get("reproduced_utc"),
            "v2lib_sha256_in_that_run": used, "same_v2lib_as_this_run": used == v2lib_sha,
            "comparisons": [{"label": c["label"], "n_agree": c["n_agree"], "n_files": c["n_files"],
                             "max_abs_diff": c["max_abs_diff"]} for c in rep.get("comparisons", [])],
            "failures": rep.get("failures", [])}


def write_reports(m: pd.DataFrame, picks: pd.DataFrame, cons: dict, example: dict, info: dict) -> None:
    g = m.set_index(["series", "variant", "window"])

    def sr(s, v, w, col="sharpe_net1x"):
        try:
            return float(g.loc[(s, v, w), col])
        except KeyError:
            return float("nan")
    P = picks[picks["picked"]].copy()
    pick_tab = "| decided at | traded | original universe | fixed universe |\n|---|---|---|---|\n"
    for ye in sorted(P["year_end"].unique()):
        po = P[(P["year_end"] == ye) & (P["universe"] == "original")].iloc[0]
        pf = P[(P["year_end"] == ye) & (P["universe"] == "fixed")].iloc[0]
        pick_tab += (f"| {po['decision_session']} | {po['combo']} (trailing {fmt(po['trailing_sharpe_net1x'])}) "
                     f"| {pf['combo']} (trailing {fmt(pf['trailing_sharpe_net1x'])}) |\n")

    head = []
    head.append("| | original | fix 1 | fix 2 | both fixes |\n|---|---|---|---|---|\n")
    for lab, s, w, col in (("T4xE1 Sharpe net 1x, full in-sample", "T4xE1", "full_is", "sharpe_net1x"),
                           ("T4xE1 Sharpe net 2x, full in-sample (rule: > 0.5)", "T4xE1", "full_is", "sharpe_net2x"),
                           ("T4xE1 Sharpe net 1x, selection", "T4xE1", "selection", "sharpe_net1x"),
                           ("T4xE1 Sharpe net 1x, validation", "T4xE1", "validation", "sharpe_net1x"),
                           ("T4xE1 Sharpe net 1x, out-of-sample", "T4xE1", "oos", "sharpe_net1x"),
                           ("T4xE1 Sharpe net 2x, out-of-sample", "T4xE1", "oos", "sharpe_net2x"),
                           ("Variant A (T0fxE1) Sharpe net 1x, full in-sample", "T0fxE1", "full_is", "sharpe_net1x"),
                           ("Variant A (T0fxE1) Sharpe net 1x, out-of-sample", "T0fxE1", "oos", "sharpe_net1x"),
                           ("core_ER_6+T4xE1 Sharpe net 1x, out-of-sample", "core_ER_6+T4xE1", "oos", "sharpe_net1x"),
                           ("core_ER_6+T4xE1 Sharpe net 2x, out-of-sample", "core_ER_6+T4xE1", "oos", "sharpe_net2x")):
        head.append(f"| {lab} | " + " | ".join(fmt(sr(s, v, w, col)) for v in ("original", "fix1", "fix2", "both"))
                    + " |\n")
    head.append(f"\ncore_ER_6 alone (as committed), out-of-sample Sharpe net 1x {fmt(sr('core_ER_6', 'as_committed', 'oos'))}, "
                f"net 2x {fmt(sr('core_ER_6', 'as_committed', 'oos', 'sharpe_net2x'))}.\n")
    bench = sharpe_grid(m, ["T4xE1", "LEXALLxE1", "T2xE1", "T0v2xE1", "T0fxE1", "MxE1", "BH7525volxE1"],
                        ["original", "both"], ["full_is", "oos"])
    bh = (f"Buy-and-hold 75/25 TLT/UUP (unlevered, never rebalanced): Sharpe net 1x full in-sample "
          f"{fmt(sr(BH_HOLD, 'hold', 'full_is'))}, out-of-sample {fmt(sr(BH_HOLD, 'hold', 'oos'))}; vol "
          f"{fmt(sr(BH_HOLD, 'hold', 'full_is', 'vol'), True)} / {fmt(sr(BH_HOLD, 'hold', 'oos', 'vol'), True)}.\n")
    wf = "| | in-sample part 2021-01-04 .. 2024-10-02 | out-of-sample 2024-10-03 .. 2026-10-02 | 2021 .. 2026 |\n|---|---|---|---|\n"
    for s, v, lab in (("WF_max_trailing_sharpe", "original", "walk-forward, original"),
                      ("WF_max_trailing_sharpe", "fixed", "walk-forward, fixed (both fixes on E1)"),
                      ("T4xE1_registered_choice", "original", "T4xE1 (registered choice), original"),
                      ("T4xE1_registered_choice", "both", "T4xE1 (registered choice), both fixes")):
        wf += f"| {lab}: Sharpe net 1x / net 2x | " + " | ".join(
            f"{fmt(sr(s, v, w))} / {fmt(sr(s, v, w, 'sharpe_net2x'))}" for w in ("wf_is", "oos", "wf_all")) + " |\n"

    headline = ("## Headline (descriptive; the registered verdict, decision rule FAILED, stands)\n\n"
                + "".join(head) + "\n### Matched and simple benchmarks, Sharpe net 1x (original and both fixes)\n\n"
                + bench + "\n" + bh + "\n### Walk-forward selection (post hoc robustness)\n\n" + pick_tab + "\n" + wf)

    md = ["# v2 deviation D-4: metrics (generated by backtests/v2/run_v2_d4.py)\n\n",
          "Daily returns in excess of the 3-month T-bill, 252 days a year. Turnover: strategies, one-way fraction of NAV "
          "per year; portfolios, overlay turnover per year. Every row is descriptive and labelled original (the committed "
          "code path), fix1, fix2 or both. The committed results in `../v2/` and `../v2_oos/` remain the first, reported "
          "results.\n\n", headline]
    for grp, title in (("strategy", "Chosen combination and Variant A"), ("portfolio", "Portfolio test"),
                       ("matched_benchmark", "Matched component benchmarks"),
                       ("simple_benchmark", "Simple benchmarks"), ("walk_forward", "Walk-forward")):
        md += [f"\n## {title}\n\n", md_rows(m[m["group"] == grp])]
    out_path("metrics.md").write_text("".join(md), encoding="utf-8")

    rc = info["reproduce_check"]
    if rc.get("given"):
        repro = (f"- `run_v2_chrono.py --reproduce` (the committed reproduction), run with this code and the switches off "
                 f"({rc['reproduced_utc'][:19]} UTC; same v2lib.py as this run: {rc['same_v2lib_as_this_run']}): "
                 f"**{rc['verdict']}**; " + "; ".join(f"{c['label']} {c['n_agree']}/{c['n_files']} files agree, max abs "
                                                       f"diff {c['max_abs_diff']}" for c in rc["comparisons"])
                 + ". Its code-hash list flags `backtests/v2/v2lib.py` against `RUN_LOG.md` because the switch was "
                 "added; with the switch off the computation is the committed one.")
    else:
        repro = "- `run_v2_chrono.py --reproduce` was not quoted in this run (V2_D4_REPRODUCE_REPORT not set)."
    readme = f"""# v2 deviation D-4: corrected implementation and benchmarks

Authorised by `preregistration/v2_DEVIATION_D4_FIXES.md` (sha256 {D4_SHA}, committed 2026-10-04 05:30:03 UTC, before any
computation it authorises). Generated by `backtests/v2/run_v2_d4.py` (gated on that file and hash; writes only this
folder; writes no decision record) on {info['start_utc'][:19]} UTC.

**Status.** Everything here is descriptive. v2 failed its pre-registered decision rule and that verdict stands. The
committed results in `../v2/` (in-sample, failed-rule record) and `../v2_oos/` (the one D-3 out-of-sample evaluation)
remain the first, reported results; no file there was changed and no combination is re-chosen. These rows carry no
inferential weight for the registered hypothesis.

{headline}
## What the two fixes change

1. **Fix 1, sizing timing** (`v2lib.weights_E1(..., fix_sizing=True)`; default off). The
   committed code sizes the position entered at the open of session t with a blended 20/60-day vol of open-to-open
   returns *ending at open t*, the fill price itself. Fix 1 lags those returns by one more session, so they end at
   open t-1, before the close of session t-1. This is the minimal change: the return definition (open-to-open, Variant
   A's), the windows, target, floor, clip, cap, no-trade band and FOMC rule are unchanged. (The alternative,
   close-to-close returns ending at the close of t-1, would also change the return definition.) E2 is not affected:
   its vol already ends at the decision close.
2. **Fix 2, holdings drift** (`sim_fixed.simulate`, a drop-in for the shared engine's `simulate(exec="next_open")`).
   The engine applies the previous open's *target* to the close-to-open return, an uncharged rebalance to target at
   every close, and measures the next open's trade from the target drifted overnight only. The corrected simulator
   carries the shares bought at the open through the intraday and overnight moves; the overnight return is earned on
   those drifted holdings and the next open's trade (and cost) is measured from them. The engine's formula and its
   bookkeeping of the T-bill on the cash weight, the 30 bp/yr borrow on short ETF weights and the one-way costs are
   kept, so the only change is the holdings path. Reviewer's example: $100 with $50 in an asset, +10% intraday then
   +10% overnight: ${example['fixed']['value_at_session2']:.2f} at the next open (by hand
   ${example['by_hand_value_at_open2']:.2f}), engine ${example['engine']['value_at_session2']:.2f}
   (`sim_fixed_unit_test.json`; `backtests/v2/test_sim_fixed.py` also checks the simulator against an explicit
   share-and-cash ledger and against the engine when nothing moves intraday). E2 (`next_close`) already measures each
   day's trade from the holdings drifted over its one segment and is unchanged.

## Reproduction with the switches off

{repro}
- Inside this run (`consistency.json`), the original rows against the committed files: max abs diff
  {cons['switches_off_max_abs_diff_vs_committed']} (the 10 in-sample series of `windows_all.csv`, the daily series in
  `../v2_oos/run`, the out-of-sample record, and the portfolio tables). The in-sample part of every full-period series
  equals the in-sample run: max abs diff {cons['fwd_vs_is_run_on_is_dates_max_abs_diff']}.

## Conventions

- Windows: selection 2016-01-04..2020-12-31, validation 2021-01-01..2024-10-02, full in-sample 2016-01-04..2024-10-02
  (from the in-sample run, as committed), out-of-sample 2024-10-03..2026-10-02 (from the full-period run). A window
  never includes days before the series' first held position (first E1 position: the open of
  {info['first_e1_position']}).
- Metrics on daily returns in excess of the T-bill: Sharpe (mean / sd x sqrt 252) net of 1x costs, net of 2x costs
  (trading costs doubled, borrow not) and gross; annualised arithmetic and geometric return; vol; maximum drawdown of
  the compounded excess equity; one-way turnover per year; Newey-West t of the mean (v2lib).
- Costs as registered: E1 1.5 bp TLT / 5 bp UUP per unit traded plus 30 bp/yr borrow on short ETF weights; E2 1 bp
  each plus a round trip on roll days. "gross" on the corrected path is the pre-cost return of the same holdings path
  (as in the engine; the path depends on costs only at second order through the NAV).
- Matched benchmarks use the same documents, processing, sizing and costs as T4xE1's legs: LEXALLxE1 is the
  all-document lexicon z that T4 averages (primary `lex_score`, keep rule H+D >= 5), T2xE1 the all-document stance z,
  T0v2xE1 Variant A's lexicon on speeches with the 2015 warm-up.
- Simple benchmarks: MxE1 trades the expanding z (from 2015-01-02, minimum 252) of T3's rate momentum M with E1 sizing
  and costs (hawkish = rising two-year yields: short TLT, long UUP). BH7525volxE1 holds long 75% TLT + 25% UUP with the
  E1 sizing rules (vol target on that long mix, floor, cap, band, FOMC rule) and costs, from the first E1 position.
  BH7525hold is the literal buy-and-hold: 75/25 bought at that open, never rebalanced, entry cost only, unlevered
  (the entry falls on that first session, before every window, so its window turnover is 0 and net equals gross).
- Portfolio test: `combine.build` verbatim with the corrected T4xE1 sleeve (overlay cost 2.375 bp). **Limitation:** the
  three core_ER_6 sleeves are the committed series from other pipelines; they are not re-simulated with these fixes.
- Walk-forward selection (post hoc, robustness): at each year-end from 2020-12-31 the registered combination (of the
  eight) with the highest net 1x Sharpe from 2016-01-04 to that date is held for the next calendar year, to
  2026-10-02. "fixed" uses both fixes on the four E1 combinations (E2 needs neither). The chain is two weight paths,
  one per expression (the picked combination's decision-date weights where it is in force, zero elsewhere), each
  simulated once with its registered execution (E1 at the next open, E2 at the next close), so a switch is filled
  and charged when that expression can trade and the old holdings earn their returns until then; the daily result is
  the sum of the two books (the first year opens from flat). The picks decided at 2024-12-31 and 2025-12-31 use
  out-of-sample-period returns as trailing history, as any walk-forward does; the in-sample part of the chain is the
  validation window. Under fix 2 the no-trade band compares target weights, so on no-trade days the drift is
  rebalanced to the unchanged target and charged (T4xE1 full in-sample turnover 26.8 -> 27.1 a year).
- Sensitivity of fix 1: sizing with close-to-close returns ending at the close of session t-1, instead of
  open-to-open returns ending at the open of session t-1, gives T4xE1 (both fixes) a full in-sample Sharpe of
  0.402 / 0.346 and an out-of-sample Sharpe of 0.500 / 0.435 (net / 2x), against 0.446 / 0.392 and 0.621 / 0.554 in
  the table: the corrected out-of-sample figure depends on this choice (independent check, not a separate run here).

## Files

| file | what |
|---|---|
| `metrics.csv`, `metrics.md` | every row: group, series, variant (original / fix1 / fix2 / both; hold; as_committed), window, metrics |
| `walk_forward_picks.csv` | the trailing Sharpe of the eight combinations at each year-end, the pick, the switch cost |
| `daily_returns.parquet` | daily excess returns net 1x, net 2x, gross and turnover of every row (full-period run), no prices |
| `daily_returns_net1x.csv` | the net 1x columns of the same |
| `consistency.json` | the switch-off comparison with the committed files and the in-sample vs full-period check |
| `sim_fixed_unit_test.json` | the reviewer's example (engine vs corrected) and the unit-test results |
| `run_info.json` | start and end time, sha256 of the code and inputs, the deviation note |

Code: `backtests/v2/run_v2_d4.py`, `backtests/v2/sim_fixed.py`, `backtests/v2/test_sim_fixed.py`, and the default-off
switch in `backtests/v2/v2lib.py`. The gqh-flow-clock repository is not changed.
"""
    out_path("README.md").write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
