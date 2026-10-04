import os, math, numpy as np, pandas as pd
OUT = os.path.dirname(os.path.abspath(__file__))
t = pd.read_csv(os.path.join(OUT, "v_is_table.csv"), index_col=0)
X = pd.read_parquet(os.path.join(OUT, "v_is_excess.parquet"))
T = t[t.sig != "BH"]
s3 = "SMA10|frozen5|equal|tbill"
nb = []
for dim, opts in [(0, ["SMA6","SMA8","SMA12","MOM12","SMA10_D1"]), (1, ["broad10","eq4"]), (2, ["invvol63"]), (3, ["IEF"])]:
    for o in opts:
        k = s3.split("|"); 
        if dim == 0 and o in ("SMA6",): continue  # one-step = adjacent? include SMA8/12 + MOM12 + D1
        k[dim] = o; nb.append("|".join(k))
print("neighbours (%d):" % len(nb)); print(T.loc[nb, "sharpe"].round(3).to_string()); print("median", T.loc[nb,"sharpe"].median().round(3))
f = T[(T.uni=="broad10")&(T.wt=="invvol63")&(T.ro=="tbill")]; print("broad10/invvol63/tbill median", f.sharpe.median().round(3))
print("by uni median IS:", T.groupby("uni").sharpe.median().round(3).to_dict(), "by wt:", T.groupby("wt").sharpe.median().round(3).to_dict())
unt = {c: "BH|%s|%s" % tuple(c.split("|")[1:3]) for c in T.index}
ir = pd.Series({c: (X[c]-X[unt[c]]).mean()/(X[c]-X[unt[c]]).std()*math.sqrt(252) for c in T.index}); print("timing increment IR median %.3f" % ir.median())
rf_net = None
# S3 - BH5 by year using excess (rf cancels in difference of compounding roughly; use excess+rf? use excess compounding diff)
y = lambda s: (1+s).groupby(s.index.year).prod()-1
d = (y(X[s3]) - y(X["BH|frozen5|equal"])) * 100
print("S3-BH5 by year (excess-return compounding, pp):", d.round(1).to_dict())
# how many timed variants beat both S3 and own untimed
print("beat both S3 and untimed:", int(((T.sharpe > T.loc[s3,"sharpe"]) & (T.d_untimed > 0)).sum()))
# sensitivity: timing gain with 1 extra day of delay (decision at close d, trade at open d+2)
