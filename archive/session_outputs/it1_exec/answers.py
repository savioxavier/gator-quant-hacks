import re, glob, os, numpy as np, pandas as pd
root = r"<scratch>/fedtalk/data_markets/vtt"
ts = re.compile(r"^(?:(\d+):)?(\d+):(\d+\.\d+)\s+-->\s+(?:(\d+):)?(\d+):(\d+\.\d+)")
lab = re.compile(r"((?:CHAIR(?:MAN)?|VICE CHAIR)?\s*[A-Z][A-Z\.\-' ]{2,40}?)\.\s")
def secs(h,m,s): return (int(h) if h else 0)*3600+int(m)*60+float(s)
rows=[]
for f in sorted(glob.glob(root+"/*.vtt")):
    d=os.path.basename(f)[:8]
    cues=[]; cur=None
    for line in open(f,encoding="utf-8"):
        line=line.rstrip("\n")
        m=ts.match(line)
        if m:
            cur=[secs(*m.groups()[:3]),secs(*m.groups()[3:]),""]; cues.append(cur); continue
        if cur is not None and line.strip(): cur[2]+=" "+line.strip()
    # speaker turns: find label tokens in cue text
    turns=[]; spk=None; start=None
    for a,b,t in cues:
        for mm in re.finditer(r"\b(CHAIR(?:MAN)? [A-Z]+|MICHELLE SMITH|MS\. SMITH|[A-Z]{2,}(?: [A-Z]{2,}){1,2})\.", t):
            name=mm.group(1)
            if name!=spk:
                if spk is not None: turns.append([spk,start,a])
                spk=name; start=a
        last=b
    if spk is not None: turns.append([spk,start,last])
    ch=[x for x in turns if x[0].startswith("CHAIR")]
    if len(ch)<3: continue
    # first chair turn = opening statement; the rest = answers
    for i,(s,a,b) in enumerate(ch[1:]):
        rows.append(dict(date=d,i=i,start=a,end=b,dur=b-a))
df=pd.DataFrame(rows)
df=df[df.dur>=10]  # drop very short interjections
print("pressers",df.date.nunique(),"answers",len(df))
print("answer duration s: median %.0f  p25 %.0f p75 %.0f"%(df.dur.median(),df.dur.quantile(.25),df.dur.quantile(.75)))
out=[]
for d,g in df.groupby("date"):
    g=g.sort_values("start"); s=g.start.values; e=g.end.values
    nxt_start=np.r_[s[1:],np.nan]
    gap=nxt_start-e
    # H1 window [e+30, e+300]; count other answers' H1 windows overlapping each
    W0=e+30; W1=e+300
    conc=[((W0<W1[j])&(W0[j]<W1)).sum()-1 for j in range(len(g))]
    # max concurrent windows at any instant
    ev=sorted([(x,1) for x in W0]+[(x,-1) for x in W1]); c=0; mx=0
    for _,k in ev: c+=k; mx=max(mx,c)
    # does next answer start before e+30 (i.e., entry happens while next answer in progress)?
    nxt_in_window = ((nxt_start>e)&(nxt_start<W1)).mean()
    out.append(dict(date=d,n=len(g),gap_med=np.nanmedian(gap),conc_mean=np.mean(conc),max_conc=mx,
                    end_last=e.max(), frac_next_starts_before_entry=np.nanmean(nxt_start<W0)))
o=pd.DataFrame(out)
print(o.describe().round(2).to_string())
print("median gap answer end -> next answer start (s):",round(np.nanmedian(np.concatenate([ (g.sort_values('start').start.values[1:]-g.sort_values('start').end.values[:-1]) for _,g in df.groupby('date')])),1))
print("share of answers whose H1 window (end+30..end+300) overlaps >=1 other answer's H1 window:",
      round(np.mean([c>0 for d,g in df.groupby('date') for c in [0]]),2))
df.to_csv(r"<scratch>/it1_exec/answers.csv",index=False)
o.to_csv(r"<scratch>/it1_exec/presser_overlap.csv",index=False)
