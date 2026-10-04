"""Time-series momentum on US Treasury futures only. See SPEC.md (pre-registered)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import bt_common as B  # noqa: E402

SID = "trend_momentum_bond_tsmom"
TK = ["F_ZT", "F_ZF", "F_ZN", "F_ZB", "F_UB"]
pan = B.Panel(TK)
pos = {d: i for i, d in enumerate(pan.idx)}
EX = pan.ex.to_numpy()


def cum(t, elig, k):
    i = pos[t]
    blk = pd.DataFrame(EX[i - k + 1:i + 1], columns=TK)[elig]
    ok = blk.notna().sum() >= k
    return ((1 + blk.fillna(0.0)).prod() - 1)[ok]


def v1(t, elig):
    return np.sign(cum(t, elig, 252))


def v2(t, elig):
    return pd.concat([np.sign(cum(t, elig, k)) for k in (21, 63, 252)], axis=1).mean(axis=1, skipna=False).dropna()


# Carver EWMAC on the excess-return index (back-adjusted price without T-bill drift)
I = B.excess_index(pan)
pvol = I.diff().ewm(span=35, min_periods=10).std()
def ewmac(f, s, scalar):
    raw = (I.ewm(span=f, min_periods=1).mean() - I.ewm(span=s, min_periods=1).mean()) / pvol
    return (raw * scalar).clip(-20, 20)
FC = (ewmac(16, 64, 3.75) + ewmac(64, 256, 1.87)) / 2.0 / 10.0


def v3(t, elig):
    return FC.loc[t, elig].dropna()


VARIANTS = {
    "V1": ("sign of 252-session excess return (MOP)", v1),
    "V2": ("mean of signs over 21/63/252 sessions", v2),
    "V3": ("Carver EWMAC16/64 + EWMAC64/256 (scalars 3.75/1.87, cap 20), /10", v3),
}
results = {}
for v, (desc, xf) in VARIANTS.items():
    diag = {}
    w = B.risk_unit_book(pan, xf, cols=TK, diag=diag)
    df, to, held = B.simulate3(w)
    rep = B.full_report(df, to, held)
    hm = held.loc[:B.IS_END]
    rep["diag"] = dict(diag, mean_abs_weight_IS={c: float(hm[c].abs().mean()) for c in TK},
                       mean_net_duration_sign_IS=float(np.sign(hm.sum(axis=1)).mean()))
    rep["desc"] = desc
    results[v] = rep
    B.save_series(SID, df, {"variant": v, "desc": desc}, folder=HERE / "variants", name=f"{SID}__{v}")
    print(v, desc, {k: round(rep["IS"][k], 3) for k in ("net_sharpe_1x", "net_sharpe_2x", "gross_sharpe", "ann_vol", "max_dd", "turnover_per_year", "mean_gross_leverage")},
          "LATER", round(rep["LATER"]["net_sharpe_1x"], 3), {k: (round(x, 2) if isinstance(x, float) else x) for k, x in rep["diag"].items() if k != "mean_abs_weight_IS"},
          {c: round(x, 2) for c, x in rep["diag"]["mean_abs_weight_IS"].items()})
B.jdump(results, HERE / "results.json")
