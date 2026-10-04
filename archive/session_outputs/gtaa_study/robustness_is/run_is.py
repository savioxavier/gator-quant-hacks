"""In-sample neighbourhood of GTAA rules (period "IS": data through 2024-10-02 only).

Writes, into this folder:
  is_variants.csv          every timed variant (72) with its untimed benchmark, differences and bootstrap CIs
  is_benchmarks.csv        the 6 untimed benchmarks
  is_families.csv          family summaries and the pre-stated robustness verdict
  is_neighbours.csv        frozen S3 and its one-step neighbours
  is_diag_assets.csv       per-asset diagnostic sleeves (10 assets x 6 signals + 10 untimed), not used to choose
  is_s3_vs_bh5_years.csv   S3 minus BH5 by calendar year on the common window
  is_daily_excess.parquet  daily excess returns of every config on the IS window
  is_summary.json          grid summaries, DSR, CSCV PBO, split-half persistence, point-in-time checks
  is_done.json             marker read by run_fwd.py (the later window is computed only after this exists)

PRE-STATED ROBUSTNESS CRITERION (fixed before any number was computed). A family of variants "robustly beats
S3 and its own untimed benchmark in-sample" only if all three hold:
  (i)   its median member Sharpe exceeds the S3 Sharpe and the median of its members' own untimed Sharpes;
  (ii)  at least 75% of its members beat both S3 and their own untimed benchmark (point estimates);
  (iii) the family-average Sharpe difference vs S3 and the family-average difference vs own untimed both have a
        90% paired circular block-bootstrap interval (63-session blocks, 2000 draws) with lower bound > 0.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gtaa_lib as L  # noqa: E402
from src import engine as E  # noqa: E402
from src import forward2 as F2  # noqa: E402
from src import pbo as PBO  # noqa: E402

t0 = time.time()
PERIOD = "IS"
B = 2000
ohlc, rf = L.load(PERIOD)
close = ohlc["close"]
cal = close.index
assert cal[-1] <= pd.Timestamp("2024-10-02"), cal[-1]
print("IS data:", cal[0].date(), "->", cal[-1].date(), "tickers", L.ALL_TICKERS)

GRID = L.grid()
BENCH = [(None, u, w, None) for u in L.UNIVERSES for w in L.WEIGHTINGS]
print(f"grid: {len(GRID)} timed variants, {len(BENCH)} untimed benchmarks")

# ---------------------------------------------------------------- common start (programmatic)
fv = {L.vid(k): L.first_valid_decision(k, close, rf) for k in GRID}
for b in BENCH:
    fv["UNTIMED|" + b[1] + "|" + b[2]] = L.first_valid_decision(("SMA10", b[1], b[2], "tbill"), close, rf, timed=False)
START_DEC = max(fv.values())
binding = sorted([k for k, v in fv.items() if v == START_DEC])
EVAL_START = cal[cal.get_loc(START_DEC) + 1]
WINDOW = (EVAL_START, cal[-1])
print("common first decision:", START_DEC.date(), "(binding:", binding[:4], "...) first return day:", EVAL_START.date())

# ---------------------------------------------------------------- run every config
rets, exs, rows, pit_hold = {}, {}, {}, {}
rfw = rf.reindex(cal).ffill().fillna(0.0)


def run(key, timed, name):
    w, net, gross, to, held = L.run_variant(key, ohlc, rf, START_DEC, WINDOW, timed=timed)
    # explicit next-open check: the weight held on session t is the decision made at the close of t-1
    exp_held = w.shift(1).fillna(0.0).loc[held.index]
    assert np.allclose(held.to_numpy(), exp_held.to_numpy()), name
    # nothing held before the common first fill
    assert held.loc[: START_DEC].abs().to_numpy().sum() == 0.0
    rets[name] = net
    exs[name] = net - rfw.loc[net.index]
    r = L.stats_row(net, rf, to, held)
    if timed:   # share of the strategic weight switched on, from the T-bill twin of the same rule
        k_tb = (key[0], key[1], key[2], "tbill")
        w_tb = L.decisions(k_tb, close, rf, START_DEC).shift(1).fillna(0.0).loc[held.index]
        r["time_in_market"] = float(w_tb.sum(axis=1).mean())
    else:
        r["time_in_market"] = 1.0
    rows[name] = r
    return w


for b in BENCH:
    run(("SMA10", b[1], b[2], "tbill"), False, f"UNTIMED|{b[1]}|{b[2]}")
wdec = {}
for k in GRID:
    wdec[L.vid(k)] = run(k, True, L.vid(k))
print(f"simulated {len(rows)} configs in {time.time()-t0:.0f}s")

# ---------------------------------------------------------------- frozen S3 reconciliation
w_s3 = F2.s3_decisions(PERIOD)
net_s3, _, to_s3, held_s3, _ = E.simulate(w_s3, E.load_ohlc(F2.S3_TICKERS, PERIOD), rf, exec="next_open")
live = held_s3.abs().sum(axis=1) > 0
first = live.idxmax()
own = L.stats_row(net_s3.loc[first:], rf, to_s3.loc[first:], held_s3.loc[first:])
grid_s3 = rets[L.vid(L.S3_KEY)]
d = (net_s3.loc[grid_s3.index[1]:] - grid_s3.loc[grid_s3.index[1]:]).abs().max()
w_bh5 = F2.s3_decisions(PERIOD, buy_and_hold=True)
net_bh5, _, to_bh5, held_bh5, _ = E.simulate(w_bh5, E.load_ohlc(F2.S3_TICKERS, PERIOD), rf, exec="next_open")
liveb = held_bh5.abs().sum(axis=1) > 0
own_bh5 = L.stats_row(net_bh5.loc[liveb.idxmax():], rf, to_bh5.loc[liveb.idxmax():], held_bh5.loc[liveb.idxmax():])
recon = {
    "frozen_S3_own_window": {k: own[k] for k in ("start", "end", "sharpe", "ann_return", "max_dd")},
    "frozen_BH5_own_window": {k: own_bh5[k] for k in ("start", "end", "sharpe", "ann_return", "max_dd")},
    "grid_S3_vs_frozen_S3_max_abs_daily_diff_from_2nd_common_day": float(d),
    "frozen_S3_on_common_window_sharpe": L.stats_row(net_s3.loc[EVAL_START:], rf, to_s3.loc[EVAL_START:],
                                                      held_s3.loc[EVAL_START:])["sharpe"],
}
print("reconciliation:", json.dumps(recon, indent=1, default=str))
assert d < 1e-12, d
assert abs(own["sharpe"] - 0.5105552812213409) < 1e-9, own["sharpe"]

# ---------------------------------------------------------------- point-in-time perturbation test
# Prices and T-bill returns after a cut date are scrambled; every decision up to the cut must be unchanged.
rng = np.random.default_rng(123)
cuts = [pd.Timestamp("2008-09-30"), pd.Timestamp("2015-06-17"), pd.Timestamp("2020-03-31"), pd.Timestamp("2023-11-08")]
pit = {}
for cut in cuts:
    cut = cal[cal.get_indexer([cut], method="pad")[0]]
    close_p = close.copy()
    fut = close_p.index > cut
    close_p.loc[fut] = close_p.loc[fut].to_numpy() * np.exp(rng.normal(0, 0.2, size=close_p.loc[fut].shape))
    rf_p = rf.copy()
    rf_p.loc[rf_p.index > cut] = rng.uniform(0, 0.01, size=(rf_p.index > cut).sum())
    worst = 0.0
    for k in GRID:
        w1 = wdec[L.vid(k)].loc[:cut]
        w2 = L.decisions(k, close_p, rf_p, START_DEC).loc[:cut]
        worst = max(worst, float((w1 - w2).abs().to_numpy().max()))
    for b in BENCH:
        key = ("SMA10", b[1], b[2], "tbill")
        w1 = L.decisions(key, close, rf, START_DEC, timed=False).loc[:cut]
        w2 = L.decisions(key, close_p, rf_p, START_DEC, timed=False).loc[:cut]
        worst = max(worst, float((w1 - w2).abs().to_numpy().max()))
    pit[str(cut.date())] = worst
    assert worst == 0.0, (cut, worst)
print("point-in-time perturbation test (max |dw| up to each cut):", pit)

# ---------------------------------------------------------------- tables
names = list(rows)
EX = pd.DataFrame(exs)[names]
assert EX.notna().all().all()
tv = [L.vid(k) for k in GRID]
untimed_of = {L.vid(k): f"UNTIMED|{k[1]}|{k[2]}" for k in GRID}
s3n = L.vid(L.S3_KEY)
col = {n: i for i, n in enumerate(names)}
print("bootstrapping...")
BS63 = L.block_boot_sharpe(EX.to_numpy(), 63, B, seed=11)
BS21 = L.block_boot_sharpe(EX.to_numpy(), 21, B, seed=12)

recs = []
for k in GRID:
    n = L.vid(k)
    u = untimed_of[n]
    r = {"variant": n, "signal": k[0], "universe": k[1], "weighting": k[2], "riskoff": k[3]}
    r.update({f"is_{a}": v for a, v in rows[n].items() if a not in ("start", "end")})
    r.update({f"untimed_{a}": rows[u][a] for a in ("sharpe", "ann_return", "ann_vol", "max_dd", "turnover_per_year")})
    r["d_sharpe_vs_untimed"] = rows[n]["sharpe"] - rows[u]["sharpe"]
    dd = BS63[:, col[n]] - BS63[:, col[u]]
    r["d_vs_untimed_ci90_lo_b63"], r["d_vs_untimed_ci90_hi_b63"] = L.ci(dd)
    r["d_vs_untimed_p_le0_b63"] = float((dd <= 0).mean())
    dd21 = BS21[:, col[n]] - BS21[:, col[u]]
    r["d_vs_untimed_ci90_lo_b21"], r["d_vs_untimed_ci90_hi_b21"] = L.ci(dd21)
    r["d_sharpe_vs_S3"] = rows[n]["sharpe"] - rows[s3n]["sharpe"]
    ds = BS63[:, col[n]] - BS63[:, col[s3n]]
    r["d_vs_S3_ci90_lo_b63"], r["d_vs_S3_ci90_hi_b63"] = L.ci(ds) if n != s3n else (0.0, 0.0)
    r["d_maxdd_vs_untimed"] = rows[n]["max_dd"] - rows[u]["max_dd"]
    r["is_rank"] = None
    recs.append(r)
VT = pd.DataFrame(recs)
VT["is_rank"] = VT["is_sharpe"].rank(ascending=False, method="min").astype(int)
VT = VT.sort_values("is_rank")
VT.to_csv(os.path.join(L.OUT, "is_variants.csv"), index=False, float_format="%.6g")
BT = pd.DataFrame([{"benchmark": n, **rows[n]} for n in names if n.startswith("UNTIMED")])
BT.to_csv(os.path.join(L.OUT, "is_benchmarks.csv"), index=False, float_format="%.6g")
EX.to_parquet(os.path.join(L.OUT, "is_daily_excess.parquet"))

# ---------------------------------------------------------------- grid summaries
def q(s):
    s = pd.Series(s)
    return {"median": float(s.median()), "q25": float(s.quantile(0.25)), "q75": float(s.quantile(0.75)),
            "iqr": float(s.quantile(0.75) - s.quantile(0.25)), "min": float(s.min()), "max": float(s.max()),
            "mean": float(s.mean())}


summary = {"period": "IS", "data_end": str(cal[-1].date()), "common_first_decision": str(START_DEC.date()),
           "first_return_day": str(EVAL_START.date()), "last_return_day": str(cal[-1].date()),
           "years": rows[s3n]["years"], "binding_configs": binding, "n_timed": len(GRID), "n_untimed": len(BENCH),
           "bootstrap": {"B": B, "blocks": [63, 21], "type": "circular, paired"}, "reconciliation": recon,
           "pit_perturbation_max_abs_dw": pit}
summary["is_sharpe"] = q(VT["is_sharpe"])
summary["d_sharpe_vs_untimed"] = q(VT["d_sharpe_vs_untimed"])
summary["d_maxdd_vs_untimed"] = q(VT["d_maxdd_vs_untimed"])
summary["frac_timing_beats_untimed"] = float((VT["d_sharpe_vs_untimed"] > 0).mean())
summary["n_timing_ci90_lo_gt0_b63"] = int((VT["d_vs_untimed_ci90_lo_b63"] > 0).sum())
summary["n_timing_ci90_hi_lt0_b63"] = int((VT["d_vs_untimed_ci90_hi_b63"] < 0).sum())
summary["frac_beats_S3"] = float((VT["d_sharpe_vs_S3"] > 0).mean())
summary["frac_beats_S3_and_untimed"] = float(((VT["d_sharpe_vs_S3"] > 0) & (VT["d_sharpe_vs_untimed"] > 0)).mean())
summary["S3_common_window"] = rows[s3n]
summary["BH5_common_window"] = rows["UNTIMED|frozen5|equal"]
summary["S3_rank_of_72"] = int(VT.loc[VT["variant"] == s3n, "is_rank"].iloc[0])
summary["grid_mean_d_vs_untimed_ci90_b63"] = L.ci(np.mean([BS63[:, col[n]] - BS63[:, col[untimed_of[n]]] for n in tv], axis=0))
summary["grid_mean_d_vs_untimed_ci90_b21"] = L.ci(np.mean([BS21[:, col[n]] - BS21[:, col[untimed_of[n]]] for n in tv], axis=0))
marg = {}
for dim in ("signal", "universe", "weighting", "riskoff"):
    g = VT.groupby(dim)
    marg[dim] = {lv: {"n": int(len(x)), "median_sharpe": float(x["is_sharpe"].median()),
                      "median_d_vs_untimed": float(x["d_sharpe_vs_untimed"].median()),
                      "frac_timing_beats_untimed": float((x["d_sharpe_vs_untimed"] > 0).mean()),
                      "median_max_dd": float(x["is_max_dd"].median()),
                      "median_turnover": float(x["is_turnover_per_year"].median())} for lv, x in g}
summary["marginals"] = marg

# ---------------------------------------------------------------- S3 one-step neighbours
nbrs = {"signal": ["SMA8", "SMA12", "SMA10_D1", "MOM12"], "universe": ["broad10", "eq4"],
        "weighting": ["invvol63"], "riskoff": ["IEF"]}
dims = ["signal", "universe", "weighting", "riskoff"]
nrec = [{"variant": s3n, "changed": "(S3 itself)", **{f"is_{a}": rows[s3n][a] for a in ("sharpe", "ann_return", "ann_vol", "max_dd", "turnover_per_year")},
         "d_vs_S3": 0.0, "ci90_lo": 0.0, "ci90_hi": 0.0}]
for dim, vals in nbrs.items():
    for v in vals:
        k = list(L.S3_KEY)
        k[dims.index(dim)] = v
        n = L.vid(tuple(k))
        ds = BS63[:, col[n]] - BS63[:, col[s3n]]
        lo, hi = L.ci(ds)
        nrec.append({"variant": n, "changed": f"{dim}->{v}", **{f"is_{a}": rows[n][a] for a in ("sharpe", "ann_return", "ann_vol", "max_dd", "turnover_per_year")},
                     "d_vs_S3": rows[n]["sharpe"] - rows[s3n]["sharpe"], "ci90_lo": lo, "ci90_hi": hi,
                     "d_vs_own_untimed": rows[n]["sharpe"] - rows[untimed_of[n]]["sharpe"]})
NB = pd.DataFrame(nrec)
NB.to_csv(os.path.join(L.OUT, "is_neighbours.csv"), index=False, float_format="%.6g")
summary["S3_neighbours"] = {"n": len(NB) - 1, "median_neighbour_sharpe": float(NB["is_sharpe"].iloc[1:].median()),
                            "min": float(NB["is_sharpe"].iloc[1:].min()), "max": float(NB["is_sharpe"].iloc[1:].max()),
                            "frac_neighbours_below_S3": float((NB["d_vs_S3"].iloc[1:] < 0).mean())}

# ---------------------------------------------------------------- overfitting control
var_sr = float(VT["is_sharpe"].var(ddof=1))
best = VT.iloc[0]["variant"]
neff = PBO.effective_trials(EX[tv])
summary["dsr_best"] = {"variant": best, "is_sharpe": float(VT.iloc[0]["is_sharpe"]), "var_sr_across_grid": var_sr,
                       "n72": E.deflated_sharpe(EX[best], len(tv), var_sr),
                       "n_effective": {"n_eff": neff, **E.deflated_sharpe(EX[best], max(2, int(round(neff))), var_sr)}}
# timing increment (timed minus untimed daily return), information-ratio style
INC = pd.DataFrame({n: EX[n] - EX[untimed_of[n]] for n in tv})
ir = INC.mean() / INC.std() * math.sqrt(252)
best_inc = ir.idxmax()
neff_inc = PBO.effective_trials(INC)
summary["dsr_best_return_increment"] = {"what": "daily return of timed minus its untimed benchmark; IR = its annualised mean/std", "variant": best_inc, "increment_ir": float(ir.max()), "var_ir": float(ir.var(ddof=1)),
                                        "n72": E.deflated_sharpe(INC[best_inc], len(tv), float(ir.var(ddof=1))),
                                        "n_effective": {"n_eff": neff_inc, **E.deflated_sharpe(INC[best_inc], max(2, int(round(neff_inc))), float(ir.var(ddof=1)))},
                                        "increment_ir_distribution": q(ir)}
summary["pbo_cscv_sharpe_72"] = PBO.cscv_pbo(EX[tv], n_blocks=16)
summary["pbo_cscv_sharpe_78_incl_untimed"] = PBO.cscv_pbo(EX, n_blocks=16)
summary["pbo_cscv_return_increment_72"] = PBO.cscv_pbo(INC, n_blocks=16)
summary["pbo_cscv_sharpe_72_blocks10"] = PBO.cscv_pbo(EX[tv], n_blocks=10)
print("PBO:", summary["pbo_cscv_sharpe_72"]["pbo"], summary["pbo_cscv_return_increment_72"]["pbo"])

# ---------------------------------------------------------------- split-half rank persistence (IS only)
mid = EX.index[len(EX) // 2]
h1, h2 = EX.loc[:mid, tv], EX.loc[EX.index > mid, tv]
sr1 = h1.mean() / h1.std() * math.sqrt(252)
sr2 = h2.mean() / h2.std() * math.sqrt(252)
i1 = INC.loc[:mid].mean() / INC.loc[:mid].std() * math.sqrt(252)
i2 = INC.loc[INC.index > mid].mean() / INC.loc[INC.index > mid].std() * math.sqrt(252)
ub = sorted(set(untimed_of.values()))
u1 = EX.loc[:mid, ub].mean() / EX.loc[:mid, ub].std() * math.sqrt(252)
u2 = EX.loc[EX.index > mid, ub].mean() / EX.loc[EX.index > mid, ub].std() * math.sqrt(252)
ds1 = pd.Series({n: sr1[n] - u1[untimed_of[n]] for n in tv})
ds2 = pd.Series({n: sr2[n] - u2[untimed_of[n]] for n in tv})
s3_1, s3_2 = sr1[s3n], sr2[s3n]
summary["split_half"] = {"split_after": str(mid.date()),
                         "spearman_sharpe": float(stats.spearmanr(sr1, sr2)[0]),
                         "spearman_d_sharpe_vs_untimed": float(stats.spearmanr(ds1, ds2)[0]),
                         "spearman_return_increment_ir": float(stats.spearmanr(i1, i2)[0]),
                         "median_sharpe_h1": float(sr1.median()), "median_sharpe_h2": float(sr2.median()),
                         "S3_sharpe_h1": float(s3_1), "S3_sharpe_h2": float(s3_2),
                         "untimed_sharpe_h1": u1.to_dict(), "untimed_sharpe_h2": u2.to_dict(),
                         "median_d_sharpe_vs_untimed_h1": float(ds1.median()), "median_d_sharpe_vs_untimed_h2": float(ds2.median()),
                         "frac_timing_beats_untimed_sharpe_h1": float((ds1 > 0).mean()),
                         "frac_timing_beats_untimed_sharpe_h2": float((ds2 > 0).mean()),
                         "frac_return_increment_positive_h1": float((i1 > 0).mean()), "frac_return_increment_positive_h2": float((i2 > 0).mean()),
                         "h1_best": sr1.idxmax(), "h1_best_rank_in_h2_of_72": int(sr2.rank(ascending=False)[sr1.idxmax()]),
                         "h1_best_sharpe_h2": float(sr2[sr1.idxmax()])}
pd.DataFrame({"sharpe_h1": sr1, "sharpe_h2": sr2, "d_vs_untimed_h1": ds1, "d_vs_untimed_h2": ds2}).to_csv(
    os.path.join(L.OUT, "is_split_half.csv"), float_format="%.6g")

# ---------------------------------------------------------------- White reality check (max-statistic bootstrap)
def reality_check(BS, pairs, obs):
    """H0: no variant's Sharpe difference is positive. Statistic: max_k d_k; null distribution: max_k (d*_k - d_k)."""
    dstar = np.column_stack([BS[:, col[a]] - BS[:, col[b]] for a, b in pairs])
    tobs = float(np.max(obs))
    tnull = (dstar - np.asarray(obs)[None, :]).max(axis=1)
    return {"max_d": tobs, "argmax": pairs[int(np.argmax(obs))][0], "p_value": float((tnull >= tobs).mean()),
            "null_95pct": float(np.quantile(tnull, 0.95))}


