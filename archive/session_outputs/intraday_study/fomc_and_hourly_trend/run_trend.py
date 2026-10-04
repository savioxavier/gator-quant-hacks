"""Part B: short-horizon trend (EWMAC) on hourly ES and ZN, versus daily-bar EWMAC on the same data.

Pre-specified grid (from the task, Carver-style EWMAC):
  hourly speeds (fast, slow) in bars: (8,32), (16,64), (32,128), (64,256), plus their combination
  daily speeds in days: (2,8), (4,16), (8,32), (16,64), plus their combination
  markets: ES, ZN and the 50/50 two-market portfolio
  execution lag: 1 bar (README convention) and 2 bars (one extra hour, robustness)
Forecast scalars and the forecast diversification multiplier are estimated on in-sample data only.
Evaluation starts 2011-03-01 for every variant (warm-up for the slowest EMA and the vol estimates).
"""
import os
import numpy as np
import pandas as pd
from common import (HERE, load_panel, COST, IS_END, LATER_START, LATER_END, sharpe_stats, nw_tstat,
                    paired_block_bootstrap_sharpe_diff)
from trend_engine import TAU, ewm_std, raw_ewmac, run_positions, pnl_from_positions

OUT = os.path.join(HERE, 'out_trend')
os.makedirs(OUT, exist_ok=True)
EVAL_START = pd.Timestamp('2011-03-01')
H_SPEEDS = [(8, 32), (16, 64), (32, 128), (64, 256)]
D_SPEEDS = [(2, 8), (4, 16), (8, 32), (16, 64)]
H_VOL_SPAN = 35 * 23      # per-bar vol: about 35 trading days of hourly bars
D_VOL_SPAN = 35

panel = load_panel()
panel = panel[panel['ret_date_1600'].notna()]

data = {}
for root, g in panel.groupby('root'):
    g = g.sort_values('bar_start_utc').reset_index(drop=True)
    r = g['ret_simple'].fillna(0.0).values
    lr = g['ret_log'].fillna(0.0).values
    rdate = pd.DatetimeIndex(g['ret_date_1600'])
    X = np.cumsum(lr)
    # daily 16:00 series
    gd = pd.DataFrame({'rdate': rdate, 'lr': lr, 'i': np.arange(len(g))})
    daily = gd.groupby('rdate').agg(lr=('lr', 'sum'), last_i=('i', 'max'))
    daily['r'] = np.expm1(daily['lr'])
    daily['X'] = X[daily['last_i'].values]
    daily['sig_ann'] = ewm_std(daily['r'].values, D_VOL_SPAN).values * np.sqrt(252)
    daily['sig_ann_prev'] = daily['sig_ann'].shift(1)
    daily['sig_d'] = ewm_std(daily['lr'].values, D_VOL_SPAN).values
    sig_ann_bar = daily['sig_ann_prev'].reindex(rdate).values
    sig_bar = ewm_std(lr, H_VOL_SPAN).values
    decision_daily = np.zeros(len(g), bool)
    decision_daily[daily['last_i'].values] = True
    data[root] = dict(g=g, r=r, lr=lr, X=X, rdate=rdate, daily=daily, sig_ann_bar=sig_ann_bar,
                      sig_bar=sig_bar, decision_daily=decision_daily, roll=g['is_roll'].values)

# ---------------- forecasts
raw = {}
for root, d in data.items():
    for f, s in H_SPEEDS:
        raw[('hourly', f'{f}_{s}', root)] = raw_ewmac(d['X'], f, s, d['sig_bar'])
    dd = d['daily']
    for f, s in D_SPEEDS:
        raw[('daily', f'{f}_{s}', root)] = raw_ewmac(dd['X'].values, f, s, dd['sig_d'].values)


def is_mask(system, root):
    d = data[root]
    dates = d['rdate'] if system == 'hourly' else d['daily'].index
    return (dates >= EVAL_START) & (dates <= IS_END)


scalars = {}
for system, speeds in [('hourly', H_SPEEDS), ('daily', D_SPEEDS)]:
    for f, s in speeds:
        k = f'{f}_{s}'
        vals = np.concatenate([np.abs(raw[(system, k, root)][is_mask(system, root)]) for root in data])
        scalars[(system, k)] = 10.0 / np.nanmean(vals)
fc = {}
for (system, k, root), v in raw.items():
    fc[(system, k, root)] = np.clip(v * scalars[(system, k)], -20, 20)
fdm = {}
for system, speeds in [('hourly', H_SPEEDS), ('daily', D_SPEEDS)]:
    keys = [f'{f}_{s}' for f, s in speeds]
    mats = []
    for root in data:
        m = is_mask(system, root)
        mats.append(np.column_stack([fc[(system, k, root)][m] for k in keys]))
    M = pd.DataFrame(np.vstack(mats)).dropna()
    C = M.corr().values
    w = np.full(len(keys), 1.0 / len(keys))
    fdm[system] = min(2.5, 1.0 / np.sqrt(w @ C @ w))
    for root in data:
        comb = np.mean(np.column_stack([fc[(system, k, root)] for k in keys]), axis=1) * fdm[system]
        fc[(system, 'combined', root)] = np.clip(comb, -20, 20)
