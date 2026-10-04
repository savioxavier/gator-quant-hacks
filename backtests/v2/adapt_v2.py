"""Adapter: chrono walk-forward document scores -> fedspeak_v2 score/doc_scores.parquet (HYPOTHESIS_v2 Amendments 2-3).

    python adapt_v2.py --chrono-root <chrono work root> --out <doc_scores.parquet> [--placebo] [--keep-if-equal]

--keep-if-equal (used by run_results.sh once the v2 run is complete): if --out exists, it is left byte-for-byte
untouched when the rebuilt table is identical, and the call fails when it differs (the finished v2 run used it).

Starts from score/doc_scores_lexonly.parquet (same 1,098 documents, lexicon columns) and fills only the model columns:
  rob_hawk = share_hawk, rob_dove = share_dove, rob_neut = share_neut, rob_score = score (= share hawkish - share
  dovish, sentence label = argmax of the 3-seed averaged probabilities, document dated in year Y scored by model Y),
  n_sentences = the chrono splitter's unit count (the v2 splitter's count is kept as n_sentences_v2split),
  rob_status = the scorer id.
Every lex_* column is copied unchanged and checked equal to the lexicon-only file. The v2 doc_type maps to the chrono
source (presser -> presser_doc); doc_id, source and date must match one to one.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "wire"))
from wirelib import V2, V2_SOURCES, jdump, jload, sha256  # noqa: E402

LEXONLY = V2 / "score" / "doc_scores_lexonly.parquet"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrono-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--placebo", action="store_true")
    ap.add_argument("--keep-if-equal", action="store_true")
    a = ap.parse_args()
    root, out = Path(a.chrono_root), Path(a.out)
    if a.placebo and "placebo" not in str(out).lower():
        raise SystemExit("refusing: a placebo output path must contain 'placebo'")
    if not a.placebo and "placebo" in str(root).lower():
        raise SystemExit("refusing: real mode pointed at a placebo chrono root")
    src = root / "scores" / "doc_scores_chrono.parquet"
    mm = jload(root / "scores" / "merge_meta.json")
    if mm.get("label_year_rule") != "true":
        raise SystemExit(f"label-year rule {mm.get('label_year_rule')} != true (Amendment 3)")
    if mm.get("years_absent"):
        raise SystemExit(f"merged scores lack years {mm['years_absent']}")
    if mm.get("nonspec_years") and not a.placebo:
        raise SystemExit(f"non-full-spec years in the merge: {mm['nonspec_years']}")
    D = pd.read_parquet(src)
    D = D[D.source.isin(V2_SOURCES.values())]
    if D.doc_id.duplicated().any():
        raise SystemExit("duplicated doc_id in chrono scores")
    lx = pd.read_parquet(LEXONLY)
    lx["_source"] = lx.doc_type.map(V2_SOURCES)
    if lx._source.isna().any():
        raise SystemExit(f"unmapped v2 doc_type {sorted(lx.doc_type[lx._source.isna()].unique())}")
    j = lx[["doc_id", "_source", "date"]].merge(
        D[["doc_id", "source", "date", "n_sentences", "share_hawk", "share_dove", "share_neut", "score",
           "model_year", "base_model", "seeds", "label_year_rule"]].rename(columns={"date": "c_date"}),
        on="doc_id", how="left", validate="one_to_one")
    miss = j.source.isna()
    if miss.any():
        raise SystemExit(f"{int(miss.sum())} v2 documents have no chrono score, e.g. {j.doc_id[miss].head(5).tolist()}")
    if (j.source != j._source).any():
        raise SystemExit(f"source mismatch for {int((j.source != j._source).sum())} documents")
    dd = pd.to_datetime(j.date).dt.normalize() != pd.to_datetime(j.c_date).dt.normalize()
    if dd.any():
        raise SystemExit(f"date mismatch for {int(dd.sum())} documents, e.g. {j.doc_id[dd].head(5).tolist()}")
    if (pd.to_datetime(j.date).dt.year != j.model_year).any():
        raise SystemExit("a document was scored by a model of another year")
    o = lx.drop(columns="_source").copy()
    lex_cols = [c for c in o.columns if c.startswith("lex_")]
    o["n_sentences_v2split"] = o["n_sentences"]
    o["rob_hawk"] = j.share_hawk.to_numpy()
    o["rob_dove"] = j.share_dove.to_numpy()
    o["rob_neut"] = j.share_neut.to_numpy()
    o["rob_score"] = j.score.to_numpy()
    o["n_sentences"] = j.n_sentences.astype(int).to_numpy()
    o["stance_model_year"] = j.model_year.astype(int).to_numpy()
    o["stance_base_model"] = j.base_model.to_numpy()
    o["stance_seeds"] = j.seeds.to_numpy()
    o["stance_label_year_rule"] = j.label_year_rule.to_numpy()
    tag = ("PLACEBO random scores (wiring test only)" if a.placebo else
           "chrono walk-forward stance model (HYPOTHESIS_v2 Amendments 2-3; model Y scores year Y; "
           "3-seed mean probabilities, argmax; label-year rule true)")
    o["rob_status"] = tag
    for c in lex_cols:  # lexicon columns untouched
        pd.testing.assert_series_equal(o[c], lx[c], check_names=True)
    nan = o.rob_score.isna()
    if nan.any():
        raise SystemExit(f"{int(nan.sum())} documents have zero chrono sentence units (rob_score NaN): "
                         f"{o.doc_id[nan].head(10).tolist()}")
    if a.keep_if_equal and out.exists():
        try:
            pd.testing.assert_frame_equal(pd.read_parquet(out), o.reset_index(drop=True))
        except AssertionError as e:
            raise SystemExit(f"refusing: {out} differs from the rebuilt table, and the completed v2 run used it: "
                             f"{str(e)[:300]}")
        print(f"{out} unchanged (identical to the rebuilt table); left untouched")
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    o.to_parquet(out, index=False)
    meta = {"placebo": a.placebo, "stance_scorer": tag, "out": str(out), "out_sha256": sha256(out),
            "chrono_doc_scores": str(src), "chrono_doc_scores_sha256": sha256(src),
            "lexonly": str(LEXONLY), "lexonly_sha256": sha256(LEXONLY), "merge_meta": mm,
            "n_docs": int(len(o)), "docs_by_type": o.doc_type.value_counts().to_dict(),
            "lex_columns_unchanged": lex_cols,
            "n_sentences_chrono_vs_v2split_equal_share": float(np.mean(o.n_sentences == o.n_sentences_v2split)),
            "rob_score_mean_by_type": o.groupby("doc_type").rob_score.mean().to_dict()}
    jdump(meta, out.with_name(out.stem + "_meta.json"))
    print(f"wrote {out}: {len(o)} documents; chrono vs v2 splitter unit counts equal for "
          f"{meta['n_sentences_chrono_vs_v2split_equal_share']:.1%}")


if __name__ == "__main__":
    main()
