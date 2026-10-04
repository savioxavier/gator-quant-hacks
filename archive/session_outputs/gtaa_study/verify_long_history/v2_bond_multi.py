"""Bonds (own duration-convexity rebuild) and monthly multi-asset mixes, own parsing; execution sensitivity."""
import math
import numpy as np
import pandas as pd
import vdata as D
import vcore as C

pd.set_option("display.width", 250)
rules = ["SMA6", "SMA8", "SMA10", "SMA12", "MOM12"]

# ------------------------------------------------------------------ bonds daily strict
bd = D.bond_daily_duration()
e = pd.read_parquet(D.CACHE / "etf_daily.parquet")
ief = e[e.ticker == "IEF"].set_index("date")["close"]
ief.index = pd.to_datetime(ief.index)
bm = (1 + bd["R"]).groupby(bd.index.to_period("M")).prod() - 1
im = ief.groupby(ief.index.to_period("M")).last().pct_change()
j = pd.concat([bm, im], axis=1).dropna().loc["2003-09":"2024-09"]
print("bond rebuild vs IEF monthly corr", round(j.corr().iloc[0, 1], 3), "ann means", (j.mean() * 12).round(4).tolist())
res = {r: C.daily_strict(bd["R"], bd["rf"], r) for r in rules}
res["BH"] = C.daily_strict(bd["R"], bd["rf"], None)
start = max(v["pos"].first_valid_index() for v in res.values())
print("bond eval start", start.date())
for p, (a, b) in {"PRE_OOS": (start, "2024-10-02"), "2007-2024": ("2007-01-01", "2024-10-02")}.items():
    bh = res["BH"].loc[a:b]
    f = len(bh) / ((bh.index[-1] - bh.index[0]).days / 365.25)
    bex = (bh["net"] - bh["rf"]).to_numpy()
    sb = C.sharpe(bex, f)
    ds = {}
    for r in rules:
        x = res[r].loc[a:b]
        ds[r] = C.sharpe((x["net"] - x["rf"]).to_numpy(), f) - sb
    exs = [(res[r].loc[a:b]["net"] - res[r].loc[a:b]["rf"]).to_numpy() for r in rules[:4]]
    ci = C.boot_median_dsr(exs, bex, f, 63, B=500)
    print(f"bond {p}: BH SR {sb:.3f}, dSR {({k: round(v, 3) for k, v in ds.items()})}, median SMA {np.median(list(ds.values())[:4]):+.3f} CI [{ci[0]:+.2f},{ci[1]:+.2f}]"
          f", BH mdd {C.mdd(bh['net']):.3f}, SMA10 mdd {C.mdd(res['SMA10'].loc[a:b]['net']):.3f}")
    if p == "PRE_OOS":
        x = res["MOM12"].loc[a:b]
        print("   MOM12 CI63", np.round(C.boot_dsr((x["net"] - x["rf"]).to_numpy(), bex, f, 63, B=1000), 3))

# ------------------------------------------------------------------ monthly panel
km = D.kf_monthly()
rf = km["rf"].copy()
# extend cash after KF ends with own compounding of rf_daily
rfd = D.rf_daily()
rfm_d = (1 + rfd).groupby(rfd.index.to_period("M")).prod() - 1
rfm_d.index = rfm_d.index.to_timestamp(how="end").normalize()
rf = pd.concat([rf, rfm_d[(rfm_d.index > rf.index[-1]) & (rfm_d.index <= "2026-09-30")]])
bmm = bm.copy()
bmm.index = bmm.index.to_timestamp(how="end").normalize()
bmm = bmm.loc["1962-02-28":"2026-09-30"]
ia = D.ind_all()
dx = D.dev_ex_us()
intl = pd.concat([ia[ia.index < dx.index[0]], dx])
aqr = D.aqr_commod_er()
# own commodity-futures extension: EW of month-end returns of the 15 commodity roots
fu = pd.read_parquet(D.CACHE / "futures_daily.parquet")
roots = ["F_CL", "F_HO", "F_RB", "F_NG", "F_GC", "F_SI", "F_HG", "F_PL", "F_ZC", "F_ZS", "F_ZW", "F_ZL", "F_ZM", "F_LE", "F_HE"]
fp = fu[fu.ticker.isin(roots)].pivot(index="date", columns="ticker", values="close")
fp.index = pd.to_datetime(fp.index)
fr = fp.groupby(fp.index.to_period("M")).last().pct_change().mean(axis=1)
fr.index = fr.index.to_timestamp(how="end").normalize()
fr = fr.loc[:"2026-09-30"]
com = pd.concat([aqr + rf.reindex(aqr.index), fr[fr.index > aqr.index[-1]]])
cc = pd.concat([aqr, fr - rf.reindex(fr.index)], axis=1).dropna()
print("AQR vs futures EW excess corr", round(cc.corr().iloc[0, 1], 3), cc.index.min().date(), cc.index.max().date())
reit = D.nareit_all_equity()
panel = pd.DataFrame({"US_EQ": km["US_EQ"], "INTL": intl, "US_10Y": bmm, "COMMOD": com, "REIT": reit})
print(panel.apply(lambda s: f"{s.dropna().index.min().date()}..{s.dropna().index.max().date()}"))

# hybrid strict sleeves: US_EQ and US_10Y monthly returns of the daily-strict timed positions
deq = D.kf_daily()


