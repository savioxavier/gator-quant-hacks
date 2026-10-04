"""Build a SYNTHETIC data dir: real cache copied (read-only source) + ~70 synthetic NYSE sessions.

Futures are NOT written here: they are produced by data/download_databento.py itself, run in this
fresh dir with a fake `databento` client (fake_databento.py) that serves the real raw bars plus a
synthetic extension. This script writes the synthetic raw extension to synth_raw/ for that client.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path("<home>/.cache/gqh")
OUT = Path(sys.argv[1])
RAWX = Path(sys.argv[2])          # synthetic raw extension for the fake Databento client
OUT.mkdir(parents=True, exist_ok=True)
RAWX.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(20261003)

HOL = pd.DatetimeIndex(["2026-11-26", "2026-12-25", "2027-01-01"])
SESS = pd.bdate_range("2026-10-05", "2027-01-12")
SESS = SESS[~SESS.isin(HOL)]
WEEKDAYS = pd.bdate_range("2026-10-05", "2027-01-12")      # FRED-style rows (holidays included)
print("synthetic sessions:", len(SESS), SESS[0].date(), "..", SESS[-1].date())


def extend_ohlcv(df: pd.DataFrame, dates: pd.DatetimeIndex, vol_default=0.01) -> pd.DataFrame:
    rows = []
    for tk, g in df.groupby("ticker"):
        g = g.sort_values("date")
        if g["date"].max() < pd.Timestamp("2026-09-01"):
            continue                                   # dead ticker: nothing to continue
        c = float(g["close"].iloc[-1])
        lr = np.log(g["close"]).diff().tail(252)
        sig = float(lr.std()) if lr.notna().sum() > 50 else vol_default
        sig = min(max(sig, 0.002), 0.05)
        v0 = float(g["volume"].iloc[-1]) if "volume" in g else 0.0
        for d in dates:
            gap = rng.normal(0, sig * 0.4)
            intr = rng.normal(0, sig * 0.9)
            o = c * np.exp(gap)
            cl = o * np.exp(intr)
            hi = max(o, cl) * (1 + abs(rng.normal(0, sig * 0.3)))
            lo = min(o, cl) * (1 - abs(rng.normal(0, sig * 0.3)))
            rows.append({"date": d, "ticker": tk, "open": o, "high": hi, "low": lo, "close": cl,
                         "volume": v0 * float(np.exp(rng.normal(0, 0.2)))})
            c = cl
    ext = pd.DataFrame(rows)
    out = pd.concat([df, ext.astype({c: df[c].dtype for c in ext.columns if c in df.columns})], ignore_index=True)
    return out.sort_values(["ticker", "date"]).reset_index(drop=True)


# ---------------- ETFs, indices, local indices
for f in ("etf_daily", "index_daily", "local_indices"):
    df = pd.read_parquet(SRC / f"{f}.parquet")
    out = extend_ohlcv(df, SESS)
    out = out[df.columns]
    out.to_parquet(OUT / f"{f}.parquet", index=False)
    print(f, df["date"].max().date(), "->", out["date"].max().date(), len(df), "->", len(out))

# ---------------- rf and FRED (weekday rows, last value carried; FRED publishes holidays as NaN)
fred = pd.read_parquet(SRC / "fred_daily.parquet")
last = fred.drop(columns="date").ffill().iloc[-1]
ext = pd.DataFrame({"date": WEEKDAYS})
for c in last.index:
    walk = last[c] + np.cumsum(rng.normal(0, 0.01, len(WEEKDAYS)))
    ext[c] = np.where(WEEKDAYS.isin(HOL), np.nan, np.round(walk, 2))
ext["date"] = ext["date"].astype(fred["date"].dtype)
fred2 = pd.concat([fred, ext], ignore_index=True)
fred2.to_parquet(OUT / "fred_daily.parquet", index=False)
rf = pd.read_parquet(SRC / "rf_daily.parquet")
rf_ext = (fred2.set_index("date")["DTB3"].ffill() / 100 / 252).loc[WEEKDAYS[0]:].rename("rf").reset_index()
rf2 = pd.concat([rf, rf_ext.astype(rf.dtypes.to_dict())], ignore_index=True)
rf2.to_parquet(OUT / "rf_daily.parquet", index=False)
print("rf", rf["date"].max().date(), "->", rf2["date"].max().date())

# ---------------- French factors: unchanged (the library lags ~1-2 months)
shutil.copy2(SRC / "ff_daily.parquet", OUT / "ff_daily.parquet")

# ---------------- Treasury auctions: real file + the year-ago calendar shifted 52 weeks, with yields
# moved by the change of the nominal curve (keeps the TIPS/nominal gap of every row unchanged)
au = pd.read_parquet(SRC / "treasury_auctions.parquet")
last_real = au["auction_date"].max()
src = au[(au["auction_date"] + pd.Timedelta(days=364) > last_real) &
         (au["auction_date"] + pd.Timedelta(days=364) <= pd.Timestamp("2027-01-12"))].copy()
fr = fred.set_index("date")[["DGS2", "DGS10", "DGS30"]].ffill()
now_curve = fr.iloc[-1].to_numpy()
def curve_at(d):
    return fr.loc[:d].iloc[-1].to_numpy()
new = src.copy()
for c in ("record_date", "auction_date", "issue_date", "maturity_date", "announcemt_date"):
    new[c] = new[c] + pd.Timedelta(days=364)
mat = (src["maturity_date"] - src["auction_date"]).dt.days.to_numpy() / 365.25
dy = [np.interp(m, [2, 10, 30], now_curve) - np.interp(m, [2, 10, 30], curve_at(d))
      for m, d in zip(mat, src["auction_date"])]
new["high_yield"] = src["high_yield"].to_numpy() + np.array(dy)
new["cusip"] = [f"SYN{i:06d}" for i in range(len(new))]
for c in ("total_accepted", "bid_to_cover_ratio", "primary_dealer_accepted", "direct_bidder_accepted",
          "indirect_bidder_accepted"):
    new[c] = np.nan
au2 = pd.concat([au, new], ignore_index=True)
au2.to_parquet(OUT / "treasury_auctions.parquet", index=False)
print("auctions", len(au), "->", len(au2), "last auction", au2["auction_date"].max().date())

# ---------------- synthetic raw Databento extension (UTC-day bars incl. Sunday evening; hourly ES/ZN)
RAW = SRC / "databento_raw"
roll_day = {}
days_utc = pd.date_range("2026-10-04", "2027-01-12", freq="D")          # Sunday 10-04 onwards
days_utc = days_utc[~days_utc.isin(HOL)]
days_utc = days_utc[days_utc.dayofweek != 5]                          # no Saturday bars
daily_ext = []
for p in sorted(RAW.glob("glbx_ohlcv1d_v01__*__2010.parquet")):
    root = p.name.split("__")[1]
    g = pd.read_parquet(p)
    g = g.sort_values("ts_event")
    r0 = g[g["symbol"] == f"{root}.v.0"].iloc[-1]
    r1 = g[g["symbol"] == f"{root}.v.1"].iloc[-1]
    print(" ", root, "last v0", r0["ts_event"].date(), "last v1", r1["ts_event"].date())
    sig = float(np.log(g[g["symbol"] == f"{root}.v.0"]["close"]).diff().tail(252).std())
    sig = min(max(sig, 0.002), 0.04)
    ids = [int(r0["instrument_id"]), int(r1["instrument_id"])]
    px = [float(r0["close"]), float(r1["close"])]
    vol = [int(r0["volume"]), int(r1["volume"])]
    rd = pd.Timestamp("2026-12-14") if root in {"ES", "NQ", "RTY", "YM", "6E", "6J", "6B", "6A", "6C", "6S",
                                                 "ZT", "ZF", "ZN", "ZB", "UB"} else pd.Timestamp("2026-11-17")
    roll_day[root] = rd
    newid = 90_000_000 + len(roll_day)
    for d in days_utc:
        r = rng.normal(0, sig) if d.dayofweek != 6 else rng.normal(0, sig * 0.1)
        px = [x * (1 + r + rng.normal(0, sig * 0.05)) for x in px]
        if d == rd:                                   # roll: old second becomes front, a new second appears
            ids = [ids[1], newid]
            px = [px[1], px[1] * 1.002]
            vol = [vol[0], max(vol[1], 1)]
        for k in (0, 1):
            c = px[k]
            daily_ext.append({"ts_event": d.tz_localize("UTC"), "rtype": 35, "publisher_id": 1,
                              "instrument_id": ids[k], "open": c, "high": c * 1.003, "low": c * 0.997,
                              "close": c, "volume": int(vol[k] * float(np.exp(rng.normal(0, 0.2)))),
                              "symbol": f"{root}.v.{k}"})
dx = pd.DataFrame(daily_ext)
dx.to_parquet(RAWX / "daily_ext.parquet", index=False)
# hourly ES/ZN: bars 13:00..21:00 UTC each NYSE session, close = that day's daily close with noise
hx = []
for root in ("ES", "ZN"):
    d0 = dx[dx["symbol"].str.startswith(root + ".")]
    for _, row in d0.iterrows():
        d = row["ts_event"].tz_convert(None)
        if d.dayofweek >= 5:
            continue
        for h in range(13, 22):
            c = row["close"] * (1 + rng.normal(0, 0.0005))
            hx.append({"ts_event": (d + pd.Timedelta(hours=h)).tz_localize("UTC"), "rtype": 34, "publisher_id": 1,
                       "instrument_id": row["instrument_id"], "open": c, "high": c, "low": c, "close": c,
                       "volume": 1000, "symbol": row["symbol"]})
pd.DataFrame(hx).to_parquet(RAWX / "hourly_ext.parquet", index=False)
pd.Series({k: str(v.date()) for k, v in roll_day.items()}).to_json(RAWX / "roll_days.json")
print("raw ext:", len(dx), "daily rows,", len(hx), "hourly rows")
