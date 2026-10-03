"""Frozen hawk/dove lexicon score. Date-only speeches usable next session open."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

import sys
from pathlib import Path as _P

sys.path.insert(0, str(_P(__file__).resolve().parent))

from config import DATA_PROC, DATA_RAW, IS_END, LEXICON, MIN_HD, NEGATION_WINDOW

HAWK = {w.strip().lower() for w in (LEXICON / "hawk.txt").read_text(encoding="utf-8").splitlines() if w.strip()}
DOVE = {w.strip().lower() for w in (LEXICON / "dove.txt").read_text(encoding="utf-8").splitlines() if w.strip()}
NEG = {"not", "no", "never", "neither", "nor", "without", "cannot", "dont", "doesnt", "didnt", "wont", "isnt", "wasnt"}
HEDGE = {"unlikely", "less", "little"}
# "no longer" handled via NEG "no" plus optional explicit bigram
RESET_PUNCT = {",", ";", "."}
RESET_WORDS = {"but", "however", "although"}
TOKEN_RE = re.compile(r"[a-z]+|[,.;]", re.I)


def tokenize(text: str) -> list[str]:
    t = text.lower().replace("'", "").replace("'", "").replace("'", "")
    t = t.replace("—", " ").replace("–", " ").replace("-", " ")
    t = t.replace("n't", "nt")
    return [m.group(0).lower() for m in TOKEN_RE.finditer(t)]


def score_tokens(tokens: list[str]) -> tuple[int, int]:
    h = d = 0
    flip_left = 0
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok in RESET_PUNCT or tok in RESET_WORDS:
            flip_left = 0
            i += 1
            continue
        # bigram hedge: no longer / no longer already covered by no
        if tok == "no" and i + 1 < n and tokens[i + 1] == "longer":
            flip_left = NEGATION_WINDOW
            i += 2
            continue
        if tok in NEG or tok in HEDGE:
            flip_left = NEGATION_WINDOW
            i += 1
            continue
        is_h = tok in HAWK
        is_d = tok in DOVE
        if is_h or is_d:
            flipped = flip_left > 0
            if is_h:
                if flipped:
                    d += 1
                else:
                    h += 1
            if is_d:
                if flipped:
                    h += 1
                else:
                    d += 1
            if flip_left > 0:
                flip_left -= 1
            i += 1
            continue
        if flip_left > 0:
            flip_left -= 1
        i += 1
    return h, d


def extract_body(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    main = (
        soup.find("div", id="content")
        or soup.find("div", class_="col-xs-12 col-sm-8 col-md-8")
        or soup.find("article")
        or soup.find("div", id="article")
        or soup.body
    )
    if main is None:
        return ""
    # drop share/print chrome
    for cls in ["share", "breadcrumb", "related", "social"]:
        for n in main.find_all(class_=re.compile(cls, re.I)):
            n.decompose()
    return main.get_text(" ", strip=True)


def main() -> None:
    idx = pd.read_csv(DATA_PROC / "speech_index.csv")
    idx["speech_date"] = pd.to_datetime(idx["speech_date"], errors="coerce")
    speech_dir = DATA_RAW / "speeches"
    rows = []
    for rec in idx.itertuples(index=False):
        path = speech_dir / f"{rec.slug}.html"
        if not path.exists():
            continue
        html = path.read_text(encoding="utf-8", errors="replace")
        body = extract_body(html)
        h, d = score_tokens(tokenize(body))
        hd = h + d
        s = (h - d) / (h + d + 1.0) if hd >= MIN_HD else float("nan")
        rows.append(
            {
                "slug": rec.slug,
                "url": rec.url,
                "speech_date": rec.speech_date,
                "title": rec.title,
                "H": h,
                "D": d,
                "HD": hd,
                "s": s,
                "kept": hd >= MIN_HD and pd.notna(rec.speech_date),
                "chars": len(body),
            }
        )
    df = pd.DataFrame(rows)
    is_end = pd.Timestamp(IS_END)
    df["speech_date"] = pd.to_datetime(df["speech_date"])
    n_dated = int(df["speech_date"].notna().sum())
    n_is = int(((df["speech_date"] <= is_end) & df["speech_date"].notna()).sum())
    n_kept = int(df["kept"].fillna(False).sum())
    df.to_csv(DATA_PROC / "speech_scores.csv", index=False)
    print(
        f"scored n_docs={len(df)} dated={n_dated} is_calendar<={IS_END}={n_is} "
        f"kept_HD>={MIN_HD}={n_kept} drop={int((~df['kept'].fillna(False)).sum())}"
    )


if __name__ == "__main__":
    main()
