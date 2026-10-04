"""Independent H1-answer (lexicon) 1m rows and the 1s latency sweep on bbo-1s (addendum 4)."""
import json
import math
import numpy as np
import pandas as pd
from vlib import *

ev = pd.read_csv(BT / "events/events.csv", dtype={"date": str})
ans = pd.read_parquet(BT / "text/answers.parquet")
ans["date"] = pd.to_datetime(ans.meeting, format="%Y%m%d").dt.strftime("%Y-%m-%d")
mt = pd.read_parquet(BT / "text/meetings.parquet")
mt["date"] = pd.to_datetime(mt.meeting, format="%Y%m%d").dt.strftime("%Y-%m-%d")
lex = pd.read_csv(V / "v03_lex_h1primary_trades_ZT.csv", dtype={"date": str})  # not used for signals
# meeting fitted value shat = s - resid from my own PIT fit (recomputed in v03); recompute here quickly
import importlib.util
spec = importlib.util.spec_from_file_location("v03", V / "v03_h1_lex.py")
m1 = load_1m()
px = Px(m1)
qc, _ = clean_bbo(load_bbo())
bt_m = pd.read_csv(BT / "backtest/positions/meetings_positions.csv", dtype={"date": str})
# I verified in v03 that my PIT residuals equal the backtest's to 5e-13, so shat is taken as s - resid from my own fit:
from v03_h1_lex import df as mydf  # noqa: E402  (re-runs v03; acceptable)
mydf["shat"] = mydf.lex_H1_raw - mydf.lex_H1_raw_resid
a = ans.merge(ev[["date", "drop_timing", "scheduled", "sample_role", "start_unc_s", "v0_minus_sched_tv_s", "presser_sched_et"]],
              on="date").merge(mt[["date", "lex_statement_raw"]], on="date").merge(mydf[["date", "shat"]], on="date")
a = a[(a.drop_timing == 0) & (a.scheduled == 1) & (a.timing_source == "vtt") & (a.n_words >= 40) & (a.n_sentences >= 1)
      & a.shat.notna() & a.lex_score_raw.notna()].copy()
a["tau_k"] = [ts(d, s) + pd.Timedelta(seconds=v0 + te + cd + u) for d, s, v0, te, cd, u in
              zip(a.date, a.presser_sched_et, a.v0_minus_sched_tv_s, a.t_end_video_s, a.end_cue_dur, a.start_unc_s)]
a["t0"] = [px.next_open(d, "ZT", t)[0] for d, t in zip(a.date, a.tau_k)]
a = a[a.t0.notna()]
a["resid"] = (a.lex_score_raw - a.lex_statement_raw) - a.shat
a["pos"] = -np.sign(a.resid)


def select(df, h):
    keep = []
    for _, g in df.groupby("date"):
        g = g.sort_values(["t0", "answer_no"]).drop_duplicates("t0", keep="last")
        last = None
        for i, r in g.iterrows():
            if last is None or r.t0 >= last + pd.Timedelta(minutes=h):
                keep.append(i)
                last = r.t0
    return df.loc[keep]


res, out = {}, {}
conf = a[a.sample_role == "confirmation_2023_2026_powell"]
res["eligible_confirmation_answers"] = len(conf)
sel = {h: select(conf, h) for h in [1, 5, 15]}
res["selected_counts"] = {h: len(s) for h, s in sel.items()}
# compare selection to the backtest's
for h in [1, 5, 15]:
    b = pd.read_csv(BT / f"backtest/positions/answer_sel_lexH1raw_h{h}.csv", dtype={"date": str})
    b = b[b.sample_role == "confirmation_2023_2026_powell"]
    res[f"sel_h{h}_same_ids"] = set(b.answer_id) == set(sel[h].answer_id)
    jb = sel[h].merge(b[["answer_id", "lexH1raw__pos"]], on="answer_id")
    res[f"sel_h{h}_pos_mismatch"] = int((jb.pos != jb.lexH1raw__pos).sum())

