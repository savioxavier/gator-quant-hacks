"""Walk-forward chronological hawkish/dovish stance model (fedspeak v2 Amendment 2, press-conference Deviation D1).

Spec (fixed before any v2 or H1 return was computed):
  research/fedspeak_v2/HYPOTHESIS_v2.md, Amendment 2 (with its clarification) and Amendment 3
  research/fed_presser_plan/DEVIATION_D1_stance_model.md, including Update D1a

For each test year Y (2015..2026; 2015 scores the v2 warm-up documents, per the clarification to Amendment 2):
  * base model   manelalab/chrono-bert-v1-<min(Y-1, 2024)>1231 (MIT; ModernBERT-base encoder pretrained only on
                 text up to the end of that year), loaded with a new 3-way sequence-classification head;
  * labels       gtfintechlab/fomc_communication (CC BY-NC 4.0, ungated), train + test splits combined, only rows
                 whose source document is dated before Y-01-01 (Amendment 3 / D1a: the date comes from
                 data/text_corpus/label_dates.parquet, built by nlp/build_label_dates.py from the authors' per-document
                 files; undatable rows are left out for Y <= 2022 and kept for Y >= 2023). Labels end in 2022, so
                 Y >= 2023 uses all rows. The older rules `dataset` (dataset `year` <= Y-1) and `redated` stay
                 available through --label-year / CHRONO_LABEL_YEAR;
  * validation   15% stratified split of those rows (seed 0, same split for every training seed), early stopping
                 on macro-F1;
  * settings     lr 2e-5, batch 16, max length 256, at most 8 epochs, patience 2, weight decay 0.01, 10% linear
                 warmup then linear decay; seeds 42, 43, 44;
  * scoring      a document dated in year Y is scored only by model Y; class probabilities are averaged across the
                 seeds; sentence label = argmax; document score = share hawkish - share dovish.

Label ids (dataset card README, "Label Interpretation"): LABEL_0 = Dovish, LABEL_1 = Hawkish, LABEL_2 = Neutral.
`prepare` re-reads the card and checks the ids against cue words in the labelled sentences; it aborts on a mismatch.

Implementation choices not fixed by the spec (fixed here, before any scoring):
  * training rows are put in a canonical order (year, sentence, label, orig_index) before the split, so the split
    does not depend on file order; validation size per class = round(0.15 * n_class), drawn with
    numpy RandomState(0) class by class in label order 0, 1, 2;
  * AdamW; as in the Hugging Face Trainer, biases and normalisation weights get no weight decay, gradients are
    clipped at norm 1.0, and the linear schedule spans the maximum of 8 epochs (early stopping cuts it short);
  * bf16 autocast for training when the GPU supports it (fp32 master weights); scoring runs in fp32;
  * the checkpoint kept is the epoch with the best validation macro-F1 (ties keep the earlier epoch);
  * sentence splitter = the team's fedspeak_v2 rule (split_units below), with NLTK Punkt (English, punkt_tab);
    statement voting-roster sentences ("Voting for ...") are flagged and reported both ways.

Subcommands
  export   build data/text_corpus/docs_to_score.parquet from the local v2 corpus and press-conference text
  prepare  download the labels (pinned revision), verify the label ids, attach the source-document dates of
           label_dates.parquet (checked against the dataset row by row), print rows by year, fetch the base models
           and the Punkt data so that training and scoring can run offline
  train    --year Y --seed S   fine-tune one model, save it to <root>/models/Y/seed_S/ with metrics.json
  score    --year Y            score every document dated in year Y -> <root>/scores/Y.parquet, Y_docs.parquet
  merge    concatenate -> <root>/scores/doc_scores_chrono.parquet, presser_answers_chrono.parquet,
           presser_meetings_chrono.parquet (copied to data/text_corpus/chrono_scores/ in the repo)

<root> is $CHRONO_ROOT, or --root, or nlp/work inside the repo (git-ignored).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
DOCS_PATH = REPO / "data" / "text_corpus" / "docs_to_score.parquet"
PUBLISH_DIR = REPO / "data" / "text_corpus" / "chrono_scores"
LABEL_DATES_PATH = REPO / "data" / "text_corpus" / "label_dates.parquet"

DATASET_ID = "gtfintechlab/fomc_communication"
DATASET_REV = "6b0283f55f0005a6d38d49f271d795c21fccc1a3"  # main on 2026-10-03
LABELS = {0: "dove", 1: "hawk", 2: "neut"}
CARD_EXPECTED = {0: "dovish", 1: "hawkish", 2: "neutral"}

YEARS = list(range(2015, 2027))  # 2015 = v2 warm-up year (Amendment 2 clarification); 2016-2026 = test years
PREP_YEARS = YEARS
SEEDS = [42, 43, 44]
HP = {"lr": 2e-5, "batch_size": 16, "max_len": 256, "max_epochs": 8, "patience": 2, "weight_decay": 0.01,
      "warmup_ratio": 0.10, "val_frac": 0.15, "split_seed": 0, "max_grad_norm": 1.0}
SOURCES = ["speech", "statement", "minutes", "presser_doc", "presser_answer", "presser_question",
           "presser_statement"]

# Which date decides whether a labelled row may train model Y.
#   true     = (default; fedspeak v2 Amendment 3, press-conference D1a) the date of the row's source document, from
#              data/text_corpus/label_dates.parquet (nlp/build_label_dates.py, the authors' per-document files in
#              github.com/gtfintechlab/fomc-hawkish-dovish; earliest document when the sentence occurs in several;
#              minutes dated by release). Model Y uses rows with source_date < Y-01-01; rows without a source date
#              are excluded for Y <= 2022 and included for Y >= 2023 (every label predates 2023).
#   dataset  = the dataset's own `year` column <= Y-1 (Amendment 2 taken literally; superseded);
#   redated  = max(dataset year, year of the first document in docs_to_score.parquet that contains the sentence
#              verbatim, 2020 if it mentions COVID/coronavirus) <= Y-1 (interim audit rule; superseded).
# Audit 2026-10-03: the dataset's `year` column is not the source-document year for most rows (2,336 of 2,480 rows
# differ from the source document's year, by up to 26 years either way). `prepare` writes label_year_audit.json.
LABEL_YEAR_RULES = ("true", "dataset", "redated")
LABEL_YEAR_DEFAULT = os.environ.get("CHRONO_LABEL_YEAR", "true")
UNDATED_FROM_YEAR = 2023  # rows without a source date train models Y >= this year only
REDATE_MIN_WORDS = 8
LEAK_MIN_WORDS = 4  # leakage audit: labelled sentences of 4+ words are looked up in docs_to_score.parquet
COVID_RE = re.compile(r"\b(?:covid|coronavirus)", re.I)


def base_model_id(year: int) -> str:
    return f"manelalab/chrono-bert-v1-{min(year - 1, 2024)}1231"


def get_root(arg: str | None) -> Path:
    r = Path(arg or os.environ.get("CHRONO_ROOT") or (REPO / "nlp" / "work"))
    r.mkdir(parents=True, exist_ok=True)
    return r


def log(*a) -> None:
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


# ----------------------------------------------------------------------------------------------------------------
# Sentence splitter (fixed before any scoring). Identical to split_units in the fedspeak_v2 scorer:
#   paragraphs = split on newlines; stage directions ([Laughter], [Cough], [Inaudible], [No response],
#   [extended pause], [pause], [crosstalk], [applause]) removed; footnote-call digits glued to a sentence end
#   ("well.1 It") removed; a paragraph with <= 15 words and no terminal punctuation is a heading and is dropped;
#   each paragraph -> nltk.sent_tokenize (Punkt, English); whitespace collapsed; a unit is kept if it has >= 3
#   alphabetic words of 2+ letters. Roster flag: unit starts with "Voting for".
# ----------------------------------------------------------------------------------------------------------------
STAGE = re.compile(r"\[\s*(?:laughter|cough|inaudible|no response|extended pause|pause|crosstalk|applause)\s*\]", re.I)
TERM = re.compile(r"[.?!:;][\"'”’)\]]*\s*$")
FNCALL = re.compile(r"(?<=[a-z\)”\"])([.;,])\d{1,3}(?=\s+[A-Z“\"(])")
WORD = re.compile(r"[A-Za-z]{2,}")
ROSTER = re.compile(r"^Voting for\b")


def nltk_data_dir(root: Path) -> Path:
    return Path(os.environ.get("CHRONO_NLTK_DATA") or (root / "nltk_data"))


def get_sent_tokenize(root: Path, download: bool = False):
    import nltk
    d = nltk_data_dir(root)
    if str(d) not in nltk.data.path:
        nltk.data.path.insert(0, str(d))
    try:
        nltk.data.find("tokenizers/punkt_tab/english/")
    except LookupError:
        if not download:
            raise SystemExit(f"NLTK punkt_tab not found (looked in {nltk.data.path}); run `prepare` first")
        d.mkdir(parents=True, exist_ok=True)
        nltk.download("punkt_tab", download_dir=str(d), quiet=True)
        nltk.data.find("tokenizers/punkt_tab/english/")
    from nltk.tokenize import sent_tokenize
    return sent_tokenize


def punkt_fingerprint() -> dict:
    import nltk
    p = Path(nltk.data.find("tokenizers/punkt_tab/english/"))
    h = hashlib.sha256()
    for f in sorted(p.iterdir()):
        if f.is_file():
            h.update(f.name.encode())
            h.update(f.read_bytes())
    return {"nltk": nltk.__version__, "punkt_tab_english_sha256": h.hexdigest(), "path": str(p)}


def split_units(text: str, sent_tokenize) -> list[str]:
    units = []
    for para in re.split(r"\n+", text or ""):
        p = STAGE.sub(" ", para)
        p = FNCALL.sub(r"\1", p)
        p = " ".join(p.split())
        if not p:
            continue
        if not TERM.search(p) and len(p.split()) <= 15:
            continue
        for s in sent_tokenize(p):
            s = " ".join(s.split())
            if len(WORD.findall(s)) >= 3:
                units.append(s)
    return units


# ----------------------------------------------------------------------------------------------------------------
# export
# ----------------------------------------------------------------------------------------------------------------
def cmd_export(a) -> None:
    v2 = Path(a.v2_corpus)
    pt = Path(a.presser_text)
    sp = pd.read_parquet(v2 / "speeches.parquet")
    fd = pd.read_parquet(v2 / "fomc_docs.parquet")
    am = pd.read_parquet(pt / "answer_map.parquet")
    st = pd.read_parquet(pt / "statements.parquet")
    mt = pd.read_parquet(pt / "meetings.parquet")

    def day(s) -> pd.Series:
        s = pd.to_datetime(s)
        if getattr(s.dt, "tz", None) is not None:
            s = s.dt.tz_localize(None)
        return s.dt.normalize().astype("datetime64[ns]")

    parts = []
    parts.append(pd.DataFrame({"doc_id": sp.doc_id, "source": "speech", "date": day(sp.date), "text": sp.text,
                               "meeting": None, "n_words": sp.text.str.split().str.len()}))
    kind = {"statement": "statement", "minutes": "minutes", "presser": "presser_doc"}
    unknown = set(fd.doc_type) - set(kind)
    if unknown:
        raise SystemExit(f"unexpected fomc_docs doc_type(s): {unknown}")
    parts.append(pd.DataFrame({"doc_id": fd.doc_id, "source": fd.doc_type.map(kind), "date": day(fd.date),
                               "text": fd.text_core, "meeting": None,
                               "n_words": fd.text_core.str.split().str.len()}))
    mdate = dict(zip(mt.meeting, day(mt.date)))
    if set(am.meeting) - set(mdate) or set(st.meeting) - set(mdate):
        raise SystemExit("answer/statement meeting missing from meetings.parquet")
    parts.append(pd.DataFrame({"doc_id": am.answer_id, "source": "presser_answer", "date": am.meeting.map(mdate),
                               "text": am.answer_text, "meeting": am.meeting, "n_words": am.n_words}))
    parts.append(pd.DataFrame({"doc_id": "q_" + am.answer_id, "source": "presser_question",
                               "date": am.meeting.map(mdate), "text": am.question_text, "meeting": am.meeting,
                               "n_words": am.q_n_words}))
    parts.append(pd.DataFrame({"doc_id": "presser_" + st.doc_id, "source": "presser_statement",
                               "date": st.meeting.map(mdate), "text": st.text_core, "meeting": st.meeting,
                               "n_words": st.text_core.str.split().str.len()}))
    d = pd.concat(parts, ignore_index=True)
    d["text"] = d.text.fillna("")
    d["year"] = d.date.dt.year.astype("int16")
    d["n_words"] = d.n_words.fillna(0).astype("int32")
    d = d[["doc_id", "source", "date", "year", "text", "meeting", "n_words"]].sort_values(
        ["date", "source", "doc_id"]).reset_index(drop=True)
    assert d.doc_id.is_unique, "doc_id not unique"
    assert d.date.notna().all(), "missing date"
    assert set(d.source) <= set(SOURCES)
    # the same-day statement must be the identical text the v2 corpus holds
    v2st = dict(zip(fd.loc[fd.doc_type == "statement", "doc_id"], fd.loc[fd.doc_type == "statement", "text_core"]))
    same = sum(v2st.get(i) == t for i, t in zip(st.doc_id, st.text_core))
    DOCS_PATH.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(DOCS_PATH, index=False, compression="zstd", compression_level=19)
    mb = DOCS_PATH.stat().st_size / 2**20
    print(pd.crosstab(d.year, d.source, margins=True).to_string())
    print(f"presser statements identical to the v2 statement text: {same}/{len(st)}")
    print(f"empty texts: {(d.text.str.strip() == '').groupby(d.source).sum().to_dict()}")
    print(f"wrote {DOCS_PATH} ({len(d)} docs, {mb:.1f} MB)")
    if mb > 90:
        raise SystemExit("docs_to_score.parquet is over 90 MB")


# ----------------------------------------------------------------------------------------------------------------
# prepare
# ----------------------------------------------------------------------------------------------------------------
HAWK_CUES = [r"\btighten", r"\bremov\w*\s+(?:some\s+|the\s+)?(?:policy\s+)?accommodation",
             r"\b(?:raise|raising|increase|increasing)\s+(?:the\s+)?(?:target|federal funds rate|interest rates|policy rate)",
             r"\bfirming\b"]
DOVE_CUES = [r"\b(?:lower|lowering|reduce|reducing|cut|cutting)\s+(?:the\s+)?(?:target|federal funds rate|interest rates|policy rate)",
             r"\basset purchases\b", r"\bdownside risks?\b", r"\beas(?:e|ing)\b", r"\bstimul"]


def labels_path(root: Path) -> Path:
    return root / "data" / "labels.parquet"


def norm_text(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


def corpus_hits(sentences, docs: pd.DataFrame, min_words: int) -> list[list[int]]:
    """For each sentence, the positions (into docs sorted by date, doc_id) of every document whose normalised text
    contains the normalised sentence as a whole-word substring; sentences under min_words words get no hits."""
    import bisect
    parts, starts, pos = [], [], 0
    for t in docs.text:
        n = norm_text(t)
        starts.append(pos)
        parts.append(n)
        pos += len(n) + 3
    big = " " + " # ".join(parts) + " "
    out = []
    for s in sentences:
        k = norm_text(s)
        hits = []
        if len(k.split()) >= min_words:
            needle, i = " " + k + " ", 0
            while (i := big.find(needle, i)) >= 0:
                j = bisect.bisect_right(starts, i) - 1
                if not hits or hits[-1] != j:
                    hits.append(j)
                i += 1
        out.append(hits)
    return out


def redate_labels(lab: pd.DataFrame, docs: pd.DataFrame) -> pd.DataFrame:
    """Add year_redated / redate_first_doc (earliest corpus document containing the sentence verbatim) and, for the
    leakage audit, corpus_first_date / corpus_last_date / corpus_last_doc (earliest and latest such document,
    sentences of LEAK_MIN_WORDS+ words)."""
    docs = docs.sort_values(["date", "doc_id"], kind="mergesort").reset_index(drop=True)
    years = docs.date.dt.year.to_numpy()
    dates = docs.date.to_numpy()
    ids = docs.doc_id.to_numpy()
    hits = corpus_hits(lab.sentence, docs, min(REDATE_MIN_WORDS, LEAK_MIN_WORDS))
    long_enough = [len(norm_text(s).split()) >= REDATE_MIN_WORDS for s in lab.sentence]
    fy = [float(years[h[0]]) if h and ok else np.nan for h, ok in zip(hits, long_enough)]
    fd = [str(ids[h[0]]) if h and ok else None for h, ok in zip(hits, long_enough)]
    lab = lab.copy()
    lab["corpus_first_date"] = pd.to_datetime([dates[h[0]] if h else pd.NaT for h in hits])
    lab["corpus_last_date"] = pd.to_datetime([dates[h[-1]] if h else pd.NaT for h in hits])
    lab["corpus_last_doc"] = [str(ids[h[-1]]) if h else None for h in hits]
    lab["corpus_n_docs"] = [len(h) for h in hits]
    lab["redate_first_year"] = fy
    lab["redate_first_doc"] = fd
    covid = np.where(lab.sentence.str.contains(COVID_RE), 2020.0, np.nan)
    lab["year_redated"] = np.nanmax(np.vstack([lab.year.to_numpy(float), np.asarray(fy, float), covid]),
                                    axis=0).astype(int)
    return lab


def label_year_col(rule: str) -> str:
    if rule not in LABEL_YEAR_RULES:
        raise SystemExit(f"label-year rule must be one of {LABEL_YEAR_RULES}, got {rule!r}")
    return {"dataset": "year", "redated": "year_redated", "true": "source_date"}[rule]


LABEL_DATES_KEY = ["split", "index", "orig_index", "sentence"]


def attach_label_dates(lab: pd.DataFrame, path: Path = LABEL_DATES_PATH) -> tuple[pd.DataFrame, dict]:
    """Join label_dates.parquet onto the labelled rows; stop unless it covers every dataset row exactly once."""
    if not path.exists():
        raise SystemExit(f"{path} missing; build it with `python nlp/build_label_dates.py --tdw-repo <clone>` "
                         f"(see nlp/README.md, Label years)")
    ld = pd.read_parquet(path)
    if len(ld) != len(lab):
        raise SystemExit(f"{path.name} has {len(ld)} rows, the dataset has {len(lab)}; rebuild it")
    if ld.duplicated(LABEL_DATES_KEY).any():
        raise SystemExit(f"{path.name}: key {LABEL_DATES_KEY} is not unique")
    cols = ["source_type", "source_doc_id", "source_date", "match_method", "n_source_docs"]
    m = lab.merge(ld[LABEL_DATES_KEY + ["label", "dataset_year"] + cols], on=LABEL_DATES_KEY, how="left",
                  suffixes=("", "_ld"), validate="one_to_one", indicator=True)
    if (m._merge != "both").any():
        raise SystemExit(f"{int((m._merge != 'both').sum())} dataset rows are missing from {path.name}; rebuild it")
    if (m.label_ld != m.label).any() or (m.dataset_year != m.year).any():
        raise SystemExit(f"{path.name} disagrees with the dataset on label or year; rebuild it")
    m = m.drop(columns=["_merge", "label_ld", "dataset_year"])
    m["source_date"] = pd.to_datetime(m.source_date)
    info = {"path": str(path.name), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "n_rows": int(len(ld)),
            "n_dated": int(m.source_date.notna().sum()), "by_method": ld.match_method.value_counts().to_dict()}
    return m, info


def train_mask(lab: pd.DataFrame, rule: str, year: int) -> pd.Series:
    """Rows that may train model `year` under `rule`."""
    col = label_year_col(rule)
    if col not in lab.columns:
        raise SystemExit(f"labels have no {col} column; rerun `prepare` (rule {rule!r} needs "
                         f"{'label_dates.parquet' if rule == 'true' else 'docs_to_score.parquet'})")
    if rule == "true":
        undated = lab.source_date.isna()
        return (lab.source_date < pd.Timestamp(f"{year}-01-01")) | (undated & (year >= UNDATED_FROM_YEAR))
    return lab[col] <= year - 1


def cmd_prepare(a) -> None:
    from huggingface_hub import hf_hub_download, snapshot_download
    root = get_root(a.root)
    (root / "data").mkdir(parents=True, exist_ok=True)
    frames, files = [], {}
    for split in ("train", "test"):
        p = Path(hf_hub_download(DATASET_ID, f"{split}.csv", repo_type="dataset", revision=DATASET_REV))
        files[split] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
        f = pd.read_csv(p, encoding="utf-8-sig")  # the CSV header carries a BOM
        if list(f.columns) != ["index", "sentence", "year", "label", "orig_index"]:
            raise SystemExit(f"unexpected columns in {split}.csv: {list(f.columns)}")
        frames.append(f.assign(split=split))
    lab = pd.concat(frames, ignore_index=True)
    lab["year"] = lab.year.astype(int)
    lab["label"] = lab.label.astype(int)
    if set(lab.label) != {0, 1, 2}:
        raise SystemExit(f"unexpected label values {sorted(set(lab.label))}")
    rule = a.label_year
    label_year_col(rule)
    ld_info = None
    if LABEL_DATES_PATH.exists() or rule == "true":
        lab, ld_info = attach_label_dates(lab)
        print(f"label dates: {ld_info['path']} matches the dataset row for row ({ld_info['n_rows']} rows, "
              f"{ld_info['n_dated']} with a source date; methods {ld_info['by_method']})")
    test_years = sorted(set(YEARS) | set(getattr(a, "years", None) or []))
    if DOCS_PATH.exists():
        lab = redate_labels(lab, load_docs())
        audit = {"rule_in_use": rule, "min_words": REDATE_MIN_WORDS, "leak_min_words": LEAK_MIN_WORDS,
                 "docs": str(DOCS_PATH.name), "label_dates": ld_info,
                 "n_rows": int(len(lab)), "n_found_in_corpus": int(lab.redate_first_doc.notna().sum()),
                 "n_year_moved": int((lab.year_redated != lab.year).sum()), "per_test_year": {}, "leaks": {},
                 "examples": []}
        rules = [r for r in LABEL_YEAR_RULES if label_year_col(r) in lab.columns]
        for y in test_years:
            row = {}
            for r in rules:
                use = train_mask(lab, r, y)
                leak = use & (lab.corpus_last_date >= pd.Timestamp(f"{y}-01-01"))
                row[f"rows_{r}"] = int(use.sum())
                row[f"leak_{r}"] = int(leak.sum())
                row[f"first_{r}"] = int((use & (lab.corpus_first_date >= pd.Timestamp(f"{y}-01-01"))).sum())
                if r == rule:
                    audit["leaks"][y] = [{"sentence": s.sentence, "source_date": (str(s.source_date.date())
                                          if "source_date" in lab.columns and pd.notna(s.source_date) else None),
                                          "dataset_year": int(s.year), "corpus_last_doc": s.corpus_last_doc,
                                          "corpus_n_docs": int(s.corpus_n_docs)}
                                         for s in lab[leak].itertuples()]
            audit["per_test_year"][y] = row
        mv = lab[(lab.year_redated - lab.year) >= 5].head(10)
        audit["examples"] = [{"dataset_year": int(r.year), "first_doc": r.redate_first_doc,
                              "year_redated": int(r.year_redated), "sentence": r.sentence[:200]}
                             for r in mv.itertuples()]
        (root / "data" / "label_year_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
        print(f"Label-year audit (rule in use: {rule}). rows_<rule> = training rows of model Y; leak_<rule> = those "
              f"whose text (4+ words) also appears verbatim in a docs_to_score.parquet document dated Y or later; "
              f"first_<rule> = those whose earliest such document is dated Y or later:")
        print(pd.DataFrame(audit["per_test_year"]).T.to_string())
    else:
        print(f"note: {DOCS_PATH} missing, so the label-year audit and the `redated` rule are unavailable")
    lab.to_parquet(labels_path(root), index=False)

    # (1) the dataset card's own mapping
    card = Path(hf_hub_download(DATASET_ID, "README.md", repo_type="dataset", revision=DATASET_REV)).read_text(
        encoding="utf-8")
    card_map = {int(k): v.strip().lower() for k, v in re.findall(r"LABEL_(\d)\s*:\s*([A-Za-z]+)", card)}
    if card_map != CARD_EXPECTED:
        raise SystemExit(f"dataset card mapping {card_map} differs from {CARD_EXPECTED}")
    # (2) cue words in the labelled sentences
    def cue_counts(pats):
        m = lab.sentence.str.contains("|".join(pats), case=False, regex=True)
        return {LABELS[k]: int(v) for k, v in lab.loc[m, "label"].value_counts().sort_index().items()}
    hc, dc = cue_counts(HAWK_CUES), cue_counts(DOVE_CUES)
    ok = hc.get("hawk", 0) > hc.get("dove", 0) and dc.get("dove", 0) > dc.get("hawk", 0)
    if not ok:
        raise SystemExit(f"cue-word check failed: hawkish cues {hc}, dovish cues {dc}")
    examples = {LABELS[k]: lab[lab.label == k].sentence.sample(3, random_state=1).tolist() for k in (0, 1, 2)}

    by_year = pd.crosstab(lab.year, lab.label.map(LABELS))
    print("Labelled rows by year (train + test):")
    print(pd.crosstab(lab.year, lab.label.map(LABELS), margins=True).to_string())
    rows_y = {y: int(train_mask(lab, rule, y).sum()) for y in test_years}
    print(f"Training rows per test year (rule {rule}):", rows_y)
    print(f"Label ids verified: dataset card {card_map}; hawkish cue sentences {hc}; dovish cue sentences {dc}")
    check = {"dataset": DATASET_ID, "revision": DATASET_REV, "files": files, "n_rows": int(len(lab)),
             "card_mapping": card_map, "mapping_used": LABELS, "hawk_cue_counts": hc, "dove_cue_counts": dc,
             "hawk_cues": HAWK_CUES, "dove_cues": DOVE_CUES, "examples": examples,
             "rows_by_year_label": {int(y): {k: int(v) for k, v in r.items()} for y, r in by_year.iterrows()},
             "label_year_rule": rule, "label_dates": ld_info, "train_rows_per_test_year": rows_y,
             "n_duplicate_sentences": int(lab.sentence.duplicated().sum())}
    (root / "data" / "label_check.json").write_text(json.dumps(check, indent=2), encoding="utf-8")

    get_sent_tokenize(root, download=True)
    print("Punkt:", punkt_fingerprint())
    if not a.no_models:
        years = sorted(set(YEARS) | set(getattr(a, "years", None) or []))
        revs = {}
        for mid in sorted({base_model_id(y) for y in years}):
            p = Path(snapshot_download(mid, allow_patterns=["*.json", "*.safetensors", "*.txt"]))
            revs[mid] = p.name
            log("base model cached", mid, p.name)
        (root / "data" / "base_models.json").write_text(json.dumps(revs, indent=2), encoding="utf-8")
    log("prepare done:", labels_path(root))


# ----------------------------------------------------------------------------------------------------------------
# train
# ----------------------------------------------------------------------------------------------------------------
def stratified_split(lab: pd.DataFrame, frac: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (fit_idx, val_idx) positions into lab (already in canonical order)."""
    rs = np.random.RandomState(seed)
    val = []
    y = lab.label.to_numpy()
    for c in (0, 1, 2):
        idx = np.flatnonzero(y == c)
        k = int(round(frac * len(idx)))
        val.extend(idx[rs.permutation(len(idx))[:k]].tolist())
    val = np.array(sorted(val), dtype=int)
    fit = np.setdiff1d(np.arange(len(lab)), val)
    return fit, val


