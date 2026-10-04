"""Part A: pre-FOMC announcement drift (Lucca & Moench 2015) on hourly ES and ZN.

Pre-specified (from Lucca & Moench's 2pm-to-2pm window and their close-to-2pm robustness window):
  W1 'LM_14_to_release': 14:00 ET on the previous NYSE day -> last full hour before the statement
       (14:00 for 14:00 / 14:15 releases, 12:00 for the 12:30 press-conference releases of 2011-12)
  W2 'LM_14_to_release_m1h': same start, end one hour earlier (13:00, or 11:00 on 12:30 days)
  W3 'close16_to_release': 16:00 ET on the previous NYSE day -> same end as W1
Markets: ES and ZN, long only. Each variant is reported gross and at 1x / 2x round-trip costs
(ES 1.0 bp, ZN 1.5 bp one way). Bar timestamps are starts: a mark at H:00 is the close of the
bar that starts at (H-1):00, i.e. the last trade before H:00.
Periods: in-sample pre-publication 2010-06-08..2014-12-31, post-publication 2015-01-01..2024-10-02,
later window 2024-10-03..2026-10-02 (descriptive only).
"""
import os
import numpy as np
import pandas as pd
from common import (HERE, load_panel, nyse_days, nw_tstat, nw_regression, COST, IS_END, LATER_START,
                    LATER_END)

OUT = os.path.join(HERE, 'out_fomc')
os.makedirs(OUT, exist_ok=True)
TZ = 'America/New_York'

fomc = pd.read_csv(os.path.join(HERE, 'fomc_dates.csv'), parse_dates=['date'])
fomc = fomc[fomc.date <= LATER_END]
panel = load_panel()
days = nyse_days()
days = days[(days >= '2010-06-08') & (days <= LATER_END)]

# cumulative within-contract log index at each bar END, per root
marks = {}
for root, g in panel.groupby('root'):
    g = g.sort_values('bar_end_utc')
    L = g['ret_log'].fillna(0.0).cumsum()
    marks[root] = pd.DataFrame({'t': g['bar_end_utc'].values, 'L': L.values,
                                'other_missing': (g['gap_type'] == 'other_missing').values})


def asof_L(root, times_utc):
    m = marks[root]
    idx = np.searchsorted(m['t'].values, times_utc.values, side='right') - 1
    L = m['L'].values[idx]
    tb = m['t'].values[idx]
    stale_h = (times_utc.values - tb) / np.timedelta64(1, 'h')
    return L, stale_h, idx


def et(day, hour, minute=0):
    return (pd.DatetimeIndex(day) + pd.to_timedelta(hour, 'h') + pd.to_timedelta(minute, 'm')).tz_localize(TZ).tz_convert('UTC')


# build per-day window table
prev = pd.DatetimeIndex(np.r_[[pd.NaT], days[:-1].values])
df = pd.DataFrame({'d': days, 'p': prev}).iloc[1:].reset_index(drop=True)
f_map = fomc.set_index('date')['release_et'].to_dict()
df['fomc'] = df['d'].isin(fomc['date'])
df['release_et'] = df['d'].map(f_map)
end_h = np.where(df['release_et'] == '12:30', 12, 14)
df['end_h'] = end_h
WINDOWS = {
    'LM_14_to_release': (14, 0),
    'LM_14_to_release_m1h': (14, -1),
    'close16_to_release': (16, 0),
}
rows = []
for root in ['ES', 'ZN']:
    for wname, (start_h, end_shift) in WINDOWS.items():
        A = et(df['p'], start_h)
        Bh = df['end_h'] + end_shift
        B = (pd.DatetimeIndex(df['d']) + pd.to_timedelta(np.asarray(Bh), 'h')).tz_localize(TZ).tz_convert('UTC')
        LA, sA, iA = asof_L(root, pd.Series(A))
        LB, sB, iB = asof_L(root, pd.Series(B))
        om = marks[root]['other_missing'].values
        cs = np.r_[0, np.cumsum(om)]
        n_missing = cs[iB + 1] - cs[iA + 1]
        r = np.expm1(LB - LA)
        t = pd.DataFrame({'root': root, 'window': wname, 'd': df['d'], 'fomc': df['fomc'],
                          'release_et': df['release_et'], 'ret': r, 'stale_start_h': sA, 'stale_end_h': sB,
                          'n_vendor_gap_bars': n_missing})
        rows.append(t)
