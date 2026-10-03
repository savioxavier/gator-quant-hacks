"""Paths and loaders shared by the replication scripts."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
THEIRS = HERE.parents[1]  # strategies/01
THEIR_PROC = THEIRS / "data" / "processed"
THEIR_OUT = THEIRS / "outputs"
REPO = Path(os.environ["GQH_REPO"]) if os.environ.get("GQH_REPO") else Path(__file__).resolve().parents[5] / "gqh-flow-clock"  # clone of github.com/minh-stakc/gqh-flow-clock

IS_END = "2024-10-02"
MARKET_START = "2010-01-04"
HOLDOUT = ("2021-01-01", "2024-10-02")
OOS = ("2024-10-03", "2026-10-02")


def engine():
    """Our backtest engine (read-only use: loaders, simulate, perf_stats)."""
    assert os.environ.get("GQH_OOS_UNLOCK") != "1", "OOS unlock must stay off"
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from src import engine as E  # noqa: E402
    return E


def their_markets() -> pd.DataFrame:
    px = pd.read_csv(THEIR_PROC / "markets.csv", index_col=0, parse_dates=True)
    return px.loc[px.index <= pd.Timestamp(IS_END)]


def their_fomc() -> pd.Series:
    return pd.read_csv(THEIR_PROC / "fomc_dates.csv", parse_dates=["fomc_date"])["fomc_date"]


def their_dgs2() -> pd.Series:
    d = pd.read_csv(THEIR_PROC / "fred_DGS2.csv", parse_dates=["date"])
    return d.set_index("date")["value"].sort_index()


def our_opens(period: str = "IS", start: str = MARKET_START) -> tuple[pd.DatetimeIndex, pd.DataFrame, pd.DataFrame]:
    E = engine()
    ohlc = E.load_ohlc(["TLT", "UUP"], period)
    o, c = ohlc["open"], ohlc["close"]
    cal = o.index[o.index >= pd.Timestamp(start)]
    return cal, o.loc[cal], c.loc[cal]


def our_dgs2(period: str = "IS") -> pd.Series:
    E = engine()
    return E.load_series("fred_daily.parquet", period)["DGS2"]


def open_to_open(o: pd.Series) -> pd.Series:
    return o.shift(-1) / o - 1.0


def corr_c_dgs2(c: pd.Series, dgs2: pd.Series, idx: pd.DatetimeIndex, cal: pd.DatetimeIndex) -> float:
    d = dgs2.reindex(cal).ffill().shift(2)
    j = pd.concat([c.reindex(idx), d.reindex(idx)], axis=1).dropna()
    return float(j.iloc[:, 0].corr(j.iloc[:, 1]))
