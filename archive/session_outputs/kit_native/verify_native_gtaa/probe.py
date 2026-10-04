"""Independent probes of strategies/gqh_gtaa.py: lookahead perturbation, execution timing, costs, refusals."""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from pathlib import Path

import backtrader as bt
import numpy as np
import pandas as pd

ROOT = Path("<solo-repo>")
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from validation.starter_kit import run_in_starter as R  # noqa: E402

OUT = Path(__file__).resolve().parent
kit = R.load_kit(Path(os.environ["GQH_STARTER_KIT"]))
sys.path.insert(0, str(R.OUR_STRATEGIES))
from webull_bt.visualize import RecorderAnalyzer  # noqa: E402


def make_logged(base):
    class Logged(base):
        def __init__(self):
            super().__init__()
            self.olog, self.flog, self.plog = [], [], []

        def order_shares(self, data, delta, exec):
            self.olog.append((self.datas[0].datetime.date(0), data._name, int(delta)))
            return super().order_shares(data, delta, exec)

        def notify_order(self, order):
            super().notify_order(order)
            if order.status == order.Completed:
                self.flog.append((bt.num2date(order.created.dt).date(), bt.num2date(order.executed.dt).date(),
                                  order.data._name, order.executed.size, order.executed.price,
                                  order.executed.comm, order.exectype))

        def next(self):
            super().next()
            self.plog.append((self.datas[0].datetime.date(0),
                              tuple(self.getposition(d).size for d in self.datas)))
    Logged.__name__ = base.__name__
    return Logged


def run(argv, perturb=None):
    args = R.parse_args(argv)
    su = R.prepare(kit, args)
    if perturb is not None:
        su.ohlc = perturb(su.ohlc)
    su.strategy_cls = make_logged(su.strategy_cls)
    with contextlib.redirect_stdout(io.StringIO()):
        cerebro, strat, metrics, _ = R.run_backtest(kit, su, RecorderAnalyzer)
    return su, cerebro, strat


def perturber(cut, seed):
    def f(ohlc):
        out = {k: v.copy() for k, v in ohlc.items()}
        rng = np.random.default_rng(seed)
        after = out["close"].index > cut
        for col in ("open", "high", "low", "close"):
            px = out[col]
            noise = np.exp(np.cumsum(rng.normal(0, 0.02, size=(after.sum(), px.shape[1])), axis=0))
            base = px.loc[~after].ffill().iloc[-1].to_numpy()
            px.loc[after] = base * noise
        # keep high/low consistent with open/close
        hi = np.maximum.reduce([out[c].to_numpy() for c in ("open", "high", "low", "close")])
        lo = np.minimum.reduce([out[c].to_numpy() for c in ("open", "high", "low", "close")])
        out["high"].loc[after] = hi[after]
        out["low"].loc[after] = lo[after]
        return out
    return f


def lookahead(argv, cuts):
    _, _, base = run(argv)
    res = []
    for i, c in enumerate(cuts):
        cut = pd.Timestamp(c)
        _, _, p = run(argv, perturber(cut, 500 + i))
        bo = [x for x in base.olog if pd.Timestamp(x[0]) <= cut]
        po = [x for x in p.olog if pd.Timestamp(x[0]) <= cut]
        bp = [x for x in base.plog if pd.Timestamp(x[0]) <= cut]
        pp = [x for x in p.plog if pd.Timestamp(x[0]) <= cut]
        bd = [x for x in base.decision_log if pd.Timestamp(x[0]) <= cut]
        pd_ = [x for x in p.decision_log if pd.Timestamp(x[0]) <= cut]
        later_o = sum(a != b for a, b in zip([x for x in base.olog if pd.Timestamp(x[0]) > cut],
                                             [x for x in p.olog if pd.Timestamp(x[0]) > cut]))
        later_d = sum(a[1] != b[1] for a, b in zip([x for x in base.decision_log if pd.Timestamp(x[0]) > cut],
                                                   [x for x in p.decision_log if pd.Timestamp(x[0]) > cut]))
        res.append(dict(cut=c, orders_before=len(bo), orders_same=bo == po, positions_same=bp == pp,
                        decisions_before=len(bd), decisions_same=bd == pd_,
                        orders_differing_after=later_o, decisions_differing_after=later_d))
        print(res[-1], flush=True)
    return res


