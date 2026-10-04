"""Independent re-computation of the month-end intraday study (sleeves A and C).

Rebuilds ES/ZN hourly returns from the raw cached Databento file (no shared panel), assigns bars to
16:00-to-16:00 ET return days on the NYSE (SPY) calendar, and evaluates the five pre-specified timing
variants per sleeve with an independent position/turnover ledger.

Only the sleeve weights (repo rule output, sleeve_weights.parquet from the other analyst) are reused;
they are spot-checked against month_info.csv and ZN16/ES16 63-day vol.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OTHER = HERE.parent / "monthend_intraday"
GQH = Path("<home>/.cache/gqh")
IS_END = pd.Timestamp("2024-10-02")
LATER0, LATER1 = pd.Timestamp("2024-10-03"), pd.Timestamp("2026-10-02")
PUB = pd.Timestamp("2019-12-01")
COST = {"ES": 1.0e-4, "ZN": 1.5e-4}
OUT = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    OUT.append(s)


# ------------------------------------------------------------------ hourly from raw
def build_hourly() -> pd.DataFrame:
    raw = pd.read_parquet(GQH / "databento_raw/glbx_ohlcv1h_v01_es_zn.parquet",
                          columns=["ts_event", "instrument_id", "close", "volume", "symbol"])
    raw["root"] = raw["symbol"].str[:2]
    raw["ts_event"] = raw["ts_event"].dt.as_unit("ns")
    out = []
    for root, g in raw.groupby("root"):
        px = g.set_index(["ts_event", "instrument_id"])["close"]
        px = px[~px.index.duplicated()]
        f = g[g["symbol"] == f"{root}.v.0"].sort_values("ts_event").reset_index(drop=True)
        v1 = g[g["symbol"] == f"{root}.v.1"].set_index("ts_event")["volume"]
        v1 = v1[~v1.index.duplicated()]
        f["prev_ts"] = f["ts_event"].shift(1)
        key = pd.MultiIndex.from_arrays([f["prev_ts"], f["instrument_id"]])
        f["prev_close"] = px.reindex(key).to_numpy()
        f["r"] = f["close"] / f["prev_close"] - 1.0
        f["roll"] = f["instrument_id"] != f["instrument_id"].shift(1)
        f.loc[0, "roll"] = False
        f["vol_tot"] = f["volume"].astype(float) + v1.reindex(f["ts_event"]).fillna(0).to_numpy()
        f["root"] = root
        out.append(f)
    h = pd.concat(out, ignore_index=True)
    h["start_et"] = h["ts_event"].dt.tz_convert("America/New_York")
    h["end_et"] = h["start_et"] + pd.Timedelta(hours=1)  # tz-aware addition in absolute time
    h["hour"] = h["start_et"].dt.hour
    h["date_et"] = h["start_et"].dt.tz_localize(None).dt.normalize()
    return h


def nyse_days() -> pd.DatetimeIndex:
    e = pd.read_parquet(GQH / "etf_daily.parquet")
    d = pd.DatetimeIndex(sorted(e.loc[e["ticker"] == "SPY", "date"].unique()))
    d = d.astype("datetime64[ns]")
    return d[(d >= "2010-01-01") & (d <= "2026-10-02")]


def assign_return_day(h: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    # 16:00 ET close of each NYSE day as UTC timestamps (DST aware)
    closes = (days + pd.Timedelta(hours=16)).tz_localize("America/New_York").tz_convert("UTC").as_unit("ns")
    end_utc = h["ts_event"] + pd.Timedelta(hours=1)
    idx = np.searchsorted(closes.asi8, end_utc.astype("int64").to_numpy(), side="left")  # first close >= end
    ok = idx < len(days)
    rd = np.full(len(h), np.datetime64("NaT"), dtype="datetime64[ns]")
    rd[ok] = days.values[idx[ok]]
    h["rd"] = rd
    return h


def month_offsets(days: pd.DatetimeIndex) -> pd.DataFrame:
    s = pd.Series(np.arange(len(days)), index=days)
    per = days.to_period("M")
    last = s.groupby(per).transform("max").to_numpy()
    df = pd.DataFrame({"date": days, "i": np.arange(len(days)), "Ti": last})
    df["T"] = days.values[last]
    df["off"] = df["i"] - df["Ti"]
    df.loc[per == per[-1], ["off"]] = np.nan if days[-1] != pd.Timestamp("2026-09-30") else df["off"]
    return df


# ------------------------------------------------------------------ stats
def nw_t(x, lags=3):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    e = x - x.mean()
    s = e @ e / n
    for L in range(1, lags + 1):
        s += 2 * (1 - L / (lags + 1)) * (e[L:] @ e[:-L]) / n
    return x.mean() / math.sqrt(s / n)


def sharpe(x):
    return x.mean() / x.std() * math.sqrt(252)


# ------------------------------------------------------------------ main
def main():
    days = nyse_days()
    h = build_hourly()
    h = assign_return_day(h, days)
    log("hourly rows", len(h), "nan returns", int(h["r"].isna().sum()), "rolls", h.groupby("root")["roll"].sum().to_dict())
    # cross-check: compounded 16-16 returns vs ES16/ZN16 excess
    f16 = pd.read_parquet(GQH / "futures_1600.parquet")
    rf = pd.read_parquet(GQH / "rf_daily.parquet").set_index("date")["rf"]
    for root, tk in (("ES", "ES16"), ("ZN", "ZN16")):
        s = f16[f16.ticker == tk].set_index("date")["close"].sort_index(); s.index = pd.to_datetime(s.index); rf.index = pd.to_datetime(rf.index)
        ex = s.pct_change() - rf.reindex(s.index).fillna(0)
        hd = h[h.root == root].groupby("rd")["r"].apply(lambda v: np.prod(1 + v.dropna()) - 1)
        hd.index = pd.to_datetime(hd.index); ex.index = pd.to_datetime(ex.index); j = pd.concat([hd, ex], axis=1, keys=["h", "d"]).dropna()
        dd = (j.h - j.d) * 1e4
        log(f"{root} hourly-vs-{tk}: n {len(j)} corr {j.corr().iloc[0,1]:.6f} mean|d| {dd.abs().mean():.3f}bp >5bp {int((dd.abs()>5).sum())}")

    mo = month_offsets(days)
    # incomplete Oct 2026: no T
    mo.loc[mo["date"] >= "2026-10-01", "off"] = np.nan
    w = pd.read_parquet(OTHER / "sleeve_weights.parquet")
    w["date"] = pd.to_datetime(w["date"])
    w = w.set_index("date")
    # check analyst's window labelling against my calendar
    chk = w[w.C_ZN != 0].join(mo.set_index("date")[["off", "T"]])
    log("C window offsets (mine) of held days:", chk["off"].value_counts().to_dict(),
        " C_T == my T:", bool((chk["C_T"] == chk["T"]).all()))
    chk = w[w.A_ES != 0].join(mo.set_index("date")[["off", "T"]])
    log("A window offsets (mine) of held days:", chk["off"].value_counts().to_dict(),
        " A_T == my T:", bool((pd.to_datetime(chk["A_T"]) == chk["T"]).all()))

    # spot check C weight = min(q*0.10/vol63, 2) with vol63 of ZN16 excess? (repo uses close-to-close of the instrument)
    mi = pd.read_csv(OTHER / "month_info.csv", parse_dates=["T"])
    zn = f16[f16.ticker == "ZN16"].set_index("date")["close"].sort_index()
    es = f16[f16.ticker == "ES16"].set_index("date")["close"].sort_index()
    vz = zn.pct_change().rolling(63).std() * math.sqrt(252)
    ve = es.pct_change().rolling(63).std() * math.sqrt(252)
    moi = mo.set_index("date")
    errs = []
    for _, r in mi.dropna(subset=["C_q"]).iterrows():
        T = r["T"]
        if T not in moi.index:
            continue
        iT = int(moi.loc[T, "i"])
        d4 = days[iT - 4]
        wexp = min(r["C_q"] * 0.10 / vz.get(d4, np.nan), 2.0)
        held = w.loc[(w.C_T == T) & (w.C_ZN != 0), "C_ZN"] if "C_T" in w else None
        if held is not None and len(held):
            errs.append(abs(held.iloc[0] - wexp))
    errs = np.array(errs)
    log(f"C weight spot-check vs min(q*0.10/vol63(T-4),2): n {len(errs)} max|err| {np.nanmax(errs):.2e} n>1e-6 {int((errs>1e-6).sum())}")

    # ---------------- bar-level positions per variant
    hb = h[h["rd"].notna()].copy()
    hb = hb.merge(mo[["date", "off", "T"]], left_on="rd", right_on="date", how="left").drop(columns="date")
    holes = hb["r"].isna()
    hb["r"] = hb["r"].fillna(0.0)

    def windows(sleeve):
        col = "C_ZN" if sleeve == "C" else "A_ES"
        Tcol = f"{sleeve}_T"
        ww = w[w[col] != 0]
        g = ww.groupby(Tcol)
        tab = pd.DataFrame({"first": g.apply(lambda x: x.index.min()), "last": g.apply(lambda x: x.index.max()),
                            "n": g.size()})
        if sleeve == "C":
            tab["ZN"] = g["C_ZN"].first()
        else:
            tab["ES"] = g["A_ES"].first()
            tab["ZN"] = g["A_ZN"].first()
        return tab

    def position(root, tab, variant):
        """Return per-bar weight W for root's bars under a variant (my own construction from timestamps)."""
        d = hb[hb.root == root]
        W = np.zeros(len(d))
        s_utc = d["ts_event"].dt.tz_localize(None).to_numpy().astype("datetime64[ns]")
        e_utc = s_utc + np.timedelta64(1, "h")
        hour = d["hour"].to_numpy()
        datet = d["date_et"].to_numpy()
        rdv = d["rd"].to_numpy()
        for T, row in tab.iterrows():
            if root not in row or row[root] == 0:
                continue
            first, last = row["first"], row["last"]
            ifirst = days.get_loc(first)
            entry_day = days[ifirst - 1]
            t0 = (entry_day + pd.Timedelta(hours=16)).tz_localize("America/New_York").tz_convert("UTC").tz_localize(None).to_datetime64()
            exit_h = {"base": 16, "exit_1500": 15, "exit_1700": 17, "day_only": 16, "night_only": 16}[variant]
            t1 = (last + pd.Timedelta(hours=exit_h)).tz_localize("America/New_York").tz_convert("UTC").tz_localize(None).to_datetime64()
            m = (e_utc > t0) & (e_utc <= t1)
            daym = (datet == rdv) & (hour >= 9) & (hour <= 15)
            if variant == "day_only":
                m &= daym
            elif variant == "night_only":
                m &= ~daym
            W[m] = row[root]
        return d, W

    def ledger(d, W, root, roll_cost=True):
        r = d["r"].to_numpy()
        Wp = np.r_[0.0, W[:-1]]
        pnl = W * r
        turn = np.abs(W - Wp)
        # exits happen at the close of the last held bar, i.e. at the boundary into the next bar: assign to prev bar's day
        rd = d["rd"].to_numpy()
        roll = d["roll"].to_numpy()
        rc = np.where(roll & (W != 0) & (Wp != 0), 2 * np.abs(Wp), 0.0) if roll_cost else 0.0 * W
        # attribution of trade at boundary before bar i: to rd of bar i-1 if exit (W==0) else rd of bar i
        rd_prev = np.r_[rd[:1], rd[:-1]]
        trade_day = np.where(W == 0, rd_prev, rd)
        df = pd.DataFrame({"rd": rd, "pnl": pnl, "trade_day": trade_day, "turn": turn + rc})
        p = df.groupby("rd")["pnl"].sum()
        c = df.groupby("trade_day")["turn"].sum() * COST[root]
        tr = df.groupby("trade_day")["turn"].sum()
        return p, c, tr

    variants = ["base", "exit_1500", "exit_1700", "day_only", "night_only"]
    rows = []
    store = {}
    for sleeve in ("C", "A"):
        tab = windows(sleeve)
        roots = ["ZN"] if sleeve == "C" else ["ES", "ZN"]
        first_entry = days[days.get_loc(tab["first"].min()) - 1]
        for v in variants:
            P = pd.Series(0.0, index=days)
            Cc = pd.Series(0.0, index=days)
            Tr = pd.Series(0.0, index=days)
            Cnr = pd.Series(0.0, index=days)
            bars = []
            for root in roots:
                d, W = position(root, tab, v)
                p, c, tr = ledger(d, W, root)
                _, cnr, _ = ledger(d, W, root, roll_cost=False)
                P = P.add(p.reindex(days).fillna(0), fill_value=0)
                Cc = Cc.add(c.reindex(days).fillna(0), fill_value=0)
                Cnr = Cnr.add(cnr.reindex(days).fillna(0), fill_value=0)
                Tr = Tr.add(tr.reindex(days).fillna(0), fill_value=0)
                bb = d.assign(W=W, x=W * d["r"].to_numpy())
                bars.append(bb[bb.W != 0])
            store[(sleeve, v)] = (P, Cc, Cnr, pd.concat(bars))
            # window attribution: each day's pnl/cost to the window T whose span covers it
            wT = pd.Series(pd.NaT, index=days, dtype="datetime64[ns]")
            for T, row in tab.iterrows():
                i0 = days.get_loc(row["first"])
                i1 = days.get_loc(row["last"]) + (1 if v == "exit_1700" else 0)
                wT.iloc[i0 - 1:i1 + 1] = T  # include entry day (no pnl, cost may sit there? not here) and exit day(s)
            for smp, (a, b) in {"IS": (first_entry, IS_END), "later": (LATER0, LATER1),
                                "IS_pre": (first_entry, PUB - pd.Timedelta(days=1)), "IS_post": (PUB, IS_END)}.items():
                if sleeve == "A" and smp in ("IS_pre", "IS_post"):
                    continue
                m = (days >= a) & (days <= b)
                yrs = m.sum() / 252
                for cl, cm in (("gross", 0), ("1x", 1), ("2x", 2), ("1x_noroll", None)):
                    x = (P - (Cnr if cm is None else cm * Cc))[m]
                    wp = x.groupby(wT[m]).sum()
                    sr = sharpe(x)
                    rows.append({"sleeve": sleeve, "variant": v, "sample": smp, "cost": cl, "years": round(yrs, 2),
                                 "sharpe": sr, "se": math.sqrt((1 + sr * sr / 2) / yrs), "n_win": len(wp),
                                 "mean_win_bp": wp.mean() * 1e4, "t_nw": nw_t(wp.sort_index().to_numpy(), 3),
                                 "cost_per_win_bp_1x": Cc[m].sum() / max(len(wp), 1) * 1e4,
                                 "turn_per_win": Tr[m].sum() / max(len(wp), 1)})
    res = pd.DataFrame(rows)
    res.to_csv(HERE / "my_variants.csv", index=False)
    pd.set_option("display.width", 220)
    log(res[res["sample"].isin(["IS", "later"])].round(3).to_string())
    log(res[res["sample"].isin(["IS_pre", "IS_post"]) & (res.cost.isin(["gross", "1x"]))].round(3).to_string())
    pd.to_pickle({"store": store, "days": days, "mo": mo, "hb": hb}, HERE / "store.pkl")
    (HERE / "v01_log.txt").write_text("\n".join(OUT), encoding="utf-8")


if __name__ == "__main__":
    main()
