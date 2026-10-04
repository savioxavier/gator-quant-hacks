import sys, time, pickle
sys.path.insert(0, r"<solo-repo>")
import numpy as np, pandas as pd
from src import engine as E, forward2 as F2, config as C, calendar_utils as CU
SP = r"<scratch>/ft2_review/"
t0 = time.time()
D = {}
D["S1"] = F2.s1_decisions("FWD"); print("s1", time.time()-t0)
D["S2"] = F2.s2_decisions("FWD"); print("s2", time.time()-t0)
D["ES_10VOL"] = F2.es_sleeve_decisions("FWD")
D["S3"] = F2.s3_decisions("FWD")
D["BH5"] = F2.s3_decisions("FWD", buy_and_hold=True)
pickle.dump(D, open(SP + "dec_base.pkl", "wb"))
for k, w in D.items():
    a = w.to_numpy()
    print(k, w.shape, "nan", int(np.isnan(a).sum()), "inf", int(np.isinf(a).sum()), "max|w|", float(np.nanmax(np.abs(a))),
          "max gross", float(w.abs().sum(axis=1).max()), "first nonzero", w.index[(w.abs().sum(axis=1) > 0).argmax()].date(), "last idx", w.index[-1].date())
# month ends near the end
cal = D["S1"].index
mo = CU.month_offsets(cal)
print("last month ends:", list(mo.index[mo.off_own == 0][-3:].date), "Oct T_i:", mo.loc["2026-10"].T_i.unique())
# positions recompute
pos = pd.read_csv(r"<solo-repo>/forward/positions2_for_2026-10-06.csv")
mx = 0
for name in F2.STRATEGIES:
    p = F2.positions_for_next_session(name, "FWD")
    f = pos[pos.strategy == name].set_index("instrument")["weight_of_nav"]
    j = pd.concat([p.round(6).rename("now"), f.rename("file")], axis=1)
    d = (j["now"] - j["file"]).abs().max()
    print(name, "n_now", len(p), "n_file", len(f), "max|diff|", d, "missing", sorted(set(p.index) ^ set(f.index)))
    print("   decision at last date equals decision at last month end?", bool((D[name].iloc[-1] == D[name].loc["2026-09-30"]).all()))
# gross of S1/S2 at last month end, ex-ante vol
_, rf, ex = F2._futures_panel(F2.S1_TICKERS, "FWD")
for name in ["S1", "S2"]:
    w = D[name].loc["2026-09-30"]
    cols = [c for c in w.index if w[c] != 0]
    cov = ex.loc[:"2026-09-30", cols].tail(252).cov(min_periods=60).fillna(0).to_numpy()
    v = w[cols].to_numpy()
    print(name, "gross", float(w.abs().sum()), "exante vol", float(np.sqrt(v @ cov @ v * 252)), "net", float(w.sum()))
