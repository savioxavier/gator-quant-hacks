"""Independent monthly cross-check (no engine.simulate): unscaled equal-weight long-short monthly returns."""
import sys, math
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as K

B = Path(__file__).resolve().parents[1]

def monthly_ls(close, rf, names, win_m, n, lag_days=1):
    # month-end closes; formation = return over win_m months; hold next month (close-to-close, from the month-end
    # close + lag_days sessions to the next month-end close + lag_days): approximates next_close fills
    cal = close.index
    me = K.month_ends(cal)
    pos = cal.get_indexer(me)
    rets = []
    for i in range(win_m, len(me) - 1):
        t = me[i]
        a, b = pos[i] + 1, pos[i + 1] + 1
        if b >= len(cal):
            break
        f = close[names].iloc[pos[i]] / close[names].iloc[pos[i - win_m]] - 1 if win_m else None
        f = f.dropna()
        if len(f) < 2 * n:
            continue
        top, bot = K.rank_pick(f, n)
        h = close[names].iloc[b] / close[names].iloc[a] - 1
        rets.append((me[i + 1], h[top].mean() - h[bot].mean()))
    s = pd.Series(dict(rets))
    return s

def sr(s):
    return s.mean() / s.std() * math.sqrt(12)

P = K.futures_panel([f"F_{r}" for r in K.COMM])
c = P["ohlc"]["close"]
m = monthly_ls(c, P["rf"], list(c.columns), 12, 3)
print("commodity 12m EW top3-bot3 monthly gross SR IS:", round(sr(m.loc["2011-07":"2024-09"]), 3), "later:", round(sr(m.loc["2024-10":]), 3))
v = pd.read_parquet(B / "trend_momentum_commodity_xsmom/variants/V1_12m_EW.parquet")
g = (1 + v["gross"]).resample("ME").prod() - 1
print("  engine V1 gross monthly SR IS:", round(sr(g.loc[:"2024-09"]), 3), " corr with crosscheck:",
      round(pd.concat([g, m.rename(lambda d: d + pd.offsets.MonthEnd(0))], axis=1).dropna().corr().iloc[0, 1], 3))
P = K.futures_panel([f"F_{r}" for r in K.FX])
c = P["ohlc"]["close"]
for wm in (1, 3, 12):
    m = monthly_ls(c, P["rf"], list(c.columns), wm, 2)
    print(f"fx {wm}m top2-bot2 monthly gross SR IS:", round(sr(m.loc["2011-07":"2024-09"]), 3), "later:", round(sr(m.loc["2024-10":]), 3))
held = pd.read_parquet(B / "trend_momentum_commodity_xsmom/variants/V2_12m_IV_held.parquet")
print("commodity V2 mean gross notional", round(held.abs().sum(axis=1).loc[:"2024-10-02"].mean(), 2))
for sid, var in (("trend_momentum_fx_xsmom", "V1_1m"), ("trend_momentum_basis_momentum", "V3_TS_sign"), ("trend_momentum_sector_rs", "V3_top3_minus_bot3")):
    h = pd.read_parquet(B / sid / "variants" / f"{var}_held.parquet")
    gs = h.abs().sum(axis=1).loc[:"2024-10-02"]
    print(sid, var, "gross notional mean", round(gs.mean(), 2), "max", round(gs.max(), 2))
