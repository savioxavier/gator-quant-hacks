import sys, time
sys.path.insert(0, r'<solo-repo>')
from data import download_databento as D
import databento as db, pandas as pd
from concurrent.futures import ThreadPoolExecutor
G=r'<scratch>/gapdata/'
key=D._key()
dates=[l.strip() for l in open(r'<scratch>/fedtalk/data_markets/presser_dates.txt') if l.strip()>='2016']
def win(d):
    if d=='20200303': a,b='10:30','13:30'
    elif d=='20200315': a,b='17:30','20:30'
    else: a,b='13:30','16:30'
    s=pd.Timestamp(f'{d} {a}',tz='America/New_York').tz_convert('UTC'); e=pd.Timestamp(f'{d} {b}',tz='America/New_York').tz_convert('UTC')
    return s.isoformat(), e.isoformat()
sets={'ZT_ES':['ZT.v.0','ES.v.0'],'4':['ZT.v.0','ZF.v.0','ZN.v.0','ES.v.0']}
plan=[('ohlcv-1m','4'),('ohlcv-1s','4'),('bbo-1m','4'),('bbo-1s','4'),('mbp-1','ZT_ES')]
jobs=[(d,sch,k) for d in dates for sch,k in plan]
def run(j):
    d,sch,k=j; s,e=win(d)
    c=db.Historical(key)
    for t in range(3):
        try: return dict(date=d,schema=sch,set=k,usd=c.metadata.get_cost(dataset='GLBX.MDP3', symbols=sets[k], stype_in='continuous', schema=sch, start=s, end=e))
        except Exception as ex: err=str(ex)[:80]; time.sleep(2)
    return dict(date=d,schema=sch,set=k,usd=None,err=err)
with ThreadPoolExecutor(12) as ex: rows=list(ex.map(run, jobs))
R=pd.DataFrame(rows); R.to_csv(G+'cost_2016plus.csv', index=False)
print(R.groupby(['schema','set']).usd.agg(['count','sum','median','max']).round(4))
print('failed', R.usd.isna().sum())
