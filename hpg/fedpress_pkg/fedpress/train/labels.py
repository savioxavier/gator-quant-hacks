"""Labelled hawkish/dovish/neutral sentences for the walk-forward stance models.

Sources (``train.stance_walkforward.data``), all CC BY-NC 4.0 except the team file:

* ``hf``: gtfintechlab/fomc_communication, train.csv + test.csv at a pinned dataset revision (the registered
  training data of deviation D1). Columns: index, sentence, year, label, orig_index. No document type.
* ``github_doc_types``: the authors' annotated files per document type (minutes ``mm``, press conferences
  ``pc``, speeches ``sp``) at a pinned commit of github.com/gtfintechlab/fomc-hawkish-dovish. They supply the
  document type of each HF sentence (exact match after normalisation); ``add_missing`` also adds their rows
  that are absent from the HF copy.
* ``team_csv``: optional team labels (columns sentence, label, and date or year; doc_type optional).

Label dates (``data.redate``, deviation D1a = fedspeak_v2 Amendment 3): the dataset's ``year`` column is often
not the year of the sentence's source document (2,336 of 2,480 rows differ). With ``redate.enabled`` every
dataset row is re-dated to the earliest source document that contains it, from the team's table
``manifest/label_dates.parquet`` (built by ``manifest/build_label_dates.py`` from the authors' per-document files;
sha256 pinned in the config). ``year`` then holds the source-document year, so model Y (labels with
year <= Y-1) trains only on rows whose source date is before Y-01-01; ``dataset_year`` keeps the original
value. Rows without a source date get ``year = redate.undated_year`` (2022): they stay out of every model for
2015-2022 and are kept for 2023+ (all labels predate 2023).

Labels: 0 = dovish, 1 = hawkish, 2 = neutral (TDW convention). Duplicate sentences with conflicting labels are
dropped and counted. Output: <root>/<labels_dir>/stance_labels.parquet + labels_meta.json.
"""

from __future__ import annotations

import csv
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from ..config import Config
from ..io import atomic_write_json, read_json, sha256_file, utc_now, write_parquet
from ..log import Log
from ..nlp.split import normalise

LABELS = {0: "dovish", 1: "hawkish", 2: "neutral"}
_NAME_TO_ID = {v: k for k, v in LABELS.items()}
_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def sentence_key(text: str) -> str:
    """Matching key: normalised, lower case, letters and digits only."""
    return re.sub(r"[^a-z0-9]+", "", normalise(str(text)).lower())


def scfg(cfg: Config) -> dict[str, Any]:
    return cfg.section("train").get("stance_walkforward", {})


def labels_dir(cfg: Config) -> Path:
    p = Path(str(scfg(cfg).get("labels_dir", "train")))
    return p if p.is_absolute() else cfg.root / p


def labels_path(cfg: Config) -> Path:
    return labels_dir(cfg) / "stance_labels.parquet"


def meta_path(cfg: Config) -> Path:
    return labels_dir(cfg) / "labels_meta.json"


# ------------------------------------------------------------------ minimal .xlsx reader (no openpyxl needed)
def _col(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):  # type: ignore[union-attr]
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_xlsx(path: Path) -> list[dict[str, str]]:
    """First worksheet as a list of dicts keyed by the header row (strings; enough for the annotated files)."""
    with zipfile.ZipFile(path) as z:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iter(f"{{{_NS['m']}}}t")) for si in root.findall("m:si", _NS)]
        sheet = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))[0]
        root = ET.fromstring(z.read(sheet))
    rows: list[list[str]] = []
    for r in root.iter(f"{{{_NS['m']}}}row"):
        cells: dict[int, str] = {}
        for c in r.findall("m:c", _NS):
            t, v = c.get("t"), c.find("m:v", _NS)
            if t == "s" and v is not None:
                val = shared[int(v.text or 0)]
            elif t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter(f"{{{_NS['m']}}}t"))
            else:
                val = v.text if v is not None and v.text is not None else ""
            cells[_col(c.get("r", "A1"))] = val
        rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    if not rows:
        return []
    header = [h.strip() for h in rows[0]]
    return [{h: (row[i] if i < len(row) else "") for i, h in enumerate(header) if h} for row in rows[1:] if row]


# ------------------------------------------------------------------ sources
def _label_id(raw: str) -> int | None:
    s = str(raw).strip().lower()
    if s in _NAME_TO_ID:
        return _NAME_TO_ID[s]
    try:
        v = int(float(s))
    except ValueError:
        return None
    return v if v in LABELS else None


def _year(raw: str) -> int | None:
    m = re.search(r"(19|20)\d{2}", str(raw))
    return int(m.group(0)) if m else None


