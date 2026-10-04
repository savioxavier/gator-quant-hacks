"""Scratch: compare perturbed runs with the baseline up to each cut; check fill timing in the baseline."""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

V = Path(__file__).resolve().parent
tag = sys.argv[1] if len(sys.argv) > 1 else "la"
cuts = sys.argv[2:] or ["2013-05-31", "2015-06-29", "2020-03-16", "2022-12-30", "2025-04-30"]


def load(c):
    log = pickle.load(open(V / f"{tag}_{c}_log.pkl", "rb"))
    dec = pd.read_csv(V / f"{tag}_{c}_dec.csv", index_col=0, parse_dates=True)
    ser = pd.read_csv(V / f"{tag}_{c}.csv", index_col=0, parse_dates=True)
    return log, dec, ser


b_log, b_dec, b_ser = load("none")
bo = pd.DataFrame(b_log["orders"], columns=["date", "name", "delta", "exec"])
bf = pd.DataFrame([f for f in b_log["fills"] if "refused" not in f])
print("baseline refused/canceled:", sum("refused" in f for f in b_log["fills"]))
for c in cuts:
    log, dec, ser = load(c)
    o = pd.DataFrame(log["orders"], columns=["date", "name", "delta", "exec"])
    f = pd.DataFrame([x for x in log["fills"] if "refused" not in x])
    a1, a2 = bo[bo.date <= c].reset_index(drop=True), o[o.date <= c].reset_index(drop=True)
    same_orders = a1.equals(a2)
    f1 = bf[bf.executed <= c].reset_index(drop=True)
    f2 = f[f.executed <= c].reset_index(drop=True)
    same_fills = f1.equals(f2)
    d1, d2 = b_dec.loc[:c], dec.loc[:c]
    ddiff = float((d1 - d2.reindex(d1.index)).abs().to_numpy().max()) if len(d1) else 0.0
    later = (b_dec.loc[c:].iloc[1:] - dec.loc[c:].iloc[1:]).abs().to_numpy().max()
    r1, r2 = b_ser.loc[:c, "ret"], ser.loc[:c, "ret"]
    rdiff = float((r1 - r2).abs().max())
    print(f"cut {c}: orders<=cut {len(a1)} identical={same_orders}; fills<=cut {len(f1)} identical={same_fills}; "
          f"decisions<=cut {len(d1)} max diff {ddiff}; returns<=cut max diff {rdiff}; later decision diff {later:.3f}; "
          f"refused {sum('refused' in x for x in log['fills'])}")

# fill timing in the baseline
bf["created"] = pd.to_datetime(bf["created"])
bf["executed"] = pd.to_datetime(bf["executed"])
cal = pd.DatetimeIndex(sorted(set(pd.to_datetime(b_ser.index))))
pos = {d: i for i, d in enumerate(cal)}
lag = bf["executed"].map(pos) - bf["created"].map(pos)
print("exectypes:", bf["exectype"].value_counts().to_dict())
print("session lag created->executed:", lag.value_counts().to_dict())
print("max |price - bar close| / close:", float(((bf["price"] - bf["bar_close"]).abs() / bf["bar_close"]).max()))
