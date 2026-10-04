"""Steps 2-3: per-ETF attribution of S3 and BH5 in each period, timed vs untimed sleeves, every out-of-market spell,
whipsaws.  Writes out/s2_*.csv and out/s3_*.csv."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lib as L

ohlc, rf = L.data()
close = ohlc["close"][L.TICK]
cal = close.index
w = {"S3": L.F2.s3_decisions("FWD"), "BH5": L.F2.s3_decisions("FWD", buy_and_hold=True)}
dec = {k: L.decompose_next_open(v, ohlc, rf) for k, v in w.items()}
START = "2005-11-01"                                     # first traded day of both (s1_reproduction.csv)
PERIODS = {"IS": (START, L.IS_END), "OOS": (L.OOS_START, L.OOS_END)}
me = L.month_ends(cal)
me = me[me <= pd.Timestamp(L.OOS_END)]


def nxt(d):
    i = cal.get_loc(d)
    return cal[i + 1] if i + 1 < len(cal) else None


# ------------------------------------------------------------------ switches (decision changes at month ends)
sw_rows = []
for t in L.TICK:
    ws, wb = w["S3"][t].loc[me], w["BH5"][t].loc[me]
    for i in range(1, len(me)):
        if wb.iloc[i - 1] == 0:                          # not eligible last month: initial eligibility is not a switch
            continue
        a, b = ws.iloc[i - 1], ws.iloc[i]
        if a != b:
            fill = nxt(me[i])
            sw_rows.append({"ticker": t, "decision_date": me[i].date(), "fill_date": fill.date() if fill is not None else None,
                            "type": "exit" if b == 0 else "entry",
                            "period": "IS" if fill is not None and fill <= pd.Timestamp(L.IS_END) else "OOS"})
switches = pd.DataFrame(sw_rows)
switches.to_csv(L.OUT / "s2_switches.csv", index=False)

# ------------------------------------------------------------------ per-ETF attribution
rows = []
for pname, (lo, hi) in PERIODS.items():
    for sname in ("S3", "BH5"):
        d = dec[sname]
        sl = slice(lo, hi)
        n = len(d["net"].loc[sl])
        yrs = n / L.TD
        ex_total = (d["net"].loc[sl] - d["rf"].loc[sl])
        for t in L.TICK + ["cash", "TOTAL"]:
            if t == "cash":
                held_cash = 1 - d["held"].loc[sl].sum(axis=1)
                rows.append({"period": pname, "strategy": sname, "ticker": "cash",
                             "contrib_total_ann": float((held_cash * d["rf"].loc[sl]).mean() * L.TD),
                             "contrib_excess_ann": 0.0, "avg_weight": float(held_cash.mean())})
                continue
            if t == "TOTAL":
                rows.append({"period": pname, "strategy": sname, "ticker": "TOTAL",
                             "contrib_total_ann": float(d["net"].loc[sl].mean() * L.TD),
                             "contrib_excess_ann": float(ex_total.mean() * L.TD),
                             "check_sum_excess_contribs": float(d["ex_contrib"].loc[sl].sum(axis=1).mean() * L.TD),
                             "cost_ann": float(d["cost"].loc[sl].sum(axis=1).mean() * L.TD),
                             "avg_weight": float(d["held"].loc[sl].sum(axis=1).mean()),
                             "cum_net_return": float((1 + d["net"].loc[sl]).prod() - 1)})
                continue
            held = d["held"].loc[sl, t]
            elig = dec["BH5"]["held"].loc[sl, t] > 0
            sws = switches[(switches.ticker == t) & (switches.period == pname)] if sname == "S3" else switches.iloc[0:0]
            rows.append({
                "period": pname, "strategy": sname, "ticker": t,
                "contrib_total_ann": float(d["contrib"].loc[sl, t].mean() * L.TD),
                "contrib_excess_ann": float(d["ex_contrib"].loc[sl, t].mean() * L.TD),
                "contrib_excess_cum_sum": float(d["ex_contrib"].loc[sl, t].sum()),
                "contrib_simple_heldx_rcc_ann": float((held * d["r_cc"].loc[sl, t]).mean() * L.TD),
                "cost_ann": float(d["cost"].loc[sl, t].mean() * L.TD),
                "switch_cost_ann": float(d["switch_cost"].loc[sl, t].mean() * L.TD),
                "rebalance_cost_ann": float((d["cost"].loc[sl, t] - d["switch_cost"].loc[sl, t]).mean() * L.TD),
                "avg_weight": float(held.mean()),
                "frac_days_invested": float((held > 0).mean()),
                "frac_eligible_days_invested": float((held[elig] > 0).mean()) if elig.any() else float("nan"),
                "eligible_days": int(elig.sum()),
                "n_exits": int((sws.type == "exit").sum()), "n_entries": int((sws.type == "entry").sum()),
            })
attr = pd.DataFrame(rows)
attr.to_csv(L.OUT / "s2_per_etf_attribution.csv", index=False)

# S3 minus BH5, per ETF (daily excess-contribution differences; they add up to the excess-return difference)
diff_rows = []
for pname, (lo, hi) in PERIODS.items():
    sl = slice(lo, hi)
    dd = dec["S3"]["ex_contrib"].loc[sl] - dec["BH5"]["ex_contrib"].loc[sl]
    out_mask = (dec["S3"]["held"].loc[sl] == 0) & (dec["BH5"]["held"].loc[sl] > 0)
    for t in L.TICK:
        exr = dec["S3"]["r_cc"].loc[sl, t] - dec["S3"]["rf"].loc[sl]
        diff_rows.append({"period": pname, "ticker": t,
                          "S3_minus_BH5_excess_ann": float(dd[t].mean() * L.TD),
                          "of_which_cost_diff_ann": float(-(dec["S3"]["cost"].loc[sl, t] - dec["BH5"]["cost"].loc[sl, t]).mean() * L.TD),
                          "days_out_of_market": int(out_mask[t].sum()),
                          "etf_excess_ann_when_out": float(exr[out_mask[t]].mean() * L.TD) if out_mask[t].any() else float("nan"),
                          "etf_excess_ann_when_in": float(exr[~out_mask[t] & (dec["BH5"]["held"].loc[sl, t] > 0)].mean() * L.TD)})
    tot = (dec["S3"]["net"].loc[sl] - dec["BH5"]["net"].loc[sl]).mean() * L.TD
    diff_rows.append({"period": pname, "ticker": "TOTAL", "S3_minus_BH5_excess_ann": float(tot),
                      "of_which_cost_diff_ann": float(-(dec["S3"]["cost"].loc[sl].sum(axis=1) - dec["BH5"]["cost"].loc[sl].sum(axis=1)).mean() * L.TD)})
diff = pd.DataFrame(diff_rows)
diff.to_csv(L.OUT / "s2_S3_minus_BH5_by_etf.csv", index=False)

# ETF buy-and-hold (100 %) stats per period, for context: what the window gave each asset
etf_rows = []
for pname, (lo, hi) in PERIODS.items():
    for t in L.TICK:
        r = dec["S3"]["r_cc"].loc[lo:hi, t]
        first = close[t].first_valid_index()
        r = r.loc[max(pd.Timestamp(lo), first + pd.Timedelta(days=1)):]
        st = L.stats(r, rf)
        etf_rows.append({"period": pname, "ticker": t, **{k: st[k] for k in ("start", "ann_return", "ann_vol", "sharpe", "max_drawdown")}})
pd.DataFrame(etf_rows).to_csv(L.OUT / "s2_etf_buy_hold_stats.csv", index=False)

# ------------------------------------------------------------------ step 3: timed vs untimed sleeves
sleeve_rows, sleeve_series = [], {}
for t in L.TICK:
    first_held = dec["BH5"]["held"][t]
    first_held = first_held[first_held > 0].index[0]
    for scale in (0.2, 1.0):
        for lab, src in (("timed", "S3"), ("untimed", "BH5")):
            wd = w[src][[t]] * (scale / 0.2)
            net = L.sim(wd, ohlc, rf).loc[first_held:L.OOS_END]
            sleeve_series[f"{t}_{lab}_{scale}"] = net
            for pname, (lo, hi) in PERIODS.items():
                st = L.stats(net.loc[lo:hi], rf)
                sleeve_rows.append({"ticker": t, "scale": scale, "sleeve": lab, "period": pname, **st})
sleeves = pd.DataFrame(sleeve_rows)
sleeves.to_csv(L.OUT / "s3_sleeves_timed_vs_untimed.csv", index=False)
pd.DataFrame(sleeve_series).to_csv(L.OUT / "s3_sleeve_daily_net.csv")

# paired block bootstrap of the timing value (timed - untimed Sharpe) per sleeve and period, 100 % scale
boot_rows = []
for t in L.TICK:
    a_all, b_all = sleeve_series[f"{t}_timed_1.0"], sleeve_series[f"{t}_untimed_1.0"]
    for pname, (lo, hi) in PERIODS.items():
        a = a_all.loc[lo:hi] - rf.reindex(a_all.loc[lo:hi].index)
        b = b_all.loc[lo:hi] - rf.reindex(b_all.loc[lo:hi].index)
        res = L.paired_bootstrap(a, b, block=63, reps=5000, seed=11)
        boot_rows.append({"ticker": t, "period": pname, "sr_timed": res["sr_a"], "sr_untimed": res["sr_b"],
                          "d_sr": res["d_sr"], "d_sr_lo95": res["d_sr_ci95"][0], "d_sr_hi95": res["d_sr_ci95"][1],
                          "d_mean_excess_ann": res["d_mean_excess_ann"], "d_mean_lo95": res["d_mean_excess_ci95"][0],
                          "d_mean_hi95": res["d_mean_excess_ci95"][1], "p_boot_le_0": res["p_boot_d_sr_le_0"]})
pd.DataFrame(boot_rows).to_csv(L.OUT / "s3_sleeve_timing_bootstrap.csv", index=False)

# ------------------------------------------------------------------ out-of-market spells and whipsaws
mclose = close.loc[me]
sma = mclose.rolling(10, min_periods=10).mean()
elig = mclose.notna() & sma.notna()
on = (mclose > sma) & sma.notna()
op = ohlc["open"][L.TICK]
last_day = pd.Timestamp(L.OOS_END)
spells = []
for t in L.TICK:
    e = elig[t].to_numpy()
    o = on[t].to_numpy()
    i = 0
    while i < len(me):
        if not e[i] or o[i]:
            i += 1
            continue
        j = i
        while j < len(me) and e[j] and not o[j]:
            j += 1
        kind = "initial" if (i == 0 or not e[i - 1]) else "exit"
        exit_dec = me[i]
        exit_fill = nxt(exit_dec)
        ongoing = j >= len(me)
        entry_dec = None if ongoing else me[j]
        entry_fill = None if ongoing else nxt(entry_dec)
        p0 = op.loc[exit_fill, t]
        if ongoing or entry_fill is None:
            p1 = close.loc[last_day, t]
            rf_days = rf.loc[exit_fill:last_day]
            path = close.loc[exit_fill:last_day, t]
        else:
            p1 = op.loc[entry_fill, t]
            rf_days = rf.loc[exit_fill:cal[cal.get_loc(entry_fill) - 1]]
            path = close.loc[exit_fill:cal[cal.get_loc(entry_fill) - 1], t]
        etf_ret = p1 / p0 - 1
        bill = float((1 + rf_days).prod() - 1)
        months_out = (j - i)
        spells.append({
            "ticker": t, "kind": kind, "exit_decision": exit_dec.date(), "exit_fill": exit_fill.date(),
            "exit_dec_close": float(mclose.loc[exit_dec, t]), "exit_dec_sma10": float(sma.loc[exit_dec, t]),
            "reentry_decision": entry_dec.date() if entry_dec is not None else "ongoing",
            "reentry_fill": entry_fill.date() if entry_fill is not None else "ongoing",
            "months_out": months_out, "trading_days_out": len(rf_days),
            "exit_fill_price_adj": float(p0), "reentry_fill_price_adj": float(p1),
            "etf_return_while_out": float(etf_ret), "tbill_return_while_out": bill,
            "value_100pct_sleeve": float(bill - etf_ret),                 # + = loss avoided, - = gain missed
            "value_portfolio_20pct_approx": float(0.2 * (bill - etf_ret)),
            "etf_worst_close_vs_exit_fill": float(path.min() / p0 - 1),
            "etf_best_close_vs_exit_fill": float(path.max() / p0 - 1),
            "outcome": "loss_avoided" if bill - etf_ret > 0 else "gain_missed",
            "whipsaw_le2m_higher_reentry": bool(kind == "exit" and not ongoing and months_out <= 2 and p1 > p0),
            "reentry_higher_price": bool(not ongoing and p1 > p0),
            "period": ("IS" if exit_fill <= pd.Timestamp(L.IS_END) else "OOS"),
            "crosses_IS_OOS_boundary": bool(exit_fill <= pd.Timestamp(L.IS_END) and
                                             (ongoing or entry_fill > pd.Timestamp(L.OOS_START))),
        })
        i = j
spl = pd.DataFrame(spells)
spl.to_csv(L.OUT / "s3_out_of_market_spells.csv", index=False)

agg = (spl.groupby(["period", "ticker"])
       .agg(spells=("value_100pct_sleeve", "size"),
            exits=("kind", lambda s: int((s == "exit").sum())),
            loss_avoided_n=("outcome", lambda s: int((s == "loss_avoided").sum())),
            gain_missed_n=("outcome", lambda s: int((s == "gain_missed").sum())),
            whipsaws=("whipsaw_le2m_higher_reentry", "sum"),
            sum_value_100pct=("value_100pct_sleeve", "sum"),
            sum_avoided_100pct=("value_100pct_sleeve", lambda s: float(s[s > 0].sum())),
            sum_missed_100pct=("value_100pct_sleeve", lambda s: float(s[s < 0].sum())),
            whipsaw_cost_100pct=("value_100pct_sleeve", lambda s: float(s[spl.loc[s.index, "whipsaw_le2m_higher_reentry"]].sum())),
            months_out=("months_out", "sum"))
       .reset_index())
agg.to_csv(L.OUT / "s3_spell_summary.csv", index=False)

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
print(attr[["period", "strategy", "ticker", "contrib_total_ann", "contrib_excess_ann", "cost_ann", "switch_cost_ann",
            "avg_weight", "frac_eligible_days_invested", "n_exits", "n_entries"]].round(4).to_string(index=False))
print(attr[attr.ticker == "TOTAL"][["period", "strategy", "contrib_excess_ann", "check_sum_excess_contribs"]])
print(diff.round(4).to_string(index=False))
print(pd.DataFrame(etf_rows).round(3).to_string(index=False))
print(sleeves[sleeves.scale == 1.0][["ticker", "sleeve", "period", "start", "ann_return", "ann_vol", "sharpe", "max_drawdown"]].round(3).to_string(index=False))
print(pd.DataFrame(boot_rows).round(3).to_string(index=False))
print(agg.round(3).to_string(index=False))
