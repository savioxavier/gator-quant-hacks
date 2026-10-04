"""Step 3: P&L under the addendum (BENCH-R, H1-primary, H1-answer, 1s latency sweep, lexicon control, H1-Q).

Reads the frozen positions from backtest/positions/ (hash-checked) and joins exit prices only here.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from lib import (OUT, BT, TEXT, B, SEED, SYMS, QSYMS, TZ, COST_ROWS, Bars, Quotes, answer_summary, check_addendum,
                 sha256, stance_scorer, summarize, tick_pts, trade, usd_per_tick, write_json)
from pit import pit_fit

check_addendum()
P = OUT / "positions"
R = OUT / "results"
R.mkdir(exist_ok=True, parents=True)
for line in (P / "manifest_sha256.txt").read_text().splitlines():
    h, f = line.split("  ")
    if sha256(P / f) != h:
        raise SystemExit(f"positions file changed after freeze: {f}")

m = pd.read_csv(P / "meetings_positions.csv", dtype={"date": str})
for c in ["tau_end_upper", "tau_end_point", "tau_end_conv"]:
    m[c] = pd.to_datetime(m[c], utc=True, format="ISO8601").dt.tz_convert(TZ)
a = pd.read_csv(P / "answers_positions.csv", dtype={"date": str})
for c in ["tau_k_upper", "t0"]:
    a[c] = pd.to_datetime(a[c], utc=True, format="ISO8601").dt.tz_convert(TZ)
bars = Bars()
quotes = Quotes()
status = json.loads((P / "positions_status.json").read_text())
T = lambda d, s: pd.Timestamp(f"{d} {s}", tz=TZ)
SAMPLES = {"confirmation_2023_2026_powell": "confirmation", "contaminated_2016_2022": "2016-2022",
           "warsh_text_only": "warsh"}
summ_rows = []


def add_summary(test, variant, sample, sym, df, extra=None, side="two"):
    """Per-meeting P&L summaries: dollars pooled; ticks by tick era."""
    for cost in COST_ROWS:
        y = df[f"{cost}_usd"].dropna()
        if len(y) == 0:
            continue
        row = dict(test=test, variant=variant, sample=sample, sym=sym, cost=cost, unit="usd", tick_era="all",
                   designated_side=side, **summarize(y.values))
        if extra:
            row.update(extra)
        summ_rows.append(row)
        for te, g in df.groupby("tick_era"):
            y = g[f"{cost}_ticks"].dropna()
            if len(y):
                row = dict(test=test, variant=variant, sample=sample, sym=sym, cost=cost, unit="ticks",
                           tick_era=te, designated_side=side, **summarize(y.values))
                if extra:
                    row.update(extra)
                summ_rows.append(row)


def wild_test(y, X, j, seed=SEED, B_=B):
    """OLS coefficient j with HC3 t and a restricted (null-imposed) Rademacher wild bootstrap."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    n, k = X.shape
    XtXi = np.linalg.pinv(X.T @ X)
    A = XtXi @ X.T
    h = np.einsum("ij,ji->i", X, A)
    beta = A @ y
    u = y - X @ beta
    se = math.sqrt(np.sum(A[j] ** 2 * u ** 2 / (1 - h) ** 2))
    t0 = beta[j] / se
    Xr = np.delete(X, j, axis=1)
    br = np.linalg.lstsq(Xr, y, rcond=None)[0]
    ur = y - Xr @ br
    rng = np.random.default_rng(seed)
    W = rng.choice([-1.0, 1.0], size=(n, B_))
    Ys = (Xr @ br)[:, None] + W * ur[:, None]
    Bs = A @ Ys
    Us = Ys - X @ Bs
    ses = np.sqrt(np.sum((A[j] ** 2)[:, None] * Us ** 2 / ((1 - h) ** 2)[:, None], axis=0))
    ts = Bs[j] / ses
    return dict(coef=beta[j], t_hc3=t0, n=n, p_two=float((1 + np.sum(np.abs(ts) >= abs(t0))) / (B_ + 1)),
                p_lower=float((1 + np.sum(ts <= t0)) / (B_ + 1)), p_upper=float((1 + np.sum(ts >= t0)) / (B_ + 1)))


