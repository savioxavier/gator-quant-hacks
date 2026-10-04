"""US equities daily strict: headline SMA10 vs BH, median dSharpe by period, out-state returns, year contributions."""
import math
import numpy as np
import pandas as pd
import vdata as D
import vcore as C

d = D.kf_daily()
print("KF daily", d.index.min().date(), d.index.max().date(), len(d))
rules = ["SMA6", "SMA8", "SMA10", "SMA12", "MOM12"]
res = {r: C.daily_strict(d["R"], d["rf"], r) for r in rules}
res["BH"] = C.daily_strict(d["R"], d["rf"], None)
start = max(v["pos"].first_valid_index() for v in res.values())
print("eval start", start.date())

# truncation test (own): positions computed on data cut at T must match
for T in ["1932-07-08", "1974-10-03", "2008-11-20", "2024-10-02"]:
    cut = C.daily_strict(d["R"].loc[:T], d["rf"].loc[:T], "SMA10")["pos"]
    full = res["SMA10"]["pos"].loc[:T]
    print("truncation", T, bool((cut.fillna(-9) == full.fillna(-9)).all()))


def f_of(ix):
    return len(ix) / ((ix[-1] - ix[0]).days / 365.25)


periods = {"PRE_OOS_all": (start, "2024-10-02"), "1926-72": (start, "1972-12-31"),
           "1973-2006": ("1973-01-01", "2006-12-31"), "2007-2024": ("2007-01-01", "2024-10-02"),
           "2009-2024": ("2009-01-01", "2024-10-02"), "OOS_desc": ("2024-10-03", "2100-01-01")}
rows = []
for p, (a, b) in periods.items():
    bh = res["BH"].loc[a:b]
    f = f_of(bh.index)
    bex = (bh["net"] - bh["rf"]).to_numpy()
    sb = C.sharpe(bex, f)
    exs = []
    for r in rules:
        x = res[r].loc[a:b]
        ex = (x["net"] - x["rf"]).to_numpy()
        exs.append(ex) if r.startswith("SMA") else None
        st = C.stats(x, f)
        row = {"period": p, "rule": r, "sharpe": st["sharpe"], "bh_sharpe": sb, "dsr": st["sharpe"] - sb,
               "sharpe_252": C.sharpe(ex, 252) - C.sharpe(bex, 252),
               "cagr": st["cagr"], "bh_cagr": C.stats(bh, f)["cagr"], "vol": st["vol"],
               "bh_vol": C.stats(bh, f)["vol"], "mdd": st["mdd"], "bh_mdd": C.mdd(bh["net"]),
               "invested": float(x["pos"].mean()), "switches": float(x["sw"].sum()),
               "sw_per_yr": float(x["sw"].sum() / st["years"]),
               "gross_sharpe": C.sharpe((x["gross"] - x["rf"]).to_numpy(), f), "years": st["years"]}
        if p == "PRE_OOS_all" and r in ("SMA10", "MOM12"):
            row["ci63"] = C.boot_dsr(ex, bex, f, 63, B=2000)
            row["ci252"] = C.boot_dsr(ex, bex, f, 252, B=1000)
        rows.append(row)
    med = np.median([rr["dsr"] for rr in rows if rr["period"] == p and rr["rule"].startswith("SMA")])
    ci = C.boot_median_dsr(exs, bex, f, 63, B=1000) if p != "OOS_desc" else (np.nan, np.nan)
    print(f"{p:12s} median dSharpe SMA6-12 {med:+.3f}  CI [{ci[0]:+.2f},{ci[1]:+.2f}]  years {len(bh)/f:.1f}  BH SR {sb:.3f}")
t = pd.DataFrame(rows)
pd.set_option("display.width", 250)
print(t.drop(columns=[c for c in ["ci63", "ci252"] if c in t]).round(3).to_string())
for _, r in t.dropna(subset=["ci63"]).iterrows():
    print(r["rule"], "CI63", np.round(r["ci63"], 3), "CI252", np.round(r["ci252"], 3))
t.to_csv("out_equity_daily.csv", index=False)

# out-state excess returns, SMA10, pre-OOS
x = res["SMA10"].loc[start:"2024-10-02"]
bh = res["BH"].loc[start:"2024-10-02"]
f = f_of(bh.index)
bex = bh["net"] - bh["rf"]
out = x["pos"] < 0.5
for lab, m in [("out", out), ("in", ~out)]:
    e = bex[m]
    print(f"BH excess while {lab}: {e.mean()*f*100:+.2f}%/yr, vol {e.std()*math.sqrt(f)*100:.1f}%, days {m.sum()}")
import statsmodels.api as sm
mo = sm.OLS(bex.values, sm.add_constant(out.astype(float).values)).fit(cov_type="HAC", cov_kwds={"maxlags": 21})
print("out-state mean diff regression:", mo.params * f, "t", mo.tvalues)
o = sm.OLS(bex[out].values, np.ones(out.sum())).fit(cov_type="HAC", cov_kwds={"maxlags": 21})
print("out-state mean t (NW21)", float(o.tvalues[0]))

# calendar-year contributions (log)
yt = np.log1p(x["net"]).groupby(x.index.year).sum()
yb = np.log1p(bh["net"]).groupby(bh.index.year).sum()
dif = (yt - yb).sort_values(ascending=False)
print("years timed>BH:", (dif > 0).mean(), "n years", len(dif))
print("top5", dif.head(5).round(3).to_dict(), "sum", round(dif.head(5).sum(), 3), "rest", round(dif.iloc[5:].sum(), 3),
      "net", round(dif.sum(), 3))
print("Sharpe without top-5 years:")
keep = ~x.index.year.isin(dif.head(5).index)
print("  timed", C.sharpe((x["net"] - x["rf"])[keep].to_numpy(), f), "BH", C.sharpe(bex[keep].to_numpy(), f))
