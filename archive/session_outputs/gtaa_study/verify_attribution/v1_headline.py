import sys, json, math, numpy as np, pandas as pd
import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "."); sys.path.insert(0, "<solo-repo>")
from core import *
import statsmodels.api as sm
res = {}
px, rf = load()
dS = decisions(px["close"]); dB = decisions(px["close"], bh=True)
nS, hS, cS, onS, ocS = sim_formula(dS, px, rf)
nB, hB, cB, onB, ocB = sim_formula(dB, px, rf)
navS = sim_nav(dS, px, rf); navB = sim_nav(dB, px, rf)
first = hS.index[(hB.sum(1) > 0)][0]
print("first traded day", first)
# compare against the frozen repo code (read only)
from src import forward2
fS = forward2.returns("S3", "FWD"); fB = forward2.returns("BH5", "FWD")
print("max |mine - frozen| S3", (nS - fS.reindex(nS.index)).loc[first:].abs().max(), "BH5", (nB - fB.reindex(nB.index)).loc[first:].abs().max())
print("max |nav - formula| S3", (navS - nS).loc[first:].abs().max())
# point in time: decisions from data truncated to each cut equal the full ones up to the cut
pxI, rfI = load(IS_END)
dSI = decisions(pxI["close"])
print("IS-truncated decisions identical:", np.allclose(dSI.values, dS.loc[:IS_END].values))
rng = np.random.default_rng(7); bad = 0
for cut in rng.choice(px["close"].index[300:-30], 25, replace=False):
    p2 = {k: v.copy() for k, v in px.items()}
    for k in p2: p2[k].loc[p2[k].index > cut] *= rng.uniform(0.5, 1.5, size=p2[k].loc[p2[k].index > cut].shape)
    d2 = decisions(p2["close"])
    bad += int(not np.allclose(d2.loc[:cut].values, dS.loc[:cut].values))
print("scramble-future test failures:", bad)
# held at d equals decision at d-1
print("held(d)==dec(d-1):", np.allclose(hS.values[1:], dS.values[:-1]))
ex = lambda n: (n - rf).loc[first:]
rows = []
for nm, n in [("S3", nS), ("BH5", nB), ("S3_nav", navS), ("BH5_nav", navB)]:
    for p, s in periods(n, first).items():
        e = s - rf.reindex(s.index)
        rows.append(dict(series=nm, period=p, start=str(s.index[0].date()), end=str(s.index[-1].date()), n=len(s),
                         sharpe=sharpe(e), mdd=mdd(s), ann_excess=e.mean() * 252, vol=s.std() * math.sqrt(252),
                         cagr=(1 + s).prod() ** (252 / len(s)) - 1))
T = pd.DataFrame(rows); print(T.round(4).to_string()); T.to_csv("out/v1_stats.csv", index=False)
# bootstrap Sharpe diff and excess diff
eS = ex(nS); eB = ex(nB)
for p, (a, b) in {"IS": (eS.loc[:IS_END], eB.loc[:IS_END]), "OOS": (eS.loc[OOS_START:], eB.loc[OOS_START:])}.items():
    for blk in (21, 63):
        bs = block_boot(a.values, b.values, sr_np, blk, 5000)
        bm = block_boot(a.values, b.values, lambda z: z.mean() * 252, blk, 5000)
        pt = sr_np(a.values) - sr_np(b.values)
        print(p, blk, "SRdiff %.3f CI [%.3f, %.3f] P(<=0)=%.2f | exdiff %.4f CI [%.4f, %.4f]" % (
            pt, *np.percentile(bs, [2.5, 97.5]), (bs <= 0).mean(), (a - b).mean() * 252, *np.percentile(bm, [2.5, 97.5])))
    yrs = len(a) / 252
    for sr in (0, sr_np(a.values), sr_np(b.values)):
        print(p, "years %.2f analytic SE at SR %.2f = %.3f" % (yrs, sr, math.sqrt((1 + sr ** 2 / 2) / yrs)))
    print(p, "bootstrap SE S3 SR (63d):", np.std(block_boot(a.values, np.zeros_like(a.values) + 1e-9 * np.random.default_rng(3).standard_normal(len(a)), sr_np, 63, 3000) ))
