"""Futures carry (Koijen, Moskowitz, Pedersen & Vrugt 2018), implemented exactly as SPEC.md declares.

Run from the repo root with GQH_DATA_DIR set. Reads only; writes only under the scratchpad edges/ folders.
Never touches results/, never unlocks the OOS loader, never logs trials.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<solo-repo>")
sys.path.insert(0, str(REPO))
from src import engine as E  # noqa: E402
from src import forward2 as F2M  # noqa: E402

HERE = Path(__file__).resolve().parent
SERIES = HERE.parent / "series"
IS_END = pd.Timestamp("2024-10-02")
LATER_START = pd.Timestamp("2024-10-03")
PUB_SPLIT = pd.Timestamp("2013-07-31")

CLASSES = {
    "fx": ["6E", "6J", "6B", "6A", "6C", "6S"],
    "rates": ["ZT", "ZF", "ZN", "ZB", "UB"],
    "comm": ["CL", "HO", "RB", "NG", "GC", "SI", "PL", "HG", "ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE"],
    "eq": ["ES", "NQ", "YM", "RTY"],
}
ROOTS = [r for v in CLASSES.values() for r in v]
TICK = [f"F_{r}" for r in ROOTS]
COST = {"ES": 0.5, "NQ": 0.75, "YM": 0.75, "RTY": 1.0, "ZT": 0.3, "ZF": 0.5, "ZN": 1.0, "ZB": 1.25, "UB": 1.5,
        "6E": 0.5, "6J": 0.75, "6B": 0.75, "6A": 0.75, "6C": 0.75, "6S": 1.0, "CL": 1.5, "GC": 1.5, "SI": 1.5,
        "HG": 1.5, "NG": 2.5, "HO": 2.5, "RB": 2.5, "PL": 2.5, "ZC": 4.0, "ZS": 4.0, "ZW": 4.0, "ZL": 4.0,
        "ZM": 4.0, "LE": 4.0, "HE": 4.0}
COST_BPS = {f"F_{r}": v for r, v in COST.items()}

INSTR_VOL = 0.10
TARGET_VOL = 0.10
SCALE_CAP = 4.0
COV_WINDOW = 252
EWMA_COM = 60
MIN_HISTORY = 300
ACTIVE_WINDOW = 10
SIGNALS = {"C1": (21, 10), "C12": (252, 126)}


# ----------------------------------------------------------------------------------------------- carry

def carry_observations() -> pd.DataFrame:
    """Raw-date x root frame of daily front/second carry (positive = backwardation)."""
    c = pd.read_parquet(HERE / "contracts.parquet")
    p = c.pivot_table(index=["root", "date"], columns="rank", values=["close", "month_index"], aggfunc="first")
    p.columns = [f"{a}{b}" for a, b in p.columns]
    p = p.reset_index()
    ok = (p["close0"] > 0) & (p["close1"] > 0) & p["month_index0"].notna() & p["month_index1"].notna()
    p = p[ok].copy()
    dm = p["month_index1"] - p["month_index0"]
    p = p[(dm != 0) & (dm.abs() <= 12)].copy()
    near0 = p["month_index0"] < p["month_index1"]
    p_near = np.where(near0, p["close0"], p["close1"])
    p_far = np.where(near0, p["close1"], p["close0"])
    dt = (p["month_index1"] - p["month_index0"]).abs() / 12.0
    p["carry"] = (p_near / p_far) ** (1.0 / dt) - 1.0
    p["dt_m"] = dt * 12
    return p[["root", "date", "carry", "dt_m"]]


def carry_on_calendar(obs: pd.DataFrame, cal: pd.DatetimeIndex) -> pd.DataFrame:
    """NYSE-calendar frame: last observation per root on raw dates mapped to the next NYSE session >= them."""
    pos = cal.searchsorted(obs["date"].values, side="left")
    keep = pos < len(cal)
    o = obs[keep].copy()
    o["nyse"] = cal[pos[keep]]
    o = o.sort_values(["root", "date"]).groupby(["root", "nyse"]).last().reset_index()
    wide = o.pivot(index="nyse", columns="root", values="carry").reindex(index=cal)
    return wide.reindex(columns=ROOTS)


def signals(daily: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """C1 / C12 trailing means; lagged one extra session (the raw daily bar closes at 00:00 UTC)."""
    out = {}
    for name, (win, minobs) in SIGNALS.items():
        s = daily.rolling(win, min_periods=minobs).mean()
        out[name] = s.shift(1)
    return out


# ----------------------------------------------------------------------------------------------- books

def scale_book(w: pd.Series, cov: pd.DataFrame) -> tuple[pd.Series, float]:
    cols = [c for c in w.index if w[c] != 0]
    if not cols:
        return w * 0.0, float("nan")
    m = cov.loc[cols, cols].fillna(0.0).to_numpy()
    v = w[cols].to_numpy()
    var = float(v @ m @ v) * 252
    if not np.isfinite(var) or var <= 0:
        return w * 0.0, float("nan")
    k = min(TARGET_VOL / math.sqrt(var), SCALE_CAP)
    return w * k, k


def rank_weights(sig: pd.Series) -> pd.Series:
    n = len(sig)
    rk = sig.rank(method="average")
    dev = rk - (n + 1) / 2.0
    pos = dev[dev > 0].sum()
    if pos <= 0:
        return dev * 0.0
    return dev / pos


def decision_dates(cal: pd.DatetimeIndex, freq: str) -> pd.DatetimeIndex:
    if freq == "M":
        return F2M._month_ends(cal)
    s = pd.Series(cal, index=cal)
    last = s.groupby(cal.to_period("W-FRI")).max()
    return pd.DatetimeIndex(last.values)


def build_books(sig: pd.DataFrame, ex: pd.DataFrame, vol: pd.DataFrame, elig_base: pd.DataFrame,
                dates: pd.DatetimeIndex) -> dict:
    """Decision weights for every class book and the global book, XS and TS. Returns dict[(cons, book)] -> frame,
    plus scale diagnostics."""
    books = {(cons, b): pd.DataFrame(np.nan, index=ex.index, columns=TICK)
             for cons in ("XS", "TS") for b in list(CLASSES) + ["global"]}
    diag = []
    for t in dates:
        hist = ex.loc[:t].tail(COV_WINDOW)
        cov = hist.cov(min_periods=60)
        for cons in ("XS", "TS"):
            class_books = {}
            for cl, roots in CLASSES.items():
                tk = [f"F_{r}" for r in roots]
                el = [x for x in tk if bool(elig_base.loc[t, x]) and np.isfinite(sig.loc[t, x[2:]])]
                w = pd.Series(0.0, index=TICK)
                k = float("nan")
                if cons == "XS" and len(el) >= 3:
                    rw = rank_weights(sig.loc[t, [x[2:] for x in el]])
                    rw.index = el
                    w[el] = rw * INSTR_VOL / vol.loc[t, el]
                    w, k = scale_book(w, cov)
                elif cons == "TS" and len(el) >= 1:
                    sg = np.sign(sig.loc[t, [x[2:] for x in el]].to_numpy())
                    w[el] = sg * INSTR_VOL / vol.loc[t, el].to_numpy() / len(el)
                    w, k = scale_book(w, cov)
                if w.abs().sum() > 0:
                    class_books[cl] = w
                books[(cons, cl)].loc[t] = w.values
                diag.append(dict(date=t, cons=cons, book=cl, n=len(el), scale=k, gross=float(w.abs().sum())))
            g = pd.Series(0.0, index=TICK)
            kk = float("nan")
            if class_books:
                for w in class_books.values():
                    g = g + w / len(class_books)
                g, kk = scale_book(g, cov)
            books[(cons, "global")].loc[t] = g.values
            diag.append(dict(date=t, cons=cons, book="global", n=len(class_books), scale=kk,
                             gross=float(g.abs().sum())))
    for key in books:
        books[key] = books[key].ffill().fillna(0.0)
    return books, pd.DataFrame(diag)


# ----------------------------------------------------------------------------------------------- stats

def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(252)) if len(x) > 20 and x.std() > 0 else float("nan")


def max_dd(x: pd.Series) -> float:
    eq = (1 + x.fillna(0.0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


def block_boot_sharpe(x: np.ndarray, y: np.ndarray | None = None, block: int = 63, reps: int = 2000, seed: int = 7):
    rng = np.random.default_rng(seed)
    n = len(x)
    nb = int(math.ceil(n / block))
    out, diff = [], []
    for _ in range(reps):
        starts = rng.integers(0, n, nb)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
        xs = x[idx]
        s = xs.mean() / xs.std() * math.sqrt(252)
        out.append(s)
        if y is not None:
            ys = y[idx]
            diff.append(s - ys.mean() / ys.std() * math.sqrt(252))
    res = {"boot_sr_p05": float(np.percentile(out, 5)), "boot_sr_p95": float(np.percentile(out, 95)),
           "boot_p_sr_le0": float(np.mean(np.array(out) <= 0))}
    if y is not None:
        res.update({"boot_diff_vs_S1_p05": float(np.percentile(diff, 5)),
                    "boot_diff_vs_S1_p95": float(np.percentile(diff, 95)),
                    "boot_p_diff_le0": float(np.mean(np.array(diff) <= 0))})
    return res


def window_stats(df: pd.DataFrame, turnover: pd.Series, gross_n: pd.Series, refs: dict, boot: bool = False) -> dict:
    """df columns net_1x, net_2x, gross (daily excess returns) on one window."""
    n1 = df["net_1x"]
    yrs = len(n1) / 252
    yearly = (1 + n1).groupby(n1.index.year).prod() - 1
    ycount = n1.groupby(n1.index.year).size()
    yearly_full = yearly[ycount >= 126]
    roll = n1.rolling(504).mean() / n1.rolling(504).std() * math.sqrt(252)
    roll = roll.dropna()
    out = {
        "start": str(n1.index[0].date()), "end": str(n1.index[-1].date()), "years": round(yrs, 2),
        "sharpe_net_1x": sharpe(n1), "sharpe_net_2x": sharpe(df["net_2x"]), "sharpe_gross": sharpe(df["gross"]),
        "ann_mean_excess": float(n1.mean() * 252),
        "cagr_excess": float((1 + n1).prod() ** (1 / yrs) - 1) if yrs > 0 else float("nan"),
        "ann_vol": float(n1.std() * math.sqrt(252)), "max_dd": max_dd(n1),
        "worst_year": float(yearly_full.min()) if len(yearly_full) else float("nan"),
        "worst_year_label": int(yearly_full.idxmin()) if len(yearly_full) else None,
        "pct_pos_years": float((yearly_full > 0).mean()) if len(yearly_full) else float("nan"),
        "roll2y_p10": float(roll.quantile(0.10)) if len(roll) else float("nan"),
        "roll2y_p50": float(roll.quantile(0.50)) if len(roll) else float("nan"),
        "roll2y_p90": float(roll.quantile(0.90)) if len(roll) else float("nan"),
        "turnover_per_year": float(turnover.reindex(n1.index).sum() / yrs) if yrs > 0 else float("nan"),
        "mean_gross_notional": float(gross_n.reindex(n1.index).mean()),
        "max_gross_notional": float(gross_n.reindex(n1.index).max()),
        "nw_t": E.newey_west_tstat(n1),
        "skew": float(n1.skew()),
    }
    for k, r in refs.items():
        j = pd.concat([n1, r], axis=1, join="inner").dropna()
        out[f"corr_{k}"] = float(j.iloc[:, 0].corr(j.iloc[:, 1])) if len(j) > 60 else float("nan")
    if boot:
        j = pd.concat([n1, refs["S1"]], axis=1, join="inner").dropna()
        out.update(block_boot_sharpe(j.iloc[:, 0].to_numpy(), j.iloc[:, 1].to_numpy()))
    return out


# ----------------------------------------------------------------------------------------------- main

def main() -> None:
    period = "FWD"            # every date through 2026-10-02; signals are point-in-time, windows sliced below
    ohlc = E.load_ohlc(TICK, period)
    rf = E.load_rf(period).reindex(ohlc["close"].index).ffill().fillna(0.0)
    cal = ohlc["close"].index
    ex = ohlc["close"].pct_change(fill_method=None).sub(rf, axis=0)
    vol = np.sqrt(ex.pow(2).ewm(com=EWMA_COM, min_periods=60).mean() * 252)
    counts = ex.notna().cumsum()
    traded = (ohlc["volume"].fillna(0.0) > 0).astype(float)
    active = traded.rolling(ACTIVE_WINDOW, min_periods=1).max().astype(bool)
    elig_base = (counts >= MIN_HISTORY) & np.isfinite(vol) & (vol > 0) & active

    obs = carry_observations()
    daily = carry_on_calendar(obs, cal)
    sigs = signals(daily)
    daily.to_parquet(HERE / "carry_daily.parquet")
    for k, s in sigs.items():
        s.to_parquet(HERE / f"signal_{k}.parquet")

    # reference series (read-only use of the frozen forward-test code)
    from src import forward as F1M
    es_ex = ex["F_ES"]
    s1 = F2M.returns("S1", period) - rf
    f2 = F1M.returns("F2", period)
    f2 = f2 - rf.reindex(f2.index).ffill().fillna(0.0)
    refs_all = {"ES": es_ex, "S1": s1, "F2": f2}

    series, meta, diags = {}, {}, []
    for sname, sig in sigs.items():
        for freq in ("M", "W"):
            dates = decision_dates(cal, freq)
            books, diag = build_books(sig, ex, vol, elig_base, dates)
            diag["signal"], diag["freq"] = sname, freq
            diags.append(diag)
            for (cons, book), w in books.items():
                tk = TICK if book == "global" else [f"F_{r}" for r in CLASSES[book]]
                w = w[tk]
                res = {}
                for lab, mult in (("net_1x", 1.0), ("net_2x", 2.0)):
                    net, gross, turn, held, _ = E.simulate(w, {k: v[tk] for k, v in ohlc.items()}, rf,
                                                           exec="next_close", cost_mult=mult, cost_bps=COST_BPS)
                    res[lab] = net - rf
                    if mult == 1.0:
                        res["gross"] = gross - rf
                        res["_turn"] = turn
                        res["_gross_n"] = held.abs().sum(axis=1)
                        res["_live"] = held.abs().sum(axis=1) > 0
                key = f"{cons}_{book}_{sname}_{freq}"
                series[key] = res
                print("built", key, flush=True)

    # common start: first session on which every global variant holds positions
    starts = [series[k]["_live"].idxmax() for k in series if "_global_" in k]
    start = max(starts)
    print("common start", start.date())
    rows = []
    for key, res in series.items():
        cons, book, sname, freq = key.split("_")
        df = pd.DataFrame({c: res[c] for c in ("net_1x", "net_2x", "gross")}).loc[start:]
        windows = {"IS": df.loc[:IS_END], "IS_pre_pub": df.loc[:PUB_SPLIT], "IS_post_pub": df.loc[PUB_SPLIT + pd.Timedelta(days=1):IS_END],
                   "LATER": df.loc[LATER_START:], "IS_2011_2014": df.loc[:"2014-12-31"],
                   "IS_2015_2019": df.loc["2015-01-01":"2019-12-31"], "IS_2020_2024": df.loc["2020-01-01":IS_END]}
        for wn, d in windows.items():
            if len(d) < 60:
                continue
            st = window_stats(d, res["_turn"], res["_gross_n"], refs_all, boot=(wn == "IS" and book == "global"))
            rows.append(dict(series=key, construction=cons, book=book, signal=sname, rebalance=freq, window=wn, **st))
    table = pd.DataFrame(rows)
    # deflated Sharpe across the 8 global variants (in-sample, realistic costs)
    gl = table[(table.book == "global") & (table.window == "IS")]
    var_sr = float(gl["sharpe_net_1x"].var(ddof=1))
    dsr = {}
    for key in gl["series"]:
        d = pd.DataFrame({c: series[key][c] for c in ("net_1x",)}).loc[start:IS_END]["net_1x"]
        dsr[key] = E.deflated_sharpe(d, n_trials=8, var_sr_ann=var_sr)["dsr"]
    table["dsr_8"] = table.apply(lambda r: dsr.get(r["series"]) if (r["window"] == "IS") else np.nan, axis=1)
    table.to_csv(HERE / "carry_all_variants.csv", index=False)
    pd.concat(diags).to_csv(HERE / "book_diagnostics.csv", index=False)

    # headline selection: per construction, highest IS net Sharpe (1x) among its 4 global variants
    sel = {}
    for cons in ("XS", "TS"):
        g = gl[gl.construction == cons].sort_values("sharpe_net_1x", ascending=False)
        sel[cons] = g.iloc[0]["series"]
        med = float(g["sharpe_net_1x"].median())
        print(cons, "selected", sel[cons], "IS SR", round(g.iloc[0]["sharpe_net_1x"], 3), "median of 4", round(med, 3))
    json.dump({"selected": sel, "common_start": str(start.date()), "var_sr_global_is": var_sr},
              open(HERE / "selection.json", "w"), indent=2)

    # write series: headline globals and the class books of the same variant
    SERIES.mkdir(parents=True, exist_ok=True)
    for cons, key in sel.items():
        _, _, sname, freq = key.split("_")
        for book in ["global"] + list(CLASSES):
            k = f"{cons}_{book}_{sname}_{freq}"
            df = pd.DataFrame({c: series[k][c] for c in ("net_1x", "net_2x", "gross")}).loc[start:]
            df.index.name = "date"
            name = f"carry_{cons.lower()}_{book}"
            df.to_parquet(SERIES / f"{name}.parquet")
            side = {
                "candidate": name, "variant": k,
                "rule": (f"Futures carry, {('cross-sectional rank-weighted' if cons == 'XS' else 'time-series sign')} "
                         f"(KMPV 2018), signal {sname} ({'21' if sname == 'C1' else '252'}-session trailing mean of "
                         f"front/second annualised carry, lagged 1 session), {('monthly' if freq == 'M' else 'weekly')} "
                         f"decisions, next-close fills, book: {book}"),
                "universe": CLASSES[book] if book != "global" else CLASSES,
                "columns": {"net_1x": "daily excess return over T-bill net of the realistic cost map",
                            "net_2x": "same at 2x costs", "gross": "before costs"},
                "cost_bps_one_way": {r: COST[r] for r in (ROOTS if book == "global" else CLASSES[book])},
                "vol_scaling": "10% annualised ex-ante via trailing 252-session sample covariance of daily instrument "
                               "excess returns (min 60 obs), instruments normalised by EWMA vol (com 60); scale cap 4",
                "window": {"start": str(start.date()), "in_sample_end": str(IS_END.date()),
                           "later_window": f"{LATER_START.date()}..{df.index[-1].date()} (descriptive only)"},
                "selection": "headline variant = highest in-sample net Sharpe among 4 global variants of this "
                             "construction; class books use the same variant (no per-class selection)",
                "spec": str(HERE / "SPEC.md"),
            }
            (SERIES / f"{name}.json").write_text(json.dumps(side, indent=2))
    print("done")


if __name__ == "__main__":
    main()