# ======================================================================== BENCH-R (addendum 5)
bench_rows = []
sch = m[(m.scheduled == 1) & (m.market_window_covers_event == 1)].copy()
for r in sch.itertuples():
    for s in SYMS:
        pos = getattr(r, f"bench_pos_{s}")
        if not np.isfinite(pos) or pos == 0:
            continue
        e_ts, e_px = bars.next_open(r.date, s, T(r.date, "14:20:00"), tag="bench_entry")
        for variant, tx in [("exit_tau_upper", r.tau_end_upper), ("exit_1530", T(r.date, "15:30:00"))]:
            x_ts, x_px = bars.next_open(r.date, s, tx, tag=f"bench_{variant}")
            if e_ts is None or x_ts is None:
                continue
            tr = trade(r.date, s, pos, e_ts, e_px, x_ts, x_px, e_ts, x_ts, quotes)
            tr.update(meeting=r.meeting, variant=variant, era=r.era_bench, chair=r.chair,
                      drop_timing=r.drop_timing, sample_role=r.sample_role, year=int(r.date[:4]),
                      R=getattr(r, f"R_{s}"), tau_src=r.tau_src)
            bench_rows.append(tr)
bench = pd.DataFrame(bench_rows)
bench.to_csv(R / "benchr_trades.csv", index=False)

for (variant, s), g in bench.groupby(["variant", "sym"]):
    for era, ge in g.groupby("era"):
        side = "one(>0)" if era == "2016-2019" else "two"
        add_summary("BENCH-R", variant, f"era_{era}", s, ge, side=side)
        add_summary("BENCH-R", variant + "|timing_eligible", f"era_{era}", s, ge[ge.drop_timing == 0], side=side)
        add_summary("BENCH-R", variant + "|ex_warsh", f"era_{era}", s, ge[ge.chair != "Warsh"], side=side)
        add_summary("BENCH-R", variant + "|ex_2022", f"era_{era}", s, ge[ge.year != 2022], side=side)
    # Jan 2020 -> earlier era
    g2 = g.copy()
    g2["era2"] = np.where(g2.date <= "2020-01-31", "2016-2020Jan", "2020Mar-2026")
    for era, ge in g2.groupby("era2"):
        add_summary("BENCH-R", variant + "|jan2020_early", f"era_{era}", s, ge,
                    side="one(>0)" if era.startswith("2016") else "two")
    for y, gy in g.groupby("year"):
        add_summary("BENCH-R", variant + "|yearly", f"year_{y}", s, gy)
    dec = g[(g.date >= "2024-10-01") & (g.date <= "2026-09-30")]
    add_summary("BENCH-R", variant + "|decay_2024-10_2026-09", "decay", s, dec)

# break statistics (two-sided): mean difference in gross $ and slope difference of the hold return on R
brk = []
for (variant, s), g in bench.groupby(["variant", "sym"]):
    g = g.sort_values("date")
    late = (g.era == "2020-2026").astype(float).values
    one = np.ones(len(g))
    md = wild_test(g.C0_usd.values, np.column_stack([one, late]), 1)
    brk.append(dict(variant=variant, sym=s, stat="mean_gross_usd_diff_late_minus_early", **md))
    Rv = g.R.values
    sl = wild_test(g.ret.values, np.column_stack([one, late, Rv, Rv * late]), 3)
    brk.append(dict(variant=variant, sym=s, stat="slope_diff_hold_ret_on_R_late_minus_early", **sl))
    for era, ge in g.groupby("era"):
        se = wild_test(ge.ret.values, np.column_stack([np.ones(len(ge)), ge.R.values]), 1)
        brk.append(dict(variant=variant, sym=s, stat=f"slope_hold_ret_on_R_{era}", **se))
        brk.append(dict(variant=variant, sym=s, stat=f"corr_R_vs_hold_move_{era}",
                        coef=float(np.corrcoef(ge.R.values, ge.move_ticks.values)[0, 1]), n=len(ge)))
