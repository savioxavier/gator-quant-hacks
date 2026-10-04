"""Audit helper (read-only): do the scratch synth_run / savetest files contain real out-of-sample returns?"""
import pandas as pd

S = "<scratch>/"
B = S + "v2_oos_build/"
R = S + "team_push/backtests/results/v2_oos/run/"

for f in ["synth_run/daily_T4xE1_full.parquet", "synth_run/daily_VariantA_frozen_T0fxE1_full.parquet",
          "synth_run/daily_portfolio_full.parquet", "savetest/daily_portfolio_full.parquet",
          "savetest/daily_VariantA_frozen_T0fxE1_full.parquet"]:
    d = pd.read_parquet(B + f)
    nn = d.dropna(how="all")
    print(f, d.shape, d.index.min(), d.index.max(), "last non-null row", nn.index.max(), list(d.columns)[:6])
print("savetest portfolio_info_oos:", open(B + "savetest/portfolio_info_oos.json").read())
print("real portfolio_info_oos:", open(R + "portfolio_info_oos.json").read())
print("real portfolio_info (IS):", open(R + "portfolio_info.json").read())

real = pd.read_parquet(R + "daily_T4xE1_full.parquet")
syn = pd.read_parquet(B + "synth_run/daily_T4xE1_full.parquet")
for col in ["ex1", "exg", "turnover"]:
    if col in syn.columns and col in real.columns:
        j = pd.concat([real[col], syn[col]], axis=1, keys=["r", "s"]).dropna()
        o = j.loc["2024-10-03":]
        print("synth vs real T4xE1", col, "OOS n", len(o),
              "OOS maxdiff", float((o.r - o.s).abs().max()) if len(o) else None,
              "OOS corr", float(o.r.corr(o.s)) if len(o) > 2 else None)
rp = pd.read_parquet(R + "daily_portfolio_full.parquet")
sp = pd.read_parquet(B + "synth_run/daily_portfolio_full.parquet")
for col in [x for x in rp.columns if x in sp.columns][:3]:
    j = pd.concat([rp[col], sp[col]], axis=1, keys=["r", "s"]).dropna()
    o = j.loc["2024-10-03":]
    print("synth vs real portfolio", col, "OOS n", len(o),
          "maxdiff", float((o.r - o.s).abs().max()) if len(o) else None,
          "corr", float(o.r.corr(o.s)) if len(o) > 2 else None)
for f in ["savetest/daily_portfolio_full.parquet", "savetest/daily_VariantA_frozen_T0fxE1_full.parquet"]:
    d = pd.read_parquet(B + f)
    print(f, "rows with data on/after 2024-10-03:", int(d.loc["2024-10-03":].notna().any(axis=1).sum()))
is_t4 = pd.read_parquet(R + "daily_T4xE1_is.parquet")
sv = pd.read_parquet(B + "savetest/daily_VariantA_frozen_T0fxE1_full.parquet")
print("savetest VA equals run daily_T4xE1_is:", sv.shape == is_t4.shape and bool((sv.fillna(-9) == is_t4.fillna(-9)).all().all()))
