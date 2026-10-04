# Post-publication check of Faber (2010) sector relative strength and Moskowitz-Grinblatt (1999) industry momentum
# on Ken French 10 value-weighted industries (monthly, gross, no costs). Descriptive evidence only.
import io, numpy as np, pandas as pd
import os
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data') + os.sep
def read_block(path, start_marker_idx=0):
    lines = open(path, encoding='latin-1').read().splitlines()
    hdr_idx = [i for i, l in enumerate(lines) if l.startswith(',')][start_marker_idx]
    rows = []
    for l in lines[hdr_idx+1:]:
        p = l.split(',')
        if len(p) < 2 or not p[0].strip().isdigit() or len(p[0].strip()) != 6: break
        rows.append(p)
    cols = [c.strip() for c in lines[hdr_idx].split(',')]
    df = pd.DataFrame(rows, columns=cols).set_index(cols[0])
    df.index = pd.PeriodIndex([f'{s.strip()[:4]}-{s.strip()[4:]}' for s in df.index], freq='M')
    return df.astype(float) / 100.0
ind = read_block(D + '10_Industry_Portfolios.csv', 0)
ff = read_block(D + 'F-F_Research_Data_Factors.csv', 0)
rf = ff['RF'].reindex(ind.index)
gross = 1 + ind
def trail(k): return gross.rolling(k).apply(np.prod, raw=True) - 1
sig_faber = sum(trail(k) for k in (1, 3, 6, 9, 12)) / 5
sig_mg = trail(6)
def top_k(sig, k, bottom=False):
    r = sig.rank(axis=1, ascending=bottom)
    return (r <= k).astype(float).div(k)
w_top3 = top_k(sig_faber, 3).shift(1)          # signal at month-end t, held in t+1
w_mg_long = top_k(sig_mg, 3).shift(1); w_mg_short = top_k(sig_mg, 3, bottom=True).shift(1)
ew = ind.mean(axis=1)
top3 = (w_top3 * ind).sum(axis=1)
mg_ls = (w_mg_long * ind).sum(axis=1) - (w_mg_short * ind).sum(axis=1)
# 10-month SMA filter on the market proxy (EW of industries) for Faber's hedged version
mkt_idx = (1 + ew).cumprod(); sma10 = mkt_idx.rolling(10).mean()
on = (mkt_idx > sma10).astype(float).shift(1)
top3_hedged = on * top3 + (1 - on) * rf
def sr(x):
    x = x.dropna(); return x.mean() / x.std() * np.sqrt(12), x.mean() * 12, x.std() * np.sqrt(12), len(x)
periods = {'Faber sample 1928-01..2009-12': ('1928-01', '2009-12'), 'MG sample 1963-07..1995-07': ('1963-07', '1995-07'),
           'post-MG 1999-08..2026': ('1999-08', '2026-12'), 'post-Faber 2010-01..2026': ('2010-01', '2026-12'),
           '2016-01..2024-09': ('2016-01', '2024-09'), '2003-2024-09 (our ETF IS span)': ('2003-01', '2024-09')}
out = []
for name, (a, b) in periods.items():
    s = slice(a, b)
    row = {'period': name}
    for lab, ser in [('EW10 excess', ew - rf), ('Faber top3 excess', top3 - rf), ('top3 minus EW10', top3 - ew),
                     ('top3 hedged excess', top3_hedged - rf), ('MG 6m top3-bottom3', mg_ls)]:
        v = sr(ser.loc[s]); row[lab] = f'SR {v[0]:.2f} (mu {v[1]*100:.1f}%, vol {v[2]*100:.1f}%, n={v[3]})'
    out.append(row)
for r in out:
    print('==', r.pop('period'))
    for k, v in r.items(): print(f'   {k:20s} {v}')
print('last month in data:', ind.index[-1])
