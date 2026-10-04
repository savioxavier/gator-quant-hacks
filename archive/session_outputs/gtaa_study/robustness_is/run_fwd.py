"""Later window (2024-10-03..2026-10-02), DESCRIPTIVE ONLY, computed after the in-sample tables were written.

Uses period "FWD" (all cached data, no OOS unlock). No variant is selected here: every one of the 72 timed variants
(and 6 untimed benchmarks, 70 per-asset diagnostic sleeves) is reported. Also checks that re-running every config on
the full data reproduces the in-sample returns exactly (no information after 2024-10-02 entered the IS numbers).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gtaa_lib as L  # noqa: E402
from src import forward2 as F2  # noqa: E402

done = os.path.join(L.OUT, "is_done.json")
assert os.path.exists(done), "in-sample tables must be written first (run_is.py)"
marker = json.load(open(done))
h = hashlib.sha256(open(os.path.join(L.OUT, "is_variants.csv"), "rb").read()).hexdigest()
assert h == marker["is_variants_sha256"], "is_variants.csv changed after the marker"
VT = pd.read_csv(os.path.join(L.OUT, "is_variants.csv"))
DG_IS = pd.read_csv(os.path.join(L.OUT, "is_diag_assets.csv"))
EX_IS = pd.read_parquet(os.path.join(L.OUT, "is_daily_excess.parquet"))
DX_IS = pd.read_parquet(os.path.join(L.OUT, "is_diag_daily_excess.parquet"))

B = 2000
ohlc, rf = L.load("FWD")
close = ohlc["close"]
cal = close.index
LATER = (pd.Timestamp("2024-10-03"), pd.Timestamp("2026-10-02"))
assert cal[-1] == LATER[1], cal[-1]
START_DEC = pd.Timestamp(marker["common_first_decision"])
FULL = (cal[cal.get_loc(START_DEC) + 1], cal[-1])
rfw = rf.reindex(cal).ffill().fillna(0.0)
GRID = L.grid()
tv = [L.vid(k) for k in GRID]
untimed_of = {L.vid(k): f"UNTIMED|{k[1]}|{k[2]}" for k in GRID}
s3n = L.vid(L.S3_KEY)
for t in L.UNIVERSES["broad10"]:
    L.UNIVERSES[f"one_{t}"] = [t]

rows, exs, rets, maxdiff = {}, {}, {}, 0.0


def run(key, timed, name, store_ex=True):
    global maxdiff
    w, net, gross, to, held = L.run_variant(key, ohlc, rf, START_DEC, FULL, timed=timed)
    ex_full = net - rfw.loc[net.index]
    ref = EX_IS[name] if name in EX_IS else DX_IS[name]
    maxdiff = max(maxdiff, float((ex_full.loc[ref.index] - ref).abs().max()))
    sl = slice(*LATER)
    exp_held = w.shift(1).fillna(0.0).loc[held.index]
    assert np.allclose(held.to_numpy(), exp_held.to_numpy()), name
    r = L.stats_row(net.loc[sl], rf, to.loc[sl], held.loc[sl])
    rows[name] = r
    exs[name] = ex_full.loc[sl]
    rets[name] = net.loc[sl]


for u in L.UNIVERSES:
    if u.startswith("one_"):
        continue
    for wgt in L.WEIGHTINGS:
        run(("SMA10", u, wgt, "tbill"), False, f"UNTIMED|{u}|{wgt}")
for k in GRID:
    run(k, True, L.vid(k))
for t in L.UNIVERSES["broad10"]:
    u = f"one_{t}"
    run(("SMA10", u, "equal", "tbill"), False, f"UNTIMED|{u}")
    for s in L.SIGNALS:
        run((s, u, "equal", "tbill"), True, f"{s}|{u}")
print("max |daily excess diff| on the IS window, full-data vs IS-truncated run:", maxdiff)
assert maxdiff < 1e-12

# frozen S3 / BH5 reconciliation with forward/historical_context2.json (0.70 / 0.82)
s3f = F2.returns("S3", "FWD").loc[slice(*LATER)]
bhf = F2.returns("BH5", "FWD").loc[slice(*LATER)]
sr = lambda x: float((x - rfw.loc[x.index]).mean() / (x - rfw.loc[x.index]).std() * math.sqrt(252))  # noqa: E731
recon = {"frozen_S3_later_sharpe": sr(s3f), "frozen_BH5_later_sharpe": sr(bhf),
         "grid_S3_later_sharpe": rows[s3n]["sharpe"], "grid_BH5_later_sharpe": rows["UNTIMED|frozen5|equal"]["sharpe"],
         "grid_S3_vs_frozen_max_abs_daily_diff": float((rets[s3n] - s3f).abs().max())}
print(recon)

EX = pd.DataFrame(exs)
names = list(EX.columns)
col = {n: i for i, n in enumerate(names)}
BS21 = L.block_boot_sharpe(EX.to_numpy(), 21, B, seed=21)
BS63 = L.block_boot_sharpe(EX.to_numpy(), 63, B, seed=22)

recs = []
for _, v in VT.iterrows():
    n = v["variant"]
    u = untimed_of[n]
    d = BS21[:, col[n]] - BS21[:, col[u]]
    ds = BS21[:, col[n]] - BS21[:, col[s3n]]
    recs.append({"variant": n, "signal": v["signal"], "universe": v["universe"], "weighting": v["weighting"],
                 "riskoff": v["riskoff"], "is_rank": v["is_rank"], "is_sharpe": v["is_sharpe"],
                 "is_d_vs_untimed": v["d_sharpe_vs_untimed"],
                 "later_sharpe": rows[n]["sharpe"], "later_sharpe_se": rows[n]["sharpe_se"],
                 "later_ann_return": rows[n]["ann_return"], "later_ann_vol": rows[n]["ann_vol"],
                 "later_max_dd": rows[n]["max_dd"], "later_turnover_per_year": rows[n]["turnover_per_year"],
                 "later_untimed_sharpe": rows[u]["sharpe"], "later_untimed_max_dd": rows[u]["max_dd"],
                 "later_d_vs_untimed": rows[n]["sharpe"] - rows[u]["sharpe"],
                 "later_d_vs_untimed_ci90_b21": "[%.3f, %.3f]" % L.ci(d),
                 "later_d_vs_S3": rows[n]["sharpe"] - rows[s3n]["sharpe"],
                 "later_d_vs_S3_ci90_b21": "[%.3f, %.3f]" % (L.ci(ds) if n != s3n else (0.0, 0.0))})
FT = pd.DataFrame(recs)
FT["later_rank"] = FT["later_sharpe"].rank(ascending=False, method="min").astype(int)
FT.to_csv(os.path.join(L.OUT, "fwd_variants.csv"), index=False, float_format="%.6g")
pd.DataFrame([{"benchmark": n, **rows[n]} for n in names if n.startswith("UNTIMED|") and "one_" not in n]).to_csv(
    os.path.join(L.OUT, "fwd_benchmarks.csv"), index=False, float_format="%.6g")


def q(s):
    s = pd.Series(s)
    return {"median": float(s.median()), "q25": float(s.quantile(0.25)), "q75": float(s.quantile(0.75)),
            "iqr": float(s.quantile(0.75) - s.quantile(0.25)), "min": float(s.min()), "max": float(s.max()),
            "mean": float(s.mean())}


S = {"window": [str(LATER[0].date()), str(LATER[1].date())], "years": rows[s3n]["years"],
     "consistency_max_abs_diff_IS_window": maxdiff, "reconciliation": recon}
S["later_sharpe"] = q(FT["later_sharpe"])
S["later_sharpe_deciles"] = {f"p{int(p*100)}": float(FT["later_sharpe"].quantile(p)) for p in np.arange(0, 1.01, 0.1)}
S["later_d_vs_untimed"] = q(FT["later_d_vs_untimed"])
S["later_frac_timing_beats_untimed"] = float((FT["later_d_vs_untimed"] > 0).mean())
S["later_frac_beats_S3"] = float((FT["later_d_vs_S3"] > 0).mean())
S["later_untimed"] = {n: rows[n]["sharpe"] for n in names if n.startswith("UNTIMED|") and "one_" not in n}
S["later_grid_mean_d_vs_untimed_ci90_b21"] = L.ci(np.mean([BS21[:, col[n]] - BS21[:, col[untimed_of[n]]] for n in tv], axis=0))
S["later_grid_mean_d_vs_untimed_ci90_b63"] = L.ci(np.mean([BS63[:, col[n]] - BS63[:, col[untimed_of[n]]] for n in tv], axis=0))
S["S3_later_rank_of_72"] = int(FT.loc[FT.variant == s3n, "later_rank"].iloc[0])
best_is = FT.sort_values("is_rank").iloc[0]
S["is_best"] = {"variant": best_is["variant"], "is_sharpe": float(best_is["is_sharpe"]),
                "later_sharpe": float(best_is["later_sharpe"]), "later_rank_of_72": int(best_is["later_rank"])}
top = FT.sort_values("is_rank").head(7)
bot = FT.sort_values("is_rank").tail(7)
S["is_top_decile_later_median"] = float(top["later_sharpe"].median())
S["is_bottom_decile_later_median"] = float(bot["later_sharpe"].median())
rho_s = stats.spearmanr(FT["is_sharpe"], FT["later_sharpe"])[0]
rho_d = stats.spearmanr(FT["is_d_vs_untimed"], FT["later_d_vs_untimed"])[0]
tau_s = stats.kendalltau(FT["is_sharpe"], FT["later_sharpe"])[0]
order = [col[n] for n in FT["variant"]]
boot_rho = np.array([stats.spearmanr(FT["is_sharpe"].to_numpy(), BS21[b, order])[0] for b in range(B)])
dlater = np.column_stack([BS21[:, col[n]] - BS21[:, col[untimed_of[n]]] for n in FT["variant"]])
boot_rho_d = np.array([stats.spearmanr(FT["is_d_vs_untimed"].to_numpy(), dlater[b])[0] for b in range(B)])
S["rank_corr"] = {"spearman_is_vs_later_sharpe": float(rho_s), "spearman_ci90_b21": L.ci(boot_rho),
                  "kendall_is_vs_later_sharpe": float(tau_s),
                  "spearman_is_vs_later_d_vs_untimed": float(rho_d), "spearman_d_ci90_b21": L.ci(boot_rho_d),
                  "note": "CI resamples later-window days (21-session circular blocks) holding IS values fixed; "
                          "variants are highly correlated, so the effective number of independent ranks is small"}
marg = {}
for dim in ("signal", "universe", "weighting", "riskoff"):
    marg[dim] = {lv: {"n": int(len(x)), "is_median_sharpe": float(x["is_sharpe"].median()),
                      "later_median_sharpe": float(x["later_sharpe"].median()),
                      "later_median_d_vs_untimed": float(x["later_d_vs_untimed"].median()),
                      "later_frac_timing_beats_untimed": float((x["later_d_vs_untimed"] > 0).mean())}
                 for lv, x in FT.groupby(dim)}
S["later_marginals"] = marg
fam = []
for (u, w, ro), x in FT.groupby(["universe", "weighting", "riskoff"]):
    fam.append({"config": f"{u}|{w}|{ro}", "n": len(x), "is_median_sharpe": float(x["is_sharpe"].median()),
                "later_median_sharpe": float(x["later_sharpe"].median()),
                "later_untimed_sharpe": float(x["later_untimed_sharpe"].iloc[0]),
                "later_median_d_vs_untimed": float(x["later_d_vs_untimed"].median()),
                "later_median_d_vs_S3": float(x["later_d_vs_S3"].median())})
pd.DataFrame(fam).to_csv(os.path.join(L.OUT, "fwd_families.csv"), index=False, float_format="%.6g")

# per-asset diagnostic sleeves, later window
dg = []
for _, v in DG_IS.iterrows():
    n, u = f"{v['signal']}|one_{v['asset']}", f"UNTIMED|one_{v['asset']}"
    dg.append({"asset": v["asset"], "signal": v["signal"], "is_d_vs_untimed": v["d_sharpe_vs_untimed"],
               "later_sharpe": rows[n]["sharpe"], "later_untimed_sharpe": rows[u]["sharpe"],
               "later_d_vs_untimed": rows[n]["sharpe"] - rows[u]["sharpe"], "later_max_dd": rows[n]["max_dd"],
               "later_untimed_max_dd": rows[u]["max_dd"]})
DGF = pd.DataFrame(dg)
DGF.to_csv(os.path.join(L.OUT, "fwd_diag_assets.csv"), index=False, float_format="%.6g")
S["diag_later_frac_timing_beats_untimed"] = float((DGF["later_d_vs_untimed"] > 0).mean())
S["diag_spearman_is_vs_later_d"] = float(stats.spearmanr(DGF["is_d_vs_untimed"], DGF["later_d_vs_untimed"])[0])
S["diag_later_median_d_by_asset"] = DGF.groupby("asset")["later_d_vs_untimed"].median().to_dict()

# timed minus untimed by calendar year (later window), grid median
RT = pd.DataFrame(rets)
yrs = (1 + RT).groupby(RT.index.year).prod() - 1
gy = pd.DataFrame({n: yrs[n] - yrs[untimed_of[n]] for n in tv})
S["later_years_median_timed_minus_untimed"] = gy.median(axis=1).to_dict()
S["later_years_S3_minus_BH5"] = gy[s3n].to_dict()
with open(os.path.join(L.OUT, "fwd_summary.json"), "w", encoding="utf-8") as fh:
    json.dump(S, fh, indent=1, default=str)
print(json.dumps({k: S[k] for k in ("later_sharpe", "later_d_vs_untimed", "later_frac_timing_beats_untimed",
                                    "later_frac_beats_S3", "rank_corr", "is_best", "S3_later_rank_of_72")}, indent=1, default=str))
