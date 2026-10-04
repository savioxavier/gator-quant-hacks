"""Adapter: chrono walk-forward scores -> press-conference text tables (DEVIATION_D1 + D1a), H1 = qa_mean - statement.

    python adapt_presser.py --chrono-root <chrono work root> --text-out <dir> [--placebo]

Reads presser_bt/text/answers.parquet and meetings.parquet (segmentation, timing, lexicon control; stance columns NaN)
and writes copies to --text-out with the stance columns filled by the definitions of presser_bt/text/code/build.py,
applied to the chrono sentence labels:
  answers : hawk, dove, score (share hawkish - share dovish over the answer's chrono units), question_score (same
            over the preceding question), cum_mean_score (running mean of scorable answer scores within the meeting),
            n_sentences_chrono / q_n_sentences_chrono (the scorer's unit counts)
  meetings: statement_hawk/dove/score (roster sentence excluded), statement_score_incl_roster,
            qa_mean_score (answers with >= 1 chrono unit), qa_mean_score_ge40w, qa_pooled_score, q_mean_score,
            H1 = qa_mean_score - statement_score, statement_n_sentences_chrono, n_answers_scorable_chrono,
            roberta_status (scorer id)
The text pipeline's own unit counts (n_sentences, q_n_sentences, statement_n_sentences, n_answers_scorable) are kept
unchanged, so the answer eligibility of the lexicon control is exactly as before; a stance answer additionally needs a
finite chrono score (the backtest's own rule). The chrono and text-pipeline splitters agree for 99.4% of answers.
Every lex_* column and all timing columns are copied unchanged (checked). The meeting values are cross-checked against
the team code's own merged table scores/presser_meetings_chrono.parquet. Also writes build_meta.json (copied) and
scorer.json (scorer id, input hashes), which the backtest records.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from wirelib import PRESSER, YEARS, jdump, jload, sha256

TEXT_IN = PRESSER / "text"


def shares(lab: pd.DataFrame, key: str) -> pd.DataFrame:
    g = lab.groupby(key).label
    o = pd.DataFrame({"n": g.size(), "hawk": g.apply(lambda x: float((x == "hawk").mean())),
                      "dove": g.apply(lambda x: float((x == "dove").mean()))})
    o["score"] = o.hawk - o.dove
    return o


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrono-root", required=True)
    ap.add_argument("--text-out", required=True)
    ap.add_argument("--placebo", action="store_true")
    a = ap.parse_args()
    root, out = Path(a.chrono_root), Path(a.text_out)
    if a.placebo and "placebo" not in str(out).lower():
        raise SystemExit("refusing: a placebo output path must contain 'placebo'")
    if not a.placebo and "placebo" in str(root).lower():
        raise SystemExit("refusing: real mode pointed at a placebo chrono root")
    if out.resolve() == TEXT_IN.resolve():
        raise SystemExit("refusing to overwrite presser_bt/text (keep the frozen text label)")
    sd = root / "scores"
    mm = jload(sd / "merge_meta.json")
    if mm.get("label_year_rule") != "true":
        raise SystemExit(f"label-year rule {mm.get('label_year_rule')} != true (D1a)")
    if mm.get("nonspec_years") and not a.placebo:
        raise SystemExit(f"non-full-spec years in the merge: {mm['nonspec_years']}")
    D = pd.read_parquet(sd / "doc_scores_chrono.parquet")
    pres = D[D.source.isin(["presser_answer", "presser_question", "presser_statement"])]
    if (pres.meeting.astype(str).str.slice(0, 4).astype(int) != pres.model_year).any():
        raise SystemExit("a press-conference document was scored by a model of another year than its meeting")
    S = pd.concat([pd.read_parquet(sd / f"{y}.parquet", columns=["doc_id", "source", "roster", "label"])
                   for y in YEARS if (sd / f"{y}.parquet").exists()], ignore_index=True)

    # ------------------------------------------------------------------ answers
    A0 = pd.read_parquet(TEXT_IN / "answers.parquet")
    A = A0.copy()
    da = D[D.source == "presser_answer"].set_index("doc_id")
    dq = D[D.source == "presser_question"].set_index("doc_id")
    miss = sorted(set(A.answer_id) - set(da.index))
    if miss:
        raise SystemExit(f"{len(miss)} answers have no chrono score, e.g. {miss[:5]}")
    missq = sorted(set("q_" + A.answer_id) - set(dq.index))
    if missq:
        raise SystemExit(f"{len(missq)} questions have no chrono score, e.g. {missq[:5]}")
    if (da.loc[A.answer_id, "meeting"].astype(str).to_numpy() != A.meeting.astype(str).to_numpy()).any():
        raise SystemExit("answer -> meeting mismatch between chrono docs and answers.parquet")
    A["n_sentences_chrono"] = da.loc[A.answer_id, "n_sentences"].astype(int).to_numpy()
    A["hawk"] = da.loc[A.answer_id, "share_hawk"].to_numpy()
    A["dove"] = da.loc[A.answer_id, "share_dove"].to_numpy()
    A["score"] = da.loc[A.answer_id, "score"].to_numpy()
    qid = "q_" + A.answer_id
    A["q_n_sentences_chrono"] = dq.loc[qid, "n_sentences"].astype(int).to_numpy()
    A["question_score"] = dq.loc[qid, "score"].to_numpy()
    sc = A.score.where(A.n_sentences_chrono > 0)
    A["cum_mean_score"] = sc.groupby(A.meeting).transform(lambda x: x.expanding().mean())
    A["stance_model_year"] = da.loc[A.answer_id, "model_year"].astype(int).to_numpy()

    # ------------------------------------------------------------------ meetings
    M0 = pd.read_parquet(TEXT_IN / "meetings.parquet")
    M = M0.copy()
    st = D[D.source == "presser_statement"][["doc_id", "meeting"]]
    stm = S[S.source == "presser_statement"].merge(st, on="doc_id", how="left")
    if stm.meeting.isna().any():
        raise SystemExit("statement sentences without a meeting")
    ex = shares(stm[~stm.roster], "meeting")
    inc = shares(stm, "meeting")
    sa = S[S.source == "presser_answer"].copy()
    sa["meeting"] = sa.doc_id.str.slice(0, 8)
    pooled = shares(sa, "meeting")
    k = M.meeting.astype(str)
    missm = sorted(set(k) - set(ex.index))
    if missm:
        raise SystemExit(f"{len(missm)} meetings have no scored statement units: {missm[:5]}")
    M["statement_hawk"] = k.map(ex.hawk).to_numpy()
    M["statement_dove"] = k.map(ex.dove).to_numpy()
    M["statement_score"] = k.map(ex.score).to_numpy()
    M["statement_n_sentences_chrono"] = k.map(ex.n).fillna(0).astype(int).to_numpy()
    M["statement_score_incl_roster"] = k.map(inc.score).to_numpy()
    M["qa_pooled_score"] = k.map(pooled.score).to_numpy()
    g = A[A.n_sentences_chrono > 0].groupby("meeting")
    M["qa_mean_score"] = k.map(g.score.mean()).to_numpy()
    M["qa_mean_score_ge40w"] = k.map(A[(A.n_sentences_chrono > 0) & (A.n_words >= 40)].groupby("meeting").score.mean()).to_numpy()
    M["q_mean_score"] = k.map(A[A.q_n_sentences_chrono > 0].groupby("meeting").question_score.mean()).to_numpy()
    M["H1"] = M.qa_mean_score - M.statement_score
    M["n_answers_scorable_chrono"] = k.map(A.groupby("meeting").n_sentences_chrono.apply(lambda x: int((x > 0).sum()))).fillna(0).astype(int).to_numpy()
    tag = ("PLACEBO random scores (wiring test only)" if a.placebo else
           "chrono walk-forward stance model (DEVIATION_D1 + D1a = HYPOTHESIS_v2 Amendments 2-3; model Y scores "
           "year Y; 3-seed mean probabilities, argmax; label-year rule true)")
    M["roberta_status"] = f"replaced: {tag}"

    # ------------------------------------------------------------------ checks
    for c in [c for c in A0.columns if c.startswith("lex_") or c.startswith("q_lex_")] + [
            "t_start_et", "t_end_et", "timing_source", "t_end_video_s", "end_cue_dur", "n_words", "drop_P_timing",
            "n_sentences", "q_n_sentences"]:
        pd.testing.assert_series_equal(A[c], A0[c])
    for c in [c for c in M0.columns if c.startswith("lex_")] + ["date", "chair", "sample", "drop_P_timing",
                                                                 "statement_n_sentences", "n_answers_scorable"]:
        pd.testing.assert_series_equal(M[c], M0[c])
    ref = pd.read_parquet(sd / "presser_meetings_chrono.parquet").set_index("meeting")
    xchk = {}
    for mine, theirs in [("statement_score", "statement_score"), ("qa_mean_score", "qa_mean"), ("H1", "H1"),
                         ("qa_pooled_score", "qa_pooled"), ("q_mean_score", "q_mean"),
                         ("statement_score_incl_roster", "statement_score_incl_roster"),
                         ("qa_mean_score_ge40w", "qa_mean_ge40w")]:
        x = M.set_index(k)[mine]
        y = ref[theirs].reindex(x.index)
        both = x.notna() & y.notna()
        xchk[mine] = {"max_abs_diff": float((x[both] - y[both]).abs().max()) if both.any() else None,
                      "nan_pattern_mismatch": int((x.isna() != y.isna()).sum())}
    for c in ("statement_score", "qa_mean_score", "H1"):
        if (xchk[c]["max_abs_diff"] or 0) > 1e-9 or xchk[c]["nan_pattern_mismatch"]:
            raise SystemExit(f"cross-check vs presser_meetings_chrono.parquet failed for {c}: {xchk[c]}")

    out.mkdir(parents=True, exist_ok=True)
    A.to_parquet(out / "answers.parquet", index=False)
    M.to_parquet(out / "meetings.parquet", index=False)
    shutil.copy2(TEXT_IN / "build_meta.json", out / "build_meta.json")
    meta = {"stance_scorer": tag, "placebo": a.placebo, "chrono_root": str(root),
            "inputs_sha256": {str(p): sha256(p) for p in [sd / "doc_scores_chrono.parquet",
                                                          sd / "presser_meetings_chrono.parquet",
                                                          TEXT_IN / "answers.parquet", TEXT_IN / "meetings.parquet"]},
            "merge_meta": mm, "crosscheck_vs_team_merge": xchk,
            "n_answers": int(len(A)), "n_answers_scorable_chrono": int((A.n_sentences_chrono > 0).sum()),
            "n_answers_unit_count_equal_textpipe": int((A.n_sentences_chrono == A.n_sentences).sum()),
            "n_answers_textpipe_ge1_but_no_chrono_score": int(((A.n_sentences > 0) & A.score.isna()).sum()),
            "n_meetings": int(len(M)), "n_meetings_H1": int(M.H1.notna().sum()),
            "H1_by_sample": M.groupby("sample").H1.agg(["count", "mean", "std"]).to_dict()}
    jdump(meta, out / "scorer.json")
    print(f"wrote {out}: {len(A)} answers ({meta['n_answers_scorable_chrono']} scorable), {len(M)} meetings "
          f"({meta['n_meetings_H1']} with H1); cross-check {xchk['H1']}")


if __name__ == "__main__":
    main()
