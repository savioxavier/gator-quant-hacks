"""Extra fragility checks: FOMC subsample dependence and an independent long-history proxy trend check."""
import os
import numpy as np
import pandas as pd
from v_common import HERE, GQH, IS_END, nw_t

W = pd.read_csv(os.path.join(HERE, 'v_fomc_windows.csv'), parse_dates=['d'])
g = W[(W.root == 'ES') & (W.window == '14_to_rel') & (W.d <= IS_END)].copy()
y = g.d.dt.year
rng = np.random.default_rng(1)


def summ(x, lab):
    x = x.values
    print(f'{lab:32s} n={len(x):3d} mean={x.mean()*1e4:7.2f} bp median={np.median(x)*1e4:7.2f} t_nw2={nw_t(x,2):5.2f}')


summ(g.ret, 'IS all')
summ(g.ret[y >= 2011], 'IS ex-2010')
summ(g.ret[(y >= 2011) & (y <= 2014)], '2011-2014')
summ(g.ret[y == 2010], '2010')
summ(g.ret[(y >= 2015) & ~y.isin([2020, 2022])], '2015-24 ex 2020,2022')
summ(g.ret[~y.isin([2020, 2022])], 'IS ex 2020,2022')
summ(g.ret[~y.isin([2022])], 'IS ex 2022')
# winsorised / trimmed
x = g.ret.values
q = np.sort(x)
print('IS trimmed mean (drop top/bottom 5)', round(q[5:-5].mean() * 1e4, 2), 'bp')
a = g.ret[(y >= 2011) & (y <= 2014)].values
b = g.ret[(y >= 2015)].values
da = rng.choice(a, (20000, len(a))).mean(1) - rng.choice(b, (20000, len(b))).mean(1)
print('2011-14 minus 2015-24', round((a.mean() - b.mean()) * 1e4, 1), 'bp, boot p', 2 * min((da <= 0).mean(), (da >= 0).mean()))
# sign-randomisation-free check: share of years positive
print('years with positive mean (IS):', (g.groupby(y).ret.mean() > 0).sum(), 'of', y.nunique())

# ---- long-history proxy: equity (FF Mkt-RF) EWMAC(2,8) and (16,64), no buffer, gross, own code
ff = pd.read_parquet(os.path.join(GQH, 'ff_daily.parquet')).set_index('date')
r = ff['Mkt_RF'].loc['1988-01-01':'2024-10-02']
lr = np.log1p(r)
X = lr.cumsum()
sd = np.sqrt((lr ** 2).ewm(span=35, adjust=False, min_periods=35).mean())
sa = np.sqrt((r ** 2).ewm(span=35, adjust=False, min_periods=35).mean() * 252).shift(1)
print('FF lag-1 autocorr 1990-99 / 2000-08 / 2009-24:',
      [round(r.loc[a:b].autocorr(1), 3) for a, b in [('1990', '1999'), ('2000', '2008'), ('2009', '2024')]])
for f, s in [(2, 8), (16, 64)]:
    raw = (X.ewm(span=f, adjust=False).mean() - X.ewm(span=s, adjust=False).mean()) / sd
    fc = (raw * 10 / raw.loc['1990':].abs().mean()).clip(-20, 20)
    pos = fc / 10 * 0.1 / sa
    pnl = pos.shift(1) * r
    out = {p: pnl.loc[a:b] for p, (a, b) in {'1990-2008': ('1990', '2008'), '2000-2008': ('2000', '2008'),
                                               '2009-2024': ('2009', '2024')}.items()}
    print('EQ proxy', (f, s), {k: round(v.mean() / v.std() * np.sqrt(252), 2) for k, v in out.items()})
