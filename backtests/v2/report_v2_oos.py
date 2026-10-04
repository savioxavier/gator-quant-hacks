"""Deviation D-3 report: metrics, daily return series and equity curves of the ONE v2 out-of-sample evaluation.

    python report_v2_oos.py [--run <run folder>] [--out <report folder>] [--committed <results/v2>]

Defaults: --run backtests/results/v2_oos/run (written by run_v2_chrono.py under D-3), --out backtests/results/v2_oos,
--committed backtests/results/v2. Reads only the run's saved daily series (excess returns, turnover, the fourth
sleeve's multiplier; no market data, no price levels) and the committed in-sample tables (consistency check). It
changes no signal, position, parameter, cost or window.

Series: T4xE1 (the chosen combination), VariantA_frozen(T0fxE1) (the reference), core_ER_6 and core_ER_6+T4xE1
(the portfolio test). Windows: selection, validation, full in-sample, out-of-sample. Bases: net 1x, net 2x, gross.
Metrics (daily excess returns over the T-bill, 252 days a year):
  ann_return_arith  mean x 252                    ann_return_geo  compounded, annualised
  ann_total_return_geo  compounded (excess + T-bill), annualised
  ann_vol           sd (ddof 1) x sqrt(252)       sharpe  v2lib.sharpe (mean / sd x sqrt(252), > 20 days)
  max_drawdown      v2lib.max_dd (compounded excess equity)   hit_rate  share of days with return > 0
  turnover_per_year strategies: sum of daily one-way turnover (fraction of NAV, roll trades included) / years;
                    portfolios: overlay turnover (|change in sleeve multiplier| x sleeve instrument gross, combine.build)
                    / years. fed_sleeve_turnover_per_year: the T4xE1 sleeve's own turnover x its multiplier.
  nw_t              v2lib.nw_t (Newey-West t of the mean)
A strategy window never includes days before its first held position (as run_v2.stats_row).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent                  # backtests/v2
BTS = HERE.parent
sys.path.insert(0, str(HERE))
import v2lib as L  # noqa: E402

CHOSEN = "T4xE1"
WINDOWS = [("selection", "2016-01-04", "2020-12-31"), ("validation", "2021-01-01", "2024-10-02"),
           ("full_is", "2016-01-04", "2024-10-02"), ("oos", "2024-10-03", "2026-10-02")]
BASES = ("net_1x", "net_2x", "gross")
EQUITY_START = "2016-01-04"
OOS_START = "2024-10-03"
ANN = L.ANN

# reference palette (dataviz skill): categorical slots 1-3, neutral ink, chart surface
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, SURF = "#0b0b0b", "#52514e", "#fcfcfb"


def load(run: Path) -> dict:
    """series name -> DataFrame with columns net_1x, net_2x, gross, turnover (+ fed_turnover for the portfolio)."""
    out = {}
    for name, f in ((CHOSEN, f"daily_{CHOSEN}_full.parquet"),
                    ("VariantA_frozen(T0fxE1)", "daily_VariantA_frozen_T0fxE1_full.parquet")):
        s = pd.read_parquet(run / f)
        first = s.index[s["gross_exposure"] > 0][0]
        df = pd.DataFrame({"net_1x": s["ex1"], "net_2x": s["ex2"], "gross": s["exg"], "turnover": s["turnover"],
                           "rf": s["rf"]})
        out[name] = df.loc[first:]
    rf = out[CHOSEN]["rf"]
    p = pd.read_parquet(run / "daily_portfolio_full.parquet")
    for name in ("core_ER_6", f"core_ER_6+{CHOSEN}"):
        df = pd.DataFrame({b: p[f"{name}|{b}"] for b in BASES})
        df["turnover"] = p[f"{name}|overlay_turnover"]
        df = df.dropna(subset=["net_1x"])
        if name != "core_ER_6":
            m = p[f"{name}|m_FED_{CHOSEN}"].reindex(df.index).fillna(0.0)
            df["fed_turnover"] = m * out[CHOSEN]["turnover"].reindex(df.index).fillna(0.0)
        df["rf"] = rf.reindex(df.index.union(rf.index)).sort_index().ffill().reindex(df.index).fillna(0.0)
        out[name] = df
    return out


def metrics(df: pd.DataFrame, basis: str, a: str, b: str) -> dict:
    s = slice(pd.Timestamp(a), pd.Timestamp(b))
    x = df[basis].loc[s].dropna()
    if len(x) < 2:
        return {"n_days": int(len(x))}
    yrs = len(x) / ANN
    rf = df["rf"].reindex(x.index).fillna(0.0)
    row = {"start": str(x.index[0].date()), "end": str(x.index[-1].date()), "n_days": int(len(x)),
           "ann_return_arith": float(x.mean() * ANN), "ann_return_geo": float((1 + x).prod() ** (1 / yrs) - 1),
           "ann_total_return_geo": float((1 + x + rf).prod() ** (1 / yrs) - 1),
           "ann_vol": float(x.std(ddof=1) * math.sqrt(ANN)), "sharpe": L.sharpe(x), "max_drawdown": L.max_dd(x),
           "hit_rate": float((x > 0).mean()), "turnover_per_year": float(df["turnover"].loc[x.index].sum() / yrs),
           "nw_t": L.nw_t(x)}
    if "fed_turnover" in df:
        row["fed_sleeve_turnover_per_year"] = float(df["fed_turnover"].loc[x.index].sum() / yrs)
    return row


def table(series: dict) -> pd.DataFrame:
    rows = []
    for name, df in series.items():
        for wn, a, b in WINDOWS:
            for basis in BASES:
                rows.append({"series": name, "window": wn, "basis": basis, **metrics(df, basis, a, b)})
    return pd.DataFrame(rows)


def consistency(tab: pd.DataFrame, run: Path, committed: Path) -> dict:
    """The full-period series of the D-3 run against the committed in-sample tables and the run's own OOS files."""
    g = tab.set_index(["series", "window", "basis"]).sort_index()
    out = {}
    wa = pd.read_csv(committed / "windows_all.csv").set_index(["combo", "window"])
    d = []
    for name, combo in ((CHOSEN, CHOSEN), ("VariantA_frozen(T0fxE1)", "T0fxE1")):
        for wn in ("selection", "validation", "full_is"):
            c = wa.loc[(combo, wn)]
            pairs = [(g.loc[(name, wn, "net_1x"), "sharpe"], c["sharpe_net1x"]),
                     (g.loc[(name, wn, "net_2x"), "sharpe"], c["sharpe_net2x"]),
                     (g.loc[(name, wn, "gross"), "sharpe"], c["sharpe_gross"]),
                     (g.loc[(name, wn, "net_1x"), "ann_return_arith"], c["ann_excess_arith"]),
                     (g.loc[(name, wn, "net_1x"), "ann_vol"], c["vol"]),
                     (g.loc[(name, wn, "net_1x"), "max_drawdown"], c["max_dd_excess"]),
                     (g.loc[(name, wn, "net_1x"), "turnover_per_year"], c["turnover_per_year"])]
            d += [abs(float(x) - float(y)) for x, y in pairs]
    out["strategies_is_vs_committed_windows_all_max_abs_diff"] = max(d)
    pc = pd.read_csv(committed / "portfolio.csv").set_index(["portfolio", "window"])
    d = []
    for name in ("core_ER_6", f"core_ER_6+{CHOSEN}"):
        for wn in ("selection", "validation", "full_is"):
            c = pc.loc[(name, wn)]
            d += [abs(float(g.loc[(name, wn, "net_1x"), "sharpe"]) - c["sharpe_net1x"]),
                  abs(float(g.loc[(name, wn, "net_2x"), "sharpe"]) - c["sharpe_net2x"]),
                  abs(float(g.loc[(name, wn, "net_1x"), "ann_return_geo"]) - c["ann_excess_geo"]),
                  abs(float(g.loc[(name, wn, "net_1x"), "ann_vol"]) - c["vol"]),
                  abs(float(g.loc[(name, wn, "net_1x"), "max_drawdown"]) - c["max_dd_excess"])]
    out["portfolio_is_vs_committed_portfolio_csv_max_abs_diff"] = max(d)
    rec = json.loads((run / "oos_chosen.json").read_text(encoding="utf-8"))
    out["run_is_consistency_max_abs_diff (oos_chosen.json)"] = rec["is_consistency_max_abs_diff"]
    o = g.loc[(CHOSEN, "oos")]
    out["oos_vs_oos_chosen_json_max_abs_diff"] = max(
        abs(float(o.loc["net_1x", "sharpe"]) - rec["sharpe_net1x"]), abs(float(o.loc["net_2x", "sharpe"]) - rec["sharpe_net2x"]),
        abs(float(o.loc["gross", "sharpe"]) - rec["sharpe_gross"]), abs(float(o.loc["net_1x", "ann_vol"]) - rec["vol"]),
        abs(float(o.loc["net_1x", "max_drawdown"]) - rec["max_dd_excess"]))
    po = pd.read_csv(run / "portfolio_oos.csv").set_index("portfolio")
    out["portfolio_oos_vs_portfolio_oos_csv_max_abs_diff"] = max(
        abs(float(g.loc[(n, "oos", b), "sharpe"]) - po.loc[n, f"sharpe_{b.replace('_', '')}"])
        for n in ("core_ER_6", f"core_ER_6+{CHOSEN}") for b in ("net_1x", "net_2x"))
    return out


