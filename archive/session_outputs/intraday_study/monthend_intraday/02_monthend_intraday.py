"""When during the day do the month-end flow effects (sleeves A and C) happen, and would intraday timing help?

Specification: prespec.txt in this folder (written before this script was run).
Inputs: ../data/hourly_panel.parquet, ../data/nyse_calendar_offsets.parquet, sleeve_weights.parquet and
month_info.csv from 01_sleeve_weights.py, futures_1600.parquet + rf_daily.parquet (validation only).
Outputs (this folder): profile_hourly.csv, profile_blocks.csv, profile_offsets_daynight.csv, variants.csv,
variant_monthly_pnl.csv, oos_diag_C_hours.csv, oos_diag_C_months.csv, validation_baseline.csv, run_log.txt.

Run from the repo root:
  GQH_DATA_DIR=<home>/.cache/gqh PYTHONIOENCODING=utf-8 <venv python> <this file>
"""
from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
GQH = Path(os.environ.get("GQH_DATA_DIR", "<home>/.cache/gqh"))
IS_END = pd.Timestamp("2024-10-02")
LATER = (pd.Timestamp("2024-10-03"), pd.Timestamp("2026-10-02"))
PUB_SPLIT_C = pd.Timestamp("2019-12-01")      # Hartley & Schwarz working paper, Nov 2019
COST = {"ES": 1.0e-4, "ZN": 1.5e-4}            # one-way per unit notional
COST_LEVELS = {"gross": 0.0, "1x": 1.0, "2x": 2.0}
OFFSETS = list(range(-5, 3))
BLOCKS = {                                      # by bar START hour (ET)
    "post_close_16_18": [16, 17],
    "asia_18_02": [18, 19, 20, 21, 22, 23, 0, 1],
    "europe_02_08": [2, 3, 4, 5, 6, 7],
    "us_open_08_10": [8, 9],
    "late_morning_fix_10_12": [10, 11],
    "midday_12_14": [12, 13],
    "pre_pricing_14_15": [14],
    "close_hour_15_16": [15],
}
HOUR2BLOCK = {h: b for b, hs in BLOCKS.items() for h in hs}
VARIANTS = ["base", "exit_1500", "exit_1600", "exit_1700", "day_only", "night_only"]
DISTINCT_VARIANTS = ["base", "exit_1500", "exit_1700", "day_only", "night_only"]   # exit_1600 == base
N_BOOT = 5000
BLOCK_MONTHS = 3
RNG = np.random.default_rng(20261003)
# months whose window contains a vendor hole / outage bar (gap_type other_missing) in a traded root
HOLE_MONTHS = {"A": ["2014-09", "2019-02", "2020-02", "2020-06", "2025-11"], "C": ["2019-02", "2020-02", "2020-06", "2025-11"]}
LOG: list[str] = []


def log(*a) -> None:
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


# --------------------------------------------------------------------------- statistics

def nw_t(x, lags: int = 3) -> float:
    x = np.asarray(pd.Series(x).dropna(), dtype=float)
    n = len(x)
    if n < 5:
        return float("nan")
    e = x - x.mean()
    s = e @ e / n
    for L in range(1, min(lags, n - 1) + 1):
        s += 2 * (1 - L / (lags + 1)) * (e[L:] @ e[:-L]) / n
    return float(x.mean() / math.sqrt(s / n)) if s > 0 else float("nan")


def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    sd = x.std()
    return float(x.mean() / sd * math.sqrt(252)) if sd > 0 else float("nan")


def sr_se(sr: float, years: float) -> float:
    return math.sqrt((1 + sr * sr / 2) / years)


# --------------------------------------------------------------------------- data

def load_panel() -> pd.DataFrame:
    cols = ["root", "bar_start_utc", "bar_start_et", "date_et", "hour_et", "ret_date_1600", "ret_simple",
            "is_roll", "instrument_id", "gap_type"]
    p = pd.read_parquet(DATA / "hourly_panel.parquet", columns=cols)
    p = p.rename(columns={"ret_date_1600": "rd"})
    p = p[p["rd"].notna() & p["ret_simple"].notna()].copy()
    p["rd"] = p["rd"].astype("datetime64[ns]")
    p["date_et"] = p["date_et"].astype("datetime64[ns]")
    p["hour_et"] = p["hour_et"].astype(int)
    p = p.sort_values(["root", "bar_start_utc"]).reset_index(drop=True)
    return p


