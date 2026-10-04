"""face (gpu): chair-only facial behaviour per frame and per answer (Powell-only expression_proxy).

Pipeline per meeting (one worker process, models loaded once; several workers share a GPU):
  frames  frames zip at face.fps (default, from the CPU frames stage) or the video decoded in batches
          (source: stream; NVDEC when available); slot k is at t = k / face.fps and never shows later content
  enrol   the chair's face from the first face.enroll_max_s of the opening remarks (they precede every Q&A
          frame): largest face per frame, robust mean embedding (SFace by default) or median box geometry
  detect  face.detector: mediapipe (team plan) | insightface | pyfeat; every face gets an identity score and
          the best-scoring one is the chair candidate; identity_ok = score >= threshold
  measure head pose, size, blur, luminance, mouth opening, eye closure, reading (head down), causal track
          and head speed; gate_ok = identity, size, |yaw|, |pitch|, blur and detector score gates
  express face.expression: EmotiEffLib (8 expressions + valence/arousal) and/or py-feat (20 AUs, 7 emotions,
          valence/arousal, gaze); MediaPipe blendshapes from the detector or, if the detector is not
          MediaPipe, from a cross-check run on the chair crop
Outputs
  face/face_frames.parquet  one row per feature frame (answers by default); t_start_s = t_end_s = frame time
  face/face_turns.parquet   gated chair frames averaged per answer (unit=turn) and per tumbling 30/60 s window
                            inside each answer (unit=window, t_end_s = window end); trailing data only
  face/enroll.json          enrolment summary and reference (embedding or geometry), threshold used
Nothing is normalised within or across meetings here: per-chair baselines are computed at analysis time from
earlier meetings only. Frame rows before the answer start, and features of later frames, never enter a row.
Prefetch the weights once (outbound network): ``python -m fedpress.stages.face prefetch``.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .. import io
from ..config import Config
from ..stage import StageContext, StageResult, StageSpec, max_seconds

SPEC = StageSpec(name="face", requires=("frames", "turns"), resource="gpu",
                 outputs=("face_frames", "face_turns", "face_enroll"))

DEFAULT_THRESHOLD = {"sface": 0.363, "insightface": 0.40, "pyfeat": 0.40, "geometry": 0.25}
POSE = ("pitch_deg", "yaw_deg", "roll_deg")


def applies(ctx: StageContext) -> str | None:
    chairs = ctx.scfg.get("chairs") or []
    if chairs and ctx.meeting.chair not in chairs:
        return f"chair {ctx.meeting.chair} not in face.chairs {list(chairs)}"
    return None


# ------------------------------------------------------------------ segments
def _turns(ctx: StageContext) -> Any:
    import pandas as pd

    t = io.read_parquet(ctx.out("turns"))
    if "is_chair" not in t.columns:
        t["is_chair"] = t.get("role", pd.Series("", index=t.index)).eq("chair")
    t = t[np.isfinite(t["t_start_s"].astype(float)) & np.isfinite(t["t_end_s"].astype(float))]
    return t[t["t_end_s"] > t["t_start_s"]].sort_values("t_start_s").reset_index(drop=True)


def _segments(ctx: StageContext, turns: Any, cut: float | None) -> tuple[Any, list[tuple[float, float]]]:
    s = ctx.scfg
    chair = turns["is_chair"].astype(bool)
    feat = turns[chair & turns["segment_kind"].isin(list(s.get("segments", ["answer"])))].copy()
    if cut:
        feat = feat[feat["t_start_s"] < cut].copy()
        feat["t_end_s"] = feat["t_end_s"].clip(upper=cut)
    enroll, left = [], float(s.get("enroll_max_s", 180))
    for r in turns[chair & turns["segment_kind"].isin(list(s.get("enroll_segments", ["opening"])))].itertuples():
        a, b = float(r.t_start_s), min(float(r.t_end_s), float(r.t_start_s) + left, cut or math.inf)
        if b > a and left > 0:
            enroll.append((a, b))
            left -= b - a
    return feat.reset_index(drop=True), enroll


# ------------------------------------------------------------------ frame source
class FrameSource:
    """Frames at face.fps from the frames zip (exact fps or an integer stride) or from the video."""

    def __init__(self, ctx: StageContext, fps: float) -> None:
        self.ctx, self.fps, s = ctx, fps, ctx.scfg
        self.mode, self.stride, self.store = "stream", 1, None
        mode = str(s.get("source", "auto"))
        if mode in ("auto", "zip"):
            ffps = float(ctx.cfg.get("frames.fps", fps))
            for zfps, stride in ((fps, 1), (ffps, round(ffps / fps))):
                if stride >= 1 and abs(zfps - stride * fps) < 1e-9 and ctx.out("frames_zip", fps=zfps).exists():
                    store = io.FrameStore(ctx.paths, zfps)
                    if len(store.index) and (store.index["member"].astype(str) != "").all():
                        self.mode, self.stride, self.store = "zip", stride, store
                        break
            if self.mode != "zip" and mode == "zip":
                raise FileNotFoundError(f"face.source=zip but no frames zip matches face.fps={fps}")
        self.decode_events: list[dict[str, Any]] = []

    def frames(self, ranges: list[tuple[float, float]]) -> Iterator[tuple[int, float, np.ndarray]]:
        from . import _video

        if not ranges:
            return
        if self.mode == "zip":
            import cv2

            assert self.store is not None
            idx = self.store.index
            idx = idx[(idx["frame_idx"] % self.stride) == 0]
            t = idx["t_s"].to_numpy(float)
            keep = np.zeros(len(idx), bool)
            for a, b in _video.merge_ranges(ranges):
                keep |= (t >= a - 1e-9) & (t < b - 1e-9)
            for r in idx[keep].itertuples(index=False):
                bgr = cv2.imdecode(np.frombuffer(self.store.read(str(r.member)), np.uint8), cv2.IMREAD_COLOR)
                yield int(r.frame_idx) // self.stride, float(r.t_s), np.ascontiguousarray(bgr[:, :, ::-1])
            return
        s, video = self.ctx.scfg.get("decode", {}) or {}, self.ctx.out("video")
        ffmpeg = _video.resolve_ffmpeg(str(self.ctx.cfg.get("frames.ffmpeg", "ffmpeg")))
        info = _video.probe(video, ffmpeg)
        yield from _video.iter_frames(video, info, self.fps, ranges, max_height=s.get("max_height", 540),
                                      hwaccel=str(s.get("hwaccel", "auto")), threads=int(s.get("threads", 2)),
                                      ffmpeg=ffmpeg, on_event=lambda e, **f: self.decode_events.append({"event": e, **f}))

    def close(self) -> None:
        if self.store is not None:
            self.store.close()


# ------------------------------------------------------------------ backends
@dataclass
class Backends:
    detector: Any
    identity: str
    embedder: Any | None
    emotieff: Any | None
    pyfeat_expr: Any | None
    crosscheck: Any | None
    models: tuple[str, ...]
    timings: dict[str, float] = field(default_factory=dict)

    def close(self) -> None:
        for b in {id(x): x for x in (self.detector, self.embedder, self.emotieff, self.pyfeat_expr, self.crosscheck)
                  if x is not None}.values():
            b.close()


def _model_file(cfg: Config, key: str) -> Path:
    from .. import models

    p = models.local_path(cfg, key)
    if not p.exists():
        raise FileNotFoundError(f"{p} missing: run `python -m fedpress.cli prefetch-models --keys {key}`")
    return p


def _pyfeat_weights(cfg: Config, s: dict[str, Any]) -> str:
    from huggingface_hub import hf_hub_download

    spec = cfg.model(str(s.get("model", "pyfeat_multitask_v2")))
    return hf_hub_download(repo_id=spec["id"], filename=str(s.get("weights_file", "face_multitask_v28.safetensors")),
                           revision=spec.get("revision"), local_files_only=os.environ.get("HF_HUB_OFFLINE") == "1")


def check_config(det_name: str, ident: str, expr: list[str], on: dict[str, bool]) -> None:
    """Each role (detector, identity, expression) must name an enabled backend."""
    errs = []
    if det_name not in ("mediapipe", "insightface", "pyfeat"):
        errs.append(f"face.detector must be mediapipe|insightface|pyfeat, got {det_name!r}")
    elif not on.get(det_name):
        errs.append(f"face.detector={det_name} needs face.{det_name}.enabled=true")
    if ident not in ("sface", "insightface", "pyfeat", "geometry", "none"):
        errs.append(f"face.identity.method must be sface|insightface|pyfeat|geometry|none, got {ident!r}")
    elif ident in ("sface", "insightface", "pyfeat") and not on.get(ident):
        errs.append(f"face.identity.method={ident} needs face.{ident}.enabled=true")
    if ident == "pyfeat" and det_name != "pyfeat":
        errs.append("face.identity.method=pyfeat needs face.detector=pyfeat")
    errs += [f"face.expression {e!r} needs face.{e}.enabled=true" for e in expr
             if e not in ("emotiefflib", "pyfeat") or not on.get(e)]
    if errs:
        raise ValueError("face config: " + "; ".join(errs))


def load_backends(ctx: StageContext) -> Backends:
    from .. import gpu
    from . import _face_models as fm

    s, cfg = ctx.scfg, ctx.cfg
    gpu.preload_cuda_libs()
    dev = gpu.device(str(s.get("device", "cuda")))
    sec = {k: dict(s.get(k) or {}) for k in ("mediapipe", "insightface", "pyfeat", "sface", "emotiefflib")}
    on = {k: bool(v.get("enabled", False)) for k, v in sec.items()}
    det_name, ident = str(s.get("detector", "mediapipe")), str((s.get("identity") or {}).get("method", "sface"))
    expr = list(s.get("expression") or [])
    check_config(det_name, ident, expr, on)
    used: list[str] = []
    mp = ins = pf = None
    if on["mediapipe"]:
        m = sec["mediapipe"]
        threads = int(m.get("threads") or os.environ.get("OMP_NUM_THREADS") or 1)
        mp = fm.MediaPipeDetector(_model_file(cfg, str(m.get("model", "mediapipe_face_landmarker"))),
                                  int(m.get("num_faces", 4)), float(m.get("min_detection_confidence", 0.5)),
                                  float(m.get("min_presence_confidence", 0.5)), threads)
        used.append(str(m.get("model", "mediapipe_face_landmarker")))
    if on["insightface"]:
        m = sec["insightface"]
        pack_key = str(m.get("pack", "insightface_buffalo_l"))
        ins = fm.InsightFaceDetector(cfg.root_path("cache") / "insightface", str(cfg.model(pack_key)["id"]),
                                     int(m.get("det_size", 640)), float(m.get("det_thresh", 0.5)),
                                     list(m.get("providers") or []), dev, recognition=ident == "insightface")
        used.append(pack_key)
    if on["pyfeat"]:
        m = sec["pyfeat"]
        pf = fm.PyFeat(dev, _pyfeat_weights(cfg, m), identity=ident == "pyfeat", amp=bool(m.get("amp", True)),
                       det_threshold=float(m.get("face_detection_threshold", 0.5)), blendshapes=bool(m.get("blendshapes", False)))
        used.append(str(m.get("model", "pyfeat_multitask_v2")))
    detector = {"mediapipe": mp, "insightface": ins, "pyfeat": pf}[det_name]
    embedder = None
    if ident == "sface":
        m = sec["sface"]
        embedder = fm.SFaceEmbedder(_model_file(cfg, str(m.get("model", "sface_opencv"))),
                                    list(m.get("providers") or []), dev)
        used.append(str(m.get("model", "sface_opencv")))
    elif ident == "insightface" and det_name != "insightface":
        embedder = ins
    emo = None
    if "emotiefflib" in expr:
        m = sec["emotiefflib"]
        key = str(m.get("model", "emotiefflib_enet_b0_8_va_mtl"))
        engine, spec = str(m.get("engine", "torch")), cfg.model(key)
        weights = _model_file(cfg, key) if spec["source"] == "url" and engine == "torch" else None
        emo = fm.EmotiEff(str(spec["id"]), engine, dev, float(m.get("crop_expand", 1.1)), weights)
        used.append(key)
    cross = mp if (mp is not None and det_name != "mediapipe" and bool(sec["mediapipe"].get("crosscheck", True))) else None
    return Backends(detector, ident, embedder, emo, pf if ("pyfeat" in expr and det_name != "pyfeat") else None,
                    cross, tuple(dict.fromkeys(used)))


# ------------------------------------------------------------------ identity
class Enrolment:
    """Reference for the chair's face built from the opening remarks only."""

    def __init__(self, method: str, s: dict[str, Any]) -> None:
        idc = dict(s.get("identity") or {})
        self.method = method
        thr = idc.get("threshold")
        self.threshold = float(thr) if thr is not None else DEFAULT_THRESHOLD.get(method, 0.0)
        self.min_frames, self.min_cos = int(idc.get("enroll_min_frames", 10)), float(idc.get("enroll_min_cos", 0.5))
        geo = dict(idc.get("geometry") or {})
        self.sig_pos, self.sig_size = float(geo.get("sigma_pos", 0.10)), float(geo.get("sigma_size", 0.25))
        self.embs: list[np.ndarray] = []
        self.geo: list[tuple[float, float, float]] = []
        self.ref: np.ndarray | None = None
        self.ref_geo: tuple[float, float, float] | None = None
        self.n_frames = 0
        self.summary: dict[str, Any] = {}

    def add(self, w: int, h: int, cands: list[Any]) -> None:
        self.n_frames += 1
        if not cands:
            return
        c = max(cands, key=lambda c: c.h)
        x1, y1, x2, y2 = (float(v) for v in c.box)
        self.geo.append(((x1 + x2) / 2 / w, (y1 + y2) / 2 / h, math.log(max(y2 - y1, 1.0) / h)))
        if c.emb is not None:
            self.embs.append(np.asarray(c.emb, np.float32))

    def finish(self) -> dict[str, Any]:
        out: dict[str, Any] = {"method": self.method, "threshold": self.threshold, "enroll_frames": self.n_frames,
                               "faces": len(self.geo)}
        if self.geo:
            g = np.array(self.geo)
            self.ref_geo = tuple(float(v) for v in np.median(g, 0))
            out["geometry"] = {"cx": self.ref_geo[0], "cy": self.ref_geo[1], "log_h": self.ref_geo[2]}
        if self.method in ("sface", "insightface", "pyfeat") and self.embs:
            e = np.stack(self.embs)
            keep = np.ones(len(e), bool)
            for _ in range(3):
                ref = e[keep].mean(0)
                ref /= max(float(np.linalg.norm(ref)), 1e-9)
                cos = e @ ref
                keep = cos >= self.min_cos
                if keep.sum() < 2:
                    break
            self.ref = ref if keep.sum() >= self.min_frames else None
            out.update(kept=int(keep.sum()), self_cos_median=float(np.median(cos[keep])) if keep.any() else None,
                       self_cos_p05=float(np.quantile(cos[keep], 0.05)) if keep.any() else None,
                       embedding=None if self.ref is None else [round(float(v), 6) for v in self.ref])
        ok = (self.ref is not None) if self.method in ("sface", "insightface", "pyfeat") else \
            (self.ref_geo is not None and len(self.geo) >= self.min_frames) if self.method == "geometry" else True
        out["ok"] = bool(ok)
        self.ok = bool(ok)
        self.summary = out
        return out

    def score(self, c: Any, w: int, h: int) -> float:
        if self.method == "none":
            return float("nan")
        if not self.ok:
            return 0.0
        if self.method == "geometry":
            assert self.ref_geo is not None
            x1, y1, x2, y2 = (float(v) for v in c.box)
            dx, dy = (x1 + x2) / 2 / w - self.ref_geo[0], (y1 + y2) / 2 / h - self.ref_geo[1]
            ds = math.log(max(y2 - y1, 1.0) / h) - self.ref_geo[2]
            return math.exp(-0.5 * ((dx * dx + dy * dy) / self.sig_pos ** 2 + ds * ds / self.sig_size ** 2))
        if c.emb is None or self.ref is None:
            return 0.0
        return float(np.dot(c.emb, self.ref))