# 1m rows
for h, s in sel.items():
    s = s[s.pos != 0]
    rows = []
    for r in s.itertuples():
        e_t, e_p = px.next_open(r.date, "ZT", r.t0)
        x_t, x_p = px.close_before(r.date, "ZT", r.t0 + pd.Timedelta(minutes=h), lo=e_t)
        if x_t is None:
            continue
        rows.append(dict(date=r.date, aid=r.answer_id, ticks=r.pos * (x_p - e_p) / tick("ZT", r.date), unc=r.start_unc_s,
                         x_t=x_t, e_t=e_t))
    t1 = pd.DataFrame(rows)
    out[f"1m_h{h}_gross_ticks"] = cluster_summ(t1.ticks, t1.date)
    out[f"1m_h{h}_exit_bar_is_t0+h-1"] = float(((t1.x_t - t1.e_t) == pd.Timedelta(minutes=h - 1)).mean())

# 1s sweep
sw = []
for h, hs in [(1, 60), (5, 300)]:
    s = sel[h][sel[h].pos != 0]
    for L in [0, 5, 15, 30]:
        te = pd.Series([(t + pd.Timedelta(seconds=L)).ceil("s") for t in s.tau_k])
        for sym in ["ZT", "ZN", "ES"]:
            q0 = quote_asof(qc, pd.DataFrame({"sym": sym, "t": te}))
            q1 = quote_asof(qc, pd.DataFrame({"sym": sym, "t": te + pd.Timedelta(seconds=hs)}))
            tk = np.array([tick(sym, d) for d in s.date])
            pos = s.pos.values
            mid = pos * (((q1.bid + q1.ask) / 2).values - ((q0.bid + q0.ask) / 2).values) / tk
            qf = np.where(pos > 0, q1.bid.values - q0.ask.values, q0.bid.values - q1.ask.values) / tk
            d = pd.DataFrame(dict(date=s.date.values, mid=mid, qf=qf, unc=s.start_unc_s.values, st0=q0.stale_s.values,
                                  st1=q1.stale_s.values)).dropna(subset=["mid"])
            for split, dd in [("all", d), ("unc_le10", d[d.unc <= 10]), ("unc_gt10", d[d.unc > 10])]:
                if dd.date.nunique() < 3:
                    continue
                sw.append(dict(h=h, L=L, sym=sym, split=split, mid=cluster_summ(dd.mid, dd.date),
                               quote=cluster_summ(dd.qf, dd.date), stale_gt60=int(((dd.st0 > 60) | (dd.st1 > 60)).sum()),
                               median_rt_cost_ticks=float(np.median(dd.mid - dd.qf))))
out["sweep"] = sw
# compare with backtest sweep summary (ZT, all, mid)
bs = pd.read_csv(BT / "backtest/results/h1answer_1s_sweep_summary.csv")
bs = bs[(bs.signal == "lexH1raw") & (bs["sample"] == "confirmation") & (bs.split == "all")]
cmp = []
for r in sw:
    if r["split"] != "all":
        continue
    for cost, key in [("mid", "mid"), ("quote", "quote")]:
        b = bs[(bs.h == r["h"]) & (bs.L == r["L"]) & (bs.sym == r["sym"]) & (bs.cost == cost)]
        if len(b):
            cmp.append(dict(h=r["h"], L=r["L"], sym=r["sym"], cost=cost, mine=round(r[key]["mean"], 4),
                            bt=round(float(b["mean"].iloc[0]), 4), n_mine=r[key]["n"], n_bt=int(b.n_answers.iloc[0]),
                            p_mine=round(r[key]["p_two"], 3), p_bt=round(float(b.wcb_p_two.iloc[0]), 3)))
res["sweep_vs_backtest"] = cmp
json.dump(dict(checks=res, results=out), open(V / "v04_answer_sweep.json", "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
for k, v in out.items():
    if k != "sweep":
        print(k, v)
for r in sw:
    if r["split"] == "all":
        print(r["h"], r["L"], r["sym"], "mid", {k: round(v, 3) if isinstance(v, float) else v for k, v in r["mid"].items()},
              "quote", round(r["quote"]["mean"], 3), "rt_cost_med", r["median_rt_cost_ticks"], "stale>60", r["stale_gt60"])
