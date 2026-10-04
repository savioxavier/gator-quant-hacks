"""PLACEBO code-path test of the OOS branch WITHOUT any out-of-sample data: the engine period 'FWD' is redirected to
'IS' and the 'OOS' window is set to an in-sample window (2023-01-03..2024-10-02). Random scores. Not results."""
import sys
from pathlib import Path
import pandas as pd
S = Path("<scratch>")
sys.path.insert(0, str(S / "wire"))
import run_v2_chrono as W
R = W.R
_market = R.market
R.market = lambda period: _market("IS")          # never loads FWD
R.OOS = ("2023-01-03", "2024-10-02")             # stand-in window inside IS
R.PREREG_SHA = W.PREREG_SHA_NOW
R.DOC_SCORES = S / "placebo_chain/v2_score/doc_scores.parquet"
out = S / "placebo_chain/oos_codepath_test/v2_out_placebo"
out.mkdir(parents=True, exist_ok=True)
res = R.pipeline_is("run", out)
res["passed"] = True                             # force the branch
rec = R.stage_oos(res, out)
pd.DataFrame(W.scheduled_only(res["chosen"], "FWD", [("oos", R.OOS)], R.OOS[1])).to_csv(out / "sens_scheduled_only_oos.csv", index=False)
print("stage_oos code path OK:", {k: rec[k] for k in ("chosen", "window", "is_consistency_max_abs_diff")})
print(pd.read_csv(out / "sens_scheduled_only_oos.csv").iloc[:, :6].to_string())
print(sorted(p.name for p in out.iterdir()))
