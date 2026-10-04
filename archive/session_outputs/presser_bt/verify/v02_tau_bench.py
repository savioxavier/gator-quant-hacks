"""Independent recomputation of tau_end,upper, R_m and BENCH-R (addendum 1.1, 3.2, 5, 7)."""
import json
import numpy as np
import pandas as pd
from vlib import *

ev = pd.read_csv(BT / "events/events.csv", dtype={"date": str})
ans = pd.read_parquet(BT / "text/answers.parquet")
ans["date"] = pd.to_datetime(ans.meeting, format="%Y%m%d").dt.strftime("%Y-%m-%d")

# ---------- tau_end,upper from raw fields
rows = []
for r in ev.itertuples():
    sched = ts(r.date, r.presser_sched_et)
    a = ans[(ans.date == r.date) & (ans.timing_source == "vtt")]
    if pd.notna(r.v0_minus_sched_tv_s) and (pd.notna(r.last_speech_end_s) or len(a)):
        x = np.nanmax([r.last_speech_end_s] + list(a.t_end_video_s + a.end_cue_dur))
        tp = sched + pd.Timedelta(seconds=r.v0_minus_sched_tv_s + x)
        tu = tp + pd.Timedelta(seconds=r.start_unc_s)
        src = "tv"
        gap = x - r.last_speech_end_s
    else:
        tu = ts(r.date, r.presser_end_est_et) + pd.Timedelta(seconds=r.start_unc_s + 1)
        tp = pd.NaT
        src = "fallback"
        gap = np.nan
    rows.append(dict(date=r.date, tau_u=tu, tau_p=tp, src=src, ans_over_lastcue_s=gap))
T = pd.DataFrame(rows)
ev = ev.merge(T, on="date")
theirs = pd.read_csv(BT / "backtest/positions/meetings_positions.csv", dtype={"date": str})
theirs["tau_end_upper"] = pd.to_datetime(theirs.tau_end_upper, utc=True, format="ISO8601").dt.tz_convert(NY)
cmp = ev[["date", "tau_u"]].merge(theirs[["date", "tau_end_upper"]], on="date")
cmp["d_s"] = (cmp.tau_u - cmp.tau_end_upper).dt.total_seconds()
res = {"tau_upper_max_abs_diff_s_vs_backtest": float(cmp.d_s.abs().max()),
       "tau_src_counts": T.src.value_counts().to_dict(),
       "answer_end_past_last_cue_s": T.ans_over_lastcue_s.describe().round(2).to_dict()}
ev["tau_conv"] = pd.to_datetime(ev.date + " " + ev.presser_end_conv_et).dt.tz_localize(NY)
el = ev[(ev.drop_timing == 0) & (ev.scheduled == 1)]
res["tau_upper_minus_conv_s_eligible"] = (el.tau_u - el.tau_conv).dt.total_seconds().describe().round(1).to_dict()

# ---------- market
m1 = load_1m()
px = Px(m1)
qc, nbad = clean_bbo(load_bbo())
sch = ev[(ev.scheduled == 1) & (ev.market_window_covers_event == 1)].copy()


def Rm(day, sym):
    b0, c0 = px.close_before(day, sym, ts(day, "13:50:00"), lo=ts(day, "13:30:00"))
    b1, c1 = px.close_before(day, sym, ts(day, "14:20:00"), lo=ts(day, "13:50:00"))
    return ((c1 / c0 - 1) if (b0 is not None and b1 is not None) else np.nan), b0, b1


for s in ["ZT", "ES", "ZN", "ZF"]:
    sch[f"R_{s}"] = [Rm(d, s)[0] for d in sch.date]
chk = sch[["date", "R_ZT", "R_ES"]].merge(theirs[["date", "R_ZT", "R_ES"]], on="date", suffixes=("", "_bt"))
res["R_ZT_max_abs_diff_vs_backtest"] = float((chk.R_ZT - chk.R_ZT_bt).abs().max())
res["R_ES_max_abs_diff_vs_backtest"] = float((chk.R_ES - chk.R_ES_bt).abs().max())
res["R_ZT_max_abs_diff_vs_events_csv"] = float((sch.R_ZT - sch.zt_r_1350_1420).abs().max())
bb = [Rm(d, "ZT") for d in sch.date]
res["R_end_bar_times"] = pd.Series([b[2].strftime("%H:%M") for b in bb]).value_counts().to_dict()
res["R_start_bar_times"] = pd.Series([b[1].strftime("%H:%M") for b in bb]).value_counts().to_dict()
res["R_ZT_zero_sign_dates"] = sch.loc[sch.R_ZT == 0, "date"].tolist()

trades = []
for r in sch.itertuples():
    for s in ["ZT", "ES", "ZN", "ZF"]:
        Rv = getattr(r, f"R_{s}")
        pos = np.sign(Rv)
        if not np.isfinite(pos) or pos == 0:
            continue
        e_t, e_p = px.next_open(r.date, s, ts(r.date, "14:20:00"))
        for var, tx in [("tau", r.tau_u), ("1530", ts(r.date, "15:30:00"))]:
            x_t, x_p = px.next_open(r.date, s, tx)
            if e_t is None or x_t is None:
                continue
            tk = tick(s, r.date)
            trades.append(dict(date=r.date, sym=s, var=var, pos=pos, R=Rv, e_t=e_t, e_p=e_p, x_t=x_t, x_p=x_p,
                               tk=tk, upt=tk * PT_USD[s], era="2016-2019" if r.date < "2020-01-01" else "2020-2026",
                               drop_timing=r.drop_timing, chair=r.chair, src=r.src,
                               gross_ticks=pos * (x_p - e_p) / tk, ret=x_p / e_p - 1))
