"""Step 2 (addendum 9.2): signals, point-in-time fits, positions and answer selection, hashed before any exit price
is joined. The only prices used here are the 13:30-14:20 ZT/ES/ZF/ZN bars that define R_m (known at 14:20) and
bar start times (for answer entry bars and selection)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from pit import pit_fit
from lib import (OUT, SYMS, TZ, Bars, check_addendum, load_answers, load_events, load_meetings, sha256, tau_answer,
                 tau_end, write_json, BT)

check_addendum()
P = OUT / "positions"
P.mkdir(exist_ok=True, parents=True)
ev = load_events()
ans = load_answers()
mt = load_meetings()
bars = Bars()


# ---------------------------------------------------------------- meeting frame
m = ev[["date", "meeting", "chair", "scheduled", "sep_meeting", "sample_role", "era_bench", "drop_timing",
        "start_unc_s", "databento_degraded_day", "market_window_covers_event", "v0_minus_sched_tv_s",
        "usmpd_stmt_UST2Y", "usmpd_pc_UST2Y"]].copy()
m = m.merge(mt[["meeting", "H1", "statement_score", "qa_mean_score", "q_mean_score", "qa_mean_score_ge40w",
                "qa_pooled_score", "lex_H1", "lex_H1_raw", "lex_statement_raw", "lex_statement",
                "drop_P_timing", "n_answers"]], on="meeting", how="left")
m["sens1_drop"] = m.drop_P_timing.astype(bool) & (m.drop_timing == 0)
m["sens2_drop"] = m.databento_degraded_day == 1
m["sens3_keep"] = m.start_unc_s <= 10

taus = []
for _, r in ev.iterrows():
    am = ans[ans.meeting == r.meeting]
    tu, src = tau_end(r, am, "upper")
    tp, _ = tau_end(r, am, "point")
    tc, _ = tau_end(r, am, "conv")
    taus.append(dict(meeting=r.meeting, tau_end_upper=tu, tau_end_point=tp, tau_end_conv=tc, tau_src=src))
m = m.merge(pd.DataFrame(taus), on="meeting")

# R_m per symbol (3.2): close at 13:50 (last bar <= 13:49, >= 13:30) to close at 14:20 (last bar <= 14:19, >= 13:50)
for s in SYMS:
    R = []
    for _, r in m.iterrows():
        if r.scheduled != 1 or r.market_window_covers_event != 1:
            R.append(np.nan)
            continue
        T = lambda x: pd.Timestamp(f"{r.date} {x}", tz=TZ)
        b0, c0 = bars.close_at(r.date, s, T("13:50:00"), lo=T("13:30:00"), tag="R_1350")
        b1, c1 = bars.close_at(r.date, s, T("14:20:00"), lo=T("13:50:00"), tag="R_1420")
        R.append(c1 / c0 - 1 if (b0 is not None and b1 is not None) else np.nan)
    m[f"R_{s}"] = R

# BENCH-R positions (5): own-symbol sign of R; 0 = no trade
for s in SYMS:
    m[f"bench_pos_{s}"] = np.sign(m[f"R_{s}"])
m["bench_pos_usmpd"] = -np.sign(m.usmpd_stmt_UST2Y)  # long ZT-equivalent when yields fell (continuation)
m = m.sort_values("date").reset_index(drop=True)


m["q_H1Q"] = m.q_mean_score - m.statement_score
SIGNALS = {"H1": dict(sig="H1"),                       # stance (D1 scorer when filled)
           "H1Q": dict(sig="H1", extra=["q_H1Q"]),     # H1-Q robustness
           "lexH1raw": dict(sig="lex_H1_raw"),          # lexicon control, ungated (NOT the frozen spec)
           "lexH1": dict(sig="lex_H1")}                 # lexicon control, frozen MIN_HD=5
fits = [pit_fit(m, prefix=k, **v) for k, v in SIGNALS.items()]
m = pd.concat([m] + fits, axis=1)

status = {k: dict(n_signal=int(np.isfinite(m[v["sig"]].astype(float)).sum()),
                  n_positions=int(np.isfinite(m[f"{k}__pos"]).sum()),
                  n_pos_conf_eligible=int((np.isfinite(m[f"{k}__pos"]) & (m.drop_timing == 0) &
                                           (m.sample_role == "confirmation_2023_2026_powell")).sum()))
          for k, v in SIGNALS.items()}
status["first_position_date_lexH1raw"] = m.loc[np.isfinite(m["lexH1raw__pos"]), "date"].min()
print(json.dumps(status, indent=1))

# ---------------------------------------------------------------- answer-level signals (4.1) and entry bars
a = ans.merge(m[["meeting", "date", "drop_timing", "scheduled", "sample_role", "start_unc_s", "v0_minus_sched_tv_s",
                 "statement_score", "lex_statement_raw", "H1__shat", "lexH1raw__shat", "lexH1__shat",
                 "lex_statement"]], on="meeting", how="left", suffixes=("", "_m"))
evi = ev.set_index("meeting")
tk, t0 = [], []
for r in a.itertuples():
    if r.timing_source == "vtt" and pd.notna(r.v0_minus_sched_tv_s):
        tu = tau_answer(evi.loc[r.meeting], r)
        bt, _ = bars.next_open(r.date, "ZT", tu, tag="answer_entry")
        tk.append(tu)
        t0.append(bt)
    else:
        tk.append(pd.NaT)
        t0.append(None)
a["tau_k_upper"] = tk
a["t0"] = t0
a["eligible_base"] = ((a.drop_timing == 0) & (a.scheduled == 1) & (a.timing_source == "vtt") & (a.n_words >= 40) &
                      (a.n_sentences >= 1) & a.t0.notna())
a["H1__a"] = a.score - a.statement_score
a["H1__resid"] = a["H1__a"] - a["H1__shat"]
a["lexH1raw__a"] = a.lex_score_raw - a.lex_statement_raw
a["lexH1raw__resid"] = a["lexH1raw__a"] - a["lexH1raw__shat"]
a["lexH1__a"] = a.lex_score - a.lex_statement
a["lexH1__resid"] = a["lexH1__a"] - a["lexH1__shat"]
for k in ["H1", "lexH1raw", "lexH1"]:
    a[f"{k}__pos"] = -np.sign(a[f"{k}__resid"])
    a[f"{k}__eligible"] = a.eligible_base & np.isfinite(a[f"{k}__resid"])


def select(df: pd.DataFrame, h: int) -> pd.DataFrame:
    """A-22: latest answer per entry bar, then earliest-first non-overlapping per meeting."""
    keep = []
    for mtg, g in df.groupby("meeting"):
        g = g.sort_values(["t0", "answer_no"]).groupby("t0").tail(1).sort_values("t0")
        last = None
        for r in g.itertuples():
            if last is None or r.t0 >= last + pd.Timedelta(minutes=h):
                keep.append(r.Index)
                last = r.t0
    return df.loc[keep]


sel = {}
for k in ["H1", "lexH1raw", "lexH1"]:
    el = a[a[f"{k}__eligible"]]
    for h in [1, 5, 15]:
        s_ = select(el, h)
        sel[(k, h)] = s_
        s_[["answer_id", "meeting", "date", "answer_no", "sample_role", "start_unc_s", "tau_k_upper", "t0",
            f"{k}__a", f"{k}__shat", f"{k}__resid", f"{k}__pos"]].to_csv(P / f"answer_sel_{k}_h{h}.csv", index=False)
    status[f"answers_{k}"] = {"eligible": int(len(el)), **{f"h{h}": int(len(sel[(k, h)])) for h in [1, 5, 15]}}

m.to_csv(P / "meetings_positions.csv", index=False)
a.drop(columns=[c for c in a.columns if c.startswith("q_lex")]).to_csv(P / "answers_positions.csv", index=False)
pd.DataFrame(bars.log).to_csv(P / "bar_log_positions.csv", index=False)
write_json(P / "positions_status.json", status)
files = sorted(P.glob("*.csv")) + [P / "positions_status.json"]
(P / "manifest_sha256.txt").write_text("".join(f"{sha256(f)}  {f.name}\n" for f in files))
print(json.dumps(status, indent=1, default=str))