W = pd.concat(rows, ignore_index=True)
# exclude windows that span a vendor hole / outage, or whose marks are more than 2h stale
W['valid'] = (W['n_vendor_gap_bars'] == 0) & (W['stale_start_h'] <= 2) & (W['stale_end_h'] <= 2)
W.to_parquet(os.path.join(OUT, 'window_returns.parquet'))


def period_of(d):
    if d <= pd.Timestamp('2014-12-31'):
        return 'IS_pre_2010_2014'
    if d <= IS_END:
        return 'IS_post_2015_2024'
    return 'later_2024_2026'


W['period'] = W['d'].map(period_of)
PERIODS = {'IS_full_2010_2024': lambda x: x <= IS_END,
           'IS_pre_2010_2014': lambda x: x <= pd.Timestamp('2014-12-31'),
           'IS_post_2015_2024': lambda x: (x > pd.Timestamp('2014-12-31')) & (x <= IS_END),
           'later_2024_2026': lambda x: x >= LATER_START}

res = []
rng = np.random.default_rng(11)
for (root, wname), g in W.groupby(['root', 'window']):
    c = COST[root]
    for pname, sel in PERIODS.items():
        gp = g[sel(g['d'])]
        allv = gp[gp['valid']]
        ev = allv[allv['fomc']]
        non = allv[~allv['fomc']]
        n_days = len(gp)
        years = n_days / 252.0
        # regression of all 24h windows on an FOMC dummy (Lucca-Moench style), NW lags 5
        X = np.c_[np.ones(len(allv)), allv['fomc'].astype(float).values]
        b, se, tt = nw_regression(allv['ret'].values, X, lags=5)
        for cost_label, mult in [('gross', 0), ('net_1x', 1), ('net_2x', 2)]:
            net = ev['ret'].values - 2 * c * mult           # round trip on each event
            n = len(net)
            tr_per_yr = n / years
            mean = net.mean()
            sd = net.std(ddof=1)
            t_nw, _ = nw_tstat(net, lags=2)
            # timeline Sharpe: zero on non-event days
            daily = pd.Series(0.0, index=gp['d'].values)
            daily.loc[ev['d'].values] = net
            sr_tl = daily.mean() / daily.std(ddof=1) * np.sqrt(252)
            res.append(dict(root=root, window=wname, period=pname, costs=cost_label, n_events=n,
                            events_per_year=tr_per_yr, mean_bp=mean * 1e4, median_bp=np.median(net) * 1e4,
                            sd_bp=sd * 1e4, hit_rate=(net > 0).mean(), t_nw_mean=t_nw,
                            sharpe_per_trade=mean / sd, sharpe_ann_timeline=sr_tl,
                            sharpe_ann_se=np.sqrt((1 + sr_tl ** 2 / 2) / years),
                            ann_contribution_pct=mean * tr_per_yr * 100,
                            nonfomc_mean_bp=non['ret'].mean() * 1e4, nonfomc_n=len(non),
                            nonfomc_sd_bp=non['ret'].std() * 1e4,
                            fomc_minus_other_bp=b[1] * 1e4, fomc_minus_other_t_nw=tt[1],
                            excluded_invalid=int((~gp['valid']).sum())))
R = pd.DataFrame(res)
R.to_csv(os.path.join(OUT, 'fomc_results.csv'), index=False)

# pre vs post difference in mean event return (independent bootstrap, 20000 reps)
diff_rows = []
for (root, wname), g in W[W['valid'] & W['fomc']].groupby(['root', 'window']):
    a = g[g['period'] == 'IS_pre_2010_2014']['ret'].values
    bb = g[g['period'] == 'IS_post_2015_2024']['ret'].values
    reps = 20000
    da = rng.choice(a, size=(reps, len(a))).mean(1) - rng.choice(bb, size=(reps, len(bb))).mean(1)
    d0 = a.mean() - bb.mean()
    welch = d0 / np.sqrt(a.var(ddof=1) / len(a) + bb.var(ddof=1) / len(bb))
    diff_rows.append(dict(root=root, window=wname, pre_mean_bp=a.mean() * 1e4, post_mean_bp=bb.mean() * 1e4,
                          diff_bp=d0 * 1e4, welch_t=welch, boot_ci_lo_bp=np.percentile(da, 2.5) * 1e4,
                          boot_ci_hi_bp=np.percentile(da, 97.5) * 1e4,
                          boot_p_two_sided=2 * min((da <= 0).mean(), (da >= 0).mean()),
                          n_pre=len(a), n_post=len(bb)))
