"""Orders, positions and internals up to each cut must not change when prices / side data after the cut do."""
import glob
import os
import sys

import numpy as np
import pandas as pd

V = "<scratch>/kit_native/verify_native_flow_clock/runs/"


def load(name):
    o = pd.read_csv(V + f"{name}_orders.csv", parse_dates=["created", "exec_dt"])
    b = pd.read_csv(V + f"{name}_book.csv", parse_dates=["date"]).set_index("date")
    d = pd.read_csv(V + f"{name}_dump.csv", parse_dates=["date"]).set_index("date")
    return o, b, d


bases = {"project": load("base_project")}
if os.path.exists(V + "base_guide_meta.json"):
    bases["guide"] = load("base_guide")
for f in sorted(glob.glob(V + "cut*_meta.json")):
    name = os.path.basename(f)[:-10]
    cut = pd.Timestamp(name.split("_")[1])
    o0, b0, d0 = bases["guide" if name.startswith("cutg") else "project"]
    o1, b1, d1 = load(name)
    key = ["created", "sym", "exectype", "size"]
    a = o0[o0.created <= cut][key].sort_values(key).reset_index(drop=True)
    b = o1[o1.created <= cut][key].sort_values(key).reset_index(drop=True)
    same_orders = a.equals(b)
    pa, pb = b0.loc[:cut], b1.loc[:cut]
    pos_cols = [c for c in b0 if c.startswith("pos_") or c == "value"]
    pos_diff = float((pa[pos_cols] - pb[pos_cols]).abs().to_numpy().max())
    da, db = d0.loc[:cut], d1.loc[:cut]
    num = da.select_dtypes("number").columns
    dd = (da[num].fillna(-9e99) - db[num].fillna(-9e99)).abs()
    dump_diff = float(dd.to_numpy().max())
    worst = dd.max().idxmax() if dump_diff else ""
    # after the cut the perturbation must bite (sanity)
    after = int((o0[o0.created > cut][key].shape[0] != o1[o1.created > cut][key].shape[0]) or
                not o0[o0.created > cut][key].reset_index(drop=True).head(200).equals(
                    o1[o1.created > cut][key].reset_index(drop=True).head(200)))
    print(f"{name}: orders<=cut {len(a)} identical={same_orders}  positions/NAV<=cut max diff {pos_diff:.3g}  "
          f"internals<=cut max diff {dump_diff:.3g} {worst}  changed after cut={bool(after)}")
