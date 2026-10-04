"""Compact digest of the stage's summary tables (no price levels)."""
import sys, json
from pathlib import Path
import pandas as pd
S = Path(sys.argv[1]); O = Path(sys.argv[2])
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 500)
a = pd.read_csv(S / "results/answer_summary.csv")
cols = ["key", "h", "sym", "variant", "sample", "cluster", "cost", "unit", "n_answers", "n_meetings", "mean", "t_cr1",
        "wcb_p_two", "bb_ci90_lo", "bb_ci90_hi", "mtg_mean", "mtg_wb_p_two", "lomo_min", "lomo_max", "lomo_most_influential"]
d = a[a.key.isin(["H2", "H3"])][cols]
d.to_csv(O / "digest_answer_summary_H2_H3.csv", index=False, float_format="%.6g")
for k in ["H2", "H3"]:
    print(f"==== {k} C0 rows")
    print(d[(d.key == k) & (d.cost == "C0")].drop(columns=["key", "cost"]).to_string(index=False))
    print(f"==== {k} primary sample, ZT, +1/+5/+15, base: all cost rows")
    print(d[(d.key == k) & (d.sym == "ZT") & (d["sample"] == "primary_2023_2026") & (d.variant == "base")]
          [["h", "cost", "unit", "n_answers", "mean", "t_cr1", "wcb_p_two", "bb_ci90_lo", "bb_ci90_hi"]].to_string(index=False))
m = pd.read_csv(S / "results/meeting_summary.csv")
mc = ["key", "sym", "clock", "exit", "sample", "cost", "unit", "n", "mean", "t", "wb_p_two", "bb_ci90_lo", "bb_ci90_hi",
      "lomo_most_influential"]
m[m.key.isin(["H2", "H3"])][mc].to_csv(O / "digest_meeting_summary_H2_H3.csv", index=False, float_format="%.6g")
print("==== meeting level, H2/H3, C0")
print(m[m.key.isin(["H2", "H3"]) & (m.cost == "C0")][mc].to_string(index=False))
print("==== meeting level, H2, primary, ZT, all costs")
print(m[(m.key == "H2") & (m.sym == "ZT") & (m["sample"] == "primary_2023_2026")][mc].to_string(index=False))
c = pd.read_csv(S / "results/companion_slopes.csv")
print("==== companion slopes")
print(c[[x for x in ["key", "sample", "cluster", "regressors", "coef", "se_cr1", "t_cr1", "n", "n_clusters", "wcb_p_two"] if x in c.columns]].to_string(index=False))
sp = pd.read_csv(S / "results/spreads_at_answer_entries.csv")
print("==== spreads at answer entries (ZT, H2/H3)")
print(sp[sp.key.isin(["H2", "H3"]) & (sp.sym == "ZT")].to_string(index=False))
fd = pd.read_csv(S / "results/feature_distributions.csv")
print(fd.to_string(index=False))
rm = json.loads((S / "results/run_meta.json").read_text())
print({k: rm[k] for k in ["seed", "draws", "prereg_sha256", "fit_sha256", "bad_quote_records_skipped", "placebo_tree"]})
