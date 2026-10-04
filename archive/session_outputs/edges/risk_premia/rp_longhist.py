"""Long-history proxy check (SPEC.md section 5): the same rules on the Ken French daily market (1926-) and a
constant-maturity 10-year par bond rebuilt from FRED DGS10 (1962-). Descriptive; not tradeable history."""
from __future__ import annotations

import numpy as np
import pandas as pd

import rp_core as R
from src import config as C
from src import engine as E

LH = R.EDGES.parent / "gtaa_study" / "long_history" / "data"
COST = {"F_LHEQ": 0.75, "F_LHBD": 1.0}
IS_END = pd.Timestamp(C.IS_END)
LATER_START = pd.Timestamp(C.OOS_START)


def load():
    eq = pd.read_parquet(LH / "daily_us_eq.parquet")
    bd = pd.read_parquet(LH / "daily_us_10y.parquet")
    rfd = E.load_series("rf_daily.parquet", "FWD")["rf"]
    cal = pd.DatetimeIndex(eq.index)
    cash = eq["rf"].copy()
    later = cal >= rfd.index[0]
    cash[later] = rfd.reindex(cal[later]).ffill().to_numpy()
    eq_ex = eq["US_EQ"] - eq["rf"]
    bex = bd["US_10Y"] - bd["rf"]
    bidx = (1 + bex).cumprod()
    bidx = bidx.reindex(cal.union(bidx.index)).ffill().reindex(cal)
    bidx[cal < bd.index[0]] = np.nan
    bd_ex = bidx.pct_change(fill_method=None)
    ex = pd.DataFrame({"F_LHEQ": eq_ex, "F_LHBD": bd_ex}, index=cal)
    tr = (1 + ex.add(cash, axis=0)).cumprod()
    tr["F_LHBD"] = (1 + ex["F_LHBD"].fillna(0.0) + cash).cumprod().where(bidx.notna())
    roll = pd.DataFrame(0.0, index=cal, columns=ex.columns)
    s = pd.Series(cal, index=cal)
    # ES-like: first session on/after the 10th of Mar/Jun/Sep/Dec; ZN-like: last session of Feb/May/Aug/Nov
    for (y, m), g in s.groupby([cal.year, cal.month]):
        if m in (3, 6, 9, 12):
            d = g[g.dt.day >= 10]
            if len(d):
                roll.loc[d.iloc[0], "F_LHEQ"] = 1.0
        if m in (2, 5, 8, 11):
            roll.loc[g.iloc[-1], "F_LHBD"] = 1.0
    ohlc = {"close": tr, "open": tr, "volume": tr.notna().astype(float), "roll": roll,
            "high": tr, "low": tr}
    return ex, tr, ohlc, cash.rename("rf"), cal


