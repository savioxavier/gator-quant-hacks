"""Build the shared hourly ES/ZN panel from the cached Databento ohlcv-1h file (no API calls).

Run from the repo root:
    GQH_DATA_DIR=<home>/.cache/gqh PYTHONIOENCODING=utf-8 <venv python> <this file>

Outputs (next to this file):
    hourly_panel.parquet            one row per front-contract (.v.0) hourly bar, ES and ZN stacked (column root)
    nyse_calendar_offsets.parquet   NYSE trading days with month-end offsets (helper for merges)
    validation_daily.parquet        per NYSE day: compounded hourly returns next to the daily references
    validation_summary.csv          correlation / MAD / share |diff| > 5 bp per comparison and sample
    validation_residuals.csv        the days with |diff| > 5 bp for the like-for-like comparisons, with causes
    build_log.txt                   counts printed by the run
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<solo-repo>")
sys.path.insert(0, str(REPO))
from src.calendar_utils import month_offsets  # noqa: E402

DATA = Path(os.environ.get("GQH_DATA_DIR", "<home>/.cache/gqh"))
OUT = Path(__file__).resolve().parent
RAW_H = DATA / "databento_raw" / "glbx_ohlcv1h_v01_es_zn.parquet"
TZ = "America/New_York"
IS_END = pd.Timestamp("2024-10-02")
LOG: list[str] = []


def log(msg: str = "") -> None:
    print(msg)
    LOG.append(msg)


def nyse_calendar() -> pd.DatetimeIndex:
    etf = pd.read_parquet(DATA / "etf_daily.parquet", columns=["date", "ticker"])
    return pd.DatetimeIndex(sorted(pd.to_datetime(etf.loc[etf["ticker"] == "SPY", "date"]).unique()))


def next_nyse(cal: pd.DatetimeIndex, d: pd.Series) -> pd.Series:
    """First NYSE day >= d (NaT past the end of the calendar)."""
    pos = cal.searchsorted(pd.DatetimeIndex(d), side="left")
    out = np.full(len(d), np.datetime64("NaT", "ns"), dtype="datetime64[ns]")
    ok = pos < len(cal)
    out[ok] = cal.values[pos[ok]]
    return pd.Series(out, index=d.index)


def build_root(raw: pd.DataFrame, root: str) -> pd.DataFrame:
    f = raw[raw["symbol"] == f"{root}.v.0"].sort_values("ts_event").reset_index(drop=True)
    b = raw[raw["symbol"] == f"{root}.v.1"].sort_values("ts_event")
    v1 = b.set_index("ts_event")[["instrument_id", "close", "volume"]]
    out = pd.DataFrame({
        "root": root,
        "bar_start_utc": f["ts_event"],
        "instrument_id": f["instrument_id"].astype("int64"),
        "open": f["open"], "high": f["high"], "low": f["low"], "close": f["close"],
        "volume": f["volume"].astype("int64"),
    })
    # second-ranked contract at the same timestamp (reference for rolls; NaN when it did not trade that hour)
    out["instrument_id_v1"] = out["bar_start_utc"].map(v1["instrument_id"]).astype("Int64")
    out["close_v1"] = out["bar_start_utc"].map(v1["close"])
    out["volume_v1"] = out["bar_start_utc"].map(v1["volume"]).astype("Int64")

    prev_ts = out["bar_start_utc"].shift(1)
    prev_id = out["instrument_id"].shift(1)
    prev_close_v0 = out["close"].shift(1)
    same = out["instrument_id"].eq(prev_id)
    # previous front bar is another contract (a roll): take the SAME contract from the .v.1 series at prev_ts
    v1_id_at_prev = prev_ts.map(v1["instrument_id"])
    v1_close_at_prev = prev_ts.map(v1["close"])
    from_v1 = (~same) & prev_ts.notna() & v1_id_at_prev.eq(out["instrument_id"])
    prev_close = pd.Series(np.where(same, prev_close_v0, np.where(from_v1, v1_close_at_prev, np.nan)),
                           index=out.index, dtype="float64")
    out["prev_bar_start_utc"] = prev_ts
    out["prev_close_same_id"] = prev_close
    out["prev_close_source"] = np.select([same, from_v1], ["v0", "v1"], default="none")
    out.loc[prev_ts.isna(), "prev_close_source"] = "none"
    out["ret_simple"] = out["close"] / prev_close - 1.0
    out["ret_log"] = np.log(out["close"] / prev_close)
    out["hours_since_prev"] = (out["bar_start_utc"] - prev_ts).dt.total_seconds() / 3600.0
    out["is_roll"] = (~same) & prev_ts.notna()
    out["is_gap"] = out["hours_since_prev"] > 1.0
    return out


def add_time_labels(p: pd.DataFrame, cal: pd.DatetimeIndex) -> pd.DataFrame:
    p["bar_start_et"] = p["bar_start_utc"].dt.tz_convert(TZ)
    p["bar_end_utc"] = p["bar_start_utc"] + pd.Timedelta(hours=1)
    p["bar_end_et"] = p["bar_end_utc"].dt.tz_convert(TZ)
    st = p["bar_start_et"].dt.tz_localize(None)
    p["date_et"] = st.dt.normalize()
    p["hour_et"] = p["bar_start_et"].dt.hour.astype("int8")
    p["dow_et"] = p["bar_start_et"].dt.dayofweek.astype("int8")
    # CME session (trade) date: bars starting at/after the 18:00 ET reopen belong to the next NYSE day,
    # every other bar to the first NYSE day on/after its ET calendar date (CME holiday sessions roll forward)
    base = p["date_et"] + pd.to_timedelta((p["hour_et"] >= 18).astype(int), unit="D")
    p["trade_date"] = next_nyse(cal, base)
    p["cme_non_nyse_session"] = (p["hour_et"] < 18) & ~p["date_et"].isin(cal)
    # 16:00-to-16:00 return day: NYSE day d with bar END in (16:00 ET of the previous NYSE day, 16:00 ET of d]
    en = p["bar_end_et"].dt.tz_localize(None)
    en_day = en.dt.normalize()
    after16 = (en - en_day) > pd.Timedelta(hours=16)
    p["ret_date_1600"] = next_nyse(cal, en_day + pd.to_timedelta(after16.astype(int), unit="D"))
    # month-end offsets of the trade date (T = last NYSE day of the month)
    mo = month_offsets(cal)
    p["month_T"] = pd.to_datetime(p["trade_date"].map(mo["T"])).astype("datetime64[ns]")
    p["me_off_own"] = p["trade_date"].map(mo["off_own"]).astype("Int64")     # 0 on T, -k on T-k
    p["me_off_prev"] = p["trade_date"].map(mo["off_prev"]).astype("Int64")   # k on T+k (k-th day of next month)
    # session flags
    p["new_session"] = p.groupby("root")["trade_date"].transform(lambda s: s.ne(s.shift(1)))
    p.loc[p.groupby("root").head(1).index, "new_session"] = True
    p["in_sample"] = p["trade_date"] <= IS_END
    return p


def classify_gaps(p: pd.DataFrame, cal: pd.DatetimeIndex) -> pd.Series:
    """Label every bar that follows a > 1 h gap. 'Covered' dates are the ET dates strictly between the previous
    bar's date and this bar's date, plus this bar's date when it starts at/after the 18:00 ET reopen (the
    whole day session of that date was then skipped)."""
    calset = set(pd.DatetimeIndex(cal))
    g = pd.Series("none", index=p.index, dtype="object")
    g[p["prev_bar_start_utc"].isna()] = "first_bar"
    idx = p.index[p["is_gap"].fillna(False)]
    prev_et = p.loc[idx, "prev_bar_start_utc"].dt.tz_convert(TZ).dt.tz_localize(None).dt.normalize()
    for i, pdate in zip(idx, prev_et):
        cdate, hr, gap = p.at[i, "date_et"], p.at[i, "hour_et"], p.at[i, "hours_since_prev"]
        covered = list(pd.date_range(pdate + pd.Timedelta(days=1), cdate - pd.Timedelta(days=1), freq="D"))
        if hr >= 18 and cdate > pdate:
            covered.append(cdate)
        whole_nyse_day_missing = any(d in calset for d in covered)
        has_sat = any(d.dayofweek == 5 for d in covered)
        holiday = any(d.dayofweek < 5 and d not in calset for d in covered)
        if whole_nyse_day_missing:
            g[i] = "other_missing"          # a full NYSE trading day without any bar: vendor data hole
        elif holiday:
            g[i] = "holiday_closure"        # Christmas, New Year, Good Friday, Thanksgiving, NYSE closures
        elif has_sat:
            g[i] = "weekend"                # Fri 16:00/17:00 (or early close) -> Sun 18:00 ET
        elif hr == 18 and gap <= 3:
            g[i] = "daily_break"            # 17:00-18:00 ET CME maintenance break
        elif hr == 18 and gap <= 10:
            g[i] = "early_close_reopen"     # holiday/half-day session that stopped early, normal 18:00 reopen
        else:
            g[i] = "other_missing"          # bars missing inside a session: outage, vendor hole, delayed reopen
    return g


def daily_refs(cal: pd.DatetimeIndex) -> pd.DataFrame:
    rf = pd.read_parquet(DATA / "rf_daily.parquet").set_index("date")["rf"]
    rf.index = pd.to_datetime(rf.index)
    fd = pd.read_parquet(DATA / "futures_daily.parquet")
    f16 = pd.read_parquet(DATA / "futures_1600.parquet")
    lev = pd.concat([fd[fd["ticker"].isin(["F_ES", "F_ZN"])], f16]).pivot(index="date", columns="ticker", values="close")
    rolls = pd.concat([fd[fd["ticker"].isin(["F_ES", "F_ZN"])], f16]).pivot(index="date", columns="ticker", values="roll")
    lev.index = pd.to_datetime(lev.index)
    rolls.index = pd.to_datetime(rolls.index)
    tr = lev.pct_change()
    rfa = rf.reindex(lev.index).ffill().fillna(0.0)
    ex = tr.sub(rfa, axis=0)            # within-contract futures excess return (the builder adds rf to it)
    ex.columns = [f"ref_{c}" for c in ex.columns]
    rolls.columns = [f"roll_{c}" for c in rolls.columns]
    return ex.join(rolls)


def compound(p: pd.DataFrame, key: str) -> pd.DataFrame:
    g = p.assign(r1=1.0 + p["ret_simple"].fillna(0.0), nan=p["ret_simple"].isna(),
                 roll=p["is_roll"], igap=p["gap_type"].eq("other_missing"))
    a = g.groupby(["root", key]).agg(comp=("r1", "prod"), n_bars=("r1", "size"), n_nan=("nan", "sum"),
                                     n_roll=("roll", "sum"), n_other_missing=("igap", "sum"))
    a["comp"] -= 1.0
    return a


def stats(x: pd.Series, y: pd.Series) -> dict:
    m = x.notna() & y.notna()
    x, y = x[m], y[m]
    d = (x - y) * 1e4
    return {"n_days": int(m.sum()), "corr": float(np.corrcoef(x, y)[0, 1]) if len(x) > 2 else np.nan,
            "mad_bp": float(d.abs().mean()), "median_ad_bp": float(d.abs().median()),
            "share_absdiff_gt_5bp": float((d.abs() > 5).mean()), "n_absdiff_gt_5bp": int((d.abs() > 5).sum()),
            "max_absdiff_bp": float(d.abs().max()), "mean_diff_bp": float(d.mean()),
            "std_hourly_bp": float(x.std() * 1e4), "std_ref_bp": float(y.std() * 1e4)}


def main() -> None:
    cal = nyse_calendar()
    raw = pd.read_parquet(RAW_H)
    assert not raw.duplicated(["symbol", "ts_event"]).any()
    assert (raw["ts_event"].dt.minute == 0).all()
    log(f"raw rows {len(raw)}: {raw['symbol'].value_counts().to_dict()}")
    log(f"raw span {raw['ts_event'].min()} .. {raw['ts_event'].max()} (UTC bar starts)")

    p = pd.concat([build_root(raw, r) for r in ("ES", "ZN")], ignore_index=True)
    p = add_time_labels(p, cal)
    p["gap_type"] = classify_gaps(p, cal)
    cols = ["root", "bar_start_utc", "bar_end_utc", "bar_start_et", "bar_end_et", "date_et", "hour_et", "dow_et",
            "trade_date", "ret_date_1600", "cme_non_nyse_session", "new_session", "month_T", "me_off_own",
            "me_off_prev", "in_sample", "instrument_id", "open", "high", "low", "close", "volume",
            "instrument_id_v1", "close_v1", "volume_v1", "prev_bar_start_utc", "prev_close_same_id",
            "prev_close_source", "ret_simple", "ret_log", "hours_since_prev", "is_gap", "gap_type", "is_roll"]
    p = p[cols].sort_values(["root", "bar_start_utc"]).reset_index(drop=True)

    # ---- checks
    assert p["trade_date"].notna().all()
    nat = p["ret_date_1600"].isna()
    log(f"bars whose 16:00 return day lies past the calendar end (2026-10-02): {int(nat.sum())} "
        f"{p.loc[nat, ['root', 'bar_start_et']].astype(str).values.tolist()}")
    assert (p.loc[nat, "bar_start_et"] >= pd.Timestamp("2026-10-02 16:00", tz=TZ)).all()
    q = p[~nat]
    assert (q["ret_date_1600"] >= q["trade_date"]).all()
    assert ((q["ret_date_1600"] - q["trade_date"]).dt.days.between(0, 5)).all()
    # point-in-time: bar end = start + 1h, and the prev bar strictly precedes
    assert (p["prev_bar_start_utc"].dropna() < p.loc[p["prev_bar_start_utc"].notna(), "bar_start_utc"]).all()
    for r, g in p.groupby("root"):
        log(f"\n{r}: {len(g)} front bars, {g['trade_date'].nunique()} trade dates "
            f"{g['trade_date'].min().date()} .. {g['trade_date'].max().date()}")
        log(f"  rolls {int(g['is_roll'].sum())}; roll bars with return from v1 {int((g['is_roll'] & g['prev_close_source'].eq('v1')).sum())},"
            f" NaN {int((g['is_roll'] & g['prev_close_source'].eq('none')).sum())}")
        log(f"  roll bar ET hours {g.loc[g['is_roll'], 'hour_et'].value_counts().to_dict()}")
        log(f"  NaN returns {int(g['ret_simple'].isna().sum())} (incl. first bar)")
        log(f"  gap types {g['gap_type'].value_counts().to_dict()}")
        log(f"  bars on CME sessions of non-NYSE days {int(g['cme_non_nyse_session'].sum())}")
        log(f"  |hourly ret| > 3%: {int((g['ret_simple'].abs() > 0.03).sum())}; max |ret| {g['ret_simple'].abs().max():.4f}")
        log(f"  front volume == 0 bars {int((g['volume'] == 0).sum())}")
        ok = g[g["hour_et"] == 15]
        log(f"  bars per trade date: median {g.groupby('trade_date').size().median():.0f}; "
            f"trade dates with a 15:00 ET bar {ok['trade_date'].nunique()}")
    p.to_parquet(OUT / "hourly_panel.parquet", index=False)
    mo = month_offsets(cal)[["T", "off_own", "off_prev"]].rename(columns={"T": "month_T", "off_own": "me_off_own",
                                                                         "off_prev": "me_off_prev"})
    mo.index.name = "date"
    mo.reset_index().to_parquet(OUT / "nyse_calendar_offsets.parquet", index=False)

    # ---- validation
    refs = daily_refs(cal)
    p["ret_date_utc0"] = next_nyse(cal, p["bar_start_utc"].dt.tz_localize(None).dt.normalize())
    c16 = compound(p, "ret_date_1600")
    cu = compound(p, "ret_date_utc0")
    rows, frames = [], []
    for r in ("ES", "ZN"):
        h16 = c16.loc[r].add_suffix("_1600")
        hu = cu.loc[r].add_suffix("_utc0")
        v = h16.join(hu, how="outer").join(refs[[f"ref_{r}16", f"ref_F_{r}", f"roll_{r}16", f"roll_F_{r}"]], how="left")
        v.index.name = "date"
        first_day = v.index.min()
        v = v[v.index > first_day]            # first panel day has no previous 16:00 / midnight close
        v.insert(0, "root", r)
        frames.append(v.reset_index())
        comps = [("hourly 16:00->16:00 vs ref 16:00 (ES16/ZN16 excess)", "comp_1600", f"ref_{r}16"),
                 ("hourly 16:00->16:00 vs F_ (futures_daily excess)", "comp_1600", f"ref_F_{r}"),
                 ("hourly 00:00UTC->00:00UTC vs F_ (like-for-like window)", "comp_utc0", f"ref_F_{r}"),
                 ("ref 16:00 vs F_ (daily references against each other)", f"ref_{r}16", f"ref_F_{r}")]
        samples = {"full": v.index >= first_day, "in_sample": v.index <= IS_END, "later_2024-10-03_on": v.index > IS_END}
        for name, a, b in comps:
            for sname, m in samples.items():
                s = stats(v.loc[m, a], v.loc[m, b])
                rows.append({"root": r, "comparison": name, "sample": sname, **s})
            # excluding roll days / days with NaN hourly returns
            if a.startswith("comp"):
                tag = a.split("_")[-1]
                m = (v[f"n_roll_{tag}"] == 0) & (v[f"n_nan_{tag}"] == 0)
                m &= v[f"roll_{r}16" if b.endswith("16") else f"roll_F_{r}"].fillna(0) == 0
            else:
                m = (v[f"roll_{r}16"].fillna(0) == 0) & (v[f"roll_F_{r}"].fillna(0) == 0)
            s = stats(v.loc[m, a], v.loc[m, b])
            rows.append({"root": r, "comparison": name, "sample": "full_ex_roll_and_nan_days", **s})
        for tag in ("1600", "utc0"):
            span = cal[(cal > first_day) & (cal <= v.index.max())]
            empty = span.difference(v.index[v[f"n_bars_{tag}"].fillna(0) > 0])
            log(f"{r}: NYSE days with no hourly bar in the {tag} window (hourly comp NaN, reference 0): "
                f"{[str(d.date()) for d in empty]}")
    summ = pd.DataFrame(rows)
    summ.to_csv(OUT / "validation_summary.csv", index=False, float_format="%.6g")
    val = pd.concat(frames, ignore_index=True)
    val.to_parquet(OUT / "validation_daily.parquet", index=False)

    # residual attribution for the like-for-like comparisons
    res = []
    for r, v in val.groupby("root"):
        v = v.set_index("date").sort_index()
        for tag, a, b, rollc, nanc in [("1600", "comp_1600", f"ref_{r}16", f"roll_{r}16", "n_nan_1600"),
                                       ("utc0", "comp_utc0", f"ref_F_{r}", f"roll_F_{r}", "n_nan_utc0")]:
            ok = v[a].notna() & v[b].notna()
            ch = np.log1p(v[a].where(ok, 0.0)).cumsum()
            cr = np.log1p(v[b].where(ok, 0.0)).cumsum()
            om = v[f"n_other_missing_{tag}"].fillna(0).rolling(7, center=True, min_periods=1).sum()
            for i, (dt, row) in enumerate(v.iterrows()):
                if not ok.iloc[i]:
                    continue
                d = (row[a] - row[b]) * 1e4
                if abs(d) <= 5:
                    continue
                lo, hi = max(i - 4, 0), min(i + 3, len(v) - 1)
                win = ((ch.iloc[hi] - ch.iloc[lo]) - (cr.iloc[hi] - cr.iloc[lo])) * 1e4
                cause = []
                if row[f"n_roll_{tag}"] > 0 or row[rollc] > 0:
                    cause.append("roll day (contract switch at a different hour in the two series)")
                if row[nanc] > 0:
                    cause.append(f"{int(row[nanc])} NaN hourly return(s)")
                if om.iloc[i] > 0:
                    cause.append("vendor data hole (other_missing gap) within +-3 days")
                if abs(row[b]) < 1e-12:
                    cause.append("reference return exactly 0 (no reference bar that day)")
                res.append({"date": dt, "root": r, "window": tag, "hourly": row[a], "ref": row[b], "diff_bp": d,
                            "n_bars": row[f"n_bars_{tag}"], "cum_diff_7day_window_bp": win,
                            "cause": "; ".join(cause) or "unexplained"})
    resid = pd.DataFrame(res)
    resid.to_csv(OUT / "validation_residuals.csv", index=False, float_format="%.6g")
    for r, v in val.groupby("root"):          # whole-sample drift between the hourly chain and the references
        for a, b in [("comp_1600", f"ref_{r}16"), ("comp_utc0", f"ref_F_{r}"), ("comp_1600", f"ref_F_{r}")]:
            ok = v[a].notna() & v[b].notna()
            dd = (np.log1p(v.loc[ok, a]).sum() - np.log1p(v.loc[ok, b]).sum()) * 1e4
            log(f"{r}: total log-return difference {a} - {b} over {int(ok.sum())} days: {dd:.2f} bp")
    nr = p.loc[p["gap_type"].eq("other_missing"), ["root", "prev_bar_start_utc", "bar_start_et", "hours_since_prev",
                                                 "trade_date", "ret_simple"]].copy()
    nr["prev_bar_start_et"] = nr.pop("prev_bar_start_utc").dt.tz_convert(TZ)
    nr.to_csv(OUT / "nonroutine_gaps.csv", index=False)
    log(f"\nnon-routine gaps (gap_type other_missing): {len(nr)}")
    with pd.option_context("display.width", 250):
        log(nr.to_string(index=False))
    log("\nvalidation summary (diff in bp):")
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        log(summ[["root", "comparison", "sample", "n_days", "corr", "mad_bp", "share_absdiff_gt_5bp",
                  "n_absdiff_gt_5bp", "max_absdiff_bp"]].to_string(index=False))
        if len(resid):
            log("\nresidual days |diff| > 5 bp (like-for-like windows):")
            log(resid.to_string(index=False))
    (OUT / "build_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
