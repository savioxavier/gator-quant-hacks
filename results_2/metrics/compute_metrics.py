"""Machine-readable v2 metrics table with both drawdown conventions (review items 1 and 2).

    python results_2/metrics/compute_metrics.py [--out results_2/metrics]

Run from the repository root. Reads committed daily series only (no market data, no price levels, no backtest is
run or re-run):

  backtests/results/v2_oos/daily_returns.parquet         original (D-3, frozen) daily excess returns and T4xE1 turnover
  backtests/results/v2_oos/run/daily_portfolio_full.parquet  original portfolio overlay turnover and T4xE1 multiplier
  backtests/results/v2_oos/metrics.csv                   committed original metrics (consistency check)
  backtests/results/v2_d4/daily_returns.parquet          D-4 daily excess returns and turnover (both fixes)
  backtests/results/v2_d4/metrics.csv                    committed D-4 metrics (consistency check; the D-4 v2-sleeve
                                                         turnover, whose multiplier path is not a committed file)
  backtests/v2/inputs/data/rf_daily.parquet              3-month T-bill (FRED DTB3 / 100 / 252, public), only for
                                                         the total-account return and drawdown

Writes to --out: v2_metrics.csv, metrics.md, equity_v2.png, equity_portfolio.png, consistency_vs_committed.csv,
inputs_sha256.json. Exits 2 when an input is missing or the output folder is a frozen one, and 3 when a recomputed
number that also exists in a committed file differs from it by more than 1e-9.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ANN = 252
TOL = 1e-9
WINDOWS = [("selection", "2016-01-04", "2020-12-31"), ("validation", "2021-01-01", "2024-10-02"),
           ("full_is", "2016-01-04", "2024-10-02"), ("oos", "2024-10-03", "2026-10-02")]
FULL_START, OOS_START, OOS_END = "2016-01-04", "2024-10-03", "2026-10-02"

INPUTS = {
    "d3_daily": "backtests/results/v2_oos/daily_returns.parquet",
    "d3_portfolio_run": "backtests/results/v2_oos/run/daily_portfolio_full.parquet",
    "d3_metrics": "backtests/results/v2_oos/metrics.csv",
    "d4_daily": "backtests/results/v2_d4/daily_returns.parquet",
    "d4_metrics": "backtests/results/v2_d4/metrics.csv",
    "rf": "backtests/v2/inputs/data/rf_daily.parquet",
}
FROZEN_PREFIXES = ("backtests/", "preregistration/", "hpg/", "data/", "archive/", "backtest_snapshot/")

STATUS = {
    "original_D3": "first reported result (D-3 out-of-sample evaluation of the frozen code)",
    "D4_both_fixes": "descriptive corrected implementation (D-4); no inferential weight; the failed verdict stands",
    "as_committed": "core_ER_6 sleeves as committed by their own pipelines; not re-simulated under D-4",
}

# reference palette (categorical slots 1-3), neutral ink, chart surface: the same as the committed v2 figures
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, SURF = "#0b0b0b", "#52514e", "#fcfcfb"


# ----------------------------------------------------------------------------- inputs
def check_inputs(root: Path, keys=None) -> dict[str, Path]:
    keys = list(INPUTS) if keys is None else keys
    paths = {k: root / INPUTS[k] for k in keys}
    missing = [INPUTS[k] for k, p in paths.items() if not p.is_file()]
    if missing:
        for m in missing:
            print(f"MISSING INPUT: {m}", file=sys.stderr)
        raise SystemExit(2)
    return paths


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def guard_out(root: Path, out: Path) -> Path:
    out = out if out.is_absolute() else root / out
    try:
        rel = out.resolve().relative_to(root.resolve()).as_posix() + "/"
    except ValueError:
        return out
    if rel.startswith(FROZEN_PREFIXES):
        print(f"refusing to write into a frozen folder: {rel}", file=sys.stderr)
        raise SystemExit(2)
    return out


# ----------------------------------------------------------------------------- statistics
def max_dd_from_first_close(r) -> float:
    """Old convention (v2lib.max_dd): the running peak starts at the first close, after the first day's return.

    A loss on the window's first day is therefore never part of a drawdown."""
    r = np.asarray(r, float)
    if len(r) == 0:
        return float("nan")
    eq = np.cumprod(1.0 + r)
    return float((eq / np.maximum.accumulate(eq) - 1.0).min())


def drawdown_incl_start_nav(r, index=None) -> dict:
    """Corrected convention: the equity curve starts at the window's starting NAV of 1, which enters the running peak.

    Returns depth (<= 0), the peak ("start_nav" or a date) and the trough date."""
    r = np.asarray(r, float)
    if len(r) == 0:
        return {"depth": float("nan"), "peak": None, "trough": None}
    eq = np.r_[1.0, np.cumprod(1.0 + r)]
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1.0
    i = int(np.argmin(dd))
    depth = float(dd[i])
    if depth >= 0.0:
        return {"depth": 0.0, "peak": None, "trough": None}
    j = int(np.argmax(eq[: i + 1]))

    def lab(k):
        if k == 0:
            return "start_nav"
        return str(pd.Timestamp(index[k - 1]).date()) if index is not None else int(k)

    return {"depth": depth, "peak": lab(j), "trough": lab(i)}


