"""Independent driver: runs gqh_flow_clock through the harness in-process, logs every order and the
book per bar, and optionally perturbs prices / side data after a cut date (lookahead test)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import backtrader as bt
import numpy as np
import pandas as pd

ROOT = Path("<solo-repo>")
sys.path.insert(0, str(ROOT))
from validation.starter_kit import run_in_starter as H  # noqa: E402
from src import engine as E  # noqa: E402
from src.strategies import ifc_treasury as IT  # noqa: E402


class Log(bt.Analyzer):
    def start(self):
        self.orders, self.book = [], []

    def notify_order(self, o):
        if o.status in (o.Completed, o.Margin, o.Rejected, o.Canceled, o.Partial):
            self.orders.append(dict(ref=o.ref, sym=o.data._name, created=bt.num2date(o.created.dt).date(),
                                    exec_dt=bt.num2date(o.data.datetime[0]).date(), status=o.getstatusname(),
                                    exectype=o.exectype, size=o.created.size, ex_size=o.executed.size,
                                    ex_price=o.executed.price, comm=o.executed.comm,
                                    bar_open=o.data.open[0], bar_close=o.data.close[0],
                                    bar_high=o.data.high[0], bar_low=o.data.low[0],
                                    coc=bool(o.info.get("coc", True))))

    def next(self):
        s = self.strategy
        row = {"date": s.datas[0].datetime.date(0), "value": s.broker.getvalue(), "cash": s.broker.getcash()}
        for d in s.datas:
            row["pos_" + d._name] = s.getposition(d).size
            row["c_" + d._name] = d.close[0]
            row["o_" + d._name] = d.open[0]
        self.book.append(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--costs", default="project")
    ap.add_argument("--params", default="fill=native")
    ap.add_argument("--cut", default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--perturb-side", action="store_true")
    ap.add_argument("--end", default=None)
    ap.add_argument("--no-price", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    kit = H.load_kit(Path(os.environ["GQH_STARTER_KIT"]))
    sys.path.insert(0, str(H.OUR_STRATEGIES))
    from webull_bt.visualize import RecorderAnalyzer
    argv = ["--strategy", "gqh_flow_clock", "--costs", a.costs,
            "--params", f"{a.params},dump={out.as_posix()}_dump.csv"]
    if a.end:
        argv += ["--end", a.end]
    args = H.parse_args(argv)
    os.environ["WEBULL_VISUALIZE"] = "false"
    su = H.prepare(kit, args)
    if a.cut:
        cut = pd.Timestamp(a.cut)
        rng = np.random.default_rng(a.seed)
        idx = su.ohlc["close"].index
        after = idx > cut
        n = int(after.sum())
        for t in ([] if a.no_price else su.symbols):
            f = np.exp(np.cumsum(rng.normal(0, 0.02, n)))        # random walk on the level after the cut
            g = np.exp(rng.normal(0, 0.01, n))                   # independent open gap noise
            for c in ("open", "high", "low", "close"):
                col = su.ohlc[c][t].copy()
                mult = f * (g if c == "open" else 1.0)
                col.loc[after] = col.loc[after].to_numpy() * mult
                su.ohlc[c][t] = col
            hi = np.maximum.reduce([su.ohlc[c][t] for c in ("open", "high", "low", "close")])
            lo = np.minimum.reduce([su.ohlc[c][t] for c in ("open", "high", "low", "close")])
            su.ohlc["high"][t], su.ohlc["low"][t] = hi, lo
        if a.perturb_side:
            orig_rf, orig_auc = E.load_rf, IT.load_nominal_auctions

            def rf2(period="IS"):
                r = orig_rf(period).copy()
                m = r.index > cut
                r[m] = r[m] * rng.uniform(0, 3, int(m.sum()))
                return r

            def auc2(period="IS", return_report=False):
                res = orig_auc(period, return_report)
                df = res[0] if return_report else res
                df = df.copy()
                m = df["announcemt_date"] > cut
                df.loc[m, "dv01"] = df.loc[m, "dv01"] * rng.uniform(0, 5, int(m.sum()))
                # a fake large auction announced the day after the cut, issued in the cut's month
                fake = df.iloc[[0]].copy()
                fake["announcemt_date"] = cut + pd.Timedelta(days=1)
                fake["issue_date"] = cut
                fake["dv01"] = 1e7
                df = pd.concat([df, fake], ignore_index=True)
                return (df, res[1]) if return_report else df
            E.load_rf = rf2
            IT.load_nominal_auctions = auc2
    log_cls = Log
    # attach our logger through run_backtest: add analyzer by wrapping Cerebro.run
    orig_run = bt.Cerebro.run

    def run(self, *x, **k):
        self.addanalyzer(log_cls, _name="vlog")
        return orig_run(self, *x, **k)
    bt.Cerebro.run = run
    cerebro, strat, metrics, side_bps = H.run_backtest(kit, su, RecorderAnalyzer)
    lg = strat.analyzers.vlog
    pd.DataFrame(lg.orders).to_csv(f"{out}_orders.csv", index=False)
    pd.DataFrame(lg.book).to_csv(f"{out}_book.csv", index=False)
    daily = H.daily_frame(strat, su.extra)
    daily.rename_axis("date").to_csv(f"{out}_daily.csv")
    meta = {"side_bps": side_bps, "symbols": su.symbols, "extra": su.extra,
            "extra_totals": strat.analyzers.extra.totals if su.extra else None,
            "desync": int(strat.desync), "refused": int(strat.orders_refused)}
    Path(f"{out}_meta.json").write_text(json.dumps(meta, default=str, indent=1))


if __name__ == "__main__":
    main()
