import sys, math, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
sys.path.insert(0, "<solo-repo>")
V = "<scratch>/edges/"
OUT = V + "verify_carry/"
START, ISEND, LSTART = "2011-09-02", "2024-10-02", "2024-10-03"


def sr(x):
    x = x.dropna()
    return x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else np.nan


def mdd(x):
    e = (1 + x.fillna(0)).cumprod()
    return (e / e.cummax() - 1).min()


def nw(x):
    x = x.dropna().values
    n = len(x); L = int(4 * (n / 100) ** (2 / 9)); e = x - x.mean(); s = e @ e / n
    for k in range(1, L + 1):
        s += 2 * (1 - k / (L + 1)) * (e[k:] @ e[:-k]) / n
    return x.mean() / math.sqrt(s / n)


res = pd.read_pickle(OUT + "v_results.pkl")
tab = pd.read_csv(V + "carry/carry_all_variants.csv")
an = tab[tab.window.isin(["IS", "LATER"])].pivot_table(index="series", columns="window", values="sharpe_net_1x")
rows = []
for (lagx, sn, fq, cons, b), (df, to, gn) in res.items():
    IS = df.loc[START:ISEND]; L = df.loc[LSTART:]
    yrs = len(IS) / 252
    key = f"{cons}_{b}_{sn}_{fq}"
    row = dict(lag=lagx, series=key, IS_1x=sr(IS.net_1x), IS_2x=sr(IS.net_2x), IS_g=sr(IS.gross), IS_mdd=mdd(IS.net_1x),
               IS_vol=IS.net_1x.std() * math.sqrt(252), nw_t=nw(IS.net_1x), LATER_1x=sr(L.net_1x),
               pre_pub=sr(df.loc[START:"2013-07-31"].net_1x), post_pub=sr(df.loc["2013-08-01":ISEND].net_1x),
               turn=to.loc[START:ISEND].sum() / yrs, gross_notional=gn.loc[START:ISEND].mean())
    if lagx == 0 and key in an.index:
        row["an_IS_1x"] = an.loc[key, "IS"]; row["an_LATER_1x"] = an.loc[key, "LATER"]
    rows.append(row)
t = pd.DataFrame(rows)
t.to_csv(OUT + "verify_table.csv", index=False)
pd.set_option("display.width", 250)
print(t[t.lag == 0].sort_values("series").round(3).to_string(index=False))
print()
print("lag sensitivity (monthly):")
p = t[t.series.str.endswith("_M")].pivot_table(index="series", columns="lag", values="IS_1x").round(3)
print(p.to_string())

# daily correlation of my series vs the analyst's saved series
names = {"XS_global_C1_M": "carry_xs_global", "TS_global_C1_M": "carry_ts_global"}
for b in ["fx", "rates", "comm", "eq"]:
    names[f"XS_{b}_C1_M"] = f"carry_xs_{b}"; names[f"TS_{b}_C1_M"] = f"carry_ts_{b}"
print()
for k, n in names.items():
    cons, b, sn, fq = k.split("_")
    mine = res[(0, sn, fq, cons, b)][0]
    a = pd.read_parquet(V + f"series/{n}.parquet")
    j = pd.concat([mine.net_1x.rename("m"), a.net_1x.rename("a")], axis=1, join="inner").loc[START:ISEND]
    print(f"{n:18s} corr {j.m.corr(j.a):.4f}  mine {sr(j.m):.3f}  theirs {sr(j.a):.3f}")
