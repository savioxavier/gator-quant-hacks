"""Independent re-computation of the overnight-drift study from the RAW cached hourly parquet.

Built without the shared panel: returns are rebuilt per instrument_id from the raw file (prev close = the same
contract's last close in any slot, .v.0 or .v.1), NYSE days come from SPY dates in etf_daily, windows are assigned
by bar END time in America/New_York.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

OUT = Path(__file__).resolve().parent
RAW = Path(r"<home>/.cache/gqh/databento_raw/glbx_ohlcv1h_v01_es_zn.parquet")
GQH = Path(os.environ.get("GQH_DATA_DIR", r"<home>/.cache/gqh"))
TZ = "America/New_York"
IS_END = pd.Timestamp("2024-10-02")
PUB = pd.Timestamp("2020-02-01")
COST = {"ES": 1e-4, "ZN": 1.5e-4}
RNG = np.random.default_rng(7)
lines = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    lines.append(s)


def nw_t(x, L=None):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if L is None:
        L = int(np.floor(4 * (n / 100) ** (2 / 9)))
    m = sm.OLS(x, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": L})
    return float(m.tvalues[0])


def sr(x):
    x = np.asarray(x, float)
    return x.mean() / x.std(ddof=1) * np.sqrt(252)


# ------------------------------------------------------------------ raw -> per-contract hourly returns
raw = pd.read_parquet(RAW)
raw["root"] = raw["symbol"].str[:2]
raw["slot"] = raw["symbol"].str[-1].astype(int)
spy = pd.read_parquet(GQH / "etf_daily.parquet")
nyse = pd.DatetimeIndex(sorted(pd.to_datetime(spy.loc[spy.ticker == "SPY", "date"]).dt.normalize().unique()))
nyse = nyse[(nyse >= "2010-06-01") & (nyse <= "2026-10-31")]
log("NYSE days", len(nyse), nyse[0].date(), nyse[-1].date())

bars = {}
for root in ("ES", "ZN"):
    r = raw[raw.root == root].copy()
    # every contract's own close history (any slot), sorted by time
    allc = r[["ts_event", "instrument_id", "close"]].drop_duplicates(["instrument_id", "ts_event"]).sort_values(
        ["instrument_id", "ts_event"])
    allc["prev_close_own"] = allc.groupby("instrument_id")["close"].shift(1)
    allc["prev_ts_own"] = allc.groupby("instrument_id")["ts_event"].shift(1)
    f = r[r.slot == 0][["ts_event", "instrument_id", "close", "volume"]].sort_values("ts_event").reset_index(drop=True)
    f = f.merge(allc[["ts_event", "instrument_id", "prev_close_own", "prev_ts_own"]], on=["ts_event", "instrument_id"],
                how="left")
    f["prev_front_ts"] = f["ts_event"].shift(1)
    f["roll"] = f["instrument_id"] != f["instrument_id"].shift(1)
    f.loc[0, "roll"] = False
    # if the contract traded (in any slot) after the previous front bar but before this one, its own prev close is
    # later than the previous front bar; that is still a within-contract return, just a different start point
    f["ret"] = f["close"] / f["prev_close_own"] - 1
    f["lr"] = np.log1p(f["ret"])
    f["bar_end_et"] = (f["ts_event"] + pd.Timedelta(hours=1)).dt.tz_convert(TZ)
    f["bar_start_et"] = f["ts_event"].dt.tz_convert(TZ)
    # sanity: front change gaps
    log(f"[{root}] front bars {len(f)}, rolls {int(f.roll.sum())}, NaN rets {int(f.ret.isna().sum())}, "
        f"own-prev earlier than prev front bar (gap inside contract) {(f.prev_ts_own < f.prev_front_ts).sum()}, "
        f"own-prev later than prev front bar {(f.prev_ts_own > f.prev_front_ts).sum()}")
    bars[root] = f

# ------------------------------------------------------------------ day assignment by bar END
def assign(f):
    be = f["bar_end_et"]
    be_naive = be.dt.tz_localize(None)
    # 16:00 ET boundary of each NYSE day as naive ET timestamps
    b16 = nyse + pd.Timedelta(hours=16)
    pos = np.searchsorted(b16.values, be_naive.values, side="left")  # first d with 16:00 >= bar end
    ok = pos < len(nyse)
    d = pd.Series(pd.NaT, index=f.index, dtype="datetime64[ns]")
    d[ok] = nyse[pos[ok]]
    f["d"] = d
    f["d_prev"] = pd.Series(pd.NaT, index=f.index, dtype="datetime64[ns]")
    f.loc[ok & (pos > 0), "d_prev"] = nyse[pos[ok & (pos > 0)] - 1]
    t = be_naive
    f["end_le_09_d"] = t <= f["d"] + pd.Timedelta(hours=9)
    f["in_eu"] = (t > f["d"] + pd.Timedelta(hours=1)) & (t <= f["d"] + pd.Timedelta(hours=4))
    f["in_on17"] = (t > f["d_prev"] + pd.Timedelta(hours=17)) & f["end_le_09_d"]
    f["is_lasthour"] = (t > f["d"] + pd.Timedelta(hours=15)) & (t <= f["d"] + pd.Timedelta(hours=16))
    f["et_hour_start"] = f["bar_start_et"].dt.hour
    return f


for root in bars:
    bars[root] = assign(bars[root])

# DST spot check: bar starting 02:00 ET must be 07:00 UTC in winter and 06:00 UTC in summer
f = bars["ES"]
for day in ("2023-01-10", "2023-07-11", "2023-03-13", "2023-11-06"):
    x = f[(f.bar_start_et.dt.strftime("%Y-%m-%d") == day) & (f.et_hour_start == 2)]
    log("DST check", day, x["ts_event"].iloc[0], "->", x["bar_start_et"].iloc[0])

# vendor holes: bars whose prev front bar is >1h earlier and that are not routine (daily break/weekend/holiday)
def hole_days(f):
    gap = (f["ts_event"] - f["prev_front_ts"]).dt.total_seconds() / 3600
    st = f["prev_front_ts"].dt.tz_convert(TZ)
    routine = (
        (gap <= 1)
        | ((st.dt.hour.isin([15, 16, 17, 12, 13])) & (f["bar_start_et"].dt.hour.isin([17, 18])))  # daily break / early
        | ((gap >= 40) & (gap <= 120) & (f["bar_start_et"].dt.hour.isin([17, 18])))             # weekend/holiday
        | f["prev_front_ts"].isna()
    )
    nr = f[~routine]
    return nr


for root in bars:
    nr = hole_days(bars[root])
    log(f"[{root}] non-routine gap bars (my heuristic): {len(nr)}")
    log(nr[["prev_front_ts", "ts_event", "bar_start_et", "d"]].assign(
        prev_et=nr.prev_front_ts.dt.tz_convert(TZ)).drop(columns="prev_front_ts").to_string())

# panel's other_missing list (to align exclusions for a like-for-like comparison)
ex = pd.read_parquet(r"<scratch>/"
                     r"scratchpad/intraday_study/overnight_drift/daily_strategy_returns.parquet")

# ------------------------------------------------------------------ daily strategy series
def daily(root):
    f = bars[root]
    f = f[f["d"].notna()]
    g = f.groupby("d")
    bh = g["lr"].sum()
    on = f[f.end_le_09_d].groupby("d")["lr"].sum()
    eu = f[f.in_eu].groupby("d")["lr"].sum()
    on17 = f[f.in_on17].groupby("d")["lr"].sum()
    h02 = f[(f.et_hour_start == 2) & f.end_le_09_d & (f.bar_start_et.dt.tz_localize(None) >= f.d - pd.Timedelta(hours=8))]
    h02 = h02.groupby("d")["lr"].sum()
    lh = f[f.is_lasthour].groupby("d")["lr"].sum()
    rolls_bh = g["roll"].sum()
    rolls_on = f[f.end_le_09_d].groupby("d")["roll"].sum()
    rolls_eu = f[f.in_eu].groupby("d")["roll"].sum()
    D = pd.DataFrame({"bh": bh, "on": on, "eu": eu, "on17": on17, "h02": h02, "lh": lh, "rolls_bh": rolls_bh,
                      "rolls_on": rolls_on, "rolls_eu": rolls_eu}).reindex(nyse).fillna(0.0)
    D["day"] = D["bh"] - D["on"]
    D = D[(D.index >= "2010-06-08") & (D.index <= "2026-10-02")]
    D["lh_prev"] = D["lh"].shift(1)
    return D


res = {}
for root in ("ES", "ZN"):
    D = daily(root)
    # use the analyst's exclusions? Compute both: (a) no exclusion, (b) their excluded days (dates missing in their file)
    their = ex[f"{root}|BH|gross"].dropna().index
    D_all = D
    D_ex = D[D.index.isin(their)]
    c = COST[root]
    for tag, DD in (("their_excl", D_ex), ("no_excl", D_all)):
        S = {}
        # simple returns per strategy, gross and net. one round trip per traded day (+1 per roll inside the window)
        simple = lambda s: np.expm1(s)
        S["BH"] = (simple(DD.bh), 2 * DD.rolls_bh)
        S["ON_16_09"] = (simple(DD.on), 2 + 2 * DD.rolls_on.clip(lower=0))
        S["EU_01_04"] = (simple(DD.eu), 2 + 2 * DD.rolls_eu)
        S["DAY_09_16"] = (simple(DD.day), pd.Series(2.0, index=DD.index))
        cond = (DD.lh_prev < 0)
        S["ON_17_09|lasthour_neg"] = (simple(DD.on17).where(cond, 0.0), (2.0 * cond))
        S["EU_01_04|lasthour_neg"] = (simple(DD.eu).where(cond, 0.0), (2.0 * cond))
        # tilt EU w=2: BH plus one extra unit in 01-04
        S["TILT_EU_w2"] = ((1 + 2 * simple(DD.eu)) * (1 + simple(DD.bh)) / (1 + simple(DD.eu)) - 1,
                           2 * DD.rolls_bh + 2.0)
        res[(root, tag)] = (DD, S)

samples = {"IS": ("2010-06-08", "2024-10-02"), "pre": ("2010-06-08", "2020-01-31"),
           "post": ("2020-02-01", "2024-10-02"), "later": ("2024-10-03", "2026-10-02")}
rows = []
for (root, tag), (DD, S) in res.items():
    c = COST[root]
    for name, (g, units) in S.items():
        for lvl, k in (("gross", 0), ("1x", 1), ("2x", 2)):
            net = g - k * c * units
            for sn, (a, b) in samples.items():
                m = (net.index >= a) & (net.index <= b)
                x = net[m].to_numpy()
                rows.append(dict(root=root, excl=tag, variant=name, cost=lvl, sample=sn, n=len(x), sharpe=sr(x),
                                 ann_mean_pct=x.mean() * 252 * 100, nw_t=nw_t(x),
                                 be_oneway_bp=g[m].sum() / units[m].sum() * 1e4 if units[m].sum() > 0 else np.nan))
T = pd.DataFrame(rows)
T.to_csv(OUT / "verify_strategies.csv", index=False)
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
log("\n== my strategy Sharpes (their exclusions) ==")
piv = T[T.excl == "their_excl"].pivot_table(index=["root", "variant", "sample"], columns="cost", values="sharpe")
log(piv.round(3).to_string())
log("\n== no exclusions, IS ==")
log(T[(T.excl == "no_excl") & (T["sample"] == "IS")].pivot_table(index=["root", "variant"], columns="cost",
                                                                  values="sharpe").round(3).to_string())

# compare daily series with the analyst's file
for root in ("ES", "ZN"):
    DD, S = res[(root, "their_excl")]
    for nm in ("BH", "ON_16_09", "EU_01_04", "ON_17_09|lasthour_neg"):
        mine = S[nm][0]
        th = ex[f"{root}|{nm}|gross"].reindex(mine.index)
        d = (mine - th).abs()
        log(f"[{root}] {nm}: max |mine-theirs| gross {d.max() * 1e4:.3f} bp, days >0.5bp {(d > 5e-5).sum()}, "
            f"corr {np.corrcoef(mine, th.fillna(0))[0, 1]:.6f}")
        big = d[d > 5e-5]
        if len(big):
            log("   largest:", [(str(i.date()), round(v * 1e4, 2)) for i, v in big.sort_values().tail(5).items()])

# ------------------------------------------------------------------ segment shares (log) IS, ES
for root in ("ES", "ZN"):
    DD, S = res[(root, "their_excl")]
    x = DD[DD.index <= IS_END]
    tot = x.bh
    for col in ("on", "eu", "day", "h02"):
        cv = np.cov(x[col], tot)
        log(f"[{root}] IS seg {col}: share of return {x[col].mean() / tot.mean():.3f}, risk share "
            f"{cv[0, 1] / cv[1, 1]:.3f}, ann {x[col].mean() * 252 * 100:.2f}%/yr log, NW t {nw_t(x[col]):.2f}, "
            f"Sharpe {sr(x[col]):.2f}")

# 02:00 hour per-bar mean and NW t (bars, all ET 02:00 bar starts on NYSE day d mornings)
for root in ("ES",):
    f = bars[root]
    f = f[(f.et_hour_start == 2) & f.d.notna()]
    f = f[f.bar_start_et.dt.date.astype("datetime64[ns]") == f.d]  # only bars on the NYSE day's own morning
    their = ex[f"{root}|BH|gross"].dropna().index
    for sn, (a, b) in samples.items():
        y = f[(f.d >= a) & (f.d <= b) & f.d.isin(their)]["ret"]
        log(f"[{root}] 02:00-03:00 bar {sn}: n {len(y)}, mean {y.mean() * 1e4:.3f} bp, NW t {nw_t(y):.2f}")

# ------------------------------------------------------------------ spanning alpha EU on BH (gross, 1x), IS
for root in ("ES",):
    DD, S = res[(root, "their_excl")]
    for nm in ("EU_01_04", "ON_16_09", "EU_01_04|lasthour_neg", "ON_17_09|lasthour_neg"):
        for lvl, k in (("gross", 0), ("1x", 1)):
            y = S[nm][0] - k * COST[root] * S[nm][1]
            xb = S["BH"][0] - k * COST[root] * S["BH"][1]
            for sn, (a, b) in samples.items():
                m = (y.index >= a) & (y.index <= b)
                n = int(m.sum())
                L = int(np.floor(4 * (n / 100) ** (2 / 9)))
                fit = sm.OLS(y[m].to_numpy(), sm.add_constant(xb[m].to_numpy())).fit(cov_type="HAC",
                                                                                     cov_kwds={"maxlags": L})
                log(f"[{root}] span {nm} {lvl} {sn}: alpha {fit.params[0] * 252 * 100:.2f}%/yr t {fit.tvalues[0]:.2f} "
                    f"beta {fit.params[1]:.3f}")

# ------------------------------------------------------------------ bootstrap Sharpe diff, IS, block 21 and 63
def boot(x, y, block, B=4000):
    n = len(x)
    nb = int(np.ceil(n / block))
    st = RNG.integers(0, n, size=(B, nb))
    idx = ((st[:, :, None] + np.arange(block)) % n).reshape(B, -1)[:, :n]
    xb, yb = x[idx], y[idx]
    d = xb.mean(1) / xb.std(1, ddof=1) * np.sqrt(252) - yb.mean(1) / yb.std(1, ddof=1) * np.sqrt(252)
    return sr(x) - sr(y), np.quantile(d, [0.025, 0.975]), 2 * min((d <= 0).mean(), (d >= 0).mean())


DD, S = res[("ES", "their_excl")]
m = DD.index <= IS_END
for a_, b_, lvl, k in (("ON_16_09", "BH", "gross", 0), ("EU_01_04", "BH", "gross", 0), ("TILT_EU_w2", "BH", "gross", 0),
                       ("TILT_EU_w2", "BH", "1x", 1), ("ON_17_09|lasthour_neg", "BH", "1x", 1),
                       ("ON_16_09", "BH", "1x", 1)):
    x = (S[a_][0] - k * 1e-4 * S[a_][1])[m].to_numpy()
    y = (S[b_][0] - k * 1e-4 * S[b_][1])[m].to_numpy()
    for blk in (21, 63):
        d, ci, p = boot(x, y, blk)
        log(f"[ES] boot {a_} - {b_} {lvl} block {blk}: diff {d:.3f} CI {ci.round(2)} p {p:.3f}")

# ------------------------------------------------------------------ the best non-BH 1x variant: dependence on 2020
DD, S = res[("ES", "their_excl")]
y = S["ON_17_09|lasthour_neg"][0] - 1e-4 * S["ON_17_09|lasthour_neg"][1]
yi = y[y.index <= IS_END]
log(f"[ES] ON_17_09|lasthour_neg 1x IS {sr(yi):.3f}, ex-2020 {sr(yi[yi.index.year != 2020]):.3f}, "
    f"2020 compounded gross {(np.prod(1 + S['ON_17_09|lasthour_neg'][0][S['ON_17_09|lasthour_neg'][0].index.year == 2020]) - 1) * 100:.1f}%")
# deflated view: max of N iid Sharpe estimates under null with SE ~ 1/sqrt(14.3)
yrs = len(yi) / 252
for N in (16, 32, 64):
    from scipy.stats import norm
    e_max = norm.ppf(1 - 1 / N) / np.sqrt(yrs)
    log(f"expected max Sharpe of {N} null variants over {yrs:.1f}y ~ {e_max:.2f}")

(OUT / "verify_log.txt").write_text("\n".join(lines), encoding="utf-8")
