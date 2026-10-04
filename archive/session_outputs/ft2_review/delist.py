import sys, pickle
sys.path.insert(0, r"<solo-repo>")
import numpy as np, pandas as pd
from src import engine as E, forward2 as F2, calendar_utils as CU
SP = r"<scratch>/ft2_review/"
D = pickle.load(open(SP + "dec_base.pkl", "rb"))
ORIG = E.load_ohlc
TK, CUT = sys.argv[1], pd.Timestamp(sys.argv[2])
rf_all = E.load_rf("FWD")
def load_ohlc(tickers=None, period="IS"):
    out = {k: v.copy() for k, v in ORIG(tickers, period).items()}
    if TK in out["close"].columns:
        c = out["close"][TK]
        after = c.index > CUT
        r = rf_all.reindex(c.index).ffill().fillna(0.0)
        # exactly what download_databento._to_nyse writes once the vendor stops sending bars: comp = 0, tr = rf
        tr = c.pct_change(fill_method=None).fillna(0.0)
        tr[after] = r[after]
        lvl = 100 * (1 + tr).cumprod()
        for k in ("open", "high", "low", "close"):
            out[k][TK] = lvl.values
        out["volume"].loc[after, TK] = 0.0
    return out
E.load_ohlc = load_ohlc
s1 = F2.s1_decisions("FWD")
E.load_ohlc = ORIG
me = CU.month_offsets(s1.index); me = me.index[me.off_own == 0]
rows = []
for t in me[me > CUT][:30:2]:
    w = s1.loc[t]; g = w.abs().sum()
    rows.append({"month_end": t.date(), f"{TK} weight": round(w[TK], 3), f"base {TK}": round(D["S1"].loc[t, TK], 3),
                 f"{TK} share of gross": round(abs(w[TK]) / g, 3) if g else np.nan, "gross": round(g, 3),
                 "max|other w - base|": round(float((w.drop(TK) - D["S1"].loc[t].drop(TK)).abs().max()), 3)})
print(pd.DataFrame(rows).to_string(index=False))
