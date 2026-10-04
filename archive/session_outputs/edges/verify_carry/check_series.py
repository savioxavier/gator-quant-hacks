import pandas as pd, numpy as np, json, math, glob, os
S="<scratch>/edges/series/"
def sr(x): x=x.dropna(); return x.mean()/x.std()*math.sqrt(252)
def mdd(x): e=(1+x.fillna(0)).cumprod(); return (e/e.cummax()-1).min()
def nw(x,L=None):
    x=x.dropna().values; n=len(x); L=L or int(4*(n/100)**(2/9)); e=x-x.mean(); s=e@e/n
    for k in range(1,L+1): s+=2*(1-k/(L+1))*(e[k:]@e[:-k])/n
    return x.mean()/math.sqrt(s/n)
for f in sorted(glob.glob(S+"carry_*.parquet")):
    d=pd.read_parquet(f); n=os.path.basename(f)[:-8]
    IS=d.loc[:"2024-10-02"]; L=d.loc["2024-10-03":]
    yr=(1+IS.net_1x).groupby(IS.index.year).prod()-1; cnt=IS.net_1x.groupby(IS.index.year).size(); yr=yr[cnt>=126]
    r2=(IS.net_1x.rolling(504).mean()/IS.net_1x.rolling(504).std()*math.sqrt(252)).dropna()
    print(f"{n:18s} {IS.index[0].date()}..{IS.index[-1].date()} n={len(IS)} IS1x={sr(IS.net_1x):.3f} 2x={sr(IS.net_2x):.3f} g={sr(IS.gross):.3f} mdd={mdd(IS.net_1x):.3f} nw={nw(IS.net_1x):.2f} pos={ (yr>0).mean():.3f} r2p10={r2.quantile(.1):.3f} vol={IS.net_1x.std()*math.sqrt(252):.3f} | LATER {L.index[0].date()}..{L.index[-1].date()} {sr(L.net_1x):.3f} nans={d.isna().sum().sum()}")
