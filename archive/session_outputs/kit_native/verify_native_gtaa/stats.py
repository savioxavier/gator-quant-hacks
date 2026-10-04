"""Independent agreement numbers for the native GTAA runs against our engine."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<solo-repo>")
sys.path.insert(0, str(ROOT))
from src import calendar_utils as CU  # noqa: E402
from src import config as C  # noqa: E402
from src import engine as E  # noqa: E402
from src import forward2 as F2  # noqa: E402

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
WIN = {"IS": ("2005-11-01", "2024-10-02"), "OOS": ("2024-10-03", "2026-10-02")}

# ---- month-end calendar
cal = E.trading_calendar("FWD")
ohlc = E.load_ohlc(F2.S3_TICKERS, "FWD")
from validation.starter_kit.strategies import gqh_gtaa as G  # noqa: E402
strat_me = sorted(G.month_ends())
real_me = [t.date() for t in F2._month_ends(ohlc["close"].index)]
plan = CU.planned_calendar(cal)
plan_me = [t.date() for t in F2._month_ends(plan)]
# naive calendar-only rule: last weekday-business-day of month that is in cal
cal_check = {"strategy_eq_engine_realized": strat_me == real_me, "n": len(strat_me),
             "strategy_eq_planned": strat_me == plan_me,
             "planned_minus_strategy": [str(x) for x in sorted(set(plan_me) - set(strat_me))],
             "feed_index_eq_calendar": bool(ohlc["close"].index.equals(cal))}
print("calendar", cal_check)

rf = E.load_rf("FWD").reindex(cal).ffill().fillna(0.0)
ref = {("S3", "project"): F2.returns("S3", "FWD"), ("BH5", "project"): F2.returns("BH5", "FWD")}
for name, bh in (("S3", False), ("BH5", True)):
    w = F2.s3_decisions("FWD", buy_and_hold=bh)
    ref[name, "guide"] = E.simulate(w, ohlc, rf, exec="next_open", cost_bps={t: 10.0 for t in F2.S3_TICKERS})[0]
    ref[name, "none"] = E.simulate(w, ohlc, rf, exec="next_open", cost_bps={t: 0.0 for t in F2.S3_TICKERS})[0]
    ref[name, "held"] = E.simulate(w, ohlc, rf, exec="next_open")[3].sum(axis=1)


def kit_sh(r):
    return float(r.mean() / r.std(ddof=0) * np.sqrt(252))


def our_sh(x):
    return float(x.mean() / x.std(ddof=1) * np.sqrt(252))


def mdd(r):
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


rows = []
for f in sorted(RUNS.glob("*.csv")):
    name, costs = f.stem.split("_")[:2]
    d = pd.read_csv(f, index_col=0, parse_dates=True)
    js = json.loads(f.with_suffix(".json").read_text())
    for wname, (lo, hi) in WIN.items():
        x = d.loc[lo:hi]
        r = x["ret"]
        rfx = rf.reindex(x.index)
        held = ref[name, "held"].reindex(x.index)
        ex_h = r - x["net_weight"] * rfx                         # harness net weight
        ex_e = r - held * rfx * (1 - 0.0)                        # engine's held weight instead
        for refc in ("project", costs) if costs != "project" else ("project",):
            e = ref[name, refc].reindex(x.index)
            ee = e - rfx
            dd = ex_h - ee
            rows.append(dict(run=f.stem, window=wname, ref=refc,
                             kit=kit_sh(r), ours=our_sh(ex_h), ours_engine_netw=our_sh(ex_e),
                             harness_kit=js["windows"]["in_sample" if wname == "IS" else "out_of_sample"]["kit_sharpe_rf0"],
                             harness_ours=js["windows"]["in_sample" if wname == "IS" else "out_of_sample"]["our_sharpe_excess"],
                             ann=float((1 + r).prod() ** (252 / len(r)) - 1), mdd=mdd(r),
                             eng_ours=our_sh(ee), eng_kit=kit_sh(e),
                             corr_ex=float(ex_h.corr(ee)), corr_total=float(r.corr(e)),
                             mad_bp=float(dd.abs().mean() * 1e4), max_bp=float(dd.abs().max() * 1e4),
                             netw_minus_held_mean=float((x["net_weight"] - held).mean()),
                             refused=js["orders"]["refused"], orders=js["orders"]["total"]))
df = pd.DataFrame(rows)
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
print(df.round(6).to_string(index=False))
df.to_csv(HERE / "stats.csv", index=False)
(HERE / "calendar_check.json").write_text(json.dumps(cal_check, indent=1))
