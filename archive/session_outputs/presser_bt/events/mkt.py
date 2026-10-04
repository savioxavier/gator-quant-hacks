"""Market-data helpers for the presser event table (Databento GLBX.MDP3 ohlcv-1m / ohlcv-1s / bbo-1s;
ts_event = bar start in UTC; prices in index points; continuous volume-ranked front .v.0)."""
import os, glob
import numpy as np, pandas as pd

CACHE = r'<home>/.cache/gqh/presser'
SYMS = ['ZT.v.0', 'ZF.v.0', 'ZN.v.0', 'ES.v.0']
ET = 'America/New_York'
# tick size in points and $ per point (contract multiplier): CME specs; ZT tick checked empirically in the data
# (only 1/128-point prices through 2018-12-19, 1/256-point prices from 2019-01-30 on).
MULT = {'ZT': 2000.0, 'ZF': 1000.0, 'ZN': 1000.0, 'ES': 50.0}

def tick(root, date):
    if root == 'ZT':
        return 1 / 128 if pd.Timestamp(date) < pd.Timestamp('2019-01-01') else 1 / 256
    return {'ZF': 1 / 128, 'ZN': 1 / 64, 'ES': 0.25}[root]

def load_1m():
    x = pd.read_parquet(os.path.join(CACHE, 'ohlcv-1m__all_2016_2026.parquet'))
    x['t'] = x.ts_event.dt.tz_convert(ET)
    x['d'] = x.t.dt.strftime('%Y%m%d')
    return x

def load_1s():
    x = pd.read_parquet(os.path.join(CACHE, 'ohlcv-1s__all_2016_2026.parquet'))
    x['t'] = x.ts_event.dt.tz_convert(ET)
    x['d'] = x.t.dt.strftime('%Y%m%d')
    return x

def load_bbo(d):
    f = os.path.join(CACHE, f'bbo-1s__{d}.parquet')
    if not os.path.exists(f):
        return None
    b = pd.read_parquet(f)
    b['t'] = b.ts_recv.dt.tz_convert(ET)
    return b

class Bars:
    """1m bars of one symbol on one day, indexed by bar start (ET)."""
    def __init__(self, g, width_s=60):
        self.g = g.sort_values('t').set_index('t')
        self.w = pd.Timedelta(seconds=width_s)

    def asof(self, t):
        """close of the last bar completed by t (bar start + width <= t); returns (price, staleness_s)."""
        g = self.g[self.g.index + self.w <= t]
        if not len(g):
            return np.nan, np.nan
        return float(g.close.iloc[-1]), (t - (g.index[-1] + self.w)).total_seconds()

    def next_open(self, t):
        """open of the first bar starting at or after t; returns (price, delay_s)."""
        g = self.g[self.g.index >= t]
        if not len(g):
            return np.nan, np.nan
        return float(g.open.iloc[0]), (g.index[0] - t).total_seconds()
