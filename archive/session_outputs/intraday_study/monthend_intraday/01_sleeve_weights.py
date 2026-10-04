"""Daily hold weights of sleeves A and C on the futures instruments (ES16 / ZN16), per return day.

Uses the repo's own pure data functions (no backtest, no trial logging, no OOS unlock):
  * sleeve C: src.strategies.ifc_treasury.hold_weights(ticker="ZN16")
  * sleeve A: src.strategies.ifc_rebalance.hold_weights on ES16/ZN16 closes, planned calendar
In-sample weights come from period "IS" (data visible to 2024-10-02). The descriptive later window uses
period "FWD" (the repo's forward-test mode, which reads every cached date without unlocking OOS); the script
checks that FWD and IS weights agree on every in-sample return day (point-in-time check).

Output: sleeve_weights.parquet (date, A_ES, A_ZN, C_ZN, A_q, C_q, window ids) and month_info.csv.
Run from the repo root:
  GQH_DATA_DIR=<home>/.cache/gqh PYTHONIOENCODING=utf-8 <venv python> <this file>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path.cwd()))
from src import calendar_utils as CU  # noqa: E402
from src import engine as E  # noqa: E402
from src.strategies import ifc_rebalance as RB  # noqa: E402
from src.strategies import ifc_treasury as TR  # noqa: E402

OUT = Path(__file__).resolve().parent
IS_END = pd.Timestamp("2024-10-02")


def sleeve_c(period: str) -> pd.DataFrame:
    ohlc = E.load_ohlc(["ZN16"], period)
    hold = TR.hold_weights(period, ohlc=ohlc, ticker="ZN16")
    mt = TR.monthly_issuance(period, ticker="ZN16")
    return hold.rename(columns={"ZN16": "C_ZN"}), mt


def sleeve_a(period: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    p = RB._params(equity="ES16", bond="ZN16")
    ohlc = E.load_ohlc(["ES16", "ZN16"], period)
    close = ohlc["close"][["ES16", "ZN16"]].ffill(limit=5)
    planned = CU.to_planned(close)
    hold = CU.planned_to_realized(RB.hold_weights(planned, p), close.index)
    mt = RB.month_table(planned, p)
    return hold.rename(columns={"ES16": "A_ES", "ZN16": "A_ZN"}), mt


def main() -> None:
    res = {}
    for period in ("IS", "FWD"):
        c, cmt = sleeve_c(period)
        a, amt = sleeve_a(period)
        w = pd.concat([a, c], axis=1).fillna(0.0)
        res[period] = (w, cmt, amt)
    w_is, cmt_is, amt_is = res["IS"]
    w_fw, cmt_fw, amt_fw = res["FWD"]
    # point-in-time check: FWD weights equal IS weights on in-sample return days, except the window that
    # straddles IS_END (its exit lies after the in-sample end, so period IS cannot hold it to T)
    common = w_is.index[w_is.index <= IS_END]
    diff = (w_fw.reindex(common) - w_is.reindex(common)).abs()
    bad = diff[(diff > 1e-12).any(axis=1)]
    print("in-sample days where FWD != IS weights:", len(bad))
    if len(bad):
        print(bad.tail(10))
    w = w_fw.copy()
    w.index.name = "date"
    # window ids: the month-end T each hold day belongs to
    for s, col in (("A", "A_ES"), ("C", "C_ZN")):
        held = w[col] != 0
        cal = w.index
        mo = CU.month_offsets(cal)
        # windows end at T (b = 0) for both sleeves: label each held day with its own month's T
        w[f"{s}_T"] = pd.Series(mo["T"].values, index=cal).where(held)
        w[f"{s}_off"] = pd.Series(mo["off_own"].values, index=cal).where(held)
    w.reset_index().to_parquet(OUT / "sleeve_weights.parquet", index=False)
    # month info
    cm = cmt_fw.reset_index()[["month", "T", "cutoff", "S", "q"]].rename(columns={"q": "C_q"})
    am = amt_fw.reset_index()[["T", "obs_date", "D", "z", "q", "vol_eq", "vol_bd", "active"]].rename(
        columns={"q": "A_q", "vol_eq": "A_vol_ES", "vol_bd": "A_vol_ZN", "active": "A_active"})
    info = cm.merge(am, on="T", how="outer").sort_values("T")
    info.to_csv(OUT / "month_info.csv", index=False)
    # summary
    for s, col in (("A", "A_ES"), ("C", "C_ZN")):
        held = w[col] != 0
        print(s, "held days", int(held.sum()), "first", w.index[held][0].date(), "last", w.index[held][-1].date(),
              "windows", w.loc[held, f"{s}_T"].nunique())
        offs = w.loc[held, f"{s}_off"].value_counts().sort_index()
        print("  offsets:", offs.to_dict())
    print(w[(w.A_ES != 0) | (w.C_ZN != 0)].tail(12))


if __name__ == "__main__":
    main()
