"""G3 operating characteristics for the H1-primary decision rule (simulation only; no market or text data used).

Rule: per-meeting gross P&L Y_m = sign(s_m) * r_m (signal-aligned), GO iff mean(Y) > 0 and the one-sided
studentised sign-flip (Rademacher wild) bootstrap p <= 0.05. (s, r) bivariate with correlation rho; r either
Gaussian or Student-t(4) (heavy tails). Reports false-GO rate (rho = 0) and power.
"""
import numpy as np, json, sys
rng = np.random.default_rng(20261003)
B, NSIM = 1999, 4000

def tstat(Y):
    n = Y.shape[-1]; m = Y.mean(-1); s = Y.std(-1, ddof=1)
    return m / (s / np.sqrt(n))

def go(Y):
    t0 = tstat(Y)
    if not (Y.mean() > 0): return False
    W = rng.choice([-1.0, 1.0], size=(B, Y.size))
    tb = tstat(W * Y)
    p = (1 + np.sum(tb >= t0)) / (B + 1)
    return p <= 0.05

out = {}
for n in (20, 18, 27):
    for tails in ("gauss", "t4"):
        for rho in (0.0, 0.1, 0.2, 0.3, 0.47):
            hits = 0
            for _ in range(NSIM):
                x = rng.standard_normal(n)
                if tails == "gauss":
                    e = rng.standard_normal(n)
                else:
                    e = rng.standard_t(4, n) / np.sqrt(2.0)  # unit variance
                r = rho * x * (1.0 if tails == "gauss" else 1.0) + np.sqrt(1 - rho**2) * e
                Y = np.sign(x) * r
                hits += go(Y)
            out[f"n={n} {tails} rho={rho}"] = round(hits / NSIM, 3)
            print(f"n={n:2d} {tails:5s} rho={rho:4.2f}  P(GO)={hits/NSIM:.3f}", flush=True)
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "g3_oc.json", "w"), indent=1)
