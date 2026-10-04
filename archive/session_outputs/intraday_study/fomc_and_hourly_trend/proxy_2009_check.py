"""Check the claim that short-term trend stopped paying around 2009, on long daily proxies of ES and ZN.

The hourly panel starts in June 2010, so the break cannot be tested on the futures themselves.
Proxies (labelled as such):
  EQ proxy: Fama-French daily Mkt-RF (US market excess total return), 1988-2026-08.
  BOND proxy: synthetic 10-year par bond from FRED DGS10: carry y(t-1)*days/365 minus modified
              duration * change in yield, minus the T-bill (rf_daily). Convexity ignored.
Same daily EWMAC speeds as run_trend.py, same buffer, same ES/ZN costs, roll cost charged on four
dates a year. Forecast scalars / FDM estimated over 1990-01-01..2024-10-02 (in-sample).
Pre-specified split: 1990-2008 vs 2009-2024-10-02; later window descriptive.
"""
import os
import numpy as np
import pandas as pd
from common import HERE, GQH, COST, IS_END, sharpe_stats, block_bootstrap_idx
from trend_engine import TAU, ewm_std, raw_ewmac, run_positions

OUT = os.path.join(HERE, 'out_trend')
D_SPEEDS = [(2, 8), (4, 16), (8, 32), (16, 64)]
START = pd.Timestamp('1990-01-01')

ff = pd.read_parquet(os.path.join(GQH, 'ff_daily.parquet')).set_index('date')
fred = pd.read_parquet(os.path.join(GQH, 'fred_daily.parquet')).set_index('date')
rf = pd.read_parquet(os.path.join(GQH, 'rf_daily.parquet')).set_index('date')['rf']
eq = ff['Mkt_RF'].loc['1988-01-01':]
dates = eq.index
y = fred['DGS10'].reindex(fred.index).ffill().reindex(dates).ffill() / 100.0
dy = y.diff()
D = (1 - (1 + y / 2) ** (-20)) / y
gap = pd.Series(dates, index=dates).diff().dt.days.fillna(1)
bond = y.shift(1) * gap / 365.0 - D.shift(1) * dy - rf.reindex(dates).ffill()
px = pd.DataFrame({'EQ': eq, 'BOND': bond}).dropna()

# validation against the 16:00 futures (excess returns) over the overlap
f16 = pd.read_parquet(os.path.join(GQH, 'futures_1600.parquet'))
f16 = f16.pivot(index='date', columns='ticker', values='close').pct_change()
f16 = f16.sub(rf.reindex(f16.index), axis=0)
val = pd.DataFrame({'EQ_vs_ES16': [px['EQ'].corr(f16['ES16'].reindex(px.index))],
                    'BOND_vs_ZN16': [px['BOND'].corr(f16['ZN16'].reindex(px.index))],
                    'vol_ratio_BOND_ZN16': [px['BOND'].std() / f16['ZN16'].reindex(px.index).dropna().std()]})
val.to_csv(os.path.join(OUT, 'proxy_validation.csv'), index=False)

cost = {'EQ': COST['ES'], 'BOND': COST['ZN']}
roll_days = set()
for yy in range(1988, 2027):
    for mm in (3, 6, 9, 12):
        cand = px.index[(px.index >= pd.Timestamp(yy, mm, 15))]
        if len(cand):
            roll_days.add(cand[0])

raw, info = {}, {}
for m in px:
    r = px[m]
    lr = np.log1p(r)
    X = lr.cumsum().values
    sd = ewm_std(lr.values, 35).values
    sig_ann_prev = pd.Series(ewm_std(r.values, 35).values * np.sqrt(252), index=r.index).shift(1).values
    info[m] = (r, sig_ann_prev)
    for f, s in D_SPEEDS:
        raw[(f'{f}_{s}', m)] = raw_ewmac(X, f, s, sd)
ism = (px.index >= START) & (px.index <= IS_END)
scal = {f'{f}_{s}': 10 / np.nanmean(np.abs(np.concatenate([raw[(f'{f}_{s}', m)][ism] for m in px])))
        for f, s in D_SPEEDS}
