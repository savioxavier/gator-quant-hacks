"""Diagnostic (no new variants): how much of each variant is a directional bond / equity exposure created by the
announcement gate (truncated short legs, full long legs). OLS of daily net 1x excess on the instrument excess."""
import sys, os, json, math
sys.path.insert(0, "<solo-repo>")
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
import statsmodels.api as sm
import auction_futures as AF
ohlc, rf, cal, calx, rex, a = AF.load_data()
out = {}
for vid, inst in [("V3_all_t10_x", "F_ZN"), ("V1_all_t10", "F_ZN"), ("V1_all_t5", "F_ZN"), ("V3_all_t5_x", "F_ZN"),
                  ("D1_all_t5_known", "F_ZN"), ("V4_ES_2y", "F_ES"), ("V4_ES_2y_x", "F_ES")]:
    s = pd.read_parquet(f"{AF.SER}/{vid}.parquet")["net_1x"]
    s.index = pd.to_datetime(s.index)
    d = {}
    for wn, (w0, w1) in (("sel", AF.SEL), ("val", AF.VAL), ("full", AF.FULL)):
        j = pd.concat([s.loc[w0:w1], rex[inst].loc[w0:w1]], axis=1).dropna()
        j.columns = ["y", "x"]
        fit = sm.OLS(j["y"], sm.add_constant(j["x"])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
        resid_alpha = j["y"] - fit.params["x"] * j["x"]
        d[wn] = {"beta": float(fit.params["x"]), "alpha_ann_pct": float(fit.params["const"] * 252 * 100),
                 "alpha_t": float(fit.tvalues["const"]),
                 "beta_hedged_sharpe": float(resid_alpha.mean() / resid_alpha.std() * math.sqrt(252)),
                 "inst_sharpe": float(j["x"].mean() / j["x"].std() * math.sqrt(252))}
    out[vid] = d
    print(vid, inst, {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in d.items()})
# signed exposure of the gated legs: long days vs short days (unit signals), all traded maturities, t=10 / t=5
for t in (5, 10):
    longd = shortd = 0
    for term in AF.TRADED:
        ev = a[a.term == term]
        w, er, fl, held = AF.sleeve_positions(ev, AF.INST[term], None, (-t + 1, 0), (1, t), True, cal, calx, rex, 30 / AF.DUR[AF.INST[term]])
        h = pd.Series(held, index=cal).loc[AF.FULL[0]:AF.FULL[1]]
        longd += int((h > 0).sum()); shortd += int((h < 0).sum())
    out[f"gated_long_short_days_t{t}"] = {"long": longd, "short": shortd}
    print("t", t, "sleeve-days long", longd, "short", shortd)
json.dump(out, open(os.path.join(os.path.dirname(__file__), "beta_diag.json"), "w"), indent=2)
