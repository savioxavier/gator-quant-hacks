"""Sanity checks of signals and decisions (no new variants)."""
import sys, runpy
import numpy as np, pandas as pd
g = runpy.run_path(__file__.replace("check.py", "study.py"))
L, SIG, MOM, dec, spot, me = g["L"], g["SIG"], g["MOM"], g["dec"], g["spot"], g["me"]
t = pd.Timestamp("2015-12-31")
print("CL spot levels 2010-06..2011-06:", L.loc["2010-06-30":"2011-06-30", "F_CL"].round(2).tolist())
print("CL spot at t", L.at[t, "F_CL"], " VW1", SIG["VW1"].at[t, "F_CL"], "check", np.log(L.loc["2010-06-30":"2011-06-30","F_CL"].mean()) - np.log(L.at[t,"F_CL"]))
print("VW1 at t by market:\n", SIG["VW1"].loc[t].round(3).to_string())
for n in ["VAL_XS_VW1", "COMBO_XS", "VAL_ALL", "BOND_B1"]:
    d = dec[n]
    ks = sorted(d)
    w = pd.DataFrame({k: d[k] for k in ks}).T
    print(n, "gross mean", w.abs().sum(axis=1).mean().round(2), "max", w.abs().sum(axis=1).max().round(2), "net mean", w.sum(axis=1).mean().round(3), "n nonzero mean", (w.abs() > 1e-9).sum(axis=1).mean().round(1))
w = pd.DataFrame({k: dec["VAL_XS_VW1"][k] for k in sorted(dec["VAL_XS_VW1"])}).T
print(w.loc["2016-01-29"].round(3)[w.loc["2016-01-29"].abs() > 0].to_string())
print("EQ count over time:", (w[[c for c in w if c in g['CLASSES']['EQ']]].abs() > 0).sum(axis=1).resample('YE').last().to_dict())
print("bond dev B1 at a few dates:", g["BOND_DEV"]["B1"].loc[["2012-12-31","2016-12-30","2020-12-31","2023-10-31"]].round(2).to_dict())
