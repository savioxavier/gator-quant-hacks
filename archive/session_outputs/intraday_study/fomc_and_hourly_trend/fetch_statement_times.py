"""Fetch each scheduled FOMC statement page once (plain HTTP GET, no credentials) and read its
'For release at' time. Pages are cached under fed_html/statements/."""
import os, re, time, urllib.request
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'fed_html', 'statements')
f = pd.read_csv(os.path.join(HERE, 'fomc_dates.csv'), dtype={'statement': str})
out = []
for _, r in f.iterrows():
    sid = r.statement
    path = os.path.join(D, f'monetary{sid}a.htm')
    url = f'https://www.federalreserve.gov/newsevents/pressreleases/monetary{sid}a.htm'
    if not os.path.exists(path):
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            html = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
        except Exception as e:
            html = ''
            print('fail', sid, e)
        open(path, 'w', encoding='utf-8').write(html)
        time.sleep(0.4)
    html = open(path, encoding='utf-8').read()
    m = re.search(r'For release at\s*([0-9:]+\s*[ap]\.?m\.?)\s*([A-Z]{3})?', html, re.I)
    out.append(dict(date=r.date, statement=sid, url=url, release_text=(m.group(0) if m else None)))
o = pd.DataFrame(out)
o.to_csv(os.path.join(HERE, 'fomc_statement_times.csv'), index=False)
print(o.to_string())
