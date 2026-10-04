"""Independent re-implementation of the four calendar candidates (no repo engine / calendar_utils used).
Reads raw cached parquet files directly."""
import math, json
import numpy as np, pandas as pd
D = "<home>/.cache/gqh/"
ED = "<scratch>/edges/"
IS_END = pd.Timestamp("2024-10-02"); L0 = pd.Timestamp("2024-10-03"); L1 = pd.Timestamp("2026-10-02")

etf = pd.read_parquet(D + "etf_daily.parquet")
cal = pd.DatetimeIndex(sorted(etf.loc[etf.ticker == "SPY", "date"].unique()))
cal = cal[cal <= L1]
rf = pd.read_parquet(D + "rf_daily.parquet"); rf = rf.set_index("date")["rf"] if "date" in rf.columns else rf["rf"]
rf.index = pd.to_datetime(rf.index)
fut = pd.concat([pd.read_parquet(D + "futures_1600.parquet"), pd.read_parquet(D + "futures_daily.parquet")])

def inst(tk):
    g = fut[fut.ticker == tk].set_index("date").sort_index()
    c = g["close"].reindex(cal)
    ex = c.pct_change(fill_method=None) - rf.reindex(cal).ffill().fillna(0)
    roll = g["roll"].reindex(cal).fillna(0)
    return ex, roll

# --- my own month-end offsets on the realised calendar (unscheduled closures ignored; differences tiny)
s = pd.Series(np.arange(len(cal)), index=cal)
per = cal.to_period("M")
lastpos = s.groupby(per).transform("max").to_numpy()
firstpos = s.groupby(per).transform("min").to_numpy()
i = np.arange(len(cal))
off_own = i - lastpos            # 0 on T
off_prev = i - firstpos + 1      # 1 on first day of month
# the final month (Oct 2026) is incomplete
inc = per == per[-1]
off_own = np.where(inc, -999, off_own)
def win(a, b):
    m = np.zeros(len(cal), bool)
    if a <= 0: m |= (off_own >= a) & (off_own <= min(b, 0))
    if b >= 1: m |= (off_prev >= max(a, 1)) & (off_prev <= b)
    return pd.Series(m, index=cal)

def run(mask, tk, c1, cap=5.0, scaled=True):
    ex, roll = inst(tk)
    sig = np.sqrt((ex ** 2).ewm(com=60, min_periods=60).mean() * 252)
    f = mask.astype(float).rolling(252, min_periods=126).mean()
    m = mask.to_numpy(); L = np.zeros(len(cal))
    start = -1
    for j in range(len(cal)):
        if m[j]:
            if j == 0 or not m[j - 1]:
                start = j
                d = j - 2
                sv, fv = sig.iloc[d], f.iloc[d]
                lev = min(cap, 0.10 / (sv * math.sqrt(fv))) if (np.isfinite(sv) and np.isfinite(fv) and fv > 0) else 0.0
                if not scaled and lev > 0: lev = 1.0
            L[j] = lev
    L = pd.Series(L, index=cal)
    gross = L * ex.fillna(0)
    # costs: |change in position| at each close; entry trade charged on first held day, exit on next day
    dL = (L - L.shift(1).fillna(0)).abs()
    trade = dL + 2 * L * roll
    out = {}
    for lab, cm in (("net_1x", 1), ("net_2x", 2), ("gross", 0)):
        out[lab] = gross - trade * c1 * cm / 1e4
    return pd.DataFrame(out), L, trade