def max_dd_incl_start_nav(r) -> float:
    return drawdown_incl_start_nav(r)["depth"]


def newey_west_t(x) -> tuple[float, int | None]:
    """t of the mean with a Bartlett-kernel Newey-West variance; lag L = floor(4 (n/100)^(2/9)); autocovariances
    divided by n; no small-sample correction (as v2lib.nw_t)."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 10:
        return float("nan"), None
    lag = int(4 * (n / 100) ** (2 / 9))
    e = x - x.mean()
    s = e @ e / n
    for k in range(1, lag + 1):
        s += 2 * (1 - k / (lag + 1)) * (e[k:] @ e[:-k]) / n
    return (float(x.mean() / math.sqrt(s / n)) if s > 0 else float("nan")), lag


def sharpe(x) -> float:
    x = np.asarray(x, float)
    sd = x.std(ddof=1)
    return float(x.mean() / sd * math.sqrt(ANN)) if len(x) > 20 and sd > 0 else float("nan")


# ----------------------------------------------------------------------------- series
def load_series(paths: dict[str, Path]) -> list[dict]:
    """The five series of the table, each with net_1x, net_2x, gross, rf and its turnover columns."""
    d3 = pd.read_parquet(paths["d3_daily"])
    d4 = pd.read_parquet(paths["d4_daily"])
    p3 = pd.read_parquet(paths["d3_portfolio_run"])
    rf = pd.read_parquet(paths["rf"])
    rf = pd.Series(rf["rf"].to_numpy(), index=pd.to_datetime(rf["date"]).astype("datetime64[ns]")).sort_index()
    d4m = pd.read_csv(paths["d4_metrics"])

    def frame(src: pd.DataFrame, prefix: str) -> pd.DataFrame:
        f = pd.DataFrame({b: src[f"{prefix}|{b}"] for b in ("net_1x", "net_2x", "gross")})
        f.index = pd.DatetimeIndex(f.index).astype("datetime64[ns]")
        return f

    def with_rf(f: pd.DataFrame) -> pd.DataFrame:
        r = rf.reindex(f.index)
        if r.isna().any():
            raise SystemExit("the T-bill series does not cover every trading day of the daily series")
        return f.assign(rf=r.to_numpy())

    out = []
    # T4xE1, original (D-3 frozen series)
    f = with_rf(frame(d3, "T4xE1"))
    f["turnover"] = d3["T4xE1|turnover"].to_numpy()
    out.append({"series": "T4xE1", "variant": "original_D3", "kind": "strategy", "data": f,
                "source": INPUTS["d3_daily"]})
    # T4xE1, D-4 both fixes
    f = with_rf(frame(d4, "T4xE1|both"))
    f["turnover"] = d4["T4xE1|both|turnover"].to_numpy()
    out.append({"series": "T4xE1", "variant": "D4_both_fixes", "kind": "strategy", "data": f,
                "source": INPUTS["d4_daily"]})
    # core_ER_6 alone (as committed)
    f = with_rf(frame(d3, "core_ER_6"))
    f["overlay_turnover"] = p3["core_ER_6|overlay_turnover"].reindex(d3.index).to_numpy()
    out.append({"series": "core_ER_6", "variant": "as_committed", "kind": "portfolio", "data": f,
                "source": f"{INPUTS['d3_daily']}; overlay turnover {INPUTS['d3_portfolio_run']}"})
    # core_ER_6 + T4xE1, original
    f = with_rf(frame(d3, "core_ER_6+T4xE1"))
    f["overlay_turnover"] = p3["core_ER_6+T4xE1|overlay_turnover"].reindex(d3.index).to_numpy()
    m = p3["core_ER_6+T4xE1|m_FED_T4xE1"].reindex(d3.index).fillna(0.0).to_numpy()
    f["v2_sleeve_turnover"] = m * d3["T4xE1|turnover"].fillna(0.0).to_numpy()
    out.append({"series": "core_ER_6+T4xE1", "variant": "original_D3", "kind": "portfolio", "data": f,
                "source": f"{INPUTS['d3_daily']}; overlay turnover and T4xE1 multiplier {INPUTS['d3_portfolio_run']}"})
    # core_ER_6 + T4xE1, D-4 both fixes (the v2-sleeve multiplier path of D-4 is not a committed file)
    f = with_rf(frame(d4, "core_ER_6+T4xE1|both"))
    f["overlay_turnover"] = d4["core_ER_6+T4xE1|both|turnover"].to_numpy()
    committed = d4m[(d4m.series == "core_ER_6+T4xE1") & (d4m.variant == "both")].set_index("window")
    out.append({"series": "core_ER_6+T4xE1", "variant": "D4_both_fixes", "kind": "portfolio", "data": f,
                "source": INPUTS["d4_daily"],
                "v2_sleeve_turnover_committed": committed["fed_sleeve_turnover_per_year"].to_dict()})
    for s in out:
        if s["data"][["net_1x", "net_2x", "gross"]].loc[FULL_START:OOS_END].isna().any().any():
            raise SystemExit(f"missing daily returns inside the windows: {s['series']} {s['variant']}")
    return out


def window_row(s: dict, wn: str, a: str, b: str) -> dict:
    df = s["data"]
    if pd.Timestamp(a) < df.index[0]:
        raise SystemExit(f"window {wn} starts before the first held position of {s['series']} {s['variant']}")
    w = df.loc[a:b]
    x = w["net_1x"].to_numpy()
    n = len(x)
    yrs = n / ANN
    rf = w["rf"].to_numpy()
    nw, lag = newey_west_t(x)
    dd = drawdown_incl_start_nav(x, w.index)
    row = {
        "series": s["series"], "variant": s["variant"], "status": STATUS[s["variant"]], "window": wn,
        "window_nominal_start": a, "window_nominal_end": b,
        "first_obs": str(w.index[0].date()), "last_obs": str(w.index[-1].date()), "n_obs": n, "years": yrs,
        "ann_excess_arith": float(x.mean() * ANN),
        "ann_excess_geo": float(np.prod(1 + x) ** (1 / yrs) - 1),
        "ann_total_geo_incl_tbill": float(np.prod(1 + x + rf) ** (1 / yrs) - 1),
        "cum_excess_return": float(np.prod(1 + x) - 1),
        "vol_ann": float(x.std(ddof=1) * math.sqrt(ANN)),
        "sharpe_net1x": sharpe(x), "sharpe_net2x": sharpe(w["net_2x"].to_numpy()),
        "sharpe_gross": sharpe(w["gross"].to_numpy()),
        "max_dd_from_first_close": max_dd_from_first_close(x),
        "max_dd_incl_start_nav": dd["depth"],
        "max_dd_peak": dd["peak"], "max_dd_trough": dd["trough"],
        "max_dd_incl_start_nav_net2x": max_dd_incl_start_nav(w["net_2x"].to_numpy()),
        "max_dd_total_account_incl_start_nav": max_dd_incl_start_nav(x + rf),
        "first_obs_excess_return": float(x[0]),
        "hit_rate_pos_excess_days": float((x > 0).mean()),
        "n_zero_return_days": int((x == 0).sum()),
        "nw_t": nw, "nw_lag": lag,
    }
    if s["kind"] == "strategy":
        row["turnover_instrument_oneway_per_year"] = float(w["turnover"].fillna(0.0).sum() / yrs)
        row["turnover_overlay_per_year"] = float("nan")
        row["turnover_v2_sleeve_per_year"] = float("nan")
        row["turnover_v2_sleeve_source"] = ""
    else:
        row["turnover_instrument_oneway_per_year"] = float("nan")   # core sleeves' trades are not committed
        row["turnover_overlay_per_year"] = float(w["overlay_turnover"].fillna(0.0).sum() / yrs)
        if "v2_sleeve_turnover" in w:
            row["turnover_v2_sleeve_per_year"] = float(w["v2_sleeve_turnover"].sum() / yrs)
            row["turnover_v2_sleeve_source"] = "recomputed: T4xE1 multiplier x T4xE1 one-way turnover"
        elif "v2_sleeve_turnover_committed" in s:
            row["turnover_v2_sleeve_per_year"] = float(s["v2_sleeve_turnover_committed"][wn])
            row["turnover_v2_sleeve_source"] = (f"carried from {INPUTS['d4_metrics']} (D-4 multiplier path not "
                                                "committed; not recomputed)")
        else:
            row["turnover_v2_sleeve_per_year"] = float("nan")
            row["turnover_v2_sleeve_source"] = "no v2 sleeve"
    row["source"] = s["source"]
    return row


COLUMNS = ["series", "variant", "status", "window", "window_nominal_start", "window_nominal_end", "first_obs",
           "last_obs", "n_obs", "years", "ann_excess_arith", "ann_excess_geo", "ann_total_geo_incl_tbill",
           "cum_excess_return", "vol_ann", "sharpe_net1x", "sharpe_net2x", "sharpe_gross",
           "max_dd_from_first_close", "max_dd_incl_start_nav", "max_dd_peak", "max_dd_trough",
           "max_dd_incl_start_nav_net2x", "max_dd_total_account_incl_start_nav", "first_obs_excess_return",
           "turnover_instrument_oneway_per_year", "turnover_overlay_per_year", "turnover_v2_sleeve_per_year",
           "turnover_v2_sleeve_source", "hit_rate_pos_excess_days", "n_zero_return_days", "nw_t", "nw_lag", "source"]


def build_table(series: list[dict]) -> pd.DataFrame:
    rows = [window_row(s, wn, a, b) for s in series for wn, a, b in WINDOWS]
    return pd.DataFrame(rows).reindex(columns=COLUMNS)


# ----------------------------------------------------------------------------- consistency with committed files
def consistency(tab: pd.DataFrame, paths: dict[str, Path]) -> pd.DataFrame:
    d3m = pd.read_csv(paths["d3_metrics"])
    d4m = pd.read_csv(paths["d4_metrics"])
    rows = []

    def add(key, metric, ours, theirs, file):
        if isinstance(theirs, str) or isinstance(ours, str):
            diff = 0.0 if str(ours) == str(theirs) else float("inf")
        else:
            diff = abs(float(ours) - float(theirs))
        rows.append({"row": key, "metric": metric, "ours": ours, "committed": theirs, "abs_diff": diff,
                     "committed_file": file})

    for r in tab.itertuples():
        key = f"{r.series}|{r.variant}|{r.window}"
        if r.variant in ("original_D3", "as_committed"):
            name = r.series
            c = {b: d3m[(d3m.series == name) & (d3m.window == r.window) & (d3m.basis == b)].iloc[0]
                 for b in ("net_1x", "net_2x", "gross")}
            f = INPUTS["d3_metrics"]
            for ours, col in ((r.first_obs, "start"), (r.last_obs, "end"), (r.n_obs, "n_days"),
                              (r.ann_excess_arith, "ann_return_arith"), (r.ann_excess_geo, "ann_return_geo"),
                              (r.ann_total_geo_incl_tbill, "ann_total_return_geo"), (r.vol_ann, "ann_vol"),
                              (r.sharpe_net1x, "sharpe"), (r.max_dd_from_first_close, "max_drawdown"),
                              (r.hit_rate_pos_excess_days, "hit_rate"), (r.nw_t, "nw_t")):
                add(key, f"{col} (net_1x)", ours, c["net_1x"][col], f)
            add(key, "sharpe (net_2x)", r.sharpe_net2x, c["net_2x"]["sharpe"], f)
            add(key, "sharpe (gross)", r.sharpe_gross, c["gross"]["sharpe"], f)
            turn = r.turnover_instrument_oneway_per_year if r.series == "T4xE1" else r.turnover_overlay_per_year
            add(key, "turnover_per_year", turn, c["net_1x"]["turnover_per_year"], f)
            if r.series == "core_ER_6+T4xE1":
                add(key, "fed_sleeve_turnover_per_year", r.turnover_v2_sleeve_per_year,
                    c["net_1x"]["fed_sleeve_turnover_per_year"], f)
        d4v = {"original_D3": "original", "D4_both_fixes": "both", "as_committed": "as_committed"}[r.variant]
        c = d4m[(d4m.series == r.series) & (d4m.variant == d4v) & (d4m.window == r.window)
                & (d4m.group.isin(["strategy", "portfolio"]))].iloc[0]
        f = INPUTS["d4_metrics"]
        turn = r.turnover_instrument_oneway_per_year if r.series == "T4xE1" else r.turnover_overlay_per_year
        for ours, col in ((r.first_obs, "start"), (r.last_obs, "end"), (r.n_obs, "n_days"),
                          (r.ann_excess_arith, "ann_excess_arith"), (r.ann_excess_geo, "ann_excess_geo"),
                          (r.vol_ann, "vol"), (r.sharpe_net1x, "sharpe_net1x"), (r.sharpe_net2x, "sharpe_net2x"),
                          (r.sharpe_gross, "sharpe_gross"), (r.max_dd_from_first_close, "max_dd_excess"),
                          (turn, "turnover_per_year"), (r.nw_t, "nw_t")):
            add(key, col, ours, c[col], f)
        if r.series == "core_ER_6+T4xE1" and r.variant == "original_D3":
            add(key, "fed_sleeve_turnover_per_year", r.turnover_v2_sleeve_per_year,
                c["fed_sleeve_turnover_per_year"], f)
    return pd.DataFrame(rows)


def series_identity(paths: dict[str, Path]) -> pd.DataFrame:
    """The original series in the D-4 file are the frozen D-3 series."""
    d3 = pd.read_parquet(paths["d3_daily"])
    d4 = pd.read_parquet(paths["d4_daily"])
    pairs = [("T4xE1|original|" + b, "T4xE1|" + b) for b in ("net_1x", "net_2x", "gross", "turnover")]
    pairs += [(f"{n}|{v}|{b}", f"{n}|{b}") for n, v in (("core_ER_6", "as_committed"),
                                                         ("core_ER_6+T4xE1", "original"))
              for b in ("net_1x", "net_2x", "gross")]
    rows = []
    for a, b in pairs:
        x, y = d4[a], d3[b].reindex(d4.index)
        rows.append({"row": f"daily {a} vs {b}", "metric": "max abs diff over 2015-12-31..2026-10-02",
                     "ours": float((x - y).abs().max()), "committed": 0.0,
                     "abs_diff": float((x - y).abs().max()), "committed_file": INPUTS["d3_daily"]})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- figures
def _end_labels(ax, items, xpos, min_gap):
    """Direct labels at the right end of each line, nudged apart so they do not overlap."""
    items = sorted(items, key=lambda t: t[1])
    placed = []
    for lab, y in items:
        if placed and y - placed[-1][1] < min_gap:
            y = placed[-1][1] + min_gap
        placed.append((lab, y))
    for lab, y in placed:
        ax.text(xpos, y, lab, fontsize=8, color=INK2, va="center", ha="left")


def equity_figure(curves: list[tuple[str, pd.Series, str, str, str]], title: str, oos_note: tuple, path: Path) -> None:
    """curves: (legend label, daily excess returns, colour, line style, short end label).
    oos_note: (index into curves, text) marking the out-of-sample drawdown of one curve."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2,
                         "ytick.color": INK2, "text.color": INK})
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(10.5, 7.6), height_ratios=[3, 2], facecolor=SURF)
    oos0 = pd.Timestamp(OOS_START)
    for axis, lo in ((ax, FULL_START), (bx, OOS_START)):
        axis.set_facecolor(SURF)
        ends = []
        for lab, r, color, ls, short in curves:
            x = r.loc[lo:OOS_END]
            prev = r.index[r.index < pd.Timestamp(lo)][-1]          # the close before the window: NAV 1
            eq = pd.concat([pd.Series([1.0], index=[prev]), (1 + x).cumprod()])
            lw = 1.3 if short == "original" or "orig" in short else (2.2 if ls == "-" else 1.5)
            axis.plot(eq.index, eq.to_numpy(), color=color, ls=ls, lw=lw, label=lab)
            ends.append((short, float(eq.iloc[-1])))
        axis.axhline(1.0, color=INK2, lw=0.6, alpha=0.6)
        axis.grid(axis="y", color="#e4e3df", lw=0.6)
        for side in ("top", "right"):
            axis.spines[side].set_visible(False)
        lo_y, hi_y = axis.get_ylim()
        axis.set_xlim(right=pd.Timestamp(OOS_END) + pd.Timedelta(days=30 if axis is bx else 10))
        _end_labels(axis, ends, pd.Timestamp(OOS_END) + pd.Timedelta(days=12 if axis is bx else 40),
                    (hi_y - lo_y) * 0.045)
        axis.set_ylabel("growth of 1, excess of T-bill")
    ax.axvspan(pd.Timestamp(FULL_START), pd.Timestamp("2020-12-31"), color="#ecebe7", lw=0, zorder=0)
    ax.axvspan(pd.Timestamp("2021-01-01"), pd.Timestamp("2024-10-02"), color="#f4f3f0", lw=0, zorder=0)
    ax.axvspan(oos0, pd.Timestamp(OOS_END), color="#fbe3d6", lw=0, zorder=0)
    ax.axvline(oos0, color=INK2, lw=0.9, ls=":")
    top = ax.get_ylim()[1]
    for xx, t in ((pd.Timestamp("2016-02-01"), "IS selection"), (pd.Timestamp("2021-02-01"), "IS validation"),
                  (pd.Timestamp("2024-11-01"), "out-of-sample")):
        ax.text(xx, top, t, va="top", ha="left", fontsize=8.5, color=INK2)
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.93), frameon=False, fontsize=8.5)
    # out-of-sample panel: rebased to 1 at the close of 2024-10-02, the starting NAV of the window
    bx.set_facecolor("#fdf3ec")
    k, note = oos_note
    lab, r, color, ls, short = curves[k]
    x = r.loc[OOS_START:OOS_END]
    dd = drawdown_incl_start_nav(x.to_numpy(), x.index)
    eq = (1 + x).cumprod()
    tr = pd.Timestamp(dd["trough"])
    bx.plot([tr], [eq.loc[tr]], marker="o", ms=7, color=color, mec=SURF, mew=1.5, zorder=5)
    bx.annotate(note, xy=(tr, eq.loc[tr]), xytext=(0.03, 0.95), textcoords="axes fraction", fontsize=8.5,
                color=INK, va="top", ha="left",
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8, shrinkA=2, shrinkB=5))
    bx.set_title("Out-of-sample only (2024-10-03 to 2026-10-02), starting NAV 1 at the close of 2024-10-02",
                 loc="left", fontsize=9.5, color=INK2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    bx.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.text(0.01, 0.005, "Daily excess returns over the 3-month T-bill, compounded. Same series as v2_metrics.csv.",
             fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.015, 1, 1))
    fig.savefig(path, dpi=150, facecolor=SURF)
    plt.close(fig)


