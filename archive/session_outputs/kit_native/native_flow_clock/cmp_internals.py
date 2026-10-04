import sys, numpy as np, pandas as pd
sys.path.insert(0, "<solo-repo>")
from src import forward as F, ensemble as EN
S = sys.argv[1]
d = pd.read_csv(f"{S}/t0_dump.csv", index_col=0, parse_dates=True)
fr = F.stream_frames("F1", "FWD")
labels = list(fr["ex"].columns)
out = EN.combine(fr["ex"], fr["gr"], fr["rf"], labels, "minvar_lw", 0.08, False)
def rep(name, a, b):
    a, b = a.align(b, join="inner")
    diff = (a - b).abs()
    print(f"{name:24s} max|diff| {diff.max():.3e}  days>1e-12 {int((diff > 1e-12).sum())}  first {diff[diff > 1e-12].index[:3].strftime('%Y-%m-%d').tolist()}")
h = fr["held"]
rep("held A SPY", d["heldA_SPY"], h["A"]["SPY"]); rep("held A IEF", d["heldA_IEF"], h["A"]["IEF"]); rep("held C IEF", d["heldC_IEF"], h["C"]["IEF"])
for t in h["TSMOM"].columns:
    rep(f"w_dec TSMOM {t}", d[f"wT_{t}"], fr["w_dec"]["TSMOM"][t])
wd = fr["w_dec"]
rep("order tgt A SPY vs w_dec", d["ordA_SPY"], wd["A"]["SPY"]); rep("order tgt C vs w_dec", d["ordC_IEF"], wd["C"]["IEF"])
for s in labels:
    rep(f"ex {s}", d[f"ex_{s}"], fr["ex"][s]); rep(f"gr {s}", d[f"gr_{s}"], fr["gr"][s])
    rep(f"lam {s}", d[f"lam_{s}"], out["lam"][s])
rep("k", d["k"], out["k"])
kp = d["kproxy"].dropna(); act = (d["heldA_SPY"].abs() + d["heldC_IEF"].abs()) > 0
rep("kproxy vs k (A/C held)", kp[act.reindex(kp.index, fill_value=False)], out["k"])
rep("kproxy vs k (all)", kp, out["k"])
rep("paper net vs official", d["paper_net"].dropna(), out["net"])
off = F.returns("F1", "FWD")
rep("official vs F.returns", out["net"], off)