pd.DataFrame(brk).to_csv(R / "benchr_break_stats.csv", index=False)

# cost hurdle: break-even cost per side = mean gross P&L per trade / 2
hur = []
for (variant, s), g in bench.groupby(["variant", "sym"]):
    for key, gg in list(g.groupby("era")) + [(f"year_{y}", gy) for y, gy in g.groupby("year")]:
        for te, gt in gg.groupby("tick_era"):
            hur.append(dict(variant=variant, sym=s, group=key, tick_era=te, n=len(gt),
                            mean_gross_ticks=gt.C0_ticks.mean(), breakeven_ticks_per_side=gt.C0_ticks.mean() / 2,
                            breakeven_usd_per_side=gt.C0_usd.mean() / 2,
                            median_measured_halfspread_ticks=np.nanmedian(
                                np.r_[gt.hs_entry_ticks.values, gt.hs_exit_ticks.values])
                            if gt.hs_entry_ticks.notna().any() else np.nan))
pd.DataFrame(hur).to_csv(R / "benchr_cost_hurdle.csv", index=False)

# USMPD UST2Y version: continuation in yields, P&L in bp of yield
us = sch[sch.usmpd_stmt_UST2Y.notna()].copy()
us["pnl_bp"] = np.sign(us.usmpd_stmt_UST2Y) * us.usmpd_pc_UST2Y * 100
us[["date", "era_bench", "usmpd_stmt_UST2Y", "usmpd_pc_UST2Y", "pnl_bp"]].to_csv(R / "benchr_usmpd_ust2y.csv",
                                                                               index=False)
for era, g in us.groupby("era_bench"):
    summ_rows.append(dict(test="BENCH-R", variant="usmpd_UST2Y_stmt_sign_on_pc_window", sample=f"era_{era}",
                          sym="UST2Y", cost="C0", unit="bp_yield", tick_era="all",
                          designated_side="one(>0)" if era == "2016-2019" else "two",
                          **summarize(g.pnl_bp[g.pnl_bp.notna() & (g.usmpd_stmt_UST2Y != 0)].values)))


# ======================================================================== H1-primary (addendum 3)
def h1_trades(key: str, pos_col: str | None = None) -> pd.DataFrame:
    pos_col = pos_col or f"{key}__pos"
    rows = []
    elig = m[(m.scheduled == 1) & (m.drop_timing == 0) & np.isfinite(m[pos_col]) & (m[pos_col] != 0)]
    for r in elig.itertuples():
        pos = getattr(r, pos_col)
        clocks = {"primary": r.tau_end_upper, "exec30": r.tau_end_upper + pd.Timedelta(seconds=30),
                  "point_clock": r.tau_end_point, "convention_clock": r.tau_end_conv}
        for s in SYMS:
            for clock, tau in clocks.items():
                e_ts, e_px = bars.next_open(r.date, s, tau, tag=f"h1_{clock}")
                if e_ts is None or e_ts >= T(r.date, "15:59:00"):
                    continue
                exits = [("exit_1600", T(r.date, "16:00:00"))]
                if clock == "primary":
                    exits.append(("exit_1630", T(r.date, "16:30:00")))
                for ex, TT in exits:
                    x_ts, x_px = bars.close_at(r.date, s, TT, lo=e_ts, tag=f"h1_{ex}")
                    if x_ts is None:
                        continue
                    tr = trade(r.date, s, pos, e_ts, e_px, x_ts, x_px, e_ts, x_ts + pd.Timedelta(minutes=1), quotes)
                    tr.update(meeting=r.meeting, signal=key, clock=clock, exit=ex,
                              sample=SAMPLES.get(r.sample_role, r.sample_role), chair=r.chair,
                              sep=r.sep_meeting, year=int(r.date[:4]), start_unc_s=r.start_unc_s,
                              sens1_drop=r.sens1_drop, sens2_drop=r.sens2_drop, sens3_keep=r.sens3_keep,
                              s=getattr(r, "H1") if key.startswith("H1") else getattr(r, "lex_H1_raw")
                              if key == "lexH1raw" else getattr(r, "lex_H1"),
                              R_ZT=r.R_ZT, resid=getattr(r, f"{key}__resid"),
                              es_halt_exit=(s == "ES" and ex == "exit_1630" and x_ts < T(r.date, "16:15:00")))
                    rows.append(tr)
    return pd.DataFrame(rows)