# ------------------------------------------------------------------ per-frame measurement
def _measure(frames: list[tuple[int, float, np.ndarray]], cands: list[list[Any]], enrol: Enrolment,
             be: Backends, s: dict[str, Any]) -> list[dict[str, Any]]:
    from . import _face_models as fm

    rows, chosen = [], []
    for (k, t, rgb), cs in zip(frames, cands):
        h, w = rgb.shape[:2]
        row: dict[str, Any] = {"frame_idx": k, "t_s": t, "frame_w": w, "frame_h": h, "n_faces": len(cs),
                               "face_found": bool(cs)}
        best = None
        if cs:
            scores = [enrol.score(c, w, h) for c in cs]
            if enrol.method == "none":
                i = int(np.argmax([c.h for c in cs]))
                row.update(identity_score=float("nan"), identity_ok=True)
            else:
                i = int(np.argmax(scores))
                row.update(identity_score=scores[i], identity_ok=bool(enrol.ok and scores[i] >= enrol.threshold))
            best = cs[i]
            x1, y1, x2, y2 = (float(v) for v in best.box)
            blur, luma = fm.sharpness(fm.crop(rgb, best.box, 1.0, square=False))
            row.update(box_x=x1, box_y=y1, box_w=x2 - x1, box_h=y2 - y1, face_h_px=y2 - y1,
                       det_score=float(best.score), blur=blur, luma=luma)
            if best.pose is not None:
                row.update(zip(POSE, best.pose))
            row.update(best.extra)
            if best.blend:
                row.update({f"bs_{fm._bs_name(n)}": v for n, v in best.blend.items()})
        else:
            row.update(identity_ok=False)
        rows.append(row)
        chosen.append(best)
    sel = [i for i, c in enumerate(chosen) if c is not None]
    if not sel:
        return rows
    fr = [frames[i][2] for i in sel]
    boxes = [chosen[i].box for i in sel]
    t0 = time.perf_counter()
    if be.crosscheck is not None:  # MediaPipe blendshapes (and pose if missing) on the chair crop
        res = be.crosscheck.blend_on_crop([fm.crop(f, b, 1.4) for f, b in zip(fr, boxes)])
        for i, c in zip(sel, res):
            if c is None:
                continue
            if c.blend:
                rows[i].update({f"bs_{fm._bs_name(n)}": v for n, v in c.blend.items()})
            if "pitch_deg" not in rows[i] and c.pose is not None:
                rows[i].update(zip(POSE, c.pose))
            rows[i]["mp_mouth_open"] = c.extra.get("mp_mouth_open", float("nan"))
        be.timings["crosscheck"] = be.timings.get("crosscheck", 0.0) + time.perf_counter() - t0
    t0 = time.perf_counter()
    if be.emotieff is not None:
        for i, d in zip(sel, be.emotieff.predict(fr, boxes)):
            rows[i].update(d)
        be.timings["emotiefflib"] = be.timings.get("emotiefflib", 0.0) + time.perf_counter() - t0
    t0 = time.perf_counter()
    if be.pyfeat_expr is not None:
        for i, c in zip(sel, be.pyfeat_expr.on_boxes(fr, boxes)):
            if c is not None:
                rows[i].update(c.extra)
        be.timings["pyfeat"] = be.timings.get("pyfeat", 0.0) + time.perf_counter() - t0
    return rows


