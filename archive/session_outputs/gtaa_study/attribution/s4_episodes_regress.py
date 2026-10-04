"""Steps 4-5: stress episodes (S3 vs BH5 drawdowns, when the filter exited / re-entered) and regressions of S3 excess
returns on BH5 and SPY excess returns with Newey-West t, up/down capture, timing regressions.  Writes out/s4_*."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lib as L

ohlc, rf = L.data()
close = ohlc["close"][L.TICK]
cal = close.index
d = pd.read_csv(L.OUT / "s1_daily_net_S3_BH5.csv", index_col=0, parse_dates=True)
s3, bh = d["S3"].dropna(), d["BH5"].dropna()
spy = close["SPY"].pct_change(fill_method=None).reindex(s3.index)
sw = pd.read_csv(L.OUT / "s2_switches.csv", parse_dates=["decision_date", "fill_date"])
w_s3 = L.F2.s3_decisions("FWD")
held = w_s3.shift(1).fillna(0.0)

# windows fixed from the event list in the brief (peak of the stress to the end of the rebound); the 2026 ones from
# the 2026 drawdowns of the five ETFs (largest: SPY/EFA/VNQ Jan-Mar, DBC May-Jun, IEF/VNQ Jul-Oct)
EPISODES = [
    ("2008-09 GFC", "2007-10-01", "2009-12-31"),
    ("2011 euro crisis / US downgrade", "2011-04-01", "2011-12-30"),
    ("2015-16 China deval / oil", "2015-05-01", "2016-04-29"),
    ("2018 Q4 selloff", "2018-09-20", "2019-03-29"),
    ("Feb-Mar 2020 COVID", "2020-02-19", "2020-08-31"),
    ("2022 rate shock", "2022-01-03", "2022-12-30"),
    ("Apr 2025 tariff shock", "2025-02-19", "2025-06-30"),
    ("Mar 2026 equity/REIT selloff", "2026-01-27", "2026-04-30"),
    ("May-Jun 2026 commodity drop", "2026-05-12", "2026-07-31"),
    ("Jul-Sep 2026 bond+REIT selloff", "2026-07-28", "2026-10-02"),
]


def window_stats(r: pd.Series) -> dict:
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax().clip(lower=1.0) - 1          # drawdown from the window start or any later peak
    return {"ret": float(eq.iloc[-1] - 1), "mdd": float(dd.min()), "trough": str(dd.idxmin().date())}


ep_rows = []
for name, lo, hi in EPISODES:
    a, b, c = window_stats(s3.loc[lo:hi]), window_stats(bh.loc[lo:hi]), window_stats(spy.loc[lo:hi])
    first = s3.loc[lo:hi].index[0]
    state = {t: ("in" if held.loc[first, t] > 0 else "out") for t in L.TICK}
    ev = sw[(sw.fill_date >= pd.Timestamp(lo) - pd.Timedelta(days=62)) & (sw.fill_date <= pd.Timestamp(hi))]
    ev_txt = "; ".join(f"{r.ticker} {r.type} {r.fill_date.date()}" for r in ev.sort_values("fill_date").itertuples())
    etf_ret = {f"ret_{t}": float(close[t].loc[lo:hi].iloc[-1] / close[t].loc[:pd.Timestamp(lo) - pd.Timedelta(days=1)].iloc[-1] - 1) for t in L.TICK}
    ep_rows.append({"episode": name, "start": lo, "end": hi,
                    "S3_ret": a["ret"], "BH5_ret": b["ret"], "SPY_ret": c["ret"],
                    "S3_mdd": a["mdd"], "BH5_mdd": b["mdd"], "SPY_mdd": c["mdd"],
                    "S3_trough": a["trough"], "BH5_trough": b["trough"],
                    "S3_minus_BH5_ret": a["ret"] - b["ret"], "S3_minus_BH5_mdd": a["mdd"] - b["mdd"],
                    "S3_avg_invested": float(held.loc[lo:hi].sum(axis=1).mean()),
                    "held_at_start": " ".join(f"{t}:{s}" for t, s in state.items()),
                    "filter_events": ev_txt, **etf_ret})
ep = pd.DataFrame(ep_rows)
ep.to_csv(L.OUT / "s4_episodes.csv", index=False)


# largest BH5 drawdowns over the whole history (non-overlapping peak-to-recovery), for anything the list missed
def top_drawdowns(r: pd.Series, k: int = 8) -> list[dict]:
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1
    out, used = [], pd.Series(False, index=dd.index)
    for _ in range(k):
        x = dd[~used]
        if x.min() >= -0.03:
            break
        t = x.idxmin()
        peak = eq.loc[:t].idxmax()
        rec = dd.loc[t:]
        rec = rec[rec >= 0].index[0] if (rec >= 0).any() else dd.index[-1]
        used.loc[peak:rec] = True
        out.append({"peak": peak, "trough": t, "recovery": rec, "dd": float(dd.loc[t])})
    return out


td_rows = []
for lab, ser, other in (("BH5", bh, s3), ("S3", s3, bh)):
    for x in top_drawdowns(ser):
        o = (1 + other.loc[x["peak"]:x["trough"]]).prod() - 1
        s_ = (1 + spy.loc[x["peak"]:x["trough"]]).prod() - 1
        td_rows.append({"ranked_by": lab, "peak": x["peak"].date(), "trough": x["trough"].date(),
                        "recovery": x["recovery"].date(), "dd": x["dd"],
                        "other_strategy_ret_peak_to_trough": float(o), "SPY_ret_peak_to_trough": float(s_)})
pd.DataFrame(td_rows).to_csv(L.OUT / "s4_top_drawdowns.csv", index=False)

# ------------------------------------------------------------------ regressions
rfx = rf.reindex(s3.index)
ex = pd.DataFrame({"S3": s3 - rfx, "BH5": bh - rfx, "SPY": spy - rfx}).dropna()
mret = pd.DataFrame({k: L.monthly(v) for k, v in {"S3": s3, "BH5": bh, "SPY": spy.fillna(0.0)}.items()})
mrf = L.monthly(rfx)
mex = mret.sub(mrf, axis=0)
PER = {"IS": ("2005-11-01", L.IS_END), "OOS": (L.OOS_START, L.OOS_END)}
# monthly: IS months Nov 2005..Sep 2024 (Oct 2024 straddles the split and is dropped); OOS Nov 2024..Sep 2026
MPER = {"IS": ("2005-11-30", "2024-09-30"), "OOS": ("2024-11-30", "2026-09-30")}

reg_rows = []
for pname, (lo, hi) in PER.items():
    for bench in ("BH5", "SPY"):
        y, X = ex.loc[lo:hi, "S3"], ex.loc[lo:hi, [bench]]
        r, fit = L.ols_nw(y, X)
        reg_rows.append({"freq": "daily", "period": pname, "bench": bench, "n": r["n"], "nw_lags": r["nw_lags"],
                         "alpha_ann": r["const_coef"] * 252, "alpha_t_nw": r["const_t"],
                         "beta": r[f"{bench}_coef"], "beta_t_nw": r[f"{bench}_t"], "r2": r["r2"]})
    mlo, mhi = MPER[pname]
    for bench in ("BH5", "SPY"):
        y, X = mex.loc[mlo:mhi, "S3"], mex.loc[mlo:mhi, [bench]]
        r, fit = L.ols_nw(y, X, lags=3)
        reg_rows.append({"freq": "monthly", "period": pname, "bench": bench, "n": r["n"], "nw_lags": 3,
                         "alpha_ann": r["const_coef"] * 12, "alpha_t_nw": r["const_t"],
                         "beta": r[f"{bench}_coef"], "beta_t_nw": r[f"{bench}_t"], "r2": r["r2"]})
        # timing regressions on monthly data: up/down beta and Treynor-Mazuy
        xb = mex.loc[mlo:mhi, bench]
        X2 = pd.DataFrame({"up": xb.clip(lower=0), "down": xb.clip(upper=0)})
        r2_, fit2 = L.ols_nw(y, X2, lags=3)
        diff_t = float(fit2.t_test("up - down = 0").tvalue.squeeze())
        X3 = pd.DataFrame({"x": xb, "x2": xb ** 2})
        r3_, _ = L.ols_nw(y, X3, lags=3)
        reg_rows[-1].update({"beta_up": r2_["up_coef"], "beta_down": r2_["down_coef"],
                             "beta_up_minus_down": r2_["up_coef"] - r2_["down_coef"], "up_minus_down_t_nw": diff_t,
                             "alpha_updown_ann": r2_["const_coef"] * 12, "alpha_updown_t": r2_["const_t"],
                             "TM_gamma": r3_["x2_coef"], "TM_gamma_t_nw": r3_["x2_t"],
                             "TM_alpha_ann": r3_["const_coef"] * 12, "TM_alpha_t": r3_["const_t"]})
reg = pd.DataFrame(reg_rows)
reg.to_csv(L.OUT / "s4_regressions.csv", index=False)

cap_rows = []
for pname, (mlo, mhi) in MPER.items():
    for bench in ("BH5", "SPY"):
        c = L.capture(mret.loc[mlo:mhi, "S3"], mret.loc[mlo:mhi, bench])
        cap_rows.append({"period": pname, "bench": bench, **c})
    # daily capture as a cross-check (2-year window has only 23 months)
    lo, hi = PER[pname]
    for bench in ("BH5", "SPY"):
        c = L.capture(s3.loc[lo:hi], (bh if bench == "BH5" else spy).loc[lo:hi])
        cap_rows.append({"period": pname, "bench": bench + "_daily", **c})
cap = pd.DataFrame(cap_rows)
cap.to_csv(L.OUT / "s4_capture.csv", index=False)

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_colwidth", 400)
print(ep[["episode", "S3_ret", "BH5_ret", "SPY_ret", "S3_mdd", "BH5_mdd", "SPY_mdd", "S3_avg_invested"]].round(3).to_string(index=False))
for r in ep.itertuples():
    print(r.episode, "|", r.held_at_start, "|", r.filter_events)
print(pd.DataFrame(td_rows).round(3).to_string(index=False))
print(reg.round(3).to_string(index=False))
print(cap.round(3).to_string(index=False))
