import math
import numpy as np, pandas as pd
import statsmodels.api as sm
D = "<home>/.cache/gqh/"; ED = "<scratch>/edges/"
ff = pd.read_parquet(D + "ff_daily.parquet").set_index("date"); ff.index = pd.to_datetime(ff.index)
r = ff["Mkt_RF"].dropna()
if r.abs().mean() > 0.05: r = r / 100
cal = r.index
s = pd.Series(np.arange(len(cal)), index=cal); per = cal.to_period("M")
i = np.arange(len(cal)); lastpos = s.groupby(per).transform("max").to_numpy(); firstpos = s.groupby(per).transform("min").to_numpy()
off_own = np.where(per == per[-1], -999, i - lastpos); off_prev = i - firstpos + 1
def win(a, b):
    m = np.zeros(len(cal), bool)
    if a <= 0: m |= (off_own >= a) & (off_own <= min(b, 0))
    if b >= 1: m |= (off_prev >= max(a, 1)) & (off_prev <= b)
    return pd.Series(m, index=cal)
def dt(y, m, a, b):
    y = y.loc[a:b]; d = m.reindex(y.index).astype(float)
    f = sm.OLS(y, sm.add_constant(d)).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    return round(f.params.iloc[1] * 1e4, 2), round(f.tvalues.iloc[1], 2), int(d.sum())
tom = win(-1, 3)
print("FF TOM T-1..T+3 diff bp, t, n_in")
for a, b in (("1963-07-01", "1987-12-31"), ("1988-01-01", "2007-12-31"), ("2008-01-01", "2024-10-02"), ("2024-10-03", "2026-08-31")):
    print(" ", a, b, dt(r, tom, a, b))
# pre-holiday: weekday gaps excluding known unscheduled closures (approx, uses analyst list from summary.json)
import json
sm_ = json.load(open(ED + "calendar/summary.json"))
uns = pd.DatetimeIndex(sm_["ff_unscheduled_closures_excluded"])
wk = pd.bdate_range(cal[0], cal[-1]); miss = wk.difference(cal).difference(uns)
pos = cal.searchsorted(miss) - 1
pre = pd.Series(False, index=cal); pre.iloc[np.unique(pos[pos >= 0])] = True
print("FF pre-holiday diff")
for a, b in (("1963-07-01", "1982-12-31"), ("1983-01-01", "1990-12-31"), ("1991-01-01", "2024-10-02"), ("2024-10-03", "2026-08-31")):
    print(" ", a, b, dt(r, pre, a, b))
# FOMC even vs odd
fomc = pd.to_datetime(pd.read_csv(ED + "calendar/fomc_scheduled.csv")["day0"])
c2 = cal[cal >= "1994-01-01"]
idx0 = c2.get_indexer(pd.DatetimeIndex(fomc[(fomc >= c2[0]) & (fomc <= c2[-1])]))
print("fomc not in FF cal:", int((idx0 < 0).sum()))
idx0 = idx0[idx0 >= 0]; ii = np.arange(len(c2))
last = pd.Series(np.where(np.isin(ii, idx0), ii, np.nan)).ffill().to_numpy(); k = ii - last; k[np.isin(ii + 1, idx0)] = -1
kk = pd.Series(k, index=c2)
ev = (kk.between(-1, 3) | kk.between(9, 13) | kk.between(19, 23) | kk.between(29, 33)).fillna(False)
print("FF FOMC even-minus-other")
for a, b in (("1994-01-01", "2016-12-31"), ("2017-01-01", "2024-10-02"), ("2024-10-03", "2026-08-31")):
    print(" ", a, b, dt(r, ev, a, b))
ext = pd.read_csv(ED + "calendar/long_history_evidence.csv")
print(ext[ext.source == "FF_Mkt_RF"][["rule", "split", "diff_bp", "diff_t_nw", "n_in"]].round(2).to_string())
