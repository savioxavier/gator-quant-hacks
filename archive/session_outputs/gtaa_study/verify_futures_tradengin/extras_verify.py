"""Extra checks: vol-matched drawdowns, execution-lag dispersion, timing-term uncertainty, 2008, EWMAC turnover."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import mylib as M
import verify as Vf   # reuses the already-built series (re-runs verify.py once)

V, rf, cal = Vf.V, Vf.rf, Vf.cal


def volmatch(k, target, win):
    x = (V[k][0] - rf).loc[win[0]:win[1]]
    s = target / (x.std() * math.sqrt(252))
    net = rf.loc[x.index] + s * x
    return s, M.mdd(net)


print("\n--- vol-matched max DD (scaled excess + T-bill)")
for win, pairs in ((M.IS_F, [("C1", "C3"), ("S3", "BH5"), ("B1", "A1")]), (M.IS_E, [("S3", "BH5")])):
    for a, b in pairs:
        vb = (V[b][0] - rf).loc[win[0]:win[1]].std() * math.sqrt(252)
        print(win, a, "at", b, "vol %.3f" % vb, "-> mdd a %.3f" % volmatch(a, vb, win)[1],
              "mdd b %.3f" % volmatch(b, vb, win)[1], "| both at 10%%: a %.3f b %.3f" % (volmatch(a, .1, win)[1], volmatch(b, .1, win)[1]))

print("\n--- C1 execution lag dispersion (IS_F Sharpe)")
W = Vf.W_C1
for lag in (-1, 0, 1, 2, 3, 5, 10):
    Wl = W.shift(lag).ffill().fillna(0) if lag >= 0 else W.shift(lag).ffill()
    net, *_ = M.sim_next_close(Wl, Vf.fc, rf, M.FCOST, Vf.fp["roll"])
    print("extra lag", lag, "sharpe IS %.3f" % M.sharpe((net - rf).loc[M.IS_F[0]:M.IS_F[1]]),
          "OOS %.3f" % M.sharpe((net - rf).loc[M.OOS[0]:M.OOS[1]]))
# bootstrap the same-close minus next-close difference
X = pd.DataFrame({"same": V["C1_sameclose"][0] - rf, "base": V["C1"][0] - rf}).loc[M.IS_F[0]:M.IS_F[1]]
S = M.block_boot(X, 63, 3000, 7)
d = S[:, 0] - S[:, 1]
print("same-close minus next-close IS: %.3f CI %.3f..%.3f" % (M.sharpe(X.same) - M.sharpe(X.base), *np.percentile(d, [2.5, 97.5])))

print("\n--- S3 timing term uncertainty (monthly-block bootstrap of Cov(w,r))")
for win in (M.IS_F, M.IS_E):
    H = V["S3"][3].loc[win[0]:win[1]]
    R = Vf.ep["close"].pct_change(fill_method=None).sub(rf, axis=0).loc[win[0]:win[1]].fillna(0)
    Hn, Rn = H.to_numpy(), R.to_numpy()
    n = len(Hn)
    rng = np.random.default_rng(3)
    tim = []
    for _ in range(2000):
        st = rng.integers(0, n, size=n // 63 + 1)
        idx = ((st[:, None] + np.arange(63)) % n).ravel()[:n]
        h, r = Hn[idx], Rn[idx]
        tim.append(((h * r).sum(1).mean() - (h.mean(0) * r.mean(0)).sum()) * 252)
    tot = (Hn * Rn).sum(1).mean() * 252
    tpt = tot - (Hn.mean(0) * Rn.mean(0)).sum() * 252
    print(win, "timing %.4f, 95%% CI %.4f..%.4f" % (tpt, *np.percentile(tim, [2.5, 97.5])))

print("\n--- yearly excess 2008 / 2022")
for k in ("S3", "BH5", "LS5", "S1", "B1", "E1", "C1"):
    x = (V[k][0] - rf)
    y = (1 + x).groupby(x.index.year).prod() - 1
    print(k, {yr: round(float(y.get(yr, np.nan)), 3) for yr in (2008, 2014, 2019, 2022)})

print("\n--- simple Carver EWMAC (published fixed scalars), turnover split trade vs roll")
ex, fc, fp = Vf.ex, Vf.fc, Vf.fp
px = (1 + ex.fillna(0)).cumprod()
sd = ex.ewm(span=32, min_periods=32).std()
sd = 0.7 * sd + 0.3 * sd.rolling(252, min_periods=60).mean()
scal = {(2, 8): 10.6, (4, 16): 7.5, (8, 32): 5.3, (16, 64): 3.75, (32, 128): 2.65, (64, 256): 1.87}
fcs = [((px.ewm(span=f, min_periods=s).mean() - px.ewm(span=s, min_periods=s).mean()) / (sd * px) * k).clip(-20, 20)
       for (f, s), k in scal.items()]
comb = (sum(fcs) / len(fcs) * 1.26).clip(-20, 20)
ok = Vf.traded & sd.notna() & (ex.notna().cumsum() >= 300)
n = ok.sum(axis=1).replace(0, np.nan)
avg = (0.20 / (sd * math.sqrt(252))).mul(2.5 / n, axis=0)
tgt = (comb / 10 * avg).where(ok, 0).fillna(0)
T, A = tgt.to_numpy(), avg.fillna(0).to_numpy()
cur = np.zeros(T.shape[1]); out = np.zeros_like(T)
for i in range(len(T)):
    b = 0.1 * np.abs(A[i]); cur = np.clip(cur, T[i] - b, T[i] + b); cur = np.where(T[i] == 0, 0, cur); out[i] = cur
Wb = pd.DataFrame(out, index=tgt.index, columns=tgt.columns)
for nm, Wx in (("slow_buffered", Wb), ("slow_unbuffered", tgt)):
    net, gross, turn, H = M.sim_next_close(Wx, fc, rf, M.FCOST, fp["roll"])
    _, _, turn_noroll, _ = M.sim_next_close(Wx, fc, rf, M.FCOST, None)
    sl = slice(*M.IS_F)
    yrs = len(net.loc[sl]) / 252
    print(nm, "IS net %.3f gross %.3f vol %.3f turnover/yr %.0f (roll part %.0f) avg gross lev %.2f" % (
        M.sharpe((net - rf).loc[sl]), M.sharpe((gross - rf).loc[sl]), net.loc[sl].std() * math.sqrt(252),
        turn.loc[sl].sum() / yrs, (turn - turn_noroll).loc[sl].sum() / yrs, H.abs().sum(1).loc[sl].mean()))
