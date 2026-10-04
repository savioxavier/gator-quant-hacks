"""Step 1 (addendum 9.1): QA before any P&L. Writes backtest/qa/."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lib import (OUT, CACHE, SYMS, TZ, Bars, check_addendum, load_answers, load_events, load_meetings, tau_answer,
                 tau_end, write_json, sha256, BT, PLAN, TEXT)

check_addendum()
QA = OUT / "qa"
QA.mkdir(exist_ok=True, parents=True)
ev = load_events()
ans = load_answers()
mt = load_meetings()
res = {}

# --- input manifest
def _plan_doc(*names: str):
    """First existing plan document among ``names`` (the team repo's preregistration/ folder uses a 'presser_'
    prefix and keeps only some of the plan files); None when none is in this checkout."""
    for name in names:
        for cand in (PLAN / name, PLAN / f"presser_{name}"):
            if cand.exists():
                return cand
    return None


# recorded only (QA); a plan document absent from this checkout is listed as missing instead of stopping the run
man = {}
for key, p in [("ADDENDUM.md", BT / "ADDENDUM.md"),
               ("team_FINAL_PLAN.md", _plan_doc("team_FINAL_PLAN.md")),
               ("merged_plan_v0.md", _plan_doc("merged_plan_v0.md")),
               ("GAP_REPORT.md", _plan_doc("GAP_REPORT.md")),
               ("DEVIATION_D1_stance_model.md", _plan_doc("DEVIATION_D1_stance_model.md", "DEVIATION_D1.md"))]:
    man[str(p) if p is not None else f"{PLAN / key} (missing)"] = sha256(p) if p is not None else "missing"
for p in [BT / "events/events.csv", TEXT / "answers.parquet", TEXT / "meetings.parquet", TEXT / "build_meta.json",
          CACHE / "ohlcv-1m__all_2016_2026.parquet", CACHE / "ohlcv-1s__all_2016_2026.parquet",
          CACHE / "bbo-1s__all_2016_2026.parquet"]:
    man[str(p)] = sha256(p)
write_json(QA / "input_manifest.json", man)

# --- instrument_id per window (13:30-16:30 ET) for each schema
rows = []
for schema in ["ohlcv-1m", "ohlcv-1s", "bbo-1s"]:
    cols = ["ts_recv" if schema == "bbo-1s" else "ts_event", "instrument_id", "symbol"]
    d = pd.read_parquet(CACHE / f"{schema}__all_2016_2026.parquet", columns=cols)
    t = d[cols[0]].dt.tz_convert(TZ)
    d["date"] = t.dt.strftime("%Y-%m-%d")
    g = d.groupby(["date", "symbol"]).instrument_id.agg(["nunique", "first", "size"]).reset_index()
    g["schema"] = schema
    rows.append(g)
inst = pd.concat(rows)
inst.to_csv(QA / "instrument_ids_per_window.csv", index=False)
res["instrument_id_changes_in_window"] = int((inst["nunique"] > 1).sum())
# same instrument across schemas per day/symbol
piv = inst.pivot_table(index=["date", "symbol"], columns="schema", values="first")
mism = piv[piv.nunique(axis=1) > 1]
res["instrument_id_mismatch_across_schemas"] = int(len(mism))

# --- tick re-verification: smallest price step per symbol and year (1m opens/closes)
d = pd.read_parquet(CACHE / "ohlcv-1m__all_2016_2026.parquet", columns=["ts_event", "open", "close", "symbol"])
d["year"] = d.ts_event.dt.year
tk = []
for (s, y), v in d.groupby(["symbol", "year"]):
    px = np.unique(np.concatenate([v.open.values, v.close.values]))
    step = np.diff(px)
    step = step[step > 1e-9]
    # smallest grid that divides every price: check 1/256, 1/128, 1/64, 0.25
    fine = None
    for gsz in [0.25, 1 / 64, 1 / 128, 1 / 256]:  # coarsest grid on which every price lies
        if np.all(np.abs(px / gsz - np.round(px / gsz)) < 1e-6):
            fine = gsz
            break
    tk.append(dict(symbol=s, year=y, min_step=float(step.min()) if len(step) else np.nan, coarsest_grid=fine))
pd.DataFrame(tk).to_csv(QA / "tick_check.csv", index=False)

# --- caption-timeline agreement events vs text label (1.5 s)
cmp = ev[["date", "meeting", "greeting_s", "last_speech_end_s"]].merge(
    mt[["meeting", "greeting_video_s", "last_word_video_s"]], on="meeting", how="left")
cmp["greet_diff_s"] = cmp.greeting_s - cmp.greeting_video_s
cmp["last_diff_s"] = cmp.last_speech_end_s - cmp.last_word_video_s
cmp["flag"] = (cmp.greet_diff_s.abs() > 1.5) | (cmp.last_diff_s.abs() > 1.5)
cmp.to_csv(QA / "caption_timeline_agreement.csv", index=False)
res["caption_agreement_flags"] = cmp.loc[cmp.flag, ["date", "greet_diff_s", "last_diff_s"]].round(2).to_dict("records")
res["caption_greeting_max_abs_diff_s"] = float(cmp.greet_diff_s.abs().max())

# --- tau ordering and entry bars
bars = Bars()
tau_rows = []
for _, r in ev.iterrows():
    am = ans[ans.meeting == r.meeting]
    tu, src = tau_end(r, am, "upper")
    tp, _ = tau_end(r, am, "point")
    tc, _ = tau_end(r, am, "conv")
    timed = am[am.timing_source == "vtt"]
    max_ans_tau = max([tau_answer(r, a) for a in timed.itertuples()]) if (len(timed) and pd.notna(r.v0_minus_sched_tv_s)) else pd.NaT
    e14, _ = bars.next_open(r.date, "ZT", pd.Timestamp(f"{r.date} 14:20:00", tz=TZ), "qa")
    eb, _ = bars.next_open(r.date, "ZT", tu, "qa")
    tau_rows.append(dict(date=r.date, scheduled=r.scheduled, drop_timing=r.drop_timing, tau_src=src,
                         tau_end_upper=tu, tau_end_point=tp, tau_end_conv=tc, max_answer_tau_upper=max_ans_tau,
                         ok_tau_ge_answers=(pd.isna(max_ans_tau) or tu >= max_ans_tau),
                         zt_bar_1420=e14, zt_entry_bar_after_tau=eb,
                         ok_order=(e14 is not None and eb is not None and eb > e14),
                         entry_before_1559=(eb is not None and eb < pd.Timestamp(f"{r.date} 15:59:00", tz=TZ))))
tau = pd.DataFrame(tau_rows)
tau.to_csv(QA / "tau_ordering.csv", index=False)
sch = tau[tau.scheduled == 1]
res["tau_ok_ge_answers_all"] = bool(sch.ok_tau_ge_answers.all())
res["tau_order_ok_scheduled"] = int(sch.ok_order.sum())
res["n_scheduled"] = int(len(sch))
res["entry_before_1559_scheduled"] = int(sch.entry_before_1559.sum())
res["tau_src_counts"] = sch.tau_src.value_counts().to_dict()

# --- A-07 USMPD flags (statement and press-conference windows)
DUR = 1.9  # assumed ZT modified duration for the implied move (QA only)
fl = []
for _, r in ev[ev.scheduled == 1].iterrows():
    d0 = r.date
    T = lambda s: pd.Timestamp(f"{d0} {s}", tz=TZ)
    _, c1350 = bars.close_at(d0, "ZT", T("13:50:00"), lo=T("13:30:00"))
    _, c1420 = bars.close_at(d0, "ZT", T("14:20:00"), lo=T("13:50:00"))
    _, o1420 = bars.next_open(d0, "ZT", T("14:20:00"))
    _, o1530 = bars.next_open(d0, "ZT", T("15:30:00"))
    for win, ret, dy in [("statement", c1420 / c1350 - 1, r.usmpd_stmt_UST2Y),
                         ("presser", o1530 / o1420 - 1, r.usmpd_pc_UST2Y)]:
        implied = -DUR * dy / 100
        big = abs(dy) > 0.02
        wrong = np.sign(ret) != np.sign(implied)
        small = abs(ret) < 0.25 * abs(implied)
        fl.append(dict(date=d0, window=win, zt_ret=ret, ust2y_pp=dy, implied_ret=implied, abs_dy_gt_2bp=big,
                       wrong_way=bool(wrong), lt25pct=bool(small), flag=bool(big and (wrong or small))))
fl = pd.DataFrame(fl)
fl.to_csv(QA / "a07_usmpd_flags.csv", index=False)
res["a07_corr"] = {w: float(v.zt_ret.corr(v.ust2y_pp)) for w, v in fl.groupby("window")}
res["a07_flags"] = fl.loc[fl.flag, ["date", "window", "zt_ret", "ust2y_pp", "implied_ret"]].round(6).to_dict("records")
pd.DataFrame(bars.log).to_csv(QA / "bar_skips_qa.csv", index=False)
write_json(QA / "qa_summary.json", res)
print(pd.Series(res).to_string())
