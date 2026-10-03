"""Step 2: attach video time and ET to every turn from the official WebVTT captions.

The Board's WebVTT captions are a forced alignment of the transcript text to the video (speaker labels included).
PDF = words, VTT = time. Per meeting:
  * VTT cues -> word stream; each word gets [start, end] by character-weighted interpolation inside its cue.
  * transcript turns (labels + text) -> normalised token stream.
  * global token alignment (difflib.SequenceMatcher, autojunk off); a turn's start = start of its first matched
    text token, end = end of its last matched text token. Label tokens are never used for timing.
  * ET = scheduled start + video seconds. Convention (Gomez-Cram & Grotteria Table 1 = caption cue + 14:30:00):
    video zero = 14:30:00 ET for scheduled pressers; 11:00:00 ET on 2020-03-03 and 18:30:00 ET on 2020-03-15
    (unscheduled; USMPD scheduled minute).
  * uncertainty per turn: duration of the cue holding the first / last matched token (within-cue interpolation
    can be off by at most that much). This is NOT the wall-clock anchor error, which is unknown (no Bloomberg).
Meetings without captions: timing missing (no forced alignment; no media downloaded).

Output: turn_times.parquet, align_meetings.parquet
"""
from __future__ import annotations

import difflib
import re
import os
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1]
VTT_DIR = Path(os.environ.get("VTT_DIR") or (Path(__file__).resolve().parents[4] / "data" / "fomc_pressers" / "captions"))  # repo captions
TS = re.compile(r"^((?:\d+:)?\d+:\d+\.\d+)\s+-->\s+((?:\d+:)?\d+:\d+\.\d+)")
START_ET = {"20200303": "11:00:00", "20200315": "18:30:00"}  # all other pressers in the sample: 14:30:00


def secs(s: str) -> float:
    p = [float(x) for x in s.split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def norm_tokens(text: str) -> list[str]:
    t = text.lower().replace("\u2019", "'").replace("\u2018", "'").replace("'", "")
    return re.findall(r"[a-z0-9]+", t)


def parse_vtt(path: Path) -> pd.DataFrame:
    cues, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = TS.match(line.strip())
        if m:
            cur = [secs(m.group(1)), secs(m.group(2)), ""]
            cues.append(cur)
        elif cur is not None and line.strip():
            cur[2] += " " + line.strip()
        elif not line.strip():
            cur = None
    words = []
    for ci, (s, e, txt) in enumerate(cues):
        toks = norm_tokens(txt)
        if not toks:
            continue
        w = np.array([len(x) for x in toks], dtype=float)
        c = np.r_[0.0, np.cumsum(w)] / w.sum()
        for k, tok in enumerate(toks):
            words.append((tok, s + (e - s) * c[k], s + (e - s) * c[k + 1], ci, e - s))
    return pd.DataFrame(words, columns=["tok", "ws", "we", "cue", "cue_dur"]), len(cues)


def main() -> None:
    turns = pd.read_parquet(OUT / "turns.parquet")
    turns = turns[turns.role != "preamble"].copy()
    rows, mrows = [], []
    for m, g in turns.groupby("meeting", sort=True):
        g = g.sort_values("turn_idx")
        base = pd.Timestamp(f"{m[:4]}-{m[4:6]}-{m[6:]} {START_ET.get(m, '14:30:00')}", tz="America/New_York")
        vtt = VTT_DIR / f"{m}.vtt"
        if not vtt.exists():
            for t in g.itertuples(index=False):
                rows.append(dict(meeting=m, turn_idx=t.turn_idx, timing_source="missing_no_captions"))
            mrows.append(dict(meeting=m, captions=False, base_et=base))
            continue
        W, n_cues = parse_vtt(vtt)
        ttok, tturn, tlab = [], [], []
        for t in g.itertuples(index=False):
            lt = norm_tokens(t.speaker)
            xt = norm_tokens(t.text)
            ttok += lt + xt
            tturn += [t.turn_idx] * (len(lt) + len(xt))
            tlab += [True] * len(lt) + [False] * len(xt)
        ttok_a = np.array(tturn)
        tlab_a = np.array(tlab)
        sm = difflib.SequenceMatcher(None, ttok, W.tok.tolist(), autojunk=False)
        match = np.full(len(ttok), -1)
        for a, b, size in sm.get_matching_blocks():
            if size:
                match[a:a + size] = np.arange(b, b + size)
        ws, we, cd = W.ws.to_numpy(), W.we.to_numpy(), W.cue_dur.to_numpy()
        for t in g.itertuples(index=False):
            idx = np.where((ttok_a == t.turn_idx) & ~tlab_a)[0]
            mi = idx[match[idx] >= 0]
            r = dict(meeting=m, turn_idx=t.turn_idx, n_tok=len(idx), n_matched=len(mi),
                     coverage=len(mi) / len(idx) if len(idx) else np.nan)
            if len(mi):
                v0, v1 = match[mi[0]], match[mi[-1]]
                r.update(t_start_video_s=ws[v0], t_end_video_s=we[v1], start_cue_dur=cd[v0], end_cue_dur=cd[v1],
                         lead_unmatched=int(np.searchsorted(idx, mi[0])),
                         tail_unmatched=int(len(idx) - 1 - np.searchsorted(idx, mi[-1])),
                         timing_source="vtt")
            else:
                r.update(timing_source="vtt_unmatched")
            rows.append(r)
        qa = np.isin(ttok_a, g[g.role != "opening"].turn_idx.to_numpy()) & ~tlab_a
        op = np.isin(ttok_a, g[g.role == "opening"].turn_idx.to_numpy()) & ~tlab_a
        op_m = np.where(op & (match >= 0))[0]
        all_m = np.where(match >= 0)[0]
        mrows.append(dict(meeting=m, captions=True, base_et=base, n_cues=n_cues, vtt_words=len(W),
                          transcript_tokens=len(ttok), match_rate_all=float((match >= 0).mean()),
                          match_rate_qa=float((match[qa] >= 0).mean()),
                          greeting_video_s=float(ws[match[op_m[0]]]) if len(op_m) else np.nan,
                          opening_end_video_s=float(we[match[op_m[-1]]]) if len(op_m) else np.nan,
                          last_word_video_s=float(we[match[all_m[-1]]]) if len(all_m) else np.nan,
                          last_cue_end_video_s=float(W.we.max())))
    T = pd.DataFrame(rows)
    M = pd.DataFrame(mrows)
    T = T.merge(M[["meeting", "base_et"]], on="meeting")
    for c in ("start", "end"):
        T[f"t_{c}_et"] = T.base_et + pd.to_timedelta(T[f"t_{c}_video_s"], unit="s")
    T = T.drop(columns="base_et")
    T.to_parquet(OUT / "turn_times.parquet", index=False)
    M.to_parquet(OUT / "align_meetings.parquet", index=False)
    print(M.drop(columns=["base_et"]).describe().round(3).to_string())


if __name__ == "__main__":
    main()
