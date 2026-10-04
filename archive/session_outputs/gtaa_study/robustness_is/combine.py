"""Join the in-sample and later-window tables into one file covering every configuration computed."""
import json
import os

import pandas as pd

D = os.path.dirname(os.path.abspath(__file__))
iv = pd.read_csv(os.path.join(D, "is_variants.csv"))
fv = pd.read_csv(os.path.join(D, "fwd_variants.csv"))
g = iv.merge(fv[[c for c in fv.columns if c.startswith("later_")] + ["variant"]], on="variant")
g.insert(0, "kind", "grid_timed")
ib = pd.read_csv(os.path.join(D, "is_benchmarks.csv"))
fb = pd.read_csv(os.path.join(D, "fwd_benchmarks.csv"))
b = ib[["benchmark", "sharpe", "sharpe_se", "ann_return", "ann_vol", "max_dd", "turnover_per_year"]].add_prefix("is_").rename(
    columns={"is_benchmark": "variant"}).merge(
    fb[["benchmark", "sharpe", "sharpe_se", "ann_return", "ann_vol", "max_dd", "turnover_per_year"]].add_prefix("later_").rename(
        columns={"later_benchmark": "variant"}), on="variant")
b.insert(0, "kind", "grid_untimed")
di = pd.read_csv(os.path.join(D, "is_diag_assets.csv"))
df = pd.read_csv(os.path.join(D, "fwd_diag_assets.csv"))
d = di.merge(df[["asset", "signal", "later_sharpe", "later_untimed_sharpe", "later_d_vs_untimed", "later_max_dd", "later_untimed_max_dd"]],
             on=["asset", "signal"])
d["variant"] = d["signal"] + "|one_" + d["asset"] + "|equal|tbill"
d = d.rename(columns={"d_sharpe_vs_untimed": "d_sharpe_vs_untimed"})
d.insert(0, "kind", "diag_single_asset_timed")
du = d.drop_duplicates("asset")[["asset", "untimed_sharpe", "untimed_max_dd", "later_untimed_sharpe", "later_untimed_max_dd"]].rename(
    columns={"untimed_sharpe": "is_sharpe", "untimed_max_dd": "is_max_dd", "later_untimed_sharpe": "later_sharpe",
             "later_untimed_max_dd": "later_max_dd"})
du["variant"] = "UNTIMED|one_" + du["asset"]
du.insert(0, "kind", "diag_single_asset_untimed")
out = pd.concat([g, b, d, du], ignore_index=True, sort=False)
out.to_csv(os.path.join(D, "all_configs_is_and_later.csv"), index=False, float_format="%.6g")
print(out["kind"].value_counts().to_dict(), "total", len(out))
