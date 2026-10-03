"""Official transcript PDF -> speaker turns -> roles (chair, moderator, reporter) and segment kinds.

Fed transcripts label every turn in capitals ("CHAIR POWELL.", "MICHELLE SMITH.", reporter names). The label
regex follows the research parse (2-4 capitalised tokens before '.' or ':'). Known typos ("CHAIRIMAN POWELL",
"CHARIMAN WARSH", "MICHELE SMITH") are caught by fuzzy matching against the expected chair and moderator labels.

The 2011-04-27 transcript labels reporters only as "QUESTION."; single-word labels QUESTION/REPORTER are accepted.
Curly quotes become straight quotes; em dashes and "--" separate words; fractions (U+00BC..U+00BE) are kept.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

LABEL_RE = re.compile(r"(?<![A-Za-z'\u2019])((?:[A-Z][A-Z'\u2019\-]+ ){1,3}[A-Z][A-Z'\u2019\-]+|QUESTION|REPORTER)"
                      r"[\.:](?=\s|$)")
# Page header "March 18, 2015 Chair Yellen's Press Conference FINAL". pypdf splits some headers oddly
# ("Powe ll's", "P ress Conference", "PressConference") and 2020-03-15 reads "Press Conference Call FINAL".
HEADER_RE = re.compile(r"[A-Z][a-z]+\.? \d{1,2}, \d{4}\s+(?:Vice )?Chair(?:man|woman)?\s+[A-Z][a-z]*(?: ?[a-z]+)?"
                       r"\S{0,2}s\s*P ?ress\s*Conference(?:\s+Call)?\s+FINAL")
FINAL_PREFIX_RE = re.compile(r"^FINAL\s+")  # a header remnant glued to the next speaker label
PAGE_RE = re.compile(r"^\s*(?:Page\s+)?\d+\s+of\s+\d+\s*$", re.M)
BRACKET_RE = re.compile(r"\[[^\]]*\]")
WORD_RE = re.compile(r"[^\s]+")


@dataclass
class Turn:
    speaker: str
    text: str
    role: str = "other"            # chair | moderator | reporter | other
    segment_kind: str = "other"    # opening | question | answer | moderator | closing | other
    qa_idx: int = -1
    words: list[str] = field(default_factory=list)

    @property
    def is_chair(self) -> bool:
        return self.role == "chair"


def pdf_text(path: Path) -> str:
    """Text of every page with page headers and page numbers removed (pypdf, pdfplumber as fallback)."""
    try:
        from pypdf import PdfReader

        pages = [p.extract_text() or "" for p in PdfReader(str(path)).pages]
    except ImportError:
        import pdfplumber

        with pdfplumber.open(str(path)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
    return "\n".join(clean_page(p) for p in pages)


def clean_page(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = HEADER_RE.sub(" ", text)
    return PAGE_RE.sub(" ", text)


def join_lines(text: str) -> str:
    """Join wrapped lines; a line ending in a hyphen or dash joins without a space."""
    out: list[str] = []
    for line in (ln.strip() for ln in text.splitlines()):
        if not line:
            continue
        if out and out[-1].endswith("-") and not out[-1].endswith(" -"):
            out[-1] += line
        else:
            out.append(line)
    return re.sub(r"\s+", " ", " ".join(out)).strip()


def repair(text: str) -> str:
    """Straight quotes and plain spaces (the PDFs use U+2019, U+201C/D and narrow no-break spaces)."""
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u202f", " "), ("\xa0", " ")):
        text = text.replace(a, b)
    return text


def split_turns(text: str) -> list[Turn]:
    """Split cleaned transcript text on speaker labels; text before the first label (the title) is dropped."""
    text = repair(join_lines(text))
    parts = LABEL_RE.split(text)
    turns = []
    for k in range(1, len(parts) - 1, 2):
        body = parts[k + 1].strip()
        speaker = FINAL_PREFIX_RE.sub("", parts[k].strip()) or parts[k].strip()
        turns.append(Turn(speaker=speaker, text=body, words=spoken_words(body)))
    return turns


def spoken_words(text: str) -> list[str]:
    """Spoken tokens: bracketed editorial insertions removed, dashes split words."""
    text = BRACKET_RE.sub(" ", text)
    text = re.sub(r"--+|\u2014|\u2013", " ", text)
    return [w for w in WORD_RE.findall(text) if re.search(r"[A-Za-z0-9\xbc-\xbe]", w)]


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def label_role(label: str, chair: str, chair_regex: str, moderator_regex: str, fuzzy: float = 0.8) -> str:
    name = chair.upper()
    m = re.match(chair_regex, label)
    if m:
        return "chair" if label.split()[-1] == name else "other"
    if max(_similar(label, f"{t} {name}") for t in ("CHAIR", "CHAIRMAN", "CHAIRWOMAN")) >= fuzzy:
        return "chair"
    if re.match(moderator_regex, label) or _similar(label, "MICHELLE SMITH") >= max(fuzzy, 0.85):
        return "moderator"
    if label.startswith(("VICE CHAIR", "GOVERNOR", "PRESIDENT")):
        return "other"
    return "reporter"


def classify(turns: list[Turn], chair: str, chair_regex: str, moderator_regex: str,
             closing_max_words: int = 25, fuzzy: float = 0.8) -> list[Turn]:
    """Assign role, segment_kind and qa_idx.

    opening  : chair turns before the first reporter turn
    question : a reporter turn (starts a new qa_idx; follow-ups get their own qa_idx)
    answer   : any later chair turn, with the qa_idx of the latest question (a turn that follows a moderator
               interjection continues the current answer)
    closing  : the final chair turn when it follows the moderator and is short
    other    : speakers labelled VICE CHAIR, GOVERNOR or PRESIDENT
    """
    qa = -1
    for t in turns:
        t.role = label_role(t.speaker, chair, chair_regex, moderator_regex, fuzzy)
        if t.role == "reporter":
            qa += 1
            t.segment_kind, t.qa_idx = "question", qa
        elif t.role == "moderator":
            t.segment_kind = "moderator"
        elif t.role == "chair":
            t.segment_kind, t.qa_idx = ("opening", -1) if qa < 0 else ("answer", qa)
    seen_reporter = qa >= 0
    chair_idx = [i for i, t in enumerate(turns) if t.is_chair]
    if chair_idx:
        last = turns[chair_idx[-1]]
        prev = next((turns[j].role for j in range(chair_idx[-1] - 1, -1, -1) if not turns[j].is_chair), "")
        if prev == "moderator" and len(last.words) <= closing_max_words and seen_reporter:
            last.segment_kind, last.qa_idx = "closing", -1
    return turns