def g3_block(key: str, tr: pd.DataFrame) -> dict:
    """G3 decision on the confirmation sample (ZT, primary clock, 16:00 exit, gross) plus non-decisive extras."""
    out = {"signal": key}
    c = tr[(tr["sample"] == "confirmation") & (tr.sym == "ZT") & (tr.clock == "primary") &
           (tr.exit == "exit_1600")].sort_values("date")
    y = c.C0_ticks.values
    out["n"] = len(y)
    if len(y) < 3:
        out["decision"] = "NO-GO (insufficient data: n < 15)" if len(y) < 15 else None
        return out
    sm = summarize(y)
    out.update({k: sm[k] for k in ["mean", "sd", "median", "hit", "t", "wb_p_one", "wb_p_two", "bb_ci90_lo",
                                   "bb_ci90_hi", "bb_p_one"]})
    out["mean_usd"] = c.C0_usd.mean()
    se = sm["sd"] / math.sqrt(len(y))
    from scipy import stats
    out["t_ci90_hi"] = sm["mean"] + stats.t.ppf(0.95, len(y) - 1) * se
    go = (len(y) >= 15) and (sm["mean"] > 0) and (sm["wb_p_one"] <= 0.05)
    if len(y) < 15:
        out["decision"] = "NO-GO (insufficient data: n < 15)"
    else:
        out["decision"] = "GO" if go else (f"NO-GO: not detected (90% block-bootstrap CI upper bound "
                                           f"{sm['bb_ci90_hi']:.2f} ticks)")
    out["block_boot_agrees"] = bool((sm["bb_p_one"] <= 0.05) == (sm["wb_p_one"] <= 0.05))
    # leave-one-out and drop top-2 |ZT move|
    loo = [(c.date.iloc[i], np.delete(y, i).mean()) for i in range(len(y))]
    out["loo_min"] = min(v for _, v in loo)
    out["loo_max"] = max(v for _, v in loo)
    infl = max(loo, key=lambda kv: abs(kv[1] - sm["mean"]))
    out["loo_most_influential"] = infl[0]
    top2 = c.assign(absmove=c.move_ticks.abs()).nlargest(2, "absmove").date.tolist()
    y2 = c[~c.date.isin(top2)].C0_ticks.values
    s2 = summarize(y2)
    out.update(drop_top2_dates=top2, drop_top2_mean=s2["mean"], drop_top2_wb_p_one=s2["wb_p_one"])
    # permutation: signals permuted across the valid confirmation meetings, positions recomputed point-in-time
    sigcol = {"H1": "H1", "lexH1raw": "lex_H1_raw", "lexH1": "lex_H1"}[key]
    mm = m.sort_values("date").reset_index(drop=True)
    idx = mm.index[mm.date.isin(c.date)].values
    move = c.set_index("date").move_ticks.reindex(mm.date.iloc[idx]).values
    s0 = mm[sigcol].values.astype(float)
    rng = np.random.default_rng(SEED)
    stat0 = y.mean()
    cnt = 0
    for _ in range(B):
        sp = s0.copy()
        sp[idx] = s0[idx][rng.permutation(len(idx))]
        f = pit_fit(mm, sigcol, prefix="p", sig_override=sp, only_idx=idx)
        pos = f["p__pos"].values[idx]
        cnt += np.nanmean(pos * move) >= stat0
    out["perm_p_one"] = (1 + cnt) / (B + 1)
    # companion slope (3.7): ZT exit return on s with R control; one-sided slope < 0
    ws = wild_test(c.ret.values, np.column_stack([np.ones(len(c)), c.s.values, c.R_ZT.values]), 1)
    out.update(slope_coef=ws["coef"], slope_t_hc3=ws["t_hc3"], slope_p_lower=ws["p_lower"],
               slope_p_two=ws["p_two"])
    # extra rows and robustness symbols
    for clock in ["exec30", "point_clock", "convention_clock"]:
        e = tr[(tr["sample"] == "confirmation") & (tr.sym == "ZT") & (tr.clock == clock) & (tr.exit == "exit_1600")]
        out[f"{clock}_n"], out[f"{clock}_mean"] = len(e), e.C0_ticks.mean()
    if go:
        out["exec30_rule"] = "no-trade conclusion" if not (out["exec30_mean"] > 0) else "exec30 positive"
    for nm, mask in [("sens1_drop_text_flags", ~c.sens1_drop.astype(bool)),
                     ("sens2_drop_degraded", ~c.sens2_drop.astype(bool)),
                     ("sens3_unc_le10", c.sens3_keep.astype(bool))]:
        ss = summarize(c[mask].C0_ticks.values)
        out[f"{nm}_n"], out[f"{nm}_mean"], out[f"{nm}_wb_p_one"] = ss["n"], ss.get("mean"), ss.get("wb_p_one")
    return out


