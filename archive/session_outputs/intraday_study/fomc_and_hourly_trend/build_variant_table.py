"""Collect every variant of Parts A and B into one table: all_variants.csv (one row per variant x period
x cost level). Counts distinct variants."""
import os
import pandas as pd
from common import HERE

A = pd.read_csv(os.path.join(HERE, 'out_fomc', 'fomc_results.csv'))
B = pd.read_csv(os.path.join(HERE, 'out_trend', 'trend_results_all.csv'))
C = pd.read_csv(os.path.join(HERE, 'out_trend', 'proxy_2009_results.csv'))
C = C[C['period'] != 'diff_post2009_minus_pre']

a = pd.DataFrame({'part': 'A_preFOMC_long', 'variant': 'fomc_' + A['window'] + '_' + A['root'], 'market': A['root'],
                  'spec': A['window'], 'system': 'hourly_event', 'lag': 1, 'period': A['period'], 'costs': A['costs'],
                  'n_obs': A['n_events'], 'obs_unit': 'events', 'mean_per_trade_bp': A['mean_bp'],
                  'sharpe_per_trade': A['sharpe_per_trade'], 'sharpe_ann': A['sharpe_ann_timeline'],
                  'sharpe_se': A['sharpe_ann_se'], 't_nw': A['t_nw_mean'], 'ann_ret_pct': A['ann_contribution_pct'],
                  'ann_vol_pct': float('nan'), 'fomc_minus_other_bp': A['fomc_minus_other_bp'],
                  'fomc_minus_other_t_nw': A['fomc_minus_other_t_nw']})
b = pd.DataFrame({'part': 'B_trend_ES_ZN_panel', 'variant': B['variant'], 'market': B['market'], 'spec': B['speed'],
                  'system': B['system'], 'lag': B['lag'], 'period': B['period'], 'costs': B['costs'],
                  'n_obs': B['n_days'], 'obs_unit': 'days', 'sharpe_ann': B['sharpe'], 'sharpe_se': B['sharpe_se'],
                  't_nw': B['t_nw'], 'ann_ret_pct': B['ann_ret_pct'], 'ann_vol_pct': B['ann_vol_pct']})
c = pd.DataFrame({'part': 'B_trend_daily_proxy_1990', 'variant': C['variant'], 'market': C['market'],
                  'spec': C['speed'], 'system': 'daily_proxy', 'lag': 1, 'period': C['period'], 'costs': C['costs'],
                  'n_obs': C['n_days'], 'obs_unit': 'days', 'sharpe_ann': C['sharpe'], 'sharpe_se': C['sharpe_se'],
                  't_nw': C['t_nw'], 'ann_ret_pct': C['ann_ret_pct'], 'ann_vol_pct': C['ann_vol_pct']})
T = pd.concat([a, b, c], ignore_index=True)
T.to_csv(os.path.join(HERE, 'all_variants.csv'), index=False)
cnt = T.groupby('part')['variant'].nunique()
print(cnt.to_string())
print('distinct variants:', T['variant'].nunique(), 'rows:', len(T))
