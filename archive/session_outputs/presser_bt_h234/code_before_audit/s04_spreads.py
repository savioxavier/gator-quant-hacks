"""Step 4: measured bbo-1s half-spreads by instrument and minute (addendum 1.3 quote rule; section 7 summary)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lib import OUT, QSYMS, TZ, Quotes, check_addendum, load_events, tick_pts

check_addendum()
R = OUT / "results"
ev = load_events()
ev = ev[(ev.scheduled == 1) & (ev.market_window_covers_event == 1)]
q = Quotes()
P = OUT / "positions"
m = pd.read_csv(P / "meetings_positions.csv", dtype={"date": str})
m["tau_end_upper"] = pd.to_datetime(m.tau_end_upper, utc=True, format="ISO8601").dt.tz_convert(TZ)
a = pd.read_csv(P / "answers_positions.csv", dtype={"date": str})
a["t0"] = pd.to_datetime(a.t0, utc=True, format="ISO8601").dt.tz_convert(TZ)


def era(sym, date):
    if sym == "ZT":
        return "2016-2018 (1/128)" if date <= "2018-12-31" else "2019-2026 (1/256)"
    return "2016-2019" if date < "2020-01-01" else "2020-2026"


frames = []
for r in ev.itertuples():
    st = pd.Timestamp(f"{r.date} 13:30:00", tz=TZ)
    en = pd.Timestamp(f"{r.date} 16:30:00", tz=TZ)
    for s in QSYMS:
        x = q.series(r.date, s, st, en)
        tk = tick_pts(s, r.date)
        x["hs_ticks"] = (x.ask - x.bid) / 2 / tk
        x["sym"] = s
        x["date"] = r.date
        x["era"] = era(s, r.date)
        x["clock_min"] = ((x.index - st).total_seconds() // 60).astype(int)  # 0 = 13:30
        x["presser_min"] = np.floor((x.index - r.start_est_ts).total_seconds() / 60).astype(int)
        frames.append(x[["sym", "date", "era", "clock_min", "presser_min", "hs_ticks", "stale"]])
sec = pd.concat(frames)


def agg(g):
    v = g.hs_ticks.dropna()
    return pd.Series(dict(n_sec=len(v), n_days=g.date.nunique(), median=v.median(), p90=v.quantile(0.9),
                          p99=v.quantile(0.99), max=v.max(), mean=v.mean(), stale_gt60_share=(g.stale > 60).mean()))


by_pm = sec[(sec.presser_min >= -60) & (sec.presser_min <= 90)].groupby(["sym", "era", "presser_min"]).apply(agg)
by_pm.reset_index().to_csv(R / "spreads_by_minute_of_presser.csv", index=False)
by_cm = sec.groupby(["sym", "era", "clock_min"]).apply(agg).reset_index()
by_cm["clock_et"] = (pd.Timestamp("2000-01-01 13:30") + pd.to_timedelta(by_cm.clock_min, unit="m")).dt.strftime("%H:%M")
by_cm.to_csv(R / "spreads_by_clock_minute.csv", index=False)

# phase table: minute-of-presser buckets
bins = [-61, -31, -11, -1, 4, 14, 29, 44, 59, 91]
labels = ["-60..-31 (pre-statement)", "-30..-11 (statement window)", "-10..-1", "0..4 (opening)", "5..14",
          "15..29", "30..44", "45..59", "60..90"]
s2 = sec[(sec.presser_min >= -60) & (sec.presser_min <= 90)].copy()
s2["bucket"] = pd.cut(s2.presser_min, bins=bins, labels=labels)
s2.groupby(["sym", "era", "bucket"], observed=True).apply(agg).reset_index().to_csv(
    R / "spreads_by_presser_phase.csv", index=False)

# section 7 fill-second summary: 14:20:00, each tau_end,upper entry, each answer entry, 16:00 exit
pts = []
sch = m[(m.scheduled == 1) & (m.market_window_covers_event == 1)]
for r in sch.itertuples():
    for s in QSYMS:
        for lab, t in [("14:20:00", pd.Timestamp(f"{r.date} 14:20:00", tz=TZ)),
                       ("tau_end_upper (next second)", r.tau_end_upper.ceil("s")),
                       ("16:00:00", pd.Timestamp(f"{r.date} 16:00:00", tz=TZ))]:
            b, k, st = q.at(r.date, s, t)
            pts.append(dict(point=lab, sym=s, date=r.date, era=era(s, r.date), hs_ticks=(k - b) / 2 / tick_pts(s, r.date),
                            stale=st))
el = a[a.eligible_base.astype(bool)]
for r in el.itertuples():
    for s in QSYMS:
        b, k, st = q.at(r.date, s, r.t0)
        pts.append(dict(point="answer entry (t0)", sym=s, date=r.date, era=era(s, r.date),
                        hs_ticks=(k - b) / 2 / tick_pts(s, r.date), stale=st))
pts = pd.DataFrame(pts)
pts.groupby(["point", "sym", "era"]).apply(
    lambda g: pd.Series(dict(n=g.hs_ticks.notna().sum(), median=g.hs_ticks.median(), p90=g.hs_ticks.quantile(0.9),
                             mean=g.hs_ticks.mean(), stale_gt60=(g.stale > 60).sum(),
                             stale_median_s=g.stale.median()))).reset_index().to_csv(
    R / "spreads_at_fill_points.csv", index=False)
print(pd.read_csv(R / "spreads_by_presser_phase.csv").round(3).to_string())
print(pd.read_csv(R / "spreads_at_fill_points.csv").round(3).to_string())