def timing_and_costs(argv, costs):
    su, cerebro, s = run(argv)
    o = su.ohlc
    cal = list(o["close"].index)
    nxt = {cal[i].date(): cal[i + 1].date() for i in range(len(cal) - 1)}
    bad_day = bad_px = bad_comm = 0
    max_px_err = max_comm_err = 0.0
    slip_bp = []
    for created, ex, name, size, price, comm, et in s.flog:
        if et != bt.Order.Market:
            bad_day += 1
        if nxt.get(created) != ex:
            bad_day += 1
        op = float(o["open"][name].reindex([pd.Timestamp(ex)]).fillna(o["close"][name].ffill().bfill()
                                                                      .loc[pd.Timestamp(ex)]).iloc[0])
        if costs == "project":
            err = abs(price - op) / op
            max_px_err = max(max_px_err, err)
            bad_px += err > 1e-12
            rate = R.project_cost_bps(name) / 1e4
        else:
            slip_bp.append(np.sign(size) * (price / op - 1) * 1e4)
            rate = R.GUIDE_COMMISSION
        ce = abs(comm - abs(size) * price * rate) / max(abs(size) * price * rate, 1e-9)
        max_comm_err = max(max_comm_err, ce)
        bad_comm += ce > 1e-9
    out = dict(fills=len(s.flog), orders=len(s.olog), wrong_exec_day_or_type=bad_day, open_price_mismatch=bad_px,
               max_open_price_rel_err=max_px_err, commission_mismatch=bad_comm, max_comm_rel_err=max_comm_err,
               refused=s.orders_refused)
    if slip_bp:
        sb = np.array(slip_bp)
        out.update(mean_slip_bp=float(sb.mean()), share_full_5bp=float((np.abs(sb - 5) < 1e-6).mean()),
                   min_slip_bp=float(sb.min()))
    # unfilled / unexecuted orders other than the final bar's
    last = cal[-1].date()
    filled_created = {}
    for created, *_ in s.flog:
        filled_created[created] = filled_created.get(created, 0) + 1
    made = {}
    for d, *_ in s.olog:
        made[d] = made.get(d, 0) + 1
    out["days_with_unfilled_orders_excl_last"] = sum(1 for d, n in made.items() if d != last and
                                                     filled_created.get(d, 0) != n)
    return out


if __name__ == "__main__":
    which = sys.argv[1]
    base = ["--strategy", "gqh_gtaa"]
    results = {}
    if which == "lookahead":
        cuts = ["2006-09-29", "2008-10-15", "2012-10-31", "2016-06-23", "2020-03-31", "2024-10-02", "2025-06-30"]
        results["S3_project_margin"] = lookahead(base + ["--costs", "project", "--margin"], cuts)
        results["BH5_guide_cash100k"] = lookahead(base + ["--costs", "guide", "--cash", "100000",
                                                         "--params", "buy_and_hold=true"], cuts[:4])
        results["S3_guide_cash100k"] = lookahead(base + ["--costs", "guide", "--cash", "100000"], cuts[2:])
    else:
        for tag, extra, costs in [("S3_project_margin", ["--costs", "project", "--margin"], "project"),
                                  ("S3_guide_cash100k", ["--costs", "guide", "--cash", "100000"], "guide"),
                                  ("BH5_project_cash100k", ["--costs", "project", "--cash", "100000",
                                                            "--params", "buy_and_hold=true"], "project")]:
            results[tag] = timing_and_costs(base + extra, costs)
            print(tag, results[tag], flush=True)
    (OUT / f"probe_{which}.json").write_text(json.dumps(results, indent=1, default=str))
