import os, sys, math, json, itertools
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vlib as V
from src import engine as E
from src import forward2 as F2
OUT = os.path.dirname(os.path.abspath(__file__))
assert os.path.exists(os.path.join(OUT, "v_is_table.csv"))
done = json.load(open(os.path.join(OUT, "v_is_done.json")))
start = pd.Timestamp(done["start_decision"])
ohlc = E.load_ohlc(V.TICK, "FWD"); rf = E.load_rf("FWD")
close = ohlc["close"]; cal = close.index
print("FWD data end", cal[-1].date())
me = V.complete_month_ends(cal, cal[-1]); print("last ME", me[-1].date())
rfd = rf.reindex(cal).ffill().fillna(0.0)
grid = list(itertools.product(V.SIGS, V.UNI, V.WTS, V.ROFF))
X = {}; Xis = pd.read_parquet(os.path.join(OUT, "v_is_excess.parquet"))
for k, timed in [(k, True) for k in grid] + [(("SMA10", u, w, "tbill"), False) for u in V.UNI for w in V.WTS]:
    name = "|".join(k) if timed else f"BH|{k[1]}|{k[2]}"
    if not timed and name in X: continue
    W, _ = V.build_decisions(k, close, rf, me, start, timed)
    net, *_ = E.simulate(W, ohlc, rf, exec="next_open")
    ex = net - rfd
    # full-data run must reproduce IS exactly (point-in-time)
    a = ex.loc[Xis.index]; assert float((a - Xis[name]).abs().max()) < 1e-12, name
    X[name] = ex.loc["2024-10-03":"2026-10-02"]
X = pd.DataFrame(X)
print("later window", X.index[0].date(), X.index[-1].date(), len(X) / 252, "years")
tab = pd.read_csv(os.path.join(OUT, "v_is_table.csv"), index_col=0)
timed = [c for c in X.columns if not c.startswith("BH|")]
unt = {c: "BH|%s|%s" % tuple(c.split("|")[1:3]) for c in timed}
SR = X.mean() / X.std() * math.sqrt(252)
g = pd.Series({c: SR[c] - SR[unt[c]] for c in timed})
s3 = "SMA10|frozen5|equal|tbill"
print("later median %.3f IQR %.3f-%.3f range %.3f..%.3f" % (SR[timed].median(), SR[timed].quantile(.25), SR[timed].quantile(.75), SR[timed].min(), SR[timed].max()))
print("later timing gain median %.3f beats %d/72" % (g.median(), (g > 0).sum()))
isr = tab.loc[timed, "sharpe"]
print("Spearman IS vs later %.3f Kendall %.3f" % (stats.spearmanr(isr, SR[timed])[0], stats.kendalltau(isr, SR[timed])[0]))
gis = tab.loc[timed, "d_untimed"]; print("Spearman gains %.3f" % stats.spearmanr(gis, g)[0])
best = isr.idxmax(); rk = SR[timed].rank(ascending=False)
print("IS best", best, "later %.4f rank %d" % (SR[best], rk[best]))
print("S3 later %.4f rank %d; BH5 later %.4f" % (SR[s3], rk[s3], SR["BH|frozen5|equal"]))
f2s3 = F2.returns("S3", "FWD").loc["2024-10-03":]; f2bh = F2.returns("BH5", "FWD").loc["2024-10-03":]
print("forward2 S3 later %.4f BH5 %.4f" % (V.sharpe(f2s3 - rfd.loc[f2s3.index]), V.sharpe(f2bh - rfd.loc[f2bh.index])))
top7 = isr.sort_values(ascending=False).index[:7]; bot7 = isr.sort_values().index[:7]
print("IS top7 later median %.3f, bottom7 %.3f" % (SR[top7].median(), SR[bot7].median()))
# bootstrap: Spearman CI and S3-BH5, grid mean gain
bs = pd.DataFrame(V.boot_sharpes(X.to_numpy(), L=21, B=1000, seed=3), columns=X.columns)
sp = [stats.spearmanr(isr, bs.loc[i, timed])[0] for i in range(len(bs))]
print("Spearman 90%% CI [%.2f, %.2f]" % tuple(np.quantile(sp, [.05, .95])))
d = bs[s3] - bs["BH|frozen5|equal"]; print("S3-BH5 later %.3f CI21 [%.3f,%.3f]" % (SR[s3] - SR["BH|frozen5|equal"], d.quantile(.05), d.quantile(.95)))
gm = pd.DataFrame({c: bs[c] - bs[unt[c]] for c in timed}).mean(axis=1); print("grid-mean gain CI21 [%.3f,%.3f]" % (gm.quantile(.05), gm.quantile(.95)))
bs63 = pd.DataFrame(V.boot_sharpes(X.to_numpy(), L=63, B=1000, seed=4), columns=X.columns)
d = bs63[s3] - bs63["BH|frozen5|equal"]; print("S3-BH5 CI63 [%.3f,%.3f]" % (d.quantile(.05), d.quantile(.95)))
print("family later medians:")
fam = pd.DataFrame({"is": isr, "later": SR[timed], "g": g})
fam["uni"] = [c.split("|")[1] for c in fam.index]; fam["wt"] = [c.split("|")[2] for c in fam.index]; fam["sig"] = [c.split("|")[0] for c in fam.index]
print(fam.groupby(["uni", "wt"])[["is", "later"]].median().round(3))
print(fam.groupby("sig")[["g"]].median().round(3))
print("untimed later:", SR[[c for c in X.columns if c.startswith("BH|")]].round(3).to_dict())
fam.to_csv(os.path.join(OUT, "v_fwd_table.csv"))