tr = pd.DataFrame(trades)
tr["gross_usd"] = tr.gross_ticks * tr.upt
for leg, col in [("e", "e_t"), ("x", "x_t")]:
    q = quote_asof(qc, pd.DataFrame({"sym": tr.sym.values, "t": pd.to_datetime(tr[col].astype(str)).dt.tz_convert(NY)
                                     if False else pd.Series(list(tr[col]))}))
    tr[f"{leg}_bid"], tr[f"{leg}_ask"], tr[f"{leg}_stale"] = q.bid.values, q.ask.values, q.stale_s.values
tr["hs_ticks_rt"] = ((tr.e_ask - tr.e_bid) + (tr.x_ask - tr.x_bid)) / 2 / tr.tk
tr["CM_usd"] = (tr.gross_ticks - tr.hs_ticks_rt) * tr.upt
tr["CQ_usd"] = np.where(tr.pos > 0, tr.x_bid - tr.e_ask, tr.e_bid - tr.x_ask) / tr.tk * tr.upt
tr["C2_usd"] = (tr.gross_ticks - 4) * tr.upt
tr["C4_usd"] = (tr.gross_ticks - 8) * tr.upt
tr.to_csv(V / "v02_benchr_trades.csv", index=False)

out = {}
for (var, s, era), g in tr.groupby(["var", "sym", "era"]):
    k = f"{s}|{var}|{era}"
    out[k] = {c: summ(g[c]) for c in ["gross_usd", "C2_usd", "C4_usd", "CM_usd", "CQ_usd"]}
    out[k]["gross_ticks_by_tick"] = {str(kk): round(float(v), 3) for kk, v in g.groupby("tk").gross_ticks.mean().items()}
    out[k]["median_hs_ticks_per_side"] = float(np.nanmedian(g.hs_ticks_rt) / 2)

bt = pd.read_csv(BT / "backtest/results/benchr_trades.csv", dtype={"date": str})
for var, bv in [("tau", "exit_tau_upper"), ("1530", "exit_1530")]:
    b = bt[bt.variant == bv]
    j = tr[tr["var"] == var].merge(b, on=["date", "sym"], suffixes=("", "_bt"))
    res[f"bench_{var}_trade_count_mine_vs_bt"] = [int((tr["var"] == var).sum()), int(len(b)), int(len(j))]
    res[f"bench_{var}_gross_usd_max_abs_diff"] = float((j.gross_usd - j.C0_usd).abs().max())
    res[f"bench_{var}_CM_usd_max_abs_diff"] = float((j.CM_usd - j.CM_usd_bt).abs().max())
    res[f"bench_{var}_CQ_usd_max_abs_diff"] = float((j.CQ_usd - j.CQ_usd_bt).abs().max())

zt = tr[(tr.sym == "ZT") & (tr["var"] == "tau")]
late = zt[zt.era == "2020-2026"]
early = zt[zt.era == "2016-2019"]
out["ZT|tau|2020-2026|ex2022"] = summ(late[late.date.str[:4] != "2022"].gross_usd)
out["ZT|tau|2022_only"] = summ(late[late.date.str[:4] == "2022"].gross_usd)
out["ZT|tau|decay_2024-10_2026-09"] = summ(zt[zt.date >= "2024-10-01"].gross_usd)
out["ZT|tau|2016-2019|timing_eligible"] = summ(early[early.drop_timing == 0].gross_usd)
out["ZT|tau|2020-2026|timing_eligible"] = summ(late[late.drop_timing == 0].gross_usd)
out["ZT|tau|fallback_clock_meetings"] = zt[zt.src == "fallback"][["date", "gross_usd"]].to_dict("records")
d = late.gross_usd.mean() - early.gross_usd.mean()
rng = np.random.default_rng(3)
allv = zt.sort_values("era").gross_usd.values
ne = len(early)
cnt = 0
for _ in range(20000):
    p = rng.permutation(allv)
    cnt += abs(p[ne:].mean() - p[:ne].mean()) >= abs(d)
out["ZT|tau|break_mean_diff_late_minus_early"] = dict(diff=float(d), perm_p_two=cnt / 20000)
for era, g in zt.groupby("era"):
    out[f"ZT|tau|corr_R_vs_hold_move|{era}"] = float(np.corrcoef(g.R, g.pos * g.gross_ticks)[0, 1])
    for tk_, gg in g.groupby("tk"):
        out[f"ZT|tau|breakeven_ticks_per_side|{era}|tick{tk_}"] = dict(n=len(gg), be=float(gg.gross_ticks.mean() / 2))
us = ev[(ev.scheduled == 1) & ev.usmpd_stmt_UST2Y.notna() & (ev.usmpd_stmt_UST2Y != 0)].copy()
us["pnl_bp"] = np.sign(us.usmpd_stmt_UST2Y) * us.usmpd_pc_UST2Y * 100
for era, g in us.groupby(us.date < "2020-01-01"):
    out[f"USMPD_UST2Y|{'2016-2019' if era else '2020-2026'}"] = summ(g.pnl_bp.dropna())
json.dump(dict(checks=res, results=out), open(V / "v02_bench.json", "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))


def rd(v):
    return {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()}


for k, v in out.items():
    if isinstance(v, dict) and "gross_usd" in v:
        print(k)
        for c in ["gross_usd", "C2_usd", "C4_usd", "CM_usd", "CQ_usd"]:
            print("   ", c, rd(v[c]))
        print("    ticks", v["gross_ticks_by_tick"], "median hs/side", v["median_hs_ticks_per_side"])
    else:
        print(k, rd(v) if isinstance(v, dict) else v)
