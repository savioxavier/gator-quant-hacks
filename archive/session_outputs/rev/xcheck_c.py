"""Independent cross-check of IFC sleeve C base (reviewer). Pure pandas, no module code for the
signal: reads raw parquet files, rebuilds calendar, S_m, q, vol, weights and gross/net returns.
Then compares with the module (engine run logged with identical name/params -> same hash)."""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<solo-repo>")
sys.path.insert(0, str(ROOT))
D = "<home>/.cache/gqh/"
IS_START, IS_END = pd.Timestamp("2005-01-03"), pd.Timestamp("2024-10-02")

etf = pd.read_parquet(D + "etf_daily.parquet")
cal = pd.DatetimeIndex(sorted(etf.loc[etf.ticker == "SPY", "date"].unique()))
cal = cal[(cal >= IS_START) & (cal <= IS_END)]
ief = etf[etf.ticker == "IEF"].set_index("date")["close"].reindex(cal)
assert ief.notna().all(), "IEF gaps"
r = ief.pct_change()
rf = pd.read_parquet(D + "rf_daily.parquet").set_index("date")["rf"].reindex(cal).ffill()
n = len(cal)

# ---- 2004 calendar (only for the cut-off dates of the 2004 medians)
hol04 = pd.DatetimeIndex(["2004-01-01", "2004-01-19", "2004-02-16", "2004-04-09", "2004-05-31", "2004-06-11",
                          "2004-07-05", "2004-09-06", "2004-11-25", "2004-12-24"])
c04 = pd.bdate_range("2004-01-01", "2004-12-31")
c04 = c04[~c04.isin(hol04)]
ext = c04.append(cal)

def month_T_positions(c):
    s = pd.Series(np.arange(len(c)), index=c)
    last = s.groupby(c.to_period("M")).max()
    # drop the final month if incomplete (data ends 2024-10-02)
    if c[-1].to_period("M") == pd.Timestamp("2024-10-02").to_period("M"):
        last = last.iloc[:-1]
    return last

# ---- auctions
a = pd.read_parquet(D + "treasury_auctions.parquet")
a = a[a.security_type.isin(["Note", "Bond"]) & (a.announcemt_date <= IS_END)].copy()
frn = a.high_yield.isna()
print("FRN rows", frn.sum(), "terms", a.loc[frn, "original_security_term"].unique(), "years",
      a.loc[frn, "auction_date"].dt.year.min(), a.loc[frn, "auction_date"].dt.year.max())
a = a[~frn].copy()

def yrs(t):
    import re
    m = re.match(r"(\d+)-Year(?:\s+(\d+)-Month)?", t)
    return int(m.group(1)) + (int(m.group(2)) / 12 if m.group(2) else 0)

DUR = {2: 1.9, 3: 2.8, 5: 4.5, 7: 6.2, 10: 8.3, 20: 13.5, 30: 18.0}
a["oy"] = a.original_security_term.map(yrs)
a["sterm"] = a.oy.map(lambda y: min(DUR, key=lambda k: abs(k - y)))
# independent TIPS rule: TIPS calendar maturities (15th of Jan/Apr/Jul/Oct) for 5/10/20/30y,
# plus 30y Feb-15 CUSIPs whose yield sits >0.5pp below the nominal 30y rows of the same +-45 days
md = a.maturity_date
tips_cal = (md.dt.day == 15) & md.dt.month.isin([1, 4, 7, 10]) & a.sterm.isin([5, 10, 20, 30])
b30 = a[a.sterm == 30]
low30 = pd.Series(False, index=a.index)
for i, row in b30.iterrows():
    nb = b30[(b30.auction_date - row.auction_date).abs() <= pd.Timedelta(days=45)]
    med = nb.high_yield.median()
    if row.high_yield < med - 0.5:
        low30[i] = True
nbmed = pd.Series([a.loc[(a.auction_date - d).abs() <= pd.Timedelta(days=31), "high_yield"].median()
                   for d in a.auction_date], index=a.index)
# 2003-2006 the NOMINAL 5y note was quarterly and matured on the TIPS calendar (yields 3.2-4.4%)
tips_cal = tips_cal & ~((a.sterm == 5) & (a.issue_date < "2007-01-01") & (a.high_yield > 2.5))
tips_row = tips_cal | low30
tips_cus = a.groupby("cusip")["cusip"].transform(lambda s: tips_row[s.index].any())
tips = tips_cus.astype(bool)
print("TIPS rows (indep)", int(tips.sum()), "cusips", a.loc[tips, "cusip"].nunique())
nom = a[~tips].copy()
nom["dv01"] = nom.offering_amt.astype(float) * nom.sterm.map(DUR)
print("nominal rows (indep)", len(nom))

# ---- S_m with cut-off T-4 (own month), median of previous 12, q
lastE = month_T_positions(ext)
iss_m = nom.issue_date.dt.to_period("M")
S = {}
for m, ti in lastE.items():
    cut = ext[ti - 4]
    S[m] = nom.loc[(iss_m == m) & (nom.announcemt_date <= cut), "dv01"].sum()
