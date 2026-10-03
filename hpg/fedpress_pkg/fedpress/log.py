"""Structured logging: one JSON object per line on stderr and, per meeting, in <root>/logs/<stage>/<id>.jsonl."""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HOST = socket.gethostname()
_JOB_KEYS = {"SLURM_JOB_ID": "job", "SLURM_ARRAY_TASK_ID": "task", "CUDA_VISIBLE_DEVICES": "gpu", "FEDPRESS_WORKER": "worker"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "host": _HOST,
            "pid": record.process,
        }
        out.update({short: os.environ[k] for k, short in _JOB_KEYS.items() if k in os.environ})
        out.update(getattr(record, "fields", {}))
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields = " ".join(f"{k}={v}" for k, v in getattr(record, "fields", {}).items())
        base = f"{datetime.now().strftime('%H:%M:%S')} {record.levelname[0]} {record.name}: {record.getMessage()} {fields}"
        return base + ("\n" + self.formatException(record.exc_info) if record.exc_info else "")


def setup(level: str = "INFO", fmt: str = "json") -> None:
    """Configure the root ``fedpress`` logger once per process (stderr only)."""
    root = logging.getLogger("fedpress")
    root.setLevel(level.upper())
    root.propagate = False
    if not any(getattr(h, "_fedpress", False) for h in root.handlers):
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(JsonFormatter() if fmt == "json" else TextFormatter())
        h._fedpress = True  # type: ignore[attr-defined]
        root.addHandler(h)


class Log:
    """Event logger with bound context: ``log.info("asr.done", rows=812, elapsed_s=41.2)``."""

    def __init__(self, name: str, file: Path | None = None, **context: Any) -> None:
        self._logger = logging.getLogger(f"fedpress.{name}")
        self._context = context
        self._file = file
        if file is not None:
            file.parent.mkdir(parents=True, exist_ok=True)

    def bind(self, **context: Any) -> "Log":
        return Log(self._logger.name.removeprefix("fedpress."), self._file, **{**self._context, **context})

    def _emit(self, level: int, event: str, exc: bool, fields: dict[str, Any]) -> None:
        merged = {**self._context, **fields}
        self._logger.log(level, event, extra={"fields": merged}, exc_info=exc)
        if self._file is not None and self._logger.isEnabledFor(level):
            rec = logging.LogRecord(self._logger.name, level, "", 0, event, None, sys.exc_info() if exc else None)
            rec.fields = merged  # type: ignore[attr-defined]
            with self._file.open("a", encoding="utf-8") as fh:
                fh.write(JsonFormatter().format(rec) + "\n")

    def debug(self, event: str, **fields: Any) -> None:
        self._emit(logging.DEBUG, event, False, fields)

    def info(self, event: str, **fields: Any) -> None:
        self._emit(logging.INFO, event, False, fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._emit(logging.WARNING, event, False, fields)

    def error(self, event: str, exc: bool = False, **fields: Any) -> None:
        self._emit(logging.ERROR, event, exc, fields)
