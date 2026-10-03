"""Point-in-time residual of addendum 3.3 (shared by positions and the permutation test)."""
from __future__ import annotations

import numpy as np
import pandas as pd

PREV_CHAIR = {"Powell": "Yellen", "Warsh": "Powell"}
SHRINK_W = 4.0
BURN_IN = 8


def pit_fit(df: pd.DataFrame, sig: str, extra: list[str] | None = None, prefix: str | None = None,
            sig_override: np.ndarray | None = None, only_idx=None) -> pd.DataFrame:
    """Expanding-window OLS s_j = alpha_chair + beta R_j (+ gamma q_j) on prior scheduled meetings with valid inputs.
    Intercept of the current chair is shrunk toward the preceding chair's with 4 pseudo-meetings."""
    extra = extra or []
    prefix = prefix or sig
    s_all = df[sig].values.astype(float) if sig_override is None else sig_override
    valid = (df.scheduled.values == 1) & np.isfinite(s_all) & np.isfinite(df.R_ZT.values)
    for c in extra:
        valid &= np.isfinite(df[c].values.astype(float))
    dates = df.date.values
    chairs = df.chair.values
    out = {k: np.full(len(df), np.nan) for k in ["nfit", "n_chair", "alpha_hat_c", "alpha_hat_prev",
                                                   "alpha_tilde", "beta", "shat", "resid", "pos"]}
    for i in (range(len(df)) if only_idx is None else only_idx):
        if not valid[i]:
            continue
        F = np.where(valid & (dates < dates[i]))[0]
        out["nfit"][i] = len(F)
        if len(F) < BURN_IN:
            continue
        cs = sorted(set(chairs[F]), key=lambda c: ["Yellen", "Powell", "Warsh"].index(c))
        X = np.column_stack([(chairs[F] == c).astype(float) for c in cs] +
                            [df.R_ZT.values[F]] + [df[c].values[F].astype(float) for c in extra])
        coef, *_ = np.linalg.lstsq(X, s_all[F], rcond=None)
        alpha = dict(zip(cs, coef[:len(cs)]))
        slopes = coef[len(cs):]
        c = chairs[i]
        n_c = int(np.sum(chairs[F] == c))
        prev = PREV_CHAIR.get(c)
        a_prev = alpha.get(prev, np.nan) if prev else np.nan
        if n_c == 0:
            a_t = a_prev
        elif prev is None or not np.isfinite(a_prev):
            a_t = alpha[c]
        else:
            a_t = (n_c * alpha[c] + SHRINK_W * a_prev) / (n_c + SHRINK_W)
        xr = np.array([df.R_ZT.values[i]] + [float(df[cc].values[i]) for cc in extra])
        shat = a_t + float(slopes @ xr)
        out["n_chair"][i] = n_c
        out["alpha_hat_c"][i] = alpha.get(c, np.nan)
        out["alpha_hat_prev"][i] = a_prev
        out["alpha_tilde"][i] = a_t
        out["beta"][i] = slopes[0]
        out["shat"][i] = shat
        out["resid"][i] = s_all[i] - shat
        out["pos"][i] = -np.sign(s_all[i] - shat)
    return pd.DataFrame({f"{prefix}__{k}": v for k, v in out.items()}, index=df.index)


