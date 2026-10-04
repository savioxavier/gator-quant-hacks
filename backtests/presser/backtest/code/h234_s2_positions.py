"""H2/H3/H4 step 2 (prereg 6.1-6.2, 9.5): join the answer features to the frozen H1 answer table, apply the
ADDENDUM selection per hypothesis and horizon, and write the positions with hashes before any price is joined.

Entry bars (t0) and decision times (tau_k_upper, tau_end_upper) are taken unchanged from the frozen H1 positions
(ADDENDUM 1.1, 4.2); no price is read here."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from lib import check_addendum
from h234_lib import (HYP, MEETING_COL, OUT, SYMS, check_manifest, check_prereg, dump, load_h1_answers,
                      load_h1_meetings, load_provenance, sample_of, side, write_manifest)

check_addendum()
check_prereg()
PROV = load_provenance()                           # qa manifest + placebo/real consistency
F, P = OUT / "features", OUT / "positions"
check_manifest(F, "features")
P.mkdir(parents=True, exist_ok=True)

feat = pd.read_parquet(F / "answers_h234.parquet")
mfeat = pd.read_parquet(F / "meetings_h234.parquet")
h1 = load_h1_answers()
hm = load_h1_meetings()

fcols = ["zA", "zD", "zVres", "U", "Unr", "M", "nV", "nF", "voice_known_at_pkg_max", "face_known_at_pkg_max",
         "voice_media_end_s", "face_media_end_s", "E_media_s"]
a = h1.merge(feat[["answer_id"] + fcols], on="answer_id", how="left")
a["sample"] = [sample_of(d, s) for d, s in zip(a.date, a.sample_role)]
a = a[a.chair == "Powell"].copy()
a["ex_2020_2021"] = ~a.date.str[:4].isin(["2020", "2021"])
a["s_tilde"] = a["H1__resid"]                      # ADDENDUM 4.1 point-in-time text residual
a = a.merge(hm[["meeting", "R_ZT", "sens1_drop", "sens2_drop", "sens3_keep"]], on="meeting", how="left")
# known_at QA (prereg 3.3: the package known_at is never used for a fill; recorded as a comparison only)
for ch in ["voice", "face"]:
    ka = pd.to_datetime(a[f"{ch}_known_at_pkg_max"], utc=True)
    a[f"{ch}_tau_minus_pkg_known_at_s"] = (a.tau_k_upper.dt.tz_convert("UTC") - ka).dt.total_seconds()
    a[f"{ch}_media_end_le_E"] = a[f"{ch}_media_end_s"] <= a.E_media_s + 1e-9
for k, h in HYP.items():
    for s in SYMS:
        a[f"{k}__pos_{s}"] = side(k, s) * np.sign(a[h["col"]])
    a[f"{k}__eligible"] = a["H1__eligible"].astype(bool) & np.isfinite(a[h["col"]].astype(float))
a["H4__eligible"] = (a["H1__eligible"].astype(bool) & np.isfinite(a.s_tilde) & np.isfinite(a.zA) & np.isfinite(a.U))


def select(df: pd.DataFrame, h: int) -> pd.DataFrame:
    """A-22 (copied from s02): latest answer per entry bar, then earliest-first non-overlapping per meeting."""
    keep = []
    for mtg, g in df.groupby("meeting"):
        g = g.sort_values(["t0", "answer_no"]).groupby("t0").tail(1).sort_values("t0")
        last = None
        for r in g.itertuples():
            if last is None or r.t0 >= last + pd.Timedelta(minutes=h):
                keep.append(r.Index)
                last = r.t0
    return df.loc[keep]


base_cols = ["answer_id", "meeting", "date", "answer_no", "sample", "sample_role", "start_unc_s", "tau_k_upper", "t0",
             "s_tilde", "R_ZT", "M", "zA", "zD", "zVres", "U", "Unr", "ex_2020_2021", "sens1_drop", "sens2_drop",
             "sens3_keep"]
status = {"placebo_features": bool(PROV["placebo"])}
for k in list(HYP) + ["H4"]:
    el = a[a[f"{k}__eligible"]]
    hs = [1] if k == "H4" else [1, 5, 15]
    status[k] = {"eligible": int(len(el)), "eligible_primary": int((el["sample"] == "primary_2023_2026").sum())}
    for h in hs:
        s_ = select(el, h)
        cols = base_cols + ([f"{k}__pos_{s}" for s in SYMS] if k in HYP else [])
        s_[cols].to_csv(P / f"answer_sel_{k}_h{h}.csv", index=False)
        status[k][f"h{h}"] = int(len(s_))
        status[k][f"h{h}_primary"] = int((s_["sample"] == "primary_2023_2026").sum())
        status[k][f"h{h}_primary_meetings"] = int(s_.loc[s_["sample"] == "primary_2023_2026", "meeting"].nunique())

# meeting level (prereg 6.1: as H1-primary; signal = the meeting feature)
m = hm[(hm.chair == "Powell") & (hm.scheduled == 1)].merge(
    mfeat.drop(columns=["date", "drop_timing", "sample_role"]), on="presser_id", how="left")
m["sample"] = [sample_of(d, s) for d, s in zip(m.date, m.sample_role)]
m["ex_2020_2021"] = ~m.date.str[:4].isin(["2020", "2021"])
m["s_tilde_m"] = m["H1__resid"]
for k, h in HYP.items():
    col = MEETING_COL[h["col"]]
    for s in SYMS:
        m[f"{k}__mpos_{s}"] = side(k, s) * np.sign(m[col])
    m[f"{k}__meligible"] = (m.drop_timing == 0) & np.isfinite(m[col].astype(float))
    status[k]["meetings_eligible"] = int(m[f"{k}__meligible"].sum())
    status[k]["meetings_eligible_primary"] = int((m[f"{k}__meligible"] & (m["sample"] == "primary_2023_2026")).sum())
m["H4__meligible"] = (m.drop_timing == 0) & np.isfinite(m.s_tilde_m) & np.isfinite(m.zA_m) & np.isfinite(m.U_m)
status["H4"]["meetings_eligible"] = int(m["H4__meligible"].sum())

kq = a[a.zA.notna() | a.U.notna()][["answer_id", "date", "voice_tau_minus_pkg_known_at_s", "face_tau_minus_pkg_known_at_s",
                                     "voice_media_end_le_E", "face_media_end_le_E"]]
kq.to_csv(P / "known_at_comparison.csv", index=False)
status["known_at_qa"] = {
    "voice_media_end_le_E_all": bool(kq.voice_media_end_le_E[a.zA.notna()].all()) if a.zA.notna().any() else None,
    "voice_tau_minus_pkg_known_at_s_median": float(kq.voice_tau_minus_pkg_known_at_s.median())
    if kq.voice_tau_minus_pkg_known_at_s.notna().any() else None,
    "face_tau_minus_pkg_known_at_s_median": float(kq.face_tau_minus_pkg_known_at_s.median())
    if kq.face_tau_minus_pkg_known_at_s.notna().any() else None,
    "note": "package known_at (greeting anchor + 30 s) recorded as comparison only; fills use tau_k_upper"}

a.to_csv(P / "answers_h234_positions.csv", index=False)
m.to_csv(P / "meetings_h234_positions.csv", index=False)
dump(P / "positions_status.json", status)
write_manifest(P, [p for p in P.glob("*") if p.name != "manifest_sha256.txt"])
print(json.dumps(status, indent=1, default=str))
