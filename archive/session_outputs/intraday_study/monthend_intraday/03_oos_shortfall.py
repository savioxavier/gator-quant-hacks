"""Sleeve C later-window (2024-10..2026-09) shortfall against in-sample, by hour block / day part / offset.

Descriptive only: z = (later mean - IS mean) / sqrt(SE_later^2 + SE_IS^2), SE = mean / NW t (from
window_block_decomposition.csv written by 02_monthend_intraday.py). Output: oos_diag_C_shortfall.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
d = pd.read_csv(HERE / "window_block_decomposition.csv")
c = d[(d["sleeve"] == "C") & d["dimension"].isin(["block", "part", "off", "total"])].copy()
c["se"] = (c["mean_bp_per_window"] / c["t_nw"]).abs()
rows = []
for (dim, lvl), g in c.groupby(["dimension", "level"]):
    g = g.set_index("sample")
    for ref in ("IS", "IS_post_pub"):
        if ref not in g.index or "later" not in g.index:
            continue
        diff = g.loc["later", "mean_bp_per_window"] - g.loc[ref, "mean_bp_per_window"]
        se = float(np.hypot(g.loc["later", "se"], g.loc[ref, "se"]))
        rows.append({"dimension": dim, "level": lvl, "reference": ref,
                     "ref_mean_bp": g.loc[ref, "mean_bp_per_window"], "later_mean_bp": g.loc["later", "mean_bp_per_window"],
                     "later_minus_ref_bp": diff, "se_bp": se, "z": diff / se})
out = pd.DataFrame(rows)
out.to_csv(HERE / "oos_diag_C_shortfall.csv", index=False)
pd.set_option("display.width", 200)
print(out.round(2).to_string(index=False))