pairs_u = [(n, untimed_of[n]) for n in tv]
obs_u = [rows[a]["sharpe"] - rows[b]["sharpe"] for a, b in pairs_u]
pairs_s = [(n, s3n) for n in tv if n != s3n]
obs_s = [rows[a]["sharpe"] - rows[b]["sharpe"] for a, b in pairs_s]
summary["reality_check"] = {"best_timed_vs_own_untimed_b63": reality_check(BS63, pairs_u, obs_u),
                            "best_timed_vs_own_untimed_b21": reality_check(BS21, pairs_u, obs_u),
                            "best_variant_vs_S3_b63": reality_check(BS63, pairs_s, obs_s),
                            "best_variant_vs_S3_b21": reality_check(BS21, pairs_s, obs_s)}
print("reality check:", summary["reality_check"])

# ---------------------------------------------------------------- per-year: grid median of timed minus untimed return
RT = pd.DataFrame(rets)
yrs = (1 + RT).groupby(RT.index.year).prod() - 1
gy = pd.DataFrame({n: yrs[n] - yrs[untimed_of[n]] for n in tv})
pd.DataFrame({"median_timed_minus_untimed": gy.median(axis=1), "q25": gy.quantile(0.25, axis=1),
              "q75": gy.quantile(0.75, axis=1), "frac_positive": (gy > 0).mean(axis=1),
              "S3_minus_BH5": gy[s3n]}).to_csv(os.path.join(L.OUT, "is_grid_years.csv"), float_format="%.6g")