S = pd.Series(S)
med = pd.Series([np.median(S.iloc[i - 12:i]) if i >= 12 else np.nan for i in range(len(S))], index=S.index)
q = (S / med).clip(0.5, 2.0)

# ---- weights
lastC = month_T_positions(cal)
w = pd.Series(0.0, index=cal)
for m, ti in lastC.items():
    d = ti - 4
    if d < 63 or not np.isfinite(q.get(m, np.nan)):
        continue
    vol = r.iloc[d - 62:d + 1].std(ddof=1) * math.sqrt(252)
    w.iloc[ti - 2:ti + 1] = min(q[m] * 0.10 / vol, 2.0)

# ---- Sandy (NYSE closed 2012-10-29/30, announced 10-28/29): the trader's T-4 was 10-25, entry at the
# 10-26 close, so only return day 10-31 is held, sized with vol observed at 10-25
SANDY = "--sandy" in sys.argv
if SANDY:
    w.loc["2012-10-25":"2012-10-26"] = 0.0
    dS = cal.get_loc(pd.Timestamp("2012-10-25"))
    volS = r.iloc[dS - 62:dS + 1].std(ddof=1) * math.sqrt(252)
    w.loc["2012-10-31"] = min(q[pd.Period("2012-10", "M")] * 0.10 / volS, 2.0)

# ---- independent P&L: position w_t over return day t, cash at T-bill
gross = w * r.fillna(0) + (1 - w) * rf
w_prev_drift = (w.shift(1) * (1 + r.shift(1).fillna(0))) / (1 + w.shift(1) * r.shift(1).fillna(0))
trade = (w - w_prev_drift.fillna(0)).abs()
borrow = 0.0  # long only
def net_of(mult):
    return gross - trade * 3e-4 * mult
first = w[w != 0].index[0]
def sr(x):
    x = x.loc[first:] - rf.loc[first:]
    return x.mean() / x.std() * math.sqrt(252)
print("independent first live day", first.date())
print(f"independent Sharpe gross {sr(gross):.4f}  net1x {sr(net_of(1)):.4f}  net2x {sr(net_of(2)):.4f}")

# ---- kill-condition statistic: per-window sum of IEF excess over [T-2, T] (all complete months)
ex = r - rf
win = np.array([ex.iloc[ti - 2:ti + 1].sum() for m, ti in lastC.items() if ti - 2 >= 1])
print(f"window mean {win.mean()*1e4:.2f} bp  t {win.mean()/(win.std(ddof=1)/math.sqrt(len(win))):.2f}  n {len(win)}  hit {np.mean(win>0):.3f}")

# ---- module comparison
from src import engine as E
from src.strategies import ifc_treasury as M
ohlc = E.load_ohlc(["IEF"], "IS")
rfm = E.load_rf("IS")
auc = M.load_nominal_auctions("IS")
mt = M.monthly_issuance("IS", auctions=auc)
cmpS = pd.DataFrame({"S_indep": S, "S_mod": mt["S"], "q_indep": q, "q_mod": mt["q"]}).dropna(subset=["S_mod"])
dS = (cmpS.S_indep - cmpS.S_mod).abs()
print("months with S mismatch:", int((dS > 1).sum()), "of", len(cmpS), " max|dq|", float((cmpS.q_indep - cmpS.q_mod).abs().max()))
if (dS > 1).any():
    print(cmpS[dS > 1].head(20))
p = M._params({})
wd = M.decision_weights("IS", ohlc=ohlc, auctions=auc, **p)
params = {"sleeve": M.SLEEVE, "variant": "base", **p}
res = E.run_backtest("IFC_C_base", M.FAMILY, wd, ohlc, rfm, period="IS", params=params, exec=M.EXEC,
                     cost_mult=1.0, log=True, note="reviewer xcheck (module weights)" + (" sandy" if SANDY else ""))
hold_mod = res.weights["IEF"]
dw = (hold_mod - w.reindex(hold_mod.index)).abs()
print("max |held_module - w_indep|", float(dw.max()), " days differing >1e-9:", int((dw > 1e-9).sum()))
g_mod = res.gross_returns
dg = (g_mod - gross.reindex(g_mod.index)).abs()
print("max |gross_module - gross_indep|", float(dg.max()))
gx = g_mod - rfm.reindex(g_mod.index).ffill()
print(f"module Sharpe gross {gx.mean()/gx.std()*math.sqrt(252):.4f}  net {res.stats['sharpe']:.4f}")
# run independent weights through the engine too (same name/params -> same hash, logged)
w_dec_indep = w.shift(-2).fillna(0.0).to_frame("IEF")
res_i = E.run_backtest("IFC_C_base", M.FAMILY, w_dec_indep, ohlc, rfm, period="IS", params=params, exec=M.EXEC,
                       cost_mult=1.0, log=True, note="reviewer xcheck (independent weights)" + (" sandy" if SANDY else ""))
print(f"engine on independent weights: net Sharpe {res_i.stats['sharpe']:.4f}")
dn = (res.returns - net_of(1).reindex(res.returns.index)).abs()
print("max |net_module - net_indep|", float(dn.max()))
