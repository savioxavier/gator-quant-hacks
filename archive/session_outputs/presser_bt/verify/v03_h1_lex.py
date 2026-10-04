"""Independent H1-primary (lexicon control lex_H1_raw) on the confirmation sample, plus leak checks."""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from vlib import *

ev = pd.read_csv(BT / "events/events.csv", dtype={"date": str})
mt = pd.read_parquet(BT / "text/meetings.parquet")
mt["date"] = pd.to_datetime(mt.meeting, format="%Y%m%d").dt.strftime("%Y-%m-%d")
b02 = pd.read_csv(V / "v02_benchr_trades.csv", dtype={"date": str})
tau = pd.read_csv(BT / "backtest/positions/meetings_positions.csv", dtype={"date": str})[["date"]]
# own tau (recomputed in v02 logic, re-derived here)
ans = pd.read_parquet(BT / "text/answers.parquet")
ans["date"] = pd.to_datetime(ans.meeting, format="%Y%m%d").dt.strftime("%Y-%m-%d")
m1 = load_1m()
px = Px(m1)
qc, _ = clean_bbo(load_bbo())

df = ev.merge(mt[["date", "lex_H1_raw", "lex_H1", "lex_statement_raw", "lex_qa_pooled_raw", "H1", "statement_score"]],
              on="date", how="left")


def Rm(day):
    b0, c0 = px.close_before(day, "ZT", ts(day, "13:50:00"), lo=ts(day, "13:30:00"))
    b1, c1 = px.close_before(day, "ZT", ts(day, "14:20:00"), lo=ts(day, "13:50:00"))
    return (c1 / c0 - 1) if (b0 is not None and b1 is not None) else np.nan


df["R"] = [Rm(d) if (s == 1 and w == 1) else np.nan for d, s, w in zip(df.date, df.scheduled, df.market_window_covers_event)]


def tau_u(r, clock="upper"):
    sched = ts(r.date, r.presser_sched_et)
    a = ans[(ans.date == r.date) & (ans.timing_source == "vtt")]
    x = np.nanmax([r.last_speech_end_s] + list(a.t_end_video_s + a.end_cue_dur))
    t = sched + pd.Timedelta(seconds=r.v0_minus_sched_tv_s + x)
    return t + pd.Timedelta(seconds=r.start_unc_s if clock == "upper" else 0)


PREV = {"Powell": "Yellen", "Warsh": "Powell"}


def pit(df, sig):
    df = df.sort_values("date").reset_index(drop=True)
    ok = (df.scheduled == 1) & df[sig].notna() & df.R.notna()
    out = []
    for i, r in df.iterrows():
        if not ok[i]:
            out.append(np.nan)
            continue
        F = df[ok & (df.date < r.date)]
        if len(F) < 8:
            out.append(np.nan)
            continue
        X = pd.get_dummies(F.chair).astype(float)
        X["R"] = F.R.values
        fit = sm.OLS(F[sig].values, X).fit()
        a = fit.params.drop("R")
        n_c = int((F.chair == r.chair).sum())
        p = PREV.get(r.chair)
        if n_c == 0:
            at = a[p]
        elif p is not None and p in a:
            at = (n_c * a[r.chair] + 4 * a[p]) / (n_c + 4)
        else:
            at = a[r.chair]
        out.append(r[sig] - (at + fit.params["R"] * r.R))
    df[f"{sig}_resid"] = out
    return df


df = pit(df, "lex_H1_raw")
df["pos"] = -np.sign(df.lex_H1_raw_resid)
bt = pd.read_csv(BT / "backtest/positions/meetings_positions.csv", dtype={"date": str})
j = df.merge(bt[["date", "lexH1raw__resid", "lexH1raw__pos"]], on="date")
res = {"pit_resid_max_abs_diff_vs_backtest": float((j.lex_H1_raw_resid - j.lexH1raw__resid).abs().max()),
       "pit_first_position_date": df.loc[df.pos.notna(), "date"].min(),
       "pos_mismatch_n": int(((j.pos != j.lexH1raw__pos) & j.pos.notna()).sum())}

