# Size of candidate H1-primary decision procedures at n=27 under heteroskedastic, heavy-tailed outcomes.
import numpy as np, pandas as pd
rng=np.random.default_rng(7)
U='<scratch>/fedtalk/data_markets/usmpd/USMPD.xlsx'
p=pd.read_excel(U,sheet_name='Press Conferences'); p['Date']=pd.to_datetime(p['Date'])
c=p[(p.Date>='2023-02-01')&(p.Date<='2026-04-29')]
sig=np.abs(c['UST2Y'].values)*100; sig=np.maximum(sig,0.3)  # bp, used as per-meeting vol template
n=len(sig); print('n',n,'sig bp',np.round(np.sort(sig),1))
B=999; R=2000
def ols(x,y):
    X=np.column_stack([np.ones(len(x)),x]); XtX=np.linalg.inv(X.T@X); b=XtX@X.T@y; e=y-X@b
    h=np.sum(X@XtX*X,1); V=XtX@(X.T*(e**2/(1-h)**2))@X@XtX  # HC3
    return b[1], b[1]/np.sqrt(V[1,1]), e, b, h
def wild_unres_beta(x,y,w):
    b1,t,e,b,h=ols(x,y); X=np.column_stack([np.ones(n),x]); fit=X@b
    bs=np.array([ols(x,fit+e*w[k])[0] for k in range(B)])
    return np.mean(bs-b1>=b1)        # percentile-t-free 'basic' one-sided p on beta
def wild_res_t(x,y,w):
    b1,t,e,b,h=ols(x,y); y0=y-y.mean()+0; r0=y-y.mean()   # null imposed: beta=0, intercept only
    ts=np.array([ols(x,y.mean()+r0*w[k])[1] for k in range(B)])
    return np.mean(ts>=t)
def hc3_t(x,y):
    from scipy import stats
    b1,t,*_=ols(x,y); return 1-stats.t.cdf(t,n-2)
res={k:[] for k in ['wild_unres_beta','wild_res_t','hc3_t']}
for scen in ['x_normal','x_t3','x_t3_lev_on_bigvol']:
    res={k:[] for k in res}
    for r in range(R):
        if scen=='x_normal': x=rng.standard_normal(n)
        else: x=rng.standard_t(3,n)
        if scen=='x_t3_lev_on_bigvol':
            o=np.argsort(sig); xs=np.sort(np.abs(x)); x=np.empty(n); x[o]=xs*rng.choice([-1,1],n)
        y=sig*rng.standard_t(4,n)
        w=rng.choice([-1.,1.],(B,n))
        res['wild_unres_beta'].append(wild_unres_beta(x,y,w)<0.05)
        res['wild_res_t'].append(wild_res_t(x,y,w)<0.05)
        res['hc3_t'].append(hc3_t(x,y)<0.05)
    print(scen,{k:round(np.mean(v),3) for k,v in res.items()})