# ---------------------------------------------------------------- families + pre-stated verdict
fam_defs = []
for dim in dims:
    for lv in sorted(VT[dim].unique()):
        fam_defs.append((f"{dim}={lv}", VT.loc[VT[dim] == lv, "variant"].tolist()))
for u in L.UNIVERSES:
    for w in L.WEIGHTINGS:
        for ro in L.RISKOFF:
            fam_defs.append((f"config={u}|{w}|{ro} (6 signals)",
                             VT.loc[(VT.universe == u) & (VT.weighting == w) & (VT.riskoff == ro), "variant"].tolist()))
frec = []
s3sr = rows[s3n]["sharpe"]
for fname, mem in fam_defs:
    sub = VT.set_index("variant").loc[mem]
    dvs3 = np.mean([BS63[:, col[n]] - BS63[:, col[s3n]] for n in mem], axis=0)
    dvu = np.mean([BS63[:, col[n]] - BS63[:, col[untimed_of[n]]] for n in mem], axis=0)
    c1 = (sub["is_sharpe"].median() > s3sr) and (sub["is_sharpe"].median() > sub["untimed_sharpe"].median())
    share = float(((sub["d_sharpe_vs_S3"] > 0) & (sub["d_sharpe_vs_untimed"] > 0)).mean())
    c2 = share >= 0.75
    lo3, hi3 = L.ci(dvs3)
    lou, hiu = L.ci(dvu)
    c3 = lo3 > 0 and lou > 0
    frec.append({"family": fname, "n": len(mem), "median_is_sharpe": float(sub["is_sharpe"].median()),
                 "median_untimed_sharpe": float(sub["untimed_sharpe"].median()),
                 "mean_d_vs_S3": float(sub["d_sharpe_vs_S3"].mean()), "mean_d_vs_S3_ci90": f"[{lo3:.3f}, {hi3:.3f}]",
                 "mean_d_vs_untimed": float(sub["d_sharpe_vs_untimed"].mean()), "mean_d_vs_untimed_ci90": f"[{lou:.3f}, {hiu:.3f}]",
                 "share_beating_both": share, "crit_i": bool(c1), "crit_ii": bool(c2), "crit_iii": bool(c3),
                 "robust_beat": bool(c1 and c2 and c3)})