g3_all = {}
h1_frames = []
for key in ["H1", "lexH1raw", "lexH1"]:
    npos = status[key]["n_positions"]
    if npos == 0:
        g3_all[key] = {"signal": key, "status": "not computed" if key == "H1" else "not estimable",
                       "reason": ("no stance scores: FOMC-RoBERTa gated; D1 chrono-bert scores not yet built"
                                  if key == "H1" else
                                  f"frozen MIN_HD=5 lexicon H1 defined for {status[key]['n_signal']} of 75 "
                                  f"meetings; no meeting passes the 8-meeting burn-in")}
        continue
    tr = h1_trades(key)
    h1_frames.append(tr)
    for (smp, s, clock, ex), g in tr.groupby(["sample", "sym", "clock", "exit"]):
        side = "one(>0)" if (key == "H1" and smp == "confirmation" and s == "ZT" and clock == "primary"
                             and ex == "exit_1600") else "two"
        add_summary(f"H1-primary[{key}]", f"{clock}|{ex}", smp, s, g, side=side)
    zt = tr[(tr.sym == "ZT") & (tr.clock == "primary") & (tr.exit == "exit_1600")]
    for nm, mask in [("sens1_drop_text_flags", ~zt.sens1_drop.astype(bool)),
                     ("sens2_drop_degraded", ~zt.sens2_drop.astype(bool)),
                     ("sens3_unc_le10", zt.sens3_keep.astype(bool))]:
        for smp, g in zt[mask].groupby("sample"):
            add_summary(f"H1-primary[{key}]", f"primary|exit_1600|{nm}", smp, "ZT", g)
    d = zt[zt["sample"] == "2016-2022"]
    if len(d) > 5:
        x22 = (d.year == 2022).astype(float).values
        g3x = wild_test(d.C0_usd.values, np.column_stack([np.ones(len(d)), x22]), 1)
        xs = d.sep.astype(float).values
        g3s = wild_test(d.C0_usd.values, np.column_stack([np.ones(len(d)), xs]), 1)
        g3c = wild_test(d.ret.values, np.column_stack([np.ones(len(d)), d.s.values, d.R_ZT.values,
                                                       (d.chair == "Yellen").astype(float).values]), 1)
        write_json(R / f"h1primary_{key}_2016_2022_robustness.json",
                   {"2022_vs_rest_usd": g3x, "sep_vs_nonsep_usd": g3s,
                    "companion_slope_with_chair_dummy": g3c})
    g3_all[key] = g3_block(key, tr)
