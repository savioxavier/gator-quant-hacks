"""Checks on Part B: engine sanity (constant long position), long-bias versus timing (alpha against
the market's own 16:00 return), and a cumulative-PnL figure. Reads out_trend/trend_daily_series.parquet."""
import os
import numpy as np
import pandas as pd
from common import HERE, load_panel, IS_END, LATER_START, nw_regression
from trend_engine import pnl_from_positions

OUT = os.path.join(HERE, 'out_trend')
EVAL_START = pd.Timestamp('2011-03-01')
S = pd.read_parquet(os.path.join(OUT, 'trend_daily_series.parquet'))
panel = load_panel()
panel = panel[panel['ret_date_1600'].notna()]

# market 16:00 daily excess return from the panel
mkt = {}
for root, g in panel.groupby('root'):
    mkt[root] = g.groupby('ret_date_1600')['ret_log'].sum().pipe(np.expm1)
mkt['PORT'] = None

# 1) engine sanity: constant 1x long through the hourly engine vs the 16:00 daily return
san = []
for root, g in panel.groupby('root'):
    g = g.sort_values('bar_start_utc')
    pos = np.ones(len(g))
    gross, cost, held, trades = pnl_from_positions(pos, g['ret_simple'].fillna(0).values, g['is_roll'].values, 1e-4)
    d = pd.Series(gross, index=pd.DatetimeIndex(g['ret_date_1600'])).groupby(level=0).sum()
    d = d[(d.index >= EVAL_START) & (d.index <= IS_END)]
    m = mkt[root].reindex(d.index)
    san.append(dict(market=root, corr=d.corr(m), sr_engine=d.mean() / d.std() * np.sqrt(252),
                    sr_16h=m.mean() / m.std() * np.sqrt(252), mean_diff_bp_per_day=(d - m).mean() * 1e4))
pd.DataFrame(san).to_csv(os.path.join(OUT, 'engine_sanity_constant_long.csv'), index=False)

# 2) alpha versus the market's own return (in-sample, lag 1, net 1x and gross)
rows = []
for (system, speed, market), g in S[S['lag'] == 1].groupby(['system', 'speed', 'market']):
    if market == 'PORT':
        continue
    g = g.set_index('date')
    g = g[(g.index >= EVAL_START) & (g.index <= IS_END)]
    m = mkt[market].reindex(g.index).fillna(0)
    for cl, mult in [('gross', 0), ('net_1x', 1)]:
        y = (g['gross'] - mult * g['cost']).values
        b, se, t = nw_regression(y, np.c_[np.ones(len(y)), m.values], lags=10)
        rows.append(dict(system=system, speed=speed, market=market, costs=cl, alpha_ann_pct=b[0] * 252 * 100,
                         alpha_t_nw=t[0], beta=b[1], beta_t=t[1]))
A = pd.DataFrame(rows)
A.to_csv(os.path.join(OUT, 'trend_alpha_vs_own_market.csv'), index=False)

# 3) figure
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for system, speed in [('hourly', '8_32'), ('hourly', '64_256'), ('hourly', 'combined'),
                          ('daily', '2_8'), ('daily', '16_64'), ('daily', 'combined')]:
        g = S[(S.system == system) & (S.speed == speed) & (S.market == 'PORT') & (S.lag == 1)].set_index('date')
        x = (g['gross'] - g['cost']).cumsum() * 100
        ax.plot(x.index, x.values, label=f'{system} {speed} (net 1x)', lw=1)
    ax.axvspan(LATER_START, x.index.max(), color='grey', alpha=0.15, label='later window (descriptive)')
    ax.axhline(0, color='k', lw=0.5)
    ax.set_ylabel('cumulative return, % of capital')
    ax.set_title('EWMAC on ES+ZN (50/50, 10% vol per market): hourly vs daily bars, net of 1x costs')
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'trend_cumulative_net.png'), dpi=120)
except Exception as e:
    print('plot failed', e)

pd.set_option('display.width', 200)
print(pd.DataFrame(san).round(4).to_string())
print(A.round(3).to_string())
