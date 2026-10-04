"""Forward test 2 runner (FORWARD_TEST_2.md).

    python scripts/run_forward2.py positions   # target weights for the first forward session, from the latest data
    python scripts/run_forward2.py evaluate    # performance on return days >= FWD_START (needs fresh data)

Every evaluation is appended to forward/forward2_log.csv and written to forward/report2_<last date>.json.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src import analysis as AN  # noqa: E402
from src import config as C  # noqa: E402
from src import engine as E  # noqa: E402
from src import forward2 as F2  # noqa: E402

LOG = C.FWD_DIR / "forward2_log.csv"


def positions() -> None:
    last = pd.Timestamp(E.data_end("FWD"))
    # the return day these weights are held over: second business day after the data (2026-10-06 for data
    # through 2026-10-02, the frozen file); later data get their own file instead of overwriting the frozen one
    first = pd.bdate_range(last + pd.Timedelta(days=1), periods=2)[-1]
    rows = []
    for name in F2.STRATEGIES:
        for tk, w in F2.positions_for_next_session(name, "FWD").items():
            rows.append({"strategy": name, "instrument": tk, "weight_of_nav": round(float(w), 6),
                         "held_over_return_day": str(first.date()), "data_through": str(last.date())})
    C.FWD_DIR.mkdir(parents=True, exist_ok=True)
    out = C.FWD_DIR / f"positions2_for_{first.date()}.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"wrote {out} ({len(rows)} rows)")


def _weekly_corr(a: pd.Series, ticker: str) -> float | None:
    """Implementation check: weekly correlation with a public managed-futures fund (Yahoo)."""
    try:
        import yfinance as yf

        px = yf.download(ticker, start=str(a.index[0].date()), auto_adjust=True, progress=False)["Close"].squeeze()
        b = px.pct_change().dropna()
        wa = (1 + a).resample("W-FRI").prod() - 1
        wb = (1 + b).resample("W-FRI").prod() - 1
        j = pd.concat([wa, wb], axis=1, join="inner").dropna()
        return float(j.iloc[:, 0].corr(j.iloc[:, 1])) if len(j) >= 8 else None
    except Exception:
        return None


def _last_data_dates() -> dict:
    """Last session with data per instrument: a traded day for futures (download_databento.py pads days
    without vendor bars with a zero excess return and zero volume), a close for ETFs."""
    tickers = sorted({t for spec in F2.SPECS.values() for t in spec[1]})
    ohlc = E.load_ohlc(tickers, "FWD")
    out = {}
    for t in tickers:
        ok = ohlc["volume"][t] > 0 if t.startswith("F_") else ohlc["close"][t].notna()
        out[t] = str(ok[ok].index.max().date()) if ok.any() else None
    return out


def evaluate() -> None:
    last = E.data_end("FWD")
    if pd.Timestamp(last) < pd.Timestamp(C.FWD_START):
        print(f"no forward data yet: latest cached session is {last}, forward window starts {C.FWD_START}")
        return
    # data check before anything is scored or logged: stale futures files would score S1/S2/ES_10VOL as flat
    seen = _last_data_dates()
    no_data = sorted(t for t, d in seen.items() if d is None or d < last)
    if all(t in no_data for t in seen if t.startswith("F_")):
        raise SystemExit(
            f"REFUSED, nothing logged: no futures contract has data on {last} (latest futures data "
            f"{max((d for t, d in seen.items() if t.startswith('F_') and d), default=None)}). Rebuild the futures with "
            f"data/download_databento.py in a fresh GQH_DATA_DIR holding this run's download.py output, with "
            f"GQH_DATA_END set to the day after {last}, and evaluate with that same GQH_DATA_DIR.")
    if no_data:
        print(f"WARNING: no data on {last} for {no_data} (delisting, vendor gap or partial refresh; see report)")
    rf = E.load_rf("FWD")
    report = {"as_of": last, "forward_start": C.FWD_START, "primary": F2.PRIMARY,
              "last_data_date": seen, "no_data_on_as_of": no_data, "strategies": {}}
    for name in F2.STRATEGIES + F2.BENCHMARKS:
        net = F2.returns(name, "FWD").loc[C.FWD_START:]
        if len(net) == 0:
            continue
        ex = net - rf.reindex(net.index).ffill().fillna(0.0)
        st = E.perf_stats(net, ex, pd.Series(0.0, index=net.index)) if len(net) > 2 else {}
        st.update({"n_days": len(net), "cumulative_return": float((1 + net).prod() - 1),
                   "sharpe_standard_error": float(math.sqrt(252 / max(len(ex), 1)))})
        if len(ex) >= 63:
            st["bootstrap_sharpe_90"] = AN.bootstrap_sharpe_ci(ex)
        if name == "S1":
            st["weekly_corr_DBMF"] = _weekly_corr(net, "DBMF")
            st["weekly_corr_AQMIX"] = _weekly_corr(net, "AQMIX")
        report["strategies"][name] = st
        row = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "as_of": last, "name": name,
               "n_days": len(net), "sharpe": round(st.get("sharpe", float("nan")), 4),
               "cumulative_return": round(st["cumulative_return"], 5)}
        new = not LOG.exists()
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(row))
            if new:
                w.writeheader()
            w.writerow(row)
    (C.FWD_DIR / f"report2_{last}.json").write_text(json.dumps(report, indent=2, default=str))
    for k, v in report["strategies"].items():
        print(k, {x: v.get(x) for x in ("n_days", "sharpe", "ann_return", "max_drawdown", "cumulative_return")})


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "evaluate"
    {"positions": positions, "evaluate": evaluate}[cmd]()
