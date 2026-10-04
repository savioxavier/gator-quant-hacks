# Post-publication sub-period Sharpe ratios from AQR public factor datasets already downloaded in the scratchpad.
import math, sys, datetime
import os
S = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')) + os.sep
sys.path.insert(0, S)
from xlsx_read import read_xlsx, sheet_rows

def stats(s):
    s = [x for x in s if x is not None]
    n = len(s)
    if n < 12: return None
    mu = sum(s)/n; sd = math.sqrt(sum((x-mu)**2 for x in s)/(n-1))
    return n, mu*12, sd*math.sqrt(12), mu/sd*math.sqrt(12)

def load(path, sheet, hdrtest, datefmt):
    z, sh, sheets = read_xlsx(S+path)
    print(path, list(sheets)[:10])
    rows = sheet_rows(z, sh, sheets[sheet])
    hi = next(i for i, r in enumerate(rows) if r and hdrtest(r))
    hdr = rows[hi]; out = []
    for r in rows[hi+1:]:
        if not r or not r[0]: continue
        key = datefmt(r[0])
        if key is None: continue
        vals = {}
        for j, h in enumerate(hdr):
            if j == 0 or h is None: continue
            v = r[j] if j < len(r) else None
            try: vals[h] = float(v) if v not in (None, '') else None
            except ValueError: vals[h] = None
        out.append((key, vals))
    return hdr, out

def serial(x):
    try: d = datetime.date(1899,12,30)+datetime.timedelta(days=int(float(x)))
    except Exception:
        if '/' in str(x):
            m, d_, y = str(x).split('/'); return int(y)*100+int(m)
        return None
    return d.year*100+d.month

def slash(x):
    if '/' not in str(x): return None
    m, d, y = str(x).split('/'); return int(y)*100+int(m)

def report(name, data, cols, periods):
    print('==', name)
    for p, (lo, hi) in periods.items():
        parts = []
        for c in cols:
            st = stats([v.get(c) for k, v in data if lo <= k <= hi])
            parts.append(f'{c} {st[3]:.2f}' if st else f'{c} na')
        print(f'  {p:28s} ' + ' | '.join(parts))

hdr, vme = load('vme_factors.xlsx', 'VME Factors', lambda r: r[0] == 'DATE', serial)
report('VME momentum by asset class (gross, AMP 2013 sample ends 2011-07)', vme,
       ['MOM^AA', 'MOMLS_VME_EQ', 'MOMLS_VME_FX', 'MOMLS_VME_FI', 'MOMLS_VME_COM'],
       {'IS 1972-01..2011-07': (197201, 201107), 'post-pub 2013-07..end': (201307, 999912),
        '2011-08..end': (201108, 999912), '2016-01..2024-09': (201601, 202409), '2024-10..end': (202410, 999912)})
hdr, cen = load('century.xlsx', 'Century of Factor Premia', lambda r: r[0] == 'Date', slash)
report('Century momentum by asset class (gross)', cen,
       ['Equity indices Momentum', 'Fixed income Momentum', 'Currencies Momentum', 'Commodities Momentum', 'All Macro Momentum'],
       {'1981-01..2011-12': (198101, 201112), '2012-01..end': (201201, 999912), '2016-01..2024-09': (201601, 202409),
        '2024-10..end': (202410, 999912)})
hdr, ts = load('tsmom.xlsx', 'TSMOM Factors', lambda r: r and len(r) > 1 and r[1] == 'TSMOM', serial)
report('AQR TSMOM factor (gross)', ts, ['TSMOM', 'TSMOM^CM', 'TSMOM^EQ', 'TSMOM^FI', 'TSMOM^FX'],
       {'1985-01..2009-12': (198501, 200912), 'post-pub 2012-05..end': (201205, 999912),
        '2016-01..2024-09': (201601, 202409), '2024-10..end': (202410, 999912)})
