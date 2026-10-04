import re, os
base = r'<scratch>/fedtalk/data_markets/vtt'
def ts(s):
    p=[float(x) for x in s.split(':')]; return p[0]*3600+p[1]*60+p[2] if len(p)==3 else p[0]*60+p[1]
for d in ['20190501','20210317','20221102','20230201','20240131','20240918']:
    txt=open(os.path.join(base,d+'.vtt'),encoding='utf-8').read()
    C=[(ts(a),ts(b),' '.join(t.split())) for a,b,t in re.findall(r'([\d:.]+) --> ([\d:.]+)[^\n]*\n(.*?)(?:\n\n|\Z)',txt,flags=re.S)]
    st=[(round(a),round(b-a,1),t[:45]) for a,b,t in C if b-a>8 and len(t.split())/(b-a)<0.6 and not re.fullmatch(r"(?:\d{4} )?[A-Z][A-Z .'\-]+\.",t)]
    # first Q&A label time
    qa=[a for a,b,t in C if 'MICHELLE SMITH' in t]
    print(d, 'stretched (start_s, dur_s, text):', st, '| first MICHELLE SMITH cue at', round(qa[0]) if qa else None)
