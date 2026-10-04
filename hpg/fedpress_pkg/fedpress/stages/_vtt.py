"""WebVTT captions -> cues -> timed words.

The Fed's caption tracks are a forced alignment of the official transcript, speaker labels included, with
cue-level times (cues of about 1-4 s). Word times inside a cue are spread by character count.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TIME_RE = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2}(?:[.,]\d{1,3})?)")
ARROW_RE = re.compile(r"^\s*(\S+)\s+-->\s+(\S+)")
TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


def ts(value: str) -> float:
    m = TIME_RE.fullmatch(value.strip())
    if not m:
        raise ValueError(f"bad WebVTT timestamp {value!r}")
    h, mnt, sec = m.group(1), m.group(2), m.group(3).replace(",", ".")
    return (int(h) if h else 0) * 3600 + int(mnt) * 60 + float(sec)


def parse(text: str) -> tuple[list[Cue], dict[str, str]]:
    """Cues and header fields (e.g. X-TIMESTAMP-MAP) of a WebVTT document."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    blocks = re.split(r"\n\s*\n", text)
    header: dict[str, str] = {}
    for line in blocks[0].splitlines()[1:]:
        if ":" in line or "=" in line:
            k, _, v = line.partition("=" if "=" in line.split(":")[0] else ":")
            header[k.strip()] = v.strip()
    cues = []
    for block in blocks[1:]:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if idx is None:
            continue  # NOTE / STYLE / REGION blocks
        m = ARROW_RE.match(lines[idx])
        if not m:
            continue
        body = " ".join(TAG_RE.sub("", ln).strip() for ln in lines[idx + 1:])
        cues.append(Cue(ts(m.group(1)), ts(m.group(2)), re.sub(r"\s+", " ", body).strip()))
    return cues, header


def read(path: Path) -> tuple[list[Cue], dict[str, str]]:
    return parse(path.read_text(encoding="utf-8", errors="replace"))


def timed_words(cues: list[Cue]) -> list[tuple[str, float, float]]:
    """(word, start, end) for every whitespace token; a cue's span is shared out by character count."""
    out: list[tuple[str, float, float]] = []
    for c in cues:
        toks = c.text.replace("--", " -- ").split()
        toks = [t for t in toks if t != "--"]
        if not toks:
            continue
        weights = [len(t) + 1 for t in toks]
        total, acc = float(sum(weights)), 0.0
        span = max(0.0, c.end - c.start)
        for t, w in zip(toks, weights):
            a = c.start + span * acc / total
            acc += w
            out.append((t, a, c.start + span * acc / total))
    return out
