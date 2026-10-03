"""Re-date every labelled sentence of gtfintechlab/fomc_communication to its source document (fedspeak v2
Amendment 3, press-conference Deviation D1a).

The dataset's `year` column is not the year of the sentence's source document for many rows. This script finds the
source document(s) of each labelled row in the authors' own repository (github.com/gtfintechlab/fomc-hawkish-dovish,
folder data/) and writes data/text_corpus/label_dates.parquet, one row per dataset row.

    git clone --depth 1 --filter=blob:none --sparse https://github.com/gtfintechlab/fomc-hawkish-dovish.git tdw
    git -C tdw sparse-checkout set data
    python nlp/build_label_dates.py --tdw-repo tdw

Sources used (all inside <tdw>/data):
  annotated_data/manual-{mm,pc,sp}-split.xlsx  the annotated sheets. Together they hold exactly the 2,480 dataset
        rows: dataset `index` = sheet row, `orig_index` = row of the unsplit sheet manual-{mm,pc,sp}.xlsx. A row is
        assigned to the one sheet where (index, orig_index, normalised sentence) all agree; that gives source_type.
        The sheets carry no document id or date (their `year` equals the dataset's).
  filtered_data/{meeting_minutes,press_conference,speech/all}/ and the *_labeled folders   per-document sentence
        files; raw_data/{meeting_minutes,press_conference/csv/all,speech/text/all}/   per-document full text.
        Document id = <type>:<file stem> (stem without labeled_/_select/_filtered, lower case).
  master_files/master_mm_final_Oct_2024.xlsx  minutes release dates (minutes are dated by release, about three weeks
        after the meeting, as in docs_to_score.parquet); press conferences and speeches are dated by the 8-digit
        date in the file name, cross-checked against master_pc_final.xlsx and master_speech_final.csv (where the
        speech master's date differs, the later date is used; a speech file without an 8-digit date takes the
        master's date).

Matching (comparison text = lower case, line-break hyphenation joined ("modera- tion" -> "moderation"), every run of
non-alphanumeric characters, which covers quotes, apostrophes, mis-encoded characters and whitespace, collapsed to one
space):
  occurrences  every document (of any type) whose comparison text contains the row's comparison text as a whole-word
               substring (rows of 6+ words), or contains a document sentence equal to it (shorter rows), or contains
               the unsplit sheet sentence the row was cut from (orig_index join);
  source_date  the earliest date among the occurrences (Amendment 3: earliest document when a sentence appears in
               several); ties prefer the row's own source type, then the document id;
  match_method the strongest evidence that found an occurrence:
               exact                  the raw sentence equals a sentence of a per-document file
               normalised-whitespace  equal after normalisation
               annotated-sheet join   the unsplit sheet sentence (orig_index) equals a document sentence after
                                      normalisation, or is contained in a document
               substring              the normalised sentence (6+ words) is contained in a document
               none                   no occurrence; the row is undatable
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chrono_stance as cs  # noqa: E402

TYPES = ("mm", "pc", "sp")
DATE8 = re.compile(r"((?:19|20)\d{6})")
SUBSTRING_MIN_WORDS = 6


HYPHEN_BREAK = re.compile(r"([a-z])- +([a-z])")  # line-break hyphenation in the older texts ("modera- tion")


def norm(s) -> str:
    s = HYPHEN_BREAK.sub(r"\1\2", str(s or "").lower())
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def stem_of(p: Path) -> str:
    s = p.stem.lower()
    s = re.sub(r"^labeled_", "", s)
    s = re.sub(r"(?:_select)?(?:_filtered)?$", "", s)
    s = re.sub(r"_select$", "", s)
    return s


def read_sentences(p: Path) -> list[str]:
    f = pd.read_csv(p, encoding="utf-8", encoding_errors="replace")
    return [str(x) for x in f["sentence"].dropna()]


def load_documents(data: Path) -> pd.DataFrame:
    """One row per (type, stem): raw sentences (set), comparison sentences (set), comparison full text, date."""
    sent_dirs = {"mm": ["filtered_data/meeting_minutes", "filtered_data/meeting_minutes_labeled"],
                 "pc": ["filtered_data/press_conference", "filtered_data/press_conference_labeled"],
                 "sp": ["filtered_data/speech/all", "filtered_data/speech_labeled"]}
    raw_dirs = {"mm": ("raw_data/meeting_minutes", "txt"), "pc": ("raw_data/press_conference/csv/all", "csv"),
                "sp": ("raw_data/speech/text/all", "txt")}
    docs: dict[tuple[str, str], dict] = {}

    def get(t, stem):
        return docs.setdefault((t, stem), {"raw": set(), "norm": set(), "texts": [], "files": []})

    for t in TYPES:
        for d in sent_dirs[t]:
            for p in sorted((data / d).glob("*.csv")):
                e = get(t, stem_of(p))
                ss = read_sentences(p)
                e["raw"].update(s.strip() for s in ss)
                e["norm"].update(norm(s) for s in ss)
                e["texts"].append(" # ".join(norm(s) for s in ss))
                e["files"].append(str(p.relative_to(data)).replace("\\", "/"))
        d, ext = raw_dirs[t]
        for p in sorted((data / d).glob(f"*.{ext}")):
            e = get(t, stem_of(p))
            if ext == "csv":
                e["texts"].append(" # ".join(norm(s) for s in read_sentences(p)))
            else:
                e["texts"].append(norm(p.read_text(encoding="utf-8", errors="replace")))
            e["files"].append(str(p.relative_to(data)).replace("\\", "/"))

    mm = pd.read_excel(data / "master_files" / "master_mm_final_Oct_2024.xlsx")
    rel = {DATE8.search(u).group(1): pd.Timestamp(r).normalize() for u, r in zip(mm.Url, mm.ReleaseDate)}
    pcm = pd.read_excel(data / "master_files" / "master_pc_final.xlsx")
    pc_known = {DATE8.search(u).group(1) for u in pcm.Url}
    spm = pd.read_csv(data / "master_files" / "master_speech_final.csv")
    sp_date = {}
    for path, dt in zip(spm.LocalPath, spm.Date):
        st = Path(str(path)).stem.lower()
        sp_date[st] = pd.Timestamp(dt).normalize()

    rows, problems = [], []
    for (t, stem), e in docs.items():
        m = DATE8.search(stem)
        if not m:
            if t == "sp" and stem in sp_date:
                problems.append(f"sp:{stem} has no 8-digit date in its name; master date {sp_date[stem].date()} used")
                rows.append({"doc_type": t, "doc_id": f"{t}:{stem}", "date": sp_date[stem], "meeting_date": pd.NaT,
                             "raw": e["raw"], "norm": e["norm"], "text": " # ".join(e["texts"]),
                             "files": sorted(e["files"])})
            else:
                problems.append(f"{t}:{stem} has no date in its name and is skipped")
            continue
        fdate = pd.Timestamp(m.group(1))
        if t == "mm":
            if m.group(1) not in rel:
                problems.append(f"mm:{stem} not in master_mm_final_Oct_2024.xlsx")
                continue
            date, meeting = rel[m.group(1)], fdate
        else:
            date, meeting = fdate, pd.NaT
            if t == "pc" and m.group(1) not in pc_known:
                problems.append(f"pc:{stem} not in master_pc_final.xlsx")
            if t == "sp" and stem in sp_date and sp_date[stem] != fdate:
                date = max(fdate, sp_date[stem])
                problems.append(f"sp:{stem} master date {sp_date[stem].date()} differs from the file name; "
                                f"the later date {date.date()} is used")
        rows.append({"doc_type": t, "doc_id": f"{t}:{stem}", "date": date, "meeting_date": meeting,
                     "raw": e["raw"], "norm": e["norm"], "text": " # ".join(e["texts"]),
                     "files": sorted(e["files"])})
    D = pd.DataFrame(rows).sort_values(["date", "doc_id"]).reset_index(drop=True)
    return D, problems


def load_dataset_rows() -> pd.DataFrame:
    from huggingface_hub import hf_hub_download
    frames = []
    for split in ("train", "test"):
        p = Path(hf_hub_download(cs.DATASET_ID, f"{split}.csv", repo_type="dataset", revision=cs.DATASET_REV))
        f = pd.read_csv(p, encoding="utf-8-sig")
        frames.append(f.assign(split=split))
    lab = pd.concat(frames, ignore_index=True)
    lab["row"] = range(len(lab))
    return lab


def assign_sheets(lab: pd.DataFrame, data: Path) -> pd.DataFrame:
    lab = lab.copy()
    lab["k"] = lab.sentence.map(norm)
    lab["source_type"] = None
    lab["orig_sentence"] = None
    for t in TYPES:
        sp = pd.read_excel(data / "annotated_data" / f"manual-{t}-split.xlsx").rename(columns={"Unnamed: 0": "index"})
        un = pd.read_excel(data / "annotated_data" / f"manual-{t}.xlsx").rename(columns={"Unnamed: 0": "orig_index"})
        sp["k"] = sp.sentence.map(norm)
        keys = set(zip(sp["index"], sp.orig_index, sp.k))
        hit = [(i, o, k) in keys for i, o, k in zip(lab["index"], lab.orig_index, lab.k)]
        hit = pd.Series(hit, index=lab.index)
        if (hit & lab.source_type.notna()).any():
            raise SystemExit(f"rows match more than one annotated sheet ({t})")
        lab.loc[hit, "source_type"] = t
        omap = dict(zip(un.orig_index, un.sentence.astype(str)))
        lab.loc[hit, "orig_sentence"] = lab.loc[hit, "orig_index"].map(omap)
    if lab.source_type.isna().any():
        raise SystemExit(f"{int(lab.source_type.isna().sum())} dataset rows match no annotated sheet")
    return lab


class Corpus:
    def __init__(self, D: pd.DataFrame):
        self.D = D
        self.starts, parts, pos = [], [], 0
        for t in D.text:
            self.starts.append(pos)
            parts.append(t)
            pos += len(t) + 5
        self.big = " " + " ### ".join(parts) + " "
        self.by_raw, self.by_norm = {}, {}
        for i, (raw, nn) in enumerate(zip(D.raw, D.norm)):
            for s in raw:
                self.by_raw.setdefault(s, set()).add(i)
            for s in nn:
                self.by_norm.setdefault(s, set()).add(i)

    def contains(self, k: str) -> set[int]:
        out, needle, i = set(), " " + k + " ", 0
        while True:
            i = self.big.find(needle, i)
            if i < 0:
                return out
            out.add(bisect.bisect_right(self.starts, i) - 1)
            i += 1


def match_rows(lab: pd.DataFrame, C: Corpus) -> pd.DataFrame:
    D = C.D
    rec = []
    for r in lab.itertuples(index=False):
        k, raw = r.k, str(r.sentence).strip()
        ko = norm(r.orig_sentence)
        ex = C.by_raw.get(raw, set())
        ne = C.by_norm.get(k, set())
        oj = C.by_norm.get(ko, set()) | (C.contains(ko) if len(ko.split()) >= SUBSTRING_MIN_WORDS else set())
        sub = C.contains(k) if len(k.split()) >= SUBSTRING_MIN_WORDS else set()
        occ = ex | ne | oj | sub
        method = ("exact" if ex else "normalised-whitespace" if ne else "annotated-sheet join" if oj
                  else "substring" if sub else "none")
        if occ:
            cand = sorted(occ, key=lambda j: (D.date[j], D.doc_type[j] != r.source_type, D.doc_id[j]))
            j = cand[0]
            same = [x for x in cand if D.doc_type[x] == r.source_type]
            rec.append({"source_doc_id": D.doc_id[j], "source_doc_type": D.doc_type[j],
                        "source_date": D.date[j].strftime("%Y-%m-%d"),
                        "source_meeting_date": (D.meeting_date[j].strftime("%Y-%m-%d")
                                                if pd.notna(D.meeting_date[j]) else None),
                        "match_method": method, "n_source_docs": len(occ),
                        "n_source_docs_same_type": len(same),
                        "first_same_type_date": D.date[same[0]].strftime("%Y-%m-%d") if same else None,
                        "last_source_date": D.date[cand[-1]].strftime("%Y-%m-%d"),
                        "source_doc_ids": ";".join(D.doc_id[x] for x in cand[:50])})
        else:
            rec.append({"source_doc_id": None, "source_doc_type": None, "source_date": None,
                        "source_meeting_date": None, "match_method": "none", "n_source_docs": 0,
                        "n_source_docs_same_type": 0, "first_same_type_date": None, "last_source_date": None,
                        "source_doc_ids": ""})
    return pd.concat([lab.reset_index(drop=True), pd.DataFrame(rec)], axis=1)


def git_head(p: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(p), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def report(out: pd.DataFrame) -> dict:
    dated = out.source_date.notna()
    sy = pd.to_datetime(out.source_date).dt.year
    diff = (sy - out.year)[dated]
    print(f"\nrows {len(out)}, dated {int(dated.sum())} ({dated.mean():.1%})")
    print("\nmatch method:", out.match_method.value_counts().to_dict())
    print("\ncoverage by source type:")
    print(out.groupby("source_type").agg(rows=("row", "size"), dated=("source_date", lambda s: int(s.notna().sum())),
                                         share=("source_date", lambda s: round(s.notna().mean(), 3))).to_string())
    print("\ncoverage by dataset year:")
    print(out.groupby("year").agg(rows=("row", "size"), dated=("source_date", lambda s: int(s.notna().sum())),
                                  share=("source_date", lambda s: round(s.notna().mean(), 3))).to_string())
    print(f"\ncorrected year differs from dataset year: {int((diff != 0).sum())} of {int(dated.sum())} dated rows")
    print("corrected - dataset year:", diff.describe().round(2).to_dict())
    print("distribution of (corrected - dataset) year:")
    print(diff.value_counts().sort_index().to_string())
    cross = int((out.source_doc_type.notna() & (out.source_doc_type != out.source_type)).sum())
    print(f"earliest occurrence in a document of another type than the row's sheet: {cross}")
    return {"n_rows": int(len(out)), "n_dated": int(dated.sum()), "share_dated": round(float(dated.mean()), 4),
            "by_method": out.match_method.value_counts().to_dict(),
            "by_source_type": {t: {"rows": int((out.source_type == t).sum()),
                                   "dated": int((dated & (out.source_type == t)).sum())} for t in TYPES},
            "by_dataset_year": {int(y): {"rows": int(g.shape[0]), "dated": int(g.source_date.notna().sum())}
                                for y, g in out.groupby("year")},
            "n_year_differs": int((diff != 0).sum()),
            "year_diff_counts": {int(k): int(v) for k, v in diff.value_counts().sort_index().items()},
            "n_earliest_other_type": cross}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tdw-repo", required=True, help="clone of github.com/gtfintechlab/fomc-hawkish-dovish")
    ap.add_argument("--out", default=str(cs.LABEL_DATES_PATH))
    a = ap.parse_args(argv)
    data = Path(a.tdw_repo) / "data"
    lab = assign_sheets(load_dataset_rows(), data)
    D, problems = load_documents(data)
    print(f"documents: {D.doc_type.value_counts().to_dict()}; "
          f"date range {D.date.min().date()} .. {D.date.max().date()}")
    for p in problems:
        print("note:", p)
    out = match_rows(lab, Corpus(D))
    keep = ["row", "split", "index", "orig_index", "sentence", "label", "year", "source_type", "source_doc_id",
            "source_doc_type", "source_date", "source_meeting_date", "match_method", "n_source_docs",
            "n_source_docs_same_type", "first_same_type_date", "last_source_date", "source_doc_ids"]
    out = out[keep].rename(columns={"year": "dataset_year"})
    summary = report(out.rename(columns={"dataset_year": "year"}))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(a.out, index=False)
    meta = {"tdw_repo": "https://github.com/gtfintechlab/fomc-hawkish-dovish", "tdw_commit": git_head(Path(a.tdw_repo)),
            "label_dataset": cs.DATASET_ID, "label_revision": cs.DATASET_REV,
            "n_documents": {k: int(v) for k, v in D.doc_type.value_counts().items()},
            "substring_min_words": SUBSTRING_MIN_WORDS, "document_notes": problems,
            "sha256": hashlib.sha256(Path(a.out).read_bytes()).hexdigest(), **summary}
    with open(Path(a.out).with_name("label_dates_meta.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(meta, indent=2) + "\n")
    print(f"\nwrote {a.out} ({len(out)} rows) and label_dates_meta.json")


if __name__ == "__main__":
    main()
