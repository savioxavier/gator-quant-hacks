"""Step 1: calendar facts and caption (WebVTT) timing for the 75 press-conference meetings 2016-03-16..2026-09-16.

Inputs (all local copies of public federalreserve.gov pages / files fetched 2026-10-03):
  src/boardmembership.htm                 chair tenure table
  src/fomchistorical2016..2020.htm, src/fomccalendars.htm   meeting list, SEP marker, presser link
  fedtalk/data_markets/vtt/YYYYMMDD.vtt   official caption tracks (Brightcove, forced alignment of the transcript)
  fedtalk/data_markets/video_meta.csv     Brightcove video durations
  fedtalk/data_markets/pdf/FOMCpresconfYYYYMMDD.txt  transcript text (pdftotext of the official PDF)
  fedspeak_v2/corpus/fomc_docs.parquet    statement release timestamps (press-release feed)
Output: s1_calendar_vtt.csv
"""
import os, re, html, glob, json
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.dirname(os.path.dirname(HERE))
DM = os.path.join(SP, 'fedtalk', 'data_markets')
SRC = os.path.join(HERE, 'src')

dates = [l.strip() for l in open(os.path.join(DM, 'presser_dates.txt')) if l.strip() >= '20160101']
assert len(dates) == 75, len(dates)

# ---------------- chair tenure (federalreserve.gov board membership page) ----------------
t = open(os.path.join(SRC, 'boardmembership.htm'), encoding='utf-8', errors='ignore').read()
txt = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', t)).split())
def grab(name):
    m = re.search(r'([A-Z][a-z]{2,4}\.? \d{1,2}, \d{4}) - ((?:[A-Z][a-z]{2,4}\.? \d{1,2}, \d{4})?) ?' + re.escape(name), txt)
    return m.group(1), m.group(2)
chairs = {}
for short, full in [('Yellen', 'Janet L. Yellen'), ('Powell', 'Jerome H. Powell'), ('Warsh', 'Kevin Warsh')]:
    a, b = grab(full)
    chairs[short] = (pd.Timestamp(a.replace('.', '')), pd.Timestamp(b.replace('.', '')) if b else pd.Timestamp('2099-12-31'))
print('chair tenure (federalreserve.gov boardmembership.htm):', {k: (str(v[0].date()), str(v[1].date())) for k, v in chairs.items()})

def chair_on(d):
    d = pd.Timestamp(d)
    hits = [k for k, (a, b) in chairs.items() if a <= d < b]
    return hits[0] if hits else None

# ---------------- meeting list, SEP, presser link ----------------
mon = {m: i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                                     'September', 'October', 'November', 'December'], 1)}
meet = {}
for y in range(2016, 2021):
    t = open(os.path.join(SRC, f'fomchistorical{y}.htm'), encoding='utf-8', errors='ignore').read()
    for p in re.split(r'<h5 class="panel-heading[^"]*">', t)[1:]:
        h = p.split('</h5>')[0].strip()
        for m in re.finditer(r'fomcpres+conf(\d{8})\.htm', p):
            d = m.group(1)
            meet[d] = dict(heading=h, sep=int(bool(re.search(r'SEPcompilation|projtabl', p))),
                           scheduled=int('unscheduled' not in h.lower()), cal_page=f'fomchistorical{y}.htm')
t = open(os.path.join(SRC, 'fomccalendars.htm'), encoding='utf-8', errors='ignore').read()
# split by year panels then meeting rows
for yb in re.split(r'<h4[^>]*>\s*<a[^>]*>\s*(\d{4}) FOMC Meetings', t)[1:]:
    pass
rows = re.split(r'<div class="(?:fomc-meeting--shaded )?row fomc-meeting"', t)
for r in rows[1:]:
    dd = re.search(r'fomc-meeting__date[^>]*>([^<]+)<', r)
    for m in re.finditer(r'fomcpres+conf(\d{8})\.htm', r):
        d = m.group(1)
        if d in meet:
            continue
        lab = dd.group(1).strip() if dd else ''
        meet[d] = dict(heading=lab, sep=int('*' in lab), scheduled=int('unscheduled' not in lab.lower()),
                       cal_page='fomccalendars.htm')
missing = [d for d in dates if d not in meet]
print('meetings without calendar match:', missing)

# ---------------- statement release time ----------------
docs = pd.read_parquet(os.path.join(SP, 'fedspeak_v2', 'corpus', 'fomc_docs.parquet'))
st = docs[docs.doc_type == 'statement'].copy()
st['d'] = st.date.dt.strftime('%Y%m%d')
st = st.set_index('d')

# ---------------- video meta and VTT ----------------
vm = pd.read_csv(os.path.join(DM, 'video_meta.csv'), dtype={'date': str}).set_index('date')

def ts(s):
    p = [float(x) for x in s.split(':')]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]

LAB = re.compile(r"(?:\d{4} )?(?:[A-Z][A-Z'\-]+\.? ){0,3}[A-Z][A-Z'\-]+[.:]$")
HDR = re.compile(r"Transcript of|Press Conference|Page \d+ of \d+|^FINAL$")

