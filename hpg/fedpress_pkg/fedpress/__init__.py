"""FOMC press-conference feature build for HiPerGator (chair voice, face and text, stamped with known_at)."""

from __future__ import annotations

__version__ = "0.1.0"

#: Stage order. Each name is a module ``fedpress.stages.<name>`` (see fedpress/stages/__init__.py).
STAGES: tuple[str, ...] = (
    "fetch",
    "audio",
    "frames",
    "asr",
    "turns",
    "diarize",
    "voice",
    "face",
    "text",
    "aggregate",
)
