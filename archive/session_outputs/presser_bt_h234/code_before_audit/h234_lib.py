"""Shared code for the exploratory H2 (voice), H3 (face) and H4 (combined) tests.

Specification: preregistration/presser_H2H3H4_EXPLORATORY.md (sha256 e030af98...a6d0). Every result carries the
label "exploratory, post-NO-GO; cannot rescue G3; no trading claim". The locked register keeps H2, H3 and H4 at
p = 1 and G3 at NO-GO; nothing here changes that.

Inputs
  FEDPRESS_ROOT (env, required)   the fedpress package output tree: <root>/meetings/<presser_id>/...
  H234_SI_ROOT  (env, optional)   a second tree holding the 64 kbps source-invariance re-runs (prereg 3.7)
  H234_OUT_DIR  (env, optional)   output folder (default: <scratch>/presser_bt_h234/out)
  FEDPRESS_PKG  (env, optional)   the package directory (for fedpress.baselines.causal_z)
The frozen H1 tables are read from the ADDENDUM backtest (lib.OUT/positions, hash-checked) and never rewritten.
Market data are read only by the h234_s3 and h234_s4 steps, through lib.Bars and lib.Quotes.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import lib
from lib import BT, SCR, SEED, B, WEBB, TZ, sha256, write_json

# ---------------------------------------------------------------- locations
PREREG = SCR / "team_push" / "preregistration" / "presser_H2H3H4_EXPLORATORY.md"
PREREG_SHA = "e030af98df6fb194532c236890986619341f6e14a457384cfc3ec4bba5dca6d0"
PKG = Path(os.environ.get("FEDPRESS_PKG") or (SCR / "team_push" / "hpg" / "fedpress_pkg"))
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))
from fedpress.baselines import _center_scale, causal_z  # noqa: E402  (numpy-only module of the package)

H1_POS = lib.OUT / "positions"                 # frozen H1 positions (read-only)
H1_CODE = BT / "backtest" / "code"             # hashed for H4 (prereg 6.4)
TEXT_CHRONO = BT / "text_chrono"               # the frozen text label (D1 chrono scores)
OUT = Path(os.environ.get("H234_OUT_DIR") or (SCR / "presser_bt_h234" / "out"))
LABEL = "exploratory, post-NO-GO; cannot rescue G3; no trading claim"


def fedpress_root() -> Path:
    r = os.environ.get("FEDPRESS_ROOT")
    if not r:
        raise SystemExit("FEDPRESS_ROOT is not set (the fedpress output tree: <root>/meetings/<presser_id>/)")
    p = Path(r)
    if not (p / "meetings").is_dir():
        raise SystemExit(f"{p}/meetings missing")
    return p


def si_root() -> Path | None:
    r = os.environ.get("H234_SI_ROOT")
    return Path(r) if r and (Path(r) / "meetings").is_dir() else None


def check_prereg():
    got = sha256(PREREG)
    if got != PREREG_SHA:
        raise SystemExit(f"pre-registration changed: {got}")


# ---------------------------------------------------------------- frozen constants (prereg sections 2-4)
FIRST, LAST = "2018-03-21", "2026-04-29"       # Powell baseline window (2.)
UNSCHEDULED = ("2020-03-03", "2020-03-15")
BURN_IN = 4
CLIP = 5.0
FLOOR = {"A": 0.01, "D": 0.01, "Vres": 0.01,   # model units (3.5)
         "BD": 0.005, "BI": 0.005, "ES": 0.005,  # blendshape units (4.3)
         "BOU": 0.005, "EW": 0.005, "CS": 0.005, "BDnr": 0.005, "BInr": 0.005, "ESnr": 0.005,
         # descriptive EmotiEffLib rows (4.4): prereg says "z-scored as in 3.5"; the 3.5 model-unit floor is used
         "NEG": 0.01, "EXV": 0.01, "EXA": 0.01}
MIN_CHUNK_S, MIN_VOICED, MIN_CHUNKS = 3.0, 0.25, 2
MIN_ENROLL_S, MIN_COVER = 60.0, 0.50
MAX_VTT_OFFSET_S, MAX_WAV_GAP_S = 2.0, 2.0
MIN_FRAMES_ANSWER, MIN_FRAMES_MEETING = 5, 20
FACE_GATES = dict(min_face_h_px=80.0, max_abs_yaw_deg=40.0, max_abs_pitch_deg=30.0, min_blur=20.0, min_det_score=0.5)
SFACE_THRESHOLD = 0.363
JAW_OPEN = 0.025
G4_MAX_SHARE = 0.25
ICC_MIN = 0.8
SI_MEETINGS = ("20190130", "20190320", "20190619")
EXPECTED_MODELS = {"audeering_msp_dim": "6eba34a2", "ecapa_voxceleb": "0f99f2d0",
                   "mediapipe_face_landmarker": "64184e22", "sface_opencv": "0ba9fbfa",
                   "emotiefflib_enet_b0_8_va_mtl": "emotiefflib==1.1.1"}
EX_EXPECTED = ("anger", "contempt", "disgust", "fear", "happiness", "neutral", "sadness", "surprise")
NEG_LABELS = ("anger", "contempt", "disgust", "fear", "sadness")

# hypotheses: feature column, ZT sign, ES sign (prereg 6.2). ZF and ZN take the ZT (rates) sign.
HYP = {"H2": dict(col="zA", zt=+1, es=-1, kind="primary", what="arousal z (vocal proxy)"),
       "H3": dict(col="U", zt=+1, es=-1, kind="primary", what="upper-face composite U (expression proxy)"),
       "H2D": dict(col="zD", zt=-1, es=-1, kind="descriptive", what="dominance z"),
       "H2V": dict(col="zVres", zt=-1, es=+1, kind="descriptive",
                   what="valence, residualised on the same chunk's words (A-31); descriptive")}
MEETING_COL = {"zA": "zA_m", "U": "U_m", "zD": "zD_m", "zVres": "zVres_m"}
SYMS = ["ZT", "ZF", "ZN", "ES"]


def side(key: str, sym: str) -> int:
    h = HYP[key]
    return h["es"] if sym == "ES" else h["zt"]


# ---------------------------------------------------------------- package tree access
def mdir(root: Path, pid: str) -> Path:
    return root / "meetings" / str(pid)


def read_done(root: Path, pid: str, stage: str) -> dict | None:
    p = mdir(root, pid) / "_done" / f"{stage}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def stage_state(root: Path, pid: str, stage: str) -> str:
    """ok | not_applicable | failed | missing (mirrors fedpress.stages.aggregate.input_state)."""
    d = read_done(root, pid, stage)
    if d is not None and all((mdir(root, pid) / o).exists() for o in d.get("outputs", [])):
        return str(d.get("status", "ok"))
    if (mdir(root, pid) / "_done" / f"{stage}.failed.json").exists():
        return "failed"
    return "missing"


def read_table(root: Path, pid: str, rel: str) -> pd.DataFrame | None:
    p = mdir(root, pid) / rel
    return pd.read_parquet(p) if p.exists() else None


def table_meta(root: Path, pid: str, rel: str) -> dict:
    import pyarrow.parquet as pq

    p = mdir(root, pid) / rel
    if not p.exists():
        return {}
    md = pq.read_schema(p).metadata or {}
    return json.loads(md.get(b"fedpress", b"{}"))


# ---------------------------------------------------------------- frozen H1 inputs
def check_manifest(folder: Path, what: str):
    man = folder / "manifest_sha256.txt"
    if not man.exists():
        raise SystemExit(f"{what}: {man} missing")
    for line in man.read_text().splitlines():
        h, f = line.split("  ")
        if sha256(folder / f) != h:
            raise SystemExit(f"{what}: {f} changed after its freeze")


def write_manifest(folder: Path, files: list[Path]):
    (folder / "manifest_sha256.txt").write_text("".join(f"{sha256(f)}  {f.relative_to(folder).as_posix()}\n"
                                                        for f in sorted(files)))


def load_h1_answers() -> pd.DataFrame:
    check_manifest(H1_POS, "H1 positions")
    a = pd.read_csv(H1_POS / "answers_positions.csv", dtype={"date": str, "answer_id": str})
    for c in ["tau_k_upper", "t0"]:
        a[c] = pd.to_datetime(a[c], utc=True, format="ISO8601").dt.tz_convert(TZ)
    a["presser_id"] = a.meeting.astype(str)
    return a


def load_h1_meetings() -> pd.DataFrame:
    check_manifest(H1_POS, "H1 positions")
    m = pd.read_csv(H1_POS / "meetings_positions.csv", dtype={"date": str})
    for c in ["tau_end_upper", "tau_end_point", "tau_end_conv"]:
        m[c] = pd.to_datetime(m[c], utc=True, format="ISO8601").dt.tz_convert(TZ)
    m["presser_id"] = m.meeting.astype(str)
    return m


def powell_baseline_meetings(ev: pd.DataFrame) -> pd.DataFrame:
    """Scheduled Powell pressers 2018-03-21..2026-04-29 (the two unscheduled 2020 meetings excluded)."""
    m = ev[(ev.chair == "Powell") & (ev.scheduled == 1) & (ev.date >= FIRST) & (ev.date <= LAST) &
           ~ev.date.isin(UNSCHEDULED)].copy()
    m["presser_id"] = m.meeting.astype(str)
    return m.sort_values("date").reset_index(drop=True)


def sample_of(date: str, sample_role: str) -> str:
    if sample_role == "confirmation_2023_2026_powell":
        return "primary_2023_2026"
    if "2018-01-01" <= date <= "2022-12-31":
        return "additional_2018_2022"
    return "other"


A29_NOTE = {"primary_2023_2026": "A-29 met (audeering released 2022-03; AffectNet images by 2017)",
            "additional_2018_2022": "audeering cutoff not verified for 2018-2021 rows (A-29)",
            "pooled_2018_2026": "pooled: includes rows with audeering cutoff not verified",
            "pooled_ex_2020_2021": "pooled: includes rows with audeering cutoff not verified"}


# ---------------------------------------------------------------- causal per-chair z (prereg 3.5)
def causal_feature_z(ans: pd.DataFrame, col: str, floor: float, meetings_ok: set[str], date_of: dict[str, str]):
    """z of ``col`` by fedpress.baselines.causal_z: Powell only, pool = rows of strictly earlier baseline meetings,
    robust (median, 1.4826 MAD), scale floor ``floor`` (variance_floor = floor**2), burn-in 4 meetings counted over
    meetings with a valid value of this feature, clipped to [-5, 5]. Returns (z Series aligned to ``ans``,
    per-meeting baseline table with centre, scale, raw scale and whether the floor binds)."""
    sub = ans[ans.presser_id.isin(meetings_ok) & np.isfinite(ans[col].astype(float))][["presser_id", col]].copy()
    sub["chair"] = "Powell"
    order = sorted(sub.presser_id.unique(), key=lambda p: date_of[p])
    z = causal_z(sub, [col], order=order, meeting_col="presser_id", group_cols=("chair",), burn_in=BURN_IN,
                 variance_floor=floor ** 2, robust=True, pool="rows", prefix="z_")
    zz = z[f"z_{col}"].clip(-CLIP, CLIP)
    rows = []
    for k, pid in enumerate(order):
        r = dict(feature=col, presser_id=pid, date=date_of[pid], baseline_k=k, n_rows=int((sub.presser_id == pid).sum()))
        if k >= BURN_IN:
            ref = sub.loc[sub.presser_id.isin(order[:k]), col].astype(float).to_numpy()
            c, s = _center_scale(ref, True, floor ** 2)
            raw = 1.4826 * float(np.median(np.abs(ref - np.median(ref))))
            r.update(center=c, scale=s, raw_scale=raw, floor=floor, floor_binds=bool(raw <= floor), n_ref_rows=len(ref))
            # cross-check against the package output
            mine = ((sub.loc[sub.presser_id == pid, col].astype(float) - c) / s).clip(-CLIP, CLIP)
            pk = zz.loc[mine.index]
            r["pkg_match"] = bool(np.allclose(mine.to_numpy(), pk.to_numpy(), atol=1e-9, equal_nan=True))
        rows.append(r)
    out = pd.Series(np.nan, index=ans.index)
    out.loc[zz.index] = zz
    return out, pd.DataFrame(rows)


def g4_share(stats: pd.DataFrame) -> tuple[float, int]:
    post = stats[stats.baseline_k >= BURN_IN] if len(stats) else stats
    if len(post) == 0:
        return float("nan"), 0
    return float(post.floor_binds.mean()), int(len(post))


def icc31(x: np.ndarray, y: np.ndarray) -> float:
    """ICC(3,1), two raters (consistency): (MSR - MSE) / (MSR + MSE)."""
    d = np.column_stack([x, y]).astype(float)
    d = d[np.isfinite(d).all(1)]
    n, k = d.shape
    if n < 3:
        return float("nan")
    gm = d.mean()
    ssr = k * ((d.mean(1) - gm) ** 2).sum()
    ssc = n * ((d.mean(0) - gm) ** 2).sum()
    sse = ((d - gm) ** 2).sum() - ssr - ssc
    msr, mse = ssr / (n - 1), sse / ((n - 1) * (k - 1))
    return float((msr - mse) / (msr + (k - 1) * mse))


# ---------------------------------------------------------------- inference helpers (ADDENDUM 8.1 conventions)
def ols(y, X):
    XtXi = np.linalg.pinv(X.T @ X)
    b = XtXi @ X.T @ y
    return b, XtXi


def cr1_coef(y, X, g, j):
    """OLS coefficient j with a CR1 cluster-robust SE."""
    y, X = np.asarray(y, float), np.asarray(X, float)
    n, k = X.shape
    codes, gi = np.unique(np.asarray(g), return_inverse=True)
    G = len(codes)
    b, XtXi = ols(y, X)
    u = y - X @ b
    h = X @ XtXi[j]
    s = np.bincount(gi, weights=h * u, minlength=G)
    c = (G / (G - 1)) * ((n - 1) / (n - k))
    se = math.sqrt(c * np.sum(s ** 2))
    return float(b[j]), se, (b[j] / se if se > 0 else np.nan), G


def wild_cluster_coef(y, X, g, j, seed=SEED, B_=B):
    """CR1 t of coefficient j and a restricted wild cluster bootstrap p (Webb 6-point, null b_j = 0)."""
    y, X = np.asarray(y, float), np.asarray(X, float)
    n, k = X.shape
    codes, gi = np.unique(np.asarray(g), return_inverse=True)
    G = len(codes)
    coef, se, t, _ = cr1_coef(y, X, g, j)
    out = dict(coef=coef, se_cr1=se, t_cr1=t, n=n, n_clusters=G)
    if G < 3 or not np.isfinite(t):
        return out
    Xr = np.delete(X, j, axis=1)
    br = np.linalg.lstsq(Xr, y, rcond=None)[0]
    fr, ur = Xr @ br, y - Xr @ br
    _, XtXi = ols(y, X)
    A = XtXi @ X.T
    h = X @ XtXi[j]
    c = (G / (G - 1)) * ((n - 1) / (n - k))
    rng = np.random.default_rng(seed)
    W = rng.choice(WEBB, size=(G, B_))[gi]            # n x B
    Ys = fr[:, None] + W * ur[:, None]
    Bs = A @ Ys
    Us = Ys - X @ Bs
    S = np.zeros((G, B_))
    np.add.at(S, gi, h[:, None] * Us)
    ses = np.sqrt(c * (S ** 2).sum(0))
    with np.errstate(divide="ignore", invalid="ignore"):
        ts = Bs[j] / ses
    out.update(wcb_p_two=float((1 + np.sum(np.abs(ts) >= abs(t))) / (B_ + 1)),
               wcb_p_lower=float((1 + np.sum(ts <= t)) / (B_ + 1)),
               wcb_p_upper=float((1 + np.sum(ts >= t)) / (B_ + 1)))
    return out


def lomo(y, g, dates):
    """Leave-one-meeting-out range of the mean, naming the most influential meeting."""
    y, g = np.asarray(y, float), np.asarray(g)
    codes = np.unique(g)
    if len(codes) < 3:
        return {}
    m0 = y.mean()
    vals = {c: y[g != c].mean() for c in codes}
    infl = max(vals, key=lambda c: abs(vals[c] - m0))
    d = dict(zip(g, dates))
    return dict(lomo_min=min(vals.values()), lomo_max=max(vals.values()), lomo_most_influential=d[infl],
                lomo_mean_without_it=vals[infl])


def holm(pvals: dict[str, float]) -> dict[str, float]:
    keys = sorted(pvals, key=lambda k: pvals[k])
    m = len(keys)
    adj, run = {}, 0.0
    for i, k in enumerate(keys):
        run = max(run, min(1.0, (m - i) * pvals[k]))
        adj[k] = run
    return adj


def is_placebo(root: Path) -> bool:
    return (root / "PLACEBO.json").exists()


def dump(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    write_json(p, obj)
