"""Shared helpers for bt_3 (see COMMON_SPEC.md). Read-only use of the repo; writes only under hunt100/."""
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

COMM = ["CL", "HO", "RB", "NG", "GC", "SI", "PL", "HG", "ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE"]
FX = ["6E", "6J", "6B", "6A", "6C", "6S"]
COST_ROOT = {"ES": 1.0, "NQ": 1.0, "YM": 1.0, "RTY": 2.0, "ZT": 0.5, "ZF": 0.7, "ZN": 1.0, "ZB": 1.5, "UB": 1.5,
             "6E": 1.0, "6J": 1.0, "6B": 1.0, "6A": 1.0, "6C": 1.0, "6S": 1.0,
             "CL": 2.0, "GC": 2.0, "SI": 2.0, "HG": 2.0, "NG": 3.0, "HO": 3.0, "RB": 3.0, "PL": 3.0,
             "ZC": 4.0, "ZS": 4.0, "ZW": 4.0, "ZL": 4.0, "ZM": 4.0, "LE": 4.0, "HE": 4.0}
COST_BPS = {f"F_{r}": v for r, v in COST_ROOT.items()}

EWMA_COM = 60
MIN_HISTORY = 260
ACTIVE_WINDOW = 10
COV_WINDOW = 252
TARGET_VOL = 0.10


def month_ends(cal: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return F2M._month_ends(cal)


def futures_panel(tickers: list[str]) -> dict:
    ohlc = E.load_ohlc(tickers, "FWD")
    idx = ohlc["close"].index
    rf = E.load_rf("FWD").reindex(idx).ffill().fillna(0.0)
    ex = ohlc["close"].pct_change(fill_method=None).sub(rf, axis=0)
    sigma = np.sqrt(ex.pow(2).ewm(com=EWMA_COM, min_periods=60).mean() * 252)
    counts = ex.notna().cumsum()
    traded = (ohlc["volume"].fillna(0.0) > 0).astype(float)
    active = traded.rolling(ACTIVE_WINDOW, min_periods=1).max().astype(bool)
    elig = (counts >= MIN_HISTORY) & np.isfinite(sigma) & (sigma > 0) & active
    return {"ohlc": ohlc, "rf": rf, "ex": ex, "sigma": sigma, "elig": elig, "cal": idx}


def etf_panel(tickers: list[str]) -> dict:
    ohlc = E.load_ohlc(tickers, "FWD")
    idx = ohlc["close"].index
    rf = E.load_rf("FWD").reindex(idx).ffill().fillna(0.0)
    ex = ohlc["close"].pct_change(fill_method=None).sub(rf, axis=0)
    return {"ohlc": ohlc, "rf": rf, "ex": ex, "cal": idx}


def book(w: pd.Series, ex_hist: pd.DataFrame, gross_cap: float, target: float = TARGET_VOL) -> pd.Series:
    """Scale w to `target` ex-ante vol (trailing COV_WINDOW-session covariance, min 60 obs), cap gross."""
    cols = [c for c in w.index if w[c] != 0]
    if not cols:
        return w * 0.0
    cov = ex_hist[cols].tail(COV_WINDOW).cov(min_periods=60).fillna(0.0).to_numpy()
    v = w[cols].to_numpy()
    var = float(v @ cov @ v) * 252
    if not np.isfinite(var) or var <= 0:
        return w * 0.0
    w = w * (target / math.sqrt(var))
    g = float(w.abs().sum())
    return w * (gross_cap / g) if g > gross_cap else w


def rank_pick(score: pd.Series, n: int) -> tuple[list[str], list[str]]:
    """Top-n and bottom-n names; ties broken by name order (stable)."""
    s = score.dropna()
    order = sorted(s.index, key=lambda k: (-s[k], k))
    return order[:n], order[-n:]


def run_sim(w_dec: pd.DataFrame, ohlc: dict, rf: pd.Series, exec: str, cost_bps: dict | None):
    tk = list(w_dec.columns)
    o = {k: v[tk] for k, v in ohlc.items()}
    out = {}
    turn1 = held1 = None
    for lab, mult in (("net_1x", 1.0), ("net_2x", 2.0)):
        net, gross, turn, held, _ = E.simulate(w_dec, o, rf, exec=exec, cost_mult=mult, cost_bps=cost_bps)
        out[lab] = net - rf.reindex(net.index).ffill().fillna(0.0)
        if mult == 1.0:
            out["gross"] = gross - rf.reindex(gross.index).ffill().fillna(0.0)
            turn1, held1 = turn, held
    df = pd.DataFrame(out)[["net_1x", "net_2x", "gross"]]
    df.index.name = "date"
    return df, turn1, held1


def first_live(held: pd.DataFrame) -> pd.Timestamp:
    live = held.abs().sum(axis=1) > 0
    return live.idxmax()


# ----------------------------------------------------------------------------------------------- references

def references() -> dict[str, pd.Series]:
    cache = HERE / "refs.parquet"
    if cache.exists():
        df = pd.read_parquet(cache)
        return {c: df[c] for c in df.columns}
    from src import forward as F1M

    rf = E.load_rf("FWD")
    es = E.load_ohlc(["F_ES"], "FWD")["close"]["F_ES"]
    rfa = rf.reindex(es.index).ffill().fillna(0.0)
    es_ex = es.pct_change(fill_method=None) - rfa
    s1 = F2M.returns("S1", "FWD")
    s1 = s1 - rf.reindex(s1.index).ffill().fillna(0.0)
    f2 = F1M.returns("F2", "FWD")
    f2 = f2 - rf.reindex(f2.index).ffill().fillna(0.0)
    df = pd.DataFrame({"ES": es_ex, "S1": s1, "F2": f2})
    df.to_parquet(cache)
    return {c: df[c] for c in df.columns}


# ----------------------------------------------------------------------------------------------- stats

def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(252)) if len(x) > 20 and x.std() > 0 else float("nan")


