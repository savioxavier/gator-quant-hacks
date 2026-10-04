"""Cross-check against the authors' own updated factors (AQR VME file, monthly): (1) Sharpe of the published
non-stock value / momentum factors in our windows; (2) monthly correlation of our class sleeves with them,
which validates the implementation. Context only; no rule is chosen from this."""
import json
import math
import sys
from pathlib import Path

import pandas as pd

SCR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCR))
from xlsx_read import read_xlsx, sheet_rows  # noqa: E402

OUT = Path(__file__).resolve().parent
z, shared, sheets = read_xlsx(str(SCR / "vme_factors.xlsx"))
rows = sheet_rows(z, shared, sheets["VME Factors"])
hi = next(i for i, r in enumerate(rows) if r and r[0] == "DATE")
hdr = rows[hi]
recs = []
for r in rows[hi + 1:]:
    if not r or not r[0] or "/" not in str(r[0]):
        continue
    m, d, y = str(r[0]).split("/")
    rec = {"date": pd.Timestamp(int(y), int(m), 1) + pd.offsets.MonthEnd(0)}
    for j, h in enumerate(hdr):
        if j == 0 or h is None:
            continue
        v = r[j] if j < len(r) else None
        try:
            rec[h] = float(v) if v not in (None, "") else None
        except ValueError:
            rec[h] = None
    recs.append(rec)
vme = pd.DataFrame(recs).set_index("date").astype(float)


def sr(x):
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(12)) if len(x) > 12 else float("nan")


cols = ["VAL^AA", "MOM^AA", "VALLS_VME_COM", "MOMLS_VME_COM", "VALLS_VME_FX", "MOMLS_VME_FX", "VALLS_VME_FI",
        "MOMLS_VME_FI", "VALLS_VME_EQ", "MOMLS_VME_EQ", "VAL", "MOM"]
wins = {"pre_pub 1972-2013-06": ("1972-01", "2013-06"), "post_pub 2013-07..": ("2013-07", "2026-12"),
        "our_IS 2016-01..2024-09": ("2016-01", "2024-09"), "our_LATER 2024-10..": ("2024-10", "2026-12")}
out = {"last_obs": {c: str(vme[c].dropna().index.max().date()) for c in cols}, "sharpe": {}, "corr_val_mom": {}}
for w, (a, b) in wins.items():
    sub = vme.loc[a:b]
    out["sharpe"][w] = {c: sr(sub[c]) for c in cols}
    for k in ("COM", "FX", "FI", "EQ"):
        df = sub[[f"VALLS_VME_{k}", f"MOMLS_VME_{k}"]].dropna()
        out["corr_val_mom"].setdefault(w, {})[k] = float(df.corr().iloc[0, 1]) if len(df) > 12 else None
    df = sub[["VAL^AA", "MOM^AA"]].dropna()
    out["corr_val_mom"][w]["AA"] = float(df.corr().iloc[0, 1]) if len(df) > 12 else None

R = pd.read_pickle(OUT / "results.pkl")
ours = {}
for k in ("COM", "FX", "EQ"):
    for kind in ("VAL", "MOM"):
        s = R["diag"][f"{kind}_{k}"]["gross"].loc["2016-01-05":]
        ours[f"{kind}_{k}"] = (1 + s).resample("ME").prod() - 1
ours["VAL_XS"] = (1 + R["results"]["VAL_XS_VW1"]["gross"].loc["2016-01-05":]).resample("ME").prod() - 1
ours["MOM_XS"] = (1 + R["results"]["MOM_XS"]["gross"].loc["2016-01-05":]).resample("ME").prod() - 1
pairs = {"VAL_COM": "VALLS_VME_COM", "MOM_COM": "MOMLS_VME_COM", "VAL_FX": "VALLS_VME_FX", "MOM_FX": "MOMLS_VME_FX",
         "VAL_EQ": "VALLS_VME_EQ", "MOM_EQ": "MOMLS_VME_EQ", "VAL_XS": "VAL^AA", "MOM_XS": "MOM^AA"}
out["corr_ours_vs_aqr_monthly_gross"] = {}
for a, b in pairs.items():
    df = pd.concat([ours[a], vme[b]], axis=1).dropna()
    out["corr_ours_vs_aqr_monthly_gross"][f"{a} vs {b}"] = {"corr": float(df.corr().iloc[0, 1]) if len(df) > 12 else None,
                                                             "n_months": int(len(df))}
(OUT / "vme_check.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=1))
