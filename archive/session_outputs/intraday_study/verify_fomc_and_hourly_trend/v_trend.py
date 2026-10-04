"""Independent EWMAC recomputation (hourly and daily bars) on a chain rebuilt from the raw file."""
import os
import numpy as np
import pandas as pd
from v_common import build_chain, nyse_days, TZ, IS_END, COST, nw_t, HERE

EVAL0 = pd.Timestamp('2011-03-01')
LATER0, LATER1 = pd.Timestamp('2024-10-03'), pd.Timestamp('2026-10-02')
TAU = 0.10
H = [(8, 32), (16, 64), (32, 128), (64, 256)]
D = [(2, 8), (4, 16), (8, 32), (16, 64)]
days = nyse_days()
days = days[(days >= '2010-06-01') & (days <= '2026-10-05')]
close16 = (days + pd.Timedelta(hours=16)).tz_localize(TZ).tz_convert('UTC')


def ema(x, span):
    return pd.Series(x).ewm(span=span, adjust=False).mean().values


def buffered(target, half, can):
    pos = np.empty(len(target))
    p = 0.0
    for k in range(len(target)):
        if can[k] and not (np.isnan(target[k]) or np.isnan(half[k])):
            lo, hi = target[k] - half[k], target[k] + half[k]
            p = lo if p < lo else (hi if p > hi else p)
        pos[k] = p
    return pos


data = {}
for root in ['ES', 'ZN']:
    f = build_chain(root)
    f = f.iloc[1:].reset_index(drop=True)   # first bar has no return
    # 16:00 return day: first NYSE 16:00 at or after the bar end
    j = np.searchsorted(close16.values, f['end_utc'].values, side='left')
    f = f[j < len(days)].copy()
    f['rd'] = days[j[j < len(days)]]
    lr = f['lr'].values
    X = np.cumsum(lr)
    dd = f.groupby('rd').agg(lr=('lr', 'sum'))
    dd['last'] = f.reset_index().groupby('rd')['index'].max().values
    dd['X'] = X[dd['last'].values]
    dd['r'] = np.expm1(dd['lr'])
    # annualised vol, EWMA span 35 of squared daily returns, known at the previous day's close
    dd['sa'] = np.sqrt(pd.Series(dd['r'].values ** 2).ewm(span=35, adjust=False, min_periods=35).mean().values * 252)
    dd['sa_prev'] = dd['sa'].shift(1)
    dd['sd'] = np.sqrt(pd.Series(dd['lr'].values ** 2).ewm(span=35, adjust=False, min_periods=35).mean().values)
    sh = np.sqrt(pd.Series(lr ** 2).ewm(span=35 * 23, adjust=False, min_periods=35 * 23).mean().values)
    data[root] = dict(f=f, X=X, lr=lr, r=f['r'].values, rd=pd.DatetimeIndex(f['rd']), dd=dd, sh=sh,
                      sa_bar=dd['sa_prev'].reindex(f['rd']).values, roll=f['roll'].values)

raw = {}
for root, d in data.items():
    for a, b in H:
        raw[('h', a, b, root)] = (ema(d['X'], a) - ema(d['X'], b)) / d['sh']
    for a, b in D:
        raw[('d', a, b, root)] = (ema(d['dd']['X'].values, a) - ema(d['dd']['X'].values, b)) / d['dd']['sd'].values


def ismask(sys_, root):
    idx = data[root]['rd'] if sys_ == 'h' else data[root]['dd'].index
    return (idx >= EVAL0) & (idx <= IS_END)


fc = {}
for sys_, speeds in [('h', H), ('d', D)]:
    for a, b in speeds:
        sc = 10 / np.nanmean(np.concatenate([np.abs(raw[(sys_, a, b, r)][ismask(sys_, r)]) for r in data]))
        for r in data:
            fc[(sys_, f'{a}_{b}', r)] = np.clip(raw[(sys_, a, b, r)] * sc, -20, 20)
        print(sys_, a, b, 'scalar', round(sc, 3))
    keys = [f'{a}_{b}' for a, b in speeds]
    M = np.vstack([np.column_stack([fc[(sys_, k, r)][ismask(sys_, r)] for k in keys]) for r in data])
    M = M[~np.isnan(M).any(1)]
    C = np.corrcoef(M.T)
    w = np.ones(len(keys)) / len(keys)
    fdm = 1 / np.sqrt(w @ C @ w)
    print(sys_, 'FDM', round(fdm, 3))
    for r in data:
        fc[(sys_, 'comb', r)] = np.clip(np.nanmean(np.column_stack([fc[(sys_, k, r)] for k in keys]), 1) * fdm, -20, 20)


