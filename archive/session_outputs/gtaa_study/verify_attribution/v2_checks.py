import os, sys, math, numpy as np, pandas as pd
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ".")
from core import *
px, rf = load()
daily = pd.read_csv("out/v1_daily.csv", index_col=0, parse_dates=True)
hS = pd.read_csv("out/v1_heldS3.csv", index_col=0, parse_dates=True)
first = pd.Timestamp("2005-11-01")
eS = (daily.S3 - daily.rf).loc[first:]; eB = (daily.BH5 - daily.rf).loc[first:]
# proper single-series bootstrap SE of Sharpe
def boot_one(x, block, reps=5000, seed=2):
    rng = np.random.default_rng(seed); n = len(x); x = np.asarray(x); nb = int(np.ceil(n / block)); o = np.empty(reps)
    for k in range(reps):
        st = rng.integers(0, n, nb); ix = ((st[:, None] + np.arange(block)) % n).ravel()[:n]; o[k] = sr_np(x[ix])
    return o
for blk in (21, 63):
    print("OOS S3 bootstrap SR SE blk", blk, round(boot_one(eS.loc[OOS_START:].values, blk).std(), 3))
# change OOS-IS
for nm, e in (("S3", eS), ("BH5", eB)):
    a = sr_np(e.loc[:IS_END].values); b = sr_np(e.loc[OOS_START:].values)
    sa = math.sqrt((1 + a * a / 2) / (len(e.loc[:IS_END]) / 252)); sb = math.sqrt((1 + b * b / 2) / (len(e.loc[OOS_START:]) / 252))
    print(nm, "change %.3f SE %.3f z %.2f" % (b - a, math.hypot(sa, sb), (b - a) / math.hypot(sa, sb)))
# 2y windows in-sample
eI, bI = eS.loc[:IS_END], eB.loc[:IS_END]
wins = []
for s in range(0, len(eI) - 504 + 1, 21):
    a = eI.iloc[s:s + 504].values; b = bI.iloc[s:s + 504].values
    wins.append((sr_np(a), sr_np(b)))
W = np.array(wins); d = W[:, 0] - W[:, 1]
print("2y windows n=%d S3>BH5 %.2f S3>=0.70 %.2f diff p5 %.2f p95 %.2f pct of -0.117 %.2f" % (len(W), (d > 0).mean(), (W[:, 0] >= 0.70).mean(), *np.percentile(d, [5, 95]), (d <= -0.117).mean()))
# vol regime: SPY in/out days IS
spy = px["close"]["SPY"].pct_change()
for t in TK:
    r = (px["close"][t].pct_change() - rf).loc[first:IS_END]
    held = hS[t].loc[first:IS_END]
    elig = r.notna() & (held.index >= {"DBC": pd.Timestamp("2006-12-01")}.get(t, first))
    # use eligibility from BH5: held_BH5 > 0 ; approximate with data available + warmup handled via v1 file not saved, recompute
    pass
dB = decisions(px["close"], bh=True); hB = dB.shift(1).fillna(0.0)
for t in TK:
    r = (px["close"][t].pct_change() - rf).loc[first:IS_END]
    el = hB[t].loc[first:IS_END] > 0
    out = (hS[t].loc[first:IS_END] == 0) & el; inn = (hS[t].loc[first:IS_END] > 0) & el
    rr = r[el]; m = rr.mean()
    share = ((r[out] - m) ** 2).sum() / ((rr - m) ** 2).sum()
    tv = r.rolling(63).std().shift(1) * math.sqrt(252)
    print(t, "out frac %.2f var share %.2f mean ex in %.3f out %.3f | trailing vol in %.2f out %.2f" % (out.sum() / el.sum(), share, r[inn].mean() * 252, r[out].mean() * 252, tv[inn].mean(), tv[out].mean()))
# OOS SPY whipsaw fills
for dte in ["2025-04-01", "2025-06-02", "2026-04-01", "2026-05-01"]:
    print("SPY open", dte, round(px["open"]["SPY"].loc[dte], 2), "held", hS["SPY"].loc[dte])
print(hS.loc["2025-03-25":"2025-06-05"].drop_duplicates())
print(hS.loc["2026-02-20":"2026-06-05"].drop_duplicates())
# lookback robustness IS (window from 2006-01-03 common)
for n in (6, 8, 10, 12):
    d_ = decisions(px["close"], n=n); nn, *_ = sim_formula(d_, px, rf)
    e = (nn - rf)
    print("lookback", n, "IS SR %.3f OOS SR %.3f" % (sharpe(e.loc["2006-01-03":IS_END]), sharpe(e.loc[OOS_START:])))
print("BH5 2006-01-03 IS SR %.3f" % sharpe(eB.loc["2006-01-03":IS_END]))