D = pd.DataFrame(diff_rows)
D.to_csv(os.path.join(OUT, 'fomc_pre_post_diff.csv'), index=False)

# ---- timing check: mean |hourly return| by bar start hour on FOMC days vs other days (in-sample)
p = panel[(panel['trade_date'] <= IS_END) & (panel['gap_type'] != 'other_missing')].copy()
p['fomc_rel'] = p['trade_date'].map(f_map)
p['grp'] = np.where(p['fomc_rel'].isna(), 'non_fomc', 'fomc_' + p['fomc_rel'].astype(str))
p = p[p['hour_et'].between(8, 16) & (p['date_et'] == p['trade_date'])]
tc = (p.assign(absr=p['ret_simple'].abs() * 1e4)
      .groupby(['root', 'grp', 'hour_et'])['absr'].mean().unstack('hour_et').round(1))
tc.to_csv(os.path.join(OUT, 'timing_check_abs_ret_by_hour.csv'))

# ---- hourly profile: mean return of each bar from 14:00 ET the previous day to 16:00 ET event day
prof = []
for root in ['ES', 'ZN']:
    g = panel[panel['root'] == root][['bar_end_utc', 'ret_simple', 'gap_type']].copy()
    g['bar_end_et'] = g['bar_end_utc'].dt.tz_convert(TZ)
    g = g.set_index('bar_end_utc').sort_index()
    for _, rr in df.iterrows():
        if rr['d'] > IS_END or (rr['d'] - rr['p']).days != 1:   # consecutive weekdays only (no weekend/holiday spans)
            continue
        start = pd.Timestamp(rr['p']).tz_localize(TZ).tz_convert('UTC') + pd.Timedelta(hours=14)
        end = pd.Timestamp(rr['d']).tz_localize(TZ).tz_convert('UTC') + pd.Timedelta(hours=16)
        seg = g.loc[(g.index > start) & (g.index <= end)]
        if len(seg) == 0:
            continue
        hrs = ((seg.index - start) / pd.Timedelta(hours=1)).astype(int)
        prof.append(pd.DataFrame({'root': root, 'fomc': rr['fomc'], 'rel12': rr['release_et'] == '12:30',
                                  'h_after_start': hrs, 'ret': seg['ret_simple'].values,
                                  'gap': seg['gap_type'].values}))
P = pd.concat(prof)
P = P[P['gap'] != 'other_missing']
P = P[~P['rel12']]
prof_tab = (P.groupby(['root', 'fomc', 'h_after_start'])['ret'].agg(['mean', 'count']).reset_index())
prof_tab['mean_bp'] = prof_tab['mean'] * 1e4
prof_tab.to_csv(os.path.join(OUT, 'hourly_profile_from_14h_prev_day.csv'), index=False)

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, root in zip(axes, ['ES', 'ZN']):
        for fl, lab in [(True, 'scheduled FOMC days (14:00/14:15 releases)'), (False, 'all other days')]:
            s = prof_tab[(prof_tab.root == root) & (prof_tab.fomc == fl)].set_index('h_after_start')['mean_bp']
            ax.plot(s.index, s.cumsum(), label=lab)
        ax.axvline(24, color='grey', ls='--', lw=0.8)
        ax.set_title(f'{root}: mean cumulative return from 14:00 ET previous day, in-sample')
        ax.set_xlabel('hours after 14:00 ET on previous NYSE day (24 = 14:00 ET event day)')
        ax.set_ylabel('bp')
        ax.legend(fontsize=7)
        ax.title.set_fontsize(9)
    fig.suptitle('Scheduled FOMC (14:00/14:15 releases) vs other consecutive-weekday windows, 2010-06..2024-10', fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fomc_hourly_profile.png'), dpi=120)
except Exception as e:
    print('plot failed', e)

pd.set_option('display.width', 250)
cols = ['root', 'window', 'period', 'costs', 'n_events', 'mean_bp', 'sd_bp', 't_nw_mean', 'hit_rate',
        'sharpe_per_trade', 'sharpe_ann_timeline', 'sharpe_ann_se', 'ann_contribution_pct',
        'nonfomc_mean_bp', 'fomc_minus_other_bp', 'fomc_minus_other_t_nw', 'excluded_invalid']
print(R[cols].round(3).to_string())
print(D.round(3).to_string())
print(tc.to_string())
print('FOMC events in data:', df['fomc'].sum(), 'of', len(fomc))
