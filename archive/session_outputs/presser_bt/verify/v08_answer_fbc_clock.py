"""Answer-level lexicon rows (ZT, confirmation) under the FOX-Business-implied later clock on FBC-excluded meetings."""
import json
import numpy as np
import pandas as pd
from vlib import *
from v03_h1_lex import df as mydf  # own PIT fit (re-runs v03)

ev = pd.read_csv(BT / "events/events.csv", dtype={"date": str})
sh = json.load(open(V / "v07_clock_sensitivity.json"))["fbc_excluded_eligible"]
shift = {r["date"]: max(r["fbc_shift_s"], 0) for r in sh}
ans = pd.read_parquet(BT / "text/answers.parquet")
ans["date"] = pd.to_datetime(ans.meeting, format="%Y%m%d").dt.strftime("%Y-%m-%d")
mt = pd.read_parquet(BT / "text/meetings.parquet")
mt["date"] = pd.to_datetime(mt.meeting, format="%Y%m%d").dt.strftime("%Y-%m-%d")
m1 = load_1m()
px = Px(m1)
mydf["shat"] = mydf.lex_H1_raw - mydf.lex_H1_raw_resid
a = ans.merge(ev[["date", "drop_timing", "scheduled", "sample_role", "start_unc_s", "v0_minus_sched_tv_s", "presser_sched_et"]],
              on="date").merge(mt[["date", "lex_statement_raw"]], on="date").merge(mydf[["date", "shat"]], on="date")
a = a[(a.drop_timing == 0) & (a.scheduled == 1) & (a.timing_source == "vtt") & (a.n_words >= 40) & (a.n_sentences >= 1)
      & a.shat.notna() & (a.sample_role == "confirmation_2023_2026_powell")].copy()
a["pos"] = -np.sign((a.lex_score_raw - a.lex_statement_raw) - a.shat)
out = {}
for lab, use in [("upper", False), ("fbc_clock", True)]:
    a["tau_k"] = [ts(d, s) + pd.Timedelta(seconds=v0 + te + cd + u + (shift.get(d, 0) if use else 0)) for d, s, v0, te, cd, u in
                  zip(a.date, a.presser_sched_et, a.v0_minus_sched_tv_s, a.t_end_video_s, a.end_cue_dur, a.start_unc_s)]
    a["t0"] = [px.next_open(d, "ZT", t)[0] for d, t in zip(a.date, a.tau_k)]
    b = a[a.t0.notna()]
    for h in [1, 5, 15]:
        keep = []
        for _, g in b.groupby("date"):
            g = g.sort_values(["t0", "answer_no"]).drop_duplicates("t0", keep="last")
            last = None
            for i, r in g.iterrows():
                if last is None or r.t0 >= last + pd.Timedelta(minutes=h):
                    keep.append(i)
                    last = r.t0
        s = b.loc[keep]
        s = s[s.pos != 0]
        y, gg = [], []
        for r in s.itertuples():
            e_t, e_p = px.next_open(r.date, "ZT", r.t0)
            x_t, x_p = px.close_before(r.date, "ZT", r.t0 + pd.Timedelta(minutes=h), lo=e_t)
            if x_t is not None:
                y.append(r.pos * (x_p - e_p) / tick("ZT", r.date))
                gg.append(r.date)
        out[f"{lab}_h{h}"] = cluster_summ(np.array(y), np.array(gg))
json.dump(out, open(V / "v08_answer_fbc_clock.json", "w"), indent=1)
print(json.dumps(out, indent=1))
