"""Press-conference transcript provenance check (reviewer item 3b), plus the date checks of the other v2 documents.

Question: does the press-conference text that v2 scores faithfully represent what was said at the conference?

Read-only. It runs no backtest and no model; it reads committed files only and writes only into
results_2/provenance/. Run it from the repository root:

    python results_2/provenance/provenance_check.py

It exits with status 2 when an input is missing or when it is not started from the repository root.

Sources compared, per press conference:
  scored text   the `presser_doc` row of data/text_corpus/docs_to_score.parquet (the text v2 scores; one per
                conference, 2015-03-18..2026-09-16, 79 rows)
  transcript    the official transcript PDF text (backtests/presser/text/transcripts_utf8 for 2016+, the same
                extraction the press-conference study segmented; data/fomc_pressers/transcripts/*.txt otherwise),
                segmented into speaker turns with the committed rules of backtests/presser/text/code/segment.py
  captions      data/fomc_pressers/captions/<id>.vtt (the Board's WebVTT track). The captions carry the transcript
                text forced-aligned to the video, so they show transcript/caption identity, not what was said
  ASR           data/fedpress_features_local/meetings/<id>/asr/words.parquet (Whisper large-v3-turbo, no prompt,
                64 Powell conferences): the only source here that is independent of the edited transcript

Committed alignment outputs are read and reported beside the recomputation: backtests/presser/text/
align_meetings.parquet and turn_times.parquet (transcript vs captions, 75 conferences) and the feature package's
turns done-markers (wer_proxy, match_frac, timed_frac, vtt_check) and turns tables (64 conferences).

Rules (PROVENANCE.md says which were fixed before any table was computed and which were added after a first look):
  * tokens: the feature package's normaliser (hpg/fedpress_pkg/fedpress/stages/_align.py `norm_tokens`), applied
    word by word, with curly double quotes treated as straight ones; speaker labels are not transcript tokens;
    stage directions ([Laughter] etc.) are removed from the scored text, as the stance scorer does
  * alignment: difflib.SequenceMatcher(autojunk=False) matching blocks between two token lists; a token is
    "matched" when it lies in a matching block
  * passage: a gap between consecutive matching blocks with at least PASSAGE = 8 tokens on one side
  * transcript or scored words not in the ASR (>= 8 tokens) are explained, in this order: "found elsewhere in ASR"
    (>= 50% of the passage's 5-grams occur somewhere in the ASR: ASR segment order), "ASR audio gap" (the media
    time between the flanking ASR words is >= half the passage's expected speaking time at the meeting's own ASR
    token rate: speech was there, the ASR dropped it), "no ASR audio gap" (possibly not spoken: an edit, or an ASR
    omission with stretched word times), "edge of recording"
  * ASR words not in the transcript (>= 8 tokens, inside one Chair turn): "found elsewhere in transcript",
    "repetition loop" (fewer than half of the tokens distinct), otherwise "not in transcript"
  * non-chair text in the scored text: runs of >= LEAK_MIN_BLOCK = 4 consecutive scored tokens matched to a reporter
    or moderator turn; chair text missing from the scored text: transcript gaps of >= 8 tokens, mostly Chair tokens
  * footnotes: the editorial footnote lines that segment.py removes ("1 Chair Powell intended to say ..."), searched
    as token strings in the scored text, the captions and the H1 answer/question rows
  * lexicon screen: the frozen strategy-01 hawk/dove word lists (strategies/01/lexicon, 40 words, no negation rule)
  * ASR source mismatch: ASR coverage of the Chair's transcript words below 0.80 (the feature package's own
    min_matched_frac)
  * score bound: k affected and m missing sentence units, of N scored units, can move the document score (share
    hawkish minus share dovish) by at most 2(k + m) / (N - k); sentence ids come from a regex splitter and m from
    the document's mean tokens per unit, so the counts are approximate
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True  # never write __pycache__ into the committed code folders imported below

import difflib
import hashlib
import importlib.util
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

PASSAGE = 8
LEAK_MIN_BLOCK = 4
ASR_MISMATCH = 0.80
EXAMPLE_WORDS = 12

ROOT = Path.cwd()
OUT = ROOT / "results_2" / "provenance"

INPUTS = {
    "docs": "data/text_corpus/docs_to_score.parquet",
    "doc_scores": "backtests/v2/score/doc_scores.parquet",
    "turns": "backtests/presser/text/turns.parquet",
    "turn_times": "backtests/presser/text/turn_times.parquet",
    "align_meetings": "backtests/presser/text/align_meetings.parquet",
    "segment_log": "backtests/presser/text/segment_log.json",
    "answer_map": "backtests/presser/text/answer_map.parquet",
    "segment_code": "backtests/presser/text/code/segment.py",
    "align_code": "hpg/fedpress_pkg/fedpress/stages/_align.py",
    "transcripts_utf8": "backtests/presser/text/transcripts_utf8",
    "transcripts": "data/fomc_pressers/transcripts",
    "captions": "data/fomc_pressers/captions",
    "missing_captions": "data/fomc_pressers/missing_captions.txt",
    "features": "data/fedpress_features_local/meetings",
    "manifest": "docs/research/fed_presser_hpg/manifest/pressers.csv",
    "hawk": "strategies/01/lexicon/hawk.txt",
    "dove": "strategies/01/lexicon/dove.txt",
    "signals": "backtests/results/v2_oos/run/signals_entry_session.parquet",
}
FROZEN_LEXICON_SHA256 = {  # backtests/presser/text/build_meta.json
    "hawk": "ceead1cae1edd8a2acef83e20dfe2bc5934494d20339d756f912f22dd7cf33bf",
    "dove": "2d43390600d89c7c113b6007bc36c74b37e56dc461a7e7865259acc6981ce5ae",
}
STAGE = re.compile(r"\[\s*(?:laughter|cough|inaudible|no response|extended pause|pause|crosstalk|applause)\s*\]", re.I)
BRACKET = re.compile(r"\[([^\]\n]{1,80})\]")
FNCALL = re.compile(r"(?<=[a-z\)”\"’])([.;,?!])\d{1,2}(?=\s|$)")
TS = re.compile(r"^((?:\d+:)?\d+:\d+\.\d+)\s+-->\s+((?:\d+:)?\d+:\d+\.\d+)")
SENT_SPLIT = re.compile(r"(?<=[.!?])[\"”’)\]]*\s+(?=[\"“(\[]?[A-Z0-9])")
CHAIR_EXTRA = ("BERNANKE",)  # segment.py knows POWELL, YELLEN, WARSH (its 2016+ sample); Bernanke chairs 2011-2013


def die(msg: str) -> None:
    print(f"provenance_check: {msg}", file=sys.stderr)
    sys.exit(2)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def check_inputs() -> dict[str, Path]:
    if not (ROOT / "backtests").is_dir() or not (ROOT / "preregistration").is_dir():
        die("run from the repository root (backtests/ and preregistration/ not found here)")
    paths = {k: ROOT / v for k, v in INPUTS.items()}
    missing = [INPUTS[k] for k, p in paths.items() if not p.exists()]
    if missing:
        die("missing input(s): " + ", ".join(missing))
    for k in ("hawk", "dove"):
        if sha256(paths[k]) != FROZEN_LEXICON_SHA256[k]:
            die(f"{INPUTS[k]} does not match the frozen lexicon hash")
    return paths


# ------------------------------------------------------------------------------------------------------------------
def tokens_of(text: str, norm) -> list[str]:
    out: list[str] = []
    for w in text.split():
        out.extend(norm(w))
    return out


def sentence_tokens(text: str, norm) -> tuple[list[str], list[int], int, list[bool]]:
    """Tokens of the scored text (stage directions removed, as the scorer does), an approximate sentence id per
    token (regex splitter on paragraphs) and a flag for tokens inside an editor's square brackets."""
    toks, sid, brk, k = [], [], [], 0
    for para in re.split(r"\n+", text or ""):
        p = " ".join(STAGE.sub(" ", para).split())
        if not p:
            continue
        for s in SENT_SPLIT.split(p):
            n0 = len(toks)
            depth = 0
            for w in s.split():
                inside = depth > 0 or "[" in w
                depth += w.count("[") - w.count("]")
                depth = max(depth, 0)
                t = norm(w)
                toks += t
                brk += [inside] * len(t)
            if len(toks) == n0:
                continue
            sid += [k] * (len(toks) - n0)
            k += 1
    return toks, sid, k, brk


