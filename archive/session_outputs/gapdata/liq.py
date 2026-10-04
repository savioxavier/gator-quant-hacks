import sys
sys.path.insert(0, r'<solo-repo>')
from data import download_databento as D
import databento as db, pandas as pd
c = db.Historical(D._key())
G=r'<scratch>/gapdata/'
R=pd.read_csv(G+'symb_presser.csv',dtype={'date':str}).set_index('date')
def win(d):
    if d=='20200303': a,b='10:30','13:30'
    elif d=='20200315': a,b='17:30','20:30'
    else: a,b='13:30','16:30'
    s=pd.Timestamp(f'{d} {a}',tz='America/New_York').tz_convert('UTC'); e=pd.Timestamp(f'{d} {b}',tz='America/New_York').tz_convert('UTC')
    return s.isoformat(), e.isoformat()
rows=[]
for d in R.index:
    if R.loc[d,'ZT.c.0']==R.loc[d,'ZT.v.0'] and R.loc[d,'ES.c.0']==R.loc[d,'ES.v.0']: continue
    s,e=win(d); row={'date':d}
    for sym in ['ZT.c.0','ZT.v.0','ES.c.0','ES.v.0']:
        try: row[sym]=c.metadata.get_record_count(dataset='GLBX.MDP3', symbols=[sym], stype_in='continuous', schema='trades', start=s, end=e)
        except Exception as ex: row[sym]=str(ex)[:60]
    rows.append(row)
L=pd.DataFrame(rows).set_index('date'); print(L.to_string())
L.to_csv(G+'liq_trades.csv')
z=L[R.loc[L.index,'ZT.c.0']!=R.loc[L.index,'ZT.v.0']]
print('ZT: median share of trades in .c.0 =', (z['ZT.c.0']/(z['ZT.c.0']+z['ZT.v.0'])).median())
e=L[R.loc[L.index,'ES.c.0']!=R.loc[L.index,'ES.v.0']]
print('ES: median share in .c.0 =', (e['ES.c.0']/(e['ES.c.0']+e['ES.v.0'])).median())
