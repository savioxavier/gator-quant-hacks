import pandas as pd, os
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
t = pd.read_csv(os.path.join(base, 'cost_task.csv'))
for c in ['usd_5fronts', 'usd_sr3', 'rec_5fronts', 'rec_sr3']:
    t[c] = pd.to_numeric(t[c], errors='coerce')
print('rows', len(t), 'failed 5fronts', t['usd_5fronts'].isna().sum(), 'failed sr3', t['usd_sr3'].isna().sum())
g = t.groupby('schema').agg(days=('date', 'nunique'), usd_5=('usd_5fronts', 'sum'), usd_sr3=('usd_sr3', 'sum'),
                            rec_5=('rec_5fronts', 'sum'), rec_sr3=('rec_sr3', 'sum'))
g['usd_total'] = g['usd_5'] + g['usd_sr3']
print(g.to_string())
early = t[t['date'] <= 20121231]
print('2011-2012 rows (8 days): their 13:30-16:30 window cost', early.groupby('schema')['usd_5fronts'].sum().round(4).to_dict(),
      '-> era window 12:00-16:15 is 4.25h, x1.42 =', (early.groupby('schema')['usd_5fronts'].sum() * 4.25 / 3).round(4).to_dict())
t['year'] = t['date'].astype(str).str[:4]
print(t[t['schema'] == 'ohlcv-1s'].groupby('year')[['usd_5fronts', 'usd_sr3']].sum().round(3).to_string())
print('per-day ohlcv-1s 5 fronts: median $%.4f max $%.4f' % (t[t.schema=='ohlcv-1s'].usd_5fronts.median(), t[t.schema=='ohlcv-1s'].usd_5fronts.max()))
x = pd.read_csv(os.path.join(base, 'cost_extras.csv'))
x['usd'] = pd.to_numeric(x['usd'], errors='coerce')
s = x.groupby(['dataset', 'schema', 'symbols']).agg(sample_days=('date', 'count'), mean_usd_per_day=('usd', 'mean'),
                                                     max_usd=('usd', 'max'), mean_records=('records', lambda r: pd.to_numeric(r, errors='coerce').mean()))
n_days = {'GE': 67, 'SR3': 66, 'VX': 64}  # presser days with the product listed: GE <=2023-03, SR3 >=2018-05-07, VX >=2018-11-04
s['applicable_days'] = [next((v for k, v in n_days.items() if sym.startswith(k)), 95) for sym in s.index.get_level_values('symbols')]
s['extrap_all_days'] = s['mean_usd_per_day'] * s['applicable_days']
print(s.round(4).to_string())
print(x[x['usd'].isna()].to_string())
