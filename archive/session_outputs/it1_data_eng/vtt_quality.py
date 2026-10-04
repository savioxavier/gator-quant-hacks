import re, glob, os, pandas as pd, numpy as np
base = r'<scratch>/fedtalk/data_markets'
meta = pd.read_csv(os.path.join(base, 'video_meta.csv'), dtype={'date': str}).set_index('date')
def ts(s):
    p = s.split(':'); p = [float(x) for x in p]
    return p[0]*3600+p[1]*60+p[2] if len(p) == 3 else p[0]*60+p[1]
rows = []
allcues = []
for f in sorted(glob.glob(os.path.join(base, 'vtt', '*.vtt'))):
    d = os.path.basename(f)[:8]
    txt = open(f, encoding='utf-8').read()
    cues = re.findall(r'([\d:.]+) --> ([\d:.]+)[^\n]*\n(.*?)(?:\n\n|\Z)', txt, flags=re.S)
    C = []
    for a, b, t in cues:
        t = ' '.join(t.split())
        C.append((ts(a), ts(b), t, len(t.split())))
    df = pd.DataFrame(C, columns=['s', 'e', 'text', 'nw']); df['dur'] = df.e - df.s
    df['wps'] = df.nw / df.dur.replace(0, np.nan)
    df['label'] = df.text.str.fullmatch(r"(?:\d{4} )?[A-Z][A-Z .'\-]+\.") 
    df['pagehdr'] = df.text.str.contains(r'Page \d+ of \d+|FINAL', regex=True)
    sp = df[~df.label & ~df.pagehdr]
    dur = meta.loc[d, 'duration_s']
    stretched = sp[(sp.dur > 8) & (sp.wps < 0.6)]
    gaps = (df.s.shift(-1) - df.e).dropna()
    nonmono = int((df.s.diff() < -0.001).sum())
    rows.append(dict(date=d, n=len(df), video_s=dur, last_end=df.e.max(), overrun_s=round(df.e.max() - dur, 1),
                     cues_after_end=int((df.s > dur).sum()), med_wps=round(sp.wps.median(), 2),
                     n_stretched=len(stretched), stretched_s=round(stretched.dur.sum(), 1),
                     max_cue_s=round(sp.dur.max(), 1), pagehdr=int(df.pagehdr.sum()), nonmono=nonmono,
                     max_gap=round(gaps.max(), 1)))
    df['date'] = d; allcues.append(df)
R = pd.DataFrame(rows)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
print(R.to_string())
A = pd.concat(allcues)
sp = A[~A.label & ~A.pagehdr]
print('\nall speech cues', len(sp), 'median dur', sp.dur.median(), 'p95', sp.dur.quantile(.95), 'p99', sp.dur.quantile(.99))
print('median wps', sp.wps.median(), 'cues >8s with <0.6 wps:', ((sp.dur>8)&(sp.wps<0.6)).sum(), 'total s', sp[(sp.dur>8)&(sp.wps<0.6)].dur.sum())
print('meetings with overrun > 10 s:', (R.overrun_s > 10).sum(), R[R.overrun_s > 10].date.tolist())
print('meetings with cues starting after video end:', (R.cues_after_end > 0).sum())
R.to_csv(os.path.join(os.path.dirname(__file__), 'vtt_quality.csv'), index=False)