def run(sys_, k, root, buffer=True, lag=1):
    d = data[root]
    n = len(d['r'])
    half = 0.1 * TAU / d['sa_bar'] if buffer else np.zeros(n)
    if sys_ == 'h':
        target = fc[(sys_, k, root)] / 10 * TAU / d['sa_bar']
        can = np.ones(n, bool)
    else:
        target = np.full(n, np.nan)
        dd = d['dd']
        target[dd['last'].values] = fc[(sys_, k, root)] / 10 * TAU / dd['sa_prev'].values
        can = np.zeros(n, bool)
        can[dd['last'].values] = True
    can &= (d['rd'] >= EVAL0)
    pos = buffered(target, half, can)
    if lag == 2:
        pos = np.r_[0.0, pos[:-1]]
    held = np.r_[0.0, pos[:-1]]                  # decided at close of bar k, held over bar k+1
    gross = held * d['r']
    cost = np.abs(np.diff(np.r_[0.0, pos])) * COST[root] + d['roll'] * 2 * np.abs(held) * COST[root]
    df = pd.DataFrame({'g': gross, 'c': cost, 'tr': np.abs(np.diff(np.r_[0.0, pos])), 'ah': np.abs(held)},
                      index=d['rd']).groupby(level=0).agg({'g': 'sum', 'c': 'sum', 'tr': 'sum', 'ah': 'mean'})
    return df[df.index >= EVAL0]


def sr(x):
    return x.mean() / x.std() * np.sqrt(252)


rows = []
store = {}
for sys_, speeds in [('h', H), ('d', D)]:
    for k in [f'{a}_{b}' for a, b in speeds] + ['comb']:
        for buf in [True, False]:
            for lag in [1, 2]:
                if sys_ == 'd' and lag == 2:
                    continue
                es, zn = run(sys_, k, 'ES', buf, lag), run(sys_, k, 'ZN', buf, lag)
                idx = es.index.union(zn.index)
                es, zn = es.reindex(idx).fillna(0), zn.reindex(idx).fillna(0)
                port = 0.5 * (es + zn)
                for mkt, s in [('ES', es), ('ZN', zn), ('PORT', port)]:
                    store[(sys_, k, buf, lag, mkt)] = s
                    for per, (a, b) in [('IS', (EVAL0, IS_END)), ('later', (LATER0, LATER1))]:
                        x = s[(s.index >= a) & (s.index <= b)]
                        yrs = len(x) / 252
                        rt = x['tr'].sum() / (2 * x['ah'].mean()) / yrs if mkt != 'PORT' else np.nan
                        for cl, m in [('gross', 0), ('1x', 1), ('2x', 2)]:
                            y = x['g'] - m * x['c']
                            rows.append(dict(sys=sys_, speed=k, buffer=buf, lag=lag, mkt=mkt, period=per, costs=cl,
                                             sharpe=sr(y), t_nw10=nw_t(y.values, 10), se=np.sqrt((1 + sr(y) ** 2 / 2) / yrs),
                                             rt_per_yr=rt, cost_drag_pct=x['c'].mean() * 252 * 100 * m))
R = pd.DataFrame(rows)
R.to_csv(os.path.join(HERE, 'v_trend_results.csv'), index=False)
pd.set_option('display.width', 250)
main = R[(R.mkt == 'PORT') & R.buffer & (R.lag == 1)].pivot_table(index=['sys', 'speed'], columns=['period', 'costs'], values='sharpe')
print(main.round(2).to_string())
print(R[(R.mkt == 'PORT') & (R.period == 'IS') & (R.costs == '1x')].pivot_table(index=['sys', 'speed'], columns=['buffer', 'lag'], values='sharpe').round(2).to_string())
print(R[(R.mkt != 'PORT') & (R.period == 'IS') & R.buffer & (R.lag == 1) & (R.costs == 'gross')][['sys', 'speed', 'mkt', 'sharpe', 'rt_per_yr']].round(2).to_string())
print(R[(R.mkt == 'PORT') & (R.period == 'IS') & R.buffer & (R.lag == 1) & (R.costs == '1x')][['sys', 'speed', 't_nw10', 'se', 'cost_drag_pct']].round(2).to_string())

# paired block bootstrap: hourly comb minus daily comb, portfolio, IS
rng = np.random.default_rng(123)


def boot(a, b, m, block=20, reps=5000):
    A = a['g'] - m * a['c']
    B = b['g'] - m * b['c']
    df = pd.concat([A, B], axis=1).dropna()
    df = df[(df.index >= EVAL0) & (df.index <= IS_END)].values
    n = len(df)
    base = sr(df[:, 0]) - sr(df[:, 1])
    ds = []
    for _ in range(reps):
        st = rng.integers(0, n - block + 1, int(np.ceil(n / block)))
        i = (st[:, None] + np.arange(block)).ravel()[:n]
        x = df[i]
        ds.append(sr(x[:, 0]) - sr(x[:, 1]))
    ds = np.array(ds)
    return base, np.percentile(ds, 2.5), np.percentile(ds, 97.5), 2 * min((ds <= 0).mean(), (ds >= 0).mean())


for (k1, k2) in [('comb', 'comb'), ('64_256', '2_8'), ('8_32', '8_32')]:
    for m in [0, 1]:
        print('boot h', k1, '- d', k2, 'cost', m, np.round(boot(store[('h', k1, True, 1, 'PORT')], store[('d', k2, True, 1, 'PORT')], m), 3))
