"""Gate: the chrono walk-forward run has finished cleanly.

    python check_chrono.py --root <chrono work root>

Passes (exit 0) only if
  * all 36 (year, seed) models 2015-2026 x {42, 43, 44} are done with max_epochs 8 and label-year rule `true`;
  * all 12 years have scores/<Y>.parquet and <Y>_docs.parquet, a full-spec <Y>_meta.json (all seeds, all
    documents, epoch cap, rule) and are newer than that year's models;
  * the scored documents are exactly the documents of docs_to_score.parquet;
  * every document in <Y>_docs.parquet is dated in year Y and carries model_year Y (model Y scores year Y only);
  * real mode (no --placebo): no year is marked placebo and every base model is chrono-bert-v1-<min(Y-1, 2024)>1231;
  * run.log's last line is run_local.py's "all done in ...", and the log has no FAILED or Traceback line.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

from wirelib import DOCS_TO_SCORE, LABEL_RULE, MAX_EPOCHS, SEEDS, YEARS, chrono_module


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--placebo", action="store_true", help="allow placebo-marked scores (chain test only)")
    a = ap.parse_args()
    root = Path(a.root)
    cs = chrono_module()
    problems = []
    done = [(y, s) for y in YEARS for s in SEEDS if cs.model_done(root, y, s, MAX_EPOCHS, LABEL_RULE)]
    if len(done) != len(YEARS) * len(SEEDS):
        missing = sorted(set((y, s) for y in YEARS for s in SEEDS) - set(done))
        problems.append(f"models done {len(done)}/36; missing {missing}")
    sd = root / "scores"
    ids = []
    for y in YEARS:
        f, fs = sd / f"{y}_docs.parquet", sd / f"{y}.parquet"
        if not (f.exists() and fs.exists()):
            problems.append(f"year {y}: scores missing")
            continue
        meta = cs.read_score_meta(root, y)
        p = cs.score_problems(meta, MAX_EPOCHS, SEEDS, LABEL_RULE)
        if p:
            problems.append(f"year {y}: not full-spec {p}")
        yd = pd.read_parquet(f, columns=["doc_id", "date", "model_year", "base_model"])
        nbad = int((pd.to_datetime(yd.date).dt.year != y).sum() + (yd.model_year != y).sum())
        if nbad:
            problems.append(f"year {y}: {nbad} documents dated outside {y} or scored by another model year")
        if not a.placebo:
            want_base = f"manelalab/chrono-bert-v1-{min(y - 1, 2024)}1231"
            if (meta or {}).get("placebo") or set(yd.base_model) != {want_base}:
                problems.append(f"year {y}: placebo-marked or unexpected base model {sorted(set(yd.base_model))}")
        mt = [(cs.model_dir(root, y, s) / "metrics.json") for s in SEEDS]
        if all(m.exists() for m in mt) and f.stat().st_mtime <= max(m.stat().st_mtime for m in mt):
            problems.append(f"year {y}: scores older than models")
        ids.append(pd.read_parquet(f, columns=["doc_id"]).doc_id)
    if ids:
        got = pd.concat(ids)
        want = set(pd.read_parquet(DOCS_TO_SCORE, columns=["doc_id"]).doc_id)
        if got.duplicated().any():
            problems.append(f"{int(got.duplicated().sum())} duplicated scored doc_ids")
        if set(got) != want:
            problems.append(f"scored docs {len(set(got))} vs docs_to_score {len(want)} "
                            f"(missing {len(want - set(got))}, extra {len(set(got) - want)})")
    log = root / "run.log"
    if not log.exists():
        problems.append("run.log missing")
    else:
        lines = [x for x in log.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]
        if not lines or not re.search(r"\ball done in \d+s\b", lines[-1]):
            problems.append(f"run.log does not end cleanly; last line: {lines[-1] if lines else '<empty>'!r}")
        bad = [x for x in lines if re.search(r"FAILED|Traceback|SystemExit", x)]
        if bad:
            problems.append(f"run.log has failure lines: {bad[:3]}")
    if problems:
        print("CHRONO RUN NOT READY:\n  " + "\n  ".join(problems))
        sys.exit(2)
    print(f"chrono run complete: 36/36 models, 12/12 years scored, {len(set(got))} documents, run.log clean")


if __name__ == "__main__":
    main()
