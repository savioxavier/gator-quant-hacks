import os, sys, math, numpy as np, pandas as pd
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ".")
from core import *
px, rf = load()
hS = pd.read_csv("out/v1_heldS3.csv", index_col=0, parse_dates=True)
hB = decisions(px["close"], bh=True).shift(1).fillna(0.0)
op = px["open"]
rows = []
for t in TK:
    h = (hS[t] > 0).astype(int); el = hB[t] > 0
    chg = h.diff()
    exits = chg.index[(chg == -1) & el & el.shift(1, fill_value=False)]
    entries = chg.index[(chg == 1) & el]
    for x in exits:
        nxt = entries[entries > x]
        re = nxt[0] if len(nxt) else None
        ws = re is not None and (re - x).days <= 62 and op.loc[re, t] > op.loc[x, t]
        rows.append(dict(t=t, exit=x, reentry=re, whipsaw=ws, per="OOS" if x >= OOS_START else "IS"))
S = pd.DataFrame(rows)
print(S.groupby("per").agg(n=("whipsaw", "size"), whip=("whipsaw", "sum")))
print(S[S.t == "SPY"].groupby("per").whipsaw.agg(["size", "sum"]))
# t-stat of in vs out mean excess per ETF IS (Welch, daily)
first = pd.Timestamp("2005-11-01")
from scipy import stats
for t in TK:
    r = (px["close"][t].pct_change() - rf).loc[first:IS_END]; el = hB[t].loc[first:IS_END] > 0
    o = r[(hS[t].loc[first:IS_END] == 0) & el].dropna(); i = r[(hS[t].loc[first:IS_END] > 0) & el].dropna()
    print(t, "in-out mean diff %.3f/yr welch t %.2f" % ((i.mean() - o.mean()) * 252, stats.ttest_ind(i, o, equal_var=False).statistic))
# --- futures GTAA-3 check (pre-specified single variant): 1/3 ES, 1/3 ZN, 1/3 equal-weight commodity basket, each
# long/flat on its own 10-month SMA of month-end index levels, next-close fills, 1.5 bp ES/ZN, 5 bp commodities
fu = pd.read_parquet("<home>/.cache/gqh/futures_daily.parquet")
cal = px["close"].index
C = fu.pivot(index="date", columns="ticker", values="close").reindex(cal)
com = ["F_" + r for r in ["CL", "HO", "RB", "NG", "GC", "SI", "PL", "HG", "ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE"]]
rc = C.pct_change(fill_method=None)
bask = rc[com].mean(axis=1, skipna=True)
lv = pd.DataFrame({"ES": C["F_ES"], "ZN": C["F_ZN"]})
lv["COM"] = (1 + bask.fillna(0)).cumprod().where(C[com].notna().any(axis=1))
r3 = lv.pct_change(fill_method=None)
lv = lv.loc[lv.dropna().index[0]:]; r3 = r3.loc[lv.index]
me = month_ends(lv.index)
sma = lv.loc[me].rolling(10).mean()
sig = (lv.loc[me] > sma).astype(float).where(sma.notna())
for nm, dec in (("timed", sig), ("untimed", sig.notna().astype(float).where(sma.notna()))):
    w = dec.reindex(lv.index).ffill() / 3
    held = w.shift(2)                       # decided close d, traded close d+1, earns from d+2
    tr = held.diff().abs().fillna(0)
    cost = tr["ES"] * 1.5e-4 + tr["ZN"] * 1.5e-4 + tr["COM"] * 5e-4
    rfx = rf.reindex(lv.index).fillna(0)
    ex = (held * r3.sub(rfx, axis=0)).sum(axis=1, min_count=1) - cost
    ex = ex[held.notna().all(axis=1)]
    for p, s in (("IS 2011-09..2024-10", ex.loc["2011-09-01":IS_END]), ("OOS (descriptive)", ex.loc[OOS_START:])):
        print("futures GTAA-3", nm, p, "SR %.3f ann ex %.4f vol %.3f mdd %.3f n %d" % (sharpe(s), s.mean() * 252, s.std() * math.sqrt(252), mdd(s + rfx.reindex(s.index)), len(s)))
    globals()[nm] = ex
a = timed.loc["2011-09-01":IS_END]; b = untimed.loc[a.index]
bs = block_boot(a.values, b.values, sr_np, 63, 3000)
print("futures GTAA-3 IS timed-untimed SR diff %.3f CI %s" % (sr_np(a.values) - sr_np(b.values), np.percentile(bs, [2.5, 97.5]).round(3)))
print("first full date", timed.index[0].date())