FT = pd.DataFrame(frec)
FT.to_csv(os.path.join(L.OUT, "is_families.csv"), index=False, float_format="%.6g")
summary["families_robust_beat"] = FT.loc[FT["robust_beat"], "family"].tolist()
summary["families_passing_i_and_ii"] = FT.loc[FT["crit_i"] & FT["crit_ii"], "family"].tolist()

# ---------------------------------------------------------------- why: S3 minus BH5 by year, ex-GFC
s3r, bhr = rets[s3n], rets["UNTIMED|frozen5|equal"]
yr = pd.DataFrame({"S3": (1 + s3r).groupby(s3r.index.year).prod() - 1,
                   "BH5": (1 + bhr).groupby(bhr.index.year).prod() - 1})
yr["S3_minus_BH5"] = yr["S3"] - yr["BH5"]
yr.to_csv(os.path.join(L.OUT, "is_s3_vs_bh5_years.csv"), float_format="%.6g")


def sr(x):
    return float(x.mean() / x.std() * math.sqrt(252))


exg = EX.index.year.isin([2008, 2009])
summary["S3_vs_BH5_ex_2008_2009"] = {"S3": sr(EX.loc[~exg, s3n]), "BH5": sr(EX.loc[~exg, "UNTIMED|frozen5|equal"])}
summary["grid_ex_2008_2009"] = {"median_d_vs_untimed": float(np.median([sr(EX.loc[~exg, n]) - sr(EX.loc[~exg, untimed_of[n]]) for n in tv])),
                                "frac_timing_beats_untimed": float(np.mean([sr(EX.loc[~exg, n]) > sr(EX.loc[~exg, untimed_of[n]]) for n in tv]))}
