"""Caption-level check of answer end times and presser end against the raw WebVTT files (own parser)."""
import json
import re
import numpy as np
import pandas as pd
from pathlib import Path
from vlib import *

SCR = BT.parent
VTT = [SCR / "fedtalk/data_markets/vtt", SCR / "fedtalk/data_markets/html"]
ev = pd.read_csv(BT / "events/events.csv", dtype={"date": str})
ans = pd.read_parquet(BT / "text/answers.parquet")
turns = pd.read_parquet(BT / "text/turns.parquet")


def tsec(s):
    p = s.split(":")
    return sum(float(x) * 60 ** i for i, x in enumerate(reversed(p)))


def parse(path):
    cues, cur = [], None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\s*([\d:.]+)\s*-->\s*([\d:.]+)", line)
        if m:
            cur = [tsec(m.group(1)), tsec(m.group(2)), []]
            cues.append(cur)
        elif cur is not None and line.strip():
            cur[2].append(line.strip())
        elif not line.strip():
            cur = None
    W = []
    for s, e, txt in cues:
        for w in norm(" ".join(txt)):
            W.append((w, s, e))
    return cues, W


def norm(t):
    t = t.lower().replace("’", "'")
    return re.findall(r"[a-z0-9']+", t)


rows, mrows = [], []
for r in ev[(ev.drop_timing == 0) & (ev.scheduled == 1)].itertuples():
    mtg = r.date.replace("-", "")
    p = next((d / n for d in VTT for n in [f"{mtg}.vtt", f"cap_{mtg}.vtt"] if (d / n).exists()), None)
    if p is None:
        mrows.append(dict(date=r.date, vtt="missing"))
        continue
    cues, W = parse(p)
    words = [w for w, _, _ in W]
    last_end = max(e for s, e, t in cues if t)
    mrows.append(dict(date=r.date, vtt=p.name, last_cue_end=last_end, last_speech_end_s=r.last_speech_end_s,
                      diff=last_end - r.last_speech_end_s))
    A = ans[(ans.meeting == mtg) & (ans.timing_source == "vtt")]
    T = turns[turns.meeting == mtg].set_index("turn_idx")
    for a in A.itertuples():
        tw = norm(T.loc[a.turn_idx, "text"])
        k = 6
        tail = tw[-k:]
        hits = [i for i in range(len(words) - k + 1) if words[i:i + k] == tail]
        if not hits:
            rows.append(dict(date=r.date, aid=a.answer_id, matched=False))
            continue
        i = min(hits, key=lambda i: abs(W[i + k - 1][1] - a.t_end_video_s))
        cue_end = W[i + k - 1][2]
        # first words of the next turn (the next question) after this point
        nxt = T.loc[T.index > a.turn_idx]
        nq_start = np.nan
        if len(nxt):
            hw = norm(nxt.iloc[0].text)[:5]
            h2 = [j for j in range(i + k, min(len(words) - 4, i + k + 400)) if words[j:j + 5] == hw]
            if h2:
                nq_start = W[h2[0]][1]
        rows.append(dict(date=r.date, aid=a.answer_id, matched=True, n_hits=len(hits), t_end=a.t_end_video_s,
                         end_used=a.t_end_video_s + a.end_cue_dur, cue_end_of_last_words=cue_end,
                         early_s=cue_end - (a.t_end_video_s + a.end_cue_dur), next_q_start=nq_start,
                         gap_to_next_q=nq_start - (a.t_end_video_s + a.end_cue_dur),
                         conf=r.sample_role == "confirmation_2023_2026_powell"))
R = pd.DataFrame(rows)
M = pd.DataFrame(mrows)
R.to_csv(V / "v06_answer_end_vs_vtt.csv", index=False)
mm = R[R.matched]
out = dict(meetings_checked=len(M), vtt_missing=M[M.vtt == "missing"].date.tolist(),
           last_cue_vs_events_max_abs_s=float(M["diff"].abs().max()),
           answers=len(R), matched=int(R.matched.sum()),
           early_s_describe=mm.early_s.describe().round(3).to_dict(),
           n_answer_end_before_cue_end=int((mm.early_s > 1e-6).sum()),
           n_answer_end_after_next_question_start=int((mm.gap_to_next_q < -1e-6).sum()),
           gap_to_next_q_describe=mm.gap_to_next_q.describe().round(2).to_dict(),
           confirmation_answers=int(mm.conf.sum()),
           confirmation_early=int((mm[mm.conf].early_s > 1e-6).sum()))
json.dump(out, open(V / "v06_caption_check.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
print(mm.sort_values("early_s").tail(5).to_string())
print(mm.sort_values("gap_to_next_q").head(5).to_string())