def load_calendar() -> pd.DataFrame:
    c = pd.read_parquet(DATA / "nyse_calendar_offsets.parquet")
    c["date"] = c["date"].astype("datetime64[ns]")
    c["month_T"] = c["month_T"].astype("datetime64[ns]")
    c = c.sort_values("date").reset_index(drop=True)
    pos = np.arange(len(c))
    k_prev = c["me_off_prev"].to_numpy()
    prevT = [c["date"].iloc[i - int(k)] if np.isfinite(k) and i - int(k) >= 0 else pd.NaT
             for i, k in zip(pos, k_prev)]
    c["prev_T"] = pd.DatetimeIndex(prevT)
    # event offset k in -5..+2 and its event month-end T
    own = c["me_off_own"]
    prv = c["me_off_prev"]
    k = pd.Series(np.nan, index=c.index)
    evT = pd.Series(pd.NaT, index=c.index, dtype="datetime64[ns]")
    m_own = own.between(-5, 0)
    k[m_own] = own[m_own]
    evT[m_own] = c.loc[m_own, "month_T"]
    m_prv = prv.between(1, 2) & ~m_own
    k[m_prv] = prv[m_prv]
    evT[m_prv] = c.loc[m_prv, "prev_T"]
    c["k"] = k
    c["evT"] = evT
    c["next_day"] = c["date"].shift(-1)
    return c


# --------------------------------------------------------------------------- part 1: profiles

def cell_stats(vals: pd.DataFrame, keys: list[str], other: pd.DataFrame | None, okeys: list[str]) -> pd.DataFrame:
    """vals: one row per (event month, keys...) with column x (bp). other: rows on non-event days."""
    g = vals.groupby(keys)["x"]
    out = pd.DataFrame({"n": g.size(), "mean_bp": g.mean(), "sd_bp": g.std()})
    out["t_nw"] = vals.sort_values("evT").groupby(keys)["x"].apply(lambda s: nw_t(s.to_numpy(), 2))
    out = out.reset_index()
    if other is not None:
        go = other.groupby(okeys)["x"]
        o = pd.DataFrame({"other_n": go.size(), "other_mean_bp": go.mean(), "other_sd_bp": go.std()}).reset_index()
        out = out.merge(o, on=okeys, how="left")
        out["diff_bp"] = out["mean_bp"] - out["other_mean_bp"]
        out["diff_t_welch"] = out["diff_bp"] / np.sqrt(out["sd_bp"] ** 2 / out["n"] + out["other_sd_bp"] ** 2 / out["other_n"])
    return out


