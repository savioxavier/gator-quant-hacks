#!/usr/bin/env python3
"""Build manifest/pressers.csv (one row per FOMC press conference) and manifest/meetings.csv (one row per
FOMC meeting listed by the Board).

Sources, all public: the Board's listing pages (fomccalendars.htm for 2021 onward, fomchistorical{YYYY}.htm
for 2011-2020), every press-conference page, and the Brightcove playback API that the federalreserve.gov
player calls. The player's public policy key is read at run time from the player configuration and is not
stored. Network use is HTML/JSON GETs plus HEAD (or 1-byte range) probes; no video, caption or transcript
file is downloaded.

    python build_manifest.py                                  # writes pressers.csv, meetings.csv, check.json
    python build_manifest.py --local-root DIR --usmpd-times usmpd_times.csv
    python build_manifest.py --offline                         # rebuild from the page cache only

Stdlib only (Python 3.11+), so it runs on a HiPerGator login node without the project environment.
Re-run after each new press conference (2026-10-28, 2026-12-09, ...) to append rows.
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import hashlib
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger("manifest")

FED = "https://www.federalreserve.gov"
BC_API = "https://edge.api.brightcove.com/playback/v1/accounts/{account}/videos/{video}"
BC_PLAYER = "https://players.brightcove.net/{account}/{player}_{embed}/config.json"
UA = "Mozilla/5.0 (X11; Linux x86_64) fed-presser-manifest/1.0"
CAP_W, CAP_H = 960, 540
HIST_YEARS = range(2011, 2021)  # fomchistorical{YYYY}.htm; fomccalendars.htm lists 2021 onward
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
# Chair by date: fallback only; the transcript title ("Transcript of Chair Powell's ...") wins when available.
# Warsh start 2026-05-22 is from news reports (no Board release found); no presser falls in May 2026.
CHAIRS = [(dt.date(2006, 2, 1), "Bernanke"), (dt.date(2014, 2, 3), "Yellen"),
          (dt.date(2018, 2, 5), "Powell"), (dt.date(2026, 5, 22), "Warsh")]
# Nominal presser start (ET). Board announcements: 2011-03-24 (2:15 p.m. after a 12:30 statement) and
# 2013-03-13 (statement 2:00 p.m., presser "approximately 2:30 p.m."). The two unscheduled 2020 pressers use
# the SF Fed USMPD minute (11:00, 18:30); their statement times come from the press releases.
PRESSER_ERAS = [
    (dt.date(2011, 4, 27), "14:15", f"{FED}/newsevents/pressreleases/monetary20110324a.htm"),
    (dt.date(2013, 3, 20), "14:30", f"{FED}/newsevents/pressreleases/monetary20130313a.htm"),
]
PRESSER_SPECIAL = {dt.date(2020, 3, 3): "11:00", dt.date(2020, 3, 15): "18:30"}
STATEMENT_ERAS = [(dt.date(2011, 4, 27), "12:30"), (dt.date(2013, 3, 20), "14:00")]

PRESSER_COLUMNS = [
    "presser_id", "meeting_date", "meeting_start_date", "presser_date", "chair", "scheduled", "sep",
    "statement_time_et", "presser_start_et", "time_source", "in_default_sample",
    "fed_page_url", "statement_url", "transcript_pdf_url", "transcript_pdf_bytes", "vtt_url", "vtt_bytes",
    "brightcove_account_id", "brightcove_video_id", "mp4_url", "mp4_width", "mp4_height", "mp4_avg_bitrate",
    "mp4_bytes", "mp4_rule", "mp4_renditions", "signed_url_expires_utc", "duration_s", "bc_created_at",
    "local_pdf_path", "local_txt_path", "local_vtt_path", "local_pdf_sha256", "local_vtt_sha256",
    "local_pdf_matches_remote", "local_vtt_matches_remote", "checked_at_utc", "notes",
]
MEETING_COLUMNS = [
    "meeting_start_date", "meeting_date", "kind", "sep", "has_presser", "presser_date", "chair",
    "statement_url", "in_default_sample", "held", "listing_url",
]


# ----------------------------------------------------------------------------------------------- HTTP

@dataclass
class Probe:
    url: str
    status: int | None
    nbytes: int | None
    content_type: str = ""
    method: str = "HEAD"
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300


class Http:
    """GET with an on-disk cache, HEAD probes with a 1-byte range fallback, polite pacing and retries."""

    def __init__(self, cache: Path, offline: bool, refresh: bool, pause: float) -> None:
        self.cache, self.offline, self.refresh, self.pause = cache, offline, refresh, pause
        self.cache.mkdir(parents=True, exist_ok=True)

    def _open(self, req: urllib.request.Request, tries: int = 3) -> tuple[int, dict[str, str], bytes]:
        for attempt in range(tries):
            time.sleep(self.pause)
            try:
                with urllib.request.urlopen(req, timeout=45) as r:
                    body = r.read() if req.get_method() == "GET" and "Range" not in req.headers else b""
                    return r.status, {k.lower(): v for k, v in r.headers.items()}, body
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                    time.sleep(2.0 * (attempt + 1)); continue
                return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, b""
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt < tries - 1:
                    time.sleep(2.0 * (attempt + 1)); continue
                raise RuntimeError(f"{req.full_url}: {e}") from e
        raise AssertionError("unreachable")

    def get(self, url: str, name: str, headers: dict[str, str] | None = None, fresh: bool = False) -> str:
        path = self.cache / name
        if path.exists() and not (self.refresh or (fresh and not self.offline)):
            return path.read_text(encoding="utf-8")
        if self.offline:
            raise FileNotFoundError(f"offline and not cached: {name}")
        status, _, body = self._open(urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})}))
        if status != 200:
            raise RuntimeError(f"GET {url} -> HTTP {status}")
        text = body.decode("utf-8", "replace")
        path.write_text(text, encoding="utf-8")
        log.info("event=get url=%s bytes=%d", url, len(body))
        return text

    def probe(self, url: str) -> Probe:
        if not url:
            return Probe(url, None, None, error="no url")
        if self.offline:
            return Probe(url, None, None, error="offline")
        try:
            status, h, _ = self._open(urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA}))
            if 200 <= status < 300 and h.get("content-length"):
                return Probe(url, status, int(h["content-length"]), h.get("content-type", ""))
            # Some CDNs refuse HEAD or omit the length: ask for one byte and read the total from Content-Range.
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-0"})
            status, h, _ = self._open(req)
            total = re.search(r"/(\d+)$", h.get("content-range", ""))
            return Probe(url, status, int(total.group(1)) if total else None, h.get("content-type", ""), "RANGE")
        except RuntimeError as e:
            return Probe(url, None, None, error=str(e))


# -------------------------------------------------------------------------------------------- parsing

@dataclass
class Meeting:
    start: dt.date
    end: dt.date
    kind: str  # scheduled | unscheduled | conference_call | cancelled | notation_vote
    sep: bool
    statement_url: str
    presser_url: str
    presser_date: dt.date | None
    listing_url: str


HEAD_RE = re.compile(
    r"^(?P<m1>[A-Za-z]+)(?:/(?P<m2>[A-Za-z]+))?\s+(?P<d1>\d{1,2})"
    r"(?:\s*-\s*(?:(?P<m3>[A-Za-z]+)\s+)?(?P<d2>\d{1,2}))?\*?\s*(?:\((?P<tag>[^)]+)\))?\s*"
    r"(?P<what>Meeting|Conference Call)?\s*-\s*(?P<y>\d{4})$")
ABS = r'href="(?:https?://www\.federalreserve\.gov)?'
PRESSER_LINK = re.compile(ABS + r'(/monetarypolicy/fomcpres+conf(\d{8})\.htm)"')
STATEMENT_LINK = re.compile(ABS + r'(/newsevents/pressreleases/monetary(\d{8})a\.htm)"')


def ymd(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%Y%m%d").date()


def month(name: str) -> int:
    return MONTHS[name.strip().lower()[:3]]


def parse_heading(text: str) -> tuple[dt.date, dt.date, str] | None:
    """'April 30-May 1 Meeting - 2019', 'Apr/May 30-1 - 2024', 'March 2 (unscheduled) Meeting - 2020'."""
    m = HEAD_RE.match(re.sub(r"\s+", " ", text).strip())
    if not m:
        return None
    y, m1, d1 = int(m["y"]), month(m["m1"]), int(m["d1"])
    start = dt.date(y, m1, d1)
    if m["d2"]:
        m_end = month(m["m3"] or m["m2"]) if (m["m3"] or m["m2"]) else m1
        end = dt.date(y, m_end, int(m["d2"]))
    else:
        end = start
    tag = (m["tag"] or "").lower()
    kind = ("cancelled" if "cancel" in tag else "notation_vote" if "notation" in tag
            else "unscheduled" if "unscheduled" in tag
            else "conference_call" if m["what"] == "Conference Call" else "scheduled")
    return start, end, kind


def links_in(block: str, start: dt.date, end: dt.date) -> tuple[str, str, dt.date | None]:
    """Statement and presser links whose date belongs to this meeting (guards against stray page links)."""
    lo, hi = start, end + dt.timedelta(days=3)
    st = next((FED + u for u, d in STATEMENT_LINK.findall(block) if lo <= ymd(d) <= hi), "")
    pc = next(((FED + u, ymd(d)) for u, d in PRESSER_LINK.findall(block) if lo <= ymd(d) <= hi), ("", None))
    return st, pc[0], pc[1]


def parse_historical(html: str, url: str) -> list[Meeting]:
    out: list[Meeting] = []
    for block in html.split('<h5 class="panel-heading')[1:]:
        head = re.sub(r"<[^>]+>", "", block.split(">", 1)[1].split("</h5>", 1)[0])
        parsed = parse_heading(head)
        if not parsed:
            log.warning("event=unparsed_heading page=%s text=%r", url, head.strip()); continue
        start, end, kind = parsed
        st, pc, pd = links_in(block, start, end)
        sep = "SEPcompilation" in block or "fomcprojtabl" in block
        out.append(Meeting(start, end, kind, sep, st, pc, pd, url))
    return out


def parse_calendar(html: str, url: str) -> list[Meeting]:
    out: list[Meeting] = []
    years = [(m.start(), int(m.group(1))) for m in re.finditer(r"(\d{4}) FOMC Meetings", html)]
    cuts = [m.start() for m in re.finditer(r'<div class="(?:[^"]* )?row fomc-meeting"', html)] + [len(html)]
    for pos, nxt in zip(cuts, cuts[1:]):
        block = html[pos:nxt]
        year = next((y for p, y in reversed(years) if p < pos), None)
        mon = re.search(r'fomc-meeting__month[^>]*>\s*<strong>([^<]+)</strong>', block)
        day = re.search(r'fomc-meeting__date[^>]*>([^<]+)<', block)
        if not (mon and day and year):
            continue
        raw = day.group(1).strip()
        parsed = parse_heading(f"{mon.group(1).strip()} {raw.replace('*', '')} - {year}")
        if not parsed:
            log.warning("event=unparsed_calendar text=%r %r %s", mon.group(1), raw, year); continue
        start, end, kind = parsed
        st, pc, pd = links_in(block, start, end)
        out.append(Meeting(start, end, kind, "*" in raw, st, pc, pd, url))
    return out


@dataclass
class PageInfo:
    video_ids: list[str]
    account: str
    player: str
    embed: str
    pdf_url: str
    title: str
    statement_release: str  # "HH:MM" ET from "(Released <date> at h:mm p.m.)" next to the statement


def parse_presser_page(html: str, date: dt.date) -> PageInfo:
    attr = lambda a: (re.search(rf'data-{a}="([^"]+)"', html) or [None, ""])[1]
    pdf = re.search(r"/mediacenter/files/FOMCpresconf(\d{8})\.pdf", html)
    title = re.search(r"<h3>\s*([^<]*FOMC Meeting[^<]*)</h3>", html)
    rel = ""
    i = html.find("Meeting Statement")  # 'FOMC Meeting Statement:' (newer) or '...Statement</a>' (2011-2015)
    if i >= 0:
        m = re.search(r"Released [A-Za-z]+ \d{1,2}, \d{4} at (\d{1,2}):(\d{2}) ([ap])\.m\.", html[i:i + 1500])
        if m:
            h = int(m[1]) % 12 + (12 if m[3] == "p" else 0)
            rel = f"{h:02d}:{m[2]}"
    pdf_key = pdf.group(1) if pdf else f"{date:%Y%m%d}"  # canonical name when the link is missing
    return PageInfo(re.findall(r'data-video-id="(\d+)"', html), attr("account"), attr("player") or "default",
                    attr("embed") or "default", f"{FED}/mediacenter/files/FOMCpresconf{pdf_key}.pdf",
                    title.group(1).strip() if title else "", rel)


def release_time(html: str) -> str:
    """'For release at 10:00 a.m. EST' on a statement press release -> '10:00'."""
    m = re.search(r"For release at (\d{1,2}):(\d{2}) ([ap])\.m\.", html)
    return f"{int(m[1]) % 12 + (12 if m[3] == 'p' else 0):02d}:{m[2]}" if m else ""


def token_expiry(url: str) -> str:
    """Brightcove/Fastly signed URLs carry fastly_token = base64('<hex epoch>_<sig>')."""
    tok = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("fastly_token", [""])[0]
    try:
        raw = base64.urlsafe_b64decode(tok + "=" * (-len(tok) % 4)).decode("ascii", "replace")
        return dt.datetime.fromtimestamp(int(raw.split("_", 1)[0], 16), dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, IndexError):
        return ""


def pick_mp4(sources: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str, str]:
    """Highest-resolution MP4 rendition with width <= 960 and height <= 540 (ties: higher bitrate); if every
    rendition exceeds the cap, the highest available. HTTPS sources only."""
    mp4 = [s for s in sources if s.get("container") == "MP4" and str(s.get("src", "")).startswith("https")]
    key = lambda s: ((s.get("width") or 0) * (s.get("height") or 0), s.get("avg_bitrate") or 0)
    rends = sorted({(s.get("width") or 0, s.get("height") or 0) for s in mp4}, reverse=True)
    listing = ";".join(f"{w}x{h}" for w, h in rends)
    inside = [s for s in mp4 if (s.get("width") or 0) <= CAP_W and (s.get("height") or 0) <= CAP_H]
    if inside:
        best = max(inside, key=key)
        top = max(mp4, key=key)
        rule = "max_within_960x540" if key(best) == key(top) else "capped_at_960x540"
        return best, rule, listing
    if mp4:
        return max(mp4, key=key), "above_cap_highest", listing
    return None, "no_mp4", listing


# ---------------------------------------------------------------------------------------- local files

def index_local(root: Path | None) -> dict[str, dict[str, Path]]:
    out: dict[str, dict[str, Path]] = {}
    if not root:
        return out
    pats = {"pdf": re.compile(r"^FOMCpresconf(\d{8})\.pdf$"), "txt": re.compile(r"^FOMCpresconf(\d{8})\.txt$"),
            "vtt": re.compile(r"^(?:cap_)?(\d{8})\.vtt$")}
    for p in sorted(root.rglob("*")):
        for kind, pat in pats.items():
            m = pat.match(p.name)
            if m and p.is_file():
                slot = out.setdefault(m.group(1), {})
                # Prefer the canonical caption folder (.../vtt/YYYYMMDD.vtt) over ad-hoc copies.
                if kind not in slot or (kind == "vtt" and p.parent.name == "vtt"):
                    slot[kind] = p
    return out


def served_bytes(p: Path, text: bool) -> bytes:
    """File bytes as the server sends them: text files saved on Windows get CRLF normalised back to LF."""
    b = p.read_bytes()
    return b.replace(b"\r\n", b"\n") if text else b


def sha256(p: Path | None, text: bool = False) -> str:
    return hashlib.sha256(served_bytes(p, text)).hexdigest() if p else ""


def matches(p: Path | None, probe: Probe, text: bool = False) -> bool | str:
    return "" if not (p and probe.nbytes) else len(served_bytes(p, text)) == probe.nbytes


def chair_for(date: dt.date, txt: Path | None) -> tuple[str, str]:
    if txt:
        m = re.search(r"Transcript of Chair(?:man)? ([A-Z][a-z]+)'s", txt.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1), "transcript"
    return [c for d, c in CHAIRS if d <= date][-1], "date_rule"


# ----------------------------------------------------------------------------------------------- main

def load_usmpd(path: Path | None) -> dict[str, tuple[str, str, str]]:
    """Optional cross-check: CSV with date,usmpd_statement_et,usmpd_presser_et[,usmpd_sep] (SF Fed USMPD)."""
    if not path:
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {r["date"]: (r["usmpd_statement_et"], r["usmpd_presser_et"], r.get("usmpd_sep", ""))
                for r in csv.DictReader(f)}


def build(args: argparse.Namespace) -> None:
    http = Http(Path(args.cache), args.offline, args.refresh, args.pause)
    now = dt.datetime.now(dt.UTC)
    today_et = (now - dt.timedelta(hours=4)).date()  # ET date is all that is needed here
    s0, s1 = dt.date.fromisoformat(args.sample_start), dt.date.fromisoformat(args.sample_end)

    meetings: list[Meeting] = []
    for y in HIST_YEARS:
        url = f"{FED}/monetarypolicy/fomchistorical{y}.htm"
        meetings += parse_historical(http.get(url, f"fomchistorical{y}.htm"), url)
    url = f"{FED}/monetarypolicy/fomccalendars.htm"
    meetings += [m for m in parse_calendar(http.get(url, "fomccalendars.htm", fresh=True), url)
                 if m.start.year > max(HIST_YEARS)]
    meetings.sort(key=lambda m: m.start)
    pressers = [m for m in meetings if m.presser_date]
    log.info("event=listing meetings=%d pressers=%d", len(meetings), len(pressers))

    root = Path(args.local_root).resolve() if args.local_root else None
    local = index_local(root)
    rel = lambda q: q.resolve().relative_to(root).as_posix() if q and root else ""  # paths relative to root
    usmpd = load_usmpd(Path(args.usmpd_times) if args.usmpd_times else None)
    pk_cache: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    checks: dict[str, Any] = {"built_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "offline": args.offline,
                              "rows": {}}

    for m in pressers:
        d = m.presser_date
        assert d is not None
        key, notes = f"{d:%Y%m%d}", []
        page = parse_presser_page(http.get(m.presser_url, f"pc_{key}.htm"), d)
        if len(set(page.video_ids)) != 1:
            notes.append(f"video ids on page: {page.video_ids}")
        vid = page.video_ids[0] if page.video_ids else ""

        # statement time: the press release's "For release at" line (2016 onward), else the era rule. The
        # presser page's "(Released ... at h:mm)" is only a cross-check: in 2012 it shows 12:20/12:35 where the
        # Board schedule and USMPD say 12:30, so it looks like a web-posting time.
        st_time, st_src = "", ""
        if m.statement_url:
            try:
                st_time = release_time(http.get(m.statement_url, f"statement_{key}.htm"))
                st_src = "statement_release" if st_time else ""
            except (RuntimeError, FileNotFoundError) as e:
                notes.append(f"statement page: {e}")
        if not st_time:
            st_time, st_src = [t for e, t in STATEMENT_ERAS if e <= d][-1], "era_rule"
        if page.statement_release and page.statement_release != st_time:
            notes.append(f"presser page lists statement release {page.statement_release}")
        pc_time = PRESSER_SPECIAL.get(d) or [t for e, t, _ in PRESSER_ERAS if e <= d][-1]
        pc_src = "usmpd" if d in PRESSER_SPECIAL else "board_announcement"
        if key in usmpd:
            u_st, u_pc, u_sep = usmpd[key]
            if (u_st, u_pc) != (st_time, pc_time):
                notes.append(f"USMPD times {u_st}/{u_pc} differ")
            if u_sep in ("0", "1") and (u_sep == "1") != m.sep:
                notes.append(f"USMPD SEP={u_sep} differs from listing")

        # Brightcove playback API (fresh every run: the returned media URLs are signed for a few hours)
        bc: dict[str, Any] = {}
        if vid:
            acct = page.account or "66043936001"
            if acct not in pk_cache:
                cfg = json.loads(http.get(BC_PLAYER.format(account=acct, player=page.player, embed=page.embed),
                                          f"bc_player_{acct}.json", fresh=True))
                pk_cache[acct] = cfg["video_cloud"]["policy_key"]
            bc = json.loads(http.get(BC_API.format(account=acct, video=vid), f"bc_{vid}.json",
                                     headers={"Accept": f"application/json;pk={pk_cache[acct]}"}, fresh=True))
        best, rule, rends = pick_mp4(bc.get("sources", []))
        caps = [t for t in bc.get("text_tracks", []) if t.get("kind") == "captions"]
        vtt_url = ""
        if caps:
            srcs = [s.get("src", "") for s in caps[0].get("sources") or []] + [caps[0].get("src", "")]
            vtt_url = next((s for s in srcs if s.startswith("https")), srcs[0] if srcs else "")

        pdf_p, vtt_p, mp4_p = http.probe(page.pdf_url), http.probe(vtt_url), http.probe(best["src"] if best else "")
        for name, p in (("transcript_pdf", pdf_p), ("vtt", vtt_p), ("mp4", mp4_p)):
            if p.url and not p.ok:
                notes.append(f"{name} probe failed: {p.status} {p.error}".strip())
        if best and mp4_p.nbytes and best.get("size") and int(best["size"]) != mp4_p.nbytes:
            notes.append(f"mp4 size API {best['size']} != HEAD {mp4_p.nbytes}")

        loc = local.get(key, {})
        chair, chair_src = chair_for(d, loc.get("txt"))
        if chair != (rule_chair := [c for dd, c in CHAIRS if dd <= d][-1]):
            notes.append(f"chair {chair} ({chair_src}) != date rule {rule_chair}")
        row = {
            "presser_id": key, "meeting_date": m.end.isoformat(), "meeting_start_date": m.start.isoformat(),
            "presser_date": d.isoformat(), "chair": chair, "scheduled": m.kind == "scheduled", "sep": m.sep,
            "statement_time_et": st_time, "presser_start_et": pc_time, "time_source": f"{st_src}|{pc_src}",
            "in_default_sample": s0 <= d <= s1, "fed_page_url": m.presser_url, "statement_url": m.statement_url,
            "transcript_pdf_url": page.pdf_url, "transcript_pdf_bytes": pdf_p.nbytes or "",
            "vtt_url": vtt_url if vtt_p.ok or args.offline else "", "vtt_bytes": vtt_p.nbytes or "",
            "brightcove_account_id": page.account, "brightcove_video_id": vid,
            "mp4_url": best["src"] if best else "", "mp4_width": best.get("width", "") if best else "",
            "mp4_height": best.get("height", "") if best else "",
            "mp4_avg_bitrate": best.get("avg_bitrate", "") if best else "",
            "mp4_bytes": mp4_p.nbytes or (best.get("size", "") if best else ""), "mp4_rule": rule,
            "mp4_renditions": rends, "signed_url_expires_utc": token_expiry(best["src"]) if best else "",
            "duration_s": round(bc["duration"] / 1000, 3) if bc.get("duration") else "",
            "bc_created_at": bc.get("created_at", ""),
            "local_pdf_path": rel(loc.get("pdf")), "local_txt_path": rel(loc.get("txt")),
            "local_vtt_path": rel(loc.get("vtt")), "local_pdf_sha256": sha256(loc.get("pdf")),
            "local_vtt_sha256": sha256(loc.get("vtt"), text=True),
            "local_pdf_matches_remote": matches(loc.get("pdf"), pdf_p),
            "local_vtt_matches_remote": matches(loc.get("vtt"), vtt_p, text=True),
            "checked_at_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "notes": "; ".join(notes),
        }
        rows.append(row)
        checks["rows"][key] = {"chair_source": chair_src, "page_title": page.title,
                               "probes": {n: vars(p) for n, p in (("pdf", pdf_p), ("vtt", vtt_p), ("mp4", mp4_p))}}
        log.info("event=row date=%s chair=%s vid=%s mp4=%s bytes=%s vtt=%s notes=%r", key, chair, vid,
                 f"{row['mp4_width']}x{row['mp4_height']}", row["mp4_bytes"], bool(row["vtt_url"]), row["notes"])

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "pressers.csv", PRESSER_COLUMNS, rows)
    write_csv(out / "meetings.csv", MEETING_COLUMNS, [{
        "meeting_start_date": m.start.isoformat(), "meeting_date": m.end.isoformat(), "kind": m.kind,
        "sep": m.sep, "has_presser": m.presser_date is not None,
        "presser_date": m.presser_date.isoformat() if m.presser_date else "",
        "chair": [c for dd, c in CHAIRS if dd <= m.end][-1], "statement_url": m.statement_url,
        "in_default_sample": s0 <= m.end <= s1 and (m.kind == "scheduled" or m.presser_date is not None),
        "held": m.end <= today_et and m.kind != "cancelled", "listing_url": m.listing_url} for m in meetings])
    checks["time_sources"] = {u: vars(http.probe(u)) for _, _, u in PRESSER_ERAS}
    checks["summary"] = summarize(rows)
    (out / "check.json").write_text(json.dumps(checks, indent=1, default=str), encoding="utf-8")
    log.info("event=done summary=%s", json.dumps(checks["summary"]))


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by: dict[str, int] = {}
    for r in rows:
        by[r["chair"]] = by.get(r["chair"], 0) + 1
    num = lambda k: sum(int(r[k]) for r in rows if str(r[k]).isdigit())
    return {
        "pressers": len(rows), "by_chair": by, "in_default_sample": sum(bool(r["in_default_sample"]) for r in rows),
        "mp4_bytes_total": num("mp4_bytes"),
        "duration_s_total": round(sum(float(r["duration_s"] or 0) for r in rows), 1),
        "with_vtt_url": sum(bool(r["vtt_url"]) for r in rows),
        "with_local_vtt": sum(bool(r["local_vtt_path"]) for r in rows),
        "with_local_pdf": sum(bool(r["local_pdf_path"]) for r in rows),
        "missing_mp4": [r["presser_date"] for r in rows if not r["mp4_url"]],
        "missing_vtt": [r["presser_date"] for r in rows if not r["vtt_url"]],
        "missing_pdf": [r["presser_date"] for r in rows if not r["transcript_pdf_bytes"]],
        "rows_with_notes": {r["presser_date"]: r["notes"] for r in rows if r["notes"]},
    }


def write_csv(path: Path, cols: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows({k: str(v).lower() if isinstance(v, bool) else v for k, v in r.items()} for r in rows)
    log.info("event=write path=%s rows=%d", path, len(rows))


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out-dir", default=str(here))
    ap.add_argument("--cache", default=str(Path.home() / ".cache" / "fed_presser_manifest"),
                    help="page/JSON cache (safe to delete)")
    ap.add_argument("--local-root", default="",
                    help="folder searched for FOMCpresconf*.pdf/.txt and *.vtt; local_* paths are relative to it")
    ap.add_argument("--usmpd-times", default="", help="optional CSV date,usmpd_statement_et,usmpd_presser_et")
    ap.add_argument("--sample-start", default="2016-01-01")
    ap.add_argument("--sample-end", default="2026-10-31")
    ap.add_argument("--pause", type=float, default=0.3, help="seconds between requests")
    ap.add_argument("--offline", action="store_true", help="use cached pages only, no probes")
    ap.add_argument("--refresh", action="store_true", help="refetch every cached page")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    build(args)


if __name__ == "__main__":
    main()
