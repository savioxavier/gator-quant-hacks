"""Download Board of Governors speech index pages and speech HTML. IS cut 2024-10-02."""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

import sys
from pathlib import Path as _P

sys.path.insert(0, str(_P(__file__).resolve().parent))

from config import (
    BOARD_BASE,
    BOARD_INDEX,
    DATA_PROC,
    DATA_RAW,
    IS_END,
    SPEECH_YEAR0,
    SPEECH_YEAR1,
    UA,
)

HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}


def fetch(url: str, dest: Path | None = None, retries: int = 4) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True) if dest is not None else None
    if dest is not None and dest.exists() and dest.stat().st_size > 200:
        return dest.read_text(encoding="utf-8", errors="replace")
    last_err = None
    for i in range(retries):
        try:
            r = requests.get(url, timeout=45, headers=HEADERS)
            r.raise_for_status()
            text = r.text
            if dest is not None:
                dest.write_text(text, encoding="utf-8")
            return text
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"fetch failed {url}: {last_err}")


DATE_IN_URL = re.compile(r"(19|20)\d{6}")
SPEECH_HREF = re.compile(
    r'href=["\'](/newsevents/speech/[^"\']+\.htm)["\']',
    re.I,
)


def parse_index(html: str, year: int) -> list[dict]:
    rows = []
    soup = BeautifulSoup(html, "lxml")
    seen = set()
    # Prefer structured list items if present
    for a in soup.find_all("a", href=True):
        href = a["href"].split("#")[0]
        if "/newsevents/speech/" not in href:
            continue
        if not href.endswith(".htm"):
            continue
        if "speeches.htm" in href or href.endswith("-speeches.htm"):
            continue
        if href in seen:
            continue
        seen.add(href)
        url = href if href.startswith("http") else BOARD_BASE + href
        slug = href.rstrip("/").split("/")[-1].replace(".htm", "")
        m = DATE_IN_URL.search(slug) or DATE_IN_URL.search(href)
        date = None
        if m:
            raw = m.group(0)
            date = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
        title = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        rows.append({"year": year, "url": url, "slug": slug, "html_date": date, "title": title})
    if rows:
        return rows
    # Fallback regex
    for href in SPEECH_HREF.findall(html):
        if "speeches.htm" in href:
            continue
        url = BOARD_BASE + href
        slug = href.rstrip("/").split("/")[-1].replace(".htm", "")
        m = DATE_IN_URL.search(slug)
        date = None
        if m:
            raw = m.group(0)
            date = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
        rows.append({"year": year, "url": url, "slug": slug, "html_date": date, "title": ""})
    return rows


def page_date(html: str, fallback: str | None) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    for sel in [
        {"name": "p", "class_": "speech-date"},
        {"name": "p", "class_": "article__date"},
        {"name": "time"},
    ]:
        node = soup.find(**sel) if "class_" in sel else soup.find(sel["name"])
        if node:
            txt = node.get_text(" ", strip=True)
            dt = pd.to_datetime(txt, errors="coerce")
            if pd.notna(dt):
                return dt.strftime("%Y-%m-%d")
    # "Month DD, YYYY" near top
    text = soup.get_text(" ", strip=True)[:1500]
    m = re.search(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+20\d{2}\b",
        text,
    )
    if m:
        dt = pd.to_datetime(m.group(0), errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d")
    return fallback


def main() -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    DATA_PROC.mkdir(parents=True, exist_ok=True)
    idx_dir = DATA_RAW / "indexes"
    speech_dir = DATA_RAW / "speeches"
    all_rows: list[dict] = []
    for year in range(SPEECH_YEAR0, SPEECH_YEAR1 + 1):
        url = BOARD_INDEX.format(year=year)
        html = fetch(url, idx_dir / f"{year}.html")
        rows = parse_index(html, year)
        print(f"index {year}: {len(rows)} links")
        all_rows.extend(rows)

    # Dedup by slug
    by_slug: dict[str, dict] = {}
    for r in all_rows:
        by_slug[r["slug"]] = r
    items = list(by_slug.values())

    def one(row: dict) -> dict:
        dest = speech_dir / f"{row['slug']}.html"
        try:
            html = fetch(row["url"], dest)
            row = dict(row)
            row["speech_date"] = page_date(html, row.get("html_date"))
            row["bytes"] = len(html)
            row["error"] = ""
            return row
        except Exception as e:
            row = dict(row)
            row["speech_date"] = row.get("html_date")
            row["bytes"] = 0
            row["error"] = str(e)
            return row

    out = []
    n = len(items)
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(one, r) for r in items]
        done = 0
        for fut in as_completed(futs):
            out.append(fut.result())
            done += 1
            if done % 50 == 0:
                print(f"downloaded {done}/{n}")

    df = pd.DataFrame(out)
    df["speech_date"] = pd.to_datetime(df["speech_date"], errors="coerce")
    is_end = pd.Timestamp(IS_END)
    df["in_is_calendar"] = df["speech_date"] <= is_end
    df = df.sort_values(["speech_date", "slug"])
    path = DATA_PROC / "speech_index.csv"
    df.to_csv(path, index=False)
    print(f"wrote {path} n={len(df)} dated={(df['speech_date'].notna().sum())} is_cal={int(df['in_is_calendar'].sum())}")


if __name__ == "__main__":
    main()
