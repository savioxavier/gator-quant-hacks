"""Scratch: table of the native S1/S2 runs against the engine references (official and same-cost)."""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<solo-repo>")
sys.path.insert(0, str(ROOT))
from src import engine as E  # noqa: E402

S = Path(__file__).resolve().parent
rf_all = E.load_rf("FWD")
WIN = {"IS": ("2011-09-02", "2024-10-02"), "OOS": ("2024-10-03", "2026-10-02")}


def sharpe(x, ddof):
    return float(x.mean() / x.std(ddof=ddof) * math.sqrt(252))


def agree(a, b):
    j = pd.concat([a, b], axis=1, join="inner").dropna()
    d = j.iloc[:, 0] - j.iloc[:, 1]
    return float(j.iloc[:, 0].corr(j.iloc[:, 1])), float(d.abs().mean() * 1e4)


def ref_excess(path):
    r = pd.read_csv(path, index_col=0, parse_dates=True)["ret"]
    return r - rf_all.reindex(r.index).ffill().fillna(0.0), r


rows = []
for book in ("s2", "s1"):
    off_ex, off = ref_excess(S / f"{book}_official.csv")
    for run in ("close_project", "close_guide", "close_guide_literal", "close_none", "coc_project", "coc_guide"):
        name = f"{book}_{run}"
        js = json.loads((S / f"{name}.json").read_text())
        ser = pd.read_csv(S / f"{name}.csv", index_col=0, parse_dates=True)
        ref = js["reference"]
        same_ex, same = ref_excess(S / ref["path"])
        for w, (lo, hi) in WIN.items():
            ws = js["windows"]["in_sample" if w == "IS" else "out_of_sample"]
            s = ser.loc[lo:hi]
            c_same, d_same = agree(s["excess"], same_ex.loc[lo:hi])
            c_off, d_off = agree(s["excess"], off_ex.loc[lo:hi])
            rows.append({"run": name, "win": w, "kit": ws["kit_sharpe_rf0"], "ours": ws["our_sharpe_excess"],
                         "ann": ws["ann_return"], "mdd": ws["max_drawdown"], "ref": ref["path"],
                         "ref_ours": sharpe(same_ex.loc[lo:hi], 1), "ref_kit_total": sharpe(same.loc[lo:hi], 0),
                         "corr_same": c_same, "bp_same": d_same, "corr_off": c_off, "bp_off": d_off,
                         "orders": ws["orders"], "refused": ws["refused_orders"],
                         "xcost": ws.get("extra_costs_ann", 0.0), "gross": ws["mean_gross_weight"]})
t = pd.DataFrame(rows)
pd.set_option("display.width", 250, "display.max_columns", 30)
print(t.round(4).to_string(index=False))

print("\nofficial reference Sharpe (ours, kit-on-total):")
for book in ("s2", "s1"):
    off_ex, off = ref_excess(S / f"{book}_official.csv")
    for w, (lo, hi) in WIN.items():
        print(book, w, round(sharpe(off_ex.loc[lo:hi], 1), 4), round(sharpe(off.loc[lo:hi], 0), 4),
              "ann", round(float((1 + off.loc[lo:hi]).prod() ** (252 / len(off.loc[lo:hi])) - 1), 4))

print("\nmonth-end decisions, native vs engine (max |w diff|):")
for book in ("s2", "s1"):
    eng = pd.read_csv(S / f"{book}_dec.csv", index_col=0, parse_dates=True)
    for fill in ("close", "coc"):
        nat = pd.read_csv(S / f"native_{book}_dec_{fill}.csv", index_col=0, parse_dates=True)
        e = eng.loc[nat.index[0]:]
        print(book, fill, len(nat), len(e), float((nat.reindex(e.index) - e).abs().max().max()),
              "engine nonzero before first native decision:", float(eng.loc[:nat.index[0]].iloc[:-1].abs().sum().sum()))

print("\ntiming effect (next_close vs coc, same costs, excess returns):")
for book in ("s2", "s1"):
    for cost in ("project", "guide"):
        a = pd.read_csv(S / f"{book}_close_{cost}.csv", index_col=0, parse_dates=True)["excess"]
        b = pd.read_csv(S / f"{book}_coc_{cost}.csv", index_col=0, parse_dates=True)["excess"]
        for w, (lo, hi) in WIN.items():
            c, d = agree(a.loc[lo:hi], b.loc[lo:hi])
            print(book, cost, w, "corr", round(c, 6), "mean abs diff bp", round(d, 4))
