"""Run Variant A IS simulation. rf=0, 252-day annualization. No OOS metrics."""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path as _P

sys.path.insert(0, str(_P(__file__).resolve().parent))

from config import OUTPUTS, ROOT, TRIALS

import download_markets
import download_speeches
import score
import backtest


def append_trial(summary: dict, trial: int, reason: str) -> None:
    TRIALS.mkdir(parents=True, exist_ok=True)
    path = TRIALS / "log.csv"
    row = {
        "trial": trial,
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reason": reason,
        "sharpe_gross": summary.get("sharpe_gross"),
        "sharpe_1x": summary.get("sharpe_1x"),
        "sharpe_2x": summary.get("sharpe_2x"),
        "sharpe_tlt_1x": summary.get("sharpe_tlt_1x"),
        "sharpe_uup_1x": summary.get("sharpe_uup_1x"),
        "sharpe_2022_1x": summary.get("sharpe_2022_1x"),
        "sharpe_rest_1x": summary.get("sharpe_rest_1x"),
        "corr_C_DGS2_tminus2": summary.get("corr_C_DGS2_tminus2"),
        "turnover_ann": summary.get("turnover_ann"),
        "n_docs_kept": summary.get("n_docs_kept"),
        "n_is_days": summary.get("n_is_days"),
        "first_z": summary.get("first_z"),
        "last_ret": summary.get("last_ret"),
        "n_fomc": summary.get("n_fomc"),
    }
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            w.writeheader()
        w.writerow(row)


def bug_hunt(summary: dict) -> None:
    print("\n=== BUG HUNT (1x Sharpe > 1.5) ===")
    print("Checks: IS cut, next-open lag, adj-open, cost drag, FOMC haircut, expanding z min 252.")
    print(f"max_px_date={summary.get('max_px_date')} (must be <= 2024-10-02)")
    print(f"last_ret={summary.get('last_ret')} first_z={summary.get('first_z')}")
    print(f"turnover_ann={summary.get('turnover_ann')} (extreme turnover => cost bug or daily churn)")
    print(f"gross vs 1x vs 2x: {summary.get('sharpe_gross')} {summary.get('sharpe_1x')} {summary.get('sharpe_2x')}")
    print("If gross ~ 1x, costs are not biting (possible zero turnover / leftover weights).")
    print("If 2022 Sharpe >> rest, one-regime artifact not a general Fedspeak edge.")


def main() -> None:
    print("== download speeches ==")
    download_speeches.main()
    print("== download markets/fred/fomc ==")
    download_markets.main()
    print("== score ==")
    score.main()
    print("== backtest IS ==")
    summary = backtest.main()
    append_trial(summary, trial=1, reason="initial IS simulation Variant A")
    s1 = summary.get("sharpe_1x")
    if s1 is not None and s1 > 1.5:
        bug_hunt(summary)
        append_trial(summary, trial=2, reason="debug: flag 1x Sharpe>1.5 — metrics unchanged pending code fix")
    print(f"done. outputs at {OUTPUTS}")


if __name__ == "__main__":
    main()
