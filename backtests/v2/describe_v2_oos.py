"""Deviation D-3, descriptive only: how the v2 out-of-sample result is distributed over time.

    python describe_v2_oos.py [--report <backtests/results/v2_oos>]

Written AFTER the out-of-sample result was seen (unlike report_v2_oos.py, whose metric definitions were fixed before
the run). It reads only daily_returns.csv written by report_v2_oos.py, changes nothing and tests nothing: it shows
where in the window the out-of-sample P&L came from. Output: oos_concentration.csv.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OOS = ("2024-10-03", "2026-10-02")
SERIES = ("T4xE1", "VariantA_frozen(T0fxE1)", "core_ER_6", "core_ER_6+T4xE1")


def row(x: pd.Series, label: str, series: str) -> dict:
    x = x.dropna()
    sd = x.std(ddof=1)
    return {"series": series, "subset": label, "start": str(x.index[0].date()), "end": str(x.index[-1].date()),
            "n_days": int(len(x)), "cum_excess_return": float((1 + x).prod() - 1),
            "ann_return_arith": float(x.mean() * 252), "sharpe": float(x.mean() / sd * math.sqrt(252)) if sd > 0 else None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=str(HERE.parent / "results" / "v2_oos"))
    a = ap.parse_args()
    rep = Path(a.report)
    d = pd.read_csv(rep / "daily_returns.csv", index_col="date", parse_dates=True)
    rows = []
    for s in SERIES:
        x = d[f"{s}|net_1x"].loc[OOS[0]:OOS[1]].dropna()
        rows.append(row(x, "oos, all days", s))
        for k in (1, 5, 10, 20):
            rows.append(row(x.iloc[:-k], f"oos without its last {k} days", s))
        rows.append(row(x.loc[:"2026-05-21"], "oos, Powell (to 2026-05-21)", s))
        rows.append(row(x.loc["2026-05-22":], "oos, Warsh (from 2026-05-22)", s))
        for y in (2024, 2025, 2026):
            rows.append(row(x.loc[str(y)], f"oos, calendar {y}", s))
        top = x.sort_values(ascending=False).head(5)
        rows.append({"series": s, "subset": "share of the oos daily-return sum from its 5 best days",
                     "value": float(top.sum() / x.sum()) if x.sum() != 0 else None,
                     "days": " ".join(str(t.date()) for t in top.index)})
    pd.DataFrame(rows).to_csv(rep / "oos_concentration.csv", index=False)
    print(pd.DataFrame(rows).to_string())


if __name__ == "__main__":
    main()
