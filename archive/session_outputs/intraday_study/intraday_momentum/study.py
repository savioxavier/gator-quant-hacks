"""Market intraday momentum (Gao, Han, Li & Zhou 2018; Baltussen, Da, Lammers & Martens 2021) in ES and ZN
with hourly Databento bars (shared hourly panel, no new data).

Hourly approximations (all labelled as such in the outputs):
  * r_ONFH : previous session close -> end of the first hour bar after the cash open window
             (16:00 -> 10:00 ET for the 16:00 specs; Gao's r1 is exactly prev 16:00 -> 10:00 for SPY).
  * r_ROD  : previous session close -> start of the last hour (16:00 -> 15:00 ET). Paper: -> 15:30.
  * r_LH   : last hour bar (15:00-16:00 ET). Paper: last half hour 15:30-16:00.
  * r_M    : end of ONFH -> start of the second-to-last hour; r_SLH : second-to-last hour bar.
A second ZN specification uses the US Treasury futures day-session close (Baltussen et al. table of trading
hours, 8:20-15:00 ET): close 15:00 ET, r_ONFH prev 15:00 -> 09:00, r_ROD prev 15:00 -> 14:00, r_LH 14:00-15:00.

Point in time: every predictor uses bars whose END is <= the start of the traded bar; the traded bar is the one
starting at (close-1):00 ET. Asserted per day below.

In-sample = session days <= 2024-10-02. 2024-10-03..2026-10-02 is descriptive only. Every threshold
(median |predictor|, volatility terciles, z-score moments, combination weights) is estimated in-sample only.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

BASE = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
PANEL = BASE / "data" / "hourly_panel.parquet"
CAL = BASE / "data" / "nyse_calendar_offsets.parquet"
DATA = Path(os.environ.get("GQH_DATA_DIR", "<home>/.cache/gqh"))

IS_END = pd.Timestamp("2024-10-02")
LATER_START = pd.Timestamp("2024-10-03")
LATER_END = pd.Timestamp("2026-10-02")
PUB = pd.Timestamp("2018-01-01")  # Gao et al., Journal of Financial Economics 2018 (SSRN first draft March 2014)
COST_1X = {"ES": 1.0e-4, "ZN": 1.5e-4}  # one-way, fraction of notional
ES_TICK = 0.25
ANN = 252
BOOT_B = 5000
BOOT_L = 20
RNG = np.random.default_rng(20261003)

SPECS = {
    "ES_1600": dict(root="ES", close_h=16, open_end_h=10,
                    note="as briefed: target 15:00-16:00 ET bar; ONFH prev 16:00->10:00; ROD prev 16:00->15:00"),
    "ZN_1600": dict(root="ZN", close_h=16, open_end_h=10,
                    note="as briefed: same clock as ES (one hour after the ZN settlement window)"),
    "ZN_1500": dict(root="ZN", close_h=15, open_end_h=9,
                    note="pre-specified from Baltussen et al. US Treasury futures hours 8:20-15:00 ET: target "
                         "14:00-15:00 ET bar; ONFH prev 15:00->09:00; ROD prev 15:00->14:00"),
}

# Pre-specified variant grid (fixed before any result was computed; every one is reported).
REGRESSIONS = {
    "R1_ONFH": ["onfh"],
    "R2_ROD": ["rod"],
    "R3_DECOMP": ["onfh", "m", "slh"],
    "R4_ROD_LAGLH": ["rod", "lh_lag"],
}
STRATEGIES = {
    "B0_ALWAYS_LONG": dict(kind="long"),
    "S1_SIGN_ONFH": dict(kind="sign", pred="onfh"),
    "S2_SIGN_ROD": dict(kind="sign", pred="rod"),
    "S3_JOINT_ONFH_ROD": dict(kind="joint"),
    "S4_ONFH_ABOVE_MED": dict(kind="sign_thr", pred="onfh"),
    "S5_ROD_ABOVE_MED": dict(kind="sign_thr", pred="rod"),
}
VOL_MEASURES = {
    "rv_prev": "prior session realised vol, sqrt(sum of squared hourly log returns), known at previous close",
    "vix_lag1": "VIXCLS on the previous NYSE day (as-of), known before the trade",
    "rv_sameday": "same-session realised vol of the ROD bars, known at the signal time (hourly stand-in for "
                  "Gao's first half-hour volatility)",
}
SAMPLES = {
    "IS": (None, IS_END),
    "IS_pre2018": (None, PUB - pd.Timedelta(days=1)),
    "IS_post2018": (PUB, IS_END),
    "LATER_descriptive": (LATER_START, LATER_END),
}
COST_LEVELS = ["gross", "1x", "2x", "tick"]

LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


def nw_lags(n):
    return int(np.floor(4 * (n / 100.0) ** (2.0 / 9.0)))


def nw_mean_t(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 10 or np.std(x) == 0:
        return np.nan
    m = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": nw_lags(len(x))})
    return float(m.tvalues[0])


def sharpe(x):
    x = np.asarray(x, float)
    sd = x.std(ddof=1)
    return np.nan if sd == 0 or not np.isfinite(sd) else x.mean() / sd * np.sqrt(ANN)


def sharpe_se(sr, n_days):
    yrs = n_days / ANN
    return np.sqrt((1 + sr ** 2 / 2) / yrs) if yrs > 0 else np.nan


def block_indices(n, L=BOOT_L):
    nb = int(np.ceil(n / L))
    starts = RNG.integers(0, n - L + 1, size=nb) if n > L else np.zeros(nb, int)
    idx = (starts[:, None] + np.arange(L)[None, :]).ravel()[:n]
    return idx


# ---------------------------------------------------------------- daily features
def session_day(end_wc, close_h, nyse):
    base = (end_wc - pd.Timedelta(hours=close_h) - pd.Timedelta(nanoseconds=1)).dt.normalize() + pd.Timedelta(days=1)
    pos = np.searchsorted(nyse.values, base.values, side="left")
    out = pd.Series(pd.NaT, index=end_wc.index, dtype="datetime64[ns]")
    ok = pos < len(nyse)
    out[ok] = nyse.values[pos[ok]]
    return out


def build_daily(panel, spec_name, spec, nyse, vix):
    root, H, O = spec["root"], spec["close_h"], spec["open_end_h"]
    p = panel[panel.root == root].copy().sort_values("bar_start_utc").reset_index(drop=True)
    p["end_wc"] = p.bar_end_et.dt.tz_localize(None)
    p["start_wc"] = p.bar_start_et.dt.tz_localize(None)
    p["day"] = session_day(p["end_wc"], H, nyse)
    if H == 16:
        chk = (p["day"] == p["ret_date_1600"]) | p["ret_date_1600"].isna()
        log(f"[{spec_name}] session-day key reproduces ret_date_1600 on {chk.mean()*100:.4f}% of bars")
        assert chk.mean() > 0.99999
    p = p[p["day"].notna()]
    d = p["day"]
    t_open = d + pd.Timedelta(hours=O)
    t_sig = d + pd.Timedelta(hours=H - 1)
    t_slh = d + pd.Timedelta(hours=H - 2)
    lr = p["ret_log"].fillna(0.0)
    p["lr"] = lr
    p["in_onfh"] = p.end_wc <= t_open
    p["in_rod"] = p.end_wc <= t_sig
    p["in_m"] = (p.end_wc > t_open) & (p.end_wc <= t_slh)
    p["is_slh"] = p.start_wc == t_slh
    p["is_lh"] = p.start_wc == t_sig
    p["is_open_bar"] = p.end_wc == t_open
    p["bad"] = p.gap_type == "other_missing"

    g = p.groupby("day")
    f = pd.DataFrame({
        "onfh": g.apply(lambda x: np.expm1(x.lr[x.in_onfh].sum())),
        "rod": g.apply(lambda x: np.expm1(x.lr[x.in_rod].sum())),
        "m": g.apply(lambda x: np.expm1(x.lr[x.in_m].sum())),
        "slh": g.apply(lambda x: np.expm1(x.lr[x.is_slh].sum())),
        "has_open_bar": g["is_open_bar"].any(),
        "has_slh": g["is_slh"].any(),
        "n_bad": g["bad"].sum(),
        "rv_day": g.apply(lambda x: np.sqrt((x.lr ** 2).sum())),
        "rv_sameday": g.apply(lambda x: np.sqrt((x.lr[x.in_rod] ** 2).sum())),
        "max_end_sig": g.apply(lambda x: x.end_wc[x.in_rod].max()),
        "n_bars": g.size(),
    })
    lh = p[p.is_lh].set_index("day")
    assert lh.index.is_unique
    f["lh"] = lh["ret_simple"]
    f["lh_ok"] = (lh["hours_since_prev"] == 1.0) & (lh["gap_type"] == "none")
    f["lh_start"] = lh["start_wc"]
    # entry price = close of the bar ending at the signal time (same contract as the traded bar; roll bars excluded)
    f["entry_px"] = lh["prev_close_same_id"]
    f["lh_is_roll"] = lh["is_roll"]
    f["lh_ok"] = f["lh_ok"].fillna(False).astype(bool)
    f = f.sort_index()
    f["rv_prev"] = f["rv_day"].shift(1)
    f["lh_lag"] = f["lh"].shift(1)
    f.loc[~f["lh_ok"].shift(1, fill_value=False).astype(bool), "lh_lag"] = np.nan
    # VIX on the previous NYSE day (as-of: last value dated <= previous NYSE day)
    prev_nyse = pd.Series(nyse.values, index=nyse.values).shift(1)
    f["prev_nyse"] = prev_nyse.reindex(f.index).values
    vv = vix.dropna().sort_index()
    pos = np.searchsorted(vv.index.values, f["prev_nyse"].values, side="right") - 1
    f["vix_lag1"] = np.where(pos >= 0, vv.values[np.clip(pos, 0, None)], np.nan)
    f["eligible"] = (f.lh_ok & f.has_open_bar & f.has_slh & (f.n_bad == 0) & f.lh.notna()
                     & f.onfh.notna() & f.rod.notna() & f.rv_prev.notna())
    # point-in-time check: the last predictor bar ends exactly when the traded bar starts
    e = f[f.eligible]
    pit_ok = (e.max_end_sig == e.lh_start).all() and (e.lh_start == e.index + pd.Timedelta(hours=H - 1)).all()
    log(f"[{spec_name}] point-in-time check (last predictor bar end == traded bar start == {H-1}:00 ET): {pit_ok}")
    assert pit_ok
    # identity check: ROD = ONFH*M*SLH compounding
    ident = np.abs((1 + e.onfh) * (1 + e.m) * (1 + e.slh) - (1 + e.rod)).max()
    log(f"[{spec_name}] max |(1+ONFH)(1+M)(1+SLH)-(1+ROD)| = {ident:.2e}")
    f["root"] = root
    f["spec"] = spec_name
    f.index.name = "day"
    return f


# ---------------------------------------------------------------- analyses
def sample_mask(idx, s):
    lo, hi = SAMPLES[s]
    m = pd.Series(True, index=idx)
    if lo is not None:
        m &= idx >= lo
    if hi is not None:
        m &= idx <= hi
    return m.values


def run_reg(df, cols, y="lh"):
    d = df[[y] + cols].dropna()
    if len(d) < 30:
        return None
    X = sm.add_constant(d[cols])
    m = sm.OLS(d[y], X).fit(cov_type="HAC", cov_kwds={"maxlags": nw_lags(len(d))})
    out = {"n": len(d), "r2_pct": m.rsquared * 100, "alpha_bp": m.params["const"] * 1e4,
           "alpha_t": m.tvalues["const"]}
    for c in cols:
        out[f"b_{c}"] = m.params[c]
        out[f"t_{c}"] = m.tvalues[c]
    return out


def positions(df, strat, thr):
    k = STRATEGIES[strat]["kind"]
    e = df["eligible"].values
    if k == "long":
        s = np.ones(len(df))
    elif k == "sign":
        s = np.sign(df[STRATEGIES[strat]["pred"]].values)
    elif k == "sign_thr":
        pr = STRATEGIES[strat]["pred"]
        x = df[pr].values
        s = np.where(np.abs(x) > thr[pr], np.sign(x), 0.0)
    elif k == "joint":
        a, b = np.sign(df.onfh.values), np.sign(df.rod.values)
        s = np.where(a == b, a, 0.0)
    s = np.where(e, np.nan_to_num(s), 0.0)
    return s


def daily_pnl(df, s, cost_level, root):
    gross = s * np.nan_to_num(df["lh"].values)
    traded = np.abs(s)
    if cost_level == "gross":
        c = 0.0
    elif cost_level == "1x":
        c = COST_1X[root]
    elif cost_level == "2x":
        c = 2 * COST_1X[root]
    elif cost_level == "tick":
        if root != "ES":
            return None
        c = 2 * ES_TICK / df["entry_px"].values  # 2 ticks one-way at the entry price
        c = np.nan_to_num(c, nan=COST_1X[root])
    return gross - traded * 2 * c  # one round trip per traded day


def strat_stats(x, s):
    x = np.asarray(x, float)
    n = len(x)
    sr = sharpe(x)
    tr = np.abs(s) > 0
    return {
        "n_days": n, "n_traded": int(tr.sum()), "trade_frac": tr.mean(),
        "ann_ret_pct": x.mean() * ANN * 100, "ann_vol_pct": x.std(ddof=1) * np.sqrt(ANN) * 100,
        "sharpe": sr, "sharpe_se": sharpe_se(sr, n), "nw_t_mean": nw_mean_t(x),
        "mean_per_trade_bp": x[tr].mean() * 1e4 if tr.any() else np.nan,
        "hit_rate": (x[tr] > 0).mean() if tr.any() else np.nan,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec_doc = {
        "specs": SPECS, "regressions": REGRESSIONS,
        "strategies": {k: v for k, v in STRATEGIES.items()},
        "vol_measures": VOL_MEASURES, "samples": {k: [str(a), str(b)] for k, (a, b) in SAMPLES.items()},
        "costs_one_way": COST_1X, "cost_levels": COST_LEVELS,
        "cost_rule": "one round trip (2 x one-way) per traded day; tick level = ES 2 ticks (0.5 pt) at the entry "
                     "price, ZN not computed",
        "thresholds": "S4/S5: |predictor| > its in-sample median over eligible in-sample days (fixed in advance as "
                      "the median, not optimised); vol terciles and z-score moments in-sample only",
        "publication_split": str(PUB.date()),
        "bootstrap": {"type": "moving block", "block_days": BOOT_L, "reps": BOOT_B},
    }
    (OUT / "prespecified_grid.json").write_text(json.dumps(spec_doc, indent=1, default=str))

    panel = pd.read_parquet(PANEL)
    cal = pd.read_parquet(CAL)
    nyse = pd.Series(pd.to_datetime(cal["date"]).astype("datetime64[ns]").sort_values().values)
    fred = pd.read_parquet(DATA / "fred_daily.parquet")
    vix = pd.Series(fred["VIXCLS"].values, index=pd.to_datetime(fred["date"]).astype("datetime64[ns]"))

    daily = {}
    for sn, sp in SPECS.items():
        f = build_daily(panel, sn, sp, nyse, vix)
        f = f[f.index <= LATER_END]
        daily[sn] = f
        f.drop(columns=["max_end_sig"]).to_parquet(OUT / f"daily_{sn}.parquet")
        e = f[f.eligible]
        log(f"[{sn}] session days {len(f)}, eligible {len(e)} (IS {int((e.index<=IS_END).sum())}, later "
            f"{int((e.index>=LATER_START).sum())}); ineligible: no LH bar/gap {int((~f.lh_ok).sum())}, "
            f"vendor-hole days {int((f.n_bad>0).sum())}, roll on LH bar {int(f.lh_is_roll.fillna(False).sum())}")
        log(f"[{sn}] IS std: LH {e[e.index<=IS_END].lh.std()*1e4:.1f} bp, ONFH {e[e.index<=IS_END].onfh.std()*1e4:.1f} bp, "
            f"ROD {e[e.index<=IS_END].rod.std()*1e4:.1f} bp; corr(ONFH,ROD) IS {e[e.index<=IS_END][['onfh','rod']].corr().iloc[0,1]:.3f}")

    rows = []  # the full variant table
    reg_rows, strat_rows, vol_rows, year_rows, boot_rows = [], [], [], [], []

    # ---------------- 1. predictive regressions
    for sn, f in daily.items():
        e = f[f.eligible]
        for rn, cols in REGRESSIONS.items():
            for smp in SAMPLES:
                r = run_reg(e[sample_mask(e.index, smp)], cols)
                if r is None:
                    continue
                row = {"family": "regression", "spec": sn, "variant": rn, "sample": smp, **r}
                reg_rows.append(row)
        # by year (R1, R2), IS days and later days separately
        for yr in sorted(set(e.index.year)):
            for part, msk in (("IS", (e.index.year == yr) & (e.index <= IS_END)),
                              ("LATER_descriptive", (e.index.year == yr) & (e.index >= LATER_START))):
                sub = e[msk]
                if len(sub) < 30:
                    continue
                yrow = {"spec": sn, "year": yr, "part": part, "n": len(sub)}
                for rn in ("R1_ONFH", "R2_ROD"):
                    r = run_reg(sub, REGRESSIONS[rn])
                    c = REGRESSIONS[rn][0]
                    yrow[f"{rn}_b"] = r[f"b_{c}"]
                    yrow[f"{rn}_t"] = r[f"t_{c}"]
                    yrow[f"{rn}_r2_pct"] = r["r2_pct"]
                for st in ("S1_SIGN_ONFH", "S2_SIGN_ROD"):
                    s = positions(sub, st, None)
                    yrow[f"{st}_gross_bp_per_day"] = np.mean(s * sub.lh.values) * 1e4
                year_rows.append(yrow)

    # ---------------- 2. timing strategies
    thr_all = {}
    pnl_store = {}
    for sn, f in daily.items():
        root = SPECS[sn]["root"]
        eis = f[f.eligible & (f.index <= IS_END)]
        thr = {"onfh": eis.onfh.abs().median(), "rod": eis.rod.abs().median()}
        thr_all[sn] = thr
        log(f"[{sn}] in-sample median thresholds: |ONFH| {thr['onfh']*1e4:.2f} bp, |ROD| {thr['rod']*1e4:.2f} bp")
        for st in STRATEGIES:
            s = positions(f, st, thr)
            for cl in COST_LEVELS:
                x = daily_pnl(f, s, cl, root)
                if x is None:
                    continue
                pnl_store[(sn, st, cl)] = pd.Series(x, index=f.index)
                for smp in SAMPLES:
                    m = sample_mask(f.index, smp)
                    st_ = strat_stats(x[m], s[m])
                    strat_rows.append({"family": "strategy", "spec": sn, "variant": st, "cost": cl, "sample": smp,
                                       **st_})
            # breakeven one-way cost from gross mean per traded day
    # combination ES_1600 + ZN_1600 and ES_1600 + ZN_1500, S2 (ROD) and S1, inverse in-sample gross vol weights
    for zn in ("ZN_1600", "ZN_1500"):
        for st in ("S1_SIGN_ONFH", "S2_SIGN_ROD"):
            ges = pnl_store[("ES_1600", st, "gross")]
            gzn = pnl_store[(zn, st, "gross")]
            idx = ges.index.union(gzn.index)
            ges_, gzn_ = ges.reindex(idx).fillna(0), gzn.reindex(idx).fillna(0)
            ism = idx <= IS_END
            w_es, w_zn = 1 / ges_[ism].std(), 1 / gzn_[ism].std()
            w_es, w_zn = w_es / (w_es + w_zn), w_zn / (w_es + w_zn)
            for cl in ("gross", "1x", "2x"):
                x = (w_es * pnl_store[("ES_1600", st, cl)].reindex(idx).fillna(0)
                     + w_zn * pnl_store[(zn, st, cl)].reindex(idx).fillna(0))
                spos_es = (pnl_store[("ES_1600", st, "gross")].reindex(idx).fillna(0) != 0)
                spos_zn = (pnl_store[(zn, st, "gross")].reindex(idx).fillna(0) != 0)
                sflag = (spos_es | spos_zn).astype(float).values
                pnl_store[(f"COMBO_ES_1600+{zn}", st, cl)] = x
                for smp in SAMPLES:
                    m = sample_mask(idx, smp)
                    st_ = strat_stats(x.values[m], sflag[m])
                    strat_rows.append({"family": "strategy", "spec": f"COMBO_ES_1600+{zn}", "variant": st,
                                       "cost": cl, "sample": smp, "w_es": w_es, "w_zn": w_zn, **st_})

    sdf = pd.DataFrame(strat_rows)
    g = sdf[sdf.cost == "gross"][["spec", "variant", "sample", "mean_per_trade_bp"]].rename(
        columns={"mean_per_trade_bp": "gross_bp_per_trade"})
    sdf = sdf.merge(g, on=["spec", "variant", "sample"], how="left")
    sdf["breakeven_one_way_bp"] = sdf["gross_bp_per_trade"] / 2

    # ---------------- 3. volatility interaction
    for sn, f in daily.items():
        root = SPECS[sn]["root"]
        e = f[f.eligible].copy()
        eis = e[e.index <= IS_END]
        for vm in VOL_MEASURES:
            mu, sd = eis[vm].mean(), eis[vm].std()
            q1, q2 = eis[vm].quantile([1 / 3, 2 / 3])
            e[f"z_{vm}"] = (e[vm] - mu) / sd
            e[f"terc_{vm}"] = np.select([e[vm] <= q1, e[vm] <= q2], [1, 2], 3)
            e.loc[e[vm].isna(), f"terc_{vm}"] = 0
            for pr in ("onfh", "rod"):
                e["x"] = e[pr]
                e["xz"] = e[pr] * e[f"z_{vm}"]
                e["z"] = e[f"z_{vm}"]
                for smp in SAMPLES:
                    sub = e[sample_mask(e.index, smp)]
                    r = run_reg(sub, ["x", "z", "xz"])
                    if r is None:
                        continue
                    row = {"family": "vol_interaction", "spec": sn, "variant": f"VI_{pr.upper()}_x_{vm}",
                           "sample": smp, "n": r["n"], "r2_pct": r["r2_pct"], "b_pred": r["b_x"], "t_pred": r["t_x"],
                           "b_vol": r["b_z"], "t_vol": r["t_z"], "b_pred_x_vol": r["b_xz"], "t_pred_x_vol": r["t_xz"],
                           "is_terc_cut1": q1, "is_terc_cut2": q2}
                    for tc in (1, 2, 3):
                        st_ = sub[sub[f"terc_{vm}"] == tc]
                        rr = run_reg(st_, ["x"])
                        row[f"T{tc}_n"] = len(st_)
                        row[f"T{tc}_b"] = rr["b_x"] if rr else np.nan
                        row[f"T{tc}_t"] = rr["t_x"] if rr else np.nan
                        row[f"T{tc}_r2_pct"] = rr["r2_pct"] if rr else np.nan
                        sgn = np.sign(st_[pr].values)
                        row[f"T{tc}_timing_gross_bp_per_trade"] = np.mean(sgn * st_.lh.values) * 1e4 if len(st_) else np.nan
                    vol_rows.append(row)
                # high-vol-tercile-only timing strategy at costs (thresholds in-sample)
                full = f.copy()
                terc = pd.Series(0, index=full.index)
                terc[e.index] = e[f"terc_{vm}"]
                s = np.where(full.eligible & (terc == 3), np.sign(full[pr].fillna(0)), 0.0)
                for cl in COST_LEVELS:
                    x = daily_pnl(full, s, cl, root)
                    if x is None:
                        continue
                    vname = f"S6_SIGN_{pr.upper()}_HIGHVOL_{vm}"
                    pnl_store[(sn, vname, cl)] = pd.Series(x, index=full.index)
                    for smp in SAMPLES:
                        m = sample_mask(full.index, smp)
                        st_ = strat_stats(x[m], s[m])
                        strat_rows.append({"family": "strategy", "spec": sn, "variant": vname, "cost": cl,
                                           "sample": smp, **st_})
        daily[sn] = f

    sdf = pd.DataFrame(strat_rows)
    g = sdf[sdf.cost == "gross"][["spec", "variant", "sample", "mean_per_trade_bp"]].rename(
        columns={"mean_per_trade_bp": "gross_bp_per_trade"})
    sdf = sdf.merge(g, on=["spec", "variant", "sample"], how="left")
    sdf["breakeven_one_way_bp"] = sdf["gross_bp_per_trade"] / 2

    # ---------------- bootstrap (in-sample)
    def boot_sharpe_ci(x):
        x = np.asarray(x, float)
        n = len(x)
        bs = np.array([sharpe(x[block_indices(n)]) for _ in range(BOOT_B)])
        return np.nanpercentile(bs, [2.5, 97.5]), np.mean(bs <= 0)

    for key in [k for k in pnl_store if k[2] in ("gross", "1x", "2x")
                and k[1] in ("S1_SIGN_ONFH", "S2_SIGN_ROD", "S3_JOINT_ONFH_ROD", "S5_ROD_ABOVE_MED",
                             "S4_ONFH_ABOVE_MED")]:
        x = pnl_store[key]
        xi = x[x.index <= IS_END].values
        ci, p0 = boot_sharpe_ci(xi)
        boot_rows.append({"test": "sharpe_ci_IS", "spec": key[0], "a": key[1], "b": "", "cost": key[2],
                          "point": sharpe(xi), "ci_lo": ci[0], "ci_hi": ci[1], "p_le_0": p0})
    # paired differences
    for sn in list(daily) + ["COMBO_ES_1600+ZN_1600", "COMBO_ES_1600+ZN_1500"]:
        pairs = [("S2_SIGN_ROD", "S1_SIGN_ONFH", "gross"), ("S2_SIGN_ROD", "B0_ALWAYS_LONG", "gross"),
                 ("S5_ROD_ABOVE_MED", "S2_SIGN_ROD", "1x"), ("S3_JOINT_ONFH_ROD", "S2_SIGN_ROD", "1x")]
        for a, b, cl in pairs:
            if (sn, a, cl) not in pnl_store or (sn, b, cl) not in pnl_store:
                continue
            xa = pnl_store[(sn, a, cl)]
            xb = pnl_store[(sn, b, cl)]
            xa, xb = xa[xa.index <= IS_END].values, xb[xb.index <= IS_END].values
            n = len(xa)
            dsr = []
            dmu = []
            for _ in range(BOOT_B):
                ii = block_indices(n)
                dsr.append(sharpe(xa[ii]) - sharpe(xb[ii]))
                dmu.append(xa[ii].mean() - xb[ii].mean())
            dsr, dmu = np.array(dsr), np.array(dmu)
            boot_rows.append({"test": "paired_sharpe_diff_IS", "spec": sn, "a": a, "b": b, "cost": cl,
                              "point": sharpe(xa) - sharpe(xb), "ci_lo": np.nanpercentile(dsr, 2.5),
                              "ci_hi": np.nanpercentile(dsr, 97.5), "p_le_0": np.mean(dsr <= 0)})
            boot_rows.append({"test": "paired_mean_diff_IS_bp_per_day", "spec": sn, "a": a, "b": b, "cost": cl,
                              "point": (xa.mean() - xb.mean()) * 1e4, "ci_lo": np.percentile(dmu, 2.5) * 1e4,
                              "ci_hi": np.percentile(dmu, 97.5) * 1e4, "p_le_0": np.mean(dmu <= 0)})
    # pre vs post 2018 (independent block bootstrap within each period), gross S1 and S2
    for sn in daily:
        for st in ("S1_SIGN_ONFH", "S2_SIGN_ROD"):
            x = pnl_store[(sn, st, "gross")]
            pre = x[(x.index < PUB)].values
            post = x[(x.index >= PUB) & (x.index <= IS_END)].values
            d = np.array([post[block_indices(len(post))].mean() - pre[block_indices(len(pre))].mean()
                          for _ in range(BOOT_B)])
            boot_rows.append({"test": "post2018_minus_pre2018_mean_bp_per_day", "spec": sn, "a": st, "b": "",
                              "cost": "gross", "point": (post.mean() - pre.mean()) * 1e4,
                              "ci_lo": np.percentile(d, 2.5) * 1e4, "ci_hi": np.percentile(d, 97.5) * 1e4,
                              "p_le_0": np.mean(d <= 0)})
    # high minus low vol tercile timing return per traded day (block bootstrap over days, IS)
    for sn, f in daily.items():
        e = f[f.eligible & (f.index <= IS_END)].copy()
        for vm in VOL_MEASURES:
            q1, q2 = e[vm].quantile([1 / 3, 2 / 3])
            terc = np.select([e[vm] <= q1, e[vm] <= q2], [1, 2], 3)
            terc[e[vm].isna().values] = 0
            for pr in ("onfh", "rod"):
                g_ = np.sign(e[pr].values) * e.lh.values
                n = len(g_)
                pt = g_[terc == 3].mean() - g_[terc == 1].mean()
                d = []
                for _ in range(BOOT_B):
                    ii = block_indices(n)
                    gg, tt = g_[ii], terc[ii]
                    d.append(gg[tt == 3].mean() - gg[tt == 1].mean())
                d = np.array(d)
                boot_rows.append({"test": "highvol_minus_lowvol_timing_bp_per_trade_IS", "spec": sn,
                                  "a": f"sign_{pr}", "b": vm, "cost": "gross", "point": pt * 1e4,
                                  "ci_lo": np.percentile(d, 2.5) * 1e4, "ci_hi": np.percentile(d, 97.5) * 1e4,
                                  "p_le_0": np.mean(d <= 0)})

    reg = pd.DataFrame(reg_rows)
    vol = pd.DataFrame(vol_rows)
    yr = pd.DataFrame(year_rows)
    boot = pd.DataFrame(boot_rows)
    reg.to_csv(OUT / "regressions.csv", index=False)
    sdf.to_csv(OUT / "strategies.csv", index=False)
    vol.to_csv(OUT / "vol_interaction.csv", index=False)
    yr.to_csv(OUT / "by_year.csv", index=False)
    boot.to_csv(OUT / "bootstrap.csv", index=False)
    allv = pd.concat([reg, sdf, vol], ignore_index=True, sort=False)
    allv.to_csv(OUT / "all_variants.csv", index=False)
    n_def = (reg[["spec", "variant"]].drop_duplicates().shape[0]
             + sdf[["spec", "variant"]].drop_duplicates().shape[0]
             + vol[["spec", "variant"]].drop_duplicates().shape[0])
    log(f"variant definitions: regressions {reg[['spec','variant']].drop_duplicates().shape[0]}, "
        f"strategies {sdf[['spec','variant']].drop_duplicates().shape[0]}, "
        f"vol interactions {vol[['spec','variant']].drop_duplicates().shape[0]}; total {n_def}; "
        f"table rows {len(allv)}")
    (OUT / "run_log.txt").write_text("\n".join(LOG))


if __name__ == "__main__":
    main()