def profiles(p: pd.DataFrame, cal: pd.DataFrame, w: pd.DataFrame) -> None:
    q = p[p["gap_type"] != "other_missing"].merge(cal[["date", "k", "evT"]], left_on="rd", right_on="date", how="left")
    q["block"] = q["hour_et"].map(HOUR2BLOCK)
    q["sample"] = np.where(q["rd"] <= IS_END, "IS", np.where(q["rd"] >= LATER[0], "later", "none"))
    # sleeve A legs per event month (the window weights, constant inside a window)
    aw = w[w["A_ES"] != 0].groupby("A_T")[["A_ES", "A_ZN"]].first()
    rows_h, rows_b = [], []
    series = {
        "ZN_long": ("ZN", lambda d: d["ret_simple"] * 1e4),
        "ES_long": ("ES", lambda d: d["ret_simple"] * 1e4),
        "A_spread_ZNleg": ("ZN", None),
        "A_spread_ESleg": ("ES", None),
    }
    for name, (root, fn) in series.items():
        d = q[q["root"] == root].copy()
        if fn is None:
            leg = "A_ZN" if root == "ZN" else "A_ES"
            d = d[d["k"].notna()]
            d["wA"] = d["evT"].map(aw[leg])
            d = d[d["wA"].notna()]
            d["x"] = d["wA"] * d["ret_simple"] * 1e4
            other = None
        else:
            d["x"] = fn(d)
        for smp in ("IS", "later"):
            ds = d[d["sample"] == smp]
            ev = ds[ds["k"].notna()]
            oth = ds[ds["k"].isna()] if fn is not None else None
            # per (event month, k, hour): sum of bars (normally exactly one bar)
            vh = ev.groupby(["evT", "k", "hour_et"], as_index=False)["x"].sum()
            if oth is not None:
                oh = oth.groupby(["rd", "hour_et"], as_index=False)["x"].sum()
            else:
                oh = None
            ch = cell_stats(vh, ["k", "hour_et"], oh, ["hour_et"])
            ch.insert(0, "sample", smp)
            ch.insert(0, "series", name)
            rows_h.append(ch)
            vb = ev.groupby(["evT", "k", "block"], as_index=False)["x"].sum()
            ob = oth.groupby(["rd", "block"], as_index=False)["x"].sum() if oth is not None else None
            cb = cell_stats(vb, ["k", "block"], ob, ["block"])
            cb.insert(0, "sample", smp)
            cb.insert(0, "series", name)
            rows_b.append(cb)
    ph = pd.concat(rows_h, ignore_index=True)
    pb = pd.concat(rows_b, ignore_index=True)
    # A spread combined per (event month, k, block) and (k, hour)
    comb_h, comb_b = [], []
    for smp in ("IS", "later"):
        parts = []
        for root, leg in (("ZN", "A_ZN"), ("ES", "A_ES")):
            d = q[(q["root"] == root) & (q["sample"] == smp) & q["k"].notna()].copy()
            d["wA"] = d["evT"].map(aw[leg])
            d = d[d["wA"].notna()]
            d["x"] = d["wA"] * d["ret_simple"] * 1e4
            parts.append(d)
        d = pd.concat(parts)
        vh = d.groupby(["evT", "k", "hour_et"], as_index=False)["x"].sum()
        ch = cell_stats(vh, ["k", "hour_et"], None, [])
        ch.insert(0, "sample", smp)
        ch.insert(0, "series", "A_spread_signed")
        comb_h.append(ch)
        vb = d.groupby(["evT", "k", "block"], as_index=False)["x"].sum()
        cb = cell_stats(vb, ["k", "block"], None, [])
        cb.insert(0, "sample", smp)
        cb.insert(0, "series", "A_spread_signed")
        comb_b.append(cb)
    ph = pd.concat([ph] + comb_h, ignore_index=True)
    pb = pd.concat([pb] + comb_b, ignore_index=True)
    ph.to_csv(HERE / "profile_hourly.csv", index=False)
    pb.to_csv(HERE / "profile_blocks.csv", index=False)

    # day (09-16 of d) vs night (16 of d-1 .. 09 of d) per offset, for ZN, ES and the A spread
    rows = []
    for name, root in (("ZN_long", "ZN"), ("ES_long", "ES")):
        d = q[q["root"] == root].copy()
        d["x"] = d["ret_simple"] * 1e4
        d["part"] = np.where((d["date_et"] == d["rd"]) & d["hour_et"].between(9, 15), "day_09_16", "night_16_09")
        for smp in ("IS", "later"):
            ds = d[d["sample"] == smp]
            per = ds.groupby(["rd", "part"], as_index=False)["x"].sum().merge(cal[["date", "k", "evT"]], left_on="rd", right_on="date")
            ev = per[per["k"].notna()]
            oth = per[per["k"].isna()]
            c = cell_stats(ev, ["k", "part"], oth, ["part"])
            c.insert(0, "sample", smp)
            c.insert(0, "series", name)
            rows.append(c)
            tot = ds.groupby("rd", as_index=False)["x"].sum().merge(cal[["date", "k", "evT"]], left_on="rd", right_on="date")
            tot["part"] = "full_16_16"
            c = cell_stats(tot[tot["k"].notna()], ["k", "part"], tot[tot["k"].isna()], ["part"])
            c.insert(0, "sample", smp)
            c.insert(0, "series", name)
            rows.append(c)
    pd.concat(rows, ignore_index=True).to_csv(HERE / "profile_offsets_daynight.csv", index=False)



def volume_profile(cal: pd.DataFrame) -> None:
    """Where in the day is month-end trading activity? Front + second contract volume per bar.

    For each (root, offset k, ET hour): mean share of the return day's volume traded in that bar, against the
    same hour's mean share on non-event days; and the abnormal-volume ratio = bar volume / mean volume of the
    same hour over the same month's days at offsets T-15..T-6 (a local baseline), averaged over months.
    """
    cols = ["root", "ret_date_1600", "date_et", "hour_et", "volume", "volume_v1", "gap_type"]
    v = pd.read_parquet(DATA / "hourly_panel.parquet", columns=cols).rename(columns={"ret_date_1600": "rd"})
    v = v[v["rd"].notna() & (v["gap_type"] != "other_missing")].copy()
    v["rd"] = v["rd"].astype("datetime64[ns]")
    v["vol"] = v["volume"].astype(float) + v["volume_v1"].fillna(0).astype(float)
    v["hour_et"] = v["hour_et"].astype(int)
    v = v.merge(cal[["date", "k", "evT", "me_off_own", "month_T"]], left_on="rd", right_on="date", how="left")
    v["share"] = v["vol"] / v.groupby(["root", "rd"])["vol"].transform("sum")
    v["sample"] = np.where(v["rd"] <= IS_END, "IS", np.where(v["rd"] >= LATER[0], "later", "none"))
    # local baseline: same month, offsets -15..-6, same hour
    base = v[v["me_off_own"].between(-15, -6)].groupby(["root", "month_T", "hour_et"])["vol"].mean().rename("base_vol")
    ev = v[v["k"].notna()].copy()
    ev["month_ref"] = np.where(ev["k"] <= 0, ev["evT"], ev["evT"])        # the event month's T
    ev = ev.join(base, on=["root", "month_ref", "hour_et"]) if False else ev.merge(
        base.reset_index().rename(columns={"month_T": "evT"}), on=["root", "evT", "hour_et"], how="left")
    ev["abn_ratio"] = ev["vol"] / ev["base_vol"]
    rows = []
    for (root, smp), g in ev[ev["sample"] != "none"].groupby(["root", "sample"]):
        oth = v[(v["root"] == root) & (v["sample"] == smp) & v["k"].isna()].groupby("hour_et")["share"].mean()
        for (k, h), gg in g.groupby(["k", "hour_et"]):
            rows.append({"root": root, "sample": smp, "k": int(k), "hour_et": int(h), "n": len(gg),
                         "mean_share_pct": gg["share"].mean() * 100, "other_share_pct": oth.get(h, np.nan) * 100,
                         "median_abn_ratio": gg["abn_ratio"].median(), "mean_abn_ratio": gg["abn_ratio"].mean()})
    pd.DataFrame(rows).to_csv(HERE / "volume_profile.csv", index=False)


