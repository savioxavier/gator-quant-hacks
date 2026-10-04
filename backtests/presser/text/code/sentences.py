"""Step 3a: sentence units for FOMC-RoBERTa (chair answers, reporter questions, opening, same-day statement).

Sentence rule (fixed before any classification; same rule as the team's fedspeak_v2 scorer):
  * stage directions removed: [Laughter], [Cough], [Inaudible], [No response], [extended pause], [pause],
    [crosstalk], [applause]
  * nltk.sent_tokenize (Punkt, English); whitespace collapsed
  * a unit is kept if it has >= 3 alphabetic words of 2+ letters
  * statement: Board press-release body (fomc_docs.parquet `text_core`), split on paragraphs first; the voting
    roster sentence(s) ('Voting for ...') are flagged roster=True and excluded from the primary statement score
    ('Voting against ... who preferred ...' sentences are kept: they carry stance).
  * the opening statement is split and stored (role=opening) but is excluded from every Q&A score (plan).
Questions for H1-Q: all reporter turns between the previous chair turn and the answer (moderator turns excluded).

Output: sentences.parquet (unit_id, meeting, doc, answer_id, turn_idx, sent_idx, roster, sentence)
        answer_map.parquet (meeting, answer_id, turn_idx, answer_text, question_text, n_words)
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import nltk
import pandas as pd

OUT = Path(__file__).resolve().parents[1]
SCR = Path(os.environ.get("WORK_ROOT") or "WORK_ROOT_not_set")  # the original work root (text-build inputs, not in git)
nltk.data.path.insert(0, str(SCR / "fedspeak_v2/venv/nltk_data"))
from nltk.tokenize import sent_tokenize  # noqa: E402

FOMC_DOCS = SCR / "fedspeak_v2/corpus/fomc_docs.parquet"
STAGE = re.compile(r"\[\s*(?:laughter|cough|inaudible|no response|extended pause|pause|crosstalk|applause)\s*\]", re.I)
WORD = re.compile(r"[A-Za-z]{2,}")


def units(text: str) -> list[str]:
    out = []
    for para in re.split(r"\n+", text or ""):
        p = " ".join(STAGE.sub(" ", para).split())
        if not p:
            continue
        for s in sent_tokenize(p):
            s = " ".join(s.split())
            if len(WORD.findall(s)) >= 3:
                out.append(s)
    return out


def main() -> None:
    turns = pd.read_parquet(OUT / "turns.parquet").sort_values(["meeting", "turn_idx"])
    rows, amap = [], []
    for m, g in turns.groupby("meeting", sort=True):
        qbuf, k = [], 0
        for t in g.itertuples(index=False):
            if t.role == "question":
                qbuf.append(t.text)
            elif t.role == "opening":
                for i, s in enumerate(units(t.text)):
                    rows.append(dict(meeting=m, doc="opening", answer_id=None, turn_idx=t.turn_idx, sent_idx=i,
                                     roster=False, sentence=s))
                qbuf = []
            elif t.role == "answer":
                aid = f"{m}_a{k:02d}"
                k += 1
                qtext = "\n".join(qbuf)
                amap.append(dict(meeting=m, answer_id=aid, turn_idx=t.turn_idx, answer_text=t.text,
                                 question_text=qtext, n_words=t.n_words, q_n_words=len(qtext.split())))
                for i, s in enumerate(units(t.text)):
                    rows.append(dict(meeting=m, doc="answer", answer_id=aid, turn_idx=t.turn_idx, sent_idx=i,
                                     roster=False, sentence=s))
                for i, s in enumerate(units(qtext)):
                    rows.append(dict(meeting=m, doc="question", answer_id=aid, turn_idx=t.turn_idx, sent_idx=i,
                                     roster=False, sentence=s))
                qbuf = []
    meetings = sorted(turns.meeting.unique())
    fd = pd.read_parquet(FOMC_DOCS)
    st = fd[fd.doc_type == "statement"].copy()
    st["meeting"] = pd.to_datetime(st.date).dt.strftime("%Y%m%d")
    st = st[st.meeting.isin(meetings)]
    assert st.meeting.nunique() == len(meetings) and len(st) == len(meetings), "statement missing or duplicated"
    for r in st.itertuples(index=False):
        for i, s in enumerate(units(r.text_core)):
            rows.append(dict(meeting=r.meeting, doc="statement", answer_id=None, turn_idx=-1, sent_idx=i,
                             roster=bool(re.match(r"^Voting for\b", s)), sentence=s))
    S = pd.DataFrame(rows)
    S.insert(0, "unit_id", range(len(S)))
    S.to_parquet(OUT / "sentences.parquet", index=False)
    pd.DataFrame(amap).to_parquet(OUT / "answer_map.parquet", index=False)
    st[["meeting", "doc_id", "url", "release_time", "release_ts_et", "text_core"]].to_parquet(
        OUT / "statements.parquet", index=False)
    print(S.groupby("doc").size().to_string())
    print("roster sentences", int(S.roster.sum()), "nltk", nltk.__version__)


if __name__ == "__main__":
    main()
