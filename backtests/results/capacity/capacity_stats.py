"""Capacity statistics for the report (Liquidity & Capacity): no price levels in the output.

- TLT and UUP median daily dollar volume (close x shares, Yahoo daily bars) over the out-of-sample window
  2024-10-03..2026-10-02, and what the v2 E1 sleeve's largest position is as a share of it.
- ZT contracts traded per minute 14:30-16:00 ET on 2023-2026 press-conference days (Databento ohlcv-1m, volume only).

    GQH_DATA_DIR=<data cache> GQH_MARKET_DIR=<market dir> python backtests/results/capacity/capacity_stats.py
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ["GQH_DATA_DIR"])
MKT = Path(os.environ["GQH_MARKET_DIR"])
OOS = ("2024-10-03", "2026-10-02")
CAP_GROSS, W_TLT, W_UUP = 1.5, 0.75, 0.25            # v2 gross cap and E1 weights (HYPOTHESIS_v2.md)

rows = []
etf = pd.read_parquet(DATA / "etf_daily.parquet")
etf = etf[(etf.date >= OOS[0]) & (etf.date <= OOS[1])]
for tic, w in (("TLT", W_TLT), ("UUP", W_UUP)):
    d = etf[etf.ticker == tic]
    dv = (d.close * d.volume).median()
    rows.append({"item": f"{tic} median daily dollar volume, OOS window", "value": round(dv / 1e6, 1), "unit": "USD m",
                 "n_days": len(d)})
    rows.append({"item": f"{tic} largest E1 position for $10m capital as % of that median", "value":
                 round(100 * CAP_GROSS * w * 10e6 / dv, 2), "unit": "%", "n_days": len(d)})

m = pd.read_parquet(MKT / "ohlcv-1m__all_2016_2026.parquet", columns=["ts_event", "volume", "symbol"])
m["ts"] = pd.to_datetime(m.ts_event, utc=True).dt.tz_convert("America/New_York")
zt = m[m.symbol.astype(str).str.startswith("ZT") & (m.ts.dt.year >= 2023)]
hm = zt.ts.dt.hour * 60 + zt.ts.dt.minute
win = zt[(hm >= 14 * 60 + 30) & (hm < 16 * 60)]
per_min = win.groupby(win.ts.dt.floor("min")).volume.sum()
rows.append({"item": "ZT contracts per minute, 14:30-16:00 ET, 2023-2026 conference days: median", "value":
             float(per_min.median()), "unit": "contracts", "n_days": int(win.ts.dt.date.nunique())})
rows.append({"item": "ZT contracts per minute, same window: 10th percentile", "value": float(per_min.quantile(0.1)),
             "unit": "contracts", "n_days": int(win.ts.dt.date.nunique())})
out = pd.DataFrame(rows)
out.to_csv(HERE / "capacity_stats.csv", index=False)
print(out.to_string(index=False))
