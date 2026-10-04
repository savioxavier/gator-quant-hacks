"""Independent recomputation of hourly intraday momentum (ES, ZN) straight from the raw Databento hourly file.
Price-level construction: for each NYSE day d the traded contract is the front (.v.0) contract of the bar starting
(H-1):00 ET on d; every price used for that day (previous close, ONFH end, ROD end, LH end) is THAT contract's own
close, taken from .v.0 or .v.1 rows. No compounding of a chained series, so no cross-roll return is possible.
"""
import os
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

OUT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("GQH_DATA_DIR", "<home>/.cache/gqh"))
IS_END, LATER_START, LATER_END = pd.Timestamp("2024-10-02"), pd.Timestamp("2024-10-03"), pd.Timestamp("2026-10-02")
PUB = pd.Timestamp("2018-01-01")
COST = {"ES": 1e-4, "ZN": 1.5e-4}
RNG = np.random.default_rng(7)
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


raw = pd.read_parquet(DATA / "databento_raw/glbx_ohlcv1h_v01_es_zn.parquet")
raw["root"] = raw.symbol.str[:2]
raw["leg"] = raw.symbol.str[-1].astype(int)
raw["start_et"] = raw.ts_event.dt.tz_convert("America/New_York")
chk = raw[(raw.root == "ES") & (raw.leg == 0) & (raw.start_et.dt.hour == 15)]
log("UTC hours of 15:00 ET bar starts:", chk.ts_event.dt.hour.value_counts().to_dict())
raw["start_wc"] = raw.start_et.dt.tz_localize(None).astype("datetime64[ns]")

spy = pd.read_parquet(DATA / "etf_daily.parquet")
nyse = pd.DatetimeIndex(sorted(pd.to_datetime(spy[spy.ticker == "SPY"].date).unique())).astype("datetime64[ns]")
nyse = nyse[(nyse >= "2010-06-07") & (nyse <= LATER_END)]
prev_day = pd.Series(nyse[:-1], index=nyse[1:])


def build(root, H, O):
    r = raw[raw.root == root]
    px = (r.sort_values("leg").drop_duplicates(["instrument_id", "start_wc"])
          .set_index(["instrument_id", "start_wc"]).close.sort_index())
    series_by = {i: s.droplevel(0) for i, s in px.groupby(level=0)}
    front = r[r.leg == 0].set_index("start_wc").instrument_id
    rows = []
    for d in nyse[1:]:
        t_lh = d + pd.Timedelta(hours=H - 1)  # traded bar START (it ends at H:00)
        if t_lh not in front.index:
            continue
        i = int(front.loc[t_lh])
        series = series_by[i]
        pdv = prev_day[d]

        def at(ts):
            return float(series.get(ts, np.nan))

        p_lh_end = at(t_lh)  # close of bar starting H-1 = price at H:00
        p_sig = at(t_lh - pd.Timedelta(hours=1))  # close of bar starting H-2 = price at (H-1):00, entry
        p_open = at(d + pd.Timedelta(hours=O - 1))  # price at O:00
        p_prev = at(pdv + pd.Timedelta(hours=H - 1))  # previous NYSE day's price at H:00
        lo, hi = pdv + pd.Timedelta(hours=H - 1), t_lh - pd.Timedelta(hours=1)
        w = series[(series.index > lo) & (series.index <= hi)]
        if np.isfinite(p_prev) and len(w):
            lr = np.diff(np.log(np.r_[p_prev, w.values]))
            rv = np.sqrt((lr ** 2).sum())
        else:
            rv = np.nan
        rows.append(dict(day=d, inst=i, lh=p_lh_end / p_sig - 1, rod=p_sig / p_prev - 1, onfh=p_open / p_prev - 1,
                         rv_same=rv, nbars=len(w), entry=p_sig))
    f = pd.DataFrame(rows).set_index("day")
    f["eligible"] = f[["lh", "rod", "onfh"]].notna().all(axis=1)
    return f


def nwl(n):
    return int(np.floor(4 * (n / 100) ** (2 / 9)))


def reg(d, x):
    d = d[["lh", x]].dropna()
    m = sm.OLS(d.lh, sm.add_constant(d[[x]])).fit(cov_type="HAC", cov_kwds={"maxlags": nwl(len(d))})
    return round(m.params[x], 4), round(m.tvalues[x], 2), round(m.rsquared * 100, 2), len(d)