def _detect(batch: list[tuple[int, float, np.ndarray]], be: Backends) -> list[list[Any]]:
    imgs = [f for _, _, f in batch]
    t0 = time.perf_counter()
    cands = be.detector.detect(imgs)
    be.timings["detect"] = be.timings.get("detect", 0.0) + time.perf_counter() - t0
    if be.embedder is not None:
        t0 = time.perf_counter()
        be.embedder.embed(imgs, cands)
        be.timings["identity"] = be.timings.get("identity", 0.0) + time.perf_counter() - t0
    return cands


def finish_frames(df: Any, fps: float, s: dict[str, Any]) -> Any:
    """Causal track, head speed, masks and gates (each row uses only itself and earlier rows)."""
    from . import _face_models as fm

    g, m, tr = dict(s.get("gates") or {}), dict(s.get("masks") or {}), dict(s.get("track") or {})
    df = df.sort_values("t_s").reset_index(drop=True)
    for c in ("identity_score", "box_x", "box_y", "box_w", "box_h", "face_h_px", "det_score", "blur", "luma",
              *POSE, "bs_jawOpen", "bs_eyeBlinkLeft", "bs_eyeBlinkRight"):
        if c not in df.columns:
            df[c] = np.nan
    df["identity_ok"] = df["identity_ok"].fillna(False).astype(bool)
    df["mouth_open"] = df["bs_jawOpen"]
    df["mouth_open_flag"] = df["mouth_open"] > float(m.get("jaw_open", 0.025))
    df["reading"] = df["pitch_deg"] < float(m.get("reading_pitch_deg", -10.0))
    df["eye_blink"] = (df["bs_eyeBlinkLeft"] + df["bs_eyeBlinkRight"]) / 2
    df["eyes_closed"] = (df["eye_blink"] > float(m.get("eyes_closed", 0.5))).astype(float)
    df.loc[df["eye_blink"].isna() | df["reading"], "eyes_closed"] = np.nan
    fails = {
        "no_face": ~df["face_found"].astype(bool),
        "identity": ~df["identity_ok"],
        "small": ~(df["face_h_px"] >= float(g.get("min_face_h_px", 80))),
        "yaw": ~(df["yaw_deg"].abs() <= float(g.get("max_abs_yaw_deg", 40))),
        "pitch": ~(df["pitch_deg"].abs() <= float(g.get("max_abs_pitch_deg", 30))),
        "blur": ~(df["blur"] >= float(g.get("min_blur", 0.0))),
        "det": ~(df["det_score"] >= float(g.get("min_det_score", 0.0))),
    }
    reason = np.full(len(df), "", dtype=object)
    for name, mask in fails.items():
        mask = mask.to_numpy(bool)
        reason[mask] = [f"{r}|{name}" if r else name for r in reason[mask]]
    df["gate_reason"] = reason
    df["gate_ok"] = reason == ""
    # causal track over identity_ok rows: same track if close in time and the box overlaps the previous one
    iou_min, gap = float(tr.get("iou_min", 0.3)), float(tr.get("max_gap_s", 3.0))
    tid = np.full(len(df), -1, np.int64)
    age = np.full(len(df), np.nan)
    speed = np.full(len(df), np.nan)
    cur, start, prev_i = -1, 0.0, None
    for i, r in enumerate(df.itertuples(index=False)):
        if not r.identity_ok:
            continue
        box = np.array([r.box_x, r.box_y, r.box_x + r.box_w, r.box_y + r.box_h])
        if prev_i is not None:
            p = df.iloc[prev_i]
            pbox = np.array([p.box_x, p.box_y, p.box_x + p.box_w, p.box_y + p.box_h])
            dt = r.t_s - p.t_s
            if dt <= gap + 1e-9 and fm.iou(box, pbox) >= iou_min:
                d = math.sqrt(sum((getattr(r, c) - p[c]) ** 2 for c in POSE))
                speed[i] = d / dt if dt > 0 and np.isfinite(d) else np.nan
            else:
                cur, start = cur + 1, r.t_s
        else:
            cur, start = 0, r.t_s
        tid[i], age[i], prev_i = cur, r.t_s - start, i
    df["track_id"], df["track_age_s"], df["head_speed_dps"] = tid, age, speed
    df["t_start_s"] = df["t_end_s"] = df["t_s"].astype("float64")
    return df


