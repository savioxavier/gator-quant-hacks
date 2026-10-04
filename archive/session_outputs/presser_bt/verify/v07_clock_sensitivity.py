"""Clock sensitivity: (1) FOX-Business-implied (later) video zero on meetings where FBC was excluded,
(2) how often the convention / point clocks enter before the upper-bound clock (early-clock rows)."""
import json
import numpy as np
import pandas as pd
from vlib import *

ev = pd.read_csv(BT / "events/events.csv", dtype={"date": str})
ans = pd.read_parquet(BT / "text/answers.parquet")
ans["date"] = pd.to_datetime(ans.meeting, format="%Y%m%d").dt.strftime("%Y-%m-%d")
m1 = load_1m()
px = Px(m1)
pos = pd.read_csv(V / "v03_lex_h1primary_trades_ZT.csv", dtype={"date": str})
pos = pos[pos.clock == "upper"][["date", "pos", "ticks", "e_t"]]
bench = pd.read_csv(V / "v02_benchr_trades.csv", dtype={"date": str})
bench = bench[(bench.sym == "ZT") & (bench["var"] == "tau")]


def shift(r):
    if r.tv_fbc_excluded != 1:
        return 0.0
    if pd.notna(r.tv_gdelt_cnbc_off_s) and pd.notna(r.tv_gdelt_fbc_off_s):
        return r.tv_gdelt_fbc_off_s - r.tv_gdelt_cnbc_off_s
    if pd.notna(r.tv_archive_cnbc_off_s) and pd.notna(r.tv_archive_fbc_off_s):
        return r.tv_archive_fbc_off_s - r.tv_archive_cnbc_off_s
    return np.nan


ev["fbc_shift_s"] = ev.apply(shift, axis=1)
el = ev[(ev.drop_timing == 0) & (ev.scheduled == 1)].copy()
res = {"fbc_excluded_eligible": el.loc[el.tv_fbc_excluded == 1, ["date", "fbc_shift_s", "start_unc_s"]].to_dict("records")}


def tau(r, extra=0.0, unc=True):
    a = ans[(ans.date == r.date) & (ans.timing_source == "vtt")]
    x = np.nanmax([r.last_speech_end_s] + list(a.t_end_video_s + a.end_cue_dur))
    return ts(r.date, r.presser_sched_et) + pd.Timedelta(seconds=r.v0_minus_sched_tv_s + extra + x + (r.start_unc_s if unc else 0))


rows = []
for r in el.itertuples():
    t_u = tau(r)
    t_f = tau(r, extra=max(r.fbc_shift_s, 0) if np.isfinite(r.fbc_shift_s) else 0)
    t_c = pd.Timestamp(f"{r.date} {r.presser_end_conv_et}").tz_localize(NY)
    t_p = tau(r, unc=False)
    e_u = px.next_open(r.date, "ZT", t_u)
    e_f = px.next_open(r.date, "ZT", t_f)
    e_c = px.next_open(r.date, "ZT", t_c)
    e_p = px.next_open(r.date, "ZT", t_p)
    rows.append(dict(date=r.date, role=r.sample_role, fbc=r.tv_fbc_excluded, e_u=e_u[0], e_f=e_f[0], e_c=e_c[0], e_p=e_p[0],
                     px_u=e_u[1], px_f=e_f[1], conv_minus_upper_s=(t_c - t_u).total_seconds()))
D = pd.DataFrame(rows)
res["conv_entry_bar_earlier_than_upper"] = int((D.e_c < D.e_u).sum())
res["point_entry_bar_earlier_than_upper"] = int((D.e_p < D.e_u).sum())
res["conv_tau_before_upper_tau_n"] = int((D.conv_minus_upper_s < 0).sum())
res["eligible_n"] = len(D)
res["fbc_alt_entry_bar_changes"] = D.loc[D.e_f != D.e_u, ["date", "role", "e_u", "e_f"]].astype(str).to_dict("records")
# recompute lexicon H1-primary (ZT, confirmation) and BENCH-R ZT under the FBC-implied clock
cf = D[D.role == "confirmation_2023_2026_powell"].merge(pos, on="date")
alt = []
for r in cf.itertuples():
    x_t, x_p = px.close_before(r.date, "ZT", ts(r.date, "16:00:00"), lo=r.e_f)
    alt.append(r.pos * (x_p - r.px_f) / tick("ZT", r.date))
cf["ticks_fbc"] = alt
res["lex_h1_primary_ZT_conf_upper"] = summ(cf.ticks)
res["lex_h1_primary_ZT_conf_fbc_clock"] = summ(cf.ticks_fbc)
b = bench.merge(D[["date", "e_f", "e_u"]], on="date", how="left")
nb = []
for r in b.itertuples():
    if isinstance(r.e_f, pd.Timestamp) and r.e_f != r.e_u:
        x_t, x_p = px.next_open(r.date, "ZT", r.e_f)
        nb.append(r.pos * (x_p - r.e_p) / r.tk * r.upt)
    else:
        nb.append(r.gross_usd)
b["gross_fbc"] = nb
for era, g in b.groupby("era"):
    res[f"bench_ZT_{era}_gross_usd_upper"] = summ(g.gross_usd)
    res[f"bench_ZT_{era}_gross_usd_fbc_clock"] = summ(g.gross_fbc)
# 2019-05-01 fallback-clock exit sensitivity (distorted captions; drives the eligible-subset p = 0.010)
r = ev[ev.date == "2019-05-01"].iloc[0]
e_t, e_p = px.next_open("2019-05-01", "ZT", ts("2019-05-01", "14:20:00"))
sens = {}
for lab, t in [("fallback_end_est+unc+1", ts("2019-05-01", r.presser_end_est_et) + pd.Timedelta(seconds=r.start_unc_s + 1)),
               ("convention_end", ts("2019-05-01", r.presser_end_conv_et)), ("15:30", ts("2019-05-01", "15:30:00"))]:
    x_t, x_p = px.next_open("2019-05-01", "ZT", t)
    p0 = bench[bench.date == "2019-05-01"].pos.iloc[0]
    sens[lab] = dict(exit_bar=str(x_t), usd=float(p0 * (x_p - e_p) / tick("ZT", "2019-05-01") * 2000 * tick("ZT", "2019-05-01")))
res["2019-05-01_exit_sensitivity"] = sens
json.dump(res, open(V / "v07_clock_sensitivity.json", "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
