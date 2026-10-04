"""Overnight vs intraday returns and the 'overnight drift' in ES and ZN (hourly study).

Pre-specification (fixed before any return in the panel was looked at; written to prespec.json on every run):

Literature
  Boyarchenko, Larsen & Whelan, "The Overnight Drift", FRBNY Staff Report 917, first public version
  February 2020 (revised August 2022). ES futures earn most of their close-to-close return overnight, concentrated
  in the European-open hours (largest in 02:00-03:00 ET; positive in almost every interval 01:00-04:00 ET).
  Their strategies: CT C (16:15->16:15), CT O (16:15->09:30; 16:15->08:30 in Table IX), OT C (09:30->16:15),
  OD (02:00->03:00), OD+ (01:30->03:30), BtD (OD+ only after a negative closing order imbalance). They report the
  OD/OD+ Sharpe falls from about 1.1/1.3 gross to -0.5/0.3 after bid-ask costs. The older overnight-vs-intraday
  papers (Cliff, Cooper & Gulen 2008; Kelly & Clark 2011) predate this sample, so the only usable
  publication split is February 2020: pre = 2010-06-08..2020-01-31, post = 2020-02-01..2024-10-02.
  ZN has no overnight-drift paper in hand: it is run as an out-of-literature check of the same mechanism.

Hourly approximations (the data has hourly bars whose timestamp is the bar START)
  close 16:00 ET = close of the bar starting 15:00 ET; the 09:30 cash open is not a bar boundary, so the
  overnight/day split is at 09:00 ET (primary: the 09:00-10:00 bar straddles the open and Boyarchenko et al.
  report negative 'opening hour' returns there) or 10:00 ET (variant). OD+ 01:30-03:30 is not available; the
  closest hourly windows are 01:00-04:00 (primary, as briefed) and 02:00-03:00 (OD hour, variant).

Primary strategies per root (one round trip per day)
  ON_16_09   long from 16:00 ET (prev NYSE day) to 09:00 ET (day d), flat otherwise
  EU_01_04   long 01:00 -> 04:00 ET on day d
  DAY_09_16  long 09:00 -> 16:00 ET on day d
  BH         buy-and-hold (16:00 -> 16:00), costs only at contract rolls
Variants (all reported)
  ON entry {15,16,17}:00 x exit {08,09,10}:00; EU {01-04, 02-03, 02-04}; DAY entry {08,09,10} x exit {15,16};
  conditional (Boyarchenko asymmetric reversal / BtD, closing order flow proxied by price because the data has no
  signed volume): EU_01_04 and ON_17_09 only after (i) a negative 15:00-16:00 ET return or (ii) a negative
  16:00->16:00 day return, both known at 16:00 ET of the previous NYSE day (ON entry moved to 17:00 so the trade
  happens at a later bar than the signal);
  exposure tilts (does timing add to buy-and-hold?): hold w_on overnight (16->09) and 1 during the day,
  w_on in {0.5, 1.5, 2, 3}; hold w_eu during 01-04 and 1 otherwise, w_eu in {0, 0.5, 1.5, 2, 3}.
Costs: one-way per unit notional traded, ES 1.0 bp, ZN 1.5 bp; levels gross, 1x, 2x, plus a tick sensitivity
  (one tick per one-way at the entry price: ES 0.25 pt, ZN 1/64 pt). A window that spans a contract roll pays one
  extra round trip; buy-and-hold pays one round trip per roll.
Inference: Newey-West t (Bartlett, lag floor(4 (T/100)^(2/9))), Sharpe SE sqrt((1+SR^2/2)/years), paired circular
  block bootstrap (block 21 days, 5000 draws) for Sharpe differences, mean-variance spanning regression of each
  timed strategy on buy-and-hold (alpha > 0 net of cost <=> adding it raises the attainable Sharpe).
Samples: in-sample = day d <= 2024-10-02; later window 2024-10-03..2026-10-02 is descriptive only. Every choice
  among variants uses in-sample data only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

OUT = Path(r"<scratch>/intraday_study/overnight_drift")
DATA = Path(r"<scratch>/intraday_study/data")
PANEL = DATA / "hourly_panel.parquet"
CALF = DATA / "nyse_calendar_offsets.parquet"
TZ = "America/New_York"

START = pd.Timestamp("2010-06-08")
IS_END = pd.Timestamp("2024-10-02")
PUB = pd.Timestamp("2020-02-01")       # FRBNY Staff Report 917, February 2020
LATER_START = pd.Timestamp("2024-10-03")
END = pd.Timestamp("2026-10-02")
COST = {"ES": 1.0e-4, "ZN": 1.5e-4}
TICK = {"ES": 0.25, "ZN": 1.0 / 64.0}
ROOTS = ["ES", "ZN"]
SAMPLES = {
    "IS_full": (START, IS_END),
    "IS_pre_pub": (START, PUB - pd.Timedelta(days=1)),
    "IS_post_pub": (PUB, IS_END),
    "later_descriptive": (LATER_START, END),
}
BOOT_B = 5000
BOOT_BLOCK = 21
RNG = np.random.default_rng(20261003)

LOG_LINES: list[str] = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG_LINES.append(s)


# ----------------------------------------------------------------------------------------------- statistics
def nw_lag(n: int) -> int:
    return int(np.floor(4 * (n / 100.0) ** (2.0 / 9.0)))


def nw_tstat(x: np.ndarray, lag: int | None = None) -> float:
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 10:
        return np.nan
    L = nw_lag(n) if lag is None else lag
    m = x.mean()
    e = x - m
    g0 = e @ e / n
    s = g0
    for l in range(1, L + 1):
        s += 2 * (1 - l / (L + 1)) * (e[l:] @ e[:-l]) / n
    if s <= 0:
        return np.nan
    return m / np.sqrt(s / n)


def sharpe(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    sd = x.std(ddof=1)
    return np.nan if sd == 0 or np.isnan(sd) else x.mean() / sd * np.sqrt(252)


def sharpe_se(sr: float, n: int) -> float:
    years = n / 252.0
    return np.sqrt((1 + sr ** 2 / 2) / years)


def max_drawdown(x: np.ndarray) -> float:
    eq = np.cumprod(1 + np.asarray(x, float))
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1).min())


def block_boot_idx(n: int, B: int, block: int) -> np.ndarray:
    nb = int(np.ceil(n / block))
    starts = RNG.integers(0, n, size=(B, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
    return idx.reshape(B, -1)[:, :n]


def boot_sharpe_diff(x: np.ndarray, y: np.ndarray, idx: np.ndarray) -> dict:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    d0 = sharpe(x) - sharpe(y)
    xb = x[idx]
    yb = y[idx]
    srx = xb.mean(1) / xb.std(1, ddof=1) * np.sqrt(252)
    sry = yb.mean(1) / yb.std(1, ddof=1) * np.sqrt(252)
    d = srx - sry
    p = 2 * min((d <= 0).mean(), (d >= 0).mean())
    return {"sr_x": sharpe(x), "sr_y": sharpe(y), "diff": d0, "boot_se": d.std(ddof=1),
            "ci_lo": np.quantile(d, 0.025), "ci_hi": np.quantile(d, 0.975), "p_two_sided": min(p, 1.0)}


# ----------------------------------------------------------------------------------------------- data
def load():
    p = pd.read_parquet(PANEL)
    cal = pd.read_parquet(CALF)
    cal["date"] = pd.to_datetime(cal["date"]).astype("datetime64[ns]")
    days = cal.loc[(cal["date"] >= START) & (cal["date"] <= END), "date"].reset_index(drop=True)
    allcal = pd.DatetimeIndex(cal["date"])
    pos = allcal.get_indexer(pd.DatetimeIndex(days))
    prev = pd.Series(allcal[pos - 1])
    prev2 = pd.Series(allcal[pos - 2])
    D = pd.DataFrame({"d": days, "prev": prev, "prev2": prev2})
    return p, D


def et_ns(dates: pd.Series, hour: int) -> np.ndarray:
    ts = pd.DatetimeIndex(dates) + pd.Timedelta(hours=hour)
    return ts.tz_localize(TZ).tz_convert("UTC").asi8


class RootArrays:
    def __init__(self, df: pd.DataFrame):
        df = df.sort_values("bar_end_utc").reset_index(drop=True)
        self.df = df
        self.end = df["bar_end_utc"].astype("int64").to_numpy() if df["bar_end_utc"].dtype.kind == "i" else \
            pd.DatetimeIndex(df["bar_end_utc"]).asi8
        r = df["ret_log"].fillna(0.0).to_numpy()
        self.C0 = np.concatenate([[0.0], np.cumsum(r)])            # C0[k+1] = cum log ret through bar k
        self.R0 = np.concatenate([[0], np.cumsum(df["is_roll"].to_numpy().astype(int))])
        self.close = df["close"].to_numpy()
        om = df["gap_type"] == "other_missing"
        hs = (pd.DatetimeIndex(df.loc[om, "prev_bar_start_utc"]) + pd.Timedelta(hours=1)).asi8
        he = pd.DatetimeIndex(df.loc[om, "bar_end_utc"]).asi8
        self.holes = list(zip(hs, he))

    def window(self, a_ns: np.ndarray, b_ns: np.ndarray) -> dict:
        ia = np.searchsorted(self.end, a_ns, side="right") - 1    # last bar end <= a (-1 if none)
        ib = np.searchsorted(self.end, b_ns, side="right") - 1
        nb = ib - ia
        lr = self.C0[ib + 1] - self.C0[ia + 1]
        # rolls strictly inside the window: bars ia+2..ib (a roll on the first bar = enter in the new contract)
        inside = np.where(nb >= 2, self.R0[np.maximum(ib, 0) + 1] - self.R0[np.minimum(ia + 2, len(self.end))], 0)
        inside = np.maximum(inside, 0)
        rolls_all = np.where(nb >= 1, self.R0[np.maximum(ib, 0) + 1] - self.R0[ia + 1], 0)
        px = np.where(ia >= 0, self.close[np.maximum(ia, 0)], np.nan)
        hole = np.zeros(len(a_ns), bool)
        for h0, h1 in self.holes:
            hole |= (a_ns < h1) & (b_ns > h0)
        return {"ret": np.expm1(lr), "logret": lr, "nbars": nb, "rolls_inside": inside, "rolls_all": rolls_all,
                "entry_px": px, "hole": hole, "ia": ia, "ib": ib}


# ----------------------------------------------------------------------------------------------- variants
def variant_specs():
    V = []
    for e in (15, 16, 17):
        for x in (8, 9, 10):
            V.append(dict(name=f"ON_{e:02d}_{x:02d}", family="overnight", sday="prev", sh=e, eday="same", eh=x,
                          cond=None, primary=(e == 16 and x == 9)))
    for (s, x) in ((1, 4), (2, 3), (2, 4)):
        V.append(dict(name=f"EU_{s:02d}_{x:02d}", family="eu_open", sday="same", sh=s, eday="same", eh=x,
                      cond=None, primary=(s == 1 and x == 4)))
    for e in (8, 9, 10):
        for x in (15, 16):
            V.append(dict(name=f"DAY_{e:02d}_{x:02d}", family="day_session", sday="same", sh=e, eday="same", eh=x,
                          cond=None, primary=(e == 9 and x == 16)))
    V.append(dict(name="BH", family="buy_hold", sday="prev", sh=16, eday="same", eh=16, cond=None, primary=True))
    for base, (sday, sh, eh) in (("EU_01_04", ("same", 1, 4)), ("ON_17_09", ("prev", 17, 9))):
        for c in ("lasthour_neg", "dayret_neg"):
            V.append(dict(name=f"{base}|{c}", family="conditional", sday=sday, sh=sh, eday="same", eh=eh, cond=c,
                          primary=False))
    for w in (0.5, 1.5, 2.0, 3.0):
        V.append(dict(name=f"TILT_ON_w{w:g}", family="tilt_overnight", w=w, primary=False))
    for w in (0.0, 0.5, 1.5, 2.0, 3.0):
        V.append(dict(name=f"TILT_EU_w{w:g}", family="tilt_eu", w=w, primary=False))
    return V


def build_daily(p: pd.DataFrame, D: pd.DataFrame):
    """Daily strategy returns per root and variant: gross, cost (1x), cost (tick), trade flag."""
    out = {}
    specs = variant_specs()
    for root in ROOTS:
        A = RootArrays(p[p["root"] == root])
        c1 = COST[root]
        res = {}
        hole_any = np.zeros(len(D), bool)
        # windows
        for v in specs:
            if v["family"].startswith("tilt"):
                continue
            a = et_ns(D["prev"] if v["sday"] == "prev" else D["d"], v["sh"])
            b = et_ns(D["d"], v["eh"])
            w = A.window(a, b)
            hole_any |= w["hole"]
            res[v["name"]] = w
        # signals known at 16:00 ET of the previous NYSE day
        sig_lh = A.window(et_ns(D["prev"], 15), et_ns(D["prev"], 16))
        sig_dr = A.window(et_ns(D["prev2"], 16), et_ns(D["prev"], 16))
        hole_any |= sig_lh["hole"] | sig_dr["hole"]
        excl = hole_any.copy()
        daily = {}
        for v in specs:
            name = v["name"]
            if v["family"].startswith("tilt"):
                continue
            w = res[name]
            g = w["ret"].copy()
            trade = w["nbars"] >= 1
            if v["cond"] == "lasthour_neg":
                on = (sig_lh["nbars"] >= 1) & (sig_lh["ret"] < 0)
                trade &= on
            elif v["cond"] == "dayret_neg":
                on = (sig_dr["nbars"] >= 1) & (sig_dr["ret"] < 0)
                trade &= on
            g = np.where(trade, g, 0.0)
            if v["family"] == "buy_hold":
                units = 2.0 * w["rolls_all"]                          # one round trip per roll
            else:
                units = np.where(trade, 2.0 + 2.0 * w["rolls_inside"], 0.0)
            tick_cost = TICK[root] / w["entry_px"]
            tick_cost = np.where(np.isnan(tick_cost), c1, tick_cost)
            daily[name] = pd.DataFrame({"gross": g, "units": units, "c1": units * c1, "ctick": units * tick_cost,
                                        "trade": trade.astype(int), "nbars": np.where(trade, w["nbars"], 0)})
        # tilts built from the primary overnight/day legs and the EU leg vs the rest of the 16:00 day
        on, dy, bh, eu = res["ON_16_09"], res["DAY_09_16"], res["BH"], res["EU_01_04"]
        for v in specs:
            if v["family"] == "tilt_overnight":
                wt = v["w"]
                g = (1 + wt * on["ret"]) * (1 + dy["ret"]) - 1
                units = 2.0 * abs(wt - 1.0) * (on["nbars"] >= 1) + 2.0 * bh["rolls_all"]
            elif v["family"] == "tilt_eu":
                wt = v["w"]
                rest = (1 + bh["ret"]) / (1 + eu["ret"]) - 1             # 16:00->16:00 excluding 01-04
                g = (1 + wt * eu["ret"]) * (1 + rest) - 1
                units = 2.0 * abs(wt - 1.0) * (eu["nbars"] >= 1) + 2.0 * bh["rolls_all"]
            else:
                continue
            tick_cost = TICK[root] / bh["entry_px"]
            tick_cost = np.where(np.isnan(tick_cost), c1, tick_cost)
            daily[v["name"]] = pd.DataFrame({"gross": g, "units": units, "c1": units * c1,
                                             "ctick": units * tick_cost, "trade": (units > 0).astype(int),
                                             "nbars": bh["nbars"]})
        for k in daily:
            daily[k].index = pd.DatetimeIndex(D["d"])
        out[root] = dict(daily=daily, excl=pd.Series(excl, index=pd.DatetimeIndex(D["d"])), res=res, A=A,
                         sig_lh=sig_lh, sig_dr=sig_dr)
        log(f"[{root}] days {len(D)}, excluded (vendor hole / outage overlap with any window or signal): "
            f"{int(excl.sum())} -> {list(pd.DatetimeIndex(D['d'])[excl].strftime('%Y-%m-%d'))}")
    return out


def net_series(dd: pd.DataFrame, level: str) -> pd.Series:
    if level == "gross":
        return dd["gross"]
    if level == "1x":
        return dd["gross"] - dd["c1"]
    if level == "2x":
        return dd["gross"] - 2 * dd["c1"]
    if level == "tick1":
        return dd["gross"] - dd["ctick"]
    raise ValueError(level)


# ----------------------------------------------------------------------------------------------- tables
def hourly_table(p: pd.DataFrame) -> pd.DataFrame:
    rows = []
    q = p[p["ret_date_1600"].notna() & p["ret_simple"].notna()].copy()
    for root in ROOTS:
        r = q[q["root"] == root]
        for filt in ("all_ex_other_missing", "clean_1h"):
            if filt == "all_ex_other_missing":
                rr = r[r["gap_type"] != "other_missing"]
            else:
                rr = r[r["gap_type"].isin(["none", "daily_break"])]
            for sname, (s0, s1) in SAMPLES.items():
                x = rr[(rr["ret_date_1600"] >= s0) & (rr["ret_date_1600"] <= s1)]
                ndays = x["ret_date_1600"].nunique()
                years = ndays / 252.0
                tot = x["ret_log"].sum()
                for h in range(24):
                    y = x[x["hour_et"] == h].sort_values("bar_end_utc")
                    if len(y) == 0:
                        continue
                    sr = y["ret_simple"].to_numpy()
                    rows.append(dict(root=root, bar_filter=filt, sample=sname, hour_et_start=h,
                                     window=f"{h:02d}:00-{(h + 1) % 24:02d}:00", n_bars=len(y),
                                     mean_simple_bp=sr.mean() * 1e4, mean_log_bp=y["ret_log"].mean() * 1e4,
                                     nw_t=nw_tstat(sr), std_bp=sr.std(ddof=1) * 1e4,
                                     ann_contrib_logpct=y["ret_log"].sum() / years * 100,
                                     share_of_total_logret=y["ret_log"].sum() / tot,
                                     hit_rate=(sr > 0).mean(),
                                     sharpe_if_only_hour=sr.mean() / sr.std(ddof=1) * np.sqrt(len(y) / years),
                                     n_days_sample=ndays, total_logret_pct_per_yr=tot / years * 100))
    return pd.DataFrame(rows)


SEG_DEF = [
    ("A_post_close_16_18", "16:00-18:00 ET (16:00-17:00 bar; 17:00 bar pre-2015)"),
    ("B_asia_18_01", "18:00-01:00 ET (incl. Sunday reopen, spans weekend)"),
    ("C_eu_open_01_04", "01:00-04:00 ET"),
    ("D_eu_morning_04_09", "04:00-09:00 ET (incl. 08:30 macro releases)"),
    ("Z_nyse_holiday_session", "CME session bars on NYSE-holiday weekdays before 18:00 (overnight of next NYSE day)"),
    ("E_us_open_hour_09_10", "09:00-10:00 ET (straddles 09:30 cash open)"),
    ("F_us_morning_10_13", "10:00-13:00 ET"),
    ("G_us_afternoon_13_15", "13:00-15:00 ET"),
    ("H_last_hour_15_16", "15:00-16:00 ET (proxy for the last half-hour)"),
]
AGG = {
    "ON_16_09 (overnight: 16:00 prev -> 09:00)": ["A_post_close_16_18", "B_asia_18_01", "C_eu_open_01_04",
                                                  "D_eu_morning_04_09", "Z_nyse_holiday_session"],
    "DAY_09_16 (day: 09:00 -> 16:00)": ["E_us_open_hour_09_10", "F_us_morning_10_13", "G_us_afternoon_13_15",
                                        "H_last_hour_15_16"],
    "ON_16_10 (overnight incl. opening hour)": ["A_post_close_16_18", "B_asia_18_01", "C_eu_open_01_04",
                                                "D_eu_morning_04_09", "Z_nyse_holiday_session",
                                                "E_us_open_hour_09_10"],
    "DAY_10_16 (day excl. opening hour)": ["F_us_morning_10_13", "G_us_afternoon_13_15", "H_last_hour_15_16"],
    "US_MORNING_09_13 (incl. opening hour)": ["E_us_open_hour_09_10", "F_us_morning_10_13"],
}


def seg_of(df: pd.DataFrame) -> pd.Series:
    h = df["hour_et"]
    s = pd.Series("", index=df.index, dtype=object)
    s[h.isin([16, 17])] = "A_post_close_16_18"
    s[h.isin([18, 19, 20, 21, 22, 23, 0])] = "B_asia_18_01"
    s[h.isin([1, 2, 3])] = "C_eu_open_01_04"
    s[h.isin([4, 5, 6, 7, 8])] = "D_eu_morning_04_09"
    s[h == 9] = "E_us_open_hour_09_10"
    s[h.isin([10, 11, 12])] = "F_us_morning_10_13"
    s[h.isin([13, 14])] = "G_us_afternoon_13_15"
    s[h == 15] = "H_last_hour_15_16"
    s[df["cme_non_nyse_session"]] = "Z_nyse_holiday_session"
    return s


def segment_table(p: pd.DataFrame, built: dict, D: pd.DataFrame):
    rows = []
    segdaily = {}
    for root in ROOTS:
        r = p[(p["root"] == root) & p["ret_date_1600"].notna() & p["ret_log"].notna()].copy()
        r["seg"] = seg_of(r)
        piv = r.pivot_table(index="ret_date_1600", columns="seg", values="ret_log", aggfunc="sum").reindex(
            pd.DatetimeIndex(D["d"])).fillna(0.0)
        for s, _ in SEG_DEF:
            if s not in piv:
                piv[s] = 0.0
        piv = piv[[s for s, _ in SEG_DEF]]
        sub = r[r["hour_et"].isin([2, 3]) & ~r["cme_non_nyse_session"]].groupby("ret_date_1600")["ret_log"].sum()
        piv["EU_02_04 (sub-window of C)"] = sub.reindex(piv.index).fillna(0.0)
        sub = r[(r["hour_et"] == 2) & ~r["cme_non_nyse_session"]].groupby("ret_date_1600")["ret_log"].sum()
        piv["OD_02_03 (sub-window of C)"] = sub.reindex(piv.index).fillna(0.0)
        for k, comp in AGG.items():
            piv[k] = piv[comp].sum(axis=1)
        piv["TOTAL_16_16"] = piv[[s for s, _ in SEG_DEF]].sum(axis=1)
        excl = built[root]["excl"]
        piv = piv[~excl.reindex(piv.index).fillna(True).to_numpy()]
        segdaily[root] = piv
        desc = dict(SEG_DEF)
        for sname, (s0, s1) in SAMPLES.items():
            x = piv[(piv.index >= s0) & (piv.index <= s1)]
            tot = x["TOTAL_16_16"]
            for col in x.columns:
                y = x[col].to_numpy()
                cov = np.cov(y, tot.to_numpy(), ddof=1)
                rows.append(dict(root=root, sample=sample_label(sname), segment=col,
                                 definition=desc.get(col, "aggregate / sub-window" if col != "TOTAL_16_16"
                                                     else "16:00 prev NYSE day -> 16:00"),
                                 n_days=len(y), mean_daily_log_bp=y.mean() * 1e4, nw_t=nw_tstat(y),
                                 ann_mean_logpct=y.mean() * 252 * 100, ann_vol_pct=y.std(ddof=1) * np.sqrt(252) * 100,
                                 sharpe_gross=sharpe(y), share_of_total_return=y.mean() / tot.mean(),
                                 share_of_total_variance=y.var(ddof=1) / tot.var(ddof=1),
                                 risk_share_beta=cov[0, 1] / cov[1, 1],
                                 return_minus_risk_share=y.mean() / tot.mean() - cov[0, 1] / cov[1, 1],
                                 hit_rate=(y[y != 0] > 0).mean() if (y != 0).any() else np.nan))
    return pd.DataFrame(rows), segdaily


def sample_label(s):
    return s


def sample_mask(idx: pd.DatetimeIndex, sname: str) -> np.ndarray:
    s0, s1 = SAMPLES[sname]
    return (idx >= s0) & (idx <= s1)


def strategy_table(built: dict) -> tuple[pd.DataFrame, dict]:
    rows = []
    series = {}
    specs = {v["name"]: v for v in variant_specs()}
    for root in ROOTS:
        excl = built[root]["excl"]
        for name, dd in built[root]["daily"].items():
            dd = dd[~excl.to_numpy()]
            v = specs[name]
            for level in ("gross", "1x", "2x", "tick1"):
                ns = net_series(dd, level)
                series[(root, name, level)] = ns
                for sname in SAMPLES:
                    m = sample_mask(ns.index, sname)
                    x = ns[m].to_numpy()
                    g = dd["gross"][m].to_numpy()
                    tr = dd["trade"][m].to_numpy()
                    n = len(x)
                    sr = sharpe(x)
                    trade_days = int(tr.sum())
                    rows.append(dict(
                        root=root, variant=name, family=v["family"], primary=v["primary"],
                        cost_level=level, sample=sname, n_days=n, years=n / 252.0, trade_days=trade_days,
                        ann_mean_pct=x.mean() * 252 * 100, ann_vol_pct=x.std(ddof=1) * np.sqrt(252) * 100,
                        sharpe=sr, sharpe_se=sharpe_se(sr, n), nw_t_mean=nw_tstat(x),
                        mean_bp_per_trade_day_gross=(g[tr == 1].mean() * 1e4) if trade_days else np.nan,
                        breakeven_oneway_cost_bp=((g.sum() / dd["units"][m].sum()) * 1e4)
                        if dd["units"][m].sum() > 0 else np.nan,
                        cost_drag_ann_pct=(g.mean() - x.mean()) * 252 * 100,
                        hit_rate_trade_days=(x[tr == 1] > 0).mean() if trade_days else np.nan,
                        max_drawdown_pct=max_drawdown(x) * 100,
                        avg_bars_held_per_day=dd["nbars"][m].mean(),
                    ))
    return pd.DataFrame(rows), series


def bootstrap_table(series: dict) -> pd.DataFrame:
    pairs = [("ON_16_09", "BH"), ("EU_01_04", "BH"), ("DAY_09_16", "BH"), ("ON_16_09", "DAY_09_16"),
             ("EU_01_04", "ON_16_09"), ("EU_01_04|lasthour_neg", "EU_01_04"), ("EU_01_04|dayret_neg", "EU_01_04"),
             ("ON_17_09|dayret_neg", "ON_17_09"), ("TILT_ON_w2", "BH"), ("TILT_EU_w2", "BH")]
    rows = []
    for root in ROOTS:
        for sname in ("IS_full", "IS_pre_pub", "IS_post_pub", "later_descriptive"):
            base = series[(root, "BH", "gross")]
            m = sample_mask(base.index, sname)
            idx = block_boot_idx(int(m.sum()), BOOT_B, BOOT_BLOCK)
            for level in ("gross", "1x", "2x"):
                for a, b in pairs:
                    x = series[(root, a, level)][m].to_numpy()
                    y = series[(root, b, level)][m].to_numpy()
                    r = boot_sharpe_diff(x, y, idx)
                    rows.append(dict(root=root, sample=sname, cost_level=level, x=a, y=b, **r))
    return pd.DataFrame(rows)


def spanning_table(series: dict) -> pd.DataFrame:
    """Regress each timed strategy (net) on buy-and-hold (net, same level). alpha>0 <=> it raises the attainable
    Sharpe; the max Sharpe of {BH, X} is sqrt(SR_BH^2 + AR^2) with AR = alpha / resid vol (annualised).
    A short overlay of X costs the same, so its alpha is -alpha_gross - cost."""
    rows = []
    for root in ROOTS:
        for xname in ("ON_16_09", "ON_16_10", "EU_01_04", "EU_02_03", "DAY_09_16", "EU_01_04|lasthour_neg",
                      "EU_01_04|dayret_neg", "ON_17_09|lasthour_neg", "ON_17_09|dayret_neg"):
            for sname in SAMPLES:
                for level in ("gross", "1x", "2x", "tick1"):
                    bh = series[(root, "BH", level)]
                    m = sample_mask(bh.index, sname)
                    y = series[(root, xname, level)][m].to_numpy()
                    yg = series[(root, xname, "gross")][m].to_numpy()
                    xb = bh[m].to_numpy()
                    n = len(y)
                    L = nw_lag(n)
                    X = sm.add_constant(xb)
                    f = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": L})
                    fg = sm.OLS(yg, X).fit(cov_type="HAC", cov_kwds={"maxlags": L})
                    a = f.params[0]
                    resid_sd = f.resid.std(ddof=2)
                    cost_daily = (yg - y).mean()
                    a_short = -fg.params[0] - cost_daily
                    ar_long = a / resid_sd * np.sqrt(252)
                    ar_short = a_short / resid_sd * np.sqrt(252)
                    sr_bh = sharpe(xb)
                    ar_best = max(ar_long, ar_short, 0.0)
                    # the spanning bound assumes BH may be held either way; only meaningful when BH is held long
                    combo = np.sqrt(sr_bh ** 2 + ar_best ** 2) if sr_bh > 0 else np.nan
                    units_day = cost_daily / COST[root] if level == "1x" else np.nan
                    be = (fg.params[0] / (units_day / 1.0)) * 1e4 if level == "1x" and units_day > 0 else np.nan
                    rows.append(dict(root=root, timed_strategy=xname, sample=sname, cost_level=level, n_days=n,
                                     alpha_ann_pct=a * 252 * 100, alpha_nw_t=f.tvalues[0], beta=f.params[1],
                                     resid_vol_ann_pct=resid_sd * np.sqrt(252) * 100,
                                     appraisal_long=ar_long, appraisal_short_overlay=ar_short,
                                     sharpe_bh=sr_bh, sharpe_max_combo=combo, sharpe_gain=combo - sr_bh,
                                     breakeven_oneway_cost_bp_for_alpha=be))
    return pd.DataFrame(rows)


def annual_table(series: dict) -> pd.DataFrame:
    rows = []
    for root in ROOTS:
        for name in ("ON_16_09", "EU_01_04", "DAY_09_16", "BH", "EU_01_04|lasthour_neg", "ON_17_09|lasthour_neg"):
            for level in ("gross", "1x"):
                s = series[(root, name, level)]
                for y, g in s.groupby(s.index.year):
                    rows.append(dict(root=root, variant=name, cost_level=level, year=y,
                                     ret_pct=(np.prod(1 + g.to_numpy()) - 1) * 100,
                                     sharpe=sharpe(g.to_numpy()), n_days=len(g)))
    return pd.DataFrame(rows)


def robustness_table(series: dict) -> pd.DataFrame:
    """In-sample robustness per variant: Sharpe ex-2020, 0.5%/99.5% winsorised Sharpe, median day, positive years."""
    rows = []
    for (root, name, level), s in series.items():
        if level == "tick1":
            continue
        x = s[s.index <= IS_END]
        y = x[x.index.year != 2020]
        lo, hi = x.quantile([0.005, 0.995])
        yr = x.groupby(x.index.year).apply(lambda g: np.prod(1 + g.to_numpy()) - 1)
        rows.append(dict(root=root, variant=name, cost_level=level, is_sharpe=sharpe(x.to_numpy()),
                         is_sharpe_ex2020=sharpe(y.to_numpy()), is_sharpe_winsor=sharpe(x.clip(lo, hi).to_numpy()),
                         is_median_day_bp=x.median() * 1e4, is_years_positive=int((yr > 0).sum()),
                         is_years=int(len(yr))))
    return pd.DataFrame(rows)


def tilt_selection(strat: pd.DataFrame) -> pd.DataFrame:
    """In-sample-only choice inside each tilt family (and BH as the w=1 member), by in-sample net Sharpe."""
    rows = []
    for root in ROOTS:
        for fam, prefix in (("tilt_overnight", "TILT_ON"), ("tilt_eu", "TILT_EU")):
            for level in ("1x", "2x", "gross"):
                cand = strat[(strat["root"] == root) & (strat["cost_level"] == level) &
                             (strat["sample"] == "IS_full") &
                             ((strat["family"] == fam) | (strat["variant"] == "BH"))]
                best = cand.loc[cand["sharpe"].idxmax()]
                later = strat[(strat["root"] == root) & (strat["cost_level"] == level) &
                              (strat["sample"] == "later_descriptive") & (strat["variant"] == best["variant"])].iloc[0]
                bh_later = strat[(strat["root"] == root) & (strat["cost_level"] == level) &
                                 (strat["sample"] == "later_descriptive") & (strat["variant"] == "BH")].iloc[0]
                rows.append(dict(root=root, family=fam, selection_cost_level=level, chosen=best["variant"],
                                 is_sharpe=best["sharpe"], is_sharpe_bh=cand.loc[cand["variant"] == "BH", "sharpe"].iloc[0],
                                 later_sharpe=later["sharpe"], later_sharpe_bh=bh_later["sharpe"],
                                 members=",".join(cand["variant"])))
    return pd.DataFrame(rows)


def timing_checks(p: pd.DataFrame, built: dict, D: pd.DataFrame):
    log("\n== explicit timing check (bar_start_et listed; ts are bar START, close at start+1h) ==")
    for root in ROOTS:
        A = built[root]["A"]
        df = A.df
        for day in ("2023-03-14", "2024-07-05"):
            i = int(np.where(pd.DatetimeIndex(D["d"]) == pd.Timestamp(day))[0][0])
            for nm in ("ON_16_09", "EU_01_04", "DAY_09_16", "BH"):
                w = built[root]["res"][nm]
                ia, ib = w["ia"][i], w["ib"][i]
                bars = df.iloc[ia + 1: ib + 1]
                log(f"[{root}] {day} {nm}: entry price = close of bar starting "
                    f"{df['bar_start_et'].iloc[ia]} (closes {df['bar_end_et'].iloc[ia]}); held bars start "
                    f"{bars['bar_start_et'].iloc[0]} .. {bars['bar_start_et'].iloc[-1]} ({len(bars)} bars); "
                    f"exit at {bars['bar_end_et'].iloc[-1]}; ret {w['ret'][i] * 1e4:.2f} bp")
            sl = built[root]["sig_lh"]
            ia, ib = sl["ia"][i], sl["ib"][i]
            log(f"[{root}] {day} signal last-hour: bar starting {df['bar_start_et'].iloc[ib]} "
                f"(known at {df['bar_end_et'].iloc[ib]}); conditional ON enters at 17:00 bar end, EU at 01:00")
    # consistency: ON_16_09 + DAY_09_16 (log) == BH (log) on every day; BH == 16:00 day compound
    for root in ROOTS:
        r = built[root]["res"]
        diff = np.abs(r["ON_16_09"]["logret"] + r["DAY_09_16"]["logret"] - r["BH"]["logret"])
        q = p[(p["root"] == root) & p["ret_date_1600"].notna()]
        comp = q.groupby("ret_date_1600")["ret_log"].sum().reindex(pd.DatetimeIndex(D["d"])).fillna(0).to_numpy()
        d2 = np.abs(comp - r["BH"]["logret"])
        log(f"[{root}] max |ON+DAY-BH| log = {diff.max():.2e}; max |BH - 16:00 day compound| = {d2.max():.2e}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = {"doc": __doc__, "variants": variant_specs(), "costs_oneway": COST, "tick": TICK,
            "samples": {k: [str(a.date()), str(b.date())] for k, (a, b) in SAMPLES.items()},
            "publication_split": "2020-02-01 (Boyarchenko, Larsen & Whelan, FRBNY Staff Report 917, Feb 2020)",
            "bootstrap": {"B": BOOT_B, "block_days": BOOT_BLOCK}}
    (OUT / "prespec.json").write_text(json.dumps(spec, indent=1, default=str), encoding="utf-8")

    p, D = load()
    log(f"panel rows {len(p)}; NYSE days {len(D)} from {D['d'].iloc[0].date()} to {D['d'].iloc[-1].date()}")
    built = build_daily(p, D)
    timing_checks(p, built, D)

    ht = hourly_table(p)
    ht.to_csv(OUT / "hourly_table.csv", index=False)
    st, segdaily = segment_table(p, built, D)
    st.to_csv(OUT / "segment_table.csv", index=False)
    strat, series = strategy_table(built)
    strat.to_csv(OUT / "strategy_variants_full.csv", index=False)
    nvar = strat[["root", "variant"]].drop_duplicates().shape[0]
    log(f"\nstrategy variants (root x rule): {nvar}; rows in full table: {len(strat)}")
    bt = bootstrap_table(series)
    bt.to_csv(OUT / "bootstrap_sharpe_differences.csv", index=False)
    sp = spanning_table(series)
    sp.to_csv(OUT / "spanning_alpha.csv", index=False)
    an = annual_table(series)
    an.to_csv(OUT / "annual_returns.csv", index=False)
    rb = robustness_table(series)
    rb.to_csv(OUT / "robustness_in_sample.csv", index=False)
    ts = tilt_selection(strat)
    ts.to_csv(OUT / "tilt_in_sample_selection.csv", index=False)
    dl = pd.DataFrame({f"{r}|{n}|{l}": s for (r, n, l), s in series.items() if l in ("gross", "1x")})
    dl.to_parquet(OUT / "daily_strategy_returns.parquet")

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.max_rows", 500)
    log("\n== hourly (all bars ex other_missing), in-sample ==")
    h = ht[(ht["bar_filter"] == "all_ex_other_missing") & (ht["sample"] == "IS_full")]
    log(h[["root", "window", "n_bars", "mean_simple_bp", "nw_t", "std_bp", "ann_contrib_logpct",
           "share_of_total_logret", "hit_rate", "sharpe_if_only_hour"]].round(3).to_string(index=False))
    log("\n== segments, in-sample ==")
    s = st[st["sample"] == "IS_full"]
    log(s[["root", "segment", "mean_daily_log_bp", "nw_t", "ann_mean_logpct", "ann_vol_pct", "sharpe_gross",
           "share_of_total_return", "risk_share_beta", "share_of_total_variance"]].round(3).to_string(index=False))
    log("\n== primary strategies ==")
    pr = strat[strat["primary"]]
    log(pr[["root", "variant", "cost_level", "sample", "ann_mean_pct", "ann_vol_pct", "sharpe", "sharpe_se",
            "nw_t_mean", "breakeven_oneway_cost_bp", "cost_drag_ann_pct"]].round(3).to_string(index=False))
    (OUT / "run_log.txt").write_text("\n".join(LOG_LINES), encoding="utf-8")


if __name__ == "__main__":
    main()
