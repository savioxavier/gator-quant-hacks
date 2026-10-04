"""Build a PLACEBO chrono work root: random sentence labels with the exact output schema of chrono_stance.py score.

    python make_placebo.py --root <placebo dir>/chrono [--seed 0]

Writes models/<Y>/seed_<S>/metrics.json (stubs that pass model_done), scores/<Y>.parquet (sentence rows with random
labels), scores/<Y>_docs.parquet and <Y>_meta.json (built with the team code's own share_frame), and a run.log
ending like run_local.py's. Every file is marked placebo. The numbers carry no information.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from wirelib import DOCS_TO_SCORE, LABEL_RULE, MAX_EPOCHS, SEEDS, YEARS, chrono_module, jdump


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    root = Path(a.root)
    if "placebo" not in str(root).lower():
        raise SystemExit("refusing: the placebo root path must contain 'placebo'")
    cs = chrono_module()
    rng = np.random.default_rng(a.seed)
    docs = pd.read_parquet(DOCS_TO_SCORE)
    (root / "PLACEBO_README.txt").parent.mkdir(parents=True, exist_ok=True)
    (root / "PLACEBO_README.txt").write_text(
        "PLACEBO chrono work root: random sentence labels with the real output schema. Not results.\n",
        encoding="utf-8")
    for y in YEARS:
        for s in SEEDS:
            jdump({"done": True, "placebo": True, "year": y, "seed": s, "hp": {"max_epochs": MAX_EPOCHS},
                   "label_year_rule": LABEL_RULE, "val_macro_f1": None}, cs.model_dir(root, y, s) / "metrics.json")
    time.sleep(1.1)  # scores must be newer than the models (the completion check compares mtimes)
    sd = root / "scores"
    sd.mkdir(parents=True, exist_ok=True)
    log = [f"[00:00:00] PLACEBO run: label-year rule: {LABEL_RULE}",
           f"[00:00:00] training: 0 to run, {len(YEARS) * len(SEEDS)} already done, concurrency 0"]
    for y in YEARS:
        d = docs[docs.year == y]
        rows = []
        for r in d.itertuples(index=False):
            k = int(rng.poisson(max(r.n_words, 1) / 25.0))
            if r.source != "presser_question" and r.source != "presser_answer":
                k = max(k, 1)
            for i in range(k):
                rows.append((r.doc_id, r.source, r.date, i, "placebo sentence", False))
            if r.source in ("statement", "presser_statement"):
                rows.append((r.doc_id, r.source, r.date, k, "Voting for the monetary policy action were placebo.",
                             True))
        S = pd.DataFrame(rows, columns=["doc_id", "source", "date", "sent_idx", "sentence", "roster"])
        P = rng.dirichlet([1.0, 1.0, 1.0], len(S)).astype("float32")
        for sd_ in SEEDS:
            S[f"p_hawk_s{sd_}"] = P[:, 1]
            S[f"p_dove_s{sd_}"] = P[:, 0]
        S["p_dove"], S["p_hawk"], S["p_neut"] = P[:, 0], P[:, 1], P[:, 2]
        S["label"] = [cs.LABELS[int(k)] for k in P.argmax(1)] if len(S) else []
        S["model_year"] = y
        S.to_parquet(sd / f"{y}.parquet", index=False)
        D = d[["doc_id", "source", "date", "year", "meeting", "n_words"]].set_index("doc_id")
        allf = cs.share_frame(S, "doc_id")
        exr = cs.share_frame(S[~S.roster], "doc_id")[["n_sentences", "score"]].add_suffix("_excl_roster")
        D = D.join(allf).join(exr)
        D["n_sentences"] = D.n_sentences.fillna(0).astype(int)
        D["n_sentences_excl_roster"] = D.n_sentences_excl_roster.fillna(0).astype(int)
        D["model_year"] = y
        D["base_model"] = "PLACEBO"
        D["seeds"] = ",".join(map(str, SEEDS))
        D["label_year_rule"] = LABEL_RULE
        D.reset_index().to_parquet(sd / f"{y}_docs.parquet", index=False)
        jdump({"year": y, "seeds": SEEDS, "label_year_rule": LABEL_RULE, "max_epochs": MAX_EPOCHS, "placebo": True,
               "seed_val_macro_f1": {}, "n_docs": int(len(D)), "n_sentences": int(len(S)), "partial": False,
               "sources": "all", "limit_docs": 0}, sd / f"{y}_meta.json")
        log.append(f"[00:00:00] score {y}: PLACEBO ({len(D)} docs, {len(S)} sentences)")
    log.append(f"[00:00:00] all done in 0s; outputs in {sd} (PLACEBO)")
    (root / "run.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"placebo chrono root written: {root}")


if __name__ == "__main__":
    main()
