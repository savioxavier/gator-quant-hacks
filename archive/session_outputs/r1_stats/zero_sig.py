import pandas as pd, numpy as np
from scipy import stats
U='<scratch>/fedtalk/data_markets/usmpd/USMPD.xlsx'
s=pd.read_excel(U,sheet_name='Statements'); p=pd.read_excel(U,sheet_name='Press Conferences')
s['Date']=pd.to_datetime(s['Date']); p['Date']=pd.to_datetime(p['Date'])
m=s.merge(p[['Date','UST2Y']],on='Date',suffixes=('_s','_p'))
m=m[~m.Date.dt.strftime('%Y%m%d').isin(['20200303','20200315'])]
m['yr']=m.Date.dt.year
DV01=38.0
m['tick_usd']=np.where(m.Date>='2019-01-14',7.8125,15.625)
m['ticks_s']=m.UST2Y_s*100*DV01/m.tick_usd   # statement-window move in ZT ticks (approx, sign flipped irrelevant)
for lo,hi in [(2011,2015),(2016,2019),(2011,2019),(2020,2026)]:
    g=m[(m.yr>=lo)&(m.yr<=hi)]
    print(f'{lo}-{hi} n={len(g)}  |stmt move| < 0.5 tick: {int((g.ticks_s.abs()<0.5).sum())}  < 1 tick: {int((g.ticks_s.abs()<1).sum())}  median |ticks| {g.ticks_s.abs().median():.1f}  UST2Y_s exactly 0: {int((g.UST2Y_s==0).sum())}')
# D-VAL gate misclassification at meeting level n=36 (Fisher z)
for n in (36,16):
    se=1/np.sqrt(n-3)
    for rho in (0.25,0.45,0.55,0.65):
        print(f'n={n} true rho={rho}: P(rho_hat<0.4)={stats.norm.cdf((np.arctanh(0.4)-np.arctanh(rho))/se):.2f}')
