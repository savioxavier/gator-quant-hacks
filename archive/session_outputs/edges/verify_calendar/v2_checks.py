import math, sys
import numpy as np, pandas as pd
sys.path.insert(0, "<solo-repo>")
exec(open("<scratch>/edges/verify_calendar/v1_recompute.py").read().split("cands = {")[0])
mine = pd.read_parquet(ED + "verify_calendar/v1_series.parquet")
tsy = mine[("CAL_TSY_ME_ZN", "net_1x")].dropna()
bench = pd.read_parquet(ED + "calendar/bench.parquet")
for w, a, b in (("IS", "2010-09-28", IS_END), ("later", L0, L1)):
    j = pd.concat([tsy, bench[["ES16", "S1", "F2", "ZN16"]]], axis=1, join="inner").loc[a:b].dropna()
    print(w, "corr", j.corr().iloc[0, 1:].round(3).to_dict())
from src import forward
fr = forward.stream_frames("F2", "FWD")
cf = fr["ex"]["C_F"]
j = pd.concat([tsy, cf], axis=1, join="inner").dropna()
print("corr with C_F IS", round(j.loc[:IS_END].corr().iloc[0, 1], 3), "later", round(j.loc[L0:].corr().iloc[0, 1], 3), "C_F SR IS", round(sr(cf.loc["2010-09-28":IS_END]), 3), "later", round(sr(cf.loc[L0:]), 3))

# gross unscaled ZN16 in-window per-window returns: by month-of-year (roll months 2,5,8,11) and by year
ex, roll = inst("ZN16")
m = win(-2, 0)
mid = pd.Series(np.where(m, cal.to_period("M").astype(str), None), index=cal)
pw = ex[m].groupby(mid[m]).sum()
pw.index = pd.PeriodIndex(pw.index, freq="M")
pwis = pw[(pw.index >= pd.Period("2010-09", "M")) & (pw.index <= pd.Period("2024-09", "M"))]
pwl = pw[pw.index >= pd.Period("2024-10", "M")]
print("IS windows", len(pwis), "mean bp", round(pwis.mean() * 1e4, 2), "t", round(pwis.mean() / pwis.std() * math.sqrt(len(pwis)), 2), "hit", round((pwis > 0).mean(), 3))
print("later windows", len(pwl), "mean bp", round(pwl.mean() * 1e4, 2), "t", round(pwl.mean() / pwl.std() * math.sqrt(len(pwl)), 2), "hit", round((pwl > 0).mean(), 3))
rm = pwis.index.month.isin([2, 5, 8, 11])
print("roll months mean bp", round(pwis[rm].mean() * 1e4, 2), "n", rm.sum(), "| other", round(pwis[~rm].mean() * 1e4, 2))
print("roll flags inside windows IS:", int(roll[m].loc[:IS_END].sum()))
print("by year mean bp/window:", (pwis.groupby(pwis.index.year).mean() * 1e4).round(1).to_dict())
# day-by-day contribution T-2, T-1, T
for o in (-2, -1, 0, 1, -3):
    mm = pd.Series(off_own == o, index=cal) if o <= 0 else pd.Series(off_prev == o, index=cal)
    a = ex[mm].loc["2010-09-28":IS_END]; bl = ex[mm].loc[L0:]
    print("offset", o, "IS mean bp", round(a.mean() * 1e4, 2), "t", round(a.mean() / a.std() * math.sqrt(len(a)), 2), "later", round(bl.mean() * 1e4, 2))
print("ZN16 all-day mean bp IS", round(ex.loc["2010-09-28":IS_END].mean() * 1e4, 2))
# bootstrap the later-window Sharpe CI (iid windows of months)
x = tsy.loc[L0:]
mon = (1 + x).groupby(x.index.to_period("M")).prod() - 1
rng = np.random.default_rng(1)
bs = [ (lambda s: s.mean() / s.std() * math.sqrt(12))(mon.sample(len(mon), replace=True, random_state=int(rng.integers(1e9)))) for _ in range(4000)]
print("later monthly SR", round(mon.mean() / mon.std() * math.sqrt(12), 3), "90% CI", np.round(np.quantile(bs, [0.05, 0.95]), 2))
xi = tsy.loc[:IS_END]; moni = (1 + xi).groupby(xi.index.to_period("M")).prod() - 1
print("IS monthly SR", round(moni.mean() / moni.std() * math.sqrt(12), 3))
# yearly
yr = (1 + tsy).groupby(tsy.index.year).prod() - 1
print("yearly net:", yr.round(3).to_dict())
# Deflated-ish: probability SR>0 given 3 declared variants median .93 ; haircut with original sleeve selection unknown
