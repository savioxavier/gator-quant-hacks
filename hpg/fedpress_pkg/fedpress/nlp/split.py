"""Pinned sentence splitter and word tokens (amendment A-10: the splitter is fixed in code and versioned).

``SPLITTER_ID`` is written on every sentence row; change it whenever a rule below changes, so outputs made
with different rules can never be mixed silently.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

SPLITTER_ID = "fedpress-regex-1"

# Tokens that end with a period without ending a sentence (lower case, without the final period).
_ABBREV = frozenset({
    "mr", "mrs", "ms", "dr", "prof", "st", "jr", "sr", "vs", "etc", "e.g", "i.e", "u.s", "u.k", "u.n", "no", "nos",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec", "inc", "corp", "co",
    "ltd", "gov", "sen", "rep", "a.m", "p.m", "fig", "approx", "cf", "al", "op", "ed", "vol", "pp", "dept",
})
_BOUNDARY = re.compile(r"[.?!]+[\"'”’)\]]*(?=\s+[\"'“‘(\[]*[A-Z0-9])")
_TOKEN = re.compile(r"\S+")
_WORDLIKE = re.compile(r"[A-Za-z0-9]")
_TRANSLATE = {0x00A0: " ", 0x202F: " ", 0x2011: "-", 0x2010: "-", 0x2013: "--", 0x2014: "--", 0x2018: "'",
              0x2019: "'", 0x201C: '"', 0x201D: '"', 0x2026: "...", 0xFFFD: "?"}


@dataclass(frozen=True)
class Span:
    start: int   # character offsets into the normalised text
    end: int
    text: str


def normalise(text: str) -> str:
    """NFKC, typographic punctuation to ASCII, collapsed whitespace."""
    t = unicodedata.normalize("NFKC", text).translate(_TRANSLATE)
    return re.sub(r"\s+", " ", t).strip()


def _is_abbrev(text: str, dot: int) -> bool:
    """True when the period at ``dot`` closes an abbreviation or an initial (``H.`` in ``Jerome H. Powell``)."""
    j = dot
    while j > 0 and not text[j - 1].isspace():
        j -= 1
    tok = text[j:dot].lstrip("(\"'[").lower()
    return tok in _ABBREV or (len(tok) == 1 and tok.isalpha())


def split_sentences(text: str) -> list[Span]:
    """Split normalised text into sentences. A boundary is [.?!] (plus closing quotes/brackets) followed by
    whitespace and an upper-case letter, digit or opening quote; abbreviations and initials are not boundaries."""
    out: list[Span] = []
    start = 0
    for m in _BOUNDARY.finditer(text):
        if text[m.start()] == "." and m.group(0).rstrip("\"')]") == "." and _is_abbrev(text, m.start()):
            continue
        end = m.end()
        seg = text[start:end].strip()
        if seg:
            s = start + (len(text[start:end]) - len(text[start:end].lstrip()))
            out.append(Span(s, s + len(seg), seg))
        start = end
    seg = text[start:].strip()
    if seg:
        s = start + (len(text[start:]) - len(text[start:].lstrip()))
        out.append(Span(s, s + len(seg), seg))
    return out


def tokens(text: str) -> list[tuple[int, int]]:
    """Whitespace tokens as (start, end) character offsets (the transcript word convention)."""
    return [(m.start(), m.end()) for m in _TOKEN.finditer(text)]


_BRACKET = re.compile(r"\[[^\]]*\]")
_DASHES = re.compile(r"--+|—|–")
_SPOKEN = re.compile(r"[A-Za-z0-9\xbc-\xbe]")


def spoken_tokens(text: str) -> list[tuple[int, int]]:
    """Token offsets under the ``turns`` word rule (bracketed editorial insertions dropped, dashes split words,
    tokens need a letter, digit or fraction), so sentence k maps onto the same rows of turns/words.parquet."""
    masked = _BRACKET.sub(lambda m: " " * len(m.group(0)), text)
    masked = _DASHES.sub(lambda m: " " * len(m.group(0)), masked)
    return [(m.start(), m.end()) for m in _TOKEN.finditer(masked) if _SPOKEN.search(m.group(0))]


def n_words(text: str) -> int:
    """Whitespace tokens that contain a letter or digit."""
    return sum(1 for m in _TOKEN.finditer(text) if _WORDLIKE.search(m.group(0)))


def splitter_info(name: str) -> dict[str, str]:
    """Identifier and version of the configured splitter (recorded on rows and in the done-marker)."""
    if name in ("fedpress_regex", SPLITTER_ID):
        return {"splitter": SPLITTER_ID}
    if name == "nltk_punkt":
        import nltk

        return {"splitter": f"nltk-punkt-{nltk.__version__}"}
    raise ValueError(f"unknown text.sentences.splitter {name!r} (fedpress_regex | nltk_punkt)")


def make_splitter(name: str):
    """Callable text -> list[Span] for the configured splitter."""
    if name in ("fedpress_regex", SPLITTER_ID):
        return split_sentences
    if name == "nltk_punkt":
        from nltk.tokenize import PunktSentenceTokenizer

        tok = PunktSentenceTokenizer()

        def _punkt(text: str) -> list[Span]:
            return [Span(a, b, text[a:b]) for a, b in tok.span_tokenize(text)]

        return _punkt
    raise ValueError(f"unknown text.sentences.splitter {name!r} (fedpress_regex | nltk_punkt)")
