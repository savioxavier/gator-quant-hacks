"""Independent read-only audit of backtests/results/presser_strategy against the frozen positions and suite outputs."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<scratch>/team_push")
H1D = REPO / "backtests/results/presser_h1"
POS = REPO / "backtests/presser/backtest/positions"
OUT = REPO / "backtests/results/presser_strategy"
SYMS = ["ZT", "ZF", "ZN", "ES"]
FEE = 2.0
res = {}

# 1. manifest (raw and CRLF forms)
forms = {}
for line in (POS / "manifest_sha256.txt").read_text().splitlines():
    h, f = line.split("  ")
    raw = (POS / f).read_bytes()
    crlf = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    forms[f] = ("raw" if hashlib.sha256(raw).hexdigest() == h else
                "crlf" if hashlib.sha256(crlf).hexdigest() == h else "MISMATCH")
res["manifest_forms"] = pd.Series(forms).value_counts().to_dict()
# git HEAD blob equality for positions dir and suite outputs is checked separately with git diff

mpos = pd.read_csv(POS / "meetings_positions.csv", dtype={"date": str}).set_index("date")
P = pd.read_csv(OUT / "per_trade.csv", dtype={"date": str})

# 2. H1 rows vs suite rows and frozen positions
h1 = pd.read_csv(H1D / "h1primary_trades.csv", dtype={"date": str})
res["h1_trades_filters_available"] = {c: sorted(h1[c].dropna().astype(str).unique().tolist())[:8] for c in ["signal", "clock", "exit"]}
h1 = h1[(h1.signal == "H1") & (h1.clock == "primary") & (h1.exit == "exit_1600")]
ph1 = P[P.strategy == "H1-primary"]
m = ph1.merge(h1, on=["date", "sym"], how="outer", indicator=True, suffixes=("", "_s"))
res["h1_rows_only_in_one_side"] = int((m._merge != "both").sum())
both = m[m._merge == "both"]
res["h1_pos_eq_suite"] = bool((both.pos == both.pos_s).all())
res["h1_gross_ticks_eq_C0_ticks"] = bool(np.allclose(both.gross_ticks, both.C0_ticks))
res["h1_hs_eq_suite"] = bool(np.allclose(both.hs_entry_ticks.fillna(-1), both.hs_entry_ticks_s.fillna(-1)) and
                             np.allclose(both.hs_exit_ticks.fillna(-1), both.hs_exit_ticks_s.fillna(-1)))
res["h1_usd_per_tick_eq"] = bool(np.allclose(both.usd_per_tick, both.usd_per_tick_s))
res["h1_net1x_eq_CMF_usd"] = bool(np.allclose(both.net1x_usd, both.CMF_usd, atol=1e-6))
res["h1_net1x_eq_formula"] = bool(np.allclose(both.net1x_usd, both.C0_usd - (both.hs_entry_ticks_s + both.hs_exit_ticks_s) * both.usd_per_tick_s - 2 * FEE, atol=1e-6, equal_nan=False)) if both.sym.ne("ZF").all() else None
nz = both[both.sym != "ZF"]
res["h1_net1x_eq_formula_exZF"] = bool(np.allclose(nz.net1x_usd, nz.C0_usd - (nz.hs_entry_ticks_s + nz.hs_exit_ticks_s) * nz.usd_per_tick_s - 2 * FEE, atol=1e-6))
res["h1_net2x_eq_gross_minus_2cost"] = bool(np.allclose(both.net2x_usd, both.gross_usd - 2 * (both.gross_usd - both.net1x_usd), atol=1e-6))
zf = both[both.sym == "ZF"]
res["h1_ZF_net1x_eq_C2F"] = bool(np.allclose(zf.net1x_usd, zf.C2F_usd, atol=1e-6))
res["h1_fixed1x_eq_C2F"] = bool(np.allclose(both.fixed1x_usd, both.C2F_usd, atol=1e-6))
res["h1_pos_eq_frozen_H1__pos"] = bool((ph1.pos.values == mpos.loc[ph1.date, "H1__pos"].values).all())
# frozen meetings with a nonzero H1 position but no trade (and vice versa)
fz = mpos[mpos["H1__pos"].fillna(0) != 0].index
tr = set(ph1.date)
res["h1_frozen_nonzero_meetings"] = int(len(fz))
res["h1_trade_meetings"] = int(len(tr))
res["h1_frozen_nonzero_without_trade"] = sorted(set(fz) - tr)
res["h1_trades_with_zero_frozen_pos"] = sorted(d for d in tr if mpos.loc[d, "H1__pos"] == 0)
res["h1_trades_per_sym"] = ph1.groupby("sym").size().to_dict()
res["h1_sample_counts"] = {f"{a}|{b}": int(v) for (a, b), v in ph1[ph1.sym == "ZT"].groupby(["window", "sample"]).size().items()}
res["h1_sample_role_of_frozen_nonzero_without_trade"] = mpos.loc[sorted(set(fz) - tr), "sample_role"].value_counts().to_dict() if len(set(fz) - tr) else {}

# 3. BENCH-R rows vs suite and frozen positions
for s in SYMS:
    b = pd.read_csv(H1D / "tables" / f"benchr_per_meeting_{s}.csv", dtype={"date": str})
    pb = P[(P.strategy == "BENCH-R") & (P.sym == s)]
    mm = pb.merge(b, on="date", how="outer", indicator=True, suffixes=("", "_s"))
    bb = mm[mm._merge == "both"]
    r = {"rows_only_one_side": int((mm._merge != "both").sum()),
         "pos_eq_suite": bool((bb.pos == bb.pos_s).all()),
         "pos_eq_frozen": bool((pb.pos.values == mpos.loc[pb.date, f"bench_pos_{s}"].values).all()),
         "gross_eq_C0": bool(np.allclose(bb.gross_ticks, bb.C0_ticks)),
         "fixed1x_eq_C2F": bool(np.allclose(bb.fixed1x_usd, bb.C2F_usd, atol=1e-6)),
         "timing_eligible_eq_drop_timing0": bool((bb.timing_eligible == (bb.drop_timing == 0).astype(int)).all()),
         "n_drop_timing_rows_included": int((bb.drop_timing != 0).sum())}
    if s != "ZF":
        r["net1x_eq_CM_minus_fee"] = bool(np.allclose(bb.net1x_usd, bb.CM_usd - 2 * FEE, atol=1e-6))
        r["CM_eq_formula"] = bool(np.allclose(bb.CM_usd, bb.C0_usd - (bb.hs_entry_ticks_s + bb.hs_exit_ticks_s) * bb.usd_per_tick_s, atol=1e-6))
    else:
        r["net1x_eq_C2F"] = bool(np.allclose(bb.net1x_usd, bb.C2F_usd, atol=1e-6))
    fzb = mpos[mpos[f"bench_pos_{s}"].fillna(0) != 0].index
    r["frozen_nonzero"] = int(len(fzb))
    r["trades"] = int(len(pb))
    r["frozen_nonzero_without_trade"] = sorted(set(fzb) - set(pb.date))
    r["trades_with_zero_frozen_pos"] = sorted(d for d in pb.date if mpos.loc[d, f"bench_pos_{s}"] == 0)
    res[f"benchr_{s}"] = r

# 4. drop_timing / sample-role in the suite summary: what sample does the suite's headline BENCH-R use?
S = pd.read_csv(H1D / "summary_long.csv")
bs = S[(S.test == "BENCH-R") & (S.variant == "exit_tau_upper") & (S.cost == "C0") & (S.unit == "usd")]
res["suite_benchr_samples"] = sorted(bs["sample"].unique().tolist())
res["suite_benchr_n_by_sample_ZT"] = bs[bs.sym == "ZT"].set_index("sample").n.to_dict()

# 5. recompute daily series and headline metrics
D = pd.read_csv(OUT / "daily_returns.csv", dtype={"date": str})
M = pd.read_csv(OUT / "metrics.csv")
sz = pd.read_csv(OUT / "sizing.csv").set_index(["strategy", "sym"]).N
mx_daily, mx_met = 0.0, 0.0
for (st, s), g in P.groupby(["strategy", "sym"]):
    d = D[(D.strategy == st) & (D.sym == s)].set_index("date")
    n = sz[(st, s)]
    if not (g.N == n).all():
        res[f"N_mismatch_{st}_{s}"] = True
    for c in ["gross", "net1x", "net2x"]:
        p = (g.groupby("date")[f"{c}_usd"].sum() * n / 1e7).reindex(d.index, fill_value=0.0)
        mx_daily = max(mx_daily, float((p - d[f"ret_{c}"]).abs().max()))
        for w in ["IS", "OOS"]:
            r = p[d.window == w].values
            row = M[(M.strategy == st) & (M.sym == s) & (M.variant == "all") & (M.window == w) & (M.cost == c)].iloc[0]
            sh = r.mean() / r.std(ddof=1) * np.sqrt(252)
            eq = 1 + np.cumsum(r)
            pk = np.maximum.accumulate(np.r_[1.0, eq])[1:]
            dd = (eq / pk - 1).min()
            mx_met = max(mx_met, abs(sh - row.sharpe), abs(r.mean() * 252 - row.ann_return),
                         abs(r.std(ddof=1) * np.sqrt(252) - row.ann_vol), abs(dd - row.max_drawdown),
                         abs(len(g[(g.window == w)]) - row.n_trades))
res["daily_recompute_max_abs_diff"] = mx_daily
res["headline_metric_recompute_max_abs_diff (Sharpe/ret/vol/DD/n, 6 sig. digits in csv)"] = mx_met
# window split sanity
res["IS_trades_after_IS_end"] = int((P[P.window == "IS"].date > "2024-10-02").sum())
res["OOS_trades_outside_window"] = int(((P[P.window == "OOS"].date < "2024-10-03") | (P[P.window == "OOS"].date > "2026-10-02")).sum())
res["daily_IS_rows_after_IS_end"] = int((D[D.window == "IS"].date > "2024-10-02").sum())
res["daily_last_date"] = D.date.max()

print(json.dumps(res, indent=1, default=str))
