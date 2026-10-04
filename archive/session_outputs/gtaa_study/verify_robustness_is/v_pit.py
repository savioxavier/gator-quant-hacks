import os, sys, math, itertools, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vlib as V
from src import engine as E
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "robustness_is"))
import gtaa_lib as AL   # analyst's decision builder, only to test it for lookahead
ohlc = E.load_ohlc(V.TICK, "IS"); rf = E.load_rf("IS"); close = ohlc["close"]; cal = close.index
me = V.complete_month_ends(cal, cal[-1]); start = pd.Timestamp("2007-02-28")
grid = list(itertools.product(V.SIGS, V.UNI, V.WTS, V.ROFF))
rng = np.random.default_rng(0)
bad_mine = bad_theirs = 0
for cut in ["2009-03-09", "2015-06-30", "2020-03-20"]:
    cut = pd.Timestamp(cut)
    c2 = close.copy(); m = c2.index > cut
    c2.loc[m] = c2.loc[m].to_numpy() * np.exp(rng.normal(0, 0.2, size=c2.loc[m].shape))
    rf2 = rf.copy(); rf2.loc[rf2.index > cut] = rng.uniform(0, 0.001, (rf2.index > cut).sum())
    for k in grid:
        a, _ = V.build_decisions(k, close, rf, me, start); b, _ = V.build_decisions(k, c2, rf2, me, start)
        bad_mine += int(not np.allclose(a.loc[:cut], b.loc[:cut]))
        a2 = AL.decisions(k, close, rf, start); b2 = AL.decisions(k, c2, rf2, start)
        bad_theirs += int(not np.allclose(a2.loc[:cut], b2.loc[:cut]))
        # mine vs theirs identical decisions on real data
        assert np.allclose(a.reindex(columns=a2.columns), a2), k
print("PIT violations mine", bad_mine, "theirs", bad_theirs, "; decisions identical mine vs theirs for all 72")
# delay sensitivity: trade one session later (open of d+2)
rfd = rf.reindex(cal).ffill().fillna(0.0)
gains = {}
for lag in (0, 1):
    S = {}
    for k, timed in [(k, True) for k in grid] + [(("SMA10", u, w, "tbill"), False) for u in V.UNI for w in V.WTS]:
        W, _ = V.build_decisions(k, close, rf, me, start, timed); W = W.shift(lag).fillna(0.0)
        net, *_ = E.simulate(W, ohlc, rf, exec="next_open"); ex = (net - rfd).loc["2007-03-02":]
        S["|".join(k) if timed else "BH|%s|%s" % k[1:3]] = V.sharpe(ex)
    g = pd.Series({"|".join(k): S["|".join(k)] - S["BH|%s|%s" % k[1:3]] for k in grid})
    print("lag", lag, "median timing gain %.3f share %.2f median Sharpe %.3f" % (g.median(), (g > 0).mean(), np.median([S["|".join(k)] for k in grid])))