fc = {(k, m): np.clip(v * scal[k], -20, 20) for (k, m), v in raw.items()}
keys = list(scal)
M = pd.DataFrame(np.vstack([np.column_stack([fc[(k, m)][ism] for k in keys]) for m in px])).dropna()
w = np.full(4, 0.25)
FDM = min(2.5, 1 / np.sqrt(w @ M.corr().values @ w))
for m in px:
    fc[('combined', m)] = np.clip(np.mean(np.column_stack([fc[(k, m)] for k in keys]), 1) * FDM, -20, 20)

series = {}
for (k, m), f in fc.items():
    r, sap = info[m]
    target = f / 10 * TAU / sap
    buf = 0.1 * TAU / sap
    pre = r.index < START
    pos = run_positions(np.where(pre, np.nan, target), buf, ~pre)
    held = np.r_[0.0, pos[:-1]]
    gross = held * r.values
    trades = np.abs(np.diff(np.r_[0.0, pos]))
    rollc = np.array([d in roll_days for d in r.index]) * 2 * np.abs(held) * cost[m]
    c = trades * cost[m] + rollc
    series[(k, m)] = pd.DataFrame({'gross': gross, 'cost': c}, index=r.index).loc[START:]
for k in keys + ['combined']:
    a, b = series[(k, 'EQ')], series[(k, 'BOND')]
    series[(k, 'PORT')] = 0.5 * (a + b)

PER = {'IS_1990_2008': ('1990-01-01', '2008-12-31'), 'IS_2009_2024': ('2009-01-01', '2024-10-02'),
       'IS_1990_1999': ('1990-01-01', '1999-12-31'), 'IS_2000_2008': ('2000-01-01', '2008-12-31'),
       'IS_2009_2016': ('2009-01-01', '2016-12-31'), 'IS_2017_2024': ('2017-01-01', '2024-10-02'),
       'later_2024_2026': ('2024-10-03', '2026-10-02')}
rows = []
rng = np.random.default_rng(5)
for (k, m), s in series.items():
    for cl, mult in [('gross', 0), ('net_1x', 1), ('net_2x', 2)]:
        x = s['gross'] - mult * s['cost']
        out = {}
        for p, (a, b) in PER.items():
            st = sharpe_stats(x.loc[a:b])
            rows.append(dict(variant=f'proxy_daily_{k}_{m}', speed=k, market=m, period=p, costs=cl,
                             sharpe=st['sharpe'], sharpe_se=st['sharpe_se'], t_nw=st['t_nw'],
                             ann_ret_pct=st['mean_ann'] * 100, ann_vol_pct=st['vol_ann'] * 100, n_days=st['n_days']))
            out[p] = x.loc[a:b].values
        # block bootstrap of Sharpe(2009-2024) - Sharpe(1990-2008), periods resampled independently
        def sr(v):
            return v.mean() / v.std() * np.sqrt(252)
        a1, a2 = out['IS_1990_2008'], out['IS_2009_2024']
        diffs = np.array([sr(a2[block_bootstrap_idx(len(a2), 20, rng)]) - sr(a1[block_bootstrap_idx(len(a1), 20, rng)])
                          for _ in range(2000)])
        rows.append(dict(variant=f'proxy_daily_{k}_{m}', speed=k, market=m, period='diff_post2009_minus_pre',
                         costs=cl, sharpe=sr(a2) - sr(a1), sharpe_se=diffs.std(),
                         diff_ci_lo=np.percentile(diffs, 2.5), diff_ci_hi=np.percentile(diffs, 97.5),
                         diff_p_two_sided=2 * min((diffs <= 0).mean(), (diffs >= 0).mean())))
R = pd.DataFrame(rows)
R.to_csv(os.path.join(OUT, 'proxy_2009_results.csv'), index=False)
pd.set_option('display.width', 250)
print(val.round(3).to_string())
print(scal, FDM)
print(R[R.costs == 'gross'].pivot_table(index=['market', 'speed'], columns='period', values='sharpe').round(2).to_string())
print(R[R.costs == 'net_1x'].pivot_table(index=['market', 'speed'], columns='period', values='sharpe').round(2).to_string())
print(R[R.period == 'diff_post2009_minus_pre'][['variant', 'costs', 'sharpe', 'diff_ci_lo', 'diff_ci_hi',
      'diff_p_two_sided']].round(3).to_string())