# --------------------------------------------------------------------------- part 2: variants

def bar_weights(pr: pd.DataFrame, wday: pd.Series, offd: pd.Series, Td: pd.Series, cal: pd.DataFrame,
                variant: str) -> tuple[np.ndarray, np.ndarray]:
    """Per bar of one root: held weight and the event T the bar's P&L is attributed to."""
    W = pr["rd"].map(wday).fillna(0.0).to_numpy()
    T = pr["rd"].map(Td).to_numpy(dtype="datetime64[ns]")
    off = pr["rd"].map(offd).to_numpy()
    h = pr["hour_et"].to_numpy()
    same_day = (pr["date_et"] == pr["rd"]).to_numpy()
    if variant in ("base", "exit_1600"):
        pass
    elif variant == "exit_1500":
        W = np.where((off == 0) & (h == 15) & same_day, 0.0, W)
    elif variant == "exit_1700":
        # add the 16:00 and 17:00 bars that start on T itself (they belong to the next return day)
        lastday = wday[offd == 0]                       # weight held on T, indexed by T
        is_ext = pr["date_et"].isin(lastday.index).to_numpy() & np.isin(h, [16, 17]) & (pr["rd"] != pr["date_et"]).to_numpy()
        extW = pr["date_et"].map(lastday).fillna(0.0).to_numpy()
        W = np.where(is_ext, extW, W)
        T = np.where(is_ext, pr["date_et"].to_numpy(dtype="datetime64[ns]"), T)
    elif variant == "day_only":
        W = np.where(same_day & (h >= 9) & (h <= 15), W, 0.0)
    elif variant == "night_only":
        W = np.where(same_day & (h >= 9) & (h <= 15), 0.0, W)
    else:
        raise ValueError(variant)
    return W, T


def leg_pnl(pr: pd.DataFrame, W: np.ndarray, T: np.ndarray, root: str) -> pd.DataFrame:
    """Per bar: P&L contribution, transaction cost (unit = 1x), attributed return day and event T."""
    r = pr["ret_simple"].to_numpy()
    roll = pr["is_roll"].to_numpy()
    Wp = np.concatenate([[0.0], W[:-1]])
    Wn = np.concatenate([W[1:], [0.0]])
    c = COST[root]
    # turnover at the boundary before bar h is |W_h - W_{h-1}|: charged to bar h if it holds a position,
    # otherwise (an exit) to the last held bar h-1. A position held across a front-contract change pays an
    # extra round trip (close the old contract, open the new one at the previous bar's close).
    trade = np.where(W != 0, np.abs(W - Wp), 0.0) + np.where((W != 0) & (Wn == 0), np.abs(W), 0.0)
    rollc = np.where(roll & (W != 0) & (Wp != 0), 2 * np.abs(Wp), 0.0)
    turn = trade + rollc
    cost = c * turn
    df = pd.DataFrame({"rd": pr["rd"].to_numpy(), "evT": T, "W": W, "r": r, "cost": cost, "turn": turn})
    return df


def daily_from_bars(df: pd.DataFrame) -> pd.DataFrame:
    """Per return day: compounded P&L over held bars (weight constant within a day) and costs."""
    held = df[df["W"] != 0]
    g = held.groupby("rd")
    comp = g["r"].apply(lambda s: np.prod(1 + s.to_numpy()) - 1)
    wconst = g["W"].first()
    wchk = g["W"].nunique()
    assert (wchk <= 1).all(), "weight varies within a return day"
    pnl = wconst * comp
    cost = df.groupby("rd")["cost"].sum()
    turn = df.groupby("rd")["turn"].sum()
    out = pd.DataFrame({"pnl": pnl}).join(cost, how="outer").join(turn, how="outer").fillna(0.0)
    # event month attribution per return day (for monthly window P&L)
    ev = held.groupby("rd")["evT"].first()
    out["evT"] = ev
    return out


