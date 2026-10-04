"""Parse a Board year speech-list page into rows (all /newsevents/speech/*.htm links)."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from fedscore import slug_date

BASE = "https://www.federalreserve.gov"


def parse_year(html: str, year: int) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"].split("#")[0]
        if "/newsevents/speech/" not in href or not href.endswith(".htm"):
            continue
        if "speeches.htm" in href:
            continue
        if href in seen:
            continue
        seen.add(href)
        slug = href.rstrip("/").split("/")[-1].replace(".htm", "")
        out.append(
            {
                "year": year,
                "url": href if href.startswith("http") else BASE + href,
                "slug": slug,
                "html_date": slug_date(slug) or slug_date(href),
                "title": re.sub(r"\s+", " ", a.get_text(" ", strip=True)),
                "speaker_listed": _speaker_near(a),
            }
        )
    return out


def _speaker_near(a) -> str:
    """Speaker line printed under the link on the list page (diagnostic only)."""
    block = a.find_parent("div")
    if block is None:
        return ""
    sp = block.find("p", class_="news__speaker")
    return sp.get_text(" ", strip=True) if sp else ""