def assign_turns(df: Any, feat: Any) -> Any:
    starts, ends = feat["t_start_s"].to_numpy(float), feat["t_end_s"].to_numpy(float)
    j = np.searchsorted(starts, df["t_s"].to_numpy(float), side="right") - 1
    ok = (j >= 0) & (df["t_s"].to_numpy(float) < ends[np.clip(j, 0, None)])
    df["turn_idx"] = np.where(ok, feat["turn_idx"].to_numpy()[np.clip(j, 0, None)], -1).astype(np.int64)
    df["qa_idx"] = np.where(ok, feat["qa_idx"].to_numpy()[np.clip(j, 0, None)], -1).astype(np.int64)
    df["segment_kind"] = np.where(ok, feat["segment_kind"].to_numpy()[np.clip(j, 0, None)], "other")
    return df


# ------------------------------------------------------------------ aggregation
def feature_columns(df: Any, s: dict[str, Any]) -> tuple[list[str], list[str]]:
    """(columns averaged over gated frames, columns also averaged over gated mouth-closed frames)."""
    from . import _face_models as fm

    cols = [c for c in df.columns]
    if bool(s.get("upper_face_only", True)):
        feats = [f"bs_{b}" for b in fm.UPPER_FACE_BLENDS if f"bs_{b}" in cols] + [a for a in fm.UPPER_FACE_AUS if a in cols]
    else:
        feats = [c for c in cols if c.startswith(("bs_", "au", "ex_", "pf_"))]
    feats = [*POSE, "head_speed_dps", "blur", "luma", *feats]
    mc = [c for c in (s.get("aggregate") or {}).get("mouth_closed_columns", []) if c in cols]
    return feats, mc


