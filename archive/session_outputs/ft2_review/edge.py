import sys, pickle
sys.path.insert(0, r"<solo-repo>")
import numpy as np, pandas as pd
from src import engine as E, forward2 as F2, calendar_utils as CU
SP = r"<scratch>/ft2_review/"
D = pickle.load(open(SP + "dec_base.pkl", "rb"))
ohlc, rf, ex = F2._futures_panel(F2.S1_TICKERS, "FWD")
vol = np.sqrt(ex.pow(2).ewm(com=F2.EWMA_COM, min_periods=60).mean() * 252)
print("cost map:", F2.S1_COST_BPS)
# 6S around de-peg
print(pd.DataFrame({"ex_6S": ex["F_6S"], "vol_6S": vol["F_6S"]}).loc["2015-01-12":"2015-01-21"].to_string())
me = CU.month_offsets(ex.index); me = me.index[me.off_own == 0]
for t in ["2014-12-31", "2015-01-30", "2015-02-27"]:
    print(t, "S1 6S", D["S1"].loc[t, "F_6S"], "S2 6S", D["S2"].loc[t, "F_6S"], "S1 gross", D["S1"].loc[t].abs().sum(), "S1 finite", bool(np.isfinite(D["S1"].loc[t]).all()))
# RTY eligibility
cnt = ex.notna().cumsum()
first_elig = [t for t in me if cnt.loc[t, "F_RTY"] >= 300][0]
print("RTY first ex", ex["F_RTY"].first_valid_index().date(), "first eligible month end", first_elig.date(),
      "S1 RTY weight at prior ME", D["S1"].loc[me[me < first_elig][-1], "F_RTY"], "at first", D["S1"].loc[first_elig, "F_RTY"])
# number eligible per month end, gross cap binding frequency
nel = pd.Series({t: int((D["S1"].loc[t] != 0).sum()) for t in me})
print("S1 nonzero count min/max after 2011-08:", nel.loc["2011-08-31":].min(), nel.loc["2011-08-31":].max())
g1 = D["S1"].loc[me].abs().sum(axis=1); g2 = D["S2"].loc[me].abs().sum(axis=1)
print("S1 gross cap binds at", int((g1 > 2.999999).sum()), "of", int((g1 > 0).sum()), "month-ends; S2:", int((g2 > 2.999999).sum()), "of", int((g2 > 0).sum()))
ges = D["ES_10VOL"].loc[me, "F_ES"]
print("ES_10VOL weight range", float(ges[ges > 0].min()), float(ges.max()))
# positions mechanics: extend with two pad sessions, simulate on flat dummy prices
pad = pd.DatetimeIndex(["2026-10-05", "2026-10-06"])
for name, conv, tk in [("S1", "next_close", F2.S1_TICKERS), ("S3", "next_open", F2.S3_TICKERS)]:
    w = D[name]
    idx = w.index.append(pad)
    dummy = {k: pd.DataFrame(100.0, index=idx, columns=tk) for k in ("open", "high", "low", "close")}
    dummy["roll"] = pd.DataFrame(0.0, index=idx, columns=tk)
    _, _, _, held, _ = E.simulate(w.reindex(idx).ffill(), dummy, pd.Series(0.0, index=idx), exec=conv)
    p = F2.positions_for_next_session(name, "FWD")
    h = held.loc["2026-10-06"]; h = h[h.abs() > 1e-12]
    print(name, conv, "held over 2026-10-06 equals positions file decision:", bool(np.allclose(h.reindex(p.index).values, p.values)) and set(h.index) == set(p.index),
          "| held over 2026-10-05 equals it too:", bool(np.allclose(held.loc["2026-10-05"].reindex(p.index).values, p.values)))
