import re, glob, os, pandas as pd, numpy as np
base = r'<scratch>/fedtalk/data_markets'
def ts(s):
    p=[float(x) for x in s.split(':')]; return p[0]*3600+p[1]*60+p[2] if len(p)==3 else p[0]*60+p[1]
out=[]
for f in sorted(glob.glob(os.path.join(base,'vtt','*.vtt'))):
    d=os.path.basename(f)[:8]
    txt=open(f,encoding='utf-8').read()
    for a,b,t in re.findall(r'([\d:.]+) --> ([\d:.]+)[^\n]*\n(.*?)(?:\n\n|\Z)',txt,flags=re.S):
        t=' '.join(t.split())
        m=re.search(r"\b(CHAIR(?:MAN)? [A-Z]+|MICHELLE SMITH|MR\. [A-Z]+|MS\. [A-Z]+)\.", t)
        if m or re.fullmatch(r"[A-Z][A-Z .'\-]+\.", t):
            out.append((d,ts(a),ts(b),t))
L=pd.DataFrame(out,columns=['date','s','e','t']); L['dur']=L.e-L.s
L['chair']=L.t.str.contains('CHAIR')
print('label cues', len(L), 'chair', L.chair.sum())
print('chair label cue duration quantiles', L[L.chair].dur.quantile([.5,.75,.9,.95,.99]).round(2).to_dict())
print('label cues that also contain spoken text (label embedded mid-cue):', (~L.t.str.fullmatch(r"(?:\d{4} )?[A-Z][A-Z .'\-]+\.")).sum())
print(L[~L.t.str.fullmatch(r"(?:\d{4} )?[A-Z][A-Z .'\-]+\.")].head(8).to_string())
L['y']=L.date.str[:4].astype(int)
print(L[L.chair].groupby(L.y>=2016).dur.describe())
