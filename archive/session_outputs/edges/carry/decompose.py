"""Diagnostics of individual class books (not new variants; nothing here is used for selection):
per-instrument P&L and cost contributions, average risk-weighted positions, and a 'static average position'
comparison (the book's own in-sample average weights held constant) to see whether carry timing adds anything."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import carry as K  # noqa: E402

E = K.E
pd.set_option("display.width", 250)


def sr(x):
    x = x.dropna()
    return x.mean() / x.std() * math.sqrt(252)


def main() -> None:
    ohlc = E.load_ohlc(K.TICK, "FWD")
    rf = E.load_rf("FWD").reindex(ohlc["close"].index).ffill().fillna(0.0)
    cal = ohlc["close"].index
    ex = ohlc["close"].pct_change(fill_method=None).sub(rf, axis=0)
    vol = np.sqrt(ex.pow(2).ewm(com=K.EWMA_COM, min_periods=60).mean() * 252)
    counts = ex.notna().cumsum()
    active = (ohlc["volume"].fillna(0.0) > 0).astype(float).rolling(K.ACTIVE_WINDOW, min_periods=1).max().astype(bool)
    elig = (counts >= K.MIN_HISTORY) & np.isfinite(vol) & (vol > 0) & active
    out = []
    for sname in ("C1", "C12"):
        sig = pd.read_parquet(HERE / f"signal_{sname}.parquet")
        books, _ = K.build_books(sig, ex, vol, elig, K.decision_dates(cal, "M"))
        for book in ("rates", "comm"):
            tk = [f"F_{r}" for r in K.CLASSES[book]]
            w = books[("XS", book)][tk]
            sub = {k: v[tk] for k, v in ohlc.items()}
            net, gross, turn, held, cost = E.simulate(w, sub, rf, exec="next_close", cost_bps=K.COST_BPS)
            r_cc = ohlc["close"][tk].ffill(limit=5).pct_change(fill_method=None).fillna(0.0).sub(rf, axis=0)
            pnl = held * r_cc
            sl = slice(pd.Timestamp("2011-09-02"), K.IS_END)
            # per-instrument cost (same formula as engine, roll trades included)
            cb = pd.Series(K.COST_BPS)[tk] / 1e4
            prev = w.shift(3).fillna(0.0)
            port_prev = (prev * r_cc.shift(1).fillna(0.0)).sum(axis=1)
            drifted = prev.mul(1 + r_cc.shift(1).fillna(0.0)).div((1 + port_prev).replace(0, np.nan), axis=0).fillna(0.0)
            trade = (held - drifted).abs() + 2.0 * held.abs() * ohlc["roll"][tk].fillna(0.0)
            ci = trade * cb
            risk_w = (held * vol[tk]).loc[sl]          # position x instrument vol = risk units
            rows = pd.DataFrame({
                "pnl_ann_pct": pnl.loc[sl].mean() * 252 * 100,
                "cost_ann_pct": ci.loc[sl].mean() * 252 * 100,
                "mean_notional": held.loc[sl].mean(),
                "mean_abs_notional": held.abs().loc[sl].mean(),
                "mean_risk_w": risk_w.mean(),
                "share_long": (held.loc[sl] > 0).mean(),
                "turnover_yr": trade.loc[sl].sum() / ((sl.stop - sl.start).days / 365.25),
            })
            print(f"\nXS {book} {sname} monthly, in-sample 2011-09..2024-10")
            print(rows.round(3).to_string())
            # static average position: the in-sample mean risk weights held constant (a look-ahead benchmark,
            # used only to ask whether the carry timing adds value over the average tilt)
            mean_rw = risk_w.mean()
            w_static = (pd.DataFrame(np.tile(mean_rw.values, (len(cal), 1)), index=cal, columns=tk)
                        / vol[tk].shift(0)).where(elig[tk], 0.0)
            # rescale static to the same realised IS vol as the dynamic book for comparability
            n2, g2, *_ = E.simulate(w_static.fillna(0.0), sub, rf, exec="next_close", cost_bps=K.COST_BPS)
            dyn = (net - rf).loc[sl]
            sta = (n2 - rf).loc[sl]
            print(f"dynamic SR {sr(dyn):.2f}  static-average-tilt SR {sr(sta):.2f}  corr {dyn.corr(sta):.2f}")
            yr = (1 + dyn).groupby(dyn.index.year).prod() - 1
            print("calendar-year excess %:", (yr * 100).round(1).to_dict())
            out.append(rows.assign(book=book, signal=sname))
    pd.concat(out).to_csv(HERE / "xs_book_decomposition.csv")


if __name__ == "__main__":
    main()