def figures(series: list[dict], tab: pd.DataFrame, out: Path) -> None:
    by = {(s["series"], s["variant"]): s["data"] for s in series}
    t = tab.set_index(["series", "variant", "window"])

    def note(sv):
        r = t.loc[(*sv, "oos")]
        return (f"{sv[0]}, D-4 both fixes, net 1x: max drawdown incl. starting NAV {r.max_dd_incl_start_nav:.2%}\n"
                f"(old convention, from first close: {r.max_dd_from_first_close:.2%})")

    equity_figure([("T4xE1, D-4 both fixes, net 1x", by[("T4xE1", "D4_both_fixes")]["net_1x"], C1, "-", "D-4 1x"),
                   ("T4xE1, D-4 both fixes, net 2x", by[("T4xE1", "D4_both_fixes")]["net_2x"], C1, "--", "D-4 2x"),
                   ("T4xE1, original (D-3), net 1x", by[("T4xE1", "original_D3")]["net_1x"], C2, "-", "original")],
                  "v2 T4xE1 (TLT/UUP, next open): original and corrected (D-4) implementation", (0, note(("T4xE1", "D4_both_fixes"))),
                  out / "equity_v2.png")
    equity_figure([("core_ER_6 + T4xE1, D-4 both fixes", by[("core_ER_6+T4xE1", "D4_both_fixes")]["net_1x"], C1, "-",
                    "+T4xE1 D-4"),
                   ("core_ER_6 + T4xE1, original (D-3)", by[("core_ER_6+T4xE1", "original_D3")]["net_1x"], C2, "-",
                    "+T4xE1 orig."),
                   ("core_ER_6 alone (as committed)", by[("core_ER_6", "as_committed")]["net_1x"], C3, "-",
                    "core_ER_6")],
                  "Portfolio test: core_ER_6 with and without the T4xE1 sleeve, net 1x",
                  (0, note(("core_ER_6+T4xE1", "D4_both_fixes"))), out / "equity_portfolio.png")


