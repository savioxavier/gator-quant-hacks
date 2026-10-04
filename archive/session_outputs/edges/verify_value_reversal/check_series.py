"""Recompute stats from the analyst's saved series files and compare with the independent series."""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

E = Path(__file__).resolve().parents[1]
SER = E / "series"
OUT = Path(__file__).resolve().parent
IS_END = pd.Timestamp("2024-10-02")
LAT0 = pd.Timestamp("2024-10-03")
mine = pd.read_pickle(OUT / "indep_series.pkl")
D = Path("<home>/.cache/gqh")

# own ES excess and S1/F2 from analyst bench (S1/F2 come from frozen repo code)
fu = pd.read_parquet(D / "futures_daily.parquet")
fu["date"] = pd.to_datetime(fu["date"])
es = fu[fu.ticker == "F_ES"].set_index("date")["close"].pct_change(fill_method=None)
rfd = pd.read_parquet(D / "rf_daily.parquet")
rfd = rfd.set_index(pd.to_datetime(rfd["date"])) if "date" in rfd.columns else rfd
es = es - rfd["rf"].reindex(es.index).ffill()
bench = pd.read_parquet(E / "value_reversal" / "bench_excess.parquet")


def sr(x):
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(252))


def mdd(x):
    e = (1 + x).cumprod()
    return float((e / e.cummax() - 1).min())


MAP = {"VAL_XS_VW1": "VW1", "VAL_XS_VW2": "VW2", "VAL_XS_VW3": "VW3", "MOM_XS": "MOM_XS", "COMBO_XS": "COMBO_XS",
       "VAL_ALL": "VAL_ALL", "COMBO_ALL": "COMBO_ALL", "BOND_B1": "B1", "BOND_B2": "B2", "BOND_B1_IEF": None}
rows = []
for a, m in MAP.items():
    f = pd.read_parquet(SER / f"value_reversal_{a}.parquet")
    side = json.loads((SER / f"value_reversal_{a}.json").read_text())
    isw = f.loc[:IS_END]
    lat = f.loc[LAT0:]
    row = dict(cand=a, first=str(f.index[0].date()), last=str(f.index[-1].date()), n=len(f),
               nan=int(f.isna().sum().sum()),
               is_sr1=sr(isw.net_1x), is_sr2=sr(isw.net_2x), is_srg=sr(isw.gross), is_mdd=mdd(isw.net_1x),
               lat_sr1=sr(lat.net_1x), ann_vol_is=float(isw.net_1x.std() * math.sqrt(252)),
               side_is=side.get("in_sample"),
               c_es=float(pd.concat([isw.net_1x, es], axis=1).dropna().corr().iloc[0, 1]),
               c_s1=float(pd.concat([isw.net_1x, bench["S1"]], axis=1).dropna().corr().iloc[0, 1]),
               c_f2=float(pd.concat([isw.net_1x, bench["F2"]], axis=1).dropna().corr().iloc[0, 1]))
    if m is not None:
        key = ("spec_v0", m)
        mm = mine[key].loc[f.index]
        row["corr_with_mine"] = float(np.corrcoef(mm.net_1x, f.net_1x)[0, 1])
        row["maxabs_diff_net1x"] = float((mm.net_1x - f.net_1x).abs().max())
    rows.append(row)
tab = pd.DataFrame(rows)
pd.set_option("display.width", 250)
print(tab.drop(columns=["side_is"]).round(4).to_string(index=False))
tab.to_csv(OUT / "series_check.csv", index=False)

# own bootstrap with a different seed and block length; Sharpe standard errors
def boot(a, b, block, seed, n=5000):
    df = pd.concat([a, b], axis=1).dropna().to_numpy()
    T = len(df)
    rng = np.random.default_rng(seed)
    nb = math.ceil(T / block)
    out = np.empty(n)
    for i in range(n):
        idx = ((rng.integers(0, T, nb)[:, None] + np.arange(block)) % T).ravel()[:T]
        s = df[idx]
        q = s.mean(0) / s.std(0, ddof=1) * math.sqrt(252)
        out[i] = q[0] - q[1]
    return float((out <= 0).mean()), [float(np.quantile(out, .05)), float(np.quantile(out, .95))]


st = pd.Timestamp("2016-01-05")
c = mine[("spec_v0", "COMBO_XS")].net_1x.loc[st:IS_END]
mo = mine[("spec_v0", "MOM_XS")].net_1x.loc[st:IS_END]
ca = mine[("spec_v0", "COMBO_ALL")].net_1x.loc[st:IS_END]
print("boot COMBO_XS vs MOM block 21 seed 11:", boot(c, mo, 21, 11), "block 126:", boot(c, mo, 126, 3))
print("boot COMBO_ALL vs MOM block 21:", boot(ca, mo, 21, 11))
for name, s in (("COMBO_ALL", ca), ("COMBO_XS", c)):
    yrs = len(s) / 252
    S = sr(s)
    print(name, "SR", round(S, 3), "SE", round(math.sqrt((1 + S * S / 2) / yrs), 3))

# extra-lag test (one extra session of delay) on the primary and best rows: a large drop would flag timing sensitivity
for key in [("spec_v0", "VW1"), ("spec_v0", "COMBO_ALL")]:
    print(key, "net_1x vs drift version corr", round(float(mine[key][["net_1x", "net_1x_drift"]].loc[st:].corr().iloc[0, 1]), 4))