# H1-Q (addendum 6): robustness only, reported next to H1-primary; same trades and windows, never gated
if status["H1Q"]["n_positions"] > 0:
    trq = h1_trades("H1Q")
    h1_frames.append(trq)
    for (smp, s, clock, ex), g in trq.groupby(["sample", "sym", "clock", "exit"]):
        add_summary("H1-Q[H1Q]", f"{clock}|{ex}", smp, s, g)
    g3_all["H1Q"] = {"signal": "H1-Q", "status": "robustness only (addendum 6); not gated"}
    for smp in ["confirmation", "2016-2022"]:
        c = trq[(trq["sample"] == smp) & (trq.sym == "ZT") & (trq.clock == "primary") & (trq.exit == "exit_1600")]
        blk = {"n": int(len(c))}
        if len(c) >= 3:
            sm = summarize(c.C0_ticks.values)
            blk.update({k: sm.get(k) for k in ["mean", "sd", "median", "hit", "t", "wb_p_one", "wb_p_two",
                                               "bb_ci90_lo", "bb_ci90_hi", "bb_p_one"]})
            blk["mean_usd"] = float(c.C0_usd.mean())
        g3_all["H1Q"][f"ZT_primary_exit1600_C0_{smp}"] = blk
else:
    g3_all["H1Q"] = {"signal": "H1-Q", "status": "not computed",
                     "reason": "needs stance q_mean_score and H1; FOMC-RoBERTa gated, D1 scores not built"}
h1 = pd.concat(h1_frames) if h1_frames else pd.DataFrame()
h1.to_csv(R / "h1primary_trades.csv", index=False)
write_json(R / "g3_and_h1primary_extras.json", g3_all)


# ======================================================================== H1-answer 1m (addendum 4.2/4.3)
def ans_trades(key: str) -> pd.DataFrame:
    rows = []
    for h in [1, 5, 15]:
        f = P / f"answer_sel_{key}_h{h}.csv"
        sel = pd.read_csv(f, dtype={"date": str})
        if len(sel) == 0:
            continue
        sel["t0"] = pd.to_datetime(sel.t0, utc=True, format="ISO8601").dt.tz_convert(TZ)
        for r in sel.itertuples():
            pos = getattr(r, f"{key}__pos")
            if not np.isfinite(pos) or pos == 0:
                continue
            e_ts, e_px = bars.next_open(r.date, "ZT", r.t0, tag="ans_entry")
            x_ts, x_px = bars.close_at(r.date, "ZT", r.t0 + pd.Timedelta(minutes=h), lo=e_ts, tag=f"ans_h{h}")
            if x_ts is None:
                continue
            tr = trade(r.date, "ZT", pos, e_ts, e_px, x_ts, x_px, e_ts, x_ts + pd.Timedelta(minutes=1), quotes)
            tr.update(answer_id=r.answer_id, meeting=r.meeting, h=h, signal=key,
                      sample=SAMPLES.get(r.sample_role, r.sample_role), start_unc_s=r.start_unc_s)
            rows.append(tr)
    return pd.DataFrame(rows)


ans_rows = []
sweep_frames = []
ans_frames = []
for key in ["H1", "lexH1raw", "lexH1"]:
    at = ans_trades(key)
    if len(at) == 0:
        ans_rows.append(dict(signal=key, status="not computed" if key == "H1" else "not estimable"))
        continue
    ans_frames.append(at)
    for (smp, h), g in at.groupby(["sample", "h"]):
        for split, gg in [("all", g), ("unc_le10", g[g.start_unc_s <= 10]), ("unc_gt10", g[g.start_unc_s > 10])]:
            for cost in COST_ROWS:
                col = f"{cost}_ticks" if g.tick_era.nunique() == 1 else f"{cost}_usd"
                yy = gg[[col, "meeting", "date"]].dropna()
                if len(yy) == 0:
                    continue
                ans_rows.append(dict(signal=key, sample=smp, h=h, split=split, cost=cost,
                                     unit=col.split("_")[-1], **answer_summary(yy[col].values, yy.meeting.values,
                                                                               yy.date.values)))
pd.DataFrame(ans_rows).to_csv(R / "h1answer_summary.csv", index=False)
(pd.concat(ans_frames) if ans_frames else pd.DataFrame()).to_csv(R / "h1answer_trades.csv", index=False)


