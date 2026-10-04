"""FREE Databento cost queries (metadata.get_cost / get_record_count) for FOMC press-conference windows.
No data is requested. Run from <solo-repo> with PYTHONIOENCODING=utf-8."""
import sys, os, time, json, csv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0, os.getcwd())
from data import download_databento as D
import databento as db

NY = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dates = [l.strip() for l in open(os.path.join(HERE, "presser_dates.txt")) if l.strip()]
c = db.Historical(D._key())

def window(d, mode):
    y, m, dd = int(d[:4]), int(d[4:6]), int(d[6:])
    def t(h, mi, day_shift=0):
        return datetime(y, m, dd, h, mi, tzinfo=NY) + timedelta(days=day_shift)
    if mode == "task":                      # 13:30-16:30 ET on every presser day (task definition)
        if d == "20200303": return t(10, 30), t(13, 30)   # unscheduled: statement 10:00, presser ~11:00
        if d == "20200315": return t(17, 30), t(20, 30)   # Sunday evening press call, Globex reopened 18:00
        return t(13, 30), t(16, 30)
    if mode == "era":                       # statement -30 min to presser start +2 h
        if d <= "20121231": return t(12, 0), t(16, 15)    # 2011-2012: statement ~12:30, presser 14:15
        return window(d, "task")
    raise ValueError(mode)

def cost(schema, symbols, s, e, stype="continuous", dataset="GLBX.MDP3"):
    for attempt in range(4):
        try:
            usd = c.metadata.get_cost(dataset=dataset, schema=schema, stype_in=stype, symbols=symbols,
                                      start=s.isoformat(), end=e.isoformat())
            n = c.metadata.get_record_count(dataset=dataset, schema=schema, stype_in=stype, symbols=symbols,
                                            start=s.isoformat(), end=e.isoformat())
            return float(usd), int(n)
        except Exception as ex:
            msg = str(ex)
            if attempt == 3: return None, msg[:200]
            time.sleep(2 + 3 * attempt)

if __name__ == "__main__":
    mode = sys.argv[1]
    out = os.path.join(HERE, f"cost_{mode}.csv")
    rows = []
    if mode in ("task", "era"):
        six = ["ES.v.0", "ZN.v.0", "ZT.v.0", "ZF.v.0", "6E.v.0"]
        for d in dates:
            s, e = window(d, mode)
            for schema in ("ohlcv-1s", "ohlcv-1m"):
                usd, n = cost(schema, six, s, e)
                usd2, n2 = cost(schema, ["SR3.v.0"], s, e) if d >= "20180507" else (0.0, 0)
                rows.append(dict(date=d, schema=schema, start=s.isoformat(), end=e.isoformat(), usd_5fronts=usd, rec_5fronts=n, usd_sr3=usd2, rec_sr3=n2))
                time.sleep(0.25)
            print(d, rows[-2]["usd_5fronts"], rows[-2]["rec_5fronts"], rows[-1]["usd_5fronts"], rows[-1]["rec_5fronts"], flush=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("wrote", out)