def sr(x): x = x.dropna(); return x.mean() / x.std() * math.sqrt(252)
def mdd(x): e = (1 + x).cumprod(); return (e / e.cummax() - 1).min()
def nwt(x, lags=None):
    x = x.dropna().to_numpy(); n = len(x); lags = lags or int(4 * (n / 100) ** (2 / 9))
    e = x - x.mean(); v = e @ e / n
    for k in range(1, lags + 1): v += 2 * (1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / n
    return x.mean() / math.sqrt(v / n)

# pre-holiday: weekday gaps in the NYSE calendar (my own: any weekday missing that is not an unscheduled closure)
UNSCHED = pd.DatetimeIndex(["2012-10-29", "2012-10-30", "2018-12-05", "2025-01-09", "2007-01-02", "2004-06-11", "2001-09-11", "2001-09-12", "2001-09-13", "2001-09-14"])
wk = pd.bdate_range(cal[0], cal[-1]); missing = wk.difference(cal).difference(UNSCHED)
pos = cal.searchsorted(missing) - 1
pre = pd.Series(False, index=cal); pre.iloc[np.unique(pos[pos >= 0])] = True

fomc = pd.to_datetime(pd.read_csv(ED + "calendar/fomc_scheduled.csv")["day0"])
fomc = pd.DatetimeIndex(fomc[(fomc >= cal[0]) & (fomc <= cal[-1])])
idx0 = cal.get_indexer(fomc); assert (idx0 >= 0).all()
last = pd.Series(np.where(np.isin(i, idx0), i, np.nan)).ffill().to_numpy()
k = i - last
k[np.isin(i + 1, idx0)] = -1
kk = pd.Series(k, index=cal)
fomc_even = (kk.between(-1, 3) | kk.between(9, 13) | kk.between(19, 23) | kk.between(29, 33)).fillna(False)

cands = {
    "CAL_TSY_ME_ZN": (win(-2, 0), "ZN16", 1.0),
    "CAL_TOM_ES": (win(-1, 3), "ES16", 0.75),
    "CAL_PREHOL_ES": (pre, "ES16", 0.75),
    "CAL_FOMC_EVEN_ES": (fomc_even, "ES16", 0.75),
    "TSY_V2_T-1..T": (win(-1, 0), "ZN16", 1.0),
    "TSY_F_ZN": (win(-2, 0), "F_ZN", 1.0),
    "PREHOL_exTOM": (pre & ~win(-1, 3), "ES16", 0.75),
}
rows = []
mine = {}
for nm, (mask, tk, c1) in cands.items():
    df, L, tr = run(mask, tk, c1)
    st = (L > 0).idxmax()
    df = df.loc[st:]; mine[nm] = df
    for w, a, b in (("IS", st, IS_END), ("later", L0, L1), ("IS_pre2019", st, pd.Timestamp("2018-12-31")), ("IS_2019on", pd.Timestamp("2019-01-01"), IS_END)):
        x = df.loc[a:b]
        yrs = len(x) / 252
        se = math.sqrt((1 + sr(x.net_1x) ** 2 / 2) / yrs)
        yr = (1 + x.net_1x).groupby(x.index.year).prod() - 1
        rows.append(dict(cand=nm, win=w, start=str(x.index[0].date()), n=len(x), sr1=sr(x.net_1x), sr2=sr(x.net_2x), srg=sr(x.gross),
                         se=se, nw_t=nwt(x.net_1x), vol=x.net_1x.std() * math.sqrt(252), ann=x.net_1x.mean() * 252,
                         mdd=mdd(x.net_1x), pospct=(yr > 0).mean(), worst=yr.min(),
                         turn=tr.loc[a:b].sum() / yrs, cap_share=float((L.loc[a:b][L.loc[a:b] > 0] >= 4.999).mean())))
    # compare with analyst file
    try:
        f = pd.read_parquet(ED + f"series/{nm}.parquet")
        j = pd.concat([f.net_1x, df.net_1x], axis=1, join="inner").dropna()
        jis = j.loc[:IS_END]
        print(nm, "file IS SR", round(sr(f.net_1x.loc[:IS_END]), 3), "2x", round(sr(f.net_2x.loc[:IS_END]), 3), "gross", round(sr(f.gross.loc[:IS_END]), 3),
              "later", round(sr(f.net_1x.loc[L0:]), 3), round(sr(f.net_2x.loc[L0:]), 3), "| corr mine-vs-file", round(jis.corr().iloc[0, 1], 4),
              "maxabsdiff", float((jis.iloc[:, 0] - jis.iloc[:, 1]).abs().max()), "file mdd IS", round(mdd(f.net_1x.loc[:IS_END]), 3))
    except FileNotFoundError:
        pass
t = pd.DataFrame(rows)
pd.set_option("display.width", 250)
print(t.round(3).to_string())
t.to_csv(ED + "verify_calendar/v1_table.csv", index=False)
pd.concat(mine, axis=1).to_parquet(ED + "verify_calendar/v1_series.parquet")
