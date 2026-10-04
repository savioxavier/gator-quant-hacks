"""Read manifest/pressers.csv (one row per held presser) and select meetings for a stage run."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .clock import et_to_utc
from .config import Config, ConfigError


def _int(v: str) -> int | None:
    return int(v) if v.strip() else None


def _float(v: str) -> float | None:
    return float(v) if v.strip() else None


def _bool(v: str) -> bool:
    return v.strip().lower() == "true"


@dataclass(frozen=True, slots=True)
class Meeting:
    presser_id: str           # YYYYMMDD of the presser, as in FOMCpresconfYYYYMMDD.pdf
    meeting_date: date        # last day of the policy meeting (2020-03-03 presser -> 2020-03-02)
    meeting_start_date: date
    presser_date: date
    chair: str                # Bernanke | Yellen | Powell | Warsh
    scheduled: bool
    sep: bool
    statement_time_et: str    # HH:MM, scheduled release
    presser_start_et: str     # HH:MM, scheduled (nominal) start
    statement_url: str
    fed_page_url: str
    transcript_pdf_url: str
    transcript_pdf_bytes: int | None
    has_vtt: bool
    vtt_bytes: int | None
    brightcove_account_id: str
    brightcove_video_id: str
    mp4_width: int | None
    mp4_height: int | None
    mp4_bytes: int | None     # expected download size (HEAD Content-Length at manifest build)
    mp4_rule: str
    duration_s: float | None
    local_pdf_path: str       # relative to manifest.local_seed_dir; may be absent on HiPerGator
    local_vtt_path: str
    local_pdf_sha256: str
    local_vtt_sha256: str
    notes: str
    sample_role: str          # study | calibration | outside (from the config windows)

    @property
    def calibration_only(self) -> bool:
        """2011-2015 calibration pressers (plan_v0): processed only when sample.include_calibration."""
        return self.sample_role == "calibration"

    @property
    def statement_utc(self) -> datetime:
        return et_to_utc(self.presser_date, self.statement_time_et)

    @property
    def presser_start_utc(self) -> datetime:
        return et_to_utc(self.presser_date, self.presser_start_et)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _role(cfg: Config, d: date) -> str:
    for role, key in (("study", "study_window"), ("calibration", "calibration_window")):
        start = date.fromisoformat(str(cfg.get(f"sample.{key}.start")))
        end = date.fromisoformat(str(cfg.get(f"sample.{key}.end")))
        if start <= d <= end:
            return role
    return "outside"


def load(cfg: Config) -> list[Meeting]:
    """All manifest rows, sorted by presser date."""
    path = cfg.pkg_path(str(cfg.get("manifest.pressers_csv")))
    with Path(path).open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        pdate = date.fromisoformat(r["presser_date"])
        out.append(
            Meeting(
                presser_id=r["presser_id"].strip(),
                meeting_date=date.fromisoformat(r["meeting_date"]),
                meeting_start_date=date.fromisoformat(r["meeting_start_date"]),
                presser_date=pdate,
                chair=r["chair"].strip(),
                scheduled=_bool(r["scheduled"]),
                sep=_bool(r["sep"]),
                statement_time_et=r["statement_time_et"].strip(),
                presser_start_et=r["presser_start_et"].strip(),
                statement_url=r["statement_url"].strip(),
                fed_page_url=r["fed_page_url"].strip(),
                transcript_pdf_url=r["transcript_pdf_url"].strip(),
                transcript_pdf_bytes=_int(r["transcript_pdf_bytes"]),
                has_vtt=bool(r["vtt_bytes"].strip()),
                vtt_bytes=_int(r["vtt_bytes"]),
                brightcove_account_id=r["brightcove_account_id"].strip(),
                brightcove_video_id=r["brightcove_video_id"].strip(),
                mp4_width=_int(r["mp4_width"]),
                mp4_height=_int(r["mp4_height"]),
                mp4_bytes=_int(r["mp4_bytes"]),
                mp4_rule=r["mp4_rule"].strip(),
                duration_s=_float(r["duration_s"]),
                local_pdf_path=r.get("local_pdf_path", "").strip(),
                local_vtt_path=r.get("local_vtt_path", "").strip(),
                local_pdf_sha256=r.get("local_pdf_sha256", "").strip(),
                local_vtt_sha256=r.get("local_vtt_sha256", "").strip(),
                notes=r.get("notes", "").strip(),
                sample_role=_role(cfg, pdate),
            )
        )
    return sorted(out, key=lambda m: m.presser_date)


def sample(cfg: Config, meetings: list[Meeting] | None = None) -> list[Meeting]:
    """The configured sample: study window, plus calibration if enabled, plus include, minus exclude."""
    meetings = load(cfg) if meetings is None else meetings
    include = {str(x) for x in cfg.get("sample.include", []) or []}
    exclude = {str(x) for x in cfg.get("sample.exclude", []) or []}
    roles = {"study", "calibration"} if cfg.get("sample.include_calibration", False) else {"study"}
    return [m for m in meetings if (m.sample_role in roles or m.presser_id in include) and m.presser_id not in exclude]


def select(
    cfg: Config,
    *,
    index: int | None = None,
    on_date: str | None = None,
    presser_id: str | None = None,
    all_: bool = False,
    shard: tuple[int, int] | None = None,
) -> list[Meeting]:
    """Meetings for one CLI call. ``index`` counts within the sample (0-based, by date); ``on_date`` matches the
    presser date or the meeting date; ``presser_id`` and ``on_date`` may pick meetings outside the sample."""
    meetings = load(cfg)
    if sum(x is not None and x is not False for x in (index, on_date, presser_id, all_ or None)) != 1:
        raise ConfigError("choose exactly one of --index, --date, --id, --all")
    if all_:
        chosen = sample(cfg, meetings)
    elif index is not None:
        smp = sample(cfg, meetings)
        if not 0 <= index < len(smp):
            raise ConfigError(f"--index {index} outside the sample (0..{len(smp) - 1}); see `list`")
        chosen = [smp[index]]
    elif on_date is not None:
        d = date.fromisoformat(on_date)
        chosen = [m for m in meetings if d in (m.presser_date, m.meeting_date)]
        if not chosen:
            raise ConfigError(f"no presser on {on_date}")
    else:
        chosen = [m for m in meetings if m.presser_id == str(presser_id)]
        if not chosen:
            raise ConfigError(f"no presser with id {presser_id}")
    if shard is not None:
        i, n = shard
        chosen = [m for k, m in enumerate(chosen) if k % n == i]
    return chosen


def load_calendar(cfg: Config) -> list[dict[str, str]]:
    """manifest/meetings.csv rows (all policy meetings, with has_presser), e.g. for the 88-meeting panel."""
    path = cfg.pkg_path(str(cfg.get("manifest.meetings_csv")))
    with Path(path).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))
