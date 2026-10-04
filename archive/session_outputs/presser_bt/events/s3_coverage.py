"""Step 3: market-data coverage per meeting x instrument (13:30-16:30 ET window as downloaded)."""
import os, re
import numpy as np, pandas as pd
from mkt import load_1m, load_1s, load_bbo, SYMS, ET

HERE = os.path.dirname(os.path.abspath(__file__))
B = pd.read_csv(os.path.join(HERE, 's1_calendar_vtt.csv'), dtype={'date_key': str})
m1, s1 = load_1m(), load_1s()
rows = []
for _, r in B.iterrows():
    d = r.date_key
    w0 = pd.Timestamp(f'{r.date} 13:30', tz=ET); w1 = pd.Timestamp(f'{r.date} 16:30', tz=ET)
    bbo = load_bbo(d)
    for sym in SYMS:
        g = m1[(m1.d == d) & (m1.symbol == sym) & (m1.t >= w0) & (m1.t < w1)]
        h = s1[(s1.d == d) & (s1.symbol == sym) & (s1.t >= w0) & (s1.t < w1)]
        ids = sorted(set(g.instrument_id) | set(h.instrument_id))
        k = sym.split('.')[0]
        rec = {'date_key': d, 'sym': k, 'n_1m_bars': len(g), 'n_1s_bars': len(h),
               'first_bar_et': g.t.min().strftime('%H:%M') if len(g) else None,
               'last_bar_et': g.t.max().strftime('%H:%M') if len(g) else None,
               'n_1m_1350_1420': int(((g.t >= w0.replace(hour=13, minute=50)) & (g.t < w0.replace(hour=14, minute=20))).sum()),
               'n_1m_1420_1630': int((g.t >= w0.replace(hour=14, minute=20)).sum()),
               'instrument_ids': ';'.join(map(str, ids)), 'n_instrument_ids': len(ids)}
        # missing 1m minutes inside 13:30-16:30 (no trade in that minute)
        if len(g):
            allm = pd.date_range(w0, w1 - pd.Timedelta('1min'), freq='1min')
            miss = allm.difference(pd.DatetimeIndex(g.t))
            rec['n_missing_minutes'] = len(miss)
            rec['missing_minutes_1420_1530'] = int(((miss >= w0.replace(hour=14, minute=20)) & (miss < w0.replace(hour=15, minute=30))).sum())
        if bbo is not None:
            b = bbo[(bbo.symbol == sym) & (bbo.t >= w0) & (bbo.t < w1)]
            rec['n_bbo_1s'] = len(b)
        rows.append(rec)
C = pd.DataFrame(rows)
C.to_csv(os.path.join(HERE, 's3_coverage_long.csv'), index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 400)
print(C.groupby('sym')[['n_1m_bars', 'n_1s_bars', 'n_missing_minutes', 'n_instrument_ids', 'n_1m_1350_1420']].describe().T.to_string())
print('instrument id changes inside window:', C[C.n_instrument_ids > 1][['date_key', 'sym', 'instrument_ids']].to_string())
print('ES last bar distribution:', C[C.sym == 'ES'].last_bar_et.value_counts().to_dict())
print('low coverage rows:', C[C.n_1m_bars < 150][['date_key', 'sym', 'n_1m_bars', 'first_bar_et', 'last_bar_et']].to_string())
