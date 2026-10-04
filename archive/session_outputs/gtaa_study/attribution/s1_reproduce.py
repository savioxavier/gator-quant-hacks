"""Step 1: reproduce S3 / BH5 daily net returns with forward2.returns(..., "FWD"), confirm the known Sharpe / max DD,
and check point-in-time execution explicitly.  Writes out/s1_*.{csv,json}."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lib as L

ohlc, rf = L.data()
known = json.loads((L.REPO / "forward" / "historical_context2.json").read_text())["strategies"]

rows, series = [], {}
for name in ("S3", "BH5"):
    net = L.F2.returns(name, "FWD").loc[:L.OOS_END]
    ex = net - rf.reindex(net.index)
    first = ex[ex.abs() > 1e-12].index[0]                  # same trimming rule as scripts/forward2_context.py
    net = net.loc[first:]
    series[name] = net
    for lab, lo, hi in (("in_sample", None, L.IS_END), ("out_of_sample", L.OOS_START, L.OOS_END)):
        st = L.stats(net.loc[lo:hi], rf)
        k = known[name][lab]
        rows.append({"strategy": name, "period": lab, **st,
                     "known_sharpe": k["sharpe"], "known_max_dd": k["max_drawdown"], "known_ann_return": k["ann_return"],
                     "abs_diff_sharpe": abs(st["sharpe"] - k["sharpe"]),
                     "abs_diff_mdd": abs(st["max_drawdown"] - k["max_drawdown"])})
repro = pd.DataFrame(rows)
repro.to_csv(L.OUT / "s1_reproduction.csv", index=False)
pd.DataFrame(series).to_csv(L.OUT / "s1_daily_net_S3_BH5.csv")
print(repro[["strategy", "period", "start", "end", "sharpe", "known_sharpe", "max_drawdown", "known_max_dd",
             "ann_return", "ann_vol"]].to_string(index=False))
assert repro["abs_diff_sharpe"].max() < 1e-9 and repro["abs_diff_mdd"].max() < 1e-9, "reproduction mismatch"

# ---------------------------------------------------------------- point-in-time checks
checks = {}
close = ohlc["close"][L.TICK]

# (a) replica of s3_decisions == frozen function (all timed / BH5)
w_s3 = L.F2.s3_decisions("FWD")
w_bh = L.F2.s3_decisions("FWD", buy_and_hold=True)
checks["replica_equals_frozen_S3"] = bool(np.allclose(L.sma_decisions(close, 10).values, w_s3.values))
checks["replica_equals_frozen_BH5"] = bool(np.allclose(L.sma_decisions(close, 10, timed=set()).values, w_bh.values))

# (b) truncation: decisions computed from data that stops at IS_END equal the FWD decisions on the same dates
w_is = L.F2.s3_decisions("IS")
common = w_is.index
checks["IS_loader_last_date"] = str(common[-1].date())
checks["truncated_equals_full_through_IS_END"] = bool(np.allclose(w_is.values, w_s3.loc[common].values))

# (c) future-perturbation test: scramble every close after a cut date; decisions up to the cut must not change
rng = np.random.default_rng(0)
me = L.month_ends(close.index)
bad = 0
cuts = rng.choice(me[12:-1], size=40, replace=False)
for t in cuts:
    c2 = close.copy()
    after = c2.index > t
    c2.loc[after] = c2.loc[after].values * rng.uniform(0.5, 1.5, size=c2.loc[after].shape)
    a = L.sma_decisions(close, 10).loc[:t]
    b = L.sma_decisions(c2, 10).loc[:t]
    bad += int(not np.allclose(a.values, b.values))
checks["future_perturbation_cuts"] = len(cuts)
checks["future_perturbation_violations"] = bad

# (d) execution lag: the held weight on session d+1 equals the decision at the close of d; on a month-end decision
# day the OLD weight is still held (the new one is filled at the next open).
net, gross, to, held, cost = L.E.simulate(w_s3, ohlc, rf, exec="next_open")
lagged = w_s3.reindex(held.index).ffill().fillna(0.0).shift(1).fillna(0.0)
checks["held_equals_decision_shifted_1"] = bool(np.allclose(held.values, lagged.values))
chg = w_s3.diff().abs().sum(axis=1) > 0
chg_days = chg[chg].index[1:]
same_day = [(held.loc[d] - w_s3.loc[d]).abs().sum() for d in chg_days]
checks["decision_change_days"] = int(len(chg_days))
checks["decision_change_days_where_new_weight_held_same_day"] = int(sum(s < 1e-12 for s in same_day))
# every decision change happens on a month-end close
checks["all_decision_changes_on_month_ends"] = bool(set(chg_days) <= set(me))

# (e) the per-ticker decomposition reproduces engine.simulate exactly
dec = L.decompose_next_open(w_s3, ohlc, rf)
checks["decomposition_max_abs_err_vs_simulate"] = float((dec["net"] - net).abs().max())
dec_b = L.decompose_next_open(w_bh, ohlc, rf)
net_b, *_ = L.E.simulate(w_bh, ohlc, rf, exec="next_open")
checks["decomposition_max_abs_err_vs_simulate_BH5"] = float((dec_b["net"] - net_b).abs().max())
# (f) forward2.returns equals simulate on the frozen decisions
checks["forward2_returns_equals_simulate"] = float((L.F2.returns("S3", "FWD") - net).abs().max())

# (g) first fill after a new entry earns open->close only (no overnight gap from the decision close)
entries = [(d, t) for d in chg_days for t in L.TICK if w_s3.shift(1).fillna(0).loc[d, t] == 0 and w_s3.loc[d, t] > 0]
errs = []
for d, t in entries:
    nxt = held.index[held.index.get_loc(d) + 1] if held.index.get_loc(d) + 1 < len(held.index) else None
    if nxt is None:
        continue
    on = (dec["w_old"].loc[nxt] * dec["r_co"].loc[nxt]).sum()
    errs.append(abs(dec["contrib"].loc[nxt, t] - 0.2 * (1 + on) * dec["r_oc"].loc[nxt, t]))
checks["entry_fill_day_open_to_close_only_max_err"] = float(max(errs)) if errs else None
checks["entries_checked"] = len(errs)

print(json.dumps(checks, indent=1))
for k in ("replica_equals_frozen_S3", "replica_equals_frozen_BH5", "truncated_equals_full_through_IS_END",
          "held_equals_decision_shifted_1", "all_decision_changes_on_month_ends"):
    assert checks[k], k
assert checks["future_perturbation_violations"] == 0
assert checks["decision_change_days_where_new_weight_held_same_day"] == 0
(L.OUT / "s1_point_in_time_checks.json").write_text(json.dumps(checks, indent=1))