# crisis window exclusion
m = ~((eS.index >= "2007-10-01") & (eS.index <= "2009-12-31"))
a = eS.loc[:IS_END][m[:len(eS.loc[:IS_END])]]; b = eB.loc[:IS_END][m[:len(eB.loc[:IS_END])]]
bs = block_boot(a.values, b.values, sr_np, 63, 5000)
print("IS ex-GFC S3 %.3f BH5 %.3f diff %.3f CI [%.3f, %.3f]" % (sr_np(a.values), sr_np(b.values), sr_np(a.values) - sr_np(b.values), *np.percentile(bs, [2.5, 97.5])))
# GFC episode
w = slice("2007-10-01", "2009-12-31")
print("GFC S3 %.3f BH5 %.3f mddS %.3f mddB %.3f" % ((1 + nS[w]).prod() - 1, (1 + nB[w]).prod() - 1, mdd(nS[w]), mdd(nB[w])))
# other episodes (descriptive)
for lab, a0, a1 in [("2011", "2011-07-01", "2011-12-30"), ("2015-16", "2015-07-01", "2016-03-31"), ("2018Q4", "2018-10-01", "2018-12-31"),
                    ("COVID", "2020-02-19", "2020-04-30"), ("2022", "2022-01-03", "2022-12-30"), ("Apr2025", "2025-03-01", "2025-06-30"), ("2026H1", "2026-02-01", "2026-06-30")]:
    print(lab, "S3 %.3f BH5 %.3f | mdd %.3f %.3f" % ((1 + nS[a0:a1]).prod() - 1, (1 + nB[a0:a1]).prod() - 1, mdd(nS[a0:a1]), mdd(nB[a0:a1])))
# regressions
spy_n, spy_h, *_ = sim_formula(pd.DataFrame(1.0, index=px["close"].index, columns=TK).mul([1, 0, 0, 0, 0]), px, rf)
for p, sl in {"IS": slice(first, IS_END), "OOS": slice(OOS_START, None)}.items():
    for xn, x in [("BH5", eB), ("SPY", (spy_n - rf).loc[first:])]:
        y = eS.loc[sl]; xx = x.loc[sl]
        lags = int(math.floor(4 * (len(y) / 100) ** (2 / 9)))
        r = sm.OLS(y.values, sm.add_constant(xx.values)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
        print(p, "on", xn, "beta %.3f (t %.1f) alpha %.4f/yr (t %.2f) R2 %.3f lags %d; beta*mean(x)/mean(y)=%.2f" % (
            r.params[1], r.tvalues[1], r.params[0] * 252, r.tvalues[0], r.rsquared, lags, r.params[1] * xx.mean() / y.mean()))
# per-ETF contributions and timing value
def contrib(on, oc, held, cost):
    return on + oc - held.mul(rf, axis=0) - cost
CS = contrib(onS, ocS, hS, cS).loc[first:]; CB = contrib(onB, ocB, hB, cB).loc[first:]
print("decomp check", (CS.sum(1) - eS).abs().max())
for p, sl in {"IS": slice(first, IS_END), "OOS": slice(OOS_START, None)}.items():
    print(p, "S3 contrib", (CS.loc[sl].mean() * 252).round(4).to_dict(), "sum", round(CS.loc[sl].sum(1).mean() * 252, 4))
    print(p, "timing value", ((CS.loc[sl] - CB.loc[sl]).mean() * 252).round(4).to_dict(), "total", round((CS.loc[sl] - CB.loc[sl]).sum(1).mean() * 252, 4))
    elig = hB.loc[sl] > 0
    print(p, "time invested", ((hS.loc[sl] > 0)[elig].sum() / elig.sum()).round(3).to_dict(), "avg exposure", round(hS.loc[sl].sum(1).mean() / 1.0, 3), "BH5 avg exp", round(hB.loc[sl].sum(1).mean(), 3))
    print(p, "cost/yr S3 %.5f BH5 %.5f" % (cS.loc[sl].sum(1).mean() * 252, cB.loc[sl].sum(1).mean() * 252))
# switches from decisions at month ends
me = month_ends(px["close"].index)
sig = (dS.loc[me] > 0).astype(int); el = (dB.loc[me] > 0)
ch = sig.diff()
for p, sl in {"IS": (me > first - pd.Timedelta(days=40)) & (me < IS_END), "OOS": me >= pd.Timestamp("2024-09-30")}.items():
    pass
for p, (a0, a1) in {"IS": (pd.Timestamp("2005-10-01"), pd.Timestamp("2024-10-01")), "OOS": (pd.Timestamp("2024-10-02"), pd.Timestamp("2026-10-01"))}.items():
    # count by fill date (next session after decision)
    fills = pd.Series(px["close"].index[np.searchsorted(px["close"].index, me) + 1].tolist()[:len(me)] if True else None, index=me)
    msk = (fills >= a0) & (fills <= a1) & el.shift(1).fillna(False).all(axis=1) | ((fills >= a0) & (fills <= a1))
    sub = ch[(fills >= a0) & (fills <= a1)] * el.shift(1, fill_value=False)[(fills >= a0) & (fills <= a1)]
    print(p, "exits", (sub == -1).sum().to_dict(), "entries", (sub == 1).sum().to_dict())
pd.concat({"S3": nS, "BH5": nB, "rf": rf}, axis=1).to_csv("out/v1_daily.csv")
hS.to_csv("out/v1_heldS3.csv"); CS.to_csv("out/v1_contribS3.csv"); CB.to_csv("out/v1_contribBH5.csv")
