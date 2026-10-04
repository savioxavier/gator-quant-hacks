"""Step 2: independent wall-clock check of the caption timeline using live TV closed captions.

Source: GDELT Television API 2.0 (https://api.gdeltproject.org/api/v2/tv/tv, mode=clipgallery), which indexes the
Internet Archive TV News Archive closed captions (CNBC, FOX Business, Bloomberg) in caption blocks of ~15 s, each with
a UTC start time; the block text starts at the block start. For each returned block we locate its first words in
the official caption track (VTT, seconds from video zero) and compute
    off = (block start, seconds after scheduled presser start) - (VTT time of those first words)
which estimates V0 + lag - scheduled start, where V0 = wall-clock time of caption-video zero and lag = live TV and
live-caption delay (positive, station specific, a few seconds). The literature convention is V0 = scheduled start
(14:30:00 ET), i.e. off = lag only. Per meeting x station we report the median and spread of off over blocks.
For meetings without captions, the block whose first words are the chair's first words gives the TV time of the open.
Only timing is written to the outputs; caption text stays in the local API cache (src/tv_raw).
Output: s2_tv_gdelt.csv (meeting x station) and s2_tv_blocks.csv (block level).
"""
import os, re, json, time, urllib.request, urllib.parse
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.dirname(os.path.dirname(HERE))
DM = os.path.join(SP, 'fedtalk', 'data_markets')
RAW = os.path.join(HERE, 'src', 'tv_raw'); os.makedirs(RAW, exist_ok=True)
B = pd.read_csv(os.path.join(HERE, 's1_calendar_vtt.csv'), dtype={'date_key': str})
if os.environ.get('ONLY'):
    B = B[B.date_key.isin(os.environ['ONLY'].split(','))]
WPS = 1 / 3.0  # seconds per word, used only to back out the position of the first matched word inside a block

def ts(s):
    p = [float(x) for x in s.split(':')]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]

STOP = set('the a an and of to in for on at by with that this is are be as it we our has have was were from or but not '
           'i you they he she will would can could there their about so very more also been what which'.split())

def norm(s):
    s = s.lower().replace('%', ' percent ')
    return re.findall(r"[a-z]+", s)

def vtt_words(d):
    raw = open(os.path.join(DM, 'vtt', d + '.vtt'), encoding='utf-8').read()
    W = []
    for a, b, body in re.findall(r'([\d:.]+) --> ([\d:.]+)[^\n]*\n(.*?)(?:\n\n|\Z)', raw, flags=re.S):
        body = ' '.join(body.split())
        if re.fullmatch(r"(?:\d{4} )?(?:[A-Z][A-Z'\-]+\.? ){0,3}[A-Z][A-Z'\-]+[.:]", body) or 'Transcript of' in body \
                or 'Press Conference' in body or re.search(r'Page \d+ of', body):
            continue
        body = re.sub(r"\b(?:\d{4} )?(?:CHAIR(?:MAN)?|MR\.|MS\.) ?[A-Z]+[.:]", ' ', body)
        toks = norm(body)
        s, e = ts(a), ts(b)
        for i, tk in enumerate(toks):
            W.append((s + (e - s) * i / max(len(toks), 1), tk))
    return W