def daily(series: dict) -> pd.DataFrame:
    cols = {}
    for name, df in series.items():
        for b in BASES:
            cols[f"{name}|{b}"] = df[b]
    cols[f"{CHOSEN}|turnover"] = series[CHOSEN]["turnover"]
    out = pd.DataFrame(cols).sort_index().loc[:"2026-10-02"]
    out = out.loc[out.index >= series[CHOSEN].index[0]]
    lab = pd.Series("pre_selection", index=out.index)
    for wn, a, b in (WINDOWS[0], WINDOWS[1], WINDOWS[3]):
        lab[(out.index >= pd.Timestamp(a)) & (out.index <= pd.Timestamp(b))] = wn
    out.insert(0, "window", lab)
    out.index.name = "date"
    return out


def equity_png(curves: list[tuple[str, pd.Series, str, str]], title: str, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2,
                         "ytick.color": INK2, "text.color": INK})
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(10, 7.2), height_ratios=[3, 2], facecolor=SURF)
    oos0 = pd.Timestamp(OOS_START)
    for axis, lo in ((ax, pd.Timestamp(EQUITY_START)), (bx, oos0)):
        axis.set_facecolor(SURF)
        for lab, x, color, ls in curves:
            r = x.loc[lo:"2026-10-02"].dropna()
            eq = (1 + r).cumprod()
            eq = pd.concat([pd.Series([1.0], index=[r.index[0] - pd.Timedelta(days=1)]), eq])
            axis.plot(eq.index, eq.to_numpy(), color=color, ls=ls, lw=1.6 if ls == "-" else 1.3, label=lab)
        axis.axhline(1.0, color=INK2, lw=0.6, alpha=0.6)
        axis.grid(axis="y", color="#e4e3df", lw=0.6)
        for side in ("top", "right"):
            axis.spines[side].set_visible(False)
        axis.set_ylabel("growth of 1 (excess of T-bill)")
    ax.axvspan(pd.Timestamp("2016-01-04"), pd.Timestamp("2020-12-31"), color="#ecebe7", lw=0, zorder=0)
    ax.axvspan(pd.Timestamp("2021-01-01"), pd.Timestamp("2024-10-02"), color="#f4f3f0", lw=0, zorder=0)
    ax.axvspan(oos0, pd.Timestamp("2026-10-02"), color="#fbe3d6", lw=0, zorder=0)
    ax.axvline(oos0, color=INK2, lw=0.9, ls=":")
    top = ax.get_ylim()[1]
    for xx, t in ((pd.Timestamp("2016-02-01"), "IS selection"), (pd.Timestamp("2021-02-01"), "IS validation"),
                  (pd.Timestamp("2024-11-01"), "out-of-sample")):
        ax.text(xx, top, t, va="top", ha="left", fontsize=8.5, color=INK2)
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    bx.set_title("Out-of-sample only (2024-10-03 to 2026-10-02), rebased to 1", loc="left", fontsize=9.5, color=INK2)
    bx.set_facecolor("#fdf3ec")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.93), frameon=False, fontsize=8.5)
    for axis in (ax, bx):
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y" if axis is ax else "%Y-%m"))
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURF)
    plt.close(fig)


