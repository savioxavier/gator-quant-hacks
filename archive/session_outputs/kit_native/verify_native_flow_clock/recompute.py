"""Recompute the agreement and Sharpe figures from the run series and freshly built engine references."""
import json
import math
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "<solo-repo>")
from src import engine as E, ensemble as EN, forward as F  # noqa: E402

FIN = "<scratch>/kit_native/native_flow_clock/final/"
OUT = "<scratch>/kit_native/verify_native_flow_clock/"
W = {"IS": ("2006-05-08", "2024-10-02"), "OOS": ("2024-10-03", "2026-10-02")}

official = F.returns("F1", "FWD")
rf = E.load_rf("FWD").reindex(official.index).ffill().fillna(0.0)
fr = F.stream_frames("F1", "FWD")
labels = list(fr["ex"].columns)
co = EN.combine(fr["ex"], fr["gr"], fr["rf"], labels, "minvar_lw", 0.08, False)
scale = co["lam"][labels].mul(co["k"], axis=0).reindex(official.index)
G = fr["gr"][labels].reindex(official.index)
turn = (scale.diff().fillna(scale)).abs() * np.minimum(G, G.shift(1).fillna(0.0))
zero, guide = rf.copy(), rf.copy()
for s in labels:
    w = fr["w_dec"][s]
    ohlc = E.load_ohlc(list(w.columns), "FWD")
    _, g0, *_ = E.simulate(w, ohlc, fr["rf"], exec=fr["exec"][s])
    g10, *_ = E.simulate(w, ohlc, fr["rf"], exec=fr["exec"][s], cost_bps={t: 10.0 for t in w.columns})
    zero += scale[s] * (g0.reindex(official.index) - rf)
    guide += scale[s] * (g10.reindex(official.index) - rf)
guide -= turn.sum(axis=1) * 10 / 1e4
refs = {"official": official, "zero_cost": zero, "guide_cost": guide}
for k, s in refs.items():
    b = pd.read_csv(FIN + f"ref_{k}.csv", index_col=0, parse_dates=True).iloc[:, 0]
    print(f"ref {k}: max abs diff vs builder file {float((s - b).abs().max()):.3e}")


def kit(r):
    return r.mean() / r.std(ddof=0) * math.sqrt(252)


def ours(x):
    return x.mean() / x.std(ddof=1) * math.sqrt(252)


res = {}
for k, s in refs.items():
    res["ref_" + k] = {w: {"kit": kit(s.loc[a:b]), "ours": ours((s - rf).loc[a:b])} for w, (a, b) in W.items()}
for run, ref in [("native_project", "official"), ("native_guide", "guide_cost"), ("native_none", "zero_cost"),
                 ("coc_project", "official"), ("native_guide", "official"), ("native_guide_literal", "guide_cost")]:
    d = pd.read_csv(FIN + f"{run}.csv", index_col=0, parse_dates=True)
    ex = d["ret"] - d["net_weight"] * d["rf"]
    assert float((ex - d["excess"]).abs().max()) < 1e-15
    rex = refs[ref] - rf
    row = {}
    for w, (a, b) in W.items():
        x, y = ex.loc[a:b], rex.loc[a:b].reindex(ex.loc[a:b].index)
        row[w] = {"kit": kit(d["ret"].loc[a:b]), "ours": ours(x), "corr": float(x.corr(y)),
                  "mad_bp": float((x - y).abs().mean() * 1e4), "ann": float((1 + d["ret"].loc[a:b]).prod() ** (252 / len(x)) - 1)}
    res[f"{run} vs {ref}"] = row
for k, v in res.items():
    print(k, json.dumps({w: {m: round(z, 5) for m, z in q.items()} for w, q in v.items()}))
json.dump(res, open(OUT + "recomputed.json", "w"), indent=1)
