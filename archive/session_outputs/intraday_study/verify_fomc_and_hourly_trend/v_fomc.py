"""Independent recomputation of the pre-FOMC drift numbers from the raw hourly file."""
import os
import numpy as np
import pandas as pd
from v_common import build_chain, nyse_days, FOMC, REL1230, TZ, IS_END, COST, nw_t, HERE

days = nyse_days()
days = days[(days >= '2010-06-08') & (days <= '2026-10-02')]
prev = pd.Series(days[:-1], index=days[1:])
out = []
chains = {}
for root in ['ES', 'ZN']:
    f = build_chain(root)
    chains[root] = f
    f = f.dropna(subset=['lr'])
    t_end = f['end_utc'].values
    L = np.cumsum(f['lr'].values)

    def mark(ts_et_naive):
        tu = pd.DatetimeIndex(ts_et_naive).tz_localize(TZ).tz_convert('UTC').tz_localize(None).values.astype('datetime64[ns]')
        te = pd.DatetimeIndex(t_end).tz_localize(None).values.astype('datetime64[ns]') if hasattr(t_end, 'tz') else t_end
        te = pd.to_datetime(f['end_utc']).dt.tz_localize(None).values
        i = np.searchsorted(te, tu, side='right') - 1
        stale = (tu - te[i]) / np.timedelta64(1, 'h')
        return L[i], stale

    ev = FOMC[(FOMC >= days[1]) & (FOMC <= '2026-10-02')]
    for wname, sh, eshift in [('14_to_rel', 14, 0), ('14_to_rel_m1h', 14, -1), ('16_to_rel', 16, 0)]:
        p = prev.reindex(ev).values
        endh = np.where(ev.isin(REL1230), 12, 14) + eshift
        A = pd.DatetimeIndex(p) + pd.Timedelta(hours=sh)
        B = ev + pd.to_timedelta(endh, 'h')
        LA, sA = mark(A)
        LB, sB = mark(B)
        r = np.expm1(LB - LA)
        out.append(pd.DataFrame({'root': root, 'window': wname, 'd': ev, 'ret': r, 'staleA': sA, 'staleB': sB}))
W = pd.concat(out)
W.to_csv(os.path.join(HERE, 'v_fomc_windows.csv'), index=False)
print('max stale hours', W.staleA.max(), W.staleB.max())

rows = []
for (root, wname), g in W.groupby(['root', 'window']):
    for pname, sel in [('IS_full', g.d <= IS_END), ('IS_2010_14', g.d <= '2014-12-31'),
                       ('IS_2015_24', (g.d > '2014-12-31') & (g.d <= IS_END)),
                       ('IS_2015_19', (g.d > '2014-12-31') & (g.d <= '2019-12-31')),
                       ('IS_2020_24', (g.d > '2019-12-31') & (g.d <= IS_END)),
                       ('IS_2015_24_ex2022', (g.d > '2014-12-31') & (g.d <= IS_END) & (g.d.dt.year != 2022)),
                       ('later', g.d > IS_END)]:
        x = g[sel]
        if pname.startswith('IS_full'):
            dsel = days[(days >= days[1]) & (days <= IS_END)]
        elif pname == 'later':
            dsel = days[days > IS_END]
        else:
            dsel = days[(days >= x.d.min()) & (days <= x.d.max())]
        for cl, m in [('gross', 0), ('1x', 1), ('2x', 2)]:
            net = x['ret'].values - 2 * COST[root] * m
            tl = pd.Series(0.0, index=dsel)
            tl.loc[x.d.values] = net
            sr = tl.mean() / tl.std() * np.sqrt(252)
            yrs = len(dsel) / 252
            rows.append(dict(root=root, window=wname, period=pname, costs=cl, n=len(net), mean_bp=net.mean() * 1e4,
                             t_iid=net.mean() / net.std(ddof=1) * np.sqrt(len(net)), t_nw2=nw_t(net, 2),
                             sr_timeline=sr, sr_se=np.sqrt((1 + sr ** 2 / 2) / yrs),
                             sr_from_t=net.mean() / net.std(ddof=1) * np.sqrt(len(net) / yrs),
                             ann_pct=net.mean() * len(net) / yrs * 100))
R = pd.DataFrame(rows)
R.to_csv(os.path.join(HERE, 'v_fomc_results.csv'), index=False)
pd.set_option('display.width', 250)
print(R.round(3).to_string())

# 2022 mean, per-year means for ES primary
g = W[(W.root == 'ES') & (W.window == '14_to_rel')]
print((g.groupby(g.d.dt.year)['ret'].agg(['mean', 'count']) * [1e4, 1]).round(1).T.to_string())

# compare with analyst's window returns
a = pd.read_parquet(os.path.join(os.path.dirname(HERE), 'fomc_and_hourly_trend', 'out_fomc', 'window_returns.parquet'))
a = a[a.fomc]
mp = {'LM_14_to_release': '14_to_rel', 'LM_14_to_release_m1h': '14_to_rel_m1h', 'close16_to_release': '16_to_rel'}
a['window'] = a['window'].map(mp)
c = a.merge(W, on=['root', 'window', 'd'], suffixes=('_a', '_v'))
c['diff_bp'] = (c.ret_a - c.ret_v) * 1e4
print('merged', len(c), 'max |diff| bp', c.diff_bp.abs().max())
print(c.loc[c.diff_bp.abs() > 0.5, ['root', 'window', 'd', 'ret_a', 'ret_v', 'diff_bp']])

# where does the ES drift accrue? hourly bars from 14:00 prev day to 14:00 event day, 14:00/14:15 release days, IS
f = chains['ES'].dropna(subset=['r'])
f = f.set_index('end_utc')
prof = []
for d in FOMC[(FOMC <= IS_END) & ~FOMC.isin(REL1230) & (FOMC >= days[1])]:
    p = prev[d]
    a0 = (p + pd.Timedelta(hours=14)).tz_localize(TZ).tz_convert('UTC')
    b0 = (d + pd.Timedelta(hours=14)).tz_localize(TZ).tz_convert('UTC')
    seg = f.loc[(f.index > a0) & (f.index <= b0)]
    prof.append(pd.DataFrame({'end_hour_et': seg['end_et'].dt.hour.values, 'same_day': (seg['end_et'].dt.normalize().dt.tz_localize(None) == d).values,
                              'r': seg['r'].values}))
P = pd.concat(prof)
P['bucket'] = np.select([~P.same_day, P.end_hour_et <= 5, P.end_hour_et <= 9, P.end_hour_et <= 14],
                        ['prev_day_14_to_24', 'ev_00_05', 'ev_05_09', 'ev_09_14'], 'other')
n_ev = len(prof)
print('events', n_ev)
print((P.groupby('bucket')['r'].sum() / n_ev * 1e4).round(2))
