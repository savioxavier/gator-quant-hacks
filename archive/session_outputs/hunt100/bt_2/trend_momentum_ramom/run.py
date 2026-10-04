"""RAMOM (Dudler-Gmuer-Malamud) on 30 CME futures. See SPEC.md (pre-registered)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import bt_common as B  # noqa: E402

SID = "trend_momentum_ramom"
pan = B.Panel()
pos = {d: i for i, d in enumerate(pan.idx)}
EX = pan.ex.to_numpy()


def z_at(t, elig, L):
    i = pos[t]
    blk = pd.DataFrame(EX[i - L + 1:i + 1], columns=pan.tickers)[elig]
    ok = blk.notna().sum() >= L
    s = blk.sum()
    sd = blk.std(ddof=1)
    z = s / (sd * np.sqrt(L))
    return z[ok & (sd > 0)]


def ramom_x(Ls):
    def xf(t, elig):
        xs = [np.clip(z_at(t, elig, L) / 2.0, -1, 1) for L in Ls]
        df = pd.concat(xs, axis=1)
        return df.mean(axis=1, skipna=False).dropna()   # require every look-back to be available
    return xf


def sign_x(t, elig):
    i = pos[t]
    blk = pd.DataFrame(EX[i - 251:i + 1], columns=pan.tickers)[elig]
    ok = blk.notna().sum() >= 252
    cum = (1 + blk.fillna(0.0)).prod() - 1
    return np.sign(cum)[ok]


VARIANTS = {
    "V1": ("RAMOM L=252, x=clip(t-stat/2,-1,1)", ramom_x([252])),
    "V2": ("RAMOM L=63", ramom_x([63])),
    "V3": ("RAMOM average of x over L in {21,63,126,252}", ramom_x([21, 63, 126, 252])),
    "DIAG_TSMOM252": ("diagnostic (not a variant): MOP sign of 252-session excess return", sign_x),
}
results = {}
for v, (desc, xf) in VARIANTS.items():
    diag = {}
    w = B.risk_unit_book(pan, xf, diag=diag)
    df, to, held = B.simulate3(w)
    rep = B.full_report(df, to, held)
    # dollar turnover from monthly decision changes only (excludes rolls and daily drift): mean |dw| at month-ends
    wm = w.loc[pan.me].loc[: B.IS_END]
    wm = wm.loc[wm.abs().sum(axis=1).gt(0).idxmax():]          # live decisions only
    rep["diag"] = dict(diag, decision_turnover_per_year=float(wm.diff().abs().sum(axis=1).iloc[1:].mean() * 12),
                       mean_gross_at_decision=float(wm.abs().sum(axis=1).mean()),
                       first_decision=str(wm.index[0].date()))
    rep["desc"] = desc
    results[v] = rep
    B.save_series(SID, df, {"variant": v, "desc": desc}, folder=HERE / "variants", name=f"{SID}__{v}")
    print(v, desc, {k: round(rep["IS"][k], 3) for k in ("net_sharpe_1x", "net_sharpe_2x", "gross_sharpe", "ann_vol", "max_dd", "turnover_per_year")},
          "LATER", round(rep["LATER"]["net_sharpe_1x"], 3), rep["diag"])
B.jdump(results, HERE / "results.json")
