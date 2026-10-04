import os, sys, math, json, itertools
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vlib as V
from src import engine as E
OUT = os.path.dirname(os.path.abspath(__file__))
X = pd.read_parquet(os.path.join(OUT, "v_is_excess.parquet"))
tab = pd.read_csv(os.path.join(OUT, "v_is_table.csv"), index_col=0)
timed = [c for c in X.columns if not c.startswith("BH|")]
unt = {c: "BH|%s|%s" % tuple(c.split("|")[1:3]) for c in timed}
s3 = "SMA10|frozen5|equal|tbill"
def sr(df): return df.mean() / df.std() * math.sqrt(252)
# ex 2008-09
m = ~X.index.year.isin([2008, 2009])
S = sr(X[m]); d = pd.Series({c: S[c] - S[unt[c]] for c in timed})
print("ex08-09 timing gain median %.3f share>0 %.3f" % (d.median(), (d > 0).mean()))
S = sr(X[~m]); d2 = pd.Series({c: S[c] - S[unt[c]] for c in timed}); print("08-09 only median %.3f" % d2.median())
# also ex 2008 only
m8 = X.index.year != 2008
S = sr(X[m8]); d3 = pd.Series({c: S[c] - S[unt[c]] for c in timed}); print("ex 2008 only: median %.3f share %.3f" % (d3.median(), (d3 > 0).mean()))
# split halves
mid = len(X) // 2
H1, H2 = X.iloc[:mid], X.iloc[mid:]
print("halves", H1.index[0].date(), H1.index[-1].date(), H2.index[0].date(), H2.index[-1].date())
s1, s2 = sr(H1)[timed], sr(H2)[timed]
g1 = pd.Series({c: sr(H1)[c] - sr(H1)[unt[c]] for c in timed}); g2 = pd.Series({c: sr(H2)[c] - sr(H2)[unt[c]] for c in timed})
print("H1 timing share %.2f med %.3f ; H2 share %.2f med %.3f" % ((g1 > 0).mean(), g1.median(), (g2 > 0).mean(), g2.median()))
print("Spearman H1/H2 sharpe %.3f, gains %.3f" % (stats.spearmanr(s1, s2)[0], stats.spearmanr(g1, g2)[0]))
b1 = s1.idxmax(); print("H1 best", b1, "rank in H2", int(s2.rank(ascending=False)[b1]))
# bootstrap CIs on timing gains
B = 1000
for L in (63, 21):
    bs = pd.DataFrame(V.boot_sharpes(X[timed + list(set(unt.values()))].to_numpy(), L=L, B=B, seed=5), columns=timed + list(set(unt.values())))
    D = pd.DataFrame({c: bs[c] - bs[unt[c]] for c in timed})
    lo, hi = D.quantile(.05), D.quantile(.95)
    gm = D.mean(1)
    print(f"L={L}: variants with 90% CI lo>0: {(lo > 0).sum()}; grid-mean CI [{gm.quantile(.05):.3f},{gm.quantile(.95):.3f}]")
    best = tab.loc[timed, "sharpe"].idxmax()
    ds3 = bs[best] - bs[s3]; print("  best-S3 %.3f CI [%.3f,%.3f]" % (tab.loc[best, "sharpe"] - tab.loc[s3, "sharpe"], ds3.quantile(.05), ds3.quantile(.95)))
    print("  best-untimed CI [%.3f,%.3f]" % (D[best].quantile(.05), D[best].quantile(.95)))
    # White reality check (max of centred bootstrap differences)
    obs = pd.Series({c: tab.loc[c, "sharpe"] - tab.loc[unt[c], "sharpe"] for c in timed})
    cen = D - obs
    p = (cen.max(1) >= obs.max()).mean(); print("  RC best timing gain p=%.3f" % p)
    obs3 = pd.Series({c: tab.loc[c, "sharpe"] - tab.loc[s3, "sharpe"] for c in timed if c != s3})
    D3 = pd.DataFrame({c: bs[c] - bs[s3] for c in obs3.index}) - obs3
    print("  RC best vs S3 p=%.3f" % (D3.max(1) >= obs3.max()).mean())
# DSR (own formula, Bailey-LdP)
best = tab.loc[timed, "sharpe"].idxmax(); x = X[best]
n = len(x); srd = x.mean() / x.std(); sk = stats.skew(x); ku = stats.kurtosis(x, fisher=False)
var_ann = tab.loc[timed, "sharpe"].var(ddof=1); N = len(timed); g = 0.5772156649
sr0 = math.sqrt(var_ann / 252) * ((1 - g) * stats.norm.ppf(1 - 1 / N) + g * stats.norm.ppf(1 - 1 / (N * math.e)))
dsr = stats.norm.cdf((srd - sr0) * math.sqrt(n - 1) / math.sqrt(1 - sk * srd + (ku - 1) / 4 * srd ** 2))
print("DSR best %.3f SR0_ann %.3f var %.4f" % (dsr, sr0 * math.sqrt(252), var_ann))
# own CSCV PBO
def pbo(R, S=16):
    A = R.to_numpy(); T, N = A.shape; ed = np.linspace(0, T, S + 1).astype(int)
    blocks = [A[a:b] for a, b in zip(ed[:-1], ed[1:])]
    out = []
    for tr in itertools.combinations(range(S), S // 2):
        te = [i for i in range(S) if i not in tr]
        Atr = np.vstack([blocks[i] for i in tr]); Ate = np.vstack([blocks[i] for i in te])
        st = Atr.mean(0) / Atr.std(0); se = Ate.mean(0) / Ate.std(0)
        b = st.argmax(); w = (stats.rankdata(se)[b]) / (N + 1)
        out.append(np.log(w / (1 - w)))
    return float((np.array(out) <= 0).mean())
print("PBO S=10 %.3f" % pbo(X[timed], 10))
print("PBO S=16 %.3f" % pbo(X[timed], 16))