def pick_phrases(W, t0, t1, n=10):
    cands = []
    for i in range(len(W) - 3):
        t = W[i][0]
        if not (t0 <= t < t1):
            continue
        ws = [w for _, w in W[i:i + 4]]
        if sum((w not in STOP) and len(w) >= 6 for w in ws) < 2 or 'percent' in ws:
            continue
        cands.append((t, ' '.join(ws)))
    out, slot = [], (t1 - t0) / n
    for k in range(n):
        c = [x for x in cands if t0 + k * slot <= x[0] < t0 + (k + 1) * slot]
        if c:
            out.append(c[len(c) // 2])
    return out

def gdelt(query, start, end, tag):
    f = os.path.join(RAW, tag + '.json')
    if os.path.exists(f):
        js = json.load(open(f, encoding='utf-8'))
        if not (isinstance(js, dict) and 'error' in js and 'too common' not in js['error']):
            return js
    u = 'https://api.gdeltproject.org/api/v2/tv/tv?' + urllib.parse.urlencode(dict(
        query=query, mode='clipgallery', format='json', maxrecords=50,
        startdatetime=start.strftime('%Y%m%d%H%M%S'), enddatetime=end.strftime('%Y%m%d%H%M%S')))
    js = {'error': 'not fetched'}
    for k in range(4):
        try:
            txt = urllib.request.urlopen(u, timeout=90).read().decode('utf-8', 'ignore')
            js = json.loads(txt) if txt.strip().startswith('{') else {'error': txt[:200]}
            if 'error' in js and ('limit' in js['error'].lower() or 'please' in js['error'].lower()):
                time.sleep(10); continue
            break
        except Exception as e:
            js = {'error': str(e)}; time.sleep(8)
    json.dump(js, open(f, 'w', encoding='utf-8'))
    time.sleep(3)
    return js

STATIONS = os.environ.get('STATIONS', 'CNBC,FBC,BLOOMBERG').split(',')
B = B[B.date_key <= os.environ.get('MAXDATE', '20241130')]
rows, blocks = [], []
for _, r in B.iterrows():
    d = r.date_key
    sched = pd.Timestamp(f"{r.date} {r.presser_sched_et}", tz='America/New_York')
    win0, win1 = (sched - pd.Timedelta('20min')).tz_convert('UTC'), (sched + pd.Timedelta('40min')).tz_convert('UTC')
    has_vtt = r.has_captions == 1
    if has_vtt:
        W = vtt_words(d)
        idx = {}
        for i in range(len(W) - 3):
            idx.setdefault(' '.join(w for _, w in W[i:i + 4]), []).append(i)
        ph = pick_phrases(W, r.greeting_s, r.greeting_s + 240, n=10)
        q = '(' + ' OR '.join(f'"{p}"' for _, p in ph) + ')'
    else:
        txt = open(os.path.join(DM, 'pdf', f'FOMCpresconf{d}.txt'), encoding='utf-8', errors='replace').read()
        m = re.search(r'CHAIR(?:MAN)? [A-Z]+[.:]\s*(.{0,1500})', txt, flags=re.S)
        PW = norm(m.group(1))
        pidx = {}
        for i in range(len(PW) - 3):
            pidx.setdefault(' '.join(PW[i:i + 4]), []).append(i)
        cand = [' '.join(PW[i:i + 4]) for i in range(0, 60) if sum((w not in STOP) and len(w) >= 6 for w in PW[i:i + 4]) >= 2]
        ph = [(np.nan, c) for c in cand[::3][:8]]
        q = '(' + ' OR '.join(f'"{p}"' for _, p in ph) + ')'
    for st in STATIONS:
        js = gdelt(f'{q} station:{st}', win0, win1, f'{d}_{st}')
        clips = js.get('clips', []) if isinstance(js, dict) else []
        offs, opens = [], []
        for c in clips:
            b = pd.Timestamp(c['date']).tz_convert('America/New_York')
            bs = (b - sched).total_seconds()
            sn = norm(c.get('snippet', ''))
            if has_vtt:
                for j in range(0, min(10, len(sn) - 3)):
                    occ = idx.get(' '.join(sn[j:j + 4]), [])
                    occ = [i for i in occ if -240 <= bs - W[i][0] <= 300]
                    if len(occ) == 1:
                        tv = W[occ[0]][0] - j * WPS
                        offs.append(bs - tv)
                        blocks.append(dict(date_key=d, station=st, block_et=b.strftime('%H:%M:%S'), vtt_t=round(tv, 2),
                                           off_s=round(bs - tv, 2), j=j))
                        break
            else:
                for j in range(0, min(10, len(sn) - 3)):
                    occ = pidx.get(' '.join(sn[j:j + 4]), [])
                    if occ:
                        k = occ[0] + 0  # word index of block start inside the opening text
                        opens.append((bs - j * WPS, k))
                        blocks.append(dict(date_key=d, station=st, block_et=b.strftime('%H:%M:%S'), pdf_word=k, j=j))
                        break
        rec = dict(date_key=d, station=st, n_query_phrases=len(ph), n_clips=len(clips), n_used=len(offs) or len(opens),
                   api_note=(js.get('error') or '')[:60] if isinstance(js, dict) else '')
        if offs:
            o = np.array(offs)
            med = float(np.median(o))
            rec.update(off_median_s=round(med, 1), off_mad_s=round(float(np.median(np.abs(o - med))), 1),
                       off_min_s=round(float(o.min()), 1), off_max_s=round(float(o.max()), 1))
        if opens:
            # regress block time on word index to extrapolate to word 0 (the chair's first word)
            a = np.array(opens, dtype=float)
            if len(a) >= 3 and np.ptp(a[:, 1]) > 20:
                sl, ic = np.polyfit(a[:, 1], a[:, 0], 1)
            else:
                ic = float(np.min(a[:, 0] - a[:, 1] * WPS))
            rec.update(tv_open_minus_sched_s=round(float(ic), 1), n_open_blocks=len(a))
        rows.append(rec)
    print(d, [(x['station'], x['n_used'], x.get('off_median_s'), x.get('off_mad_s'), x.get('tv_open_minus_sched_s'), x['api_note'][:30])
              for x in rows if x['date_key'] == d], flush=True)

R = pd.DataFrame(rows)
TAG = os.environ.get('TAG', '')
R.to_csv(os.path.join(HERE, f's2_tv_gdelt{TAG}.csv'), index=False)
pd.DataFrame(blocks).to_csv(os.path.join(HERE, f's2_tv_blocks{TAG}.csv'), index=False)
print(R.groupby('station')[['off_median_s', 'off_mad_s', 'tv_open_minus_sched_s']].describe().T)
