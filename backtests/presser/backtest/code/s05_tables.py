"""Step 5: per-meeting P&L tables, key-results JSON and the output manifest (no new computation of P&L)."""
from __future__ import annotations

import json

import pandas as pd

from lib import OUT, check_addendum, sha256, write_json

check_addendum()
R = OUT / "results"
T = OUT / "tables"
T.mkdir(exist_ok=True)
cols = ["date", "pos", "entry_ts", "entry_px", "exit_ts", "exit_px", "move_ticks", "tick_era", "usd_per_tick",
        "C0_ticks", "C0_usd", "C2_usd", "C4_usd", "CM_usd", "CQ_usd", "C2F_usd", "hs_entry_ticks", "hs_exit_ticks",
        "stale_entry_s", "stale_exit_s"]
b = pd.read_csv(R / "benchr_trades.csv", dtype={"date": str})
for s in ["ZT", "ES", "ZF", "ZN"]:
    x = b[(b.sym == s) & (b.variant == "exit_tau_upper")]
    x[["era", "chair", "drop_timing", "tau_src", "R"] + cols].to_csv(T / f"benchr_per_meeting_{s}.csv", index=False)
h = pd.read_csv(R / "h1primary_trades.csv", dtype={"date": str})
x = h[(h.signal == "lexH1raw") & (h.clock == "primary") & (h.exit == "exit_1600")]
for s in ["ZT", "ES", "ZF", "ZN"]:
    x[x.sym == s][["sample", "chair", "s", "R_ZT", "resid"] + cols].to_csv(
        T / f"lexicon_h1primary_per_meeting_{s}.csv", index=False)

S = pd.read_csv(R / "summary_long.csv")
g3 = json.loads((R / "g3_and_h1primary_extras.json").read_text())


def pick(test, variant, sample, sym, cost="C0", unit="usd", tick_era="all"):
    r = S[(S.test == test) & (S.variant == variant) & (S["sample"] == sample) & (S.sym == sym) & (S.cost == cost) &
          (S.unit == unit) & (S.tick_era == tick_era)]
    if len(r) == 0:
        return None
    r = r.iloc[0]
    return {k: (None if pd.isna(r[k]) else (round(float(r[k]), 4) if isinstance(r[k], float) else r[k]))
            for k in ["n", "mean", "sd", "median", "hit", "t", "bb_ci90_lo", "bb_ci90_hi", "bb_p_one", "wb_p_one",
                      "wb_p_two", "designated_side"]}


key = {"H1-primary (stance)": g3["H1"], "H1-Q": g3["H1Q"], "lexicon frozen lex_H1": g3["lexH1"],
       "lexicon lex_H1_raw G3-rule replica (control, two-sided reading)": g3["lexH1raw"], "BENCH-R": {}}
for s in ["ZT", "ES"]:
    for era in ["era_2016-2019", "era_2020-2026"]:
        for cost in ["C0", "C2", "C4", "CM", "CQ", "C2F"]:
            key["BENCH-R"][f"{s}|{era}|{cost}|usd"] = pick("BENCH-R", "exit_tau_upper", era, s, cost)
write_json(R / "key_results.json", key)

files = sorted([p for p in OUT.rglob("*") if p.is_file() and p.name != "manifest_sha256.txt"])
(OUT / "manifest_sha256.txt").write_text("".join(f"{sha256(f)}  {f.relative_to(OUT).as_posix()}\n" for f in files))
print(json.dumps(key["BENCH-R"]["ZT|era_2016-2019|C0|usd"], indent=1, default=str))
