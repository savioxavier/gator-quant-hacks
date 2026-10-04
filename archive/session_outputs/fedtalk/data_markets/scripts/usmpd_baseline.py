"""Statement-window sign -> press-conference-window return (Gomez-Cram & Grotteria baseline) on the free USMPD.
USMPD windows: statement = -10..+20 min around 14:00; press conference = -10..+60 min around presser start.
Note the two windows overlap for 14:30 pressers? statement window ends 14:20, presser window starts 14:20: adjacent, not overlapping."""
import pandas as pd, numpy as np
st = pd.read_excel('usmpd/USMPD.xlsx', sheet_name='Statements')
pc = pd.read_excel('usmpd/USMPD.xlsx', sheet_name='Press Conferences')
m = pc.merge(st, on='Date', suffixes=('_pc', '_st'))
m = m[~m['Date'].astype(str).str.startswith(('2020-03-03', '2020-03-15'))]
print('scheduled pressers with both windows:', len(m))
def report(col, unit, sub=None):
    d = m if sub is None else m[sub]
    x = d[col + '_st']; y = d[col + '_pc']
    ok = x.notna() & y.notna() & (x != 0)
    x, y = x[ok], y[ok]
    pnl = np.sign(x) * y
    n = len(pnl); t = pnl.mean() / pnl.std(ddof=1) * np.sqrt(n)
    rho = np.corrcoef(x, y)[0, 1]
    return f"{col:7s} n={n:3d} corr(st,pc)={rho:+.2f} mean signed pc move={pnl.mean():+.4f}{unit} t={t:+.2f} hit={np.mean(pnl>0):.2f} |pc| mean={y.abs().mean():.4f}{unit}"
eras = {'all': None, '2011-2019 (GCG sample era)': m['Date'] < '2020-01-31', '2020-2026 (post-GCG)': m['Date'] >= '2020-01-31',
        'every-meeting era 2019-2026': m['Date'] >= '2019-01-01'}
for name, sub in eras.items():
    print('==', name)
    for col, unit in [('SPFUT', '%'), ('SP500', '%'), ('UST2Y', 'pp'), ('UST10Y', 'pp'), ('ED4', 'pp'), ('EURUSD', '%'), ('USDJPY', '%')]:
        if col + '_st' in m.columns:
            print(report(col, unit, sub))
# variance share: presser vs statement window
for col in ['SPFUT', 'UST2Y', 'UST10Y']:
    for name, sub in [('2011-2018', m['Date'] < '2019-01-01'), ('2019-2026', m['Date'] >= '2019-01-01')]:
        d = m[sub]
        print(f"{col} {name}: std statement={d[col+'_st'].std():.4f} std presser={d[col+'_pc'].std():.4f}")
