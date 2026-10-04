"""POSITIVE CONTROL (look-ahead, synthetic): a copy of the placebo tree in which the chair's arousal and the three
upper-face blendshape pairs are shifted by the sign of each answer's realised ZT +1 min return, taken from the
placebo run's own answer_trades.csv. It exists only to show that the H2/H3/H4 stage detects a planted effect
with the pre-registered signs (long ZT when arousal or U is high). Never a result; outputs stay under
placebo_features/out/positive_control.
"""
from __future__ import annotations

import json
import shutil
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "team_push" / "hpg" / "fedpress_pkg"))
sys.modules.setdefault("yaml", types.ModuleType("yaml"))
from fedpress import io as fio  # noqa: E402

SRC, DST = HERE / "tree", HERE / "tree_posctrl"
OUT0 = HERE / "out"
SHIFT_A, SHIFT_BS = 0.05, 0.03

shutil.rmtree(DST, ignore_errors=True)
shutil.copytree(SRC, DST)
meta = json.loads((DST / "PLACEBO.json").read_text())
meta.update(positive_control=True, what="POSITIVE CONTROL: placebo tree with a planted look-ahead signal",
            generator="placebo_features/make_positive_control_tree.py")
(DST / "PLACEBO.json").write_text(json.dumps(meta, indent=2) + "\n")

tr = pd.read_csv(OUT0 / "results" / "answer_trades.csv", dtype={"answer_id": str})
tr = tr[(tr.h == 1) & (tr.sym == "ZT") & (tr.variant == "base")].drop_duplicates("answer_id")
sgn = dict(zip(tr.answer_id, np.sign(tr.logret_bp)))
ch = pd.read_parquet(OUT0 / "features" / "voice_chunks_assigned.parquet")
ans = pd.read_parquet(OUT0 / "features" / "answers_h234.parquet")


def rewrite(path, df):
    md = json.loads((pq.read_schema(path).metadata or {}).get(b"fedpress", b"{}"))
    md["positive_control"] = True
    fio.write_parquet(df, path, md)


n_v = n_f = 0
for pid, g in ch[ch.answer_id.notna()].groupby("presser_id"):
    p = DST / "meetings" / pid / "voice" / "voice_chunks.parquet"
    v = pd.read_parquet(p)
    s = g.set_index("chunk_idx").answer_id.map(sgn).fillna(0.0)
    v["arousal"] = np.clip(v.arousal + SHIFT_A * v.chunk_idx.map(s).fillna(0.0), 0, 1)
    rewrite(p, v)
    n_v += int((s != 0).sum())
for pid, g in ans.groupby("presser_id"):
    p = DST / "meetings" / pid / "face" / "face_frames.parquet"
    if not p.exists():
        continue
    f = pd.read_parquet(p)
    shift = np.zeros(len(f))
    t = f.t_s.to_numpy(float)
    for r in g.itertuples():
        k = (t >= r.t_start_video_s) & (t < r.E_media_s) & (f.segment_kind == "answer").to_numpy()
        shift[k] = sgn.get(r.answer_id, 0.0)
    for c in ["bs_browDownLeft", "bs_browDownRight", "bs_browInnerUp", "bs_eyeSquintLeft", "bs_eyeSquintRight"]:
        f[c] = np.clip(f[c] + SHIFT_BS * shift, 0, 1)
    rewrite(p, f)
    n_f += int((shift != 0).sum())
print(f"positive control tree: {n_v} voice chunks and {n_f} face frames shifted, under {DST}")
