"""EW of 15 CME commodity futures (fully collateralised TR), 2010-2024: monthly SMA rule, same-close (idealised) vs next-close (strict)."""
import numpy as np, pandas as pd
import vdata as D, vcore as C
fu = pd.read_parquet(D.CACHE / "futures_daily.parquet")
roots = ["F_CL","F_HO","F_RB","F_NG","F_GC","F_SI","F_HG","F_PL","F_ZC","F_ZS","F_ZW","F_ZL","F_ZM","F_LE","F_HE"]
fp = fu[fu.ticker.isin(roots)].pivot(index="date", columns="ticker", values="close"); fp.index = pd.to_datetime(fp.index)
r = fp.pct_change(fill_method=None).mean(axis=1).dropna().loc[:"2024-10-02"]
rf = D.rf_daily().reindex(r.index).ffill()
rules = ["SMA6","SMA8","SMA10","SMA12"]
# strict
st = {k: C.daily_strict(r, rf, k) for k in rules}; st["BH"] = C.daily_strict(r, rf, None)
# idealised daily: position effective from T+1 (trade at close T) -> shift the strict positions one day earlier
idl = {}
for k in rules:
    x = st[k].copy(); p = x["pos"].shift(-1); p.iloc[-1] = x["pos"].iloc[-1]
    sw = p.diff().abs().fillna(0); g = p * x["R"] + (1 - p) * x["rf"]
    idl[k] = pd.DataFrame({"rf": x["rf"], "net": g - 0.001 * sw, "pos": p})
s0 = max(v["pos"].first_valid_index() for v in st.values())
for a, b in [(s0, "2024-10-02"), ("2013-01-01", "2024-10-02")]:
    bh = st["BH"].loc[a:b]; sb = C.sharpe((bh.net - bh.rf).to_numpy(), 252)
    d1 = [C.sharpe((st[k].loc[a:b].net - st[k].loc[a:b].rf).to_numpy(), 252) - sb for k in rules]
    d0 = [C.sharpe((idl[k].loc[a:b].net - idl[k].loc[a:b].rf).dropna().to_numpy(), 252) - sb for k in rules]
    print(f"{pd.Timestamp(a).date()}..{b} BH {sb:.3f}  idealised {np.round(d0,3)} med {np.median(d0):+.3f} | strict {np.round(d1,3)} med {np.median(d1):+.3f}")
# monthly-frequency Sharpe of the same daily runs (to separate frequency from construction)
def msr(x):
    m = (1 + x[["net", "rf"]]).groupby(x.index.to_period("M")).prod() - 1
    return C.sharpe((m.net - m.rf).to_numpy(), 12)
a = s0
bh = st["BH"].loc[a:]
print("monthly-freq: BH", round(msr(bh), 3), "idealised d", [round(msr(idl[k].loc[a:]) - msr(bh), 3) for k in rules],
      "strict d", [round(msr(st[k].loc[a:]) - msr(bh), 3) for k in rules])
# monthly-rebalanced EW (closer to AQR): month-end-to-month-end EW of monthly returns, idealised lag 1
mr = fp.groupby(fp.index.to_period("M")).last().pct_change(fill_method=None).mean(axis=1).dropna()
mr.index = mr.index.to_timestamp(how="end").normalize(); mr = mr.loc[:"2024-09-30"]
km = D.kf_monthly(); rfm = km["rf"].reindex(mr.index).fillna(0.0)
res = {k: C.monthly_run(mr.to_frame("C"), rfm, k, 1) for k in rules}; res["BH"] = C.monthly_run(mr.to_frame("C"), rfm, None, 1)
s1 = max(v["net"].first_valid_index() for v in res.values())
bh = res["BH"].loc[s1:]; sb = C.sharpe((bh.net - bh.rf).to_numpy(), 12)
print("monthly-rebalanced EW futures, idealised lag1", s1.date(), "BH", round(sb, 3), "dSR",
      [round(C.sharpe((res[k].loc[s1:].net - res[k].loc[s1:].rf).to_numpy(), 12) - sb, 3) for k in rules])
