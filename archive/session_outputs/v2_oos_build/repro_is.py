"""Step 1 of build_v2: reproduce the committed v2 in-sample results with the reported run's own code path
(run_v2_chrono.main up to the decision rule: pipeline_is + the D-1 scheduled-only IS sensitivity).

In-sample only: run_v2.market("IS") truncates every loader at 2024-10-02; stage_oos is never called.
Writes to the folder given as argv[1] (outside the repository).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

TEAM = Path(os.environ["TEAM_REPO"])
assert os.environ.get("GQH_OOS_UNLOCK") != "1"
assert not os.environ.get("V2_OOS_DEVIATION"), "step 1 runs without the D-3 unlock"
sys.path.insert(0, str(TEAM / "backtests" / "v2"))
import run_v2_chrono as C  # noqa: E402  (defines functions only)
import run_v2 as R  # noqa: E402  (imports gqh-flow-clock's src.engine)
from wirelib import jdump, sha256  # noqa: E402

C.R = R
got = sha256(R.PREREG)
if got != C.PREREG_SHA_NOW:
    raise SystemExit(f"pre-registration hash {got} != {C.PREREG_SHA_NOW}")
R.PREREG_SHA = C.PREREG_SHA_NOW
R.DOC_SCORES = TEAM / "backtests" / "v2" / "score" / "doc_scores.parquet"
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)

res = R.pipeline_is("run", out)
summ = res["summary"]
summ["mode"] = "run (chrono walk-forward stance scores)"
summ["prereg_sha256_checked"] = C.PREREG_SHA_NOW
summ["doc_scores"] = str(R.DOC_SCORES)
summ["doc_scores_sha256"] = sha256(R.DOC_SCORES)
jdump(summ, out / "summary_is.json")
chosen = res["chosen"]
is_w = [("selection", R.SEL), ("validation", R.VAL), ("full_is", R.FULL_IS)]
pd.DataFrame(C.scheduled_only(chosen, "IS", is_w, R.IS_END)).to_csv(out / "sens_scheduled_only_is.csv", index=False)
print({k: summ[k] for k in ("chosen", "selection_sharpe_net1x", "validation_sharpe_net1x", "full_is_sharpe_net2x",
                            "decision_rule_passed")})
