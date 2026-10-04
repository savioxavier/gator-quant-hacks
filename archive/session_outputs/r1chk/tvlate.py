"""Compare TV-archive offsets (true wall - (VTT + 14:30)) by presser minute, using the 14:00 ET item and the
15:00 ET item, to test whether a single offset fitted on minutes 5-30 holds at the end of the presser."""
import re,html,json,os,sys,time,urllib.request
import pandas as pd, numpy as np
FV='<scratch>/fedtalk/data_markets'
CACHE='tvcache'; os.makedirs(CACHE,exist_ok=True)
def ts(s):
    p=[float(x) for x in s.split(':')]; return p[0]*3600+p[1]*60+p[2] if len(p)==3 else p[0]*60+p[1]
def norm(t): return re.findall(r"[a-z0-9]+", t.lower())
def tri(ws): return {' '.join(ws[i:i+3]) for i in range(len(ws)-2)}
def get(url,fn):
    p=os.path.join(CACHE,fn)
    if os.path.exists(p): return open(p,encoding='utf-8').read()
    t=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=90).read().decode('utf-8','ignore')
    open(p,'w',encoding='utf-8').write(t); return t
def segs(ident):
    t=get(f"https://archive.org/details/{ident}",f"{ident}.html")
    return [(int(k),' '.join(html.unescape(re.sub(r'<[^>]+>',' ',s)).split())) for k,s in re.findall(r'_(\d{6})\.jpg"/>(.*?)(?=_\d{6}\.jpg"/>|\Z)', t, flags=re.S)]
v=pd.read_csv(FV+'/vtt_summary.csv',dtype={'date':str}).set_index('date')
q=pd.read_csv('<solo-repo>/research/fed_presser_plan/evidence/it1_data_eng/vtt_quality.csv',dtype={'date':str}).set_index('date')
LAG=15.0
out=[]
for d,idents in [a.split('=') for a in sys.argv[1:]]:
    conv0=pd.Timestamp(f"{d} 14:30",tz='America/New_York')
    txt=open(f"{FV}/vtt/{d}.vtt",encoding='utf-8').read()
    C=[(ts(a),' '.join(t.split())) for a,b,t in re.findall(r'([\d:.]+) --> ([\d:.]+)[^\n]*\n(.*?)(?:\n\n|\Z)',txt,flags=re.S)]
    g=v.loc[d,'greeting_s']; cues=[(a,t) for a,t in C if a>=g-1 and len(norm(t))>=5]
    offs=[]
    for ident in idents.split(','):
        hh=ident.split('_')[2]; st=pd.Timestamp(f"{d} {hh[:2]}:{hh[2:4]}:{hh[4:6]}",tz='UTC')
        ST=[(k,tri(norm(x))) for k,x in segs(ident)]
        for a,t in cues:
            tt=tri(norm(t))
            if len(tt)<3: continue
            sc=[(len(tt&s),k) for k,s in ST]; m,k=max(sc)
            if m<3 or sorted([x for x,_ in sc])[-2]>=m: continue
            conv=(conv0+pd.Timedelta(seconds=a)).tz_convert('UTC'); seg0=st+pd.Timedelta(seconds=k)
            offs.append((ident.split('_')[3], a, (seg0-pd.Timedelta(seconds=LAG)-conv).total_seconds(), (seg0+pd.Timedelta(seconds=60)-conv).total_seconds()))
    O=pd.DataFrame(offs,columns=['item','a','lo','hi'])
    O['bin']=(O.a//600*10).astype(int)
    vs=q.loc[d,'video_s']
    for (it,b),G in O.groupby(["item","bin"]):
        if len(G)<5: continue
        lo=np.percentile(G.lo,80); hi=np.percentile(G.hi,20)
        out.append(dict(date=d,min_bin=b,items=it,n=len(G),lo=round(lo,1),hi=round(hi,1),mid=round((lo+hi)/2,1),video_min=round(vs/60,1),overrun=q.loc[d,'overrun_s']))
R=pd.DataFrame(out); pd.set_option('display.width',200); print(R.to_string(index=False))
R.to_csv('tvlate_out.csv',index=False)
