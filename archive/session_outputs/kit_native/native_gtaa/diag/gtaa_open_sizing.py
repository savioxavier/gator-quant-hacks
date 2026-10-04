"""Scratch diagnostic, not a strategy to submit: gqh_gtaa with orders sized at the open they fill at.

The decision is still made at the close of d from data up to that close; the shares are computed from the open of
d+1 (cheat-on-open), the engine's exact-target assumption. Only to attribute the native run's residual to sizing.
"""
from __future__ import annotations

import backtrader as bt

from validation.starter_kit.strategies.gqh_gtaa import FaberGTAA, IS_START, SYMBOLS  # noqa: F401

EXEC = "next_open"
CASH = 1e9


class OpenSized(FaberGTAA):
    def __init__(self):
        super().__init__()
        self.env.p.cheat_on_open = True
        self.broker.set_coo(True)

    def next(self):
        today = self.datas[0].datetime.date(0)
        if today in self.month_ends:
            self.targets = self.decide()
            self.decision_log.append((today, self.targets))

    def next_open(self):
        if len(self) < 2:
            return
        nav = self.broker.getvalue() + sum(self.getposition(d).size * (d.open[0] - d.close[-1]) for d in self.datas)
        deltas = []
        for d in self.datas:
            delta = round(self.targets.get(d._name, 0.0) * self.invested * nav / d.open[0]) - self.getposition(d).size
            if delta:
                deltas.append((d, delta))
        for d, delta in sorted(deltas, key=lambda x: x[1] > 0):
            (self.buy if delta > 0 else self.sell)(data=d, size=abs(delta), exectype=bt.Order.Market)


STRATEGY_CLASS = OpenSized