# ----------------------------------------------------------------------------- markdown
def pct(x, d=2):
    return "-" if pd.isna(x) else f"{x * 100:.{d}f}%"


def num(x, d=3):
    return "-" if pd.isna(x) else f"{x:.{d}f}"


def write_md(tab: pd.DataFrame, cons: pd.DataFrame, shas: dict, out: Path) -> None:
    t = tab.set_index(["series", "variant", "window"])
    L = []
    L.append("# v2 metrics: original and corrected rows, both drawdown conventions\n")
    L.append("Generated by `python results_2/metrics/compute_metrics.py` (run from the repository root) from committed "
             "daily series only. No backtest was run or re-run; no market data or price level is read or written. "
             "Machine-readable table: `v2_metrics.csv` (one row per series x variant x window). "
             "Figures: `equity_v2.png`, `equity_portfolio.png`, drawn from the same daily series.\n")
    L.append("**Status.** v2 failed its pre-registered decision rule (full in-sample Sharpe at 2x costs 0.387 <= 0.5) "
             "and that verdict stands. `original_D3` rows are the first reported results (the one D-3 out-of-sample "
             "evaluation of the frozen code). `D4_both_fixes` rows are the descriptive corrected implementation "
             "(deviation D-4, both fixes); they carry no inferential weight. `core_ER_6` is the same committed series in "
             "both files; its three sleeves were not re-simulated under D-4.\n")
    L.append("## Conventions\n")
    L.append("- **Returns.** Daily returns in excess of the 3-month T-bill (FRED DTB3 / 100 / 252), net of 1x costs "
             "unless a column says 2x or gross. Net 2x doubles trading costs (not the borrow fee); gross has no "
             "trading cost and no borrow.")
    L.append("- **Windows** (exact first and last observation and the count are columns of the CSV): selection "
             "2016-01-04..2020-12-31 (1,259 days), validation 2021-01-01..2024-10-02 (first trading day 2021-01-04; "
             "943 days), full in-sample 2016-01-04..2024-10-02 (2,202 days), out-of-sample 2024-10-03..2026-10-02 "
             "(501 days). No window includes a day before the first held position (2015-12-31).")
    L.append("- **Annualised return.** `ann_excess_arith` = mean daily excess return x 252. `ann_excess_geo` = "
             "(prod(1 + r))^(252/n) - 1 of the daily **excess** returns (the excess series compounded; not total "
             "return minus the T-bill). `ann_total_geo_incl_tbill` = (prod(1 + r + rf))^(252/n) - 1, the account "
             "including the T-bill on the full NAV.")
    L.append("- **Vol** = sd (ddof 1) x sqrt(252). **Sharpe** = mean / sd x sqrt(252) of the excess returns, at net 1x, "
             "net 2x and gross.")
    L.append("- **Drawdown, two conventions, both on the compounded excess-return curve of the window** (each window "
             "restarts at NAV 1; these are excess-return drawdowns, not total-account drawdowns):")
    L.append("  - `max_dd_from_first_close` (the convention of the committed v2 metrics files, `v2lib.max_dd`): the curve "
             "is cumprod(1 + r) and its running peak starts at the **first close**, after the first day's return. A "
             "loss on the first day of a window is never counted. Kept for comparison only.")
    L.append("  - `max_dd_incl_start_nav` (corrected): the curve starts at the window's starting NAV of 1 (the close "
             "before the first observation), which enters the running peak. `max_dd_peak` is `start_nav` when the "
             "peak is that starting NAV. Use this one.")
    L.append("  - The two differ only when the window's equity stays below the starting NAV from the first day until "
             "the deepest trough (which needs a losing first day); otherwise they are equal. That happens in the "
             "out-of-sample window: T4xE1 opens with three losing days (first day -0.81% for D-4 both fixes) and never "
             "regains the starting NAV before its trough on 2025-01-13, so the old convention measured the drawdown "
             "from a peak already 0.81% below the starting NAV. The in-sample windows are unaffected (a positive "
             "first day, or a peak above the starting NAV before the trough).")
    L.append("  - `max_dd_total_account_incl_start_nav`: the same corrected convention on 1 + r + rf (account fully "
             "funded in T-bills; for the portfolio rows the futures sleeves' excess returns are earned on top of a "
             "T-bill-funded account). `max_dd_incl_start_nav_net2x`: corrected convention at net 2x.")
    L.append("- **Turnover.** Strategy rows: `turnover_instrument_oneway_per_year` = sum over days of the one-way trades "
             "in TLT and UUP as a fraction of NAV (roll trades included), divided by years. Portfolio rows: "
             "`turnover_overlay_per_year` is **overlay-only** (|change in a sleeve multiplier| x that sleeve's "
             "instrument gross; e.g. 0.307x a year out of sample for core_ER_6 + T4xE1, D-4); "
             "`turnover_v2_sleeve_per_year` is the T4xE1 sleeve's own trading x its multiplier, i.e. the v2 sleeve "
             "inside the portfolio (6.032x a year out of sample, D-4). The **total** portfolio instrument turnover is "
             "not available: the core_ER_6 sleeves' trades are not committed, so `turnover_instrument_oneway_per_year` "
             "is blank for portfolio rows. The D-4 v2-sleeve figure is carried from `backtests/results/v2_d4/metrics.csv` "
             "because the D-4 multiplier path is not a committed file; the original one is recomputed.")
    L.append("- **Hit rate** (`hit_rate_pos_excess_days`) = fraction of days in the window with a **positive daily excess "
             "return** at net 1x (zero counts as not positive; `n_zero_return_days` gives the zeros). It is **not** a "
             "per-trade win rate: v2 holds a position nearly every day, and trades are not round trips.")
    L.append("- **Newey-West t** (`nw_t`) of the mean daily net 1x excess return: Bartlett kernel, lag "
             "L = floor(4 (n/100)^(2/9)) (`nw_lag`: 7 for selection and full IS, 6 for validation, 5 out of sample), "
             "autocovariances divided by n, no small-sample correction (as `v2lib.nw_t`). It tests the mean return, "
             "not a Sharpe difference.\n")

    def strat_table(series, variants):
        h = ("| series | variant | window | dates (n) | ann. excess arith / geo | total incl. T-bill (geo) | vol | "
             "Sharpe 1x / 2x / gross | max DD incl. start NAV | (old: from first close) | turnover/yr | hit rate | "
             "NW t (lag) |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        rows = [h]
        for v in variants:
            for wn, _, _ in WINDOWS:
                r = t.loc[(series, v, wn)]
                turn = (r.turnover_instrument_oneway_per_year if series == "T4xE1" else r.turnover_overlay_per_year)
                rows.append(f"| {series} | {v} | {wn} | {r.first_obs}..{r.last_obs} ({r.n_obs}) | "
                            f"{pct(r.ann_excess_arith)} / {pct(r.ann_excess_geo)} | {pct(r.ann_total_geo_incl_tbill)} | "
                            f"{pct(r.vol_ann)} | {num(r.sharpe_net1x)} / {num(r.sharpe_net2x)} / {num(r.sharpe_gross)} | "
                            f"**{pct(r.max_dd_incl_start_nav)}** | {pct(r.max_dd_from_first_close)} | {num(turn, 2)} | "
                            f"{pct(r.hit_rate_pos_excess_days, 1)} | {num(r.nw_t, 2)} ({r.nw_lag}) |")
        return "\n".join(rows) + "\n"

    L.append("## v2 T4xE1 (TLT/UUP, entry at the next open)\n")
    L.append("Turnover: one-way instrument turnover, x NAV a year.\n")
    L.append(strat_table("T4xE1", ["original_D3", "D4_both_fixes"]))
    L.append("## Portfolio test: core_ER_6 and core_ER_6 + T4xE1\n")
    L.append("Turnover column: overlay-only turnover (see Conventions). The v2 sleeve's own turnover inside the "
             "portfolio is in the next table.\n")
    L.append(strat_table("core_ER_6", ["as_committed"]))
    L.append(strat_table("core_ER_6+T4xE1", ["original_D3", "D4_both_fixes"]))
    h = ("| portfolio | variant | window | overlay turnover/yr (overlay only) | v2 sleeve turnover/yr (inside the "
         "portfolio) | source of the v2 sleeve figure |\n|---|---|---|---|---|---|")
    rows = [h]
    for v in ("original_D3", "D4_both_fixes"):
        for wn, _, _ in WINDOWS:
            r = t.loc[("core_ER_6+T4xE1", v, wn)]
            rows.append(f"| core_ER_6+T4xE1 | {v} | {wn} | {num(r.turnover_overlay_per_year, 3)} | "
                        f"{num(r.turnover_v2_sleeve_per_year, 3)} | {r.turnover_v2_sleeve_source} |")
    L.append("\n".join(rows) + "\n")

    L.append("## Drawdown: old and corrected convention, every row\n")
    h = ("| series | variant | window | first-day excess return | old: from first close | corrected: incl. start "
         "NAV | difference (pp) | peak -> trough (corrected) | corrected, net 2x | total account incl. T-bill "
         "(corrected) |\n|---|---|---|---|---|---|---|---|---|---|")
    rows = [h]
    for r in tab.itertuples():
        rows.append(f"| {r.series} | {r.variant} | {r.window} | {pct(r.first_obs_excess_return, 3)} | "
                    f"{pct(r.max_dd_from_first_close, 4)} | **{pct(r.max_dd_incl_start_nav, 4)}** | "
                    f"{(r.max_dd_incl_start_nav - r.max_dd_from_first_close) * 100:+.4f} | "
                    f"{r.max_dd_peak} -> {r.max_dd_trough} | {pct(r.max_dd_incl_start_nav_net2x, 2)} | "
                    f"{pct(r.max_dd_total_account_incl_start_nav, 2)} |")
    L.append("\n".join(rows) + "\n")

    L.append("## Checks\n")
    n_cmp = len(cons)
    worst = cons["abs_diff"].max()
    by_file = cons.groupby("committed_file")["abs_diff"].agg(["count", "max"])
    L.append(f"- Every number of this table that also exists in a committed metrics file was compared with it: "
             f"{n_cmp} comparisons, maximum absolute difference {worst:.3g} (tolerance {TOL:g}; "
             "`consistency_vs_committed.csv`). Old-convention drawdowns reproduce the committed `max_drawdown` / "
             "`max_dd_excess` columns.")
    for f, r in by_file.iterrows():
        L.append(f"  - `{f}`: {int(r['count'])} comparisons, max abs diff {r['max']:.3g}")
    a = t.loc[("T4xE1", "D4_both_fixes", "oos")]
    b = t.loc[("core_ER_6+T4xE1", "D4_both_fixes", "oos")]
    L.append(f"- Review item 1, out of sample, D-4 both fixes: T4xE1 corrected max drawdown "
             f"{a.max_dd_incl_start_nav * 100:.4f}% (old convention {a.max_dd_from_first_close * 100:.4f}%); "
             f"core_ER_6 + T4xE1 {b.max_dd_incl_start_nav * 100:.4f}% (old {b.max_dd_from_first_close * 100:.4f}%). "
             "`test_drawdown.py` checks both to 1e-6 against the reviewer's -7.1896% and -5.9187%, and checks that a "
             "negative first return counts.")
    L.append(f"- Review item 2, out of sample, D-4 both fixes, T4xE1: Sharpe net 1x {a.sharpe_net1x:.4f}, net 2x "
             f"{a.sharpe_net2x:.4f}, geometric excess {a.ann_excess_geo * 100:.4f}%, vol {a.vol_ann * 100:.4f}%, "
             f"one-way turnover {a.turnover_instrument_oneway_per_year:.2f}x a year, Newey-West t {a.nw_t:.4f} "
             f"(lag {a.nw_lag}), hit rate {a.hit_rate_pos_excess_days * 100:.1f}% of days.\n")
    L.append("## Inputs (sha256)\n")
    for k, v in shas.items():
        L.append(f"- `{k}`: `{v}`")
    (out / "metrics.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------- main
def compute(root: Path, out: Path, with_figures: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    paths = check_inputs(root)
    out = guard_out(root, out)
    out.mkdir(parents=True, exist_ok=True)
    series = load_series(paths)
    tab = build_table(series)
    cons = pd.concat([consistency(tab, paths), series_identity(paths)], ignore_index=True)
    shas = {INPUTS[k]: sha256(p) for k, p in paths.items()}
    tab.to_csv(out / "v2_metrics.csv", index=False, float_format="%.12g")
    cons.to_csv(out / "consistency_vs_committed.csv", index=False, float_format="%.6g")
    (out / "inputs_sha256.json").write_text(json.dumps(shas, indent=1) + "\n", encoding="utf-8")
    write_md(tab, cons, shas, out)
    if with_figures:
        figures(series, tab, out)
    return tab, cons


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="results_2/metrics", help="output folder (relative to the repository root)")
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args()
    root = Path.cwd()
    tab, cons = compute(root, Path(a.out), with_figures=not a.no_figures)
    bad = cons[cons["abs_diff"] > TOL]
    print(f"rows: {len(tab)}; comparisons with committed files: {len(cons)}; max abs diff {cons['abs_diff'].max():.3g}")
    for r in tab[tab.window == "oos"].itertuples():
        print(f"  oos {r.series:16s} {r.variant:14s} Sharpe {r.sharpe_net1x:.4f} / {r.sharpe_net2x:.4f}  "
              f"maxDD incl. start NAV {r.max_dd_incl_start_nav:.6f}  (old {r.max_dd_from_first_close:.6f})")
    if len(bad):
        print(bad.to_string(), file=sys.stderr)
        raise SystemExit(3)


if __name__ == "__main__":
    main()
