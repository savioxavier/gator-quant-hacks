"""Step 5: USMPD statement-window and press-conference-window surprises for the 75 meetings.
Source file: https://www.frbsf.org/wp-content/uploads/USMPD.xlsx (SF Fed Center for Monetary Research,
landing page https://sffed.us/usmpd, README 'Last update: 17 September 2026'; fetched 2026-10-03, sha256 recorded).
Windows (README): statements -10/+20 min around the release; press conferences -10/+60 min around the start.
Units: rates in percentage points, SP500/SPFUT/DXY/FX in percent. Source: LSEG Tick History.
"""
import os, hashlib
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
f = os.path.join(HERE, 'src', 'USMPD.xlsx')
sha = hashlib.sha256(open(f, 'rb').read()).hexdigest()
B = pd.read_csv(os.path.join(HERE, 's1_calendar_vtt.csv'), dtype={'date_key': str})
st = pd.read_excel(f, sheet_name='Statements')
pc = pd.read_excel(f, sheet_name='Press Conferences')
for x in (st, pc):
    x['date_key'] = pd.to_datetime(x.Date).dt.strftime('%Y%m%d')
st = st[st.date_key.isin(B.date_key)]
pc = pc[pc.date_key.isin(B.date_key)]
full = B[['date_key']].merge(st.add_prefix('stmt_').rename(columns={'stmt_date_key': 'date_key'}), on='date_key', how='left') \
    .merge(pc.add_prefix('pc_').rename(columns={'pc_date_key': 'date_key'}), on='date_key', how='left')
full.to_csv(os.path.join(HERE, 'usmpd_presser_days.csv'), index=False)
print('USMPD sha256', sha, '| statements matched', st.date_key.nunique(), '| pressers matched', pc.date_key.nunique())
print('statement times', st.date_time.dt.strftime('%H:%M').value_counts().to_dict())
print('presser times', pc.date_time.dt.strftime('%H:%M').value_counts().to_dict())
print('missing', sorted(set(B.date_key) - set(pc.date_key)), sorted(set(B.date_key) - set(st.date_key)))
open(os.path.join(HERE, 'usmpd_source.txt'), 'w').write(
    f'url=https://www.frbsf.org/wp-content/uploads/USMPD.xlsx\nlanding=https://sffed.us/usmpd\nsha256={sha}\n'
    'fetched=2026-10-03\nreadme_last_update=17 September 2026\n')
