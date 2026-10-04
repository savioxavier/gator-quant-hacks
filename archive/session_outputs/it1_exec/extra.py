import numpy as np, pandas as pd
from scipy.stats import norm
# Gate 4: P(mean of 8 paper events > 0) for per-event Sharpe s
for s in [0,0.1,0.2,0.3,0.5]:
    print("SR/event",s,"P(pass 8-event positive-mean gate)=%.2f"%norm.cdf(s*np.sqrt(8)))
# fat tails in USMPD presser windows 2016+
pc=pd.read_excel(r"<scratch>/fedtalk/data_markets/usmpd/USMPD.xlsx", sheet_name="Press Conferences")
pc["date"]=pd.to_datetime(pc.Date); pc=pc[(pc.date>="2016-01-01")&~pc.date.dt.strftime("%Y-%m-%d").isin(["2020-03-03","2020-03-15"])]
x=pc.SPFUT.dropna(); print("2016+ presser-window SPFUT n",len(x),"sd %.3f%% mean|r| %.3f%% ratio %.2f (normal 0.80) kurt %.1f"%(x.std(),x.abs().mean(),x.abs().mean()/x.std(),x.kurt()))
# netting: answers with real timings; random z ~ N(0,1); rules
a=pd.read_csv("answers.csv"); L=30; H=300
rng=np.random.default_rng(0)
res=[]
for rep in range(200):
    for d,g in a.groupby("date"):
        e=np.sort(g.end.values); z=rng.standard_normal(len(e))
        # (1) separate 1-lot trade per answer
        sep_rt=len(e)
        # max concurrent
        ev=sorted([(t+L,1) for t in e]+[(t+H,-1) for t in e]); c=m=0
        for _,k in ev: c+=k; m=max(m,c)
        # (2) netted path, threshold c: hold sign of latest qualifying z until next decision or expiry
        out={}
        for thr in [0,1]:
            pos=0; trades=0; t_exp=-1
            for t,zz in zip(e,z):
                td=t+L
                if pos!=0 and td>t_exp: trades+=abs(pos); pos=0
                new=np.sign(zz) if abs(zz)>thr else pos
                if abs(zz)>thr:
                    trades+=abs(new-pos); pos=new; t_exp=t+H
            trades+=abs(pos)
            out[thr]=trades/2  # round trips
        res.append(dict(sep_rt=sep_rt,maxconc=m,net_rt_all=out[0],net_rt_z1=out[1]))
r=pd.DataFrame(res); print(r.mean().round(2).to_string())