def variant_daily(p: pd.DataFrame, w: pd.DataFrame, cal: pd.DataFrame, sleeve: str, variant: str) -> pd.DataFrame:
    legs = {"A": [("ES", "A_ES"), ("ZN", "A_ZN")], "C": [("ZN", "C_ZN")]}[sleeve]
    wi = w.set_index("date")
    offd = wi[f"{sleeve}_off"]
    Td = wi[f"{sleeve}_T"]
    parts = []
    for root, col in legs:
        pr = p[p["root"] == root].reset_index(drop=True)
        W, T = bar_weights(pr, wi[col], offd, Td, cal, variant)
        bars = leg_pnl(pr, W, T, root)
        d = daily_from_bars(bars)
        d["leg"] = root
        parts.append(d)
    d = pd.concat(parts)
    evT = d.groupby(level=0)["evT"].first()
    out = d.groupby(level=0)[["pnl", "cost", "turn"]].sum()
    out["evT"] = evT
    return out


def full_calendar_series(d: pd.DataFrame, days: pd.DatetimeIndex, cm: float) -> pd.Series:
    x = (d["pnl"] - cm * d["cost"]).reindex(days).fillna(0.0)
    return x


def boot_sharpe_diff(xs: dict[str, pd.Series], base: str, months: pd.PeriodIndex) -> dict[str, dict]:
    """Paired block bootstrap over calendar months (blocks of BLOCK_MONTHS consecutive months)."""
    names = list(xs)
    mstats = {}
    for n in names:
        x = xs[n]
        per = x.index.to_period("M")
        g = pd.DataFrame({"s": x.values, "s2": x.values ** 2, "c": 1.0}, index=per).groupby(level=0).sum()
        mstats[n] = g.reindex(months).fillna(0.0).to_numpy()
    M = len(months)
    nb = int(math.ceil(M / BLOCK_MONTHS))
    starts = RNG.integers(0, M - BLOCK_MONTHS + 1, size=(N_BOOT, nb))
    idx = (starts[:, :, None] + np.arange(BLOCK_MONTHS)[None, None, :]).reshape(N_BOOT, -1)[:, :M]

    def sr_of(a):
        s, s2, c = a[..., 0].sum(-1), a[..., 1].sum(-1), a[..., 2].sum(-1)
        mu = s / c
        var = s2 / c - mu ** 2
        return mu / np.sqrt(var) * math.sqrt(252)

    srs = {n: sr_of(mstats[n][idx]) for n in names}
    out = {}
    for n in names:
        dlt = srs[n] - srs[base]
        out[n] = {"boot_sr_se": float(np.std(srs[n])),
                  "dSR_vs_base_lo95": float(np.percentile(dlt, 2.5)), "dSR_vs_base_hi95": float(np.percentile(dlt, 97.5)),
                  "dSR_vs_base_p_le0": float(np.mean(dlt <= 0)) if n != base else float("nan")}
    return out