def sr(x):
    x = np.asarray(x, float)
    return x.mean() / x.std(ddof=1) * np.sqrt(252)


def nwt(x):
    x = np.asarray(x, float)
    return sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": nwl(len(x))}).tvalues[0]


def boot_ci(x, B=3000, L=20):
    x = np.asarray(x, float)
    n = len(x)
    nb = int(np.ceil(n / L))
    out = []
    for _ in range(B):
        s = RNG.integers(0, n - L + 1, nb)
        ii = (s[:, None] + np.arange(L)).ravel()[:n]
        out.append(sr(x[ii]))
    return np.percentile(out, [2.5, 97.5]).round(2)


allrows = []
for name, root, H, O in [("ES_1600", "ES", 16, 10), ("ZN_1600", "ZN", 16, 10), ("ZN_1500", "ZN", 15, 9)]:
    f = build(root, H, O)
    f.to_parquet(OUT / f"feat_{name}.parquet")
    e = f[f.eligible]
    log(f"[{name}] days with LH bar {len(f)}, eligible {len(e)}, IS {int((e.index<=IS_END).sum())}, "
        f"later {int((e.index>=LATER_START).sum())}")
    eis = e[e.index <= IS_END]
    for x in ("rod", "onfh"):
        for lab, sub in [("IS", eis), ("pre2018", eis[eis.index < PUB]), ("post2018", eis[eis.index >= PUB]),
                         ("IS_exCOVID", eis[~((eis.index >= "2020-02-20") & (eis.index <= "2020-04-30"))]),
                         ("later", e[e.index >= LATER_START])]:
            log(f"[{name}] reg LH on {x} {lab}: slope,t,R2%,n = {reg(sub, x)}")
    thr = eis.rod.abs().median()
    q1, q2 = eis.rv_same.quantile([1 / 3, 2 / 3])
    log(f"[{name}] IS median |ROD| {thr*1e4:.2f} bp; rv_same tercile cuts {q1*1e4:.1f}/{q2*1e4:.1f} bp")
    idx = nyse[1:]
    full = f.reindex(idx)
    el = full.eligible.fillna(False).astype(bool).values
    sg_rod = np.sign(full.rod.fillna(0).values)
    sg_on = np.sign(full.onfh.fillna(0).values)
    pos = {
        "S1_sign_ONFH": np.where(el, sg_on, 0.0),
        "S2_sign_ROD": np.where(el, sg_rod, 0.0),
        "S5_ROD_above_ISmedian": np.where(el & (full.rod.abs().values > thr), sg_rod, 0.0),
        "S6_ROD_high_sameday_RV": np.where(el & (full.rv_same.values > q2), sg_rod, 0.0),
    }
    lh = np.nan_to_num(full.lh.values)
    covid = (idx >= "2020-02-20") & (idx <= "2020-04-30")
    for sname, s in pos.items():
        np.save(OUT / f"pos_{name}_{sname}.npy", s)
        for cl, mult in (("gross", 0), ("1x", 1), ("2x", 2)):
            pnl = s * lh - np.abs(s) * 2 * COST[root] * mult
            for lab, m in [("IS", idx <= IS_END), ("IS_pre2018", idx < PUB),
                           ("IS_post2018", (idx >= PUB) & (idx <= IS_END)),
                           ("IS_exCOVID", (idx <= IS_END) & ~covid), ("later", idx >= LATER_START)]:
                x = pnl[m]
                tr = np.abs(s[m]) > 0
                row = dict(spec=name, strat=sname, cost=cl, sample=lab, n_days=int(m.sum()), n_traded=int(tr.sum()),
                           sharpe=round(sr(x), 3), nw_t=round(nwt(x), 2),
                           bp_per_trade=round(x[tr].mean() * 1e4, 3) if tr.any() else np.nan,
                           sharpe_se=round(np.sqrt((1 + sr(x) ** 2 / 2) / (m.sum() / 252)), 3))
                if lab == "IS" and root == "ES" and sname != "S1_sign_ONFH":
                    row["boot95"] = str(boot_ci(x))
                allrows.append(row)
res = pd.DataFrame(allrows)
res.to_csv(OUT / "verify_strategies.csv", index=False)
pd.set_option("display.width", 250)
log(res.to_string())
(OUT / "verify_log.txt").write_text("\n".join(LOG), encoding="utf-8")
