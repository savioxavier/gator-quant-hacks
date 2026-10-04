import sys, json
sys.path.insert(0, r'<solo-repo>')
from data import download_databento as D
import databento as db
import pandas as pd
c = db.Historical(D._key())
dates=[l.strip() for l in open(r'<scratch>/fedtalk/data_markets/presser_dates.txt') if l.strip()>='2016']
dates += ['20261028','20261209']
out={}
for sym in ['ZT.c.0','ZT.v.0','ZT.n.0','ES.c.0','ES.v.0','ZN.c.0','ZN.v.0']:
    r = c.symbology.resolve(dataset='GLBX.MDP3', symbols=[sym], stype_in='continuous', stype_out='instrument_id', start_date='2016-01-01', end_date='2026-10-03')
    m = r['result'][sym]
    out[sym]=m
json.dump(out, open(r'<scratch>/gapdata/symb.json','w'))
def at(m, d):
    d=pd.Timestamp(d)
    for iv in m:
        if pd.Timestamp(iv['d0'])<=d<pd.Timestamp(iv['d1']): return iv['s']
    return None
rows=[]
for d in dates[:-2]:
    rows.append({k: at(out[k], d) for k in out} | {'date':d})
R=pd.DataFrame(rows).set_index('date')
for root in ['ZT','ES','ZN']:
    diff = R[R[f'{root}.c.0']!=R[f'{root}.v.0']]
    print(root, 'presser days where .c.0 != .v.0:', len(diff), 'of', len(R), diff.index.tolist())
print((R['ZT.v.0']!=R['ZT.n.0']).sum(), 'ZT days v!=n')
R.to_csv(r'<scratch>/gapdata/symb_presser.csv')