def blocks(a: list[str], b: list[str]):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks()


def matched_mask(n: int, bl, side: int) -> np.ndarray:
    m = np.zeros(n, dtype=bool)
    for blk in bl:
        i = blk[side]
        if blk.size:
            m[i:i + blk.size] = True
    return m


def gaps(bl):
    """(a0, a1, b0, b1) for every gap between consecutive matching blocks, including both ends."""
    out, pa, pb = [], 0, 0
    for blk in bl:
        a, b, n = blk
        if a > pa or b > pb:
            out.append((pa, a, pb, b))
        pa, pb = a + n, b + n
    return out


UNHEARD = ("found elsewhere in ASR (ASR segment order)", "ASR audio gap (speech present, ASR omitted it)",
           "no ASR audio gap (possibly not spoken: edit)", "edge of recording")
EXTRA = ("found elsewhere in transcript (ASR segment order)", "repetition loop (ASR artefact)",
         "not in transcript (disfluency edited out, or ASR insertion)")


def ngram_list(toks: list[str], n: int) -> list[tuple]:
    return [tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)]


def ngram_set(toks: list[str], n: int) -> set:
    return set(ngram_list(toks, n))


def excerpt(toks: list[str]) -> str:
    s = " ".join(toks[:EXAMPLE_WORDS])
    return s + (" ..." if len(toks) > EXAMPLE_WORDS else "")


def parse_vtt(path: Path) -> str:
    cues, cur = [], None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if TS.match(s):
            cur = []
            cues.append(cur)
        elif cur is not None and s:
            cur.append(s)
        elif not s:
            cur = None
    return " ".join(" ".join(c) for c in cues)


def assign_roles(turns: list[dict], seg) -> list[dict]:
    """segment.py's role rule, with Bernanke added as a chair surname (2011-2013 only)."""
    def is_chair(spk: str) -> bool:
        tok = spk.split()
        extra = len(tok) == 2 and tok[1] in CHAIR_EXTRA and tok[0].startswith("CH") and \
            difflib.SequenceMatcher(None, tok[0], "CHAIRMAN").ratio() >= 0.7
        return seg.is_chair(spk) or extra
    seen_other = False
    for t in turns:
        if t["role"] == "preamble":
            continue
        if is_chair(t["speaker"]):
            t["role"] = "answer" if seen_other else "opening"
        elif seg.is_moderator(t["speaker"]):
            t["role"], seen_other = "moderator", True
        else:
            t["role"], seen_other = "question", True
    return turns