def strict_monthly(R, rfx, rule):
    x = C.daily_strict(R, rfx, rule)
    m = (1 + x["net"]).groupby(x.index.to_period("M")).prod() - 1
    p = x["pos"].groupby(x.index.to_period("M")).mean()
    m.index = m.index.to_timestamp(how="end").normalize()
    p.index = m.index
    return m, p


def run_mix(cols, rule, lag, a, b, strict_daily=False):
    sub = panel[cols].loc[:b]
    out = C.monthly_run(sub, rf, rule, lag=lag)
    return out


def eval_mix(cols, a, b, lag=1, B=1000, L=3, verbose=True):
    res = {r: C.monthly_run(panel[cols], rf, r, lag=lag) for r in rules}
    res["BH"] = C.monthly_run(panel[cols], rf, None, lag=lag)
    st = max(v["net"].first_valid_index() for v in res.values())
    st = max(st, max(v["turn"].first_valid_index() for v in res.values()))
    a = max(pd.Timestamp(a), st)
    bh = res["BH"].loc[a:b]
    bex = (bh["net"] - bh["rf"]).to_numpy()
    sb = C.sharpe(bex, 12)
    ds = {r: C.sharpe((res[r].loc[a:b]["net"] - res[r].loc[a:b]["rf"]).to_numpy(), 12) - sb for r in rules}
    x10 = res["SMA10"].loc[a:b]
    ex10 = (x10["net"] - x10["rf"]).to_numpy()
    ci10 = C.boot_dsr(ex10, bex, 12, L, B=B)
    exs = [(res[r].loc[a:b]["net"] - res[r].loc[a:b]["rf"]).to_numpy() for r in rules[:4]]
    cim = C.boot_median_dsr(exs, bex, 12, L, B=B)
    o = {"mix": "+".join(cols), "lag": lag, "start": str(a.date()), "end": str(bh.index[-1].date()), "n_m": len(bh),
         "bh_sr": sb, "sma10_sr": sb + ds["SMA10"], "d_sma10": ds["SMA10"], "ci10": np.round(ci10[:2], 3).tolist(),
         "median_sma": float(np.median([ds[r] for r in rules[:4]])), "ci_med": np.round(cim, 3).tolist(),
         "d_mom12": ds["MOM12"], "sma10_cagr": C.stats(x10, 12)["cagr"], "bh_cagr": C.stats(bh, 12)["cagr"],
         "sma10_vol": C.stats(x10, 12)["vol"], "bh_vol": C.stats(bh, 12)["vol"],
         "sma10_mdd": C.mdd(x10["net"]), "bh_mdd": C.mdd(bh["net"]), "all_d": {k: round(v, 3) for k, v in ds.items()}}
    if verbose:
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in o.items()})
    return o


rows = []
M5 = ["US_EQ", "INTL", "US_10Y", "COMMOD", "REIT"]
for lag in (1, 2):
    rows.append(eval_mix(M5, "1976-01-01", "2024-09-30", lag))
    rows.append(eval_mix(M5, "2007-01-01", "2024-09-30", lag))
    rows.append(eval_mix(M5, "2009-01-01", "2024-09-30", lag))
    rows.append(eval_mix(M5, "2005-11-30", "2024-09-30", lag))   # same window as S3 in-sample
    rows.append(eval_mix(M5, "2024-10-31", "2026-08-31", lag, B=200))
    rows.append(eval_mix(["US_EQ", "COMMOD"], "1927-01-01", "2024-09-30", lag))
rows.append(eval_mix(["US_EQ", "COMMOD"], "1927-01-01", "2024-09-30", 1, L=12))
rows.append(eval_mix(["US_EQ", "US_10Y", "COMMOD"], "1963-01-01", "2024-09-30", 1))
pd.DataFrame(rows).to_csv("out_multi.csv", index=False)

# ------------------------------------------------------------------ hybrid: strict execution for US_EQ and US_10Y sleeves
print("\nHybrid MA5: US_EQ, US_10Y sleeves from daily-strict positions (trade at close T+1), others idealised lag1")
eq_m = {r: strict_monthly(deq["R"], deq["rf"], r) for r in rules + [None]}
bd_m = {r: strict_monthly(bd["R"], bd["rf"], r) for r in rules + [None]}
for (a, b) in [("1976-01-01", "2024-09-30"), ("2007-01-01", "2024-09-30"), ("2005-11-30", "2024-09-30")]:
    srs = {}
    for r in rules + [None]:
        oth = C.monthly_run(panel[["INTL", "COMMOD", "REIT"]], rf, r, lag=1)   # 1/3 each sleeves
        # recombine: each of 5 sleeves at 1/5. other-three monthly return = oth gross; convert to 3/5 weight
        df = pd.DataFrame({"eq": eq_m[r][0], "bd": bd_m[r][0], "oth": oth["net"], "rf": rf}).loc[a:b].dropna()
        net = 0.2 * df["eq"] + 0.2 * df["bd"] + 0.6 * df["oth"]
        srs[r] = (net - df["rf"])
    st = max(s.first_valid_index() for s in srs.values())
    idx = srs[None].loc[st:].index
    for r in srs:
        srs[r] = srs[r].reindex(idx)
    sb = C.sharpe(srs[None].to_numpy(), 12)
    ds = {r: round(C.sharpe(srs[r].to_numpy(), 12) - sb, 3) for r in rules}
    print(f"  {idx[0].date()}..{idx[-1].date()} BH {sb:.3f} dSR {ds} median SMA {np.median([ds[r] for r in rules[:4]]):+.3f}")
