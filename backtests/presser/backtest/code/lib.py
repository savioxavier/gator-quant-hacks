"""Shared helpers for the presser backtest (follows bt/ADDENDUM.md, sha256 1921b2ca...de2dc4).

Clock, fill, tick, quote and inference rules are the addendum's sections 1, 7 and 8. Nothing here is tuned.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

# Locations (all overridable by environment variables; nothing machine-specific is hard-coded):
#   BT    backtests/presser (this file is backtests/presser/backtest/code/lib.py)
#   OUT   output folder (PRESSER_OUT_DIR; default backtests/rerun/presser_h1). BT/backtest holds the frozen H1
#         positions read by the H2/H3/H4 stage and is never written by s01-s05.
#   TEXT  text label (PRESSER_TEXT_DIR; default BT/text_chrono, the stance-scored label of the reported H1 run;
#         BT/text has no stance columns and gives the pre-stance run: BENCH-R and the lexicon control only)
#   CACHE licensed Databento files (GQH_MARKET_DIR, else $GQH_DATA_DIR/presser); never in git
#   PLAN  plan documents (PRESSER_PLAN_DIR; default <repo>/preregistration)
BT = Path(os.environ.get("PRESSER_BT_DIR") or Path(__file__).resolve().parents[2])
REPO_ROOT = BT.parents[1]
FROZEN_H1 = BT / "backtest"
OUT = Path(os.environ.get("PRESSER_OUT_DIR") or (BT.parent / "rerun" / "presser_h1"))
TEXT = Path(os.environ.get("PRESSER_TEXT_DIR") or (BT / "text_chrono"))
if os.environ.get("GQH_MARKET_DIR"):
    CACHE = Path(os.environ["GQH_MARKET_DIR"])
elif os.environ.get("GQH_DATA_DIR"):
    CACHE = Path(os.environ["GQH_DATA_DIR"]) / "presser"
else:
    CACHE = Path("GQH_MARKET_DIR_not_set")  # licensed market data are not in git; set GQH_MARKET_DIR
PLAN = Path(os.environ.get("PRESSER_PLAN_DIR") or (REPO_ROOT / "preregistration"))
TZ = "America/New_York"
SEED = 20261003
B = 9999
ADDENDUM_SHA = "1921b2ca1dc6e646b95ee1d1bbc3e3ef7f6a864c06cd724956df7c6569de2dc4"

SYMS = ["ZT", "ZF", "ZN", "ES"]
QSYMS = ["ZT", "ZN", "ES"]
ONE_MIN = pd.Timedelta(minutes=1)
FEE_USD_SIDE = 2.00  # A-04, UNVERIFIED broker estimate


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stance_scorer() -> str:
    """Scorer id recorded with the run: TEXT/scorer.json (written by the stance-score adapter) or 'none'."""
    f = TEXT / "scorer.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8")).get("stance_scorer", "unknown")
    return "none (FOMC-RoBERTa gated; D1 chrono-bert scores not built)"


def check_addendum():
    got = sha256(BT / "ADDENDUM.md")
    if got != ADDENDUM_SHA:
        raise SystemExit(f"ADDENDUM.md changed: {got}")
    if OUT.resolve() == FROZEN_H1.resolve():
        raise SystemExit(f"PRESSER_OUT_DIR={OUT} is the frozen H1 folder (read-only); choose another output folder")


# ---------------------------------------------------------------- ticks (addendum 1.2)
def tick_pts(sym: str, date: str) -> float:
    if sym == "ZT":
        return 1 / 128 if date <= "2018-12-31" else 1 / 256
    return {"ZF": 1 / 128, "ZN": 1 / 64, "ES": 0.25}[sym]


USD_PER_PT = {"ZT": 2000.0, "ZF": 1000.0, "ZN": 1000.0, "ES": 50.0}


def usd_per_tick(sym: str, date: str) -> float:
    return tick_pts(sym, date) * USD_PER_PT[sym]


def tick_era(sym: str, date: str) -> str:
    if sym == "ZT":
        return "ZT_1/128_2016-2018" if date <= "2018-12-31" else "ZT_1/256_2019+"
    return f"{sym}_const"


# ---------------------------------------------------------------- events and clocks (addendum 1.1)
def load_events() -> pd.DataFrame:
    e = pd.read_csv(BT / "events/events.csv", dtype={"date": str}).copy()
    e["meeting"] = e.date.str.replace("-", "").astype(int)
    e["sched_ts"] = pd.to_datetime(e.date + " " + e.presser_sched_et).dt.tz_localize(TZ)

    def ts(col):
        return pd.to_datetime(e.date + " " + e[col].astype(str), errors="coerce").dt.tz_localize(TZ)

    e["end_est_ts"] = ts("presser_end_est_et")
    e["start_est_ts"] = ts("presser_start_est_et")
    e["end_conv_ts"] = ts("presser_end_conv_et")
    e["era_bench"] = np.where(e.date < "2020-01-01", "2016-2019", "2020-2026")
    return e


def load_answers() -> pd.DataFrame:
    a = pd.read_parquet(TEXT / "answers.parquet")
    a["meeting"] = a.meeting.astype(int)
    return a


def load_meetings() -> pd.DataFrame:
    m = pd.read_parquet(TEXT / "meetings.parquet")
    m["meeting"] = m.meeting.astype(int)
    return m


def wall(ev_row, x_s: float) -> pd.Timestamp:
    """W_m(x) = presser_sched_et + v0_minus_sched_tv_s + x."""
    return ev_row.sched_ts + pd.Timedelta(seconds=float(ev_row.v0_minus_sched_tv_s) + float(x_s))


def tau_end(ev_row, ans_m: pd.DataFrame, clock: str = "upper"):
    """Presser end decision time. clock in {upper, point, conv}. Returns (timestamp, source)."""
    if clock == "conv":
        return ev_row.end_conv_ts, "convention_14:30"
    unc = float(ev_row.start_unc_s) if clock == "upper" else 0.0
    if pd.notna(ev_row.v0_minus_sched_tv_s):
        cands = [ev_row.last_speech_end_s] if pd.notna(ev_row.last_speech_end_s) else []
        t = ans_m[ans_m.timing_source == "vtt"]
        if len(t):
            cands.append(float((t.t_end_video_s + t.end_cue_dur).max()))
        if cands:
            return wall(ev_row, max(cands)) + pd.Timedelta(seconds=unc), "tv_anchored"
    # fallback (timing-dropped meetings only; BENCH-R only)
    return ev_row.end_est_ts + pd.Timedelta(seconds=unc + (1.0 if clock == "upper" else 0.0)), "fallback_end_est"


def tau_answer(ev_row, ans_row, clock: str = "upper") -> pd.Timestamp:
    unc = float(ev_row.start_unc_s) if clock == "upper" else 0.0
    return wall(ev_row, float(ans_row.t_end_video_s) + float(ans_row.end_cue_dur)) + pd.Timedelta(seconds=unc)


# ---------------------------------------------------------------- bars
class Bars:
    """1m bars per (date, symbol): ts_event (bar start, ET) and OHLC."""

    def __init__(self):
        d = pd.read_parquet(CACHE / "ohlcv-1m__all_2016_2026.parquet")
        d["sym"] = d.symbol.str[:2]
        d["ts"] = d.ts_event.dt.tz_convert(TZ)
        d["date"] = d.ts.dt.strftime("%Y-%m-%d")
        self.g = {k: v.sort_values("ts").reset_index(drop=True) for k, v in d.groupby(["date", "sym"])}
        self.log = []

    def get(self, date, sym):
        return self.g.get((date, sym))

    def next_open(self, date, sym, t, tag=""):
        """Open of the first 1m bar with ts_event >= t (missing minutes skipped and logged)."""
        b = self.get(date, sym)
        if b is None:
            return None, np.nan
        i = int(np.searchsorted(b.ts.values, np.datetime64(t.tz_convert("UTC").tz_localize(None)), "left"))
        # b.ts.values are UTC-naive datetime64 internally
        if i >= len(b):
            return None, np.nan
        bt = b.ts.iloc[i]
        expected = t.ceil("min")
        if bt > expected:
            self.log.append(dict(date=date, sym=sym, tag=tag, kind="next_open_skip",
                                 t=str(t), expected_bar=str(expected), used_bar=str(bt),
                                 skipped_min=int((bt - expected) / ONE_MIN)))
        return bt, float(b.open.iloc[i])

    def close_at(self, date, sym, T, lo=None, tag=""):
        """Close of the last 1m bar with ts_event <= T - 1 min (and >= lo if given)."""
        b = self.get(date, sym)
        if b is None:
            return None, np.nan
        lim = T - ONE_MIN
        i = int(np.searchsorted(b.ts.values, np.datetime64(lim.tz_convert("UTC").tz_localize(None)), "right")) - 1
        if i < 0:
            return None, np.nan
        bt = b.ts.iloc[i]
        if lo is not None and bt < lo:
            return None, np.nan
        if bt < lim:
            self.log.append(dict(date=date, sym=sym, tag=tag, kind="close_at_stale", t=str(T),
                                 expected_bar=str(lim), used_bar=str(bt),
                                 skipped_min=int((lim - bt) / ONE_MIN)))
        return bt, float(b.close.iloc[i])


class Quotes:
    """bbo-1s: quote at second t = last record with ts_recv <= t, skipping crossed/locked/one-sided records."""

    def __init__(self):
        q = pd.read_parquet(CACHE / "bbo-1s__all_2016_2026.parquet",
                            columns=["ts_recv", "bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00", "symbol"])
        q["sym"] = q.symbol.str[:2]
        q["ts"] = q.ts_recv.dt.tz_convert(TZ)
        q["date"] = q.ts.dt.strftime("%Y-%m-%d")
        ok = (q.bid_px_00 > 0) & (q.ask_px_00 > 0) & (q.ask_px_00 > q.bid_px_00) & (q.bid_sz_00 > 0) & (q.ask_sz_00 > 0)
        self.n_bad = int((~ok).sum())
        q = q[ok]
        self.g = {}
        for k, v in q.groupby(["date", "sym"]):
            v = v.sort_values("ts_recv")
            self.g[k] = (v.ts_recv.values.astype("datetime64[ns]").astype(np.int64),
                         v.bid_px_00.values, v.ask_px_00.values)

    def at(self, date, sym, t):
        """Returns (bid, ask, staleness_s) or (nan, nan, nan)."""
        k = (date, sym)
        if k not in self.g:
            return np.nan, np.nan, np.nan
        ts, bid, ask = self.g[k]
        tn = t.tz_convert("UTC").value
        i = int(np.searchsorted(ts, tn, "right")) - 1
        if i < 0:
            return np.nan, np.nan, np.nan
        return float(bid[i]), float(ask[i]), (tn - ts[i]) / 1e9

    def series(self, date, sym, start, end):
        """Per-second quotes for seconds in [start, end) (forward-filled per the 1.3 rule)."""
        k = (date, sym)
        secs = pd.date_range(start, end, freq="s", inclusive="left")
        if k not in self.g:
            return pd.DataFrame(index=secs, columns=["bid", "ask", "stale"], dtype=float)
        ts, bid, ask = self.g[k]
        tn = secs.tz_convert("UTC").as_unit("ns").asi8
        i = np.searchsorted(ts, tn, "right") - 1
        ok = i >= 0
        ii = np.where(ok, i, 0)
        out = pd.DataFrame({"bid": np.where(ok, bid[ii], np.nan), "ask": np.where(ok, ask[ii], np.nan),
                            "stale": np.where(ok, (tn - ts[ii]) / 1e9, np.nan)}, index=secs)
        return out


# ---------------------------------------------------------------- trade evaluation (addendum 1.2, 1.3, 7)
def trade(date, sym, pos, entry_ts, entry_px, exit_ts, exit_px, entry_sec, exit_sec, quotes: Quotes | None):
    """One 1-contract trade: gross ticks/usd on trade prints, plus C2, C4, CM, CQ and fee lines."""
    tk = tick_pts(sym, date)
    upt = usd_per_tick(sym, date)
    r = dict(date=date, sym=sym, pos=pos, entry_ts=entry_ts, entry_px=entry_px, exit_ts=exit_ts, exit_px=exit_px,
             tick_pts=tk, usd_per_tick=upt, tick_era=tick_era(sym, date))
    g = pos * (exit_px - entry_px) / tk
    r["move_ticks"] = (exit_px - entry_px) / tk
    r["ret"] = exit_px / entry_px - 1
    r["C0_ticks"] = g
    r["C2_ticks"] = g - 4
    r["C4_ticks"] = g - 8
    r["hs_entry_ticks"] = r["hs_exit_ticks"] = r["stale_entry_s"] = r["stale_exit_s"] = np.nan
    r["CM_ticks"] = r["CQ_ticks"] = np.nan
    if quotes is not None and sym in QSYMS:
        b0, a0, s0 = quotes.at(date, sym, entry_sec)
        b1, a1, s1 = quotes.at(date, sym, exit_sec)
        r["stale_entry_s"], r["stale_exit_s"] = s0, s1
        if np.isfinite(b0) and np.isfinite(b1):
            r["hs_entry_ticks"] = (a0 - b0) / 2 / tk
            r["hs_exit_ticks"] = (a1 - b1) / 2 / tk
            r["CM_ticks"] = g - r["hs_entry_ticks"] - r["hs_exit_ticks"]
            if pos > 0:
                r["CQ_ticks"] = (b1 - a0) / tk
            else:
                r["CQ_ticks"] = (b0 - a1) / tk
    fee_ticks = 2 * FEE_USD_SIDE / upt
    r["C2F_ticks"] = r["C2_ticks"] - fee_ticks
    r["C4F_ticks"] = r["C4_ticks"] - fee_ticks
    r["CMF_ticks"] = r["CM_ticks"] - fee_ticks
    for c in ["C0", "C2", "C4", "CM", "CQ", "C2F", "C4F", "CMF"]:
        r[f"{c}_usd"] = r[f"{c}_ticks"] * upt
    return r


COST_ROWS = ["C0", "C2", "C4", "CM", "CQ", "C2F", "C4F", "CMF"]
COST_LABEL = {"C0": "gross (trade prints)", "C2": "2 ticks/side", "C4": "4 ticks/side",
              "CM": "measured half-spread (bbo-1s)", "CQ": "quote fills (ask/bid)",
              "C2F": "2 ticks/side + $2/side fee (UNVERIFIED)", "C4F": "4 ticks/side + $2/side fee (UNVERIFIED)",
              "CMF": "measured half-spread + $2/side fee (UNVERIFIED)"}


# ---------------------------------------------------------------- inference (addendum 8.1)
def _t(y):
    n = len(y)
    s = y.std(ddof=1)
    return y.mean() / (s / math.sqrt(n)) if s > 0 else np.nan


def block_len(n):
    return max(2, int(round(n ** (1 / 3))))


def block_boot(y, rng=None, B_=B):
    """Circular block bootstrap over meetings in date order: percentile 90% CI of the mean and studentised p."""
    y = np.asarray(y, float)
    n = len(y)
    if n < 3:
        return dict(bb_b=np.nan, bb_ci90_lo=np.nan, bb_ci90_hi=np.nan, bb_p_one=np.nan, bb_p_two=np.nan)
    rng = rng or np.random.default_rng(SEED)
    b = block_len(n)
    nb = math.ceil(n / b)
    starts = rng.integers(0, n, size=(B_, nb))
    idx = (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(B_, nb * b)[:, :n] % n
    ys = y[idx]
    m = ys.mean(1)
    s = ys.std(1, ddof=1)
    tstar = (m - y.mean()) / (s / math.sqrt(n))
    t0 = _t(y)
    return dict(bb_b=b, bb_ci90_lo=float(np.percentile(m, 5)), bb_ci90_hi=float(np.percentile(m, 95)),
                bb_p_one=float((1 + np.sum(tstar >= t0)) / (B_ + 1)),
                bb_p_two=float((1 + np.sum(np.abs(tstar) >= abs(t0))) / (B_ + 1)))


def signflip(y, rng=None, B_=B):
    """Studentised Rademacher sign flip on Y_m (null of zero mean). One-sided p for mean > 0, and two-sided."""
    y = np.asarray(y, float)
    n = len(y)
    if n < 3:
        return dict(wb_p_one=np.nan, wb_p_two=np.nan, wb_p_one_neg=np.nan)
    rng = rng or np.random.default_rng(SEED)
    w = rng.choice([-1.0, 1.0], size=(B_, n))
    ys = w * y
    s = ys.std(1, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        tstar = ys.mean(1) / (s / math.sqrt(n))
    t0 = _t(y)
    return dict(wb_p_one=float((1 + np.sum(tstar >= t0)) / (B_ + 1)),
                wb_p_one_neg=float((1 + np.sum(tstar <= t0)) / (B_ + 1)),
                wb_p_two=float((1 + np.sum(np.abs(tstar) >= abs(t0))) / (B_ + 1)))


def summarize(y, label=None):
    y = np.asarray(pd.Series(y).dropna(), float)
    n = len(y)
    r = dict(n=n)
    if n == 0:
        return r
    r.update(mean=y.mean(), sd=y.std(ddof=1) if n > 1 else np.nan, median=float(np.median(y)),
             hit=float(np.mean(y > 0)), zero_share=float(np.mean(y == 0)), t=_t(y) if n > 1 else np.nan)
    r.update(block_boot(y))
    r.update(signflip(y))
    return r


WEBB = np.array([-math.sqrt(1.5), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(1.5)])


def cluster_t(y, g):
    """Mean with CR1 meeting-clustered SE."""
    y = np.asarray(y, float)
    codes, gi = np.unique(g, return_inverse=True)
    G, n = len(codes), len(y)
    m = y.mean()
    S = np.bincount(gi, weights=y - m, minlength=G)
    v = (G / (G - 1)) * ((n - 1) / (n - 1)) * np.sum(S ** 2) / n ** 2
    se = math.sqrt(v)
    return m, se, (m / se if se > 0 else np.nan), G


def answer_summary(y, g, order_key):
    """Answer-level: mean per answer, CR1 t, wild cluster bootstrap (Webb, null imposed),
    block bootstrap over whole meetings, and the meeting-averaged sign flip."""
    y = np.asarray(y, float)
    g = np.asarray(g)
    n = len(y)
    r = dict(n_answers=n)
    if n == 0:
        return r
    codes, gi = np.unique(g, return_inverse=True)
    G = len(codes)
    r["n_meetings"] = G
    if G < 3:
        r.update(mean=y.mean(), hit=float(np.mean(y > 0)))
        return r
    m, se, t, _ = cluster_t(y, g)
    r.update(mean=m, sd=y.std(ddof=1), median=float(np.median(y)), hit=float(np.mean(y > 0)),
             zero_share=float(np.mean(y == 0)), se_cr1=se, t_cr1=t)
    rng = np.random.default_rng(SEED)
    w = rng.choice(WEBB, size=(B, G))
    ysum = np.bincount(gi, weights=y, minlength=G)
    cnt = np.bincount(gi, minlength=G).astype(float)
    ms = (w @ ysum) / n  # null imposed: restricted residual = y, y* = w_g y
    S = w * ysum[None, :] - ms[:, None] * cnt[None, :]
    ses = np.sqrt((G / (G - 1)) * (S ** 2).sum(1) / n ** 2)
    ts = ms / ses
    r["wcb_p_one"] = float((1 + np.sum(ts >= t)) / (B + 1))
    r["wcb_p_two"] = float((1 + np.sum(np.abs(ts) >= abs(t))) / (B + 1))
    # block bootstrap over whole meetings in date order
    okey = pd.Series(order_key, index=g).groupby(level=0).first().reindex(codes).values
    morder = np.argsort(okey, kind="stable")
    sums = ysum[morder]
    cnts = cnt[morder]
    b = block_len(G)
    nb = math.ceil(G / b)
    rng2 = np.random.default_rng(SEED)
    starts = rng2.integers(0, G, size=(B, nb))
    sel = (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(B, nb * b)[:, :G] % G
    tot = cnts[sel].sum(1)
    mstar = sums[sel].sum(1) / tot
    Sg = sums[sel] - cnts[sel] * mstar[:, None]
    sse = np.sqrt((G / (G - 1)) * np.sum(Sg ** 2, 1) / tot ** 2)
    with np.errstate(divide="ignore", invalid="ignore"):
        tstar = (mstar - m) / sse
    r.update(bb_b=b, bb_ci90_lo=float(np.nanpercentile(mstar, 5)), bb_ci90_hi=float(np.nanpercentile(mstar, 95)),
             bb_p_two=float((1 + np.nansum(np.abs(tstar) >= abs(t))) / (B + 1)))
    # meeting-averaged
    ym = pd.Series(y).groupby(gi).mean().values
    sm = summarize(ym)
    r.update({f"mtg_{k}": v for k, v in sm.items() if k in ("n", "mean", "t", "hit", "wb_p_two", "wb_p_one")})
    return r


def write_json(p, obj):
    def conv(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, (pd.Timestamp,)):
            return str(o)
        return str(o)
    Path(p).write_text(json.dumps(obj, indent=2, default=conv))
