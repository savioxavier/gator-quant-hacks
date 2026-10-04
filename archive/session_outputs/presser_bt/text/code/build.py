"""Step 4: assemble answers.parquet and meetings.parquet (text features + timing; no returns).

FOMC-RoBERTa columns are filled from sentence_labels.parquet when it exists (score_roberta.py); otherwise they
stay NaN and roberta_status says why. Everything else (segmentation, timing, lexicon control) is filled now.

Scores
  * answer score       = share hawkish - share dovish over the answer's sentence units (FOMC-RoBERTa argmax)
  * statement_score    = same over the same-day statement, roster sentence(s) excluded
  * qa_mean_score      = equal-weight mean of answer scores over answers with >= 1 sentence unit  (plan: mean(hawk(Q&A)))
  * H1                 = qa_mean_score - statement_score
  * question_score     = same share difference over the reporter question(s) that preceded the answer (H1-Q only)
  * cum_mean_score     = running mean of answer scores through this answer (known at this answer's end)
  * lex_*              = frozen strategies/01 lexicon, code imported verbatim (tokenize, score_tokens):
                         s = (H - D) / (H + D + 1) if H + D >= 5 else NaN (MIN_HD = 5); *_raw = same without the gate.
Timing (plan: drop a meeting from (P) tests if start uncertainty > 30 s)
  * t_*_et = video zero (14:30:00 ET; 11:00 on 2020-03-03; 18:30 on 2020-03-15) + caption time.
  * start_uncert_lb_s = max(greeting_video_s, robust caption overrun, |gpt_offset_s|): a LOWER bound on the
    disagreement between start-time sources (video zero vs first audible PDF-matching open vs caption timeline vs
    the published video length vs the Gorodnichenko et al. YouTube-based clock, 2016-2019 only). True wall-clock
    error is unknown (no Bloomberg anchor). drop_P_timing = no captions or start_uncert_lb_s > 30.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1]
SCR = Path("<scratch>")
S01 = SCR / "savio_gqh/strategies/01"
VIDEO_META = SCR / "fedtalk/data_markets/video_meta.csv"
VTT_DIR = SCR / "fedtalk/data_markets/vtt"
GPT_XLSX = SCR / "fedtalk/verify_literature/fomc_all.xlsx"
FROZEN_SHA = {"scripts/score.py": "be6ad6e3b8259a42d20362f575c1de0bf75de5a54964154f7f7e5fccf2b790aa",
              "lexicon/hawk.txt": "ceead1cae1edd8a2acef83e20dfe2bc5934494d20339d756f912f22dd7cf33bf",
              "lexicon/dove.txt": "2d43390600d89c7c113b6007bc36c74b37e56dc461a7e7865259acc6981ce5ae"}


def load_frozen_lexicon():
    for rel, h in FROZEN_SHA.items():
        got = hashlib.sha256((S01 / rel).read_bytes()).hexdigest()
        if got != h:
            raise SystemExit(f"frozen lexicon file changed: {rel} {got}")
    if "bs4" not in sys.modules:  # score.py imports bs4 for HTML extraction only; not used here
        try:
            import bs4  # noqa: F401
        except ImportError:
            stub = types.ModuleType("bs4")
            stub.BeautifulSoup = None
            sys.modules["bs4"] = stub
    sys.path.insert(0, str(S01 / "scripts"))
    import score as s01  # noqa: E402
    import config as c01  # noqa: E402
    return s01, c01.MIN_HD


def lex_s(h, d, min_hd):
    h, d = np.asarray(h, float), np.asarray(d, float)
    raw = (h - d) / (h + d + 1.0)
    return np.where(h + d >= min_hd, raw, np.nan), raw


def share_scores(lab: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    g = lab.groupby(keys)
    out = pd.DataFrame({"n_sentences": g.size(),
                        "hawk": g.label.apply(lambda x: (x == "hawk").mean()),
                        "dove": g.label.apply(lambda x: (x == "dove").mean())})
    out["score"] = out.hawk - out.dove
    return out.reset_index()


def gpt_offsets(ans: pd.DataFrame) -> pd.DataFrame:
    """Gorodnichenko-Pham-Talavera replication answer clock (YouTube copy, 14:30 + video time) vs our caption clock."""
    if not GPT_XLSX.exists():
        return pd.DataFrame(columns=["meeting", "gpt_offset_s", "gpt_n_matched", "gpt_n"])
    d = pd.read_excel(GPT_XLSX, sheet_name="QA_identifier").drop(columns=["answer"])
    d["meeting"] = pd.to_datetime(d.date).dt.strftime("%Y%m%d")
    d["s"] = (pd.to_datetime(d.datetime_start) - pd.to_datetime(d.press_conf_time)).dt.total_seconds()
    rows = []
    for m, g in d.groupby("meeting"):
        cs = ans.loc[(ans.meeting == m) & ans.t_start_video_s.notna(), "t_start_video_s"].to_numpy()
        if len(cs) == 0:
            continue
        gs = np.sort(g.s.to_numpy())
        grid = np.arange(-400, 400.25, 0.25)
        score = [int(np.sum(np.min(np.abs((gs[:, None] - o) - cs[None, :]), axis=1) < 3)) for o in grid]
        best = int(np.argmax(score))
        o = grid[best]
        res = np.array([(x - o) - cs[np.argmin(np.abs(cs - (x - o)))] for x in gs])
        rows.append(dict(meeting=m, gpt_offset_s=float(o + np.median(res[np.abs(res) < 3])) if score[best] else np.nan,
                         gpt_n_matched=score[best], gpt_n=len(gs)))
    return pd.DataFrame(rows)


def vtt_last_cue_start(m: str) -> float:
    p = VTT_DIR / f"{m}.vtt"
    if not p.exists():
        return np.nan
    ts = re.findall(r"^((?:\d+:)?\d+:\d+\.\d+)\s+-->", p.read_text(encoding="utf-8"), flags=re.M)
    s = ts[-1].split(":")
    return float(s[0]) * 3600 + float(s[1]) * 60 + float(s[2]) if len(s) == 3 else float(s[0]) * 60 + float(s[1])


def sample_of(m: str, chair: str) -> str:
    if "WARSH" in chair:
        return "warsh_2026"
    if m >= "20230101":
        return "confirm_2023_2026_powell"
    return "contaminated_2016_2022"


def main() -> None:
    s01, min_hd = load_frozen_lexicon()
    turns = pd.read_parquet(OUT / "turns.parquet")
    amap = pd.read_parquet(OUT / "answer_map.parquet")
    S = pd.read_parquet(OUT / "sentences.parquet")
    TT = pd.read_parquet(OUT / "turn_times.parquet")
    AM = pd.read_parquet(OUT / "align_meetings.parquet")
    st = pd.read_parquet(OUT / "statements.parquet")
    vm = pd.read_csv(VIDEO_META, dtype={"date": str}).rename(columns={"date": "meeting"})

    lab_path = OUT / "sentence_labels.parquet"
    status_path = OUT / "rob_status.json"
    if lab_path.exists():
        L = S.merge(pd.read_parquet(lab_path), on="unit_id", how="left")
        roberta_status = "scored"
    else:
        L = S.assign(label=pd.NA)
        roberta_status = json.loads(status_path.read_text())["status"] if status_path.exists() else "not_run"
        roberta_status = f"{roberta_status}: gtfintechlab/FOMC-RoBERTa is a gated repo (manual approval); no access"

    # ---------------- answers ----------------
    A = amap.merge(TT, on=["meeting", "turn_idx"], how="left")
    n_sent = S[S.doc == "answer"].groupby("answer_id").size().rename("n_sentences")
    q_sent = S[S.doc == "question"].groupby("answer_id").size().rename("q_n_sentences")
    A = A.merge(n_sent, on="answer_id", how="left").merge(q_sent, on="answer_id", how="left")
    A[["n_sentences", "q_n_sentences"]] = A[["n_sentences", "q_n_sentences"]].fillna(0).astype(int)
    if roberta_status == "scored":
        sa = share_scores(L[L.doc == "answer"], ["answer_id"]).drop(columns="n_sentences")
        sq = share_scores(L[L.doc == "question"], ["answer_id"])[["answer_id", "score"]].rename(
            columns={"score": "question_score"})
        A = A.merge(sa, on="answer_id", how="left").merge(sq, on="answer_id", how="left")
    else:
        A["hawk"] = A["dove"] = A["score"] = A["question_score"] = np.nan
    hd = [s01.score_tokens(s01.tokenize(t)) for t in A.answer_text]
    A["lex_h"] = [h for h, _ in hd]
    A["lex_d"] = [d for _, d in hd]
    A["lex_score"], A["lex_score_raw"] = lex_s(A.lex_h, A.lex_d, min_hd)
    qhd = [s01.score_tokens(s01.tokenize(t)) for t in A.question_text]
    A["q_lex_h"] = [h for h, _ in qhd]
    A["q_lex_d"] = [d for _, d in qhd]
    A = A.sort_values(["meeting", "turn_idx"]).reset_index(drop=True)
    A["answer_no"] = A.groupby("meeting").cumcount()
    sc = A.score.where(A.n_sentences > 0)
    A["cum_mean_score"] = sc.groupby(A.meeting).transform(lambda x: x.expanding().mean())
    A["timing_uncert_s"] = A[["start_cue_dur", "end_cue_dur"]].max(axis=1)

    # ---------------- meetings ----------------
    chair = turns[turns.role == "opening"].set_index("meeting").speaker.str.replace("CHAIRMAN", "CHAIR")
    M = pd.DataFrame({"meeting": sorted(A.meeting.unique())})
    M["date"] = pd.to_datetime(M.meeting)
    M["chair"] = M.meeting.map(chair).str.replace("CHAIR ", "").str.title()
    M["sample"] = [sample_of(m, c.upper()) for m, c in zip(M.meeting, M.chair)]
    M["pre2020"] = M.meeting < "20200101"
    M["unscheduled"] = M.meeting.isin(["20200303", "20200315"])
    M["sep"] = M.date.dt.month.isin([3, 6, 9, 12]) & ~M.unscheduled
    stmt = L[(L.doc == "statement")]
    M = M.merge(stmt[~stmt.roster].groupby("meeting").size().rename("statement_n_sentences"), on="meeting")
    if roberta_status == "scored":
        ss = share_scores(stmt[~stmt.roster], ["meeting"]).rename(
            columns={"hawk": "statement_hawk", "dove": "statement_dove", "score": "statement_score"}).drop(
            columns="n_sentences")
        ssa = share_scores(stmt, ["meeting"])[["meeting", "score"]].rename(columns={"score": "statement_score_incl_roster"})
        M = M.merge(ss, on="meeting", how="left").merge(ssa, on="meeting", how="left")
        pooled = share_scores(L[L.doc == "answer"], ["meeting"])[["meeting", "score"]].rename(
            columns={"score": "qa_pooled_score"})
        M = M.merge(pooled, on="meeting", how="left")
    else:
        for c in ["statement_hawk", "statement_dove", "statement_score", "statement_score_incl_roster",
                  "qa_pooled_score"]:
            M[c] = np.nan
    g = A[A.n_sentences > 0].groupby("meeting")
    M = M.merge(g.score.mean().rename("qa_mean_score"), on="meeting", how="left")
    M = M.merge(A[(A.n_sentences > 0) & (A.n_words >= 40)].groupby("meeting").score.mean().rename(
        "qa_mean_score_ge40w"), on="meeting", how="left")
    M = M.merge(A[A.q_n_sentences > 0].groupby("meeting").question_score.mean().rename("q_mean_score"),
                on="meeting", how="left")
    M["H1"] = M.qa_mean_score - M.statement_score
    cnt = A.groupby("meeting").agg(n_answers=("answer_id", "size"),
                                   n_answers_scorable=("n_sentences", lambda x: int((x > 0).sum())),
                                   n_answers_timed=("t_start_video_s", lambda x: int(x.notna().sum())),
                                   qa_start_et=("t_start_et", "min"), last_answer_end_et=("t_end_et", "max"))
    M = M.merge(cnt, on="meeting", how="left")
    M["timing_coverage"] = M.n_answers_timed / M.n_answers
    # lexicon control
    sth = {r.meeting: s01.score_tokens(s01.tokenize(" ".join(
        stmt[(stmt.meeting == r.meeting) & ~stmt.roster].sentence))) for r in M.itertuples()}
    M["lex_statement_h"] = M.meeting.map(lambda m: sth[m][0])
    M["lex_statement_d"] = M.meeting.map(lambda m: sth[m][1])
    M["lex_statement"], M["lex_statement_raw"] = lex_s(M.lex_statement_h, M.lex_statement_d, min_hd)
    lp = A.groupby("meeting")[["lex_h", "lex_d"]].sum()
    M["lex_qa_h"] = M.meeting.map(lp.lex_h)
    M["lex_qa_d"] = M.meeting.map(lp.lex_d)
    M["lex_qa_pooled"], M["lex_qa_pooled_raw"] = lex_s(M.lex_qa_h, M.lex_qa_d, min_hd)
    M["lex_qa_mean"] = M.meeting.map(A.groupby("meeting").lex_score.mean())
    M["lex_H1"] = M.lex_qa_pooled - M.lex_statement
    M["lex_H1_raw"] = M.lex_qa_pooled_raw - M.lex_statement_raw
    # timing / alignment quality
    M = M.merge(AM.drop(columns=["base_et"]), on="meeting", how="left")
    M = M.merge(vm[["meeting", "duration_s"]].rename(columns={"duration_s": "video_duration_s"}), on="meeting",
                how="left")
    M["vtt_last_cue_start_s"] = M.meeting.map(vtt_last_cue_start)
    M["caption_overrun_s"] = M.vtt_last_cue_start_s - M.video_duration_s
    gp = gpt_offsets(A)
    M = M.merge(gp, on="meeting", how="left")
    base = {m: pd.Timestamp(f"{m[:4]}-{m[4:6]}-{m[6:]} " + {"20200303": "11:00:00", "20200315": "18:30:00"}.get(
        m, "14:30:00"), tz="America/New_York") for m in M.meeting}
    M["video_zero_et"] = M.meeting.map(base)
    M["opening_end_et"] = M.video_zero_et + pd.to_timedelta(M.opening_end_video_s, unit="s")
    M["presser_end_et"] = M.video_zero_et + pd.to_timedelta(M.last_word_video_s, unit="s")
    M["presser_end_et_from_video_length"] = M.video_zero_et + pd.to_timedelta(M.video_duration_s, unit="s")
    M["start_uncert_lb_s"] = np.nanmax(np.c_[M.greeting_video_s, M.caption_overrun_s.clip(lower=0),
                                              M.gpt_offset_s.abs()], axis=1)
    M.loc[~M.captions.fillna(False).astype(bool), "start_uncert_lb_s"] = np.nan
    M["timing_source"] = np.where(M.captions.fillna(False).astype(bool), "vtt", "missing_no_captions")
    M["drop_P_timing"] = (M.timing_source != "vtt") | (M.start_uncert_lb_s > 30)
    M["roberta_status"] = roberta_status

    # ---------------- write ----------------
    a_cols = ["meeting", "answer_id", "answer_no", "turn_idx", "t_start_et", "t_end_et", "timing_source",
              "n_sentences", "hawk", "dove", "score", "lex_score", "question_score",
              "t_start_video_s", "t_end_video_s", "timing_uncert_s", "start_cue_dur", "end_cue_dur", "coverage",
              "n_words", "q_n_words", "q_n_sentences", "cum_mean_score", "lex_h", "lex_d", "lex_score_raw",
              "q_lex_h", "q_lex_d"]
    A = A.merge(M[["meeting", "drop_P_timing", "chair", "sample"]], on="meeting", how="left")
    A[a_cols + ["drop_P_timing", "chair", "sample"]].to_parquet(OUT / "answers.parquet", index=False)
    m_cols = ["meeting", "date", "chair", "sample", "pre2020", "unscheduled", "sep",
              "statement_score", "qa_mean_score", "H1", "n_answers", "n_answers_scorable", "n_answers_timed",
              "timing_coverage", "timing_source", "drop_P_timing", "start_uncert_lb_s",
              "statement_hawk", "statement_dove", "statement_n_sentences", "statement_score_incl_roster",
              "qa_pooled_score", "qa_mean_score_ge40w", "q_mean_score",
              "lex_statement", "lex_qa_pooled", "lex_H1", "lex_qa_mean", "lex_statement_raw", "lex_qa_pooled_raw",
              "lex_H1_raw", "lex_statement_h", "lex_statement_d", "lex_qa_h", "lex_qa_d",
              "video_zero_et", "greeting_video_s", "opening_end_et", "qa_start_et", "last_answer_end_et",
              "presser_end_et", "presser_end_et_from_video_length", "video_duration_s", "last_word_video_s",
              "caption_overrun_s", "gpt_offset_s", "gpt_n_matched", "gpt_n", "match_rate_qa", "roberta_status"]
    M[m_cols].to_parquet(OUT / "meetings.parquet", index=False)
    meta = {"roberta_status": roberta_status, "lexicon_min_hd": min_hd, "frozen_lexicon_sha256": FROZEN_SHA,
            "n_meetings": int(len(M)), "n_answers": int(len(A)),
            "n_answers_timed": int(A.t_start_video_s.notna().sum()),
            "meetings_no_captions": M.loc[M.timing_source != "vtt", "meeting"].tolist(),
            "meetings_drop_P_timing": M.loc[M.drop_P_timing, "meeting"].tolist()}
    (OUT / "build_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
