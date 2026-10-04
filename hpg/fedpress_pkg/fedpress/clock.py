"""Media time -> wall clock -> known_at. The only place the known_at rule is implemented.

known_at (UTC) = anchor_wall_utc + (t_end_s - anchor_media_s) + timing.latency_s

* ``t_end_s`` is the end of the segment, chunk, frame or window in media seconds (video time).
* The anchor maps one media instant to one wall-clock instant (``timing.anchor``). ``turns`` writes it to
  ``turns/anchor.json``; later stages read it with :func:`load_anchor`.
* Statement-level rows use the statement release time: known_at = statement_utc + latency_s.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    import pandas as pd

    from .config import Config
    from .manifest import Meeting

ET = ZoneInfo("America/New_York")
TIMING_COLUMNS = ("t_end_utc", "known_at", "latency_s", "anchor_source", "anchor_unc_s")


def et_to_utc(d: date, hhmm: str) -> datetime:
    """Eastern local date + HH:MM (DST-aware) -> aware UTC datetime."""
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime(d.year, d.month, d.day, h, m, tzinfo=ET).astimezone(timezone.utc)


@dataclass(frozen=True)
class Anchor:
    media_s: float            # media instant (video seconds) that is anchored
    wall_utc: datetime        # wall-clock instant of that media instant (aware, UTC)
    source: str               # scheduled_start | video_zero_scheduled | anchors_csv:<source>
    uncertainty_s: float      # NaN = unknown
    rule: str

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["wall_utc"] = self.wall_utc.isoformat()
        d["uncertainty_s"] = None if math.isnan(self.uncertainty_s) else self.uncertainty_s
        return d

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "Anchor":
        unc = d.get("uncertainty_s")
        return cls(float(d["media_s"]), datetime.fromisoformat(d["wall_utc"]).astimezone(timezone.utc),
                   str(d["source"]), float("nan") if unc is None else float(unc), str(d["rule"]))

    def wall(self, t_s: float) -> datetime:
        return self.wall_utc + timedelta(seconds=float(t_s) - self.media_s)


def _csv_override(cfg: "Config", meeting: "Meeting") -> Anchor | None:
    """anchors_csv columns: presser_id, anchor_media_s, anchor_wall_utc (ISO, with offset), source, uncertainty_s."""
    path = cfg.pkg_path(str(cfg.get("manifest.anchors_csv", "manifest/anchors.csv")))
    if not path.exists():
        return None
    with path.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["presser_id"].strip() == meeting.presser_id:
                unc = (r.get("uncertainty_s") or "").strip()
                return Anchor(float(r["anchor_media_s"]),
                              datetime.fromisoformat(r["anchor_wall_utc"].strip()).astimezone(timezone.utc),
                              f"anchors_csv:{(r.get('source') or 'unknown').strip()}",
                              float(unc) if unc else float("nan"), "file")
    return None


def make_anchor(cfg: "Config", meeting: "Meeting", greeting_media_s: float | None) -> Anchor:
    """Anchor for one meeting (called by ``turns``). ``greeting_media_s`` = media time of the chair's first
    transcript words; required by the greeting rule."""
    override = _csv_override(cfg, meeting)
    if override is not None:
        return override
    rule = str(cfg.get("timing.anchor.rule"))
    unc = cfg.get("timing.anchor.default_uncertainty_s", None)
    unc_f = float("nan") if unc is None else float(unc)
    if rule == "greeting_at_scheduled":
        if greeting_media_s is None:
            raise ValueError(f"{meeting.presser_id}: greeting time unknown, cannot anchor (rule {rule})")
        return Anchor(float(greeting_media_s), meeting.presser_start_utc, "scheduled_start", unc_f, rule)
    if rule == "video_zero_at_scheduled":
        return Anchor(0.0, meeting.presser_start_utc, "video_zero_scheduled", unc_f, rule)
    raise ValueError(f"{meeting.presser_id}: no row in anchors_csv and timing.anchor.rule is 'file'")


def anchor_path(meeting_dir: Path) -> Path:
    return meeting_dir / "turns" / "anchor.json"


def save_anchor(meeting_dir: Path, anchor: Anchor) -> Path:
    from .io import atomic_write_json

    return atomic_write_json(anchor_path(meeting_dir), anchor.to_json())


def load_anchor(meeting_dir: Path) -> Anchor:
    p = anchor_path(meeting_dir)
    if not p.exists():
        raise FileNotFoundError(f"{p} missing: run the turns stage first")
    return Anchor.from_json(json.loads(p.read_text(encoding="utf-8")))


def stamp(df: "pd.DataFrame", anchor: Anchor, latency_s: float, t_end_col: str = "t_end_s") -> "pd.DataFrame":
    """Add t_end_utc, known_at, latency_s, anchor_source, anchor_unc_s from ``df[t_end_col]`` (media seconds)."""
    import pandas as pd

    out = df.copy()
    base = pd.Timestamp(anchor.wall_utc)
    t_end_utc = base + pd.to_timedelta(out[t_end_col].astype("float64") - anchor.media_s, unit="s")
    out["t_end_utc"] = t_end_utc.dt.tz_convert("UTC").astype("datetime64[us, UTC]")
    out["known_at"] = (out["t_end_utc"] + pd.to_timedelta(float(latency_s), unit="s")).astype("datetime64[us, UTC]")
    out["latency_s"] = float(latency_s)
    out["anchor_source"] = anchor.source
    out["anchor_unc_s"] = anchor.uncertainty_s
    return out


def stamp_at(df: "pd.DataFrame", when_utc: datetime, latency_s: float, source: str) -> "pd.DataFrame":
    """Stamp rows whose information appears at a fixed wall time (e.g. the statement release)."""
    import pandas as pd

    out = df.copy()
    out["t_end_utc"] = pd.Series(pd.Timestamp(when_utc), index=out.index).astype("datetime64[us, UTC]")
    out["known_at"] = (out["t_end_utc"] + pd.to_timedelta(float(latency_s), unit="s")).astype("datetime64[us, UTC]")
    out["latency_s"] = float(latency_s)
    out["anchor_source"] = source
    out["anchor_unc_s"] = 0.0
    return out
