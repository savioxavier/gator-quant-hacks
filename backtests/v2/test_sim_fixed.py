"""Unit tests of the deviation D-4 simulators (sim_fixed.simulate and the fix-1 switch of v2lib.weights_E1).

    GQH_REPO=<gqh-flow-clock clone> python backtests/v2/test_sim_fixed.py     (or pytest, where installed)

Needs gqh-flow-clock's src.engine (for the comparison with the shared engine); no data cache, no market data.
1. The reviewer's example: $100, $50 in an asset that rises 10% intraday and then 10% overnight. Held as shares, the
   account is worth $110.50 at the next open; the engine gives $110.25 (it rebalances back to 50% at the close).
2. With no intraday moves, no T-bill and no costs the corrected simulator equals the engine exactly.
3. Random prices, long and short targets, T-bill, costs and borrow: the corrected simulator equals an explicit
   share-and-cash ledger (shares bought at the open, valued at the close and the next open), with the T-bill, borrow
   and trading costs booked as the engine books them.
4. Fix 1 (v2lib.weights_E1): off reproduces the committed code path; on, the vol for the position entered at the
   open of t no longer depends on the open-t price.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if os.environ.get("GQH_REPO"):
    sys.path.insert(0, os.environ["GQH_REPO"])

from src import engine as E  # noqa: E402  (gqh-flow-clock, read only)
import sim_fixed as SF  # noqa: E402
import v2lib as L  # noqa: E402


def _panel(opens: dict, closes: dict, idx) -> dict:
    o, c = pd.DataFrame(opens, index=idx), pd.DataFrame(closes, index=idx)
    return {"open": o, "close": c, "roll": pd.DataFrame(0.0, index=idx, columns=o.columns)}


def reviewer_example() -> dict:
    """Sessions 0, 1, 2. The 50% target is decided at the close of 0 and filled at the open of 1. Session 1: +10% open
    to close. Into session 2: +10% close to open, then flat. No T-bill, no costs."""
    idx = pd.bdate_range("2020-01-06", periods=3)
    ohlc = _panel({"TLT": [100.0, 100.0, 121.0]}, {"TLT": [100.0, 110.0, 121.0]}, idx)
    w = pd.DataFrame({"TLT": [0.5, 0.5, 0.5]}, index=idx)
    rf = pd.Series(0.0, index=idx)
    zero = {"TLT": 0.0}
    eng = E.simulate(w, ohlc, rf, exec="next_open", cost_bps=zero)
    fix = SF.simulate(w, ohlc, rf, exec="next_open", cost_bps=zero)
    out = {}
    for name, (net, _g, turn, _h, _c) in (("engine", eng), ("fixed", fix)):
        out[name] = {"value_at_session2": float(100.0 * (1 + net).prod()), "turnover_open2": float(turn.iloc[2])}
    # by hand: $50 buys 0.5 share at 100, $50 stays in cash; the share is worth 110 at the close and 121 at the open
    shares, cash = 50.0 / 100.0, 50.0
    out["by_hand_value_at_open2"] = cash + shares * 121.0
    return out


def test_reviewer_example():
    r = reviewer_example()
    assert abs(r["by_hand_value_at_open2"] - 110.50) < 1e-12
    assert abs(r["fixed"]["value_at_session2"] - 110.50) < 1e-9
    assert abs(r["engine"]["value_at_session2"] - 110.25) < 1e-9


def _random_case(seed: int, intraday: bool):
    rng = np.random.default_rng(seed)
    n = 400
    idx = pd.bdate_range("2018-01-01", periods=n)
    opens, closes = {}, {}
    for t in ("TLT", "UUP"):
        lvl, o, c = 100.0, [], []
        for _ in range(n):
            lvl *= 1 + rng.normal(0, 0.006)           # close -> open
            o.append(lvl)
            if intraday:
                lvl *= 1 + rng.normal(0, 0.008)       # open -> close
            c.append(lvl)
        opens[t], closes[t] = o, c
    ohlc = _panel(opens, closes, idx)
    w = pd.DataFrame(rng.uniform(-1.0, 1.0, (n, 2)), index=idx, columns=["TLT", "UUP"])
    w.iloc[::7] = w.shift(1).iloc[::7]                 # some unchanged targets
    rf = pd.Series(rng.uniform(0, 2e-4, n), index=idx)
    return ohlc, w, rf


def test_equals_engine_without_intraday_moves_rates_or_costs():
    ohlc, w, rf = _random_case(1, intraday=False)
    w = w.abs()                                        # long only: no borrow fee
    rf0 = rf * 0.0
    zero = {"TLT": 0.0, "UUP": 0.0}
    eng = E.simulate(w, ohlc, rf0, exec="next_open", cost_bps=zero)
    fix = SF.simulate(w, ohlc, rf0, exec="next_open", cost_bps=zero)
    assert float((eng[0] - fix[0]).abs().max()) < 1e-14
    assert float((eng[2] - fix[2]).abs().max()) < 1e-14


def share_ledger(ohlc, w_dec, rf, cost_bps):
    """Explicit dollars: shares bought at the open at the target fraction of the NAV at the open, valued at the close
    and the next open; the T-bill on the cash weight, the short borrow and the trading costs booked as the engine
    books them (fractions of the previous close's NAV)."""
    t = list(w_dec.columns)
    O, Cl = ohlc["open"][t].to_numpy(float), ohlc["close"][t].to_numpy(float)
    W = w_dec.shift(1).fillna(0.0).to_numpy(float)
    cb = np.array([cost_bps[x] for x in t]) / 1e4
    br = np.array([0.0 if E.C.is_future(x) else E.C.SHORT_BORROW_BPS_PER_YEAR for x in t]) / 1e4 / E.C.TRADING_DAYS
    RF = rf.to_numpy(float)
    shares, cash, v_prev = np.zeros(len(t)), 1.0, 1.0
    ret, turn = [], []
    for i in range(len(W)):
        v_open = cash + shares @ O[i]
        target = W[i] * v_open / O[i]
        frac = np.abs(target - shares) * O[i] / v_open
        cash -= (target - shares) @ O[i]
        shares = target
        cash += (1 - W[i].sum()) * RF[i] * v_prev - (frac @ cb) * v_prev - (np.abs(np.minimum(W[i], 0)) @ br) * v_prev
        v_close = cash + shares @ Cl[i]
        ret.append(v_close / v_prev - 1)
        turn.append(frac.sum())
        v_prev = v_close
    return pd.Series(ret, index=w_dec.index), pd.Series(turn, index=w_dec.index)


def test_equals_explicit_share_ledger():
    ohlc, w, rf = _random_case(2, intraday=True)
    cbp = {"TLT": 1.5, "UUP": 5.0}
    net, _g, turn, _h, _c = SF.simulate(w, ohlc, rf, exec="next_open", cost_bps=cbp)
    lr, lt = share_ledger(ohlc, w, rf, cbp)
    assert float((net - lr).abs().max()) < 1e-12
    assert float((turn - lt).abs().max()) < 1e-12
    eng = E.simulate(w, ohlc, rf, exec="next_open", cost_bps=cbp)
    assert float((eng[0] - lr).abs().max()) > 1e-6     # the engine is not a share ledger once prices move intraday


def test_fix1_switch():
    rng = np.random.default_rng(3)
    n = 300
    idx = pd.bdate_range("2019-01-01", periods=n)
    opens = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (n, 2)), axis=0)), index=idx, columns=["TLT", "UUP"])
    z = pd.Series(rng.normal(0, 1, n), index=idx)
    fomc = pd.Series(False, index=idx)
    ex = L.EXPRS["E1"]
    saved = os.environ.pop("V2_FIX_SIZING", None)
    try:
        w_def, a_def = L.weights_E1(z, opens, fomc, ex)
        w_off, a_off = L.weights_E1(z, opens, fomc, ex, fix_sizing=False)
        w_on, a_on = L.weights_E1(z, opens, fomc, ex, fix_sizing=True)
    finally:
        if saved is not None:
            os.environ["V2_FIX_SIZING"] = saved
    assert w_def.equals(w_off) and a_def.equals(a_off)
    # perturb the open of session t: the fixed vol for the entry at t (a_on['vol_entry'] at decision t-1) is unchanged
    t = 200
    o2 = opens.copy()
    o2.iloc[t] *= 1.05
    _, b_on = L.weights_E1(z, o2, fomc, ex, fix_sizing=True)
    _, b_off = L.weights_E1(z, o2, fomc, ex, fix_sizing=False)
    assert b_on["vol_entry"].iloc[t - 1] == a_on["vol_entry"].iloc[t - 1]
    assert b_off["vol_entry"].iloc[t - 1] != a_off["vol_entry"].iloc[t - 1]


if __name__ == "__main__":
    r = reviewer_example()
    print("reviewer example ($100, $50 in the asset, +10% intraday, +10% overnight):")
    print(f"  by hand (shares and cash): ${r['by_hand_value_at_open2']:.2f}")
    print(f"  corrected simulator:       ${r['fixed']['value_at_session2']:.2f} (turnover at that open "
          f"{r['fixed']['turnover_open2']:.6f})")
    print(f"  shared engine:             ${r['engine']['value_at_session2']:.2f} (turnover at that open "
          f"{r['engine']['turnover_open2']:.6f})")
    for f in (test_reviewer_example, test_equals_engine_without_intraday_moves_rates_or_costs,
              test_equals_explicit_share_ledger, test_fix1_switch):
        f()
        print(f"PASS {f.__name__}")