def evaluate_variants(p: pd.DataFrame, w: pd.DataFrame, cal: pd.DataFrame) -> pd.DataFrame:
    days_all = pd.DatetimeIndex(cal["date"])
    rows, monthly_rows = [], []
    daily_store = {}
    for sleeve in ("A", "C"):
        col = "A_ES" if sleeve == "A" else "C_ZN"
        first = w.loc[w[col] != 0, "date"].min()
        start = days_all[days_all.searchsorted(first) - 1]       # entry close
        samples = {
            "IS": (start, IS_END),
            "IS_pre_pub": (start, PUB_SPLIT_C - pd.Timedelta(days=1)) if sleeve == "C" else None,
            "IS_post_pub": (PUB_SPLIT_C, IS_END) if sleeve == "C" else None,
            "later": LATER,
            "IS_excl_vendor_hole_months": (start, IS_END),
        }
        dv = {v: variant_daily(p, w, cal, sleeve, v) for v in VARIANTS}
        daily_store[sleeve] = dv
        for smp, rng in samples.items():
            if rng is None:
                continue
            days = days_all[(days_all >= rng[0]) & (days_all <= rng[1])]
            if smp == "IS_excl_vendor_hole_months":
                bad = HOLE_MONTHS[sleeve]
                days = days[~days.to_period("M").astype(str).isin(bad)]
            years = len(days) / 252
            months = pd.period_range(days[0], days[-1], freq="M")
            for cl, cm in COST_LEVELS.items():
                xs = {v: full_calendar_series(dv[v], days, cm) for v in VARIANTS}
                boot = boot_sharpe_diff(xs, "base", months) if smp in ("IS", "IS_pre_pub", "IS_post_pub") else None
                if smp == "IS_excl_vendor_hole_months" and cl != "1x":
                    continue
                for v in VARIANTS:
                    x = xs[v]
                    d = dv[v]
                    dd = d[d.index.isin(days)]
                    mp = (dd["pnl"] - cm * dd["cost"]).groupby(dd["evT"]).sum()
                    mp = mp[mp.index.notna()]
                    if smp == "IS_excl_vendor_hole_months":
                        mp = mp[~pd.DatetimeIndex(mp.index).to_period("M").astype(str).isin(HOLE_MONTHS[sleeve])]
                    # robustness: Sharpe without the variant's single best window (all days of that month dropped)
                    best = pd.Timestamp(mp.idxmax()) if len(mp) else None
                    x_ex = x[x.index.to_period("M") != best.to_period("M")] if best is not None else x
                    sr = sharpe(x)
                    row = {"sleeve": sleeve, "variant": v, "cost": cl, "sample": smp,
                           "start": days[0].date(), "end": days[-1].date(), "years": round(years, 2),
                           "sharpe": sr, "sharpe_se_formula": sr_se(sr, years),
                           "best_window": best.date() if best is not None else None,
                           "best_window_share_of_total": float(mp.max() / mp.sum()) if len(mp) and mp.sum() != 0 else float("nan"),
                           "sharpe_ex_best_window": sharpe(x_ex),
                           "ann_mean_pct": x.mean() * 252 * 100, "ann_vol_pct": x.std() * math.sqrt(252) * 100,
                           "n_windows": int(len(mp)), "mean_window_bp": mp.mean() * 1e4, "t_nw_window": nw_t(mp.to_numpy(), 3),
                           "hit_rate": float((mp > 0).mean()) if len(mp) else float("nan"),
                           "turnover_per_window": float(dd["turn"].sum() / max(len(mp), 1)),
                           "cost_bp_per_window_1x": float(dd["cost"].sum() / max(len(mp), 1) * 1e4)}
                    if boot is not None:
                        row.update(boot[v])
                    rows.append(row)
                    if cl == "1x":
                        for T_, val in mp.items():
                            monthly_rows.append({"sleeve": sleeve, "variant": v, "T": T_, "pnl_net1x_bp": val * 1e4})
    res = pd.DataFrame(rows)
    mp = pd.DataFrame(monthly_rows).drop_duplicates(["sleeve", "variant", "T"])
    mp.to_csv(HERE / "variant_monthly_pnl.csv", index=False)
    return res, daily_store


