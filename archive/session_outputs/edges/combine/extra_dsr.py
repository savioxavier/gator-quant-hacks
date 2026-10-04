"""Supplementary: Deflated Sharpe of the core portfolios (not the IS-best) and the analytic forward-Sharpe range
of the core equal-risk mix under the verifiers' forward expectations for each sleeve."""
import json, math, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "<solo-repo>")
from src import engine as E
OUT = Path(__file__).resolve().parent
s = json.loads((OUT / "summary.json").read_text())
start, var = s["common_start"], s["dsr"]["var_sr_ann"]
P = pd.read_parquet(OUT / "portfolios.parquet")
res = {}
for k in ("core_ER_6", "core_ER_10", "core_IV_6", "core_IV_10"):
    x = P[(k, "net_1x")].loc[start:"2024-10-02"].dropna()
    sr = x.mean() / x.std() * math.sqrt(252)
    yrs = len(x) / 252
    res[k] = {"is_sharpe": sr, "se_approx": math.sqrt((1 + sr ** 2 / 2) / yrs),
              "dsr_117_var_study": E.deflated_sharpe(x, 117, var)["dsr"],
              "dsr_117_var_0.10": E.deflated_sharpe(x, 117, 0.10)["dsr"],
              "dsr_17_var_study": E.deflated_sharpe(x, 17, var)["dsr"]}
C = pd.read_csv(OUT / "corr_core_is.csv", index_col=0).loc[["rpm_ES_MM", "CAL_TSY_ME_ZN", "S1"], ["rpm_ES_MM", "CAL_TSY_ME_ZN", "S1"]].to_numpy()
den = math.sqrt(C.sum())
fwd = {}
for lab, srs in {"low": (0.45, 0.50, 0.0), "mid": (0.50, 0.60, 0.20), "high": (0.55, 0.70, 0.40)}.items():
    fwd[lab] = {"sleeve_sr": srs, "portfolio_sr_before_overlay_costs": sum(srs) / den}
res["forward_range_core_ER"] = fwd
(OUT / "extra_dsr.json").write_text(json.dumps(res, indent=2))
print(json.dumps(res, indent=1))
