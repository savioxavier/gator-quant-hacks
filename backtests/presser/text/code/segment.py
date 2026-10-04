"""Step 1: transcript cleaning and turn segmentation for the 75 press conferences 2016-03-16..2026-09-16.

Input : transcripts_utf8/FOMCpresconfYYYYMMDD.txt  (pdftotext 4.06 -enc UTF-8 of the official Board PDFs)
Output: turns.parquet  (meeting, turn_idx, speaker, role, text, n_words)
        segment_log.json (removed footnotes, label inventory, per-meeting counts)

Rules (fixed before any scoring):
  * page furniture removed: 'Page N of M', the date line, '<Chair X>'s Press Conference[ Call]', 'FINAL',
    the 'Transcript of ...' title line.
  * editorial footnotes removed: lines directly above a 'Page N of M' footer that start with a footnote number and
    a capital letter (e.g. '1 Chair Powell intended to say ...'); footnote calls glued to text ('rate.1 The') removed.
  * speaker labels: 2-4 all-caps tokens followed by '.' or ':' and whitespace (e.g. 'CHAIR POWELL.',
    'MICHELLE SMITH.'), anywhere in the text.
  * role: chair = 'CHAIR <SURNAME>' / 'CHAIRMAN <SURNAME>' incl. PDF typos ('CHARIMAN WARSH');
    moderator = 'MICHELLE SMITH' (Board press office) incl. typos ('MICHELLE SMTH', 'MICHELE SMITH');
    everything else = reporter (question).
  * opening statement = the chair's turns before the first non-chair turn (excluded from Q&A per the plan).
  * answers = every chair turn after the first non-chair turn.
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[1]
SRC = OUT / "transcripts_utf8"

PAGE = re.compile(r"^Page \d+ of \d+$")
DATE_LINE = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}$")
CONF_LINE = re.compile(r"^(Chair|Chairman) [A-Z][a-z]+[’']s Press ?Conference( Call)?$")
TITLE_LINE = re.compile(r"^Transcript of (Chair|Chairman) [A-Z][a-z]+[’']s Press Conference( Call)?\b.*$")
FOOTNOTE = re.compile(r"^\d{1,2} [A-Z“\"]")
FNCALL = re.compile(r"(?<=[a-z\)”\"’])([.;,?!])\d{1,2}(?=\s|$)")
LABEL = re.compile(r"(?<![A-Za-z'’])((?:[A-Z][A-Z'’\-]+ ){1,3}[A-Z][A-Z'’\-]+)[.:](?=\s)")
MODERATOR = "MICHELLE SMITH"
CHAIRS = ("POWELL", "YELLEN", "WARSH")


def is_moderator(spk: str) -> bool:
    # label typos in the official PDFs: 'MICHELLE SMTH', 'MICHELE SMITH'
    return difflib.SequenceMatcher(None, spk, MODERATOR).ratio() >= 0.85


def is_chair(spk: str) -> bool:
    # 'CHAIR X', 'CHAIRMAN X' and PDF typos such as 'CHARIMAN WARSH', 'CHAIRIMAN POWELL', 'CHAIMRAN POWELL'
    tok = spk.split()
    return len(tok) == 2 and tok[1] in CHAIRS and tok[0].startswith("CH") and         difflib.SequenceMatcher(None, tok[0], "CHAIRMAN").ratio() >= 0.7
# all-caps phrases that can end a sentence but are not speakers (checked against the label inventory)
NOT_LABELS: set[str] = set()


def clean(raw: str) -> tuple[str, list[str]]:
    lines = [ln.strip() for ln in raw.replace("\r", "").replace("\f", "\n").split("\n")]
    removed = []
    keep = [True] * len(lines)
    for i, ln in enumerate(lines):
        if PAGE.match(ln):
            keep[i] = False
            j = i - 1
            while j >= 0 and (not lines[j] or FOOTNOTE.match(lines[j])):
                if lines[j] and FOOTNOTE.match(lines[j]):
                    keep[j] = False
                    removed.append(lines[j])
                j -= 1
        elif DATE_LINE.match(ln) or CONF_LINE.match(ln) or ln == "FINAL" or TITLE_LINE.match(ln):
            keep[i] = False
    body = " ".join(ln for ln, k in zip(lines, keep) if k and ln)
    body = FNCALL.sub(r"\1", body)
    body = re.sub(r"\s+", " ", body).strip()
    return body, removed


def segment(meeting: str, body: str) -> list[dict]:
    parts = LABEL.split(body)
    turns = []
    pre = parts[0].strip()
    for k in range(1, len(parts) - 1, 2):
        spk = parts[k].strip()
        if spk in NOT_LABELS:
            # glue back into the previous turn
            if turns:
                turns[-1]["text"] += " " + spk + ". " + parts[k + 1].strip()
            continue
        turns.append({"meeting": meeting, "speaker": spk, "text": parts[k + 1].strip()})
    seen_other = False
    for i, t in enumerate(turns):
        t["turn_idx"] = i
        t["label_raw"] = t["speaker"]
        if is_chair(t["speaker"]):
            t["role"] = "answer" if seen_other else "opening"
        elif is_moderator(t["speaker"]):
            t["role"] = "moderator"
            seen_other = True
        else:
            t["role"] = "question"
            seen_other = True
        t["n_words"] = len(t["text"].split())
    if pre:
        turns.insert(0, {"meeting": meeting, "speaker": "", "label_raw": "", "text": pre, "turn_idx": -1,
                         "role": "preamble", "n_words": len(pre.split())})
    return turns


def main() -> None:
    rows, log = [], {"footnotes_removed": {}, "labels": {}, "per_meeting": {}}
    for p in sorted(SRC.glob("FOMCpresconf*.txt")):
        m = re.search(r"(\d{8})", p.name).group(1)
        body, removed = clean(p.read_text(encoding="utf-8"))
        if removed:
            log["footnotes_removed"][m] = removed
        turns = segment(m, body)
        rows += turns
        roles = pd.Series([t["role"] for t in turns]).value_counts().to_dict()
        log["per_meeting"][m] = {"chair": next((t["speaker"] for t in turns if t["role"] == "opening"), None), **roles}
        for t in turns:
            log["labels"][t["speaker"]] = log["labels"].get(t["speaker"], 0) + 1
    df = pd.DataFrame(rows)[["meeting", "turn_idx", "speaker", "role", "text", "n_words"]]
    chair_of = df[df.role == "opening"].set_index("meeting").speaker
    bad = df[(df.role == "answer") & (df.speaker != df.meeting.map(chair_of))]
    log["chair_label_variants"] = bad.groupby(["meeting", "speaker"]).size().reset_index().values.tolist()
    df.to_parquet(OUT / "turns.parquet", index=False)
    log["labels"] = dict(sorted(log["labels"].items(), key=lambda kv: -kv[1]))
    (OUT / "segment_log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    print("meetings", df.meeting.nunique(), "turns", len(df))
    print(df.role.value_counts().to_string())


if __name__ == "__main__":
    main()