pd.DataFrame([dict(system=k[0], speed=k[1], scalar=v) for k, v in scalars.items()] +
             [dict(system=k, speed='FDM', scalar=v) for k, v in fdm.items()]).to_csv(
    os.path.join(OUT, 'forecast_scalars_fdm_in_sample.csv'), index=False)

# ---------------- run every variant
PERIODS = {'IS_full_2011_2024': (EVAL_START, IS_END),
           'IS_2011_2014': (EVAL_START, pd.Timestamp('2014-12-31')),
           'IS_2015_2019': (pd.Timestamp('2015-01-01'), pd.Timestamp('2019-12-31')),
           'IS_2020_2024': (pd.Timestamp('2020-01-01'), IS_END),
           'later_2024_2026': (LATER_START, LATER_END)}
series = {}
diag = []
for (system, k, root), f in fc.items():
    d = data[root]
    n = len(d['r'])
    if system == 'hourly':
        target = f / 10.0 * TAU / d['sig_ann_bar']
        decision = np.ones(n, bool)
    else:
        dd = d['daily']
        target = np.full(n, np.nan)
        target[dd['last_i'].values] = f / 10.0 * TAU / dd['sig_ann_prev'].values
        decision = d['decision_daily']
    buf = 0.10 * TAU / d['sig_ann_bar']
    # no positions before the evaluation start
    pre = d['rdate'] < EVAL_START
    target = np.where(pre, np.nan, target)
    pos = run_positions(target, buf, decision & ~pre)
    for lag in (1, 2):
        gross, cost, held, trades = pnl_from_positions(pos, d['r'], d['roll'], COST[root], lag=lag)
        df = pd.DataFrame({'gross': gross, 'cost': cost, 'trades': trades, 'absheld': np.abs(held),
                           'held': held, 'rdate': d['rdate']})
        day = df.groupby('rdate').agg(gross=('gross', 'sum'), cost=('cost', 'sum'), trades=('trades', 'sum'),
                                      absheld=('absheld', 'mean'), held=('held', 'mean'))
        day = day[day.index >= EVAL_START]
        series[(system, k, root, lag)] = day
        m = (day.index <= IS_END)
        yrs = m.sum() / 252
        f_is = f[(d['rdate'] if system == 'hourly' else d['daily'].index) >= EVAL_START]
        diag.append(dict(system=system, speed=k, market=root, lag=lag,
                         turnover_roundtrips_per_year_IS=day['trades'][m].sum() / (2 * day['absheld'][m].mean()) / yrs,
                         mean_abs_position_IS=day['absheld'][m].mean(), mean_position_IS=day['held'][m].mean(),
                         mean_forecast=np.nanmean(f_is), mean_abs_forecast=np.nanmean(np.abs(f_is)),
                         share_capped=np.nanmean(np.abs(f_is) >= 20)))

# portfolio = 50/50 of the two markets' subsystem returns (an IDM would rescale only, Sharpe unchanged)
for system, speeds in [('hourly', H_SPEEDS), ('daily', D_SPEEDS)]:
    for k in [f'{f}_{s}' for f, s in speeds] + ['combined']:
        for lag in (1, 2):
            a = series[(system, k, 'ES', lag)]
            b = series[(system, k, 'ZN', lag)]
            idx = a.index.union(b.index)
            a = a.reindex(idx).fillna(0.0)
            b = b.reindex(idx).fillna(0.0)
            p = pd.DataFrame({'gross': 0.5 * (a['gross'] + b['gross']), 'cost': 0.5 * (a['cost'] + b['cost']),
                              'trades': 0.5 * (a['trades'] + b['trades']), 'absheld': 0.5 * (a['absheld'] + b['absheld']),
                              'held': np.nan})
            series[(system, k, 'PORT', lag)] = p

rows = []
for (system, k, root, lag), day in series.items():
    for pname, (a, b) in PERIODS.items():
        s = day[(day.index >= a) & (day.index <= b)]
        for cl, mult in [('gross', 0), ('net_1x', 1), ('net_2x', 2)]:
            x = s['gross'] - mult * s['cost']
            st = sharpe_stats(x)
            rows.append(dict(variant=f'{system}_{k}_{root}_lag{lag}', system=system, speed=k, market=root, lag=lag,
                             period=pname, costs=cl, sharpe=st['sharpe'], sharpe_se=st['sharpe_se'], t_nw=st['t_nw'],
                             ann_ret_pct=st['mean_ann'] * 100, ann_vol_pct=st['vol_ann'] * 100,
                             cost_drag_pct=s['cost'].mean() * 252 * 100 * mult, n_days=st['n_days']))
R = pd.DataFrame(rows)
R.to_csv(os.path.join(OUT, 'trend_results_all.csv'), index=False)
Dg = pd.DataFrame(diag)
Dg.to_csv(os.path.join(OUT, 'trend_diagnostics.csv'), index=False)

