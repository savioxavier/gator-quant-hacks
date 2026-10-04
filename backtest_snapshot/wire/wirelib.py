"""Shared paths and helpers for the stance-score wiring (chrono walk-forward scores -> v2 and press-conference H1)."""
from __future__ import annotations

import hashlib
import json
import sys
import os
from pathlib import Path

SCR = Path(os.environ.get("WORK_ROOT") or Path(__file__).resolve().parents[1])  # backtest_snapshot/
NLP = SCR.parent / "nlp"
DOCS_TO_SCORE = SCR.parent / "data" / "text_corpus" / "docs_to_score.parquet"
V2 = SCR / "fedspeak_v2"
PRESSER = SCR / "presser_bt"
YEARS = list(range(2015, 2027))
SEEDS = [42, 43, 44]
MAX_EPOCHS = 8
LABEL_RULE = "true"
V2_SOURCES = {"speech": "speech", "statement": "statement", "minutes": "minutes", "presser": "presser_doc"}


def chrono_module():
    """Import the team's chrono_stance.py (numpy/pandas only at import time)."""
    if str(NLP) not in sys.path:
        sys.path.insert(0, str(NLP))
    import chrono_stance as cs  # noqa: E402
    return cs


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jdump(obj, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def jload(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
