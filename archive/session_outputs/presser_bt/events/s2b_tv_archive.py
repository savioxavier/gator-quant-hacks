"""Step 2b: wall-clock check from Internet Archive TV News item pages (https://archive.org/details/<item>).

Each TV item (e.g. CNBC_20190731_180000_Power_Lunch, start time in UTC in the identifier and in item metadata
start_time) has a details page that lists the closed captions in ~60 s segments keyed by the second offset of the
segment thumbnail. For each segment we locate its first words in the official caption track (VTT time t, seconds from
video zero) and compute off = (item start + segment offset - scheduled presser start) - t, i.e. V0 - scheduled start
plus the TV delay as represented on the archive page. For meetings without captions, segments are matched to the
transcript opening to give the TV time of the chair's first word.
Only timing is written to outputs; page HTML stays in the local cache src/tv_archive.
Output: s2b_tv_archive.csv (meeting x station) and s2b_tv_archive_segments.csv.
"""
import os, re, json, time, html, urllib.request, urllib.parse
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.dirname(os.path.dirname(HERE))
DM = os.path.join(SP, 'fedtalk', 'data_markets')
CACHE = os.path.join(HERE, 'src', 'tv_archive'); os.makedirs(CACHE, exist_ok=True)
B = pd.read_csv(os.path.join(HERE, 's1_calendar_vtt.csv'), dtype={'date_key': str})
if os.environ.get('ONLY'):
    B = B[B.date_key.isin(os.environ['ONLY'].split(','))]
STATIONS = os.environ.get('STATIONS', 'CNBC,FBC,BLOOMBERG').split(',')
WPS = 1 / 3.0

def ts(s):
    p = [float(x) for x in s.split(':')]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]

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

def get(url, f, tries=4):
    if os.path.exists(f) and os.path.getsize(f) > 1000:
        return open(f, encoding='utf-8', errors='ignore').read()
    for k in range(tries):
        try:
            t = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'research-script'}), timeout=120).read().decode('utf-8', 'ignore')
            open(f, 'w', encoding='utf-8').write(t)
            time.sleep(1.0)
            return t
        except Exception as e:
            time.sleep(5)
    return ''

def items(st, d):
    f = os.path.join(CACHE, f'search_{st}_{d}.json')
    u = f'https://archive.org/advancedsearch.php?q=identifier%3A{st}_{d}*&fl%5B%5D=identifier&rows=100&output=json'
    t = get(u, f)
    if not t.strip().startswith('{'):
        try: os.remove(f)
        except OSError: pass
        return []
    try:
        return [x['identifier'] for x in json.loads(t)['response']['docs']]
    except Exception:
        return []

def segments(ident):
    t = get(f'https://archive.org/details/{ident}', os.path.join(CACHE, ident + '.html'))
    segs = re.findall(r'_(\d{6})\.jpg"/>(.*?)(?=_\d{6}\.jpg"/>|\Z)', t, flags=re.S)
    out = []
    for k, s in segs:
        s = html.unescape(re.sub(r'<[^>]+>', ' ', s))
        s = re.sub(r'\b\d{1,2}:\d{2} [ap]m\b', ' ', s)
        out.append((int(k), ' '.join(s.split())))
    return out

rows, segrows = [], []
for _, r in B.iterrows():
    d = r.date_key
    sched = pd.Timestamp(f"{r.date} {r.presser_sched_et}", tz='America/New_York')
    w0, w1 = sched - pd.Timedelta('15min'), sched + pd.Timedelta('70min')
    has_vtt = r.has_captions == 1
    if has_vtt:
        W = vtt_words(d)
        idx = {}
        for i in range(len(W) - 3):
            idx.setdefault(' '.join(w for _, w in W[i:i + 4]), []).append(i)
    txt = open(os.path.join(DM, 'pdf', f'FOMCpresconf{d}.txt'), encoding='utf-8', errors='replace').read()
    m = re.search(r'CHAIR(?:MAN)? [A-Z]+[.:]\s*(.{0,3000})', txt, flags=re.S)
    PW = norm(m.group(1)) if m else []
    pidx = {}
    for i in range(len(PW) - 3):
        pidx.setdefault(' '.join(PW[i:i + 4]), []).append(i)
    for st in STATIONS:
        ids = []
        for ident in items(st, d):
            mm = re.match(rf'{st}_(\d{{8}})_(\d{{6}})_', ident)
            if not mm:
                continue
            t0 = pd.Timestamp(mm.group(1) + mm.group(2), tz='UTC').tz_convert('America/New_York')
            if t0 < w1 and t0 + pd.Timedelta('185min') > w0:
                ids.append((t0, ident))
        offs, opens = [], []
        for t0, ident in sorted(ids):
            S = segments(ident)
            for k, s in S:
                tabs = t0 + pd.Timedelta(seconds=k)
                if not (w0 <= tabs <= w1):
                    continue
                sn = norm(s)
                bs = (tabs - sched).total_seconds()
                if has_vtt:
                    for j in range(0, min(12, len(sn) - 3)):
                        occ = [i for i in idx.get(' '.join(sn[j:j + 4]), []) if -200 <= bs - W[i][0] <= 300]
                        if len(occ) == 1:
                            tv = W[occ[0]][0] - j * WPS
                            offs.append(bs - tv)
                            segrows.append(dict(date_key=d, station=st, item=ident, seg_s=k, seg_et=tabs.strftime('%H:%M:%S'),
                                                vtt_t=round(tv, 2), off_s=round(bs - tv, 2), j=j))
                            break
                for j in range(0, min(12, len(sn) - 3)):
                    occ = pidx.get(' '.join(sn[j:j + 4]), [])
                    if occ and occ[0] < 600:
                        opens.append((bs - j * WPS, occ[0]))
                        if not has_vtt:
                            segrows.append(dict(date_key=d, station=st, item=ident, seg_s=k, seg_et=tabs.strftime('%H:%M:%S'),
                                                pdf_word=occ[0], j=j))
                        break
        rec = dict(date_key=d, station=st, items=';'.join(i for _, i in sorted(ids)), n_seg_used=len(offs))
        if offs:
            o = np.array(offs); med = float(np.median(o))
            rec.update(off_median_s=round(med, 1), off_mad_s=round(float(np.median(np.abs(o - med))), 1),
                       off_p10_s=round(float(np.percentile(o, 10)), 1), off_p90_s=round(float(np.percentile(o, 90)), 1))
        if opens:
            a = np.array(opens, dtype=float)
            # first word of the opening: earliest segment matched to the opening text, backed out by word index
            if len(a) >= 3:
                sl, ic = np.polyfit(a[:, 1], a[:, 0], 1)
                rec.update(open_fit_s=round(float(ic), 1), open_fit_sec_per_word=round(float(sl), 3), n_open_seg=len(a))
        rows.append(rec)
    print(d, [(x['station'], x['n_seg_used'], x.get('off_median_s'), x.get('off_mad_s'), x.get('open_fit_s')) for x in rows if x['date_key'] == d], flush=True)

R = pd.DataFrame(rows)
R.to_csv(os.path.join(HERE, 's2b_tv_archive.csv'), index=False)
pd.DataFrame(segrows).to_csv(os.path.join(HERE, 's2b_tv_archive_segments.csv'), index=False)
print(R.groupby('station')[['off_median_s', 'off_mad_s']].describe().T)
