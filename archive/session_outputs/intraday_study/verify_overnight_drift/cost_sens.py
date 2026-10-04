import numpy as np, pandas as pd, statsmodels.api as sm
ex=pd.read_parquet('overnight_drift/daily_strategy_returns.parquet')
S={'pre':('2010-06-08','2020-01-31'),'post':('2020-02-01','2024-10-02'),'IS':('2010-06-08','2024-10-02'),'later':('2024-10-03','2026-10-02')}
bhg=ex['ES|BH|gross'].dropna()
for nm in ['EU_01_04','ON_16_09']:
    g=ex[f'ES|{nm}|gross'].dropna(); u=(g-ex[f'ES|{nm}|1x'].dropna())/1e-4
    for c in [0.25,0.5]:
        for s,(a,b) in S.items():
            m=(g.index>=a)&(g.index<=b)
            y=(g-c*1e-4*u)[m]; x=bhg[m]
            n=len(y); L=int(4*(n/100)**(2/9))
            f=sm.OLS(y.values,sm.add_constant(x.values)).fit(cov_type='HAC',cov_kwds={'maxlags':L})
            print(nm,c,'bp',s,'SR %.2f'%(y.mean()/y.std()*np.sqrt(252)),'alpha %.2f%%/yr t %.2f'%(f.params[0]*25200,f.tvalues[0]))