# ======================================================================== 1s latency sweep (addendum 4.4)
def sweep(key: str) -> pd.DataFrame:
    rows = []
    for h, hs in [(1, 60), (5, 300)]:
        sel = pd.read_csv(P / f"answer_sel_{key}_h{h}.csv", dtype={"date": str})
        if len(sel) == 0:
            continue
        sel["tau_k_upper"] = pd.to_datetime(sel.tau_k_upper, utc=True, format="ISO8601").dt.tz_convert(TZ)
        for r in sel.itertuples():
            pos = getattr(r, f"{key}__pos")
            if not np.isfinite(pos) or pos == 0:
                continue
            for L in [0, 5, 15, 30]:
                te = (r.tau_k_upper + pd.Timedelta(seconds=L)).ceil("s")
                tx = te + pd.Timedelta(seconds=hs)
                for s in QSYMS:
                    b0, a0, st0 = quotes.at(r.date, s, te)
                    b1, a1, st1 = quotes.at(r.date, s, tx)
                    if not (np.isfinite(b0) and np.isfinite(b1)):
                        continue
                    tk = tick_pts(s, r.date)
                    upt = usd_per_tick(s, r.date)
                    mid0, mid1 = (a0 + b0) / 2, (a1 + b1) / 2
                    g = pos * (mid1 - mid0) / tk
                    q = ((b1 - a0) if pos > 0 else (b0 - a1)) / tk
                    rows.append(dict(answer_id=r.answer_id, meeting=r.meeting, date=r.date, h=h, L=L, sym=s,
                                     pos=pos, sample=SAMPLES.get(r.sample_role, r.sample_role),
                                     start_unc_s=r.start_unc_s, te=te, tx=tx, stale0=st0, stale1=st1,
                                     tick_era=("ZT_1/128_2016-2018" if (s == "ZT" and r.date <= "2018-12-31")
                                               else ("ZT_1/256_2019+" if s == "ZT" else f"{s}_const")),
                                     mid_ticks=g, quote_ticks=q, C2_ticks=g - 4, C4_ticks=g - 8,
                                     mid_usd=g * upt, quote_usd=q * upt, C2_usd=(g - 4) * upt, C4_usd=(g - 8) * upt))
    return pd.DataFrame(rows)


sw_rows = []
for key in ["H1", "lexH1raw", "lexH1"]:
    sw = sweep(key)
    if len(sw) == 0:
        sw_rows.append(dict(signal=key, status="not computed" if key == "H1" else "not estimable"))
        continue
    sweep_frames.append(sw.assign(signal=key))
    for (smp, h, L, s), g in sw.groupby(["sample", "h", "L", "sym"]):
        for split, gg in [("all", g), ("unc_le10", g[g.start_unc_s <= 10]), ("unc_gt10", g[g.start_unc_s > 10])]:
            for cost in ["mid", "quote", "C2", "C4"]:
                col = f"{cost}_ticks" if gg.tick_era.nunique() == 1 else f"{cost}_usd"
                if len(gg) == 0:
                    continue
                sw_rows.append(dict(signal=key, sample=smp, h=h, L=L, sym=s, split=split, cost=cost,
                                    unit=col.split("_")[-1], stale_gt60=int(((gg.stale0 > 60) | (gg.stale1 > 60)).sum()),
                                    **answer_summary(gg[col].values, gg.meeting.values, gg.date.values)))
pd.DataFrame(sw_rows).to_csv(R / "h1answer_1s_sweep_summary.csv", index=False)
(pd.concat(sweep_frames) if sweep_frames else pd.DataFrame()).to_csv(R / "h1answer_1s_sweep_trades.csv", index=False)

pd.DataFrame(summ_rows).to_csv(R / "summary_long.csv", index=False)
pd.DataFrame(bars.log).to_csv(R / "bar_log_pnl.csv", index=False)
(R / "run_meta.json").write_text(json.dumps(dict(
    addendum_sha256=sha256(BT / "ADDENDUM.md"), seed=SEED, draws=B, bad_quote_records_skipped=quotes.n_bad,
    positions_manifest=(P / "manifest_sha256.txt").read_text(),
    stance_scorer=stance_scorer(), text_dir=str(TEXT), out_dir=str(OUT),
    text_meetings_sha256=sha256(TEXT / "meetings.parquet"),
    text_answers_sha256=sha256(TEXT / "answers.parquet")), indent=2))
print("done")