# ------------------------------------------------------------------------------------------------------------------
def main() -> None:
    P = check_inputs()
    al = load_module("fedpress_align_ro", P["align_code"])
    seg = load_module("presser_segment_ro", P["segment_code"])
    def norm(word: str) -> list[str]:  # the package normaliser; curly double quotes treated as straight ones
        return al.norm_tokens(word.replace("“", '"').replace("”", '"'))
    hawk = {w.strip().lower() for w in P["hawk"].read_text(encoding="utf-8").split() if w.strip()}
    dove = {w.strip().lower() for w in P["dove"].read_text(encoding="utf-8").split() if w.strip()}
    lex = hawk | dove

    docs = pd.read_parquet(P["docs"])
    ds = pd.read_parquet(P["doc_scores"])
    turns_c = pd.read_parquet(P["turns"])
    tt = pd.read_parquet(P["turn_times"])
    am = pd.read_parquet(P["align_meetings"]).set_index("meeting")
    seglog = json.loads(P["segment_log"].read_text(encoding="utf-8"))
    man = pd.read_csv(P["manifest"], dtype={"presser_id": str}).set_index("presser_id")
    missing_vtt = set(P["missing_captions"].read_text(encoding="utf-8").split())

    scored = docs[docs.source == "presser_doc"].copy()
    scored["meeting"] = scored.doc_id.str.replace("presser_", "", regex=False)
    scored = scored.set_index("meeting")
    v2p = ds[ds.doc_type == "presser"].copy()
    v2p["meeting"] = v2p.doc_id.str.replace("presser_", "", regex=False)
    v2p = v2p.set_index("meeting")
    if set(scored.index) != set(v2p.index):
        die("presser_doc rows of docs_to_score and presser rows of the v2 document scores differ")

    meetings = sorted(re.search(r"(\d{8})", p.name).group(1) for p in P["transcripts"].glob("FOMCpresconf*.pdf"))
    if len(meetings) != 95:
        die(f"expected 95 transcript PDFs, found {len(meetings)}")
    feat = {p.name for p in P["features"].iterdir() if p.is_dir()}

    # file identity: repo copies vs the manifest's hashes of the Board files (VTT hashed after CRLF->LF)
    pdf_ok = vtt_ok = n_vtt = 0
    for m in meetings:
        pdf_ok += sha256(P["transcripts"] / f"FOMCpresconf{m}.pdf") == man.at[m, "local_pdf_sha256"]
        v = P["captions"] / f"{m}.vtt"
        if v.exists():
            n_vtt += 1
            b = v.read_bytes()
            vtt_ok += hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest() == man.at[m, "local_vtt_sha256"] or \
                hashlib.sha256(b).hexdigest() == man.at[m, "local_vtt_sha256"]

    rows, passages = [], []
    overlap_counts, overlap_tokens, footnotes_by_meeting = {}, {}, {}
    seg_check = {"meetings": 0, "identical": 0}
    for m in meetings:
        utf = P["transcripts_utf8"] / f"FOMCpresconf{m}.txt"
        if utf.exists():
            raw, tsrc = utf.read_text(encoding="utf-8"), "transcripts_utf8 (committed text-study input)"
        else:
            raw, tsrc = (P["transcripts"] / f"FOMCpresconf{m}.txt").read_text(encoding="latin-1"), \
                "data/fomc_pressers/transcripts .txt (Latin-1 extraction)"
        body, footnotes = seg.clean(raw)
        footnotes_by_meeting[m] = footnotes
        tlist = assign_roles(seg.segment(m, body), seg)
        tlist = [t for t in tlist if t["role"] != "preamble"]
        if utf.exists():  # the committed segmentation must be reproduced exactly
            g = turns_c[(turns_c.meeting == m) & (turns_c.role != "preamble")].sort_values("turn_idx")
            seg_check["meetings"] += 1
            seg_check["identical"] += int(len(g) == len(tlist) and all(
                a["text"] == b and a["role"] == c for a, b, c in zip(tlist, g.text, g.role)))
        T, Trole, Tturn = [], [], []
        speaker_of = {t["turn_idx"]: t["speaker"] for t in tlist}
        for t in tlist:
            tk = tokens_of(t["text"], norm)
            T += tk
            Trole += [t["role"]] * len(tk)
            Tturn += [t["turn_idx"]] * len(tk)
        Trole_a, Tturn_a = np.array(Trole), np.array(Tturn)
        chair_mask = np.isin(Trole_a, ["opening", "answer"])
        chair = man.at[m, "chair"]
        r = dict(meeting=m, date=man.at[m, "presser_date"], chair=chair, scheduled=bool(man.at[m, "scheduled"]),
                 in_v2_scored=m in scored.index, in_presser_text_study=utf.exists(),
                 transcript_source=tsrc, n_turns=len(tlist),
                 n_chair_turns=int(sum(t["role"] in ("opening", "answer") for t in tlist)),
                 transcript_tokens=len(T), transcript_chair_tokens=int(chair_mask.sum()),
                 n_footnotes_in_transcript=len(footnotes),
                 video_upload_day_lag=int((pd.Timestamp(man.at[m, "bc_created_at"]).tz_convert("America/New_York")
                                           .normalize().tz_localize(None) - pd.Timestamp(man.at[m, "presser_date"])).days),
                 video_duration_s=float(man.at[m, "duration_s"]))

        # ---------------- scored text vs transcript ----------------
        S, Ssid, nsent, Sbrk = ([], [], 0, [])
        if m in scored.index:
            text = scored.at[m, "text"]
            S, Ssid, nsent, Sbrk = sentence_tokens(text, norm)
            Ssid_a = np.array(Ssid)
            bl = blocks(S, T)
            s_role = np.full(len(S), "", dtype=object)
            t_cov = np.zeros(len(T), dtype=bool)
            for a, b, n in bl:
                if n:
                    s_role[a:a + n] = Trole_a[b:b + n]
                    t_cov[b:b + n] = True
            leak = np.zeros(len(S), dtype=bool)
            leak_runs = 0
            for a, b, n in bl:  # runs of >= LEAK_MIN_BLOCK consecutive scored tokens matched to non-chair turns
                if n < LEAK_MIN_BLOCK:
                    continue
                nc = ~np.isin(Trole_a[b:b + n], ["opening", "answer"])
                i = 0
                while i < n:
                    if nc[i]:
                        j = i
                        while j < n and nc[j]:
                            j += 1
                        if j - i >= LEAK_MIN_BLOCK:
                            leak[a + i:a + j] = True
                            leak_runs += 1
                            seg_t = T[b + i:b + j]
                            passages.append(dict(meeting=m, comparison="scored_vs_transcript",
                                                 kind="non-chair turn text inside scored text",
                                                 side="scored words from a reporter or moderator turn",
                                                 role=str(Trole_a[b + i]), transcript_tokens=j - i, asr_tokens=np.nan,
                                                 turn_idx=int(Tturn_a[b + i]),
                                                 explanation=f"speaker {speaker_of[int(Tturn_a[b + i])]}",
                                                 lexicon_hits=int(sum(x in lex for x in seg_t)),
                                                 numeric_tokens=int(sum(any(c.isdigit() for c in x) for x in seg_t)),
                                                 transcript_excerpt=excerpt(seg_t), asr_excerpt=""))
                        i = j
                    else:
                        i += 1
            # footnote text inside the scored text
            sjoin = " " + " ".join(S) + " "
            fn_in, fn_tok, fn_mask = 0, 0, np.zeros(len(S), dtype=bool)
            for f in footnotes:
                ft = tokens_of(f, norm)
                ft = ft[1:] if ft and ft[0].isdigit() else ft
                key = " " + " ".join(ft) + " "
                pos = sjoin.find(key)
                found = len(ft) >= 4 and pos >= 0
                if found:
                    fn_in += 1
                    fn_tok += len(ft)
                    start = sjoin[:pos].count(" ")
                    fn_mask[start:start + len(ft)] = True
                passages.append(dict(meeting=m, comparison="footnote", kind="editorial footnote of the transcript PDF",
                                     side="included in scored text" if found else "not in scored text",
                                     role="editor", transcript_tokens=len(ft), asr_tokens=np.nan, turn_idx=-1,
                                     explanation="written correction, not spoken",
                                     lexicon_hits=int(sum(x in lex for x in ft)),
                                     numeric_tokens=int(sum(any(c.isdigit() for c in x) for x in ft)),
                                     transcript_excerpt=excerpt(ft), asr_excerpt=""))
            # chair transcript text that the scored text lacks
            miss_tok = miss_lex = 0
            for g0, g1, h0, h1 in gaps(bl):
                if h1 - h0 >= PASSAGE and chair_mask[h0:h1].mean() > 0.5:
                    cm = chair_mask[h0:h1]
                    ct = [T[h0 + q] for q in np.flatnonzero(cm)]
                    miss_tok += len(ct)
                    miss_lex += sum(x in lex for x in ct)
                    first_chair = h0 + int(np.flatnonzero(cm)[0])
                    passages.append(dict(meeting=m, comparison="transcript_vs_scored",
                                         kind="chair transcript text missing from scored text",
                                         side="chair words not in scored text", role=str(Trole_a[first_chair]),
                                         transcript_tokens=len(ct), asr_tokens=np.nan,
                                         turn_idx=int(Tturn_a[first_chair]),
                                         explanation=f"turns {int(Tturn_a[h0])}-{int(Tturn_a[h1 - 1])}",
                                         lexicon_hits=int(sum(x in lex for x in ct)),
                                         numeric_tokens=int(sum(any(c.isdigit() for c in x) for x in ct)),
                                         transcript_excerpt=excerpt(ct), asr_excerpt=""))
            brk = [x for x in BRACKET.findall(text) if not STAGE.fullmatch(f"[{x}]")]
            brk_tok = sum(len(tokens_of(x, norm)) for x in brk)
            brk_lex = sum(sum(t in lex for t in tokens_of(x, norm)) for x in brk)
            labels = seg.LABEL.findall(text)
            not_in_t = (s_role == "") & ~fn_mask
            chair_gap_runs = sum(1 for g0, g1, h0, h1 in gaps(bl)
                                 if h1 - h0 >= PASSAGE and chair_mask[h0:h1].mean() > 0.5)
            r.update(v2_doc_id=scored.at[m, "doc_id"], v2_n_sentence_units=int(v2p.at[m, "n_sentences"]),
                     v2_stance_score=float(v2p.at[m, "rob_score"]), approx_sentences=nsent,
                     scored_tokens=len(S),
                     scored_share_in_chair_turns=float(np.isin(s_role, ["opening", "answer"]).mean()),
                     scored_share_in_nonchair_turns=float(np.isin(s_role, ["question", "moderator"]).mean()),
                     scored_share_not_in_transcript_turns=float((s_role == "").mean()),
                     chair_transcript_share_in_scored=float(t_cov[chair_mask].mean()) if chair_mask.any() else np.nan,
                     chair_passages_missing_from_scored=int(chair_gap_runs),
                     chair_tokens_missing_from_scored=int(miss_tok),
                     chair_missing_lexicon_hits=int(miss_lex),
                     scored_footnotes_included=fn_in, scored_footnote_tokens=fn_tok,
                     scored_footnote_call_markers=len(FNCALL.findall(text)),
                     scored_bracket_insertions=len(brk), scored_bracket_tokens=brk_tok,
                     scored_bracket_lexicon_hits=brk_lex,
                     scored_stage_directions=len(STAGE.findall(text)),
                     scored_speaker_labels=len(labels), scored_speaker_label_list=";".join(sorted(set(labels))),
                     scored_leak_runs=leak_runs, scored_leak_tokens=int(leak.sum()),
                     scored_other_tokens_not_in_transcript=int(not_in_t.sum()),
                     scored_footnote_lexicon_hits=int(sum(S[i] in lex for i in np.flatnonzero(fn_mask))),
                     scored_leak_lexicon_hits=int(sum(S[i] in lex for i in np.flatnonzero(leak))))
            brk_mask = np.array(Sbrk, dtype=bool)  # tokens of editor insertions in square brackets
            edits = fn_mask | leak
            affected = edits.copy()
        # ---------------- captions ----------------
        vpath = P["captions"] / f"{m}.vtt"
        r["captions_available"] = vpath.exists()
        if vpath.exists():
            V = tokens_of(parse_vtt(vpath), norm)
            vjoin = " " + " ".join(V) + " "
            fn_cap = 0  # editorial footnotes of the PDF that also appear in the caption track
            for f in footnotes:
                ft = tokens_of(f, norm)
                ft = ft[1:] if ft and ft[0].isdigit() else ft
                fn_cap += int(len(ft) >= 4 and (" " + " ".join(ft) + " ") in vjoin)
            r["n_footnotes_in_captions"] = fn_cap
            mt = matched_mask(len(T), blocks(T, V), 0)
            r.update(caption_tokens=len(V), caption_cov_transcript=float(mt.mean()),
                     caption_cov_transcript_chair=float(mt[chair_mask].mean()) if chair_mask.any() else np.nan)
            if S:
                r["caption_cov_scored"] = float(matched_mask(len(S), blocks(S, V), 0).mean())
            if m in am.index and bool(am.at[m, "captions"]):
                g = tt[(tt.meeting == m)].merge(turns_c[["meeting", "turn_idx", "role"]], on=["meeting", "turn_idx"])
                gc = g[g.role.isin(["opening", "answer"])]
                r.update(committed_caption_match_rate_all=float(am.at[m, "match_rate_all"]),
                         committed_caption_match_rate_qa=float(am.at[m, "match_rate_qa"]),
                         committed_caption_chair_turn_coverage=float(gc.n_matched.sum() / gc.n_tok.sum()))
        # ---------------- ASR ----------------
        r["asr_available"] = m in feat
        possible_edit_mask = None
        if m in feat:
            fdir = P["features"] / m
            wdf = pd.read_parquet(fdir / "asr" / "words.parquet")
            A, Aw = [], []
            for wi, w in enumerate(wdf.word.astype(str)):
                tk = norm(w)
                A += tk
                Aw += [wi] * len(tk)
            Aw_a = np.array(Aw, dtype=int)
            w_start, w_end = wdf.t_start_s.to_numpy(float), wdf.t_end_s.to_numpy(float)
            segs = pd.read_parquet(fdir / "asr" / "segments.parquet")
            speech_s = float((segs.t_end_s - segs.t_start_s).clip(lower=0).sum())
            rate = len(A) / speech_s if speech_s > 0 else np.nan  # ASR tokens per second of ASR speech
            A5, T5 = ngram_set(A, 5), ngram_set(T, 5)
            asr_meta = json.loads((fdir / "asr" / "asr.json").read_text(encoding="utf-8"))
            done = json.loads((fdir / "_done" / "turns.json").read_text(encoding="utf-8"))["notes"]
            tw = pd.read_parquet(fdir / "turns" / "words.parquet")
            ttab = pd.read_parquet(fdir / "turns" / "turns.parquet")
            tw = tw.merge(ttab[["turn_idx", "is_chair"]], on="turn_idx", how="left")
            vc = done.get("vtt_check") or {}
            blTA = blocks(T, A)
            mt = matched_mask(len(T), blTA, 0)
            r.update(asr_tokens=len(A), asr_audio_s=float(asr_meta.get("audio_s", np.nan)),
                     asr_initial_prompt=str(asr_meta.get("initial_prompt")),
                     asr_speech_tokens_per_s=round(rate, 4),
                     asr_cov_transcript=float(mt.mean()),
                     asr_cov_transcript_chair=float(mt[chair_mask].mean()) if chair_mask.any() else np.nan,
                     pkg_match_frac=done.get("match_frac"), pkg_wer_proxy=done.get("wer_proxy"),
                     pkg_timed_frac=done.get("timed_frac"),
                     pkg_chair_word_match_frac=float(tw.loc[tw.is_chair == True, "matched"].mean()),
                     pkg_vtt_check_n_words=vc.get("n_words"), pkg_vtt_check_median_abs_s=vc.get("median_abs_s"))

            def asr_gap_s(b0: int, b1: int) -> float:
                """Media seconds between the ASR words that flank an ASR-side gap (not a wall clock)."""
                if b0 <= 0 or b1 >= len(A):
                    return np.nan
                return float(w_start[Aw_a[b1]] - w_end[Aw_a[b0 - 1]])

            def explain_unheard(toks: list[str], b0: int, b1: int) -> tuple[str, float, float]:
                gap = asr_gap_s(b0, b1)
                expected = len(toks) / rate if rate == rate and rate > 0 else np.nan
                g = ngram_list(toks, 5)
                if g and np.mean([x in A5 for x in g]) >= 0.5:
                    return UNHEARD[0], gap, expected
                if gap != gap:
                    return UNHEARD[3], gap, expected
                if gap >= 0.5 * expected:
                    return UNHEARD[1], gap, expected
                return UNHEARD[2], gap, expected

            def explain_extra(toks: list[str]) -> str:
                g = ngram_list(toks, 5)
                if g and np.mean([x in T5 for x in g]) >= 0.5:
                    return EXTRA[0]
                if len(set(toks)) / max(1, len(toks)) < 0.5:
                    return EXTRA[1]
                return EXTRA[2]

            cnt = {k: 0 for k in UNHEARD + EXTRA}
            tok = {k: 0 for k in UNHEARD + EXTRA}
            ex_edit, ex_extra = [], []
            for a0, a1, b0, b1 in gaps(blTA):
                la, lb = a1 - a0, b1 - b0
                if max(la, lb) < PASSAGE:
                    continue
                kind = "transcript_only" if lb <= 2 else ("speech_only" if la <= 2 else "substituted")
                ta, sa = T[a0:a1], A[b0:b1]
                if la >= PASSAGE:  # transcript words with no ASR counterpart
                    role = "chair" if chair_mask[a0:a1].mean() > 0.5 else "reporter_or_moderator"
                    why, gap, expct = explain_unheard(ta, b0, b1)
                    passages.append(dict(meeting=m, comparison="transcript_vs_asr", kind=kind,
                                         side="transcript words not in ASR", role=role,
                                         transcript_tokens=la, asr_tokens=lb, turn_idx=int(Tturn_a[a0]),
                                         explanation=why,
                                         asr_gap_media_s=round(gap, 2) if gap == gap else np.nan,
                                         expected_speech_s=round(expct, 2) if expct == expct else np.nan,
                                         lexicon_hits=int(sum(x in lex for x in ta)),
                                         numeric_tokens=int(sum(any(c.isdigit() for c in x) for x in ta)),
                                         transcript_excerpt=excerpt(ta), asr_excerpt=excerpt(sa)))
                    if role == "chair":
                        cnt[why] += 1
                        tok[why] += la
                        if why == UNHEARD[2] and len(ex_edit) < 2:
                            ex_edit.append(excerpt(ta))
                if lb >= PASSAGE:  # ASR words with no transcript counterpart
                    left, right = a0 - 1, min(a1, len(T) - 1)
                    inside = a0 > 0 and a1 < len(T) and bool(chair_mask[left]) and bool(chair_mask[right]) and \
                        (Tturn_a[left] == Tturn_a[right] or bool(chair_mask[a0:a1].all()))
                    role = "chair" if inside else "other_or_edge"
                    why = explain_extra(sa)
                    passages.append(dict(meeting=m, comparison="transcript_vs_asr", kind=kind,
                                         side="ASR words not in transcript", role=role,
                                         transcript_tokens=la, asr_tokens=lb,
                                         turn_idx=int(Tturn_a[min(a0, len(T) - 1)]), explanation=why,
                                         asr_gap_media_s=np.nan, expected_speech_s=np.nan,
                                         lexicon_hits=int(sum(x in lex for x in sa)),
                                         numeric_tokens=int(sum(any(c.isdigit() for c in x) for x in sa)),
                                         transcript_excerpt=excerpt(ta), asr_excerpt=excerpt(sa)))
                    if role == "chair":
                        cnt[why] += 1
                        tok[why] += lb
                        if why == EXTRA[2] and len(ex_extra) < 2:
                            ex_extra.append(excerpt(sa))
            r.update(chair_unheard_passages=sum(cnt[k] for k in UNHEARD),
                     chair_unheard_tokens=sum(tok[k] for k in UNHEARD),
                     chair_unheard_elsewhere_in_asr=cnt[UNHEARD[0]], chair_unheard_audio_gap=cnt[UNHEARD[1]],
                     chair_unheard_no_audio_gap=cnt[UNHEARD[2]], chair_unheard_no_audio_gap_tokens=tok[UNHEARD[2]],
                     chair_unheard_edge=cnt[UNHEARD[3]],
                     chair_extra_speech_passages=sum(cnt[k] for k in EXTRA),
                     chair_extra_speech_tokens=sum(tok[k] for k in EXTRA),
                     chair_extra_elsewhere_in_transcript=cnt[EXTRA[0]], chair_extra_repetition_loop=cnt[EXTRA[1]],
                     chair_extra_other=cnt[EXTRA[2]], chair_extra_other_tokens=tok[EXTRA[2]],
                     example_chair_unheard_no_audio_gap=" || ".join(ex_edit),
                     example_chair_extra_other=" || ".join(ex_extra))
            if S:
                blSA = blocks(S, A)
                ms = matched_mask(len(S), blSA, 0)
                c2 = {k: 0 for k in UNHEARD}
                t2 = {k: 0 for k in UNHEARD}
                lex2 = {k: 0 for k in UNHEARD}
                num_edit = 0
                ex2 = []
                un_mask = np.zeros(len(S), dtype=bool)
                edit_mask = np.zeros(len(S), dtype=bool)
                for a0, a1, b0, b1 in gaps(blSA):
                    if a1 - a0 < PASSAGE:
                        continue
                    st = S[a0:a1]
                    why, gap, expct = explain_unheard(st, b0, b1)
                    over = "footnote" if fn_mask[a0:a1].mean() >= 0.5 else (
                        "non-chair turn" if leak[a0:a1].mean() >= 0.5 else (
                            "editor brackets" if brk_mask[a0:a1].any() else ""))
                    if why == UNHEARD[2] and r["asr_cov_transcript_chair"] >= ASR_MISMATCH:
                        overlap_counts[over or "none"] = overlap_counts.get(over or "none", 0) + 1
                        overlap_tokens[over or "none"] = overlap_tokens.get(over or "none", 0) + a1 - a0
                    c2[why] += 1
                    t2[why] += a1 - a0
                    lex2[why] += sum(x in lex for x in st)
                    un_mask[a0:a1] = True
                    if why == UNHEARD[2]:
                        edit_mask[a0:a1] = True
                        num_edit += sum(any(c.isdigit() for c in x) for x in st)
                        if len(ex2) < 2:
                            ex2.append(excerpt(st))
                    passages.append(dict(meeting=m, comparison="scored_vs_asr",
                                         kind="scored_only" if b1 - b0 <= 2 else "substituted",
                                         side="scored words not in ASR", role="scored text",
                                         transcript_tokens=a1 - a0, asr_tokens=b1 - b0, turn_idx=-1,
                                         explanation=why + (f"; overlaps {over}" if over else ""),
                                         asr_gap_media_s=round(gap, 2) if gap == gap else np.nan,
                                         expected_speech_s=round(expct, 2) if expct == expct else np.nan,
                                         lexicon_hits=int(sum(x in lex for x in st)),
                                         numeric_tokens=int(sum(any(c.isdigit() for c in x) for x in st)),
                                         transcript_excerpt=excerpt(st), asr_excerpt=excerpt(A[b0:b1])))
                r.update(asr_cov_scored=float(ms.mean()),
                         scored_unheard_passages=sum(c2.values()), scored_unheard_tokens=sum(t2.values()),
                         scored_unheard_lexicon_hits=sum(lex2.values()),
                         scored_unheard_elsewhere_in_asr=c2[UNHEARD[0]], scored_unheard_audio_gap=c2[UNHEARD[1]],
                         scored_unheard_edge=c2[UNHEARD[3]],
                         scored_no_audio_gap_passages=c2[UNHEARD[2]], scored_no_audio_gap_tokens=t2[UNHEARD[2]],
                         scored_no_audio_gap_lexicon_hits=lex2[UNHEARD[2]],
                         scored_no_audio_gap_numeric_tokens=num_edit,
                         example_scored_no_audio_gap=" || ".join(ex2))
                affected = affected | un_mask
                possible_edit_mask = edit_mask
        # ---------------- bound on the document score ----------------
        if S:
            n_units = int(v2p.at[m, "n_sentences"])

            def bound(mask: np.ndarray) -> tuple[int, float]:
                k = int(len(set(Ssid_a[mask].tolist()))) if mask.any() else 0
                return k, (float(2 * k / (n_units - k)) if n_units > k else np.nan)
            k1, b1 = bound(edits)
            r.update(affected_sentences_footnote_or_nonchair=k1, score_change_bound_footnote_or_nonchair=b1)
            # missing chair text: m_add sentence units would have to be added back (bound 2(k + m) / (N - k))
            per_unit = len(S) / n_units if n_units else np.nan
            m_add = int(np.ceil(r["chair_tokens_missing_from_scored"] / per_unit)) if per_unit == per_unit else 0
            r.update(missing_chair_sentences_approx=m_add,
                     score_change_bound_text_defects=float(2 * (k1 + m_add) / (n_units - k1)) if n_units > k1 else np.nan)
            k2, b2 = bound(edits | brk_mask)
            r.update(affected_sentences_incl_brackets=k2, score_change_bound_incl_brackets=b2)
            if r.get("asr_available") and r.get("asr_cov_transcript_chair", 0) >= ASR_MISMATCH:
                k3, b3 = bound(edits | brk_mask | possible_edit_mask)
                r.update(affected_sentences_incl_possible_edits=k3, score_change_bound_incl_possible_edits=b3)
                k4, b4 = bound(affected | brk_mask)
                r.update(affected_sentences_incl_all_unheard=k4, score_change_bound_incl_all_unheard=b4)
        rows.append(r)

    df = pd.DataFrame(rows)
    # ---------------- flags and class ----------------
    def flags(x) -> str:
        f = []
        if x.get("in_v2_scored"):
            if x.get("scored_footnotes_included", 0) > 0:
                f.append("editorial_footnote_scored")
            if x.get("scored_leak_tokens", 0) > 0 or x.get("scored_speaker_labels", 0) > 0:
                f.append("nonchair_text_scored")
            if x.get("scored_bracket_insertions", 0) > 0:
                f.append("editor_bracket_insertions")
            if x.get("chair_passages_missing_from_scored", 0) > 0:
                f.append("chair_text_missing_from_scored")
        if x.get("asr_available"):
            if (x.get("asr_cov_transcript_chair") or 0) < ASR_MISMATCH:
                f.append("asr_source_mismatch_or_partial")
            elif x.get("scored_no_audio_gap_passages", 0) > 0:
                f.append("scored_passage_possibly_not_spoken")
                if x.get("scored_no_audio_gap_lexicon_hits", 0) > 0:
                    f.append("lexicon_word_in_possibly_unspoken_passage")
        else:
            f.append("no_asr")
        if not x.get("captions_available"):
            f.append("no_captions")
        return ";".join(f)

    def klass(x) -> str:
        if x.get("asr_available") and (x.get("asr_cov_transcript_chair") or 0) < ASR_MISMATCH:
            return "ASR does not match this transcript (wrong or partial recording)"
        if x.get("asr_available"):
            return "checked against independent ASR"
        if x.get("captions_available"):
            return "captions only (not independent of the transcript)"
        return "no second source"

    df["flags"] = df.apply(lambda s: flags(s.dropna().to_dict()), axis=1)
    df["provenance_class"] = df.apply(lambda s: klass(s.dropna().to_dict()), axis=1)
    df.loc[df.meeting == "20230614", "flags"] += ";recording_is_2023-07-26_conference(Note2)"
    df["captions_missing_listed"] = df.meeting.isin(missing_vtt)
    for c in df.columns:
        if df[c].dtype == float:
            df[c] = df[c].round(6)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "provenance_by_meeting.csv", index=False, lineterminator="\n")
    pas = pd.DataFrame(passages)
    pas.to_csv(OUT / "provenance_passages.csv", index=False, lineterminator="\n")

    # ---------------- H1 answers (presser_answer rows): speaker labels inside answers ----------------
    ans = docs[docs.source == "presser_answer"]
    ans_labels = int(ans.text.apply(lambda t: len(seg.LABEL.findall(t))).sum())
    ans_fn = 0  # footnote texts (token match, as for the scored text) inside the H1 answer and question rows
    qa = docs[docs.source.isin(["presser_answer", "presser_question"])]
    for m, g in qa.groupby("meeting"):
        joined = " " + " ".join(tokens_of(" ".join(g.text), norm)) + " "
        for f in footnotes_by_meeting.get(m, []):
            ft = tokens_of(f, norm)
            ft = ft[1:] if ft and ft[0].isdigit() else ft
            ans_fn += int(len(ft) >= 4 and (" " + " ".join(ft) + " ") in joined)

    # ---------------- other v2 documents: dates and the next-session rule ----------------
    timing = document_timing(docs, ds, P)

    v2 = df[df.in_v2_scored]
    asr = v2[v2.asr_available]
    asr_ok = asr[asr.asr_cov_transcript_chair >= ASR_MISMATCH]
    cap = v2[v2.captions_available]
    summ = {
        "files_identical_to_manifest": {"transcript_pdfs": f"{pdf_ok}/95", "captions_vtt": f"{vtt_ok}/{n_vtt}"},
        "segmentation_reproduces_committed_turns": f"{seg_check['identical']}/{seg_check['meetings']}",
        "v2_scored_conferences": int(len(v2)),
        "v2_scored_tokens_total": int(v2.scored_tokens.sum()),
        "scored_share_in_chair_turns_pooled": round(float((v2.scored_share_in_chair_turns * v2.scored_tokens).sum()
                                                           / v2.scored_tokens.sum()), 6),
        "chair_transcript_share_in_scored_pooled": round(float((v2.chair_transcript_share_in_scored *
                                                                v2.transcript_chair_tokens).sum()
                                                               / v2.transcript_chair_tokens.sum()), 6),
        "conferences_with_footnote_scored": int((v2.scored_footnotes_included > 0).sum()),
        "footnotes_scored": int(v2.scored_footnotes_included.sum()),
        "footnotes_in_transcripts_of_scored_conferences": int(v2.n_footnotes_in_transcript.sum()),
        "conferences_with_nonchair_text_scored": int(((v2.scored_leak_tokens > 0) | (v2.scored_speaker_labels > 0)).sum()),
        "nonchair_tokens_scored": int(v2.scored_leak_tokens.sum()),
        "speaker_labels_in_scored_text": int(v2.scored_speaker_labels.sum()),
        "bracket_insertions_scored": int(v2.scored_bracket_insertions.sum()),
        "conferences_with_bracket_insertions": int((v2.scored_bracket_insertions > 0).sum()),
        "footnotes_in_captions_all_conferences": f"{int(df.n_footnotes_in_captions.fillna(0).sum())} of {int(df.loc[df.captions_available, 'n_footnotes_in_transcript'].sum())} footnotes of captioned conferences",
        "with_captions": int(len(cap)), "without_captions": v2.loc[~v2.captions_available, "meeting"].tolist(),
        "caption_cov_scored_median": round(float(cap.caption_cov_scored.median()), 6),
        "caption_cov_scored_min": round(float(cap.caption_cov_scored.min()), 6),
        "with_asr": int(len(asr)),
        "without_asr": v2.loc[~v2.asr_available, "meeting"].tolist(),
        "asr_mismatch_or_partial": asr.loc[asr.asr_cov_transcript_chair < ASR_MISMATCH, "meeting"].tolist(),
        "asr_cov_scored_median_matching_recordings": round(float(asr_ok.asr_cov_scored.median()), 6),
        "asr_cov_scored_range_matching_recordings": [round(float(asr_ok.asr_cov_scored.min()), 6),
                                                     round(float(asr_ok.asr_cov_scored.max()), 6)],
        "asr_cov_transcript_chair_median_matching": round(float(asr_ok.asr_cov_transcript_chair.median()), 6),
        "pkg_match_frac_median_matching": round(float(asr_ok.pkg_match_frac.median()), 6),
        "pkg_wer_proxy_median_matching": round(float(asr_ok.pkg_wer_proxy.median()), 6),
        "matching_recordings": {
            "n": int(len(asr_ok)),
            "chair_unheard_passages": int(asr_ok.chair_unheard_passages.sum()),
            "chair_unheard_tokens": int(asr_ok.chair_unheard_tokens.sum()),
            "chair_unheard_elsewhere_in_asr": int(asr_ok.chair_unheard_elsewhere_in_asr.sum()),
            "chair_unheard_audio_gap": int(asr_ok.chair_unheard_audio_gap.sum()),
            "chair_unheard_no_audio_gap": int(asr_ok.chair_unheard_no_audio_gap.sum()),
            "chair_unheard_no_audio_gap_tokens": int(asr_ok.chair_unheard_no_audio_gap_tokens.sum()),
            "chair_unheard_edge": int(asr_ok.chair_unheard_edge.sum()),
            "chair_extra_speech_passages": int(asr_ok.chair_extra_speech_passages.sum()),
            "chair_extra_speech_tokens": int(asr_ok.chair_extra_speech_tokens.sum()),
            "chair_extra_elsewhere_in_transcript": int(asr_ok.chair_extra_elsewhere_in_transcript.sum()),
            "chair_extra_repetition_loop": int(asr_ok.chair_extra_repetition_loop.sum()),
            "chair_extra_other": int(asr_ok.chair_extra_other.sum()),
            "chair_extra_other_tokens": int(asr_ok.chair_extra_other_tokens.sum()),
            "scored_unheard_passages": int(asr_ok.scored_unheard_passages.sum()),
            "scored_unheard_tokens": int(asr_ok.scored_unheard_tokens.sum()),
            "scored_unheard_lexicon_hits": int(asr_ok.scored_unheard_lexicon_hits.sum()),
            "scored_unheard_elsewhere_in_asr": int(asr_ok.scored_unheard_elsewhere_in_asr.sum()),
            "scored_unheard_audio_gap": int(asr_ok.scored_unheard_audio_gap.sum()),
            "scored_unheard_edge": int(asr_ok.scored_unheard_edge.sum()),
            "scored_no_audio_gap_passages": int(asr_ok.scored_no_audio_gap_passages.sum()),
            "scored_no_audio_gap_tokens": int(asr_ok.scored_no_audio_gap_tokens.sum()),
            "scored_no_audio_gap_lexicon_hits": int(asr_ok.scored_no_audio_gap_lexicon_hits.sum()),
            "scored_no_audio_gap_numeric_tokens": int(asr_ok.scored_no_audio_gap_numeric_tokens.sum()),
            "conferences_with_scored_no_audio_gap_passage": int((asr_ok.scored_no_audio_gap_passages > 0).sum()),
            "scored_tokens": int(asr_ok.scored_tokens.sum()),
            "scored_no_audio_gap_passages_by_overlap": overlap_counts,
            "scored_no_audio_gap_tokens_by_overlap": overlap_tokens,
        },
        "conferences_with_footnote_or_nonchair_sentence": int((v2.affected_sentences_footnote_or_nonchair > 0).sum()),
        "affected_sentences_footnote_or_nonchair_total": int(v2.affected_sentences_footnote_or_nonchair.sum()),
        "conferences_with_chair_text_missing": int((v2.chair_tokens_missing_from_scored > 0).sum()),
        "chair_tokens_missing_total": int(v2.chair_tokens_missing_from_scored.sum()),
        "score_bound_text_defects": {
            "median": round(float(v2.score_change_bound_text_defects.median()), 6),
            "max": round(float(v2.score_change_bound_text_defects.max()), 6),
            "max_meeting": v2.loc[v2.score_change_bound_text_defects.idxmax(), "meeting"],
            "n_above_0.05": int((v2.score_change_bound_text_defects > 0.05).sum())},
        "score_bound_footnote_or_nonchair": {
            "median": round(float(v2.score_change_bound_footnote_or_nonchair.median()), 6),
            "max": round(float(v2.score_change_bound_footnote_or_nonchair.max()), 6),
            "max_meeting": v2.loc[v2.score_change_bound_footnote_or_nonchair.idxmax(), "meeting"]},
        "score_bound_incl_brackets": {
            "median": round(float(v2.score_change_bound_incl_brackets.median()), 6),
            "max": round(float(v2.score_change_bound_incl_brackets.max()), 6),
            "max_meeting": v2.loc[v2.score_change_bound_incl_brackets.idxmax(), "meeting"]},
        "score_bound_incl_possible_edits_matching_recordings": {
            "n": int(asr_ok.score_change_bound_incl_possible_edits.notna().sum()),
            "median": round(float(asr_ok.score_change_bound_incl_possible_edits.median()), 6),
            "max": round(float(asr_ok.score_change_bound_incl_possible_edits.max()), 6),
            "max_meeting": asr_ok.loc[asr_ok.score_change_bound_incl_possible_edits.idxmax(), "meeting"]},
        "score_bound_incl_all_unheard_matching_recordings": {
            "n": int(asr_ok.score_change_bound_incl_all_unheard.notna().sum()),
            "median": round(float(asr_ok.score_change_bound_incl_all_unheard.median()), 6),
            "max": round(float(asr_ok.score_change_bound_incl_all_unheard.max()), 6),
            "max_meeting": asr_ok.loc[asr_ok.score_change_bound_incl_all_unheard.idxmax(), "meeting"]},
        "v2_presser_stance_score_sd": round(float(v2.v2_stance_score.std(ddof=1)), 6),
        "h1_answers_with_speaker_labels": ans_labels,
        "h1_answer_and_question_rows_footnote_texts": ans_fn,
        "footnotes_removed_by_text_study_segmentation": int(sum(len(v) for v in seglog["footnotes_removed"].values())),
        "classes": v2.provenance_class.value_counts().to_dict(),
        "document_timing": timing,
    }
    (OUT / "provenance_summary.json").write_text(json.dumps(summ, indent=1, default=str), encoding="utf-8",
                                                 newline="\n")
    print(json.dumps({k: v for k, v in summ.items() if k != "document_timing"}, indent=1, default=str))
    print("wrote", OUT / "provenance_by_meeting.csv", OUT / "provenance_passages.csv", OUT / "provenance_summary.json",
          OUT / "document_timing_check.csv")


