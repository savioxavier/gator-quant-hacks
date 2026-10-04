"""Compare the independent implementation with the module + engine (all engine runs logged)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, "<solo-repo>")
sys.path.insert(0, str(HERE))

import xcheck as X  # noqa: E402  (runs the independent implementation)
from src import engine as E  # noqa: E402
from src.strategies import pct as P  # noqa: E402

def sr(x):
    return float(x.mean() / x.std() * math.sqrt(252))

w_mod, panel, diag = P.decision_weights("IS", return_panel=True)
ohlc, rf = P._data("IS", tuple(P.TICKERS))
mu0_m, sd0_m = P.null_moments(63, 4)
print(f"module null mu0={mu0_m:.5f} sd0={sd0_m:.5f}")

# my weights with the module's null moments -> should match to float precision
W_same = pd.DataFrame(np.nan, index=X.cal, columns=X.TICK)
zs = []
for T in X.dec_dates:
    w, g = X.weights_at(T, mu0_m, sd0_m)
    if w is None:
        continue
    W_same.loc[T] = w.values
    g = g.assign(date=T)
    zs.append(g)
W_same = W_same.ffill().fillna(0.0)
zz = pd.concat(zs).rename_axis("ticker").reset_index()
mp = panel.merge(zz, on=["date", "ticker"], suffixes=("_mod", "_x"))
print("panel rows module/indep/merged:", len(panel), len(zz), len(mp))
for c in ("s", "vol", "z", "m"):
    print(f"  max |{c}_mod - {c}_x| = {np.abs(mp[c + '_mod'] - mp[c + '_x']).max():.3e}")
print("max |w_mod - w_indep(same null)| =", float((w_mod - W_same.reindex_like(w_mod)).abs().max().max()))
print("max |w_mod - w_indep(own null)|  =", float((w_mod - X.W_dec.reindex_like(w_mod)).abs().max().max()))

base_params = {**P.BASE_PARAMS, "tickers": list(P.TICKERS), "mc_paths": P.MC_PATHS, "mc_seed": P.MC_SEED,
               "variant": "base"}
r1 = E.run_backtest("PCT_base", P.FAMILY, w_mod, ohlc, rf, "IS", params=base_params, exec=P.EXEC, cost_mult=1.0,
                    log=True, note="adversarial review: reproduce base")
r0 = E.run_backtest("PCT_base", P.FAMILY, w_mod, ohlc, rf, "IS", params=base_params, exec=P.EXEC, cost_mult=0.0,
                    log=True, note="adversarial review: cost_mult=0 cross-check")
rx = E.run_backtest("PCT_base_xcheck_independent", P.FAMILY, X.W_dec, ohlc, rf, "IS",
                    params={"variant": "independent re-implementation (own MC null seed 12345, 100k)"},
                    exec=P.EXEC, cost_mult=0.0, log=True,
                    note="adversarial review: independent weights, gross cross-check (cost_mult=0, not a trial)")
rfi = rf.reindex(r1.gross_returns.index).ffill().fillna(0.0)
g_mod = r1.gross_returns - rfi
print(f"\nmodule+engine base net SR (1x) = {r1.stats['sharpe']:.4f}   [json 0.30097]")
print(f"module+engine base GROSS SR     = {sr(g_mod):.4f}  ann mean ex gross = {g_mod.mean()*252:.5f}")
print(f"engine cost_mult=0 SR (borrow still charged) = {r0.stats['sharpe']:.4f}")
gx = rx.gross_returns - rf.reindex(rx.gross_returns.index).ffill().fillna(0.0)
print(f"engine GROSS SR on independent weights = {sr(gx):.4f}")
gs = X.gs
ex_s = gs - X.rf.loc[gs.index]
print(f"independent simple daily GROSS SR       = {sr(ex_s):.4f}")
common = g_mod.index.intersection(ex_s.index)
diff = (g_mod.loc[common] - ex_s.loc[common])
print(f"daily gross diff engine vs simple: mean {diff.mean()*252:.6f}/yr, max abs {diff.abs().max():.2e}, "
      f"corr {np.corrcoef(g_mod.loc[common], ex_s.loc[common])[0,1]:.6f}")
costs_ann = r1.costs.mean() * 252
print(f"mean cost drag (1x) = {costs_ann:.5f}/yr ; turnover/yr = {r1.stats['turnover_per_year']:.2f}")
borrow = (r1.weights.clip(upper=0).abs() * 30e-4 / 252).sum(axis=1).mean() * 252
print(f"of which borrow = {borrow:.5f}/yr")
# share of turnover on decision days vs drift rebalancing
dec_next = set(w_mod.index[w_mod.diff().abs().sum(axis=1) > 0] )
turn = r1.turnover
on_dec = turn[[i for i, d in enumerate(turn.index) if False]] if False else None
tr_days = pd.Series([E.trading_calendar("IS").get_loc(d) for d in turn.index], index=turn.index)
cal = E.trading_calendar("IS")
dec_trade_days = set(cal[cal.get_indexer(sorted(dec_next)) + 1])
mask = turn.index.isin(list(dec_trade_days))
print(f"turnover/yr on decision-trade days = {turn[mask].sum()/r1.stats['years']:.2f}, drift days = {turn[~mask].sum()/r1.stats['years']:.2f}")