conf = df[(df.sample_role == "confirmation_2023_2026_powell") & (df.drop_timing == 0) & df.pos.notna() & (df.pos != 0)]
rows = []
for r in conf.itertuples():
    for clock in ["upper", "point", "upper+30"]:
        tu = tau_u(r, "upper" if clock != "point" else "point")
        if clock == "upper+30":
            tu = tu + pd.Timedelta(seconds=30)
        for s in ["ZT", "ZN", "ES", "ZF"]:
            e_t, e_p = px.next_open(r.date, s, tu)
            x_t, x_p = px.close_before(r.date, s, ts(r.date, "16:00:00"), lo=e_t)
            if e_t is None or x_t is None or e_t >= ts(r.date, "15:59:00"):
                continue
            tk = tick(s, r.date)
            rows.append(dict(date=r.date, clock=clock, sym=s, pos=r.pos, tau=tu, e_t=e_t, e_p=e_p, x_t=x_t, x_p=x_p, tk=tk,
                             upt=tk * PT_USD[s], ticks=r.pos * (x_p - e_p) / tk, unc=r.start_unc_s,
                             degraded=r.databento_degraded_day))
tr = pd.DataFrame(rows)
tr["usd"] = tr.ticks * tr.upt
z = tr[(tr.sym == "ZT")]
for leg, col, add in [("e", "e_t", 0), ("x", "x_t", 60)]:
    q = quote_asof(qc, pd.DataFrame({"sym": z.sym.values, "t": pd.Series(list(z[col] + pd.Timedelta(seconds=add)))}))
    z = z.assign(**{f"{leg}_hs": ((q.ask - q.bid) / 2).values, f"{leg}_bid": q.bid.values, f"{leg}_ask": q.ask.values,
                    f"{leg}_stale": q.stale_s.values})
z["CM_ticks"] = z.ticks - (z.e_hs + z.x_hs) / z.tk
z["C2_ticks"] = z.ticks - 4
z["C4_ticks"] = z.ticks - 8
z["CQ_ticks"] = np.where(z.pos > 0, z.x_bid - z.e_ask, z.e_bid - z.x_ask) / z.tk
z.to_csv(V / "v03_lex_h1primary_trades_ZT.csv", index=False)
prim = z[z.clock == "upper"].sort_values("date")
out = {"ZT_primary_ticks": summ(prim.ticks), "ZT_primary_usd": summ(prim.usd),
       "ZT_primary_C2_ticks": summ(prim.C2_ticks), "ZT_primary_C4_ticks": summ(prim.C4_ticks),
       "ZT_primary_CM_ticks": summ(prim.CM_ticks), "ZT_primary_CQ_ticks": summ(prim.CQ_ticks),
       "ZT_point_clock_ticks": summ(z[z.clock == "point"].ticks),
       "ZT_exec30_ticks": summ(z[z.clock == "upper+30"].ticks),
       "ZT_primary_drop_degraded": summ(prim[prim.degraded == 0].ticks),
       "ZT_primary_drop_text_flags": summ(prim[~prim.date.isin(["2024-01-31", "2024-09-18"])].ticks)}
for s in ["ZN", "ES", "ZF"]:
    out[f"{s}_primary_usd"] = summ(tr[(tr.sym == s) & (tr.clock == "upper")].usd)
g3 = out["ZT_primary_ticks"]
out["G3_rule_applied_to_control"] = ("GO" if (g3["n"] >= 15 and g3["mean"] > 0 and g3["p_one_gt"] <= 0.05) else "NO-GO")
btt = pd.read_csv(BT / "backtest/results/h1primary_trades.csv", dtype={"date": str})
btt = btt[(btt.signal == "lexH1raw") & (btt["sample"] == "confirmation") & (btt.sym == "ZT") & (btt.clock == "primary") &
          (btt.exit == "exit_1600")]
jj = prim.merge(btt, on="date", suffixes=("", "_bt"))
res["trade_count_mine_vs_bt"] = [len(prim), len(btt), len(jj)]
res["ticks_max_abs_diff_vs_bt"] = float((jj.ticks - jj.C0_ticks).abs().max())
res["entry_bar_minus_tau_s"] = (prim.e_t - prim.tau).dt.total_seconds().describe().round(1).to_dict()
res["entry_bar_times"] = prim.e_t.dt.strftime("%H:%M").tolist()
# leakage: is the statement released before 14:00? check statements.parquet release times and URL dates
st = pd.read_parquet(BT / "text/statements.parquet")
st["date"] = pd.to_datetime(st.meeting, format="%Y%m%d").dt.strftime("%Y-%m-%d")
st["url_date"] = st.url.str.extract(r"(\d{8})")[0]
res["statement_release_times"] = st.release_time.value_counts().to_dict()
res["statement_url_date_mismatch"] = st.loc[st.url_date != st.meeting, ["meeting", "url"]].to_dict("records")
json.dump(dict(checks=res, results=out), open(V / "v03_h1_lex.json", "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
for k, v in out.items():
    print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()} if isinstance(v, dict) else v)