def max_dd(x: pd.Series) -> float:
    eq = (1 + x.fillna(0.0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


def window_stats(df: pd.DataFrame, turnover: pd.Series, refs: dict) -> dict:
    n1 = df["net_1x"]
    yrs = len(n1) / 252
    yearly = (1 + n1).groupby(n1.index.year).prod() - 1
    ycount = n1.groupby(n1.index.year).size()
    yfull = yearly[ycount >= 126]
    roll = (n1.rolling(504).mean() / n1.rolling(504).std() * math.sqrt(252)).dropna()
    out = {
        "start": str(n1.index[0].date()), "end": str(n1.index[-1].date()), "years": round(yrs, 2),
        "sharpe_net_1x": sharpe(n1), "sharpe_net_2x": sharpe(df["net_2x"]), "sharpe_gross": sharpe(df["gross"]),
        "ann_return": float(n1.mean() * 252),
        "cagr_excess": float((1 + n1).prod() ** (1 / yrs) - 1) if yrs > 0 else float("nan"),
        "ann_vol": float(n1.std() * math.sqrt(252)),
        "max_dd": max_dd(n1),
        "worst_year": float(yfull.min()) if len(yfull) else float("nan"),
        "worst_year_label": int(yfull.idxmin()) if len(yfull) else None,
        "pct_pos_years": float((yfull > 0).mean()) if len(yfull) else float("nan"),
        "roll2y_p10": float(roll.quantile(0.10)) if len(roll) else float("nan"),
        "turnover_per_year": float(turnover.reindex(n1.index).sum() / yrs) if yrs > 0 else float("nan"),
        "nw_t": E.newey_west_tstat(n1),
        "skew": float(n1.skew()),
        "yearly": {int(k): round(float(v), 4) for k, v in yfull.items()},
    }
    for k, r in refs.items():
        j = pd.concat([n1, r], axis=1, join="inner").dropna()
        out[f"corr_{k}"] = float(j.iloc[:, 0].corr(j.iloc[:, 1])) if len(j) > 60 else float("nan")
        out[f"corr_{k}_n"] = int(len(j))
    return out


def evaluate(variants: dict[str, tuple[pd.DataFrame, pd.Series, pd.DataFrame]], refs: dict,
             start_keys: list[str] | None = None) -> tuple[pd.Timestamp, pd.DataFrame, dict]:
    """variants: name -> (df, turnover, held). Returns common start, per-variant table, full stats dict."""
    keys = start_keys or list(variants)
    start = max(first_live(variants[k][2]) for k in keys)
    rows, full = [], {}
    for name, (df, turn, _) in variants.items():
        d = df.loc[start:]
        full[name] = {}
        for wn, dd in (("IS", d.loc[:IS_END]), ("LATER", d.loc[LATER_START:])):
            st = window_stats(dd, turn, refs)
            full[name][wn] = st
            rows.append({"variant": name, "window": wn, **{k: v for k, v in st.items() if k != "yearly"}})
    return start, pd.DataFrame(rows), full


def save_outputs(sid: str, folder: Path, variants: dict, start: pd.Timestamp, table: pd.DataFrame, full: dict,
                 sidecar: dict) -> str:
    """Pick the headline (best IS net_1x Sharpe), save the standard series + sidecar, variants, tables."""
    is_tab = table[table.window == "IS"].set_index("variant")
    head = str(is_tab["sharpe_net_1x"].idxmax())
    (folder / "variants").mkdir(exist_ok=True)
    for name, (df, _, held) in variants.items():
        df.loc[start:].to_parquet(folder / "variants" / f"{name}.parquet")
        held.loc[start:].to_parquet(folder / "variants" / f"{name}_held.parquet")
    table.to_csv(folder / "variants.csv", index=False)
    SERIES.mkdir(parents=True, exist_ok=True)
    df = variants[head][0].loc[start:]
    df.to_parquet(SERIES / f"{sid}.parquet")
    side = dict(sidecar)
    side.update({
        "id": sid, "headline_variant": head,
        "selection": "highest in-sample (start..2024-10-02) net Sharpe at realistic costs among the 3 pre-declared "
                     "variants; all variants reported in variants.csv",
        "columns": {"net_1x": "daily return minus T-bill, net of the realistic cost map",
                    "net_2x": "same at 2x costs", "gross": "daily return minus T-bill before costs"},
        "window": {"start": str(start.date()), "in_sample_end": str(IS_END.date()),
                   "later_window": f"{LATER_START.date()}..{df.index[-1].date()} (descriptive only)"},
        "spec": str(folder / "SPEC.md"),
        "variant_is_sharpe_net_1x": {k: round(float(v), 3) for k, v in is_tab["sharpe_net_1x"].items()},
    })
    (SERIES / f"{sid}.json").write_text(json.dumps(side, indent=2))
    (folder / "metrics.json").write_text(json.dumps({"headline": head, "start": str(start.date()),
                                                     "stats": full}, indent=2, default=float))
    return head