def macro_f1(y: np.ndarray, p: np.ndarray, k: int = 3) -> float:
    f = []
    for c in range(k):
        tp = int(((p == c) & (y == c)).sum())
        fp = int(((p == c) & (y != c)).sum())
        fn = int(((p != c) & (y == c)).sum())
        f.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    return float(np.mean(f))


def model_dir(root: Path, year: int, seed: int) -> Path:
    return root / "models" / str(year) / f"seed_{seed}"


def model_done(root: Path, year: int, seed: int, max_epochs: int = HP["max_epochs"],
               label_year: str | None = None) -> bool:
    m = model_dir(root, year, seed) / "metrics.json"
    if not m.exists():
        return False
    try:
        j = json.loads(m.read_text(encoding="utf-8"))
    except Exception:
        return False
    rule = label_year or LABEL_YEAR_DEFAULT
    return (bool(j.get("done")) and j.get("hp", {}).get("max_epochs") == max_epochs
            and j.get("label_year_rule", "dataset") == rule)


def resolve_base(mid: str) -> tuple[str, str]:
    from huggingface_hub import snapshot_download
    p = Path(snapshot_download(mid, allow_patterns=["*.json", "*.safetensors", "*.txt"]))
    return str(p), p.name


def pick_device():
    import torch
    return torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu")


