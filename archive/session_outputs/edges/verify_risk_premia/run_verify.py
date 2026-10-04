import json, math, sys
import numpy as np, pandas as pd
sys.path.insert(0, ".")
import v_core as V

close, vol, roll, rf, ex, rtot = V.load()
E = V.Est(ex, close, vol)
SER = "<scratch>/edges/series/"
RP = "<scratch>/edges/risk_premia/out/"
ver = pd.read_csv(RP + "verdicts.csv").set_index("name")
# first return day: first month end where all 3 eligible, +2 sessions
for t in E.me:
    if all(E.ok(t, c) for c in V.TICK):
        start = ex.index[ex.index.get_loc(t) + 2]; break
print("start", start)
rows = []; out = {}
for s in ["ES", "ZN", "GC", "SB"]:
    for ov in ["STATIC", "CV", "CVB", "MM", "FB", "FBB"]:
        name = f"rpm_{s}_{ov}"
        w = E.sb(ov) if s == "SB" else E.single({"ES": "F_ES", "ZN": "F_ZN", "GC": "F_GC"}[s], ov)
        n1, g, turn = V.sim_daily(w, rtot, rf, roll, 1.0)
        n2, _, _ = V.sim_daily(w, rtot, rf, roll, 2.0)
        d1, dg = V.sim_drift(w, rtot, rf, roll, 1.0)
        d2, _ = V.sim_drift(w, rtot, rf, roll, 2.0)
        x1 = (n1 - rf).loc[start:]; x2 = (n2 - rf).loc[start:]; xg = (g - rf).loc[start:]
        y1 = (d1 - rf).loc[start:]; y2 = (d2 - rf).loc[start:]
        out[name] = pd.DataFrame({"net_1x": x1, "net_2x": x2, "gross": xg, "drift_1x": y1, "drift_2x": y2})
        IS = slice(start, V.IS_END); A = slice(start, V.A_END); B = slice(V.A_END + pd.Timedelta(days=1), V.IS_END); L = slice(V.LATER_START, None)
        f = pd.read_parquet(SER + name + ".parquet")
        yrs = len(x1.loc[IS]) / 252
        sr = V.sharpe(x1.loc[IS])
        rows.append(dict(name=name,
            my_is_1x=sr, my_is_2x=V.sharpe(x2.loc[IS]), my_is_g=V.sharpe(xg.loc[IS]),
            my_A=V.sharpe(x1.loc[A]), my_B=V.sharpe(x1.loc[B]), my_nw=V.nw_t(x1.loc[IS]),
            my_mdd_tot=V.mdd(n1.loc[start:V.IS_END]), my_mdd_ex=V.mdd(x1.loc[IS]),
            my_later=V.sharpe(x1.loc[L]), my_drift_is_1x=V.sharpe(y1.loc[IS]), my_drift_later=V.sharpe(y1.loc[L]),
            my_turn=turn.loc[start:V.IS_END].sum() / yrs,
            se=math.sqrt((1 + sr ** 2 / 2) / yrs),
            an_is_1x=ver.at[name, "is_sharpe_net1"], an_later=ver.at[name, "later_sharpe_net1"], an_nw=ver.at[name, "is_nw_t"],
            an_mdd=ver.at[name, "is_max_dd"],
            file_is_1x=V.sharpe(f["net_1x"].loc[IS]), file_is_2x=V.sharpe(f["net_2x"].loc[IS]), file_g=V.sharpe(f["gross"].loc[IS]),
            file_later=V.sharpe(f["net_1x"].loc[L]), file_start=str(f.index[0].date()), file_end=str(f.index[-1].date()),
            corr_file_mine=float(pd.concat([f["net_1x"], x1], axis=1).dropna().corr().iloc[0, 1]),
            maxabs_file_mine=float((f["net_1x"] - x1).abs().max()),
        ))
tab = pd.DataFrame(rows)
tab.to_csv("recompute.csv", index=False)
pd.to_pickle(out, "my_series.pkl")
with pd.option_context("display.width", 300, "display.max_columns", 50):
    print(tab.round(3).to_string(index=False))