def parse_vtt(path):
    raw = open(path, encoding='utf-8').read()
    C = []
    for a, b, body in re.findall(r'([\d:.]+) --> ([\d:.]+)[^\n]*\n(.*?)(?:\n\n|\Z)', raw, flags=re.S):
        body = ' '.join(body.split())
        C.append((ts(a), ts(b), body))
    df = pd.DataFrame(C, columns=['s', 'e', 'text'])
    df['label'] = df.text.str.fullmatch(LAB.pattern)
    df['hdr'] = df.text.str.contains(HDR) & ~df.label
    df['speech'] = ~df.label & ~df.hdr
    df['nw'] = df.text.str.split().str.len()
    df['wps'] = df.nw / (df.e - df.s).replace(0, np.nan)
    return df

def norm_words(s):
    return re.findall(r"[a-z]+", s.lower())

out = []
for d in dates:
    m = meet.get(d, {})
    chair = chair_on(d)
    row = dict(date=pd.Timestamp(d).date().isoformat(), date_key=d, chair=chair,
               scheduled=m.get('scheduled', np.nan), sep_meeting=m.get('sep', np.nan),
               calendar_heading=m.get('heading'), calendar_source=('https://www.federalreserve.gov/monetarypolicy/' + m['cal_page']) if m else None)
    # statement
    if d in st.index:
        r = st.loc[d]
        row['statement_release_et'] = pd.Timestamp(r.release_ts_et).strftime('%H:%M:%S')
        row['statement_release_source'] = f"{r.release_time_source}; {r.url}"
    else:
        row['statement_release_et'] = None
    # scheduled presser time (Fed press releases / USMPD scheduled minute)
    row['presser_sched_et'] = {'20200303': '11:00:00', '20200315': '18:30:00'}.get(d, '14:30:00')
    v = vm.loc[d]
    row['video_duration_s'] = float(v.duration_s)
    row['video_page'] = v.page
    f = os.path.join(DM, 'vtt', d + '.vtt')
    row['has_captions'] = int(os.path.exists(f))
    if os.path.exists(f):
        df = parse_vtt(f)
        sp = df[df.speech]
        g = sp[sp.text.str.contains(r'\bgood (?:afternoon|morning|evening|day)\b', case=False, regex=True) & (sp.s < 400)]
        chair_lab = df[df.label & df.text.str.contains('CHAIR')]
        first_chair_lab = chair_lab.s.min() if len(chair_lab) else np.nan
        if len(g):
            gs = float(g.s.iloc[0]); gsrc = 'greeting cue'
        else:
            after = sp[sp.s >= (first_chair_lab if not np.isnan(first_chair_lab) else 0)]
            gs = float(after.s.iloc[0]); gsrc = 'first chair speech cue (no greeting)'
        other_lab = df[df.label & ~df.text.str.contains('CHAIR') & (df.s > gs)]
        qa = float(other_lab.s.iloc[0]) if len(other_lab) else np.nan
        last_end = float(sp.e.max())
        # opening-statement cues (between greeting and first Q&A label): stretched cues = alignment failure
        op = sp[(sp.s >= gs) & (sp.s < (qa if not np.isnan(qa) else 1e9))]
        stretched_open = op[((op.e - op.s) > 8) & (op.wps < 0.6)]
        allst = sp[((sp.e - sp.s) > 8) & (sp.wps < 0.6)]
        # text check: first 12 words after the greeting vs the transcript opening
        vw = norm_words(' '.join(sp[sp.s >= gs].text.head(6)))[:12]
        ptxt = open(os.path.join(DM, 'pdf', f'FOMCpresconf{d}.txt'), encoding='utf-8', errors='replace').read()
        mm = re.search(r'CHAIR(?:MAN)? [A-Z]+[.:]\s*(.{0,400})', ptxt, flags=re.S)
        pw = norm_words(mm.group(1))[:20] if mm else []
        match = np.mean([w in pw for w in vw]) if vw else np.nan
        row.update(first_cue_s=float(df.s.min()), first_chair_label_s=first_chair_lab, greeting_s=gs, greeting_src=gsrc,
                   first_qa_label_s=qa, last_speech_end_s=last_end,
                   caption_overrun_s=round(last_end - row['video_duration_s'], 1),
                   cues_after_video_end=int((df.s > row['video_duration_s']).sum()),
                   n_stretched_open=len(stretched_open), stretched_open_s=round(float((stretched_open.e - stretched_open.s).sum()), 1),
                   n_stretched_all=len(allst), stretched_all_s=round(float((allst.e - allst.s).sum()), 1),
                   chair_label_cues=len(chair_lab), opening_text_match=round(float(match), 2),
                   opening_words_vtt=' '.join(vw[:8]))
    out.append(row)

R = pd.DataFrame(out)
R.to_csv(os.path.join(HERE, 's1_calendar_vtt.csv'), index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200); pd.set_option('display.max_columns', 40)
print(R[['date', 'chair', 'scheduled', 'sep_meeting', 'statement_release_et', 'presser_sched_et', 'has_captions', 'greeting_s',
         'greeting_src', 'first_qa_label_s', 'last_speech_end_s', 'video_duration_s', 'caption_overrun_s', 'n_stretched_open',
         'stretched_all_s', 'opening_text_match']].to_string())
print(R.groupby('chair').size(), R.scheduled.value_counts(dropna=False), R.sep_meeting.value_counts(dropna=False))
