"""Independent re-implementation of the frozen hawk/dove speech score.

Rules mirrored from the reviewed third-party spec (not imported):
  * text: lower-case, drop ASCII apostrophes only (curly ones stay and split
    words), tokens are runs of a-z plus the punctuation tokens , . ;
  * lexicon: 20 hawk + 20 dove single words, exact single-token match
    (no stemming; no multi-word entries exist in the lists)
  * negation: a negator (not no never neither nor without cannot dont doesnt
    didnt wont isnt wasnt), a hedge (unlikely less little) or the bigram
    "no longer" opens a 5-token flip window; every later token, hit or not,
    uses up one slot; , . ; but however although close it at once; a hit
    inside an open window counts for the opposite side
  * score s = (H - D) / (H + D + 1), only when H + D >= 5, else NaN
  * kept = H + D >= 5 and the speech has a date
  * body = text of div#content (fallbacks below) after dropping script,
    style, nav, header, footer, noscript and any element whose class
    contains share / breadcrumb / related / social
  * date = first of p.speech-date, p.article__date, <time>, a
    "Month D, YYYY" in the first 1500 chars of the page text, else the
    YYYYMMDD in the URL slug
"""

from __future__ import annotations

import re
import os
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

# frozen strategy 01 lexicon, read as data: strategies/01/lexicon
LEX_DIR = Path(__file__).resolve().parents[2] / "lexicon"
WINDOW = 5
MIN_HITS = 5

NEGATORS = frozenset(
    "not no never neither nor without cannot dont doesnt didnt wont isnt wasnt".split()
)
HEDGES = frozenset({"unlikely", "less", "little"})
CLOSERS = frozenset({",", ";", ".", "but", "however", "although"})
_TOKEN = re.compile(r"[a-z]+|[,.;]", re.I)


def load_words(name: str) -> frozenset[str]:
    lines = (LEX_DIR / name).read_text(encoding="utf-8").splitlines()
    return frozenset(x.strip().lower() for x in lines if x.strip())


HAWK = load_words("hawk.txt")
DOVE = load_words("dove.txt")


def tokens_of(text: str) -> list[str]:
    low = text.lower().replace("'", "")
    return [t.lower() for t in _TOKEN.findall(low)]


def count_hits(toks: list[str]) -> tuple[int, int]:
    hawk = dove = 0
    left = 0  # tokens remaining in the open negation window
    k, n = 0, len(toks)
    while k < n:
        w = toks[k]
        if w in CLOSERS:
            left = 0
            k += 1
            continue
        if w == "no" and k + 1 < n and toks[k + 1] == "longer":
            left = WINDOW
            k += 2
            continue
        if w in NEGATORS or w in HEDGES:
            left = WINDOW
            k += 1
            continue
        inverted = left > 0
        if w in HAWK:
            if inverted:
                dove += 1
            else:
                hawk += 1
        if w in DOVE:
            if inverted:
                hawk += 1
            else:
                dove += 1
        if left > 0:
            left -= 1
        k += 1
    return hawk, dove


def tone(hawk: int, dove: int) -> float:
    if hawk + dove < MIN_HITS:
        return float("nan")
    return (hawk - dove) / (hawk + dove + 1.0)


_DROP_TAGS = ["script", "style", "nav", "header", "footer", "noscript"]
_DROP_CLASS = [re.compile(p, re.I) for p in ("share", "breadcrumb", "related", "social")]


def body_text(html: str) -> tuple[str, str]:
    """Return (body text, which container matched)."""
    soup = BeautifulSoup(html, "lxml")
    for el in soup(_DROP_TAGS):
        el.decompose()
    picks = [
        ("div#content", lambda: soup.find("div", id="content")),
        ("div.col-xs-12.col-sm-8.col-md-8", lambda: soup.find("div", class_="col-xs-12 col-sm-8 col-md-8")),
        ("article", lambda: soup.find("article")),
        ("div#article", lambda: soup.find("div", id="article")),
        ("body", lambda: soup.body),
    ]
    root, which = None, "none"
    for label, fn in picks:
        node = fn()
        if node:  # truthiness, as in an `a or b` chain
            root, which = node, label
            break
    if root is None:
        return "", which
    for pat in _DROP_CLASS:
        for el in root.find_all(class_=pat):
            if not el.decomposed:
                el.decompose()
    return root.get_text(" ", strip=True), which


_MONTH_DATE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},\s+20\d{2}\b"
)
_SLUG_DATE = re.compile(r"(19|20)\d{6}")


def slug_date(slug: str) -> str | None:
    m = _SLUG_DATE.search(slug)
    if not m:
        return None
    raw = m.group(0)
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def page_date(html: str, fallback: str | None) -> tuple[str | None, str]:
    """Return (YYYY-MM-DD or None, which rule produced it)."""
    soup = BeautifulSoup(html, "lxml")
    for label, node in (
        ("p.speech-date", soup.find("p", class_="speech-date")),
        ("p.article__date", soup.find("p", class_="article__date")),
        ("time", soup.find("time")),
    ):
        if node:
            dt = pd.to_datetime(node.get_text(" ", strip=True), errors="coerce")
            if pd.notna(dt):
                return dt.strftime("%Y-%m-%d"), label
    head = soup.get_text(" ", strip=True)[:1500]
    m = _MONTH_DATE.search(head)
    if m:
        dt = pd.to_datetime(m.group(0), errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d"), "text_month_date"
    return fallback, "slug"


def score_html(html: str) -> dict:
    text, which = body_text(html)
    h, d = count_hits(tokens_of(text))
    return {"H": h, "D": d, "HD": h + d, "s": tone(h, d), "chars": len(text), "container": which}