# annual Sharpe of the main variants (lag 1, portfolio)
ann = []
for (system, k, root, lag), day in series.items():
    if lag != 1:
        continue
    for cl, mult in [('gross', 0), ('net_1x', 1)]:
        x = day['gross'] - mult * day['cost']
        for y, xs in x.groupby(x.index.year):
            ann.append(dict(system=system, speed=k, market=root, costs=cl, year=y, ret_pct=xs.sum() * 100,
                            sharpe=xs.mean() / xs.std() * np.sqrt(252) if xs.std() > 0 else np.nan))
pd.DataFrame(ann).to_csv(os.path.join(OUT, 'trend_annual.csv'), index=False)

# store daily series for later checks
store = []
for (system, k, root, lag), day in series.items():
    t = day[['gross', 'cost']].copy()
    t['system'], t['speed'], t['market'], t['lag'] = system, k, root, lag
    store.append(t.reset_index().rename(columns={'index': 'date', 'rdate': 'date'}))
pd.concat(store).to_parquet(os.path.join(OUT, 'trend_daily_series.parquet'))

# ---------------- paired block bootstraps (in-sample, net 1x, lag 1, portfolio)
boots = []
def net(system, k, root='PORT', lag=1, mult=1, a=EVAL_START, b=IS_END):
    d = series[(system, k, root, lag)]
    d = d[(d.index >= a) & (d.index <= b)]
    return d['gross'] - mult * d['cost']
pairs = [(('hourly', 'combined'), ('daily', 'combined')), (('hourly', '64_256'), ('daily', '2_8')),
         (('hourly', '64_256'), ('daily', '4_16')), (('hourly', '8_32'), ('daily', '8_32'))]
for (s1, k1), (s2, k2) in pairs:
    for mult, cl in [(0, 'gross'), (1, 'net_1x')]:
        bb = paired_block_bootstrap_sharpe_diff(net(s1, k1, mult=mult), net(s2, k2, mult=mult), block=20, reps=5000)
        boots.append(dict(a=f'{s1}_{k1}_PORT', b=f'{s2}_{k2}_PORT', costs=cl, **bb))
# 1-bar vs 2-bar execution lag (hourly combined portfolio)
for mult, cl in [(0, 'gross'), (1, 'net_1x')]:
    bb = paired_block_bootstrap_sharpe_diff(net('hourly', 'combined', lag=1, mult=mult),
                                            net('hourly', 'combined', lag=2, mult=mult), block=20, reps=5000)
    boots.append(dict(a='hourly_combined_PORT_lag1', b='hourly_combined_PORT_lag2', costs=cl, **bb))
B = pd.DataFrame(boots)
B.to_csv(os.path.join(OUT, 'trend_bootstrap_pairs.csv'), index=False)

# ---------------- engine cross-check: pure daily computation for the daily system, lag 1
chk = []
for root, d in data.items():
    dd = d['daily'].copy()
    for f, s in D_SPEEDS:
        k = f'{f}_{s}'
        target = fc[('daily', k, root)] / 10.0 * TAU / dd['sig_ann_prev'].values
        buf = 0.10 * TAU / dd['sig_ann_prev'].values
        pre = dd.index < EVAL_START
        pos = run_positions(np.where(pre, np.nan, target), buf, ~pre)
        held = np.r_[0.0, pos[:-1]]
        gross = pd.Series(held * dd['r'].values, index=dd.index)
        gross = gross[gross.index >= EVAL_START]
        h = series[('daily', k, root, 1)]['gross']
        al = pd.concat([gross, h], axis=1).dropna()
        al = al[al.index <= IS_END]
        chk.append(dict(market=root, speed=k, corr=al.corr().iloc[0, 1],
                        sr_pure_daily=al.iloc[:, 0].mean() / al.iloc[:, 0].std() * np.sqrt(252),
                        sr_hourly_engine=al.iloc[:, 1].mean() / al.iloc[:, 1].std() * np.sqrt(252)))
pd.DataFrame(chk).to_csv(os.path.join(OUT, 'engine_crosscheck.csv'), index=False)

pd.set_option('display.width', 250)
main = R[(R.lag == 1) & (R.period == 'IS_full_2011_2024')].pivot_table(
    index=['system', 'speed', 'market'], columns='costs', values='sharpe').round(2)
print(main.to_string())
print(R[(R.lag == 1) & (R.market == 'PORT') & (R.costs == 'net_1x')].pivot_table(
    index=['system', 'speed'], columns='period', values='sharpe').round(2).to_string())
print(R[(R.lag == 2) & (R.period == 'IS_full_2011_2024') & (R.market == 'PORT')].pivot_table(
    index=['system', 'speed'], columns='costs', values='sharpe').round(2).to_string())
print(Dg.round(3).to_string())
print(B.round(3).to_string())
print(pd.DataFrame(chk).round(3).to_string())
print(scalars, fdm)
