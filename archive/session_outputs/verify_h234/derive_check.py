"""Can a committed file's return plus tick move give back the price level? (entry = ticks * tick_pts / ret)"""
import glob
import os
import subprocess

import numpy as np
import pandas as pd

MKT = "<home>/.cache/gqh/presser/ohlcv-1m__all_2016_2026.parquet"
b = pd.read_parquet(MKT, columns=["open", "close"])
LV = np.array(sorted(set(np.round(b.open, 9)) | set(np.round(b.close, 9))))
root = "../team_push/"


def recon(ticks, ret, tick):
    m = ticks.notna() & (ticks != 0) & ret.notna() & (ret != 0)
    tk = tick[m] if hasattr(tick, "__len__") else tick
    e = ticks[m] * tk / ret[m]
    sn = np.round(e / tk) * tk
    return dict(rows=int(m.sum()), on_tick_grid=int((np.abs(e - sn) < 1e-6 * np.abs(e)).sum()),
                equal_to_a_1m_bar_level=int(np.isin(np.round(sn, 9), LV).sum()))


for fn in ["backtests/results/presser_h1/h1primary_trades.csv", "backtests/results/presser_h1/benchr_trades.csv"]:
    if os.path.exists(root + fn):
        df = pd.read_csv(root + fn, low_memory=False)
        print(fn, recon(df.move_ticks, df.ret, df.tick_pts))
ev = pd.read_csv(root + "backtests/presser/events/events.csv")
for s in ["zt", "zf", "zn", "es"]:
    tick = ev["zt_tick_pts"] if s == "zt" else {"zf": 1 / 128, "zn": 1 / 64, "es": 0.25}[s]
    print("events.csv", s, "1350-1420", recon(ev[f"{s}_ticks_1350_1420"], ev[f"{s}_r_1350_1420"], tick))
files = subprocess.run(["git", "-C", root, "ls-files", "-co", "--exclude-standard"], capture_output=True,
                       text=True).stdout.split()
for f in files:
    if f.endswith(".csv"):
        h = open(root + f, encoding="utf-8", errors="replace").readline().strip().split(",")
        if ("ret" in h and "move_ticks" in h) or any(x.endswith("_r_1350_1420") for x in h):
            tracked = subprocess.run(["git", "-C", root, "ls-files", "--error-unmatch", f], capture_output=True).returncode == 0
            print("return + tick move in:", f, "(tracked)" if tracked else "(untracked)")

# stricter: the reconstructed entry equals the open of the 1m bar at the row's own entry_ts and symbol
bb = pd.read_parquet(MKT, columns=["ts_event", "open", "symbol"])
bb["sym"] = bb.symbol.str[:2]
key = dict(zip(zip(bb.sym, bb.ts_event.dt.as_unit("ns").astype("int64")), bb.open))
df = pd.read_csv(root + "backtests/results/presser_h1/h1primary_trades.csv", low_memory=False)
m = (df.move_ticks != 0) & df.ret.notna() & (df.ret != 0)
d = df[m].copy()
e = d.move_ticks * d.tick_pts / d.ret
d["recon"] = np.round(e / d.tick_pts) * d.tick_pts
ts = pd.to_datetime(d.entry_ts, utc=True, format="ISO8601").dt.as_unit("ns").astype("int64")
act = np.array([key.get((s, t), np.nan) for s, t in zip(d.sym, ts)])
print("h1primary_trades: reconstructed entry == open of own entry bar:", int(np.isclose(d.recon, act, rtol=0, atol=1e-9).sum()), "of", len(d))