def _download(url: str, dest: Path, timeout: float = 120.0) -> Path:
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(r.content)
    tmp.replace(dest)
    return dest


def _hf_rows(cfg: Config, src: dict[str, Any], files_meta: dict[str, Any]) -> list[dict[str, Any]]:
    from huggingface_hub import hf_hub_download

    rows: list[dict[str, Any]] = []
    for name in src.get("files", ["train.csv", "test.csv"]):
        p = Path(hf_hub_download(repo_id=src["repo"], filename=name, repo_type="dataset", revision=src["revision"]))
        files_meta[f"hf:{name}"] = {"repo": src["repo"], "revision": src["revision"], "sha256": sha256_file(p)}
        with p.open(encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                rows.append({"sentence": r["sentence"], "label": _label_id(r["label"]), "year": _year(r["year"]),
                             "doc_type": "unknown", "source": f"hf:{name}"})
    return rows


def _redate(cfg: Config, rows: list[dict[str, Any]], red: dict[str, Any], files_meta: dict[str, Any]) -> dict[str, Any]:
    """D1a: replace ``year`` by the source-document year (in place); returns counts for labels_meta.json.

    Rows are matched to the re-dating table by sentence key (normalised text); a key found in several dataset
    rows takes the earliest source date, as Amendment 3 prescribes. Team rows keep their own date."""
    import pandas as pd

    path = cfg.pkg_path(str(red.get("table", "manifest/label_dates.parquet")))
    if not path.exists():
        raise FileNotFoundError(f"{path} missing: train.stance_walkforward.data.redate needs the label dates table")
    digest = sha256_file(path)
    want = str(red.get("sha256") or "")
    if want and digest != want:
        raise ValueError(f"{path}: sha256 {digest} != pinned {want} (rebuild or update the config deliberately)")
    files_meta["label_dates"] = {"path": str(path), "sha256": digest}
    t = pd.read_parquet(path, columns=["sentence", "source_date", "source_type"])
    t = t[t["source_date"].notna()].copy()
    t["key"] = t["sentence"].map(sentence_key)
    t = t.sort_values(["key", "source_date"]).drop_duplicates("key")
    date_of = dict(zip(t["key"], t["source_date"].astype(str)))
    type_of = dict(zip(t["key"], t["source_type"].astype(str)))
    undated_year = int(red.get("undated_year", 2022))
    n = {"dated": 0, "undated": 0, "year_changed": 0, "team_rows_kept": 0}
    for r in rows:
        if r["source"] == "team_csv":
            n["team_rows_kept"] += 1
            continue
        r["dataset_year"] = r["year"]
        d = date_of.get(sentence_key(r["sentence"]))
        if d:
            r["source_date"], r["year"] = d, int(d[:4])
            if r["doc_type"] == "unknown":
                r["doc_type"] = type_of[sentence_key(r["sentence"])]
            n["dated"] += 1
        else:
            r["source_date"], r["year"] = None, undated_year
            n["undated"] += 1
        n["year_changed"] += int(r["year"] != r["dataset_year"])
    return {"enabled": True, "table": str(path), "sha256": digest, "undated_year": undated_year, **n}


def _github_rows(cfg: Config, src: dict[str, Any], files_meta: dict[str, Any]) -> list[dict[str, Any]]:
    raw_dir = labels_dir(cfg) / "raw" / "github"
    rows: list[dict[str, Any]] = []
    for doc_type, rel in (src.get("files") or {}).items():
        dest = raw_dir / f"{doc_type}_{Path(rel).name}"
        if not dest.exists():
            _download(f"https://raw.githubusercontent.com/{src['repo']}/{src['commit']}/{rel}", dest)
        files_meta[f"github:{doc_type}"] = {"repo": src["repo"], "commit": src["commit"], "path": rel,
                                            "sha256": sha256_file(dest)}
        for r in read_xlsx(dest):
            rows.append({"sentence": r.get("sentence", ""), "label": _label_id(r.get("label", "")),
                         "year": _year(r.get("year", "")), "doc_type": doc_type, "source": f"github:{doc_type}"})
    return rows


def _team_rows(path: str, files_meta: dict[str, Any]) -> list[dict[str, Any]]:
    p = Path(path).expanduser()
    files_meta["team_csv"] = {"path": str(p), "sha256": sha256_file(p)}
    rows: list[dict[str, Any]] = []
    with p.open(encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            year = _year(r.get("date") or r.get("year") or "")
            rows.append({"sentence": r["sentence"], "label": _label_id(r["label"]), "year": year,
                         "doc_type": (r.get("doc_type") or "team").strip() or "team", "source": "team_csv"})
    return rows


def build(cfg: Config, log: Log | None = None, force: bool = False) -> Path:
    """Download (if needed) and merge the label sources; returns the parquet path. Needs network once."""
    import pandas as pd

    out = labels_path(cfg)
    data = scfg(cfg).get("data", {})
    if out.exists() and meta_path(cfg).exists() and not force:
        old = (read_json(meta_path(cfg)).get("redate") or {})
        red = data.get("redate", {}) or {}
        same = bool(old.get("enabled")) == bool(red.get("enabled", False)) and (
            not red.get("enabled") or not red.get("sha256") or old.get("sha256") == red.get("sha256"))
        if same:
            return out
        if log:
            log.warning("labels.rebuild", reason="label dating (data.redate) changed since the labels were built")
    files_meta: dict[str, Any] = {}
    hf_cfg, gh_cfg, team = data.get("hf", {}), data.get("github_doc_types", {}), data.get("team_csv", {})
    base = _hf_rows(cfg, hf_cfg, files_meta) if hf_cfg.get("enabled", True) else []
    gh = _github_rows(cfg, gh_cfg, files_meta) if gh_cfg.get("enabled", True) else []
    doc_of = {}
    for r in gh:
        if r["label"] is not None:
            doc_of.setdefault(sentence_key(r["sentence"]), r["doc_type"])
    for r in base:
        r["doc_type"] = doc_of.get(sentence_key(r["sentence"]), "unknown")
    if not base or gh_cfg.get("add_missing", False):
        have = {sentence_key(r["sentence"]) for r in base}
        base += [r for r in gh if sentence_key(r["sentence"]) not in have]
    red = data.get("redate", {}) or {}
    redate_info: dict[str, Any] = {"enabled": False}
    if red.get("enabled", False):
        redate_info = _redate(cfg, base, red, files_meta)
    if str(team.get("path") or "").strip():
        base += _team_rows(str(team["path"]), files_meta)
    df = pd.DataFrame(base)
    for c in ("dataset_year", "source_date"):
        if c not in df.columns:
            df[c] = None
    n_raw = len(df)
    df = df[df["label"].notna() & df["year"].notna() & (df["sentence"].astype(str).str.strip() != "")].copy()
    df["label"] = df["label"].astype(int)
    df["year"] = df["year"].astype(int)
    df["sentence"] = df["sentence"].map(lambda s: normalise(str(s)))
    df["key"] = df["sentence"].map(sentence_key)
    n_labels = df.groupby("key")["label"].nunique()
    conflicts = set(n_labels[n_labels > 1].index)
    df = df[~df["key"].isin(conflicts)]
    df["_known"] = (df["doc_type"] == "unknown").astype(int)
    df = df.sort_values(["key", "_known", "source"]).drop_duplicates("key").drop(columns="_known")
    df["label_name"] = df["label"].map(LABELS)
    df = df.sort_values(["year", "key"]).reset_index(drop=True)
    write_parquet(df, out, {"created_utc": utc_now()})
    meta = {
        "created_utc": utc_now(), "files": files_meta, "rows_raw": n_raw, "rows": len(df),
        "conflicting_keys_dropped": len(conflicts), "max_year": int(df["year"].max()), "min_year": int(df["year"].min()),
        "by_year": {int(k): int(v) for k, v in df["year"].value_counts().sort_index().items()},
        "by_doc_type": {str(k): int(v) for k, v in df["doc_type"].value_counts().items()},
        "by_label": {str(k): int(v) for k, v in df["label_name"].value_counts().items()},
        "sha256": sha256_file(out), "label_names": LABELS, "year_basis": "source_date" if redate_info["enabled"]
        else "dataset_year", "redate": redate_info,
    }
    atomic_write_json(meta_path(cfg), meta)
    if log:
        log.info("labels.built", rows=len(df), conflicts=len(conflicts), max_year=meta["max_year"],
                 by_doc_type=meta["by_doc_type"])
    return out


def load(cfg: Config) -> tuple["Any", dict[str, Any]]:
    """(labels DataFrame, meta) or FileNotFoundError with the command that builds them."""
    import pandas as pd

    p, m = labels_path(cfg), meta_path(cfg)
    if not p.exists() or not m.exists():
        raise FileNotFoundError(f"{p} missing: run `python -m fedpress.train.stance_walkforward prepare` "
                                "(needs outbound HTTPS; CPU job or dev session)")
    meta = read_json(m)
    if (scfg(cfg).get("data", {}).get("redate", {}) or {}).get("enabled", False) and meta.get("year_basis") != "source_date":
        raise FileNotFoundError(f"{p} was built without the D1a source-date re-dating: run "
                                "`python -m fedpress.train.stance_walkforward prepare --force`")
    return pd.read_parquet(p), meta