def document_timing(docs: pd.DataFrame, ds: pd.DataFrame, P: dict[str, Path]) -> dict:
    """Dates of every v2 document, and the next-session rule checked on the committed in-sample consensus."""
    sig = pd.read_parquet(P["signals"])
    sess = sig.index.values.astype("datetime64[ns]")
    d = ds.copy()
    d["id_date"] = pd.to_datetime(d.doc_id.str.extract(r"(\d{8})")[0], format="%Y%m%d", errors="coerce")
    pos = np.searchsorted(sess, d.date.values.astype("datetime64[ns]"), side="right")
    inside = pos < len(sess)
    d["entry_session"] = pd.NaT
    d.loc[inside, "entry_session"] = pd.to_datetime(sess[pos[inside]])
    lam = 2 ** (-1 / 20)
    res = {}
    for col, keep, cons in (("rob_score", None, "C_T2"), ("lex_score", "lex_kept", "C_LEXALL")):
        dd = d[inside] if keep is None else d[inside & d[keep]]
        inj = dd.groupby("entry_session")[col].sum()
        x = (sig[cons] - lam * sig[cons].shift(1)).dropna()
        x = x[x.index >= "2015-01-05"]
        diff = (x - inj.reindex(x.index).fillna(0.0)).abs()
        res[cons] = {"sessions_checked": int(len(x)), "max_abs_diff": float(diff.max()),
                     "sessions_with_diff_gt_1e-9": int((diff > 1e-9).sum())}
    d["inside"] = inside
    d["hhmm"] = d.release_time.fillna("")
    sess_idx = pd.DatetimeIndex(sess)
    rows = []
    for t, g in d.groupby("doc_type"):
        gi = g[g.inside]
        r = dict(doc_type=t, n_docs=len(g), first=g.date.min().date(), last=g.date.max().date(),
                 release_time_missing=int(g.release_time.isna().sum()),
                 released_after_1600_et=int((g.hhmm > "16:00").sum()),
                 docs_in_checked_signal_window=int(len(gi)),
                 docs_after_committed_signal_file=int((~g.inside).sum()),
                 dated_on_non_session_day_in_window=int((~gi.date.isin(sess_idx)).sum()),
                 entry_session_strictly_after_date_in_window=f"{int((gi.entry_session > gi.date).sum())}/{len(gi)}")
        if t == "minutes":
            lag = (g.date - g.id_date).dt.days
            r.update(id_date_equals_date="n/a (id = meeting date)", minutes_release_lag_days_min=int(lag.min()),
                     minutes_release_lag_days_median=float(lag.median()), minutes_release_lag_days_max=int(lag.max()))
        else:
            r.update(id_date_equals_date=f"{int((g.id_date == g.date).sum())}/{len(g)}")
        rows.append(r)
    tab = pd.DataFrame(rows)
    # the same-day statement rows of the press-conference corpus are the v2 statement text
    st = docs[docs.source == "statement"].set_index("doc_id").text
    pst = docs[docs.source == "presser_statement"].set_index("doc_id").text
    same = sum(st.get(i.replace("presser_", "")) == t for i, t in pst.items())
    tab.to_csv(OUT / "document_timing_check.csv", index=False, lineterminator="\n")
    return {"consensus_injection_check": res, "presser_statement_identical_to_v2_statement": f"{same}/{len(pst)}",
            "by_type": tab.to_dict(orient="records"),
            "signal_file_last_session": str(pd.Timestamp(sess[-1]).date())}


if __name__ == "__main__":
    main()
