import sys, math
import numpy as np, pandas as pd
sys.path.insert(0, ".")
import v_core as V
close, vol, roll, rf, ex, rtot = V.load()
etf = pd.read_parquet(V.D / "etf_daily.parquet")
px = etf.pivot(index="date", columns="ticker", values="close")
print("1) data sanity: futures excess vs ETF TR excess, 2011-09-02..2024-10-02")
IS = slice("2011-09-02", "2024-10-02")
for f, e in [("F_ES", "SPY"), ("F_ZN", "IEF"), ("F_GC", "GLD")]:
    if e not in px: print(e, "missing"); continue
    er = px[e].pct_change().reindex(ex.index) - rf
    a = pd.concat([ex[f], er], axis=1).loc[IS].dropna()
    print(f"  {f} vs {e}: corr {a.corr().iloc[0,1]:.3f}  ann mean {a.iloc[:,0].mean()*252:.4f} vs {a.iloc[:,1].mean()*252:.4f}  SR {V.sharpe(a.iloc[:,0]):.3f} vs {V.sharpe(a.iloc[:,1]):.3f}")
    # weekly corr (removes close-time asynchrony)
    wk = (1 + a).resample("W").prod() - 1
    print(f"     weekly corr {wk.corr().iloc[0,1]:.3f}")
# roll day returns abnormal?
for f in ["F_ES", "F_ZN", "F_GC"]:
    rr = ex[f][roll[f] > 0].abs().mean(); nr = ex[f][roll[f] == 0].abs().mean()
    print(f"  {f} mean |ret| roll days {rr:.5f} vs other {nr:.5f}; n roll {int((roll[f]>0).sum())}; zero-ret days {(ex[f]+rf==0).sum()}")

S = pd.read_pickle("my_series.pkl")
SER = "<scratch>/edges/series/"
print("\n2) exact match of saved series vs my recomputation (max abs over all columns)")
mx = 0
for k, s in S.items():
    f = pd.read_parquet(SER + k + ".parquet")
    d = (f[["net_1x", "net_2x", "gross"]] - s[["net_1x", "net_2x", "gross"]]).abs().max().max()
    mx = max(mx, d)
print("  worst max abs diff:", mx)

print("\n3) Sharpe uncertainty and stats, IS")
for k in ["rpm_ES_STATIC", "rpm_ES_CV", "rpm_ES_MM", "rpm_SB_CV", "rpm_SB_FB", "rpm_SB_MM"]:
    x = S[k]["net_1x"].loc[IS]
    yrs = len(x) / 252; sr = V.sharpe(x)
    se = math.sqrt((1 + sr**2/2) / yrs)
    yr = (1 + x).groupby(x.index.year).prod() - 1
    print(f"  {k:14s} SR {sr:.3f} SE {se:.3f} 95%CI [{sr-1.96*se:.2f},{sr+1.96*se:.2f}]  2022 {yr.get(2022):+.3f}  excessDD {V.mdd(x):.3f}  realized vol {x.std()*252**.5:.3f}")

print("\n4) own paired block bootstrap (63d blocks, 5000) on IS net_1x")
def boot(a, b, block=63, reps=5000, seed=11):
    df = pd.concat([a, b], axis=1).dropna().to_numpy(); n = len(df)
    rng = np.random.default_rng(seed); nb = math.ceil(n / block); d = []
    for _ in range(reps):
        st = rng.integers(0, n - block, nb)
        idx = (st[:, None] + np.arange(block)).ravel()[:n]
        x = df[idx]
        d.append((x[:, 0].mean() / x[:, 0].std() - x[:, 1].mean() / x[:, 1].std()) * 252**.5)
    d = np.array(d); obs = V.sharpe(pd.Series(df[:, 0])) - V.sharpe(pd.Series(df[:, 1]))
    return obs, 2 * min((d <= 0).mean(), (d >= 0).mean()), np.percentile(d, [2.5, 97.5])
for a, b in [("rpm_ES_MM", "rpm_ES_STATIC"), ("rpm_ES_MM", "rpm_ES_CV"), ("rpm_SB_FB", "rpm_SB_CV"), ("rpm_SB_FB", "rpm_ES_MM"), ("rpm_SB_CV", "rpm_ES_CV"), ("rpm_ES_FB", "rpm_ES_CV")]:
    o, p, ci = boot(S[a]["net_1x"].loc[IS], S[b]["net_1x"].loc[IS])
    print(f"  {a} - {b}: {o:+.3f} p={p:.3f} CI [{ci[0]:+.2f},{ci[1]:+.2f}]")

print("\n5) MM sensitivity (verifier robustness, NOT in SPEC): cap level and lag")
Est = V.Est(ex, close, vol)
start = pd.Timestamp("2011-09-02")
for lab, kw in [("cap1.5 (spec)", {}), ("no cap", {"mm_cap": False}), ("cap1.0", {"cap_mm": 1.0}), ("cap2.0", {"cap_mm": 2.0})]:
    w = Est.single("F_ES", "MM", **kw)
    n1, g, t = V.sim_daily(w, rtot, rf, roll)
    x = (n1 - rf).loc[start:"2024-10-02"]; L = (n1 - rf).loc["2024-10-03":]
    print(f"  ES MM {lab:14s} IS SR {V.sharpe(x):.3f} DDex {V.mdd(x):.3f} avg gross {w.loc[start:'2024-10-02'].mean().iloc[0]:.2f} later {V.sharpe(L):.3f}")
ws = Est.single("F_ES", "STATIC")
print("  ES STATIC avg gross", round(float(ws.loc[start:'2024-10-02'].mean().iloc[0]), 2))
# MM vs STATIC levered to same average gross: Sharpe unchanged, compare DD at matched realized vol
xm = S["rpm_ES_MM"]["net_1x"].loc[IS]; xs = S["rpm_ES_STATIC"]["net_1x"].loc[IS]
print(f"  matched-vol excess DD: MM {V.mdd(xm * xs.std()/xm.std()):.3f} vs STATIC {V.mdd(xs):.3f}")

print("\n6) long-history proxy: excess vs total drawdowns (analyst's longhist_series)")
lh = pd.read_parquet("<scratch>/edges/risk_premia/out/longhist_series.parquet")
for k, a in [("LH_SB_FB", "1963-04-02"), ("LH_SB_CV", "1963-04-02"), ("LH_EQ_MM", "1927-08-02"), ("LH_EQ_STATIC", "1927-08-02"), ("LH_EQ_MM", "1963-04-02")]:
    x = lh[f"{k}|net_1x"].loc[a:"2024-10-02"].dropna()
    print(f"  {k:12s} from {a}: SR {V.sharpe(x):.3f}  excess DD {V.mdd(x):.3f}  1963-81 SR {V.sharpe(x.loc['1963':'1981']) if len(x.loc['1963':'1981']) else float('nan'):.3f}  2000-24 SR {V.sharpe(x.loc['2000':'2024-10-02']):.3f}")
