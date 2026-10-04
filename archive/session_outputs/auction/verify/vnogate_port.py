import sys, math, importlib.util; sys.path.insert(0, r"<scratch>/auction/verify")
import numpy as np, pandas as pd, vstrat as S, vdata as V
sl = {m: S.sleeve(S.evsel([m], True), S.INST[m], None, 10, 10, False, 30.0 / S.DUR[S.INST[m]]) for m in S.TRADED}
held = S.combine(sl); _, s = S.stats_of(held); auc = pd.DataFrame(s)
spec = importlib.util.spec_from_file_location("cb", V.SP / "edges" / "combine" / "combine.py"); CB = importlib.util.module_from_spec(spec); spec.loader.exec_module(CB)
ccal, crf, csl, *_ = CB.load()
sleeves = {n: csl[n].rename(columns={"net_1x": "n1", "net_2x": "n2"}) for n in ["rpm_ES_MM", "CAL_TSY_ME_ZN", "S1"]}
def er(sv):
    X = pd.DataFrame({n: s["n1"] for n, s in sv.items()}).reindex(ccal); cnt = X.notna().cumsum()
    m = pd.DataFrame(np.nan, index=ccal, columns=list(sv))
    for d in pd.Series(ccal, index=ccal).groupby(ccal.to_period("M")).max():
        live = [n for n in sv if cnt.loc[d, n] >= 126]
        if not live: continue
        Sg = X.loc[:d, live].tail(252).cov(min_periods=63).fillna(0).to_numpy() * 252
        w = np.ones(len(live)) / len(live); m.loc[d] = 0.0; m.loc[d, live] = w * 0.06 / math.sqrt(w @ Sg @ w)
    m = m.ffill().shift(2); st = m.notna().any(axis=1); m = m.fillna(0)
    return {c: sum(m[n] * sv[n][c].reindex(ccal).fillna(0) for n in sv).where(st) for c in ("n1", "n2")}
c = er(sleeves); p = er({**sleeves, "AUC": auc})
for wn in ("sel", "val", "full", "later", "pre14", "post14"):
    a, b = S.W[wn]; a = max(pd.Timestamp(a), pd.Timestamp("2011-08-02"))
    print(wn, "core", round(S.sharpe(c["n1"][a:b]), 3), "core+V3_nogate", round(S.sharpe(p["n1"][a:b]), 3), "2x", round(S.sharpe(c["n2"][a:b]), 3), round(S.sharpe(p["n2"][a:b]), 3))
