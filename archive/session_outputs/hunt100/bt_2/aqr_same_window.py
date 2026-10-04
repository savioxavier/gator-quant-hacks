# AQR public factor Sharpe ratios (gross, monthly) on the bt_2 in-sample window (2011-07..2024-09) and the later
# window (2024-10..last month in the file). Reuses the hunt's xlsx loader; data files already in the scratchpad.
import importlib.util, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aqs", os.path.join(HERE, "..", "trend_momentum", "aqr_subperiods.py"))
src = open(spec.origin, encoding="utf-8").read().split("hdr, vme = load(")[0]   # helper functions only
ns = {"__file__": spec.origin}
exec(compile(src, spec.origin, "exec"), ns)
load, stats, serial, slash = ns["load"], ns["stats"], ns["serial"], ns["slash"]
W = {"IS 2011-07..2024-09": (201107, 202409), "LATER 2024-10..end": (202410, 999912)}
out = {}
def rep(tag, data, cols):
    for c in cols:
        for w, (lo, hi) in W.items():
            sub = [(k, v.get(c)) for k, v in data if lo <= k <= hi and v.get(c) is not None]
            st = stats([x for _, x in sub])
            out[f"{tag}|{c}|{w}"] = None if st is None else {"n_months": st[0], "ann_mean": round(st[1], 4),
                "ann_vol": round(st[2], 4), "sharpe": round(st[3], 3), "first": sub[0][0], "last": sub[-1][0]}
hdr, vme = load("vme_factors.xlsx", "VME Factors", lambda r: r[0] == "DATE", serial)
rep("VME", vme, ["MOM^AA", "MOMLS_VME_EQ", "MOMLS_VME_FX", "MOMLS_VME_FI", "MOMLS_VME_COM"])
hdr, cen = load("century.xlsx", "Century of Factor Premia", lambda r: r[0] == "Date", slash)
rep("CENTURY", cen, ["Equity indices Momentum", "Fixed income Momentum", "Currencies Momentum",
                      "Commodities Momentum", "All Macro Momentum"])
hdr, ts = load("tsmom.xlsx", "TSMOM Factors", lambda r: r and len(r) > 1 and r[1] == "TSMOM", serial)
rep("TSMOM", ts, ["TSMOM", "TSMOM^CM", "TSMOM^EQ", "TSMOM^FI", "TSMOM^FX"])
json.dump(out, open(os.path.join(HERE, "aqr_same_window.json"), "w"), indent=1)
for k, v in out.items():
    print(k, v)
