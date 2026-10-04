"""V4: portfolio add. core_ER_6 rebuilt with the project's combine.build (equal risk, 6 % target), with
my independently built strategy series as a fourth sleeve. Also cross-checks against analyse outputs."""
import importlib.util
import json
import math

import numpy as np
import pandas as pd

import vlib as V

OUT = V.HERE / "out"
res = {}
spec = importlib.util.spec_from_file_location("combine", V.EDGES / "combine" / "combine.py")
CB = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CB)
cal, rf, slv, gr, cost, nat, es_ex, s1, f2, extra = CB.load()
core = ["rpm_ES_MM", "CAL_TSY_ME_ZN", "S1"]
saved = pd.read_parquet(V.EDGES / "series" / "PORT_core_ER_6.parquet")
base = CB.build(core, "ER", 0.06, cal, slv, gr, cost)
res["rebuild_vs_saved_core_ER_6_maxabs"] = float((base["ret"]["net_1x"].reindex(saved.index) - saved["net_1x"]).abs().max())

D = pd.read_parquet(OUT / "v3_daily.parquet")
first = pd.Timestamp("2011-12-30")
for k in ("asrun", "strict_all"):
    df = pd.DataFrame({"net_1x": D[f"{k}_ex1"], "net_2x": D[f"{k}_ex2"], "gross": D[f"{k}_exg"]})
    df.loc[df.index < first] = np.nan
    nm = "V_" + k
    slv[nm] = df.reindex(cal)
    gr[nm] = D[f"{k}_gross_lev"].reindex(cal).fillna(0.0).where(slv[nm]["net_1x"].notna(), 0.0)
    cost[nm] = float(D[f"{k}_cost_bp"].iloc[0])
res["sleeve_cost_bp"] = {k: v for k, v in cost.items() if k.startswith("V_")}

p0 = pd.Timestamp("2012-05-02")
W = {"IS": (p0, V.IS_END), "HOLDOUT": (pd.Timestamp("2021-01-01"), V.IS_END), "OOS": (V.OOS_START, V.END),
     "FULL": (p0, V.END), "IS_2012_2017": (p0, pd.Timestamp("2017-12-31"))}
rows = []
b1 = base["ret"]["net_1x"]
for k in ("asrun", "strict_all"):
    nm = "V_" + k
    bl = CB.build(core + [nm], "ER", 0.06, cal, slv, gr, cost)
    r1 = bl["ret"]["net_1x"]
    for wn, (a, z) in W.items():
        x, y = r1.loc[a:z].dropna(), b1.loc[a:z].dropna()
        bb = CB.block_boot_diff(x, y, block=63, n=5000, seed=11)
        s = slv[nm]["net_1x"].loc[a:z]
        jj = pd.concat([s, y], axis=1).dropna()
        mj = jj.groupby(jj.index.to_period("M")).sum()
        rows.append({"sleeve": nm, "window": wn, "base_sharpe": V.sharpe(y), "with_sleeve_sharpe": V.sharpe(x),
                     "d_sharpe": bb["diff"], "boot_p": bb["p_two_sided"], "ci90": bb["ci90"],
                     "corr_sleeve_vs_base_daily": float(jj.corr().iloc[0, 1]), "corr_monthly": float(mj.corr().iloc[0, 1]),
                     "mean_mult_sleeve": float(bl["m"][nm].loc[a:z].mean())})
P = pd.DataFrame(rows)
P.to_csv(OUT / "v4_portfolio.csv", index=False)

# cross-check against the analyse agent's saved daily series
A = pd.read_parquet(V.FS / "analyse" / "daily_returns.parquet")
res["analyse_daily_columns"] = list(A.columns)[:40]
for c in A.columns:
    if "tone" in c and ("ex_net1x" in c or c.endswith("ex1")):
        res[f"maxabs_mine_vs_analyse_{c}"] = float((D["asrun_ex1"].reindex(A.index) - A[c]).abs().max())
S = pd.read_parquet(V.FS / "analyse" / "signal_session_2010_2026.parquet")
Wm = pd.read_parquet(OUT / "v3_weights_session.parquet")
res["maxabs_mine_vs_analyse_session_weights"] = {"TLT": float((Wm["asrun"].reindex(S.index) - S["tone_TLT"]).abs().max()),
                                                 "UUP": float((Wm["asrun_uup"].reindex(S.index) - S["tone_UUP"]).abs().max())}
pd.set_option("display.width", 250, "display.max_columns", 30)
print(P.round(3).to_string())
print(json.dumps(res, indent=1, default=str))
(OUT / "v4_portfolio.json").write_text(json.dumps(res, indent=1, default=str))