summary["grid_2008_2009_only"] = {"median_d_vs_untimed": float(np.median([sr(EX.loc[exg, n]) - sr(EX.loc[exg, untimed_of[n]]) for n in tv]))}

# ---------------------------------------------------------------- per-asset diagnostic sleeves (not used to choose)
DIAG = []
for t in L.UNIVERSES["broad10"]:
    L.UNIVERSES[f"one_{t}"] = [t]
dex = {}
for t in L.UNIVERSES["broad10"]:
    u = f"one_{t}"
    w, net, gross, to, held = L.run_variant(("SMA10", u, "equal", "tbill"), ohlc, rf, START_DEC, WINDOW, timed=False)
    ru = L.stats_row(net, rf, to, held)
    dex[f"UNTIMED|{u}"] = net - rfw.loc[net.index]
    for s in L.SIGNALS:
        w, net, gross, to, held = L.run_variant((s, u, "equal", "tbill"), ohlc, rf, START_DEC, WINDOW, timed=True)
        r = L.stats_row(net, rf, to, held)
        dex[f"{s}|{u}"] = net - rfw.loc[net.index]
        DIAG.append({"asset": t, "signal": s, "is_sharpe": r["sharpe"], "is_ann_return": r["ann_return"],
                     "is_vol": r["ann_vol"], "is_max_dd": r["max_dd"], "time_in_market": float(held.sum(axis=1).mean()),
                     "untimed_sharpe": ru["sharpe"], "untimed_max_dd": ru["max_dd"],
                     "d_sharpe_vs_untimed": r["sharpe"] - ru["sharpe"]})
