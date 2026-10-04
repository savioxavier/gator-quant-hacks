# Same as sim_boot.py but with the A-09 control (R_stmt) in the regression, comparing four bootstrap variants.
import numpy as np, pandas as pd
rng=np.random.default_rng(11)
U='<scratch>/fedtalk/data_markets/usmpd/USMPD.xlsx'
p=pd.read_excel(U,sheet_name='Press Conferences'); p['Date']=pd.to_datetime(p['Date'])
c=p[(p.Date>='2023-02-01')&(p.Date<='2026-04-29')]
sig=np.maximum(np.abs(c['UST2Y'].values)*100,0.3); n=len(sig); B=999; R=1500
def fit(X,y):
    XtX=np.linalg.inv(X.T@X); b=XtX@X.T@y; e=y-X@b; h=np.sum(X@XtX*X,1)
    V=XtX@(X.T*(e**2/(1-h)**2))@X@XtX; return b,e,np.sqrt(V[1,1])
out={k:0 for k in ['unres_beta','unres_t','res_beta','res_t']}
for r in range(R):
    x=rng.standard_t(3,n); o=np.argsort(sig); xs=np.sort(np.abs(x)); x=np.empty(n); x[o]=xs*rng.choice([-1,1],n)
    z=0.5*x+rng.standard_normal(n)            # R_stmt correlated with the surprise
    y=sig*rng.standard_t(4,n)
    X=np.column_stack([np.ones(n),x,z]); X0=np.column_stack([np.ones(n),z])
    b,e,se=fit(X,y); t=b[1]/se
    b0=np.linalg.lstsq(X0,y,rcond=None)[0]; f0=X0@b0; e0=y-f0; f=X@b
    W=rng.choice([-1.,1.],(B,n))
    ub=np.empty(B); ut=np.empty(B); rb=np.empty(B); rt=np.empty(B)
    for k in range(B):
        bb,_,ss=fit(X,f+e*W[k]); ub[k]=bb[1]-b[1]; ut[k]=(bb[1]-b[1])/ss
        bb,_,ss=fit(X,f0+e0*W[k]); rb[k]=bb[1]; rt[k]=bb[1]/ss
    out['unres_beta']+=np.mean(ub>=b[1])<0.05; out['unres_t']+=np.mean(ut>=t)<0.05
    out['res_beta']+=np.mean(rb>=b[1])<0.05; out['res_t']+=np.mean(rt>=t)<0.05
print('one-sided 5% size, n=27, heavy-tailed leverage on high-vol meetings, R_stmt control:',{k:round(v/R,3) for k,v in out.items()})