def batches_for(enc_ids, order, bs):
    for k in range(0, len(order), bs):
        yield order[k:k + bs]


def collate(ids_list, pad_id, device):
    import torch
    n = max(len(x) for x in ids_list)
    ids = torch.full((len(ids_list), n), pad_id, dtype=torch.long)
    att = torch.zeros((len(ids_list), n), dtype=torch.long)
    for i, x in enumerate(ids_list):
        ids[i, :len(x)] = torch.tensor(x, dtype=torch.long)
        att[i, :len(x)] = 1
    return ids.to(device, non_blocking=True), att.to(device, non_blocking=True)


def predict_probs(model, ids_all, pad_id, device, bs=128, autocast_dtype=None):
    import torch
    order = np.argsort([len(x) for x in ids_all])[::-1]
    out = np.zeros((len(ids_all), 3), dtype=np.float32)
    model.eval()
    with torch.inference_mode():
        for idx in batches_for(ids_all, order, bs):
            ids, att = collate([ids_all[i] for i in idx], pad_id, device)
            if autocast_dtype is not None:
                with torch.autocast(device.type, dtype=autocast_dtype):
                    lg = model(input_ids=ids, attention_mask=att).logits
            else:
                lg = model(input_ids=ids, attention_mask=att).logits
            out[idx] = torch.softmax(lg.float(), dim=-1).cpu().numpy()
    return out