def aggregate(df: Any, feat: Any, fps: float, s: dict[str, Any]) -> Any:
    import pandas as pd

    a = dict(s.get("aggregate") or {})
    min_g = int(a.get("min_gated_frames", 3))
    blink_ok = fps >= float(s.get("blink_min_fps", 10))
    feats, mc = feature_columns(df, s)
    rows = []

    def summarise(sub: Any) -> dict[str, Any]:
        g = sub[sub["gate_ok"]]
        out: dict[str, Any] = {"n_frames": len(sub), "n_face": int(sub["face_found"].sum()),
                               "n_identity": int(sub["identity_ok"].sum()), "n_gated": len(g),
                               "gated_frac": len(g) / len(sub) if len(sub) else np.nan}
        enough = len(g) >= min_g
        for c in feats:
            out[c] = float(g[c].mean()) if enough else np.nan
        quiet = g[~g["mouth_open_flag"].astype(bool)]
        out["n_mouth_closed"] = len(quiet)
        for c in mc:
            out[f"{c}_mc"] = float(quiet[c].mean()) if len(quiet) >= min_g else np.nan
        ec = g["eyes_closed"].dropna()
        out["eyes_closed_frac"] = float(ec.mean()) if len(ec) >= min_g else np.nan
        out["reading_frac"] = float(g["reading"].mean()) if enough else np.nan
        out["mouth_open_frac"] = float(g["mouth_open_flag"].mean()) if enough else np.nan
        out["blink_rate_per_min"] = np.nan
        if blink_ok and len(ec) >= min_g:  # closing events between consecutive gated frames
            e = g[["t_s", "eyes_closed"]].dropna()
            step = np.diff(e["t_s"].to_numpy()) <= 1.5 / fps
            onsets = int(((np.diff(e["eyes_closed"].to_numpy()) > 0) & step).sum())
            out["blink_rate_per_min"] = onsets / (len(e) / fps / 60.0)
        return out

    t = df["t_s"].to_numpy(float)
    for r in feat.itertuples(index=False):
        t0, t1 = float(r.t_start_s), float(r.t_end_s)
        base = {"turn_idx": int(r.turn_idx), "qa_idx": int(r.qa_idx), "segment_kind": r.segment_kind}
        sub = df[(t >= t0) & (t < t1)]
        rows.append({"unit": "turn", "window_s": np.nan, "unit_idx": -1, **base, "t_start_s": t0, "t_end_s": t1,
                     **summarise(sub)})
        for w in a.get("windows_s", []) or []:
            w = float(w)
            for k in range(int(math.ceil((t1 - t0) / w - 1e-9))):
                a0, a1 = t0 + k * w, min(t0 + (k + 1) * w, t1)
                sub = df[(t >= a0) & (t < a1)]
                rows.append({"unit": "window", "window_s": w, "unit_idx": k, **base, "t_start_s": a0, "t_end_s": a1,
                             **summarise(sub)})
    cols = ["unit", "window_s", "unit_idx", "turn_idx", "qa_idx", "segment_kind", "t_start_s", "t_end_s"]
    return pd.DataFrame(rows, columns=None if rows else cols)


