import os, sys, math, json, itertools, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vlib as V
from src import engine as E, config as C
from src import forward2 as F2
OUT = os.path.dirname(os.path.abspath(__file__))
t0 = time.time()
ohlc = E.load_ohlc(V.TICK, "IS"); rf = E.load_rf("IS")
close = ohlc["close"]; cal = close.index
assert cal[-1] == pd.Timestamp("2024-10-02")
me = V.complete_month_ends(cal, cal[-1])
print("last month-end", me[-1].date())
rfd = rf.reindex(cal).ffill().fillna(0.0)

grid = list(itertools.product(V.SIGS, V.UNI, V.WTS, V.ROFF))
bench = [("BH", u, w, "tbill") for u in V.UNI for w in V.WTS]
fv = {k: V.first_valid(k, close, rf, me) for k in grid}
for b in bench:
    fv[b] = V.first_valid(("SMA10",) + b[1:], close, rf, me, timed=False)
start = max(fv.values())
print("common first decision", start.date(), [k for k, v in fv.items() if v == start][:3])
first_ret = cal[cal.get_loc(start) + 1]

def own_sim(W, ohlc, rf):
    """My own next-open simulator: decision at close d -> target at open d+1, daily rebalanced."""
    tk = list(W.columns)
    c = ohlc["close"][tk].ffill(limit=5); o = ohlc["open"][tk].ffill(limit=5)
    cb = np.array([C.cost_bps(t) for t in tk]) / 1e4
    wn = W.shift(1).fillna(0.0).to_numpy(); wo = W.shift(2).fillna(0.0).to_numpy()
    rco = (o / c.shift(1) - 1).fillna(0.0).to_numpy(); roc = (c / o - 1).fillna(0.0).to_numpy()
    on = (wo * rco).sum(1)
    risky = on + (1 + on) * (wn * roc).sum(1)
    drift = wo * (1 + rco) / np.where(1 + on == 0, np.nan, 1 + on)[:, None]
    drift = np.nan_to_num(drift)
    cost = (np.abs(wn - drift) * cb).sum(1)
    r = risky + (1 - wn.sum(1)) * rf.reindex(W.index).ffill().fillna(0.0).to_numpy() - cost
    return pd.Series(r, index=W.index), pd.Series(np.abs(wn - drift).sum(1), index=W.index)

rows = []; EX = {}; NET = {}
def run(key, timed, name):
    W, _ = V.build_decisions(key, close, rf, me, start, timed)
    net, gross, to, held, cost = E.simulate(W, ohlc, rf, exec="next_open")
    # point-in-time: held on day t equals decision at close t-1
    assert np.allclose(held.to_numpy(), W.shift(1).fillna(0.0).to_numpy())
    net = net.loc[first_ret:]; to = to.loc[first_ret:]
    ex = net - rfd.loc[net.index]
    EX[name] = ex; NET[name] = net
    yrs = len(net) / 252
    sr = V.sharpe(ex)
    rows.append(dict(name=name, sig=key[0] if timed else "BH", uni=key[1], wt=key[2], ro=key[3] if timed else "-",
                     sharpe=sr, se=math.sqrt((1 + sr**2/2)/yrs), ann_ret=float((1+net).prod()**(1/yrs)-1),
                     vol=float(net.std()*math.sqrt(252)), mdd=V.mdd(net), turnover=float(to.sum()/yrs)))
    return W
for k in grid: run(k, True, "|".join(k))
for b in bench: run(("SMA10",) + b[1:], False, f"BH|{b[1]}|{b[2]}")
df = pd.DataFrame(rows).set_index("name")
df["untimed"] = [df.loc[f"BH|{r.uni}|{r.wt}", "sharpe"] if r.sig != "BH" else np.nan for r in df.itertuples()]
df["d_untimed"] = df["sharpe"] - df["untimed"]
s3n = "SMA10|frozen5|equal|tbill"
df["d_s3"] = df["sharpe"] - df.loc[s3n, "sharpe"]
df.to_csv(os.path.join(OUT, "v_is_table.csv"))
pd.DataFrame(EX).to_parquet(os.path.join(OUT, "v_is_excess.parquet"))
T = df[df.sig != "BH"]
print("window", first_ret.date(), cal[-1].date(), "years", len(EX[s3n]) / 252)
print("N timed", len(T))
print("IS Sharpe median %.3f IQR %.3f-%.3f range %.3f-%.3f" % (T.sharpe.median(), T.sharpe.quantile(.25), T.sharpe.quantile(.75), T.sharpe.min(), T.sharpe.max()))
print("d_untimed median %.3f IQR %.3f..%.3f positive %d" % (T.d_untimed.median(), T.d_untimed.quantile(.25), T.d_untimed.quantile(.75), (T.d_untimed > 0).sum()))
print("S3 common window %.4f rank %d; BH5 %.4f" % (df.loc[s3n, "sharpe"], int(T.sharpe.rank(ascending=False)[s3n]), df.loc["BH|frozen5|equal", "sharpe"]))
best = T.sharpe.idxmax(); print("best", best, round(T.sharpe.max(), 4), "untimed", round(df.loc[best, "untimed"], 4))
print("mdd improvement median", (T.mdd - df.loc[[f"BH|{u}|{w}" for u, w in zip(T.uni, T.wt)], "mdd"].values).median())

# own simulator cross-check
for k in [s3n, best]:
    W, _ = V.build_decisions(tuple(k.split("|")), close, rf, me, start, True)
    r2, _ = own_sim(W, ohlc, rf)
    print("own-sim vs engine max abs diff", k, float((r2.loc[first_ret:] - NET[k]).abs().max()))

# frozen S3 reconciliation on its own window with my builder (no common start)
Wf, _ = None, None
cm = close.loc[me, V.UNI["frozen5"]]
sma = cm.rolling(10, min_periods=10).mean()
dec = ((cm > sma) & sma.notna()).astype(float) * 0.2
Wf = dec.reindex(cal).ffill().fillna(0.0)
netf, *_ = E.simulate(Wf, ohlc, rf, exec="next_open")
f2 = F2.returns("S3", "IS")
print("my S3 vs forward2 max diff", float((netf - f2).abs().max()))
s = netf.loc["2005-11-01":]; print("S3 own-window Sharpe", round(V.sharpe(s - rfd.loc[s.index]), 4), "first nonzero hold", Wf[Wf.sum(1) > 0].index[0].date())
bh = cm.notna() & sma.notna()
Wb = (bh.astype(float) * 0.2).reindex(cal).ffill().fillna(0.0)
nb, *_ = E.simulate(Wb, ohlc, rf, exec="next_open")
print("my BH5 vs forward2", float((nb - F2.returns("BH5", "IS")).abs().max()))
json.dump({"start_decision": str(start.date()), "first_return": str(first_ret.date())}, open(os.path.join(OUT, "v_is_done.json"), "w"))
print("secs", time.time() - t0)