def main() -> None:
    ex, tr, ohlc, cash, cal = load()
    P = R.Panel(ex, tr)
    sims = {}
    for sleeve, cols in (("EQ", ["F_LHEQ"]), ("BOND", ["F_LHBD"]), ("SB", ["F_LHEQ", "F_LHBD"])):
        for ov in ("STATIC", "CV", "MM", "FB"):
            w = P.single(cols[0], ov) if len(cols) == 1 else P.rp(cols, ov)
            res = {}
            for m in (1.0, 2.0, 0.0):
                net, gross, turn, held, cost = E.simulate(w, ohlc, cash, exec="next_close", cost_bps=COST, cost_mult=m)
                res[m] = (net, turn, held)
            live = res[1.0][2].abs().sum(axis=1) > 0
            first = live.idxmax()
            if ov == "FB":       # FB may start flat: use its CV twin's start
                first = sims[f"LH_{sleeve}_CV"]["start"]
            sims[f"LH_{sleeve}_{ov}"] = {"start": first, "net1": res[1.0][0], "net2": res[2.0][0], "netg": res[0.0][0],
                                       "turn": res[1.0][1], "held": res[1.0][2]}
    rows = []
    windows_eq = [("IS_full", None, IS_END), ("MM_sample_1927_2015", None, pd.Timestamp("2015-12-31")),
                  ("post_2016", pd.Timestamp("2016-01-01"), IS_END), ("IS_1963", pd.Timestamp("1963-01-01"), IS_END),
                  ("LATER", LATER_START, cal[-1])]
    windows_sb = [("IS_full", None, IS_END), ("pre_2000", None, pd.Timestamp("1999-12-31")),
                  ("post_2000", pd.Timestamp("2000-01-01"), IS_END), ("post_2016", pd.Timestamp("2016-01-01"), IS_END),
                  ("LATER", LATER_START, cal[-1])]
    decades = [(f"dec_{y}s", pd.Timestamp(f"{y}-01-01"), min(pd.Timestamp(f"{y + 9}-12-31"), IS_END))
               for y in range(1920, 2030, 10)]
    for name, d in sims.items():
        wins = (windows_eq if "_EQ_" in name else windows_sb) + decades
        for lab, a, b in wins:
            a = max(a, d["start"]) if a is not None else d["start"]
            if a >= b:
                continue
            sl = slice(a, b)
            rf = cash.loc[sl]
            ex1 = d["net1"].loc[sl] - rf
            if len(ex1) < 252:
                continue
            ex2 = d["net2"].loc[sl] - rf
            exg = d["netg"].loc[sl] - rf
            st = R.window_stats(ex1, ex2, exg, d["net1"].loc[sl], d["turn"].loc[sl], cal)
            yr = (1 + ex1).groupby(ex1.index.year).prod() - 1
            for y in (1973, 1974, 2008, 2022):
                st[f"ret_{y}"] = float(yr.get(y, np.nan))
            st["avg_gross"] = float(d["held"].loc[sl].abs().sum(axis=1).mean())
            st.update({"name": name, "window": lab})
            rows.append(st)
    tab = pd.DataFrame(rows)
    tab = tab[["name", "window"] + [c for c in tab.columns if c not in ("name", "window")]]
    tab.to_csv(R.OUT / "longhist_table.csv", index=False)

    comps = []
    for sleeve in ("EQ", "BOND", "SB"):
        s0 = sims[f"LH_{sleeve}_CV"]["start"]
        for lab, a, b in (("IS_full", s0, IS_END), ("post_2016", pd.Timestamp("2016-01-01"), IS_END)):
            g = lambda ov: (sims[f"LH_{sleeve}_{ov}"]["net1"] - cash).loc[a:b]
            for x, y in (("CV", "STATIC"), ("MM", "STATIC"), ("MM", "CV"), ("FB", "CV")):
                r = R.block_bootstrap_diff(g(x), g(y))
                comps.append({"sleeve": sleeve, "window": lab, "a": x, "b": y, **r,
                              "mdd_a": R.max_dd(sims[f"LH_{sleeve}_{x}"]["net1"].loc[a:b]),
                              "mdd_b": R.max_dd(sims[f"LH_{sleeve}_{y}"]["net1"].loc[a:b])})
    s0 = sims["LH_SB_CV"]["start"]
    for x, y in (("LH_SB_CV", "LH_EQ_CV"), ("LH_SB_STATIC", "LH_EQ_STATIC"), ("LH_SB_FB", "LH_EQ_CV")):
        r = R.block_bootstrap_diff((sims[x]["net1"] - cash).loc[s0:IS_END], (sims[y]["net1"] - cash).loc[s0:IS_END])
        comps.append({"sleeve": "cross", "window": "IS_1963", "a": x, "b": y, **r,
                      "mdd_a": R.max_dd(sims[x]["net1"].loc[s0:IS_END]), "mdd_b": R.max_dd(sims[y]["net1"].loc[s0:IS_END])})
    pd.DataFrame(comps).to_csv(R.OUT / "longhist_bootstrap.csv", index=False)

    # daily series of the proxy variants (descriptive; kept in out/, not in series/)
    ser = {}
    for name, d in sims.items():
        ser[(name, "net_1x")] = d["net1"] - cash
        ser[(name, "net_2x")] = d["net2"] - cash
        ser[(name, "gross")] = d["netg"] - cash
    sd = pd.DataFrame(ser)
    sd.columns = [f"{a}|{b}" for a, b in sd.columns]
    sd.to_parquet(R.OUT / "longhist_series.parquet")

    with pd.option_context("display.width", 250, "display.max_rows", 400):
        print(tab[["name", "window", "start", "end", "sharpe_net1", "sharpe_net2", "sharpe_gross", "ann_vol", "max_dd",
                   "worst_year", "pct_positive_years", "roll2y_p10", "nw_t"]].round(3).to_string(index=False))
        print(pd.DataFrame(comps).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