# ------------------------------------------------------------------ the stage
def run(ctx: StageContext) -> StageResult:
    import pandas as pd

    s = ctx.scfg
    fps = float(s.get("fps", 1.0))
    cut = max_seconds(ctx.cfg)
    turns = _turns(ctx)
    feat, enroll_ranges = _segments(ctx, turns, cut)
    feat_ranges = [(float(a), float(b)) for a, b in zip(feat["t_start_s"], feat["t_end_s"])]
    src = FrameSource(ctx, fps)
    be = load_backends(ctx)
    enrol = Enrolment(be.identity, s)
    bs = int(s.get("batch_size", 32))
    from ._video import batched

    t_all = time.perf_counter()
    n_enrol = 0
    try:
        for batch in batched(src.frames(enroll_ranges), bs):
            for (_, _, f), cs in zip(batch, _detect(batch, be)):
                enrol.add(f.shape[1], f.shape[0], cs)
            n_enrol += len(batch)
        summary = enrol.finish()
        if not enrol.ok:
            ctx.log.warning("face.enroll_failed", **{k: v for k, v in summary.items() if k != "embedding"})
        rows: list[dict[str, Any]] = []
        t_dec = time.perf_counter()
        for batch in batched(src.frames(feat_ranges), bs):
            rows.extend(_measure(batch, _detect(batch, be), enrol, be, s))
        loop_s = time.perf_counter() - t_dec
    finally:
        be.close()
        src.close()
    df = pd.DataFrame(rows) if rows else pd.DataFrame({"frame_idx": pd.Series(dtype="int64"),
                                                        "t_s": pd.Series(dtype="float64"),
                                                        "face_found": pd.Series(dtype=bool),
                                                        "identity_ok": pd.Series(dtype=bool)})
    df = assign_turns(finish_frames(df, fps, s), feat)
    df = df[df["turn_idx"] >= 0] if len(df) else df
    agg = aggregate(df, feat, fps, s)
    lead = ["frame_idx", "t_s", "turn_idx", "qa_idx", "segment_kind", "frame_w", "frame_h", "n_faces", "face_found",
            "box_x", "box_y", "box_w", "box_h", "face_h_px", "det_score", "identity_score", "identity_ok", *POSE,
            "blur", "luma", "mouth_open", "mouth_open_flag", "reading", "eye_blink", "eyes_closed", "track_id",
            "track_age_s", "head_speed_dps", "gate_ok", "gate_reason"]
    df = df[[c for c in lead if c in df.columns] + sorted(c for c in df.columns if c not in lead)]
    ctx.write_table(ctx.stamp(df), "face_frames", models=be.models)
    ctx.write_table(ctx.stamp(agg), "face_turns", models=be.models)
    io.atomic_write_json(ctx.out("face_enroll"), {**summary, "enroll_ranges": enroll_ranges, "fps": fps,
                                                   "source": src.mode, "models": list(be.models)})
    ctx.add_output(ctx.out("face_enroll"))
    elapsed = time.perf_counter() - t_all
    n = len(rows)
    ctx.result.notes.update(
        fps=fps, source=src.mode, frames_enrol=n_enrol, frames_feature=n, enroll_ok=enrol.ok,
        identity_method=be.identity, identity_threshold=enrol.threshold,
        enroll_self_cos_median=summary.get("self_cos_median"),
        identity_ok_frac=float(df["identity_ok"].mean()) if len(df) else None,
        gated_frac=float(df["gate_ok"].mean()) if len(df) else None,
        n_answers=int(len(feat)), max_seconds=cut, elapsed_s=round(elapsed, 2),
        frames_per_s=round((n + n_enrol) / elapsed, 2) if elapsed > 0 else None,
        feature_loop_s=round(loop_s, 2), timings_s={k: round(v, 2) for k, v in be.timings.items()},
        decode=src.decode_events[-4:])
    return ctx.result


