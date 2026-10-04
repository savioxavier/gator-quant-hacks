"""Cross-sectional 12-1 momentum within futures asset classes (Asness-Moskowitz-Pedersen). See SPEC.md (pre-registered)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import bt_common as B  # noqa: E402

SID = "trend_momentum_xsmom_futures_amp"
pan = B.Panel()
I = B.excess_index(pan)
pos = {d: i for i, d in enumerate(pan.idx)}


def signal(t, elig, voladj=False):
    i = pos[t]
    a, b = pan.idx[i - 252], pan.idx[i - 21]
    s = (I.loc[b, elig] / I.loc[a, elig] - 1).dropna()
    if voladj:
        s = s / pan.vol.loc[t, s.index]
    return s


def rank_weights(s: pd.Series) -> pd.Series:
    """AMP eq. 1: rank minus mean rank, scaled to one unit long and one unit short."""
    r = s.rank(method="average")
    w = r - r.mean()
    g = w.abs().sum()
    return w * (2.0 / g) if g > 0 else w * 0.0


def build(variant, diag):
    w_dec = pd.DataFrame(np.nan, index=pan.idx, columns=pan.tickers)
    caps = n = 0
    for t in pan.me:
        elig = pan.eligible(t)
        w = pd.Series(0.0, index=pan.tickers)
        hist = pan.ex.loc[:t]
        if elig:
            if variant == "V3":
                s = signal(t, elig)
                if len(s) >= 2:
                    w[s.index] = rank_weights(s)
            else:
                for cls, members in B.CLASSES.items():
                    e = [c for c in members if c in elig]
                    s = signal(t, e, voladj=(variant == "V2")) if e else pd.Series(dtype=float)
                    if len(s) < 2:
                        continue
                    sl = pd.Series(0.0, index=pan.tickers)
                    sl[s.index] = rank_weights(s)
                    w += B.book_to_target(sl, hist, gross_cap=np.inf)     # each class sleeve at 10% ex-ante
            if (w != 0).any():
                unc = B.book_to_target(w, hist, gross_cap=np.inf)
                w = B.book_to_target(w, hist)
                n += 1
                caps += int(unc.abs().sum() > B.GROSS_CAP + 1e-9)
        w_dec.loc[t] = w.values
    diag["months"] = n
    diag["gross_cap_binding_frac"] = caps / max(n, 1)
    return w_dec.ffill().fillna(0.0)


VARIANTS = {
    "V1": "class-neutral rank of raw 12-1 excess return, equal ex-ante class risk",
    "V2": "class-neutral rank of vol-adjusted 12-1 return, equal ex-ante class risk",
    "V3": "pooled rank across all 30 (no class neutrality), notional rank weights",
}
results = {}
for v, desc in VARIANTS.items():
    diag = {}
    w = build(v, diag)
    df, to, held = B.simulate3(w)
    rep = B.full_report(df, to, held)
    hm = held.loc[:B.IS_END]
    rep["diag"] = dict(diag, mean_abs_weight_by_class_IS={k: float(hm[m].abs().sum(axis=1).mean()) for k, m in B.CLASSES.items()})
    rep["desc"] = desc
    results[v] = rep
    B.save_series(SID, df, {"variant": v, "desc": desc}, folder=HERE / "variants", name=f"{SID}__{v}")
    print(v, desc, {k: round(rep["IS"][k], 3) for k in ("start", "net_sharpe_1x", "net_sharpe_2x", "gross_sharpe", "ann_vol", "max_dd", "turnover_per_year", "mean_gross_leverage") if k != "start"},
          rep["IS"]["start"], "LATER", round(rep["LATER"]["net_sharpe_1x"], 3), diag)
B.jdump(results, HERE / "results.json")
