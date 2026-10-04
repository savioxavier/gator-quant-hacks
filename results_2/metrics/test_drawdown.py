"""Regression tests for the drawdown convention (review item 1).

    python results_2/metrics/test_drawdown.py        (from the repository root; also runs under pytest)

1. A negative first return must count: the running peak includes the window's starting NAV of 1.
2. The reviewer's two out-of-sample checks, D-4 both fixes, reproduced to 1e-6 from the committed daily series:
   T4xE1 -7.1896% (old convention -6.4333%) and core_ER_6 + T4xE1 -5.9187% (old -5.2824%).
3. The old convention still reproduces the committed `max_dd_excess` numbers, so the old figures stay traceable.
Exits 1 if any test fails and 2 if a committed input is missing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True                       # leave no cache files in the working tree
sys.path.insert(0, str(HERE))
import compute_metrics as CM  # noqa: E402

D4_DAILY = "backtests/results/v2_d4/daily_returns.parquet"
D4_METRICS = "backtests/results/v2_d4/metrics.csv"
OOS = ("2024-10-03", "2026-10-02")
REVIEWER = {"T4xE1|both|net_1x": -0.071896, "core_ER_6+T4xE1|both|net_1x": -0.059187}
REPORTED = {"T4xE1|both|net_1x": -0.064333, "core_ER_6+T4xE1|both|net_1x": -0.052824}


def _need(path: str) -> Path:
    p = Path(path)
    if not p.is_file():
        print(f"MISSING INPUT: {path}", file=sys.stderr)
        raise SystemExit(2)
    return p


def test_negative_first_return_counts():
    r = np.array([-0.10, 0.05, 0.02])                       # NAV 1 -> 0.900 -> 0.945 -> 0.9639
    assert abs(CM.max_dd_incl_start_nav(r) - (-0.10)) < 1e-15
    assert CM.max_dd_from_first_close(r) == 0.0              # the defect being corrected: the first loss is lost
    d = CM.drawdown_incl_start_nav(r, pd.date_range("2024-10-03", periods=3, freq="B"))
    assert d["peak"] == "start_nav" and d["trough"] == "2024-10-03"


def test_single_negative_day():
    assert abs(CM.max_dd_incl_start_nav([-0.05]) - (-0.05)) < 1e-15
    assert CM.max_dd_from_first_close([-0.05]) == 0.0


def test_all_negative_days():
    r = [-0.01] * 5
    assert abs(CM.max_dd_incl_start_nav(r) - (0.99 ** 5 - 1)) < 1e-15
    assert abs(CM.max_dd_from_first_close(r) - (0.99 ** 4 - 1)) < 1e-15


def test_conventions_agree_after_a_positive_first_day():
    r = np.array([0.02, -0.05, 0.01, -0.03, 0.04])
    assert abs(CM.max_dd_incl_start_nav(r) - CM.max_dd_from_first_close(r)) < 1e-15


def test_conventions_agree_when_start_nav_is_regained_before_the_trough():
    r = np.array([-0.01, 0.03, -0.10, 0.02])                 # back above 1 on day 2, trough on day 3
    assert abs(CM.max_dd_incl_start_nav(r) - CM.max_dd_from_first_close(r)) < 1e-15
    assert abs(CM.max_dd_incl_start_nav(r) - (-0.10)) < 1e-15


def test_no_drawdown():
    d = CM.drawdown_incl_start_nav([0.01, 0.02])
    assert d["depth"] == 0.0 and d["peak"] is None and d["trough"] is None


def test_reviewer_oos_checks_to_1e6():
    d = pd.read_parquet(_need(D4_DAILY)).loc[OOS[0]:OOS[1]]
    assert len(d) == 501
    for col, target in REVIEWER.items():
        x = d[col].to_numpy()
        got = CM.max_dd_incl_start_nav(x)
        assert abs(got - target) < 1e-6, (col, got, target)
        old = CM.max_dd_from_first_close(x)
        assert abs(old - REPORTED[col]) < 1e-6, (col, old, REPORTED[col])
        assert x[0] < 0                                       # the window opens with a loss: why they differ


def test_old_convention_reproduces_committed_numbers():
    d = pd.read_parquet(_need(D4_DAILY))
    m = pd.read_csv(_need(D4_METRICS))
    n = 0
    for (series, variant), col in ((("T4xE1", "both"), "T4xE1|both|net_1x"),
                                   (("T4xE1", "original"), "T4xE1|original|net_1x"),
                                   (("core_ER_6+T4xE1", "both"), "core_ER_6+T4xE1|both|net_1x"),
                                   (("core_ER_6+T4xE1", "original"), "core_ER_6+T4xE1|original|net_1x"),
                                   (("core_ER_6", "as_committed"), "core_ER_6|as_committed|net_1x")):
        for wn, a, b in CM.WINDOWS:
            c = m[(m.series == series) & (m.variant == variant) & (m.window == wn)
                  & m.group.isin(["strategy", "portfolio"])].iloc[0]
            x = d[col].loc[a:b].to_numpy()
            assert abs(CM.max_dd_from_first_close(x) - c.max_dd_excess) < 1e-12
            assert CM.max_dd_incl_start_nav(x) <= CM.max_dd_from_first_close(x) + 1e-15
            n += 1
    assert n == 20


def test_written_table_carries_the_corrected_numbers():
    p = HERE / "v2_metrics.csv"
    if not p.is_file():
        print(f"MISSING INPUT: {p.relative_to(HERE.parent.parent).as_posix()} (run compute_metrics.py first)",
              file=sys.stderr)
        raise SystemExit(2)
    t = pd.read_csv(p).set_index(["series", "variant", "window"])
    assert abs(t.loc[("T4xE1", "D4_both_fixes", "oos"), "max_dd_incl_start_nav"] - (-0.071896)) < 1e-6
    assert abs(t.loc[("core_ER_6+T4xE1", "D4_both_fixes", "oos"), "max_dd_incl_start_nav"] - (-0.059187)) < 1e-6
    assert abs(t.loc[("T4xE1", "D4_both_fixes", "oos"), "max_dd_from_first_close"] - (-0.064333)) < 1e-6


def main() -> int:
    tests = [(k, v) for k, v in globals().items() if k.startswith("test_") and callable(v)]
    failed = 0
    for name, f in tests:
        try:
            f()
            print(f"PASS {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {name}: {e}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
