"""Build the list of scheduled FOMC statement dates and release times, 2010-2026.

Source pages (fetched once with plain HTTP GET, saved under fed_html/):
  https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm            (2021-2027)
  https://www.federalreserve.gov/monetarypolicy/fomchistorical{YYYY}.htm     (2010-2020)
Statement date = the date in the statement link monetaryYYYYMMDDa.htm of a regularly scheduled
meeting. Conference calls and meetings labelled unscheduled are excluded.
Release time (ET), following Lucca & Moench (2015, section on timing) and the Fed's practice:
  - through 2012: 14:15, except meetings with a Chair press conference (Apr 2011 - Dec 2012),
    where the statement came out at 12:30 and the press conference at 14:15;
  - from 2013: 14:00.
"""
import re, os, glob
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
H = os.path.join(HERE, 'fed_html')
rows = []

# historical pages 2010-2020
for y in range(2010, 2021):
    t = open(os.path.join(H, f'fomchistorical{y}.htm'), encoding='utf-8').read()
    parts = re.split(r'<h5[^>]*>', t)[1:]
    for p in parts:
        head = p.split('</h5>')[0].strip()
        body = p
        st = re.findall(r'/newsevents/press(?:releases)?/monetary/?(\d{8})a\.htm', body)
        pc = re.findall(r'fomcpres+conf(\d{8})', body)
        kind = 'meeting' if re.search(r'Meeting', head) else 'other'
        unsched = bool(re.search(r'unscheduled|Conference Call|Notation|cancelled', head, re.I))
        rows.append(dict(year=y, label=head, statement=st[0] if st else None,
                         press_conf=bool(pc), scheduled=(kind == 'meeting' and not unsched),
                         source=f'https://www.federalreserve.gov/monetarypolicy/fomchistorical{y}.htm'))

# current calendar page 2021-2027
t = open(os.path.join(H, 'fomccalendars.htm'), encoding='utf-8').read()
panels = re.split(r'<div class="panel-heading"><h4><a id="\d+">', t)[1:]
for pan in panels:
    yr = int(re.match(r'(\d{4})', pan).group(1))
    if yr < 2021:
        continue
    for m in re.split(r'<div class="(?:fomc-meeting--shaded )?row fomc-meeting"', pan)[1:]:
        mon = re.search(r'fomc-meeting__month[^>]*><strong>([^<]*)</strong>', m)
        dt = re.search(r'fomc-meeting__date[^>]*>([^<]*)</div>', m)
        if not mon or not dt:
            continue
        label = f'{mon.group(1)} {dt.group(1)} {yr}'
        st = re.findall(r'/newsevents/pressreleases/monetary(\d{8})a\.htm', m)
        pc = re.findall(r'fomcpres+conf(\d{8})', m)
        unsched = bool(re.search(r'unscheduled|notation|conference call', label + m[:600], re.I))
        rows.append(dict(year=yr, label=label, statement=st[0] if st else None, press_conf=bool(pc),
                         scheduled=not unsched,
                         source='https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'))

df = pd.DataFrame(rows)
df.to_csv(os.path.join(HERE, 'fomc_raw_parse.csv'), index=False)
s = df[df.scheduled].copy()
# future meetings without a statement link: date from the label (second day of the meeting)
mon_num = {m: i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                                       'September', 'October', 'November', 'December'], 1)}
def label_date(r):
    if r.statement:
        return pd.Timestamp(r.statement)
    m = re.match(r'(\w+)(?:/(\w+))? (\d+)(?:-(\d+))?\*? (\d{4})', r.label)
    if not m:
        return pd.NaT
    mon1, mon2, d1, d2, yy = m.groups()
    mon = mon2 if (mon2 and d2) else mon1
    return pd.Timestamp(int(yy), mon_num[mon], int(d2 or d1))
s['date'] = s.apply(label_date, axis=1)
s = s[s.date.notna()].sort_values('date')
def rel(r):
    d = r.date
    if d.year >= 2013:
        return '14:00'
    if r.press_conf and d >= pd.Timestamp('2011-04-01'):
        return '12:30'
    return '14:15'
s['release_et'] = s.apply(rel, axis=1)
s = s[(s.date >= '2010-06-08') & (s.date <= '2026-12-31')]
out = s[['date', 'release_et', 'press_conf', 'label', 'statement', 'source']]
out.to_csv(os.path.join(HERE, 'fomc_dates.csv'), index=False)
print(out.to_string())
print(len(out))
print(df[~df.scheduled][['year', 'label', 'statement']].to_string())