DG = pd.DataFrame(DIAG)
DX = pd.DataFrame(dex)
BSD = L.block_boot_sharpe(DX.to_numpy(), 63, B, seed=13)
dcol = {n: i for i, n in enumerate(DX.columns)}
DG["d_ci90_lo_b63"] = [L.ci(BSD[:, dcol[f"{s}|one_{a}"]] - BSD[:, dcol[f"UNTIMED|one_{a}"]])[0] for a, s in zip(DG.asset, DG.signal)]
DG["d_ci90_hi_b63"] = [L.ci(BSD[:, dcol[f"{s}|one_{a}"]] - BSD[:, dcol[f"UNTIMED|one_{a}"]])[1] for a, s in zip(DG.asset, DG.signal)]
DG.to_csv(os.path.join(L.OUT, "is_diag_assets.csv"), index=False, float_format="%.6g")
DX.to_parquet(os.path.join(L.OUT, "is_diag_daily_excess.parquet"))
summary["diag_assets_median_d_by_asset"] = DG.groupby("asset")["d_sharpe_vs_untimed"].median().to_dict()
summary["n_diag_configs"] = int(len(DG) + len(L.UNIVERSES["broad10"]))

with open(os.path.join(L.OUT, "is_summary.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=1, default=str)
h = hashlib.sha256(open(os.path.join(L.OUT, "is_variants.csv"), "rb").read()).hexdigest()
with open(os.path.join(L.OUT, "is_done.json"), "w", encoding="utf-8") as fh:
    json.dump({"written_utc": pd.Timestamp.now("UTC").isoformat(), "is_variants_sha256": h,
               "common_first_decision": str(START_DEC.date())}, fh, indent=1)
print(f"done in {time.time()-t0:.0f}s; is_variants sha256 {h[:16]}")
