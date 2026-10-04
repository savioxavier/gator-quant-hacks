"""Independent rebuild of the front-contract hourly chain from the raw Databento file (no shared panel)."""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = '<home>/.cache/gqh/databento_raw/glbx_ohlcv1h_v01_es_zn.parquet'
GQH = os.environ.get('GQH_DATA_DIR', '<home>/.cache/gqh')
TZ = 'America/New_York'
IS_END = pd.Timestamp('2024-10-02')
COST = {'ES': 1.0e-4, 'ZN': 1.5e-4}

# scheduled FOMC statement days, typed independently (federalreserve.gov fomccalendars / fomchistorical pages)
FOMC = """
2010-06-23 2010-08-10 2010-09-21 2010-11-03 2010-12-14
2011-01-26 2011-03-15 2011-04-27 2011-06-22 2011-08-09 2011-09-21 2011-11-02 2011-12-13
2012-01-25 2012-03-13 2012-04-25 2012-06-20 2012-08-01 2012-09-13 2012-10-24 2012-12-12
2013-01-30 2013-03-20 2013-05-01 2013-06-19 2013-07-31 2013-09-18 2013-10-30 2013-12-18
2014-01-29 2014-03-19 2014-04-30 2014-06-18 2014-07-30 2014-09-17 2014-10-29 2014-12-17
2015-01-28 2015-03-18 2015-04-29 2015-06-17 2015-07-29 2015-09-17 2015-10-28 2015-12-16
2016-01-27 2016-03-16 2016-04-27 2016-06-15 2016-07-27 2016-09-21 2016-11-02 2016-12-14
2017-02-01 2017-03-15 2017-05-03 2017-06-14 2017-07-26 2017-09-20 2017-11-01 2017-12-13
2018-01-31 2018-03-21 2018-05-02 2018-06-13 2018-08-01 2018-09-26 2018-11-08 2018-12-19
2019-01-30 2019-03-20 2019-05-01 2019-06-19 2019-07-31 2019-09-18 2019-10-30 2019-12-11
2020-01-29 2020-04-29 2020-06-10 2020-07-29 2020-09-16 2020-11-05 2020-12-16
2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28 2021-09-22 2021-11-03 2021-12-15
2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14
2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13
2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18
2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10
2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16
""".split()
FOMC = pd.DatetimeIndex(FOMC)
# 12:30 ET releases (2011-12 press-conference meetings); 14:15 for other meetings through 2012; 14:00 from 2013
REL1230 = pd.DatetimeIndex(['2011-04-27', '2011-06-22', '2011-11-02', '2012-01-25', '2012-04-25',
                            '2012-06-20', '2012-09-13', '2012-12-12'])


def nyse_days():
    e = pd.read_parquet(os.path.join(GQH, 'etf_daily.parquet'))
    e = e[e['ticker'] == 'SPY']
    if 'date' in e.columns:
        d = pd.to_datetime(e['date'])
    else:
        d = pd.to_datetime(e.index)
    return pd.DatetimeIndex(sorted(set(pd.DatetimeIndex(d).normalize())))


def build_chain(root):
    """Front (.v.0) bar chain; each bar's return uses the same instrument's close as of the previous
    front bar's timestamp (asof over all bars of that instrument, .v.0 or .v.1)."""
    raw = pd.read_parquet(RAW)
    raw = raw[raw['symbol'].str.startswith(root + '.')].copy()
    allbars = raw[['ts_event', 'instrument_id', 'close']].drop_duplicates(['ts_event', 'instrument_id'])
    f = raw[raw['symbol'] == root + '.v.0'].sort_values('ts_event').reset_index(drop=True)
    f['prev_ts'] = f['ts_event'].shift(1)
    # asof lookup of each instrument's close at prev_ts
    allbars = allbars.sort_values('ts_event')
    q = f[['prev_ts', 'instrument_id']].dropna().copy()
    q['row'] = q.index
    q = q.sort_values('prev_ts')
    m = pd.merge_asof(q, allbars.rename(columns={'ts_event': 'prev_ts', 'close': 'pclose'}),
                      on='prev_ts', by='instrument_id', direction='backward')
    m = m.set_index('row')['pclose']
    f['pclose'] = m.reindex(f.index)
    f['r'] = f['close'] / f['pclose'] - 1
    f['lr'] = np.log1p(f['r'])
    f['roll'] = f['instrument_id'] != f['instrument_id'].shift(1)
    f.loc[0, 'roll'] = False
    f['end_utc'] = f['ts_event'] + pd.Timedelta(hours=1)
    f['end_et'] = f['end_utc'].dt.tz_convert(TZ)
    f['start_et'] = f['ts_event'].dt.tz_convert(TZ)
    return f


def nw_t(x, lags):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    e = x - x.mean()
    s = e @ e / n
    for L in range(1, lags + 1):
        s += 2 * (1 - L / (lags + 1)) * (e[L:] @ e[:-L]) / n
    return x.mean() / np.sqrt(s / n)
