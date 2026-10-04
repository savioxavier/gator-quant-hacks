"""Map every (date, instrument_id) row of the raw Databento daily bars to its raw CME symbol and delivery month.

Uses only the free symbology.resolve endpoint (no market-data requests). Instrument ids are recycled by CME
across products and over time, so the mapping is date-aware: each raw row is matched to the symbology interval
[d0, d1) that contains its date. Output: contracts.parquet with one row per raw bar:
  date, root, rank, instrument_id, close, volume, raw_symbol, deliv_year, deliv_month, month_index
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<solo-repo>")
sys.path.insert(0, str(REPO / "data"))
import download_databento as D  # noqa: E402

OUT = Path(__file__).resolve().parent
RAW = Path("<home>/.cache/gqh/databento_raw/glbx_ohlcv1d_v01.parquet")
MONTHS = "FGHJKMNQUVXZ"


def main() -> None:
    import databento as db

    r = pd.read_parquet(RAW)
    r["date"] = r["ts_event"].dt.tz_convert(None).dt.normalize()
    r["root"] = r["symbol"].str.split(".").str[0]
    r["rank"] = r["symbol"].str.split(".").str[2].astype(int)
    r["year"] = r["date"].dt.year
    cache = OUT / "symbology_cache.json"
    store = json.loads(cache.read_text()) if cache.exists() else {}
    client = db.Historical(D._key())
    for y in sorted(r["year"].unique()):
        ids = sorted(r.loc[r["year"] == y, "instrument_id"].unique())
        for k in range(0, len(ids), 200):
            key = f"{y}:{k}"
            if key in store:
                continue
            chunk = [str(i) for i in ids[k:k + 200]]
            for attempt in range(5):
                try:
                    res = client.symbology.resolve(dataset="GLBX.MDP3", symbols=chunk, stype_in="instrument_id",
                                                   stype_out="raw_symbol", start_date=("2010-06-06" if y == 2010 else f"{y}-01-01"),
                                                   end_date=min(f"{y + 1}-01-01", "2026-10-03"))
                    break
                except Exception as exc:
                    print("retry", y, k, str(exc)[:80])
                    time.sleep(5 * (attempt + 1))
            else:
                raise RuntimeError("symbology failed")
            store[key] = res["result"]
            cache.write_text(json.dumps(store))
            print(y, k, len(chunk), "not_found", len(res.get("not_found", [])))
    # flatten intervals
    rows = []
    for key, result in store.items():
        for iid, ivs in result.items():
            for iv in ivs:
                rows.append((int(iid), pd.Timestamp(iv["d0"]), pd.Timestamp(iv["d1"]), iv["s"]))
    iv = pd.DataFrame(rows, columns=["instrument_id", "d0", "d1", "raw_symbol"]).drop_duplicates()
    # date-aware join: for each raw bar take the interval with d0 <= date < d1
    m = r.merge(iv, on="instrument_id", how="left")
    m = m[(m["date"] >= m["d0"]) & (m["date"] < m["d1"])]
    m = m.drop_duplicates(subset=["date", "symbol"], keep="first")
    # the raw symbol must belong to the same root (e.g. 'CLG4' for CL): root + month code + 1-2 digit year
    pat = m["raw_symbol"].str.extract(r"^(?P<r>[0-9A-Z]+?)(?P<m>[FGHJKMNQUVXZ])(?P<y>\d{1,2})$")
    m = pd.concat([m, pat], axis=1)
    ok = m["r"] == m["root"]
    bad = m[~ok]
    print("rows", len(r), "matched", len(m), "root mismatch", len(bad))
    if len(bad):
        print(bad[["date", "symbol", "instrument_id", "raw_symbol"]].head(20).to_string())
    m = m[ok].copy()
    yd = m["y"].astype(int)
    base = m["date"].dt.year
    # a 1-digit year: the delivery year is the first year >= (date year - 1) ending in that digit
    one = m["y"].str.len() == 1
    dec = (base - 1) - ((base - 1) % 10)
    yr1 = dec + yd
    yr1 = np.where(yr1 < base - 1, yr1 + 10, yr1)
    yr2 = 2000 + yd
    m["deliv_year"] = np.where(one, yr1, yr2).astype(int)
    m["deliv_month"] = m["m"].map(lambda c: MONTHS.index(c) + 1).astype(int)
    m["month_index"] = m["deliv_year"] * 12 + m["deliv_month"] - 1
    out = m[["date", "root", "rank", "instrument_id", "close", "volume", "raw_symbol", "deliv_year",
             "deliv_month", "month_index"]].sort_values(["root", "date", "rank"])
    out.to_parquet(OUT / "contracts.parquet", index=False)
    miss = len(r) - len(out)
    print("written", len(out), "unmatched raw rows", miss)
    print(r.merge(out[["date", "root", "rank"]], on=["date", "root", "rank"], how="left", indicator=True)
          .query("_merge=='left_only'").groupby("root").size())


if __name__ == "__main__":
    main()
