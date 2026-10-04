import sys, warnings
sys.path.insert(0, r"<solo-repo>")
import numpy as np, pandas as pd
from src import engine as E, forward2 as F2
ORIG_O, ORIG_R = E.load_ohlc, E.load_rf
cal = E.trading_calendar("FWD")
def run(label, close_fn, rf_val=0.0):
    def lo(tickers=None, period="IS"):
        c = close_fn(tickers)
        return {"open": c, "high": c, "low": c, "close": c, "volume": c * 0 + 1, "roll": c * 0}
    E.load_ohlc = lo; E.load_rf = lambda period="IS": pd.Series(rf_val, index=cal)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = {k: f() for k, f in {"S1": lambda: F2.s1_decisions("FWD"), "S2": lambda: F2.s2_decisions("FWD"),
                                       "ES": lambda: F2.es_sleeve_decisions("FWD"), "S3": lambda: F2.s3_decisions("FWD")}.items()}
        print(label, {k: (int(np.isnan(v.to_numpy()).sum()), int(np.isinf(v.to_numpy()).sum()), round(float(v.abs().sum(axis=1).max()), 4)) for k, v in out.items()})
    except Exception as e:
        print(label, "RAISED", type(e).__name__, e)
    finally:
        E.load_ohlc, E.load_rf = ORIG_O, ORIG_R
rng = np.random.default_rng(1)
run("flat prices rf=0", lambda t: pd.DataFrame(100.0, index=cal, columns=t))
run("flat prices rf>0", lambda t: pd.DataFrame(100.0, index=cal, columns=t), 0.0001)
def holes(t):
    c = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (len(cal), len(t))), axis=0)), index=cal, columns=t)
    c = c.mask(rng.random(c.shape) < 0.3)          # 30 % random missing prints
    c.iloc[:800, : len(t) // 2] = np.nan           # half the universe starts late
    return c
run("30% random holes + late starters", holes)
def one_day(t):
    c = pd.DataFrame(np.nan, index=cal, columns=t); c.iloc[-1] = 100.0; return c
run("almost no history", one_day)
