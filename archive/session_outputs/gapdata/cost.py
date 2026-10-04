import sys, time
sys.path.insert(0, r'<solo-repo>')
from data import download_databento as D
import databento as db, pandas as pd
c = db.Historical(D._key())
G=r'<scratch>/gapdata/'
dates=[l.strip() for l in open(r'<scratch>/fedtalk/data_markets/presser_dates.txt') if l.strip()>='2016']
def win(d):
    if d=='20200303': a,b='10:30','13:30'
    elif d=='20200315': a,b='17:30','20:30'
    else: a,b='13:30','16:30'
    s=pd.Timestamp(f'{d} {a}',tz='America/New_York').tz_convert('UTC'); e=pd.Timestamp(f'{d} {b}',tz='America/New_York').tz_convert('UTC')
    return s.isoformat(), e.isoformat()
sets={'ZT':['ZT.v.0'],'ZT_ES':['ZT.v.0','ES.v.0'],'4':['ZT.v.0','ZF.v.0','ZN.v.0','ES.v.0']}
plan=[('ohlcv-1m','4'),('ohlcv-1s','4'),('bbo-1m','4'),('bbo-1s','4'),('bbo-1s','ZT_ES'),('mbp-1','ZT_ES'),('tbbo','ZT_ES')]
rows=[]
for d in dates:
    s,e=win(d)
    for sch,k in plan:
        for t in range(3):
            try:
                usd=c.metadata.get_cost(dataset='GLBX.MDP3', symbols=sets[k], stype_in='continuous', schema=sch, start=s, end=e); break
            except Exception as ex:
                usd=None; time.sleep(2)
        rows.append(dict(date=d, schema=sch, set=k, usd=usd))
R=pd.DataFrame(rows); R.to_csv(G+'cost_2016plus.csv', index=False)
print(R.groupby(['schema','set']).usd.agg(['count','sum','median','max']).round(4))
print('failed', R.usd.isna().sum())
