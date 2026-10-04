"""FREE cost queries for extra instruments/schemas on 12 sample presser days (13:30-16:30 ET windows), to extrapolate.
No data requested."""
import sys, os, time, csv
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cost_query as Q
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sample = ["20110427", "20120913", "20131218", "20150917", "20161214", "20180613", "20190731", "20200916",
          "20220615", "20231101", "20250917", "20260916"]
jobs = [
    ("GLBX.MDP3", "bbo-1s",  ["ES.v.0", "ZN.v.0", "ZT.v.0"], "continuous", None),
    ("GLBX.MDP3", "tbbo",    ["ES.v.0", "ZN.v.0", "ZT.v.0"], "continuous", None),
    ("GLBX.MDP3", "mbp-1",   ["ES.v.0", "ZN.v.0", "ZT.v.0"], "continuous", None),
    ("GLBX.MDP3", "mbp-10",  ["ES.v.0"], "continuous", None),
    ("GLBX.MDP3", "ohlcv-1s", ["NQ.v.0", "6J.v.0", "GC.v.0"], "continuous", None),
    ("GLBX.MDP3", "ohlcv-1s", ["ZQ.v.0", "ZQ.v.1", "ZQ.v.2", "ZQ.v.3"], "continuous", None),
    ("GLBX.MDP3", "ohlcv-1s", ["GE.v.0", "GE.v.1", "GE.v.2", "GE.v.3", "GE.v.4", "GE.v.5", "GE.v.6", "GE.v.7"], "continuous", ("20100101", "20230331")),
    ("GLBX.MDP3", "ohlcv-1s", ["SR3.v.1", "SR3.v.2", "SR3.v.3", "SR3.v.4", "SR3.v.5", "SR3.v.6", "SR3.v.7"], "continuous", ("20180507", "20991231")),
    ("XCBF.PITCH", "ohlcv-1s", ["VX.v.0", "VX.v.1"], "continuous", ("20181104", "20991231")),
    ("XCBF.PITCH", "ohlcv-1m", ["VX.v.0", "VX.v.1"], "continuous", ("20181104", "20991231")),
]
rows = []
for d in sample:
    s, e = Q.window(d, "task")
    for ds, schema, syms, st, rng in jobs:
        if rng and not (rng[0] <= d <= rng[1]):
            continue
        usd, n = Q.cost(schema, syms, s, e, stype=st, dataset=ds)
        rows.append(dict(date=d, dataset=ds, schema=schema, symbols=" ".join(syms), usd=usd, records=n))
        time.sleep(0.3)
    print(d, "done", flush=True)
with open(os.path.join(HERE, "cost_extras.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("wrote")
