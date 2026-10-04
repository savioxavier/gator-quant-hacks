"""Second pass: cross-check against the analyst's daily features, P&L concentration in the 2020 window,
volatility interaction and tercile spread, and the multiple-testing claim."""
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

OUT = Path(__file__).resolve().parent
THEIRS = OUT.parent / "intraday_momentum"
IS_END = pd.Timestamp("2024-10-02")
RNG = np.random.default_rng(11)


def nwl(n):
    return int(np.floor(4 * (n / 100) ** (2 / 9)))


for name in ("ES_1600", "ZN_1500"):
    mine = pd.read_parquet(OUT / f"feat_{name}.parquet")
    th = pd.read_parquet(THEIRS / f"daily_{name}.parquet")
    j = mine[mine.eligible].join(th[th.eligible][["lh", "rod", "onfh"]], rsuffix="_t", how="inner")
    print(name, "common eligible days", len(j), "mine only", len(mine[mine.eligible].index.difference(j.index)),
          "theirs only", len(th[th.eligible].index.difference(j.index)))
    for c in ("lh", "rod", "onfh"):
        d = (j[c] - j[c + "_t"]).abs() * 1e4
        print(f"  {c}: max |diff| {d.max():.3f} bp, days >0.5bp {(d > 0.5).sum()}, sign disagreements "
              f"{(np.sign(j[c]) != np.sign(j[c + '_t'])).sum()}")
    big = j[(j.rod - j.rod_t).abs() * 1e4 > 0.5]
    if len(big):
        print("  examples rod diff:", big[["rod", "rod_t"]].head(5).mul(1e4).round(2).to_dict("index"))
    only_t = th[th.eligible].index.difference(j.index)
    print("  their-only days sample:", [str(x.date()) for x in only_t[:8]])

# P&L concentration of ES S2 gross in the 2020-02-20..04-30 window (mine)
f = pd.read_parquet(OUT / "feat_ES_1600.parquet")
e = f[f.eligible & (f.index <= IS_END)].copy()
e["g"] = np.sign(e.rod) * e.lh
cov = (e.index >= "2020-02-20") & (e.index <= "2020-04-30")
print(f"ES S2 gross IS total {e.g.sum()*1e4:.0f} bp; 2020-02-20..04-30 ({cov.sum()} days) {e.g[cov].sum()*1e4:.0f} bp "
      f"= {e.g[cov].sum()/e.g.sum()*100:.0f}% of total")
thr = e.rod.abs().median()
s5 = np.where(e.rod.abs() > thr, np.sign(e.rod), 0) * e.lh
print(f"ES S5 gross IS total {s5.sum()*1e4:.0f} bp; covid window {s5[cov].sum()*1e4:.0f} bp")
q2 = e.rv_same.quantile(2 / 3)
q1 = e.rv_same.quantile(1 / 3)
s6 = np.where(e.rv_same > q2, np.sign(e.rod), 0) * e.lh
print(f"ES S6 gross IS total {s6.sum()*1e4:.0f} bp; covid window {s6[cov].sum()*1e4:.0f} bp; net 1x total "
      f"{(s6.sum() - 2e-4*(e.rv_same > q2).sum())*1e4:.0f} bp, covid net {(s6[cov].sum()-2e-4*((e.rv_same>q2)&cov).sum())*1e4:.0f} bp")
# by year of S6 1x net
s6n = pd.Series(s6 - 2e-4 * (e.rv_same > q2), index=e.index)
print("ES S6 net1x by year (bp):", (s6n.groupby(s6n.index.year).sum() * 1e4).round(0).to_dict())
s5n = pd.Series(s5 - 2e-4 * (e.rod.abs() > thr), index=e.index)
print("ES S5 net1x by year (bp):", (s5n.groupby(s5n.index.year).sum() * 1e4).round(0).to_dict())

# high minus low tercile, same-day RV, sign ROD per trade
terc = np.select([e.rv_same <= q1, e.rv_same <= q2], [1, 2], 3)
g = e.g.values
pt = g[terc == 3].mean() - g[terc == 1].mean()
n = len(g); L = 20; nb = int(np.ceil(n / L)); bs = []
for _ in range(3000):
    s = RNG.integers(0, n - L + 1, nb); ii = (s[:, None] + np.arange(L)).ravel()[:n]
    bs.append(g[ii][terc[ii] == 3].mean() - g[ii][terc[ii] == 1].mean())
print(f"ES high-low same-day RV tercile sign(ROD) {pt*1e4:.2f} bp, CI {np.percentile(bs,[2.5,97.5]).round(6)*1e4}")
for lab, sub in (("all", e), ("exCOVID", e[~cov])):
    z = (sub.rv_same - e.rv_same.mean()) / e.rv_same.std()
    X = sm.add_constant(pd.DataFrame({"x": sub.rod, "z": z, "xz": sub.rod * z}))
    m = sm.OLS(sub.lh, X).fit(cov_type="HAC", cov_kwds={"maxlags": nwl(len(sub))})
    print(f"ES ROD x same-day RV interaction {lab}: b {m.params['xz']:.4f} t {m.tvalues['xz']:.2f}")

# multiple testing check from their strategy table
s = pd.read_csv(THEIRS / "strategies.csv")
q = s[(s["sample"] == "IS") & (s.cost == "gross") & (~s.variant.str.startswith("B0"))]
p = 2 * stats.norm.sf(q.nw_t_mean.abs())
print("non-benchmark gross IS strategy definitions:", len(q), "max t", q.nw_t_mean.max().round(2),
      "min Bonferroni p", (p.min() * len(q)).round(3))
srt = np.sort(p); holm = any(srt[k] <= 0.05 / (len(q) - k) for k in range(len(q)))
print("any Holm rejection at 5%:", holm)
q1x = s[(s["sample"] == "IS") & (s.cost == "1x") & (~s.variant.str.startswith("B0"))]
pos = q1x[q1x.sharpe > 0][["spec", "variant", "sharpe", "nw_t_mean"]]
print("positive 1x IS Sharpe definitions:\n", pos.to_string())
# expected max Sharpe of 6 ES S6/S5-like noise strategies: SE ~0.27
print("E[max of 18 N(0,0.27)] approx", round(0.27 * np.mean(np.max(RNG.standard_normal((20000, 18)), axis=1)), 2))
