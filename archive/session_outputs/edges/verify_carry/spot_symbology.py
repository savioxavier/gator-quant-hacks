# Free symbology endpoint spot check of the analyst's cached id->raw_symbol intervals.
import sys, json, random
import pandas as pd
sys.path.insert(0, "<solo-repo>/data")
import download_databento as D
import databento as db
st = json.load(open("<scratch>/edges/carry/symbology_cache.json"))
rows = []
for key, res in st.items():
    for iid, ivs in res.items():
        for iv in ivs:
            rows.append((key.split(":")[0], iid, iv["d0"], iv["d1"], iv["s"]))
df = pd.DataFrame(rows, columns=["year", "iid", "d0", "d1", "s"])
random.seed(11)
samp = df.sample(40, random_state=11)
c = db.Historical(D._key())
bad = 0
for y, g in samp.groupby("year"):
    y = int(y)
    res = c.symbology.resolve(dataset="GLBX.MDP3", symbols=list(g.iid), stype_in="instrument_id", stype_out="raw_symbol",
                              start_date=f"{y}-01-01" if y > 2010 else "2010-06-06", end_date=min(f"{y+1}-01-01", "2026-10-03"))["result"]
    for _, r in g.iterrows():
        got = {iv["s"] for iv in res.get(r.iid, [])}
        ok = r.s in got
        bad += (not ok)
        print(y, r.iid, r.s, sorted(got), "OK" if ok else "MISMATCH")
print("mismatches", bad, "of", len(samp))