def paired_month_diff(daily_store, w: pd.DataFrame, cal: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sleeve, dv in daily_store.items():
        for cl, cm in COST_LEVELS.items():
            mps = {}
            for v, d in dv.items():
                m = (d["pnl"] - cm * d["cost"]).groupby(d["evT"]).sum()
                mps[v] = m[m.index.notna()]
            for smp, (a, b) in {"IS": (pd.Timestamp("2000-01-01"), IS_END), "later": LATER}.items():
                base = mps["base"]
                base = base[(base.index >= a) & (base.index <= b)]
                for v in VARIANTS:
                    x = mps[v].reindex(base.index).fillna(0.0) - base
                    rows.append({"sleeve": sleeve, "variant": v, "cost": cl, "sample": smp, "n": len(x),
                                 "mean_diff_bp_per_window": x.mean() * 1e4, "t_nw_diff": nw_t(x.to_numpy(), 3)})
    return pd.DataFrame(rows)



def window_block_decomposition(p: pd.DataFrame, w: pd.DataFrame) -> pd.DataFrame:
    """Base-variant window P&L of each sleeve split into ET-hour blocks and window days (per-window sums)."""
    wi = w.set_index("date")
    rows = []
    for sleeve, legs in (("A", [("ES", "A_ES"), ("ZN", "A_ZN")]), ("C", [("ZN", "C_ZN")])):
        parts = []
        for root, col in legs:
            pr = p[p["root"] == root].copy()
            pr["W"] = pr["rd"].map(wi[col]).fillna(0.0)
            pr = pr[pr["W"] != 0].copy()
            pr["evT"] = pr["rd"].map(wi[f"{sleeve}_T"])
            pr["off"] = pr["rd"].map(wi[f"{sleeve}_off"]).astype(int)
            pr["x"] = pr["W"] * pr["ret_simple"] * 1e4
            pr["leg"] = root
            parts.append(pr)
        d = pd.concat(parts)
        d["block"] = d["hour_et"].map(HOUR2BLOCK)
        d["part"] = np.where((d["date_et"] == d["rd"]) & d["hour_et"].between(9, 15), "day_09_16", "night_16_09")
        samples = {"IS": d["rd"] <= IS_END, "later": d["rd"] >= LATER[0]}
        if sleeve == "C":
            samples["IS_pre_pub"] = d["rd"] < PUB_SPLIT_C
            samples["IS_post_pub"] = (d["rd"] >= PUB_SPLIT_C) & (d["rd"] <= IS_END)
        for smp, m in samples.items():
            ds = d[m]
            Ts = ds["evT"].unique()
            tot = ds.groupby("evT")["x"].sum().reindex(Ts).fillna(0.0)
            for dim in ("block", "part", "off", "leg"):
                piv = ds.groupby(["evT", dim])["x"].sum().unstack().reindex(Ts).fillna(0.0).sort_index()
                for c in piv.columns:
                    y = piv[c]
                    rows.append({"sleeve": sleeve, "sample": smp, "dimension": dim, "level": str(c), "n_windows": len(Ts),
                                 "mean_bp_per_window": y.mean(), "t_nw": nw_t(y.to_numpy(), 3),
                                 "share_of_window_mean": y.mean() / tot.mean() if tot.mean() != 0 else float("nan"),
                                 "n_hours_in_level": len(BLOCKS.get(str(c), [])) if dim == "block" else np.nan})
            rows.append({"sleeve": sleeve, "sample": smp, "dimension": "total", "level": "window", "n_windows": len(Ts),
                         "mean_bp_per_window": tot.mean(), "t_nw": nw_t(tot.sort_index().to_numpy(), 3),
                         "share_of_window_mean": 1.0, "n_hours_in_level": np.nan})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- validation

def validate_baseline(daily_store, w: pd.DataFrame) -> pd.DataFrame:
    f = pd.read_parquet(GQH / "futures_1600.parquet")
    rf = pd.read_parquet(GQH / "rf_daily.parquet").set_index("date")["rf"]
    rows = []
    wi = w.set_index("date")
    ex = {}
    for tk in ("ES16", "ZN16"):
        s = f[f["ticker"] == tk].set_index("date")["close"].sort_index()
        ex[tk] = s.pct_change() - rf.reindex(s.index).fillna(0.0)
    for sleeve, legs in (("A", [("ES16", "A_ES"), ("ZN16", "A_ZN")]), ("C", [("ZN16", "C_ZN")])):
        dly = sum(wi[col] * ex[tk].reindex(wi.index).fillna(0.0) for tk, col in legs)
        hb = daily_store[sleeve]["base"]["pnl"].reindex(wi.index).fillna(0.0)
        h16 = daily_store[sleeve]["exit_1600"]["pnl"].reindex(wi.index).fillna(0.0)
        held = (wi["A_ES" if sleeve == "A" else "C_ZN"] != 0)
        dd = (hb - dly)[held]
        for smp, m in (("IS", dd.index <= IS_END), ("later", dd.index >= LATER[0])):
            x = dd[m] * 1e4
            rows.append({"sleeve": sleeve, "sample": smp, "held_days": int(m.sum()),
                         "mean_abs_diff_bp": float(x.abs().mean()), "max_abs_diff_bp": float(x.abs().max()),
                         "days_gt_1bp": int((x.abs() > 1).sum()),
                         "sum_hourly_bp": float(hb[held][m].sum() * 1e4), "sum_daily16_bp": float(dly[held][m].sum() * 1e4),
                         "exit_1600_equals_base": bool(np.allclose(hb.values, h16.values))})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- part 3: OOS diagnosis of sleeve C

def oos_diag_C(p: pd.DataFrame, w: pd.DataFrame, cal: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    wi = w.set_index("date")
    pr = p[p["root"] == "ZN"].copy()
    pr["W"] = pr["rd"].map(wi["C_ZN"]).fillna(0.0)
    pr["off"] = pr["rd"].map(wi["C_off"])
    pr["evT"] = pr["rd"].map(wi["C_T"])
    pr = pr[pr["W"] != 0].copy()
    pr["x_bp"] = pr["W"] * pr["ret_simple"] * 1e4       # sleeve-weighted contribution (bp of capital)
    pr["u_bp"] = pr["ret_simple"] * 1e4                 # unit long ZN
    pr["block"] = pr["hour_et"].map(HOUR2BLOCK)
    pr["same_day"] = pr["date_et"] == pr["rd"]
    pr["sample"] = np.where(pr["rd"] <= IS_END, "IS", "later")
    pr["post_pub"] = pr["rd"] >= PUB_SPLIT_C
    rows = []
    for (smp, off, blk), g in pr.groupby(["sample", "off", "block"]):
        per = g.groupby("evT")[["x_bp", "u_bp"]].sum()
        nm = pr[pr["sample"] == smp]["evT"].nunique()
        per = per.reindex(pr[pr["sample"] == smp]["evT"].unique()).fillna(0.0)
        rows.append({"sample": smp, "offset": int(off), "block": blk, "n_windows": nm,
                     "mean_weighted_bp": per["x_bp"].mean(), "total_weighted_bp": per["x_bp"].sum(),
                     "t_nw_weighted": nw_t(per["x_bp"].sort_index().to_numpy(), 2),
                     "mean_unit_bp": per["u_bp"].mean(), "t_nw_unit": nw_t(per["u_bp"].sort_index().to_numpy(), 2)})
    hours = pd.DataFrame(rows)
    # also by post-publication in-sample
    rows = []
    for smp, g0 in (("IS_post_pub", pr[(pr["sample"] == "IS") & pr["post_pub"]]), ("IS_pre_pub", pr[(pr["sample"] == "IS") & ~pr["post_pub"]])):
        for (off, blk), g in g0.groupby(["off", "block"]):
            per = g.groupby("evT")[["x_bp", "u_bp"]].sum().reindex(g0["evT"].unique()).fillna(0.0)
            rows.append({"sample": smp, "offset": int(off), "block": blk, "n_windows": g0["evT"].nunique(),
                         "mean_weighted_bp": per["x_bp"].mean(), "total_weighted_bp": per["x_bp"].sum(),
                         "t_nw_weighted": nw_t(per["x_bp"].sort_index().to_numpy(), 2),
                         "mean_unit_bp": per["u_bp"].mean(), "t_nw_unit": nw_t(per["u_bp"].sort_index().to_numpy(), 2)})
    hours = pd.concat([hours, pd.DataFrame(rows)], ignore_index=True)
    # per window in the later sample: total, day part, night part, 15:00 bar of T
    lw = pr[pr["sample"] == "later"]
    m = lw.groupby("evT").apply(lambda g: pd.Series({
        "W": g["W"].iloc[0],
        "window_bp": g["x_bp"].sum(),
        "day_09_16_bp": g.loc[g["same_day"] & g["hour_et"].between(9, 15), "x_bp"].sum(),
        "night_16_09_bp": g.loc[~(g["same_day"] & g["hour_et"].between(9, 15)), "x_bp"].sum(),
        "T_bar_15_bp": g.loc[(g["off"] == 0) & (g["hour_et"] == 15) & g["same_day"], "x_bp"].sum(),
        "T_bars_09_15_bp": g.loc[(g["off"] == 0) & g["hour_et"].between(9, 14) & g["same_day"], "x_bp"].sum(),
    }))
    return hours, m.reset_index()


# --------------------------------------------------------------------------- main

def main() -> None:
    p = load_panel()
    cal = load_calendar()
    w = pd.read_parquet(HERE / "sleeve_weights.parquet")
    w["date"] = w["date"].astype("datetime64[ns]")
    for c in ("A_T", "C_T"):
        w[c] = w[c].astype("datetime64[ns]")
    log("panel rows", len(p), "calendar days", len(cal))
    # vendor holes inside sleeve windows
    om = p[p["gap_type"] == "other_missing"][["root", "bar_start_et", "rd"]]
    wi = w.set_index("date")
    for s, col in (("A", "A_ES"), ("C", "C_ZN")):
        inwin = om[om["rd"].map(wi[col]).fillna(0) != 0]
        log(f"other_missing bars inside sleeve {s} windows:", inwin.to_dict("records"))

    profiles(p, cal, w)
    volume_profile(cal)
    log("profiles written")
    res, store = evaluate_variants(p, w, cal)
    pdiff = paired_month_diff(store, w, cal)
    res = res.merge(pdiff, on=["sleeve", "variant", "cost", "sample"], how="left")
    res.to_csv(HERE / "variants.csv", index=False)
    val = validate_baseline(store, w)
    val.to_csv(HERE / "validation_baseline.csv", index=False)
    log(val.to_string())
    window_block_decomposition(p, w).to_csv(HERE / "window_block_decomposition.csv", index=False)
    hours, months = oos_diag_C(p, w, cal)
    hours.to_csv(HERE / "oos_diag_C_hours.csv", index=False)
    months.to_csv(HERE / "oos_diag_C_months.csv", index=False)
    pd.set_option("display.width", 250)
    show = res[res["sample"].isin(["IS", "later"])][["sleeve", "variant", "cost", "sample", "sharpe", "sharpe_se_formula",
                                                      "mean_window_bp", "t_nw_window", "hit_rate", "cost_bp_per_window_1x",
                                                      "dSR_vs_base_lo95", "dSR_vs_base_hi95", "dSR_vs_base_p_le0",
                                                      "mean_diff_bp_per_window", "t_nw_diff"]]
    log(show.round(3).to_string())
    log("distinct strategy variants:", 2 * len(DISTINCT_VARIANTS), "(exit_1600 equals base by construction)")
    (HERE / "run_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