def cmd_train(a) -> None:
    import torch
    import transformers
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

    root = get_root(a.root)
    Y, S = a.year, a.seed
    hp = dict(HP)
    hp["max_epochs"] = a.max_epochs
    out = model_dir(root, Y, S)
    ycol = label_year_col(a.label_year)
    if model_done(root, Y, S, hp["max_epochs"], a.label_year) and not a.force:
        log(f"model {Y}/seed_{S} already done; skipping (use --force to retrain)")
        return
    t0 = time.time()
    lab_all = pd.read_parquet(labels_path(root))
    if ycol not in lab_all.columns:
        raise SystemExit(f"{labels_path(root)} has no {ycol} column; rerun `prepare` "
                         f"({'label_dates.parquet' if a.label_year == 'true' else 'docs_to_score.parquet'} needed)")
    use = train_mask(lab_all, a.label_year, Y)
    lab = lab_all[use].sort_values(["year", "sentence", "label", "orig_index"], kind="mergesort")
    lab = lab.reset_index(drop=True)
    if len(lab) == 0:
        raise SystemExit(f"no labelled rows for model {Y} under rule {a.label_year}")
    sel = {"rows_total": int(len(lab_all)), "rows_used": int(len(lab)),
           "rows_dataset_rule": int((lab_all.year <= Y - 1).sum())}
    if "source_date" in lab_all.columns:
        undated = lab_all.source_date.isna()
        sel.update({"rows_dated_used": int((use & ~undated).sum()), "rows_undated_used": int((use & undated).sum()),
                    "rows_undated_excluded": int((~use & undated).sum()),
                    "rows_dated_excluded": int((~use & ~undated).sum()),
                    "source_date_max_used": (str(lab.source_date.max().date())
                                             if lab.source_date.notna().any() else None)})
    if "corpus_last_date" in lab_all.columns:
        sel["rows_text_in_docs_dated_Y_or_later"] = int(
            (use & (lab_all.corpus_last_date >= pd.Timestamp(f"{Y}-01-01"))).sum())
    try:
        sel["label_dates_sha256"] = (json.loads((root / "data" / "label_check.json").read_text(encoding="utf-8"))
                                     .get("label_dates") or {}).get("sha256")
    except (OSError, ValueError):
        sel["label_dates_sha256"] = None
    fit_i, val_i = stratified_split(lab, hp["val_frac"], hp["split_seed"])
    base = base_model_id(Y)
    base_path, base_rev = resolve_base(base)

    transformers.set_seed(S)
    dev = pick_device()
    tok = AutoTokenizer.from_pretrained(base_path)
    model = AutoModelForSequenceClassification.from_pretrained(
        base_path, num_labels=3, id2label={i: LABELS[i] for i in LABELS},
        label2id={v: k for k, v in LABELS.items()}).to(dev)
    ids_all = tok(lab.sentence.tolist(), truncation=True, max_length=hp["max_len"])["input_ids"]
    n_trunc = int(sum(len(x) >= hp["max_len"] for x in ids_all))
    y_all = lab.label.to_numpy()
    pad_id = tok.pad_token_id

    decay, no_decay = [], []
    for n, p in model.named_parameters():
        (no_decay if (n.endswith("bias") or "norm" in n.lower()) else decay).append(p)
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": hp["weight_decay"]},
                             {"params": no_decay, "weight_decay": 0.0}], lr=hp["lr"])
    steps_per_epoch = math.ceil(len(fit_i) / hp["batch_size"])
    total = steps_per_epoch * hp["max_epochs"]
    warm = math.ceil(hp["warmup_ratio"] * total)
    sch = get_linear_schedule_with_warmup(opt, warm, total)
    use_bf16 = dev.type == "cuda" and torch.cuda.is_bf16_supported()
    amp = torch.bfloat16 if use_bf16 else None
    gen = torch.Generator().manual_seed(S)

    best_f1, best_ep, best_state, bad, hist = -1.0, 0, None, 0, []
    for ep in range(1, hp["max_epochs"] + 1):
        model.train()
        te = time.time()
        perm = torch.randperm(len(fit_i), generator=gen).numpy()
        order = fit_i[perm]
        loss_sum, nb = 0.0, 0
        for idx in batches_for(ids_all, order, hp["batch_size"]):
            ids, att = collate([ids_all[i] for i in idx], pad_id, dev)
            yb = torch.as_tensor(y_all[idx], dtype=torch.long, device=dev)
            with torch.autocast(dev.type, dtype=amp, enabled=amp is not None):
                logits = model(input_ids=ids, attention_mask=att).logits
            loss = torch.nn.functional.cross_entropy(logits.float(), yb)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), hp["max_grad_norm"])
            opt.step()
            sch.step()
            loss_sum += float(loss.detach())
            nb += 1
        pv = predict_probs(model, [ids_all[i] for i in val_i], pad_id, dev, autocast_dtype=amp).argmax(1)
        f1 = macro_f1(y_all[val_i], pv)
        acc = float((pv == y_all[val_i]).mean())
        hist.append({"epoch": ep, "train_loss": round(loss_sum / max(nb, 1), 5), "val_macro_f1": round(f1, 5),
                     "val_acc": round(acc, 5), "sec": round(time.time() - te, 1)})
        log(f"Y={Y} seed={S} epoch {ep}: loss {loss_sum / max(nb, 1):.4f} val macro-F1 {f1:.4f} acc {acc:.4f} "
            f"({time.time() - te:.1f}s)")
        if f1 > best_f1:
            best_f1, best_ep, bad = f1, ep, 0
            best_state = {k: v.detach().to("cpu", copy=True) for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= hp["patience"]:
                log(f"early stop after epoch {ep} (best epoch {best_ep})")
                break
    model.load_state_dict(best_state)
    tmp = out.with_name(out.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    model.save_pretrained(tmp, safe_serialization=True)
    tok.save_pretrained(tmp)
    cls = {LABELS[c]: int((y_all == c).sum()) for c in (0, 1, 2)}
    metrics = {
        "done": True, "year": Y, "seed": S, "base_model": base, "base_revision": base_rev,
        "label_dataset": DATASET_ID, "label_revision": DATASET_REV, "label_year_rule": a.label_year,
        "label_year_max_used": (int(lab[ycol].max()) if a.label_year != "true" else
                                int(lab.source_date.dt.year.max()) if lab.source_date.notna().any() else None),
        "label_selection": sel,
        "label_years": [int(lab.year.min()), int(lab.year.max())], "train_rows": int(len(lab)),
        "n_fit": int(len(fit_i)), "n_val": int(len(val_i)), "class_counts": cls,
        "n_truncated_at_max_len": n_trunc, "hp": hp, "val_macro_f1": round(best_f1, 5), "best_epoch": best_ep,
        "epochs_run": len(hist), "history": hist, "precision_train": "bf16 autocast" if use_bf16 else "fp32",
        "device": torch.cuda.get_device_name(0) if dev.type == "cuda" else "cpu", "torch": torch.__version__,
        "transformers": transformers.__version__, "train_sec": round(time.time() - t0, 1),
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (tmp / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    if out.exists():
        shutil.rmtree(out)
    tmp.rename(out)
    log(f"saved {out} (val macro-F1 {best_f1:.4f}, best epoch {best_ep}, {time.time() - t0:.0f}s)")


# ----------------------------------------------------------------------------------------------------------------
# score
# ----------------------------------------------------------------------------------------------------------------
def load_docs() -> pd.DataFrame:
    if not DOCS_PATH.exists():
        raise SystemExit(f"{DOCS_PATH} missing; run `export`")
    return pd.read_parquet(DOCS_PATH)


def read_score_meta(root: Path, year: int) -> dict | None:
    p = root / "scores" / f"{year}_meta.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def score_problems(meta: dict | None, max_epochs: int = HP["max_epochs"], seeds=SEEDS,
                   rule: str | None = None) -> list[str]:
    """Why a year's scores are not a full-spec scoring (empty list = full: all seeds, all docs, epoch cap)."""
    if meta is None:
        return ["no score meta"]
    out = []
    if meta.get("partial"):
        out.append("partial seeds")
    if sorted(meta.get("seeds") or []) != sorted(seeds):
        out.append(f"seeds {meta.get('seeds')}")
    if meta.get("limit_docs"):
        out.append(f"limit_docs {meta.get('limit_docs')}")
    if meta.get("sources", "all") != "all":
        out.append(f"sources {meta.get('sources')}")
    if meta.get("max_epochs") != max_epochs:
        out.append(f"max_epochs {meta.get('max_epochs')}")
    if rule is not None and meta.get("label_year_rule", "dataset") != rule:
        out.append(f"label_year_rule {meta.get('label_year_rule', 'dataset')}")
    return out


def share_frame(s: pd.DataFrame, keys) -> pd.DataFrame:
    g = s.groupby(keys)
    o = pd.DataFrame({"n_sentences": g.size(),
                      "share_hawk": g.label.apply(lambda x: float((x == "hawk").mean())),
                      "share_dove": g.label.apply(lambda x: float((x == "dove").mean())),
                      "share_neut": g.label.apply(lambda x: float((x == "neut").mean()))})
    o["score"] = o.share_hawk - o.share_dove
    return o


def cmd_score(a) -> None:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    root = get_root(a.root)
    Y = a.year
    max_ep = a.max_epochs
    seeds = [s for s in a.seeds if model_done(root, Y, s, max_ep, a.label_year)]
    missing = sorted(set(a.seeds) - set(seeds))
    if missing and not a.allow_partial:
        raise SystemExit(f"year {Y}: models missing for seeds {missing} (use --allow-partial to score anyway)")
    if not seeds:
        raise SystemExit(f"year {Y}: no finished model")
    docs = load_docs()
    docs = docs[docs.year == Y]
    if a.sources:
        docs = docs[docs.source.isin(a.sources)]
    if a.limit_docs:
        docs = docs.groupby("source", group_keys=False).head(a.limit_docs)
    sent_tokenize = get_sent_tokenize(root)
    t0 = time.time()
    rows = []
    for r in docs.itertuples(index=False):
        for i, s in enumerate(split_units(r.text, sent_tokenize)):
            rows.append((r.doc_id, r.source, r.date, i, s, bool(ROSTER.match(s))))
    S = pd.DataFrame(rows, columns=["doc_id", "source", "date", "sent_idx", "sentence", "roster"])
    t_split = time.time() - t0
    log(f"year {Y}: {len(docs)} docs, {len(S)} sentences, seeds {seeds} (split {t_split:.1f}s)")
    dev = pick_device()
    probs, meta_seeds = [], {}
    n_trunc = 0
    for s in seeds:
        md = model_dir(root, Y, s)
        tok = AutoTokenizer.from_pretrained(md)
        model = AutoModelForSequenceClassification.from_pretrained(md).to(dev).float().eval()
        assert {int(k): v for k, v in model.config.id2label.items()} == LABELS, model.config.id2label
        ids = tok(S.sentence.tolist(), truncation=True, max_length=HP["max_len"])["input_ids"]
        n_trunc = int(sum(len(x) >= HP["max_len"] for x in ids))
        p = predict_probs(model, ids, tok.pad_token_id, dev, bs=a.batch_size)
        probs.append(p)
        S[f"p_hawk_s{s}"] = p[:, 1].astype("float32")
        S[f"p_dove_s{s}"] = p[:, 0].astype("float32")
        meta_seeds[s] = json.loads((md / "metrics.json").read_text(encoding="utf-8"))["val_macro_f1"]
        del model
        if dev.type == "cuda":
            torch.cuda.empty_cache()
    P = np.mean(probs, axis=0) if len(S) else np.zeros((0, 3), dtype=np.float32)
    S["p_dove"], S["p_hawk"], S["p_neut"] = P[:, 0], P[:, 1], P[:, 2]
    S["label"] = [LABELS[int(k)] for k in P.argmax(1)] if len(S) else []
    S["model_year"] = Y
    sd = root / "scores"
    sd.mkdir(parents=True, exist_ok=True)
    S.to_parquet(sd / f"{Y}.parquet", index=False, compression="zstd")

    D = docs[["doc_id", "source", "date", "year", "meeting", "n_words"]].set_index("doc_id")
    allf = share_frame(S, "doc_id")
    exr = share_frame(S[~S.roster], "doc_id")[["n_sentences", "score"]].add_suffix("_excl_roster")
    D = D.join(allf).join(exr)
    D["n_sentences"] = D.n_sentences.fillna(0).astype(int)
    D["n_sentences_excl_roster"] = D.n_sentences_excl_roster.fillna(0).astype(int)
    D["model_year"] = Y
    D["base_model"] = base_model_id(Y)
    D["seeds"] = ",".join(map(str, seeds))
    D["label_year_rule"] = a.label_year
    D = D.reset_index()
    D.to_parquet(sd / f"{Y}_docs.parquet", index=False)
    meta = {"year": Y, "seeds": seeds, "label_year_rule": a.label_year, "max_epochs": max_ep,
            "seed_val_macro_f1": meta_seeds, "n_docs": int(len(D)),
            "n_docs_no_sentences": int((D.n_sentences == 0).sum()), "n_sentences": int(len(S)),
            "n_truncated_at_256": n_trunc, "precision": "fp32", "punkt": punkt_fingerprint(),
            "device": torch.cuda.get_device_name(0) if dev.type == "cuda" else "cpu",
            "seed_label_agreement": (float(np.mean([(p.argmax(1) == P.argmax(1)).mean() for p in probs]))
                                     if len(S) else None),
            "sec": round(time.time() - t0, 1), "partial": bool(missing), "sources": a.sources or "all",
            "limit_docs": a.limit_docs}
    (sd / f"{Y}_meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    print(D.groupby("source").agg(n_docs=("doc_id", "size"), sentences=("n_sentences", "sum"),
                                  mean_score=("score", "mean")).to_string())
    log(f"wrote {sd / f'{Y}.parquet'} and {Y}_docs.parquet ({time.time() - t0:.0f}s)")


# ----------------------------------------------------------------------------------------------------------------
# merge
# ----------------------------------------------------------------------------------------------------------------
def cmd_merge(a) -> None:
    root = get_root(a.root)
    sd = root / "scores"
    years = [y for y in a.years if (sd / f"{y}_docs.parquet").exists()]
    absent = sorted(set(a.years) - set(years))
    if not years:
        raise SystemExit("no scored years")
    D = pd.concat([pd.read_parquet(sd / f"{y}_docs.parquet") for y in years], ignore_index=True)
    S = pd.concat([pd.read_parquet(sd / f"{y}.parquet", columns=["doc_id", "source", "roster", "label"])
                   for y in years], ignore_index=True)
    rules = sorted(set(D.get("label_year_rule", pd.Series(["dataset"])).fillna("dataset")))
    if len(rules) > 1:
        raise SystemExit(f"scored years mix label-year rules {rules}; rescore them with one rule")
    # smoke-test scores (fewer seeds or epochs, a document subset) may be merged locally but never published
    nonspec = {y: p for y in years if (p := score_problems(read_score_meta(root, y)))}
    if nonspec and not a.no_publish:
        raise SystemExit(f"not a full-spec scoring, refusing to publish into the repo: {nonspec}. "
                         f"Rescore those years, or merge with --no-publish.")
    D = D.sort_values(["date", "source", "doc_id"]).reset_index(drop=True)
    D.to_parquet(sd / "doc_scores_chrono.parquet", index=False)

    # press-conference tables (H1): answers and meetings
    ans = D[D.source == "presser_answer"].copy()
    q = D[D.source == "presser_question"][["doc_id", "score", "n_sentences"]].copy()
    q["answer_id"] = q.doc_id.str.slice(2)
    ans = ans.rename(columns={"doc_id": "answer_id", "share_hawk": "hawk", "share_dove": "dove",
                              "share_neut": "neut"})
    ans = ans.merge(q[["answer_id", "score", "n_sentences"]].rename(
        columns={"score": "question_score", "n_sentences": "q_n_sentences"}), on="answer_id", how="left")
    ans = ans[["meeting", "answer_id", "date", "n_words", "n_sentences", "hawk", "dove", "neut", "score",
               "question_score", "q_n_sentences", "model_year", "seeds"]].sort_values(["meeting", "answer_id"])
    stm = D[D.source == "presser_statement"].set_index("meeting")
    M = pd.DataFrame({"meeting": sorted(set(ans.meeting) | set(stm.index))})
    M["date"] = pd.to_datetime(M.meeting)
    M["statement_score"] = M.meeting.map(stm.score_excl_roster)
    M["statement_score_incl_roster"] = M.meeting.map(stm.score)
    M["statement_n_sentences"] = M.meeting.map(stm.n_sentences_excl_roster)
    sc = ans[ans.n_sentences > 0]
    M["qa_mean"] = M.meeting.map(sc.groupby("meeting").score.mean())
    M["qa_mean_ge40w"] = M.meeting.map(sc[sc.n_words >= 40].groupby("meeting").score.mean())
    sa = S[S.source == "presser_answer"].copy()
    sa["meeting"] = sa.doc_id.str.slice(0, 8)
    M["qa_pooled"] = M.meeting.map(share_frame(sa, "meeting").score)
    M["q_mean"] = M.meeting.map(ans[ans.q_n_sentences > 0].groupby("meeting").question_score.mean())
    M["n_answers"] = M.meeting.map(ans.groupby("meeting").size())
    M["n_answers_scorable"] = M.meeting.map(sc.groupby("meeting").size())
    M["H1"] = M.qa_mean - M.statement_score
    M["model_year"] = M.date.dt.year
    ans.to_parquet(sd / "presser_answers_chrono.parquet", index=False)
    M.to_parquet(sd / "presser_meetings_chrono.parquet", index=False)
    meta = {"years_merged": years, "years_absent": absent, "n_docs": int(len(D)),
            "docs_by_source": D.source.value_counts().to_dict(), "n_answers": int(len(ans)),
            "n_meetings": int(len(M)), "label_year_rule": rules[0],
            "seeds_by_year": D.groupby("model_year").seeds.first().to_dict(), "nonspec_years": nonspec}
    (sd / "merge_meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    if not a.no_publish:
        PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
        for f in ("doc_scores_chrono.parquet", "presser_answers_chrono.parquet", "presser_meetings_chrono.parquet",
                  "merge_meta.json"):
            shutil.copy2(sd / f, PUBLISH_DIR / f)
    print(json.dumps(meta, indent=2, default=str))
    print(M[["meeting", "statement_score", "qa_mean", "H1", "n_answers_scorable"]].tail(8).to_string(index=False))


# ----------------------------------------------------------------------------------------------------------------
def parse_years(s: str) -> list[int]:
    out = []
    for part in str(s).split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        elif part.strip():
            out.append(int(part))
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=None, help="work root (default $CHRONO_ROOT or nlp/work)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--v2-corpus", required=True, help="folder with speeches.parquet and fomc_docs.parquet")
    e.add_argument("--presser-text", required=True, help="folder with answer_map/statements/meetings.parquet")
    p = sub.add_parser("prepare")
    p.add_argument("--no-models", action="store_true", help="skip pre-downloading the base models")
    p.add_argument("--years", type=parse_years, default=PREP_YEARS)
    p.add_argument("--label-year", choices=LABEL_YEAR_RULES, default=LABEL_YEAR_DEFAULT,
                   help="rule reported and checked (default $CHRONO_LABEL_YEAR or true); `true` requires "
                        "data/text_corpus/label_dates.parquet")
    t = sub.add_parser("train")
    t.add_argument("--year", type=int, required=True)
    t.add_argument("--seed", type=int, required=True)
    t.add_argument("--max-epochs", type=int, default=HP["max_epochs"], help="spec: 8 (lower only for smoke tests)")
    t.add_argument("--force", action="store_true")
    t.add_argument("--label-year", choices=LABEL_YEAR_RULES, default=LABEL_YEAR_DEFAULT,
                   help="true: source-document date < Y-01-01 (label_dates.parquet); dataset: dataset year <= Y-1; "
                        "redated: corpus re-dating <= Y-1 (default $CHRONO_LABEL_YEAR or true)")
    s = sub.add_parser("score")
    s.add_argument("--year", type=int, required=True)
    s.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    s.add_argument("--max-epochs", type=int, default=HP["max_epochs"], help="only models trained with this cap")
    s.add_argument("--allow-partial", action="store_true", help="score with the seeds that exist")
    s.add_argument("--label-year", choices=LABEL_YEAR_RULES, default=LABEL_YEAR_DEFAULT,
                   help="only models trained with this label-year rule")
    s.add_argument("--batch-size", type=int, default=128)
    s.add_argument("--sources", nargs="*", default=None)
    s.add_argument("--limit-docs", type=int, default=0, help="per source; smoke tests only")
    m = sub.add_parser("merge")
    m.add_argument("--years", type=parse_years, default=YEARS)
    m.add_argument("--no-publish", action="store_true", help="do not copy merged tables into the repo")
    a = ap.parse_args(argv)
    {"export": cmd_export, "prepare": cmd_prepare, "train": cmd_train, "score": cmd_score,
     "merge": cmd_merge}[a.cmd](a)


if __name__ == "__main__":
    main()