# ------------------------------------------------------------------ weights prefetch (needs outbound network)
def prefetch(cfg: Config) -> dict[str, str]:
    """Download every weight file the enabled face configuration needs into the shared cache."""
    from .. import models

    s, report = cfg.section("face"), {}
    keys = [str((s.get(k) or {}).get("model")) for k in ("mediapipe", "sface", "emotiefflib")
            if (s.get(k) or {}).get("enabled") and (s.get(k) or {}).get("model")]
    keys = [k for k in keys if cfg.model(k)["source"] == "url"]
    report.update(models.prefetch(cfg, keys))
    em = s.get("emotiefflib") or {}
    if em.get("enabled") and (cfg.model(str(em.get("model")))["source"] != "url" or em.get("engine") == "onnx"):
        try:
            from emotiefflib.utils import get_model_path_onnx, get_model_path_torch

            mid = str(cfg.model(str(em.get("model")))["id"])
            p = (get_model_path_torch if em.get("engine", "torch") == "torch" else get_model_path_onnx)(mid)
            report[str(em.get("model"))] = f"ok {p} sha256={io.sha256_file(Path(p))[:16]}"
        except Exception as e:  # report and continue
            report[str(em.get("model"))] = f"error: {e!r}"
    ins = s.get("insightface") or {}
    if ins.get("enabled"):
        try:
            from insightface.utils import ensure_available

            key = str(ins.get("pack", "insightface_buffalo_l"))
            p = ensure_available("models", str(cfg.model(key)["id"]), root=str(cfg.root_path("cache") / "insightface"))
            report[key] = f"ok {p}"
        except Exception as e:
            report[str(ins.get("pack"))] = f"error: {e!r}"
    pf = s.get("pyfeat") or {}
    if pf.get("enabled"):
        try:
            w = _pyfeat_weights(cfg, pf)
            from feat import Detectorv2

            Detectorv2(device="cpu", identity_model="arcface" if (s.get("identity") or {}).get("method") == "pyfeat"
                       else None, multitask_weights=w)
            report[str(pf.get("model"))] = f"ok {w}"
        except Exception as e:
            report[str(pf.get("model"))] = f"error: {e!r}"
    return report


def _main(argv: list[str]) -> int:
    import argparse

    from ..config import apply_env, load

    p = argparse.ArgumentParser(prog="python -m fedpress.stages.face")
    p.add_argument("command", choices=["prefetch"])
    p.add_argument("--config")
    p.add_argument("--set", action="append", default=[])
    a = p.parse_args(argv)
    cfg = load(a.config, a.set)
    apply_env(cfg, offline=False)
    report = prefetch(cfg)
    print(json.dumps(report, indent=2))
    return 1 if any(str(v).startswith("error") for v in report.values()) else 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
