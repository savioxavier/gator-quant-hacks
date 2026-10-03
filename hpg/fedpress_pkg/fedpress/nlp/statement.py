"""FOMC statement text from the Board's press-release page (raw/statement.html, saved by ``fetch``).

The page holds the statement as plain ``<p>`` elements inside ``<div id="article">``; dated and release-time
paragraphs carry a class and are skipped. Paragraphs from the vote record on (``text.statement.stop_regex``)
are not part of the policy text.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from .split import normalise


class _ArticleParagraphs(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0            # div depth inside the article (0 = outside)
        self.in_p = False
        self.skip_p = False
        self.buf: list[str] = []
        self.paragraphs: list[str] = []
        self.any_paragraphs: list[str] = []   # fallback when the page has no article div

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "div":
            if self.depth:
                self.depth += 1
            elif a.get("id") == "article":
                self.depth = 1
        elif tag == "p":
            self.in_p, self.skip_p, self.buf = True, bool(a.get("class")), []
        elif tag in ("br",) and self.in_p:
            self.buf.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self.depth:
            self.depth -= 1
        elif tag == "p" and self.in_p:
            text = normalise("".join(self.buf))
            if text and not self.skip_p:
                (self.paragraphs if self.depth else self.any_paragraphs).append(text)
            self.in_p = False

    def handle_data(self, data: str) -> None:
        if self.in_p:
            self.buf.append(data)


def statement_paragraphs(html: str, stop_regex: str) -> list[str]:
    """Policy paragraphs of the statement, in order, up to (not including) the first stop paragraph."""
    p = _ArticleParagraphs()
    p.feed(html)
    paras = p.paragraphs or p.any_paragraphs
    stop = re.compile(stop_regex, re.IGNORECASE)
    out: list[str] = []
    for para in paras:
        if stop.search(para):
            break
        out.append(para)
    return out
