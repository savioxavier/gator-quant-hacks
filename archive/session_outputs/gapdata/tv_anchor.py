"""Independent minute-level wall-clock check of the 'video zero = 14:30:00 ET' convention.
For each captioned presser, match Fed WebVTT cues (video clock) to Internet Archive TV News Archive
CNBC caption segments (60 s segments at known broadcast offsets from a UTC program start)."""
import re, html, json, os, sys, time, urllib.request, glob
import pandas as pd, numpy as np
FV = r'<scratch>/fedtalk/data_markets'
OUT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(OUT, 'tvcache'); os.makedirs(CACHE, exist_ok=True)
def ts(s):
    p=[float(x) for x in s.split(':')]; return p[0]*3600+p[1]*60+p[2] if len(p)==3 else p[0]*60+p[1]
def norm(t): return re.findall(r"[a-z0-9]+", t.lower())
def tri(ws): return {' '.join(ws[i:i+3]) for i in range(len(ws)-2)}
def get(url, fn):
    p=os.path.join(CACHE, fn)
    if os.path.exists(p): return open(p, encoding='utf-8').read()
    for k in range(3):
        try:
            t=urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'}), timeout=90).read().decode('utf-8','ignore'); break
        except Exception as e:
            t=None; time.sleep(3)
    if t is None: return None
    open(p,'w',encoding='utf-8').write(t); return t
def items(d, ch):
    t=get(f"https://archive.org/advancedsearch.php?q=identifier%3A{ch}_{d}*&fl%5B%5D=identifier&rows=60&output=json", f"s_{ch}_{d}.json")
    return [x['identifier'] for x in json.loads(t)['response']['docs']] if t else []
def segs(ident):
    t=get(f"https://archive.org/details/{ident}", f"{ident}.html")
    if not t: return []
    return [(int(k),' '.join(html.unescape(re.sub(r'<[^>]+>',' ',s)).split())) for k,s in re.findall(r'_(\d{6})\.jpg"/>(.*?)(?=_\d{6}\.jpg"/>|\Z)', t, flags=re.S)]
v=pd.read_csv(FV+'/vtt_summary.csv', dtype={'date':str}).set_index('date')
dates=[d for d in v.index if d>='2016' and v.loc[d,'captions']]
if len(sys.argv)>1: dates=[d for d in dates if d in sys.argv[1:]]
LAG=15.0  # max caption + broadcast lag assumed (s)
rows=[]
for d in dates:
    sched = '11:00' if d=='20200303' else ('18:30' if d=='20200315' else '14:30')
    conv0 = pd.Timestamp(f"{d} {sched}", tz='America/New_York')
    txt=open(f"{FV}/vtt/{d}.vtt",encoding='utf-8').read()
    C=[(ts(a),' '.join(t.split())) for a,b,t in re.findall(r'([\d:.]+) --> ([\d:.]+)[^\n]*\n(.*?)(?:\n\n|\Z)',txt,flags=re.S)]
    g=v.loc[d,'greeting_s']
    cues=[(a,t) for a,t in C if a>=g-1 and len(norm(t))>=5]
    best=None
    for ch in ['CNBC','FBC','BLOOMBERG']:
        for ident in items(d, ch):
            hh=ident.split('_')[2]; st=pd.Timestamp(f"{d} {hh[:2]}:{hh[2:4]}:{hh[4:6]}", tz='UTC')
            # program must start within 2 h before the scheduled presser start
            dt=(conv0.tz_convert('UTC')-st).total_seconds()
            if not (0 <= dt <= 7200): continue
            S=segs(ident)
            if not S: continue
            ST=[(k, tri(norm(x))) for k,x in S]
            lo, hi, n = -1e9, 1e9, 0; offs=[]
            for a,t in cues:
                tt=tri(norm(t))
                if len(tt)<3: continue
                sc=[(len(tt & s), k) for k,s in ST]
                m,k=max(sc)
                if m < 3: continue
                # require the match to be unique-ish
                if sorted([x for x,_ in sc])[-2] >= m: continue
                conv = (conv0 + pd.Timedelta(seconds=a)).tz_convert('UTC')
                seg0 = st + pd.Timedelta(seconds=k)
                l=(seg0 - pd.Timedelta(seconds=LAG) - conv).total_seconds(); h=(seg0 + pd.Timedelta(seconds=60) - conv).total_seconds()
                offs.append((a, l, h))
            if len(offs) >= 5:
                O=np.array(offs)
                # robust intersection: use 20th pct of lower bounds and 80th of upper to resist mismatches
                early=O[O[:,0] < g+300]; late=O[O[:,0] >= g+300]
                def inter(X):
                    if len(X)<3: return (np.nan,np.nan,len(X))
                    return (np.percentile(X[:,1],80), np.percentile(X[:,2],20), len(X))
                e=inter(early); L=inter(late)
                cand=dict(date=d, ident=ident, n_match=len(O), early_lo=e[0], early_hi=e[1], n_early=e[2], late_lo=L[0], late_hi=L[1], n_late=L[2])
                if best is None or len(O)>best['n_match']: best=cand
        if best: break
    if best is None: best=dict(date=d, ident=None, n_match=0)
    best['greeting_s']=g; best['overrun_s']=None
    rows.append(best); print(best, flush=True)
R=pd.DataFrame(rows); R.to_csv(os.path.join(OUT,'tv_anchor.csv'), index=False)