def md_table(tab: pd.DataFrame, series: str) -> str:
    t = tab[tab["series"] == series]
    head = "| window | basis | Sharpe | ann. return (arith) | ann. return (geo) | vol | max DD | turnover/yr | hit rate |\n" \
           "|---|---|---|---|---|---|---|---|---|\n"
    lines = []
    for _, r in t.iterrows():
        lines.append(f"| {r['window']} | {r['basis']} | {r['sharpe']:.3f} | {r['ann_return_arith']:.2%} | "
                     f"{r['ann_return_geo']:.2%} | {r['ann_vol']:.2%} | {r['max_drawdown']:.2%} | "
                     f"{r['turnover_per_year']:.1f} | {r['hit_rate']:.1%} |")
    return head + "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(BTS / "results" / "v2_oos" / "run"))
    ap.add_argument("--out", default=str(BTS / "results" / "v2_oos"))
    ap.add_argument("--committed", default=str(BTS / "results" / "v2"))
    a = ap.parse_args()
    run, out, committed = Path(a.run), Path(a.out), Path(a.committed)
    out.mkdir(parents=True, exist_ok=True)
    series = load(run)
    tab = table(series)
    tab.to_csv(out / "metrics.csv", index=False)
    cons = consistency(tab, run, committed)
    (out / "consistency.json").write_text(json.dumps(cons, indent=2), encoding="utf-8")
    d = daily(series)
    d.to_csv(out / "daily_returns.csv", float_format="%.10g")
    d.to_parquet(out / "daily_returns.parquet")
    md = ["# v2 metrics under deviation D-3 (generated by backtests/v2/report_v2_oos.py)\n\n",
          "Daily returns in excess of the 3-month T-bill. Turnover: strategies, one-way fraction of NAV per year; "
          "portfolios, overlay turnover per year.\n"]
    for name in series:
        md += [f"\n## {name}\n\n", md_table(tab, name)]
    (out / "metrics.md").write_text("".join(md), encoding="utf-8")
    s = series
    equity_png([("net, 1x costs", s[CHOSEN]["net_1x"], C1, "-"), ("net, 2x costs", s[CHOSEN]["net_2x"], C2, "-"),
                ("gross", s[CHOSEN]["gross"], C3, "--")],
               "v2 chosen combination T4xE1 (decision rule FAILED; out-of-sample reported under D-3)",
               out / "equity_T4xE1.png")
    va = "VariantA_frozen(T0fxE1)"
    equity_png([("net, 1x costs", s[va]["net_1x"], C1, "-"), ("net, 2x costs", s[va]["net_2x"], C2, "-"),
                ("gross", s[va]["gross"], C3, "--")],
               "Variant A as frozen (T0fxE1), reference", out / "equity_VariantA_T0fxE1.png")
    pa = f"core_ER_6+{CHOSEN}"
    equity_png([("core_ER_6, net 1x", s["core_ER_6"]["net_1x"], C1, "-"),
                ("core_ER_6, net 2x", s["core_ER_6"]["net_2x"], C1, "--"),
                (f"{pa}, net 1x", s[pa]["net_1x"], C2, "-"), (f"{pa}, net 2x", s[pa]["net_2x"], C2, "--")],
               "Portfolio test: core_ER_6 alone vs core_ER_6 + T4xE1 (fourth sleeve, equal risk, 6% target)",
               out / "equity_portfolio.png")
    print(json.dumps(cons, indent=1))


if __name__ == "__main__":
    main()
