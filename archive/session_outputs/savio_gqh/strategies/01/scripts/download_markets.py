"""Download TLT/UUP (and IEF) adjusted opens, FRED series, FOMC announcement dates. Cut at 2024-10-02."""

from __future__ import annotations

import re
import time
from io import StringIO

import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

import sys
from pathlib import Path as _P

sys.path.insert(0, str(_P(__file__).resolve().parent))

from config import (
    DATA_PROC,
    DATA_RAW,
    FOMC_CAL,
    FOMC_HIST,
    FRED_CSV,
    IS_END,
    MARKET_START,
    UA,
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept": "text/html,text/csv,*/*"})


def cut_is(df: pd.DataFrame, col: str | None = None) -> pd.DataFrame:
    end = pd.Timestamp(IS_END)
    if col:
        s = pd.to_datetime(df[col])
        return df.loc[s <= end].copy()
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    return df.loc[df.index <= end]


def _flatten_ohlc(part: pd.DataFrame) -> pd.DataFrame:
    part = part.copy()
    if isinstance(part.columns, pd.MultiIndex):
        names = list(part.columns.names or [])
        if "Price" in names:
            part.columns = part.columns.get_level_values("Price")
        else:
            part.columns = [str(c[0]) for c in part.columns]
    part.columns = [str(c) for c in part.columns]
    return part


def _naive_index(idx) -> pd.DatetimeIndex:
    idx = pd.to_datetime(idx)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_convert("America/New_York").tz_localize(None)
    return pd.DatetimeIndex(idx).normalize()


def download_prices() -> pd.DataFrame:
    end = (pd.Timestamp(IS_END) + pd.Timedelta(days=3)).strftime("%Y-%m-%d")
    frames = []
    for t in ["TLT", "UUP", "IEF"]:
        raw = yf.download(
            t,
            start=MARKET_START,
            end=end,
            auto_adjust=False,
            actions=False,
            progress=False,
            threads=False,
        )
        part = _flatten_ohlc(raw)
        adj_o = part["Open"] * (part["Adj Close"] / part["Close"])
        frames.append(
            pd.DataFrame(
                {
                    f"{t}_open": part["Open"],
                    f"{t}_close": part["Close"],
                    f"{t}_adjclose": part["Adj Close"],
                    f"{t}_adjopen": adj_o,
                }
            )
        )
    px = pd.concat(frames, axis=1)
    px.index = _naive_index(px.index)
    px = px.sort_index()
    extra = px.index.max()
    if extra is not pd.NaT and extra > pd.Timestamp(IS_END):
        print(f"dropping price rows after {IS_END}: max_downloaded={extra.date()}")
    px = cut_is(px)
    for t in ["TLT", "UUP", "IEF"]:
        ao = px[f"{t}_adjopen"]
        px[f"{t}_ret"] = ao.shift(-1) / ao - 1.0
    DATA_PROC.mkdir(parents=True, exist_ok=True)
    px.to_csv(DATA_PROC / "markets.csv")
    print(f"markets {px.index.min().date()} .. {px.index.max().date()} n={len(px)}")
    assert px.index.max() <= pd.Timestamp(IS_END)
    return px


def download_fred(sid: str) -> pd.DataFrame:
    url = FRED_CSV.format(sid=sid)
    last_err = None
    r = None
    for i in range(1):
        try:
            r = SESSION.get(url, timeout=12)
            r.raise_for_status()
            break
        except Exception as e:
            last_err = e
            print(f"fred {sid} retry {i+1}: {e}")
            time.sleep(1.5)
            r = None
    if r is None:
        raise RuntimeError(f"fred {sid} failed: {last_err}")
    df = pd.read_csv(StringIO(r.text))
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])
    df = df.rename(columns={date_col: "date", sid: "value"})
    if "value" not in df.columns:
        df = df.rename(columns={df.columns[1]: "value"})
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = cut_is(df, "date")
    df.to_csv(DATA_PROC / f"fred_{sid}.csv", index=False)
    print(f"fred {sid} {df['date'].min().date()} .. {df['date'].max().date()} n={len(df)}")
    return df


def _two_year_col(df: pd.DataFrame) -> str:
    for c in df.columns:
        cl = str(c).strip().lower().replace(" ", "")
        if cl in {"2yr", "2year", "dgs2"}:
            return c
    raise KeyError(f"no 2yr column in {list(df.columns)}")


def download_dgs2_treasury() -> pd.DataFrame:
    """H.15 2y par yield via Treasury CSVs (same source FRED DGS2 wraps)."""
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    tdir = DATA_RAW / "treasury"
    tdir.mkdir(parents=True, exist_ok=True)
    urls = [
        "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rate-archives/par-yield-curve-rates-2010-2019.csv",
        "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rate-archives/par-yield-curve-rates-2020-2023.csv",
        "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2024/all?type=daily_treasury_yield_curve&field_tdr_date_value=2024&page&_format=csv",
    ]
    frames = []
    for i, url in enumerate(urls):
        dest = tdir / f"yc_{i}.csv"
        if not dest.exists() or dest.stat().st_size < 100:
            rr = SESSION.get(url, timeout=60)
            rr.raise_for_status()
            dest.write_text(rr.text, encoding="utf-8")
        raw = dest.read_text(encoding="utf-8")
        df = pd.read_csv(StringIO(raw))
        dcol = df.columns[0]
        ycol = _two_year_col(df)
        part = pd.DataFrame(
            {
                "date": pd.to_datetime(df[dcol], errors="coerce"),
                "value": pd.to_numeric(df[ycol], errors="coerce"),
            }
        )
        frames.append(part)
    df = pd.concat(frames, ignore_index=True).dropna(subset=["date"])
    df = df.drop_duplicates("date").sort_values("date")
    df = cut_is(df, "date")
    df.to_csv(DATA_PROC / "fred_DGS2.csv", index=False)
    print(f"DGS2 treasury-fallback {df['date'].min().date()} .. {df['date'].max().date()} n={len(df)}")
    return df


MONETARY = re.compile(
    r"(?:monetary|fomcminutes|fomcprojtabl|monetarypolicy)(20\d{6})",
    re.I,
)


def parse_fomc_html(html: str) -> list[str]:
    dates = set()
    for m in MONETARY.findall(html):
        dates.add(f"{m[:4]}-{m[4:6]}-{m[6:8]}")
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        m = MONETARY.search(a["href"])
        if m:
            raw = m.group(1)
            dates.add(f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}")
    return sorted(dates)


def download_fomc() -> pd.DataFrame:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    cal_path = DATA_RAW / "fomc" / "calendars.htm"
    cal_path.parent.mkdir(parents=True, exist_ok=True)
    r = SESSION.get(FOMC_CAL, timeout=45)
    r.raise_for_status()
    cal_path.write_text(r.text, encoding="utf-8")
    dates = set(parse_fomc_html(r.text))
    for year in range(2011, 2021):
        url = FOMC_HIST.format(year=year)
        try:
            rr = SESSION.get(url, timeout=45)
            rr.raise_for_status()
            (DATA_RAW / "fomc" / f"hist_{year}.htm").write_text(rr.text, encoding="utf-8")
            dates.update(parse_fomc_html(rr.text))
        except Exception as e:
            print(f"fomc hist {year} failed: {e}")
    df = pd.DataFrame({"fomc_date": sorted(dates)})
    df["fomc_date"] = pd.to_datetime(df["fomc_date"])
    df = df[(df["fomc_date"] >= "2011-01-01") & (df["fomc_date"] <= IS_END)]
    df.to_csv(DATA_PROC / "fomc_dates.csv", index=False)
    print(f"fomc announcement dates n={len(df)}")
    return df


def main() -> None:
    DATA_PROC.mkdir(parents=True, exist_ok=True)
    mkt = DATA_PROC / "markets.csv"
    if mkt.exists():
        px = pd.read_csv(mkt, index_col=0, parse_dates=True)
        if len(px) > 1000 and pd.to_datetime(px.index).max() <= pd.Timestamp(IS_END):
            print(f"markets cache ok {px.index.min().date()} .. {px.index.max().date()} n={len(px)}")
        else:
            download_prices()
    else:
        download_prices()
    try:
        download_fred("DGS2")
    except Exception as e:
        print(f"FRED DGS2 blocked ({e}); using Treasury H.15 2y CSV")
        download_dgs2_treasury()
    for sid in ["DFEDTARU", "DFEDTARL"]:
        try:
            download_fred(sid)
        except Exception as e:
            print(f"optional FRED {sid} skipped: {e}")
    download_fomc()


if __name__ == "__main__":
    main()
