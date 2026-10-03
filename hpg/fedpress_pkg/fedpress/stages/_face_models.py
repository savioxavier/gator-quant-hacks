"""Face model backends for the face stage: detectors, identity embedders and expression models.

Every backend works on RGB uint8 frames and on ``Cand`` records (one per detected face). Conventions:
boxes are pixel ``(x1, y1, x2, y2)``; ``kps5`` are the five ArcFace alignment points in image order (eye on the
image left, eye on the image right, nose tip, mouth corner image left, mouth corner image right); head pose is
in degrees with pitch > 0 = looking up, yaw > 0 = turned to the subject's right, roll > 0 = tilted to the
subject's right (the py-feat convention).

Licences (also in config.yaml models: and docs/FACE.md):
  MediaPipe Face Landmarker (Apache-2.0); SFace via OpenCV Zoo (Apache-2.0); EmotiEffLib code Apache-2.0 with
  weights trained on AffectNet (non-commercial research); InsightFace buffalo_l (non-commercial research
  only; code MIT); py-feat code MIT, face_multitask_v2 weights research-only, its ArcFace identity weights
  come from InsightFace (non-commercial).
"""

from __future__ import annotations

import math
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

# ArcFace / SFace 112x112 alignment template (same points as OpenCV FaceRecognizerSF.alignCrop)
ARC_TEMPLATE = np.array([[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
                         [41.5493, 92.3655], [70.7299, 92.2041]], dtype=np.float64)
MP_KPS5 = ((33, 133), (362, 263), (1,), (61,), (291,))   # MediaPipe 478-mesh indices per alignment point
EMOTIEFF_8 = ("anger", "contempt", "disgust", "fear", "happiness", "neutral", "sadness", "surprise")


@dataclass
class Cand:
    box: np.ndarray                         # (4,) x1, y1, x2, y2 in pixels
    score: float = 1.0                      # detector confidence (1.0 when the detector gives none)
    kps5: np.ndarray | None = None          # (5, 2) pixels, ArcFace order
    pose: tuple[float, float, float] | None = None   # pitch, yaw, roll (deg)
    blend: dict[str, float] | None = None   # 52 MediaPipe/ARKit blendshapes
    emb: np.ndarray | None = None           # L2-normalised identity embedding
    extra: dict[str, float] = field(default_factory=dict)  # backend columns (au*, pf_*, ...)

    @property
    def h(self) -> float:
        return float(self.box[3] - self.box[1])


# ------------------------------------------------------------------ geometry helpers
def box_of(xy: np.ndarray) -> np.ndarray:
    return np.array([xy[:, 0].min(), xy[:, 1].min(), xy[:, 0].max(), xy[:, 1].max()], dtype=np.float32)


def iou(a: np.ndarray, b: np.ndarray) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return float(inter / union) if union > 0 else 0.0


def umeyama(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """2x3 similarity transform mapping src points onto dst (least squares, no reflection)."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    s, d = src - mu_s, dst - mu_d
    cov = d.T @ s / len(src)
    u, sig, vt = np.linalg.svd(cov)
    sign = np.eye(2)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        sign[1, 1] = -1
    rot = u @ sign @ vt
    scale = np.trace(np.diag(sig) @ sign) / s.var(0).sum()
    t = mu_d - scale * rot @ mu_s
    return np.hstack([scale * rot, t[:, None]])


def align112(rgb: np.ndarray, kps5: np.ndarray) -> np.ndarray:
    import cv2

    m = umeyama(np.asarray(kps5, np.float64), ARC_TEMPLATE)
    return cv2.warpAffine(rgb, m, (112, 112), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def crop(rgb: np.ndarray, box: np.ndarray, expand: float = 1.0, square: bool = True) -> np.ndarray:
    """Face crop around ``box`` scaled by ``expand``; parts outside the frame are edge-padded."""
    import cv2

    x1, y1, x2, y2 = (float(v) for v in box)
    cx, cy, w, h = (x1 + x2) / 2, (y1 + y2) / 2, (x2 - x1) * expand, (y2 - y1) * expand
    if square:
        w = h = max(w, h)
    a = np.array([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]).round().astype(int)
    H, W = rgb.shape[:2]
    pad = max(0, -a[0], -a[1], a[2] - W, a[3] - H)
    img = cv2.copyMakeBorder(rgb, pad, pad, pad, pad, cv2.BORDER_REPLICATE) if pad else rgb
    a = a + pad
    out = img[a[1]:a[3], a[0]:a[2]]
    return np.ascontiguousarray(out) if out.size else np.zeros((8, 8, 3), np.uint8)


def sharpness(rgb_crop: np.ndarray, height: int = 112) -> tuple[float, float]:
    """(variance of the Laplacian at a fixed crop height, mean luminance 0-255)."""
    import cv2

    g = cv2.cvtColor(rgb_crop, cv2.COLOR_RGB2GRAY)
    if g.shape[0] != height and g.shape[0] > 0:
        g = cv2.resize(g, (max(1, round(g.shape[1] * height / g.shape[0])), height), interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(g, cv2.CV_64F).var()), float(g.mean())


def pose_from_matrix(m: np.ndarray) -> tuple[float, float, float]:
    """MediaPipe facial transformation matrix (canonical face -> camera, OpenGL axes) -> pitch, yaw, roll.
    Rx > 0 tips the head's top toward the camera (looking down), so pitch = -Rx; Ry > 0 turns the face to
    the image right (the subject's left), so yaw = -Ry; Rz > 0 tilts toward the subject's right."""
    r = np.asarray(m, np.float64)[:3, :3]
    rx = math.degrees(math.atan2(r[2, 1], r[2, 2]))
    ry = math.degrees(math.asin(float(np.clip(-r[2, 0], -1.0, 1.0))))
    rz = math.degrees(math.atan2(r[1, 0], r[0, 0]))
    return -rx, -ry, rz


def _providers(requested: list[str] | None, device: str) -> list[str]:
    import onnxruntime as ort

    avail = set(ort.get_available_providers())
    want = list(requested or ["CPUExecutionProvider"])
    if device != "cuda":
        want = [p for p in want if p != "CUDAExecutionProvider"]
    return [p for p in want if p in avail] or ["CPUExecutionProvider"]


# ------------------------------------------------------------------ detectors
class MediaPipeDetector:
    """MediaPipe Face Landmarker (CPU; IMAGE mode, so every frame is independent). 478 landmarks, 52
    blendshapes and the head pose matrix. Threads: one landmarker per thread (the C API releases the GIL)."""

    name = "mediapipe"

    def __init__(self, model_path: Path, num_faces: int = 4, min_det: float = 0.5, min_presence: float = 0.5,
                 threads: int = 1) -> None:
        self.model_path, self.num_faces, self.min_det, self.min_presence = str(model_path), num_faces, min_det, min_presence
        self.threads = max(1, int(threads))
        self._local = threading.local()
        self._all: list[Any] = []
        self._pool = ThreadPoolExecutor(self.threads) if self.threads > 1 else None

    def _landmarker(self) -> Any:
        lm = getattr(self._local, "lm", None)
        if lm is None:
            from mediapipe.tasks.python import BaseOptions, vision

            opts = vision.FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=self.model_path), num_faces=self.num_faces,
                min_face_detection_confidence=self.min_det, min_face_presence_confidence=self.min_presence,
                output_face_blendshapes=True, output_facial_transformation_matrixes=True)
            lm = self._local.lm = vision.FaceLandmarker.create_from_options(opts)
            self._all.append(lm)
        return lm

    def _one(self, rgb: np.ndarray) -> list[Cand]:
        import mediapipe as mp

        h, w = rgb.shape[:2]
        res = self._landmarker().detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
        out = []
        for i, pts in enumerate(res.face_landmarks):
            xy = np.array([[p.x * w, p.y * h] for p in pts], np.float32)
            kps = np.array([xy[list(ix)].mean(0) for ix in MP_KPS5], np.float32)
            blend = {c.category_name: float(c.score) for c in res.face_blendshapes[i]} if res.face_blendshapes else None
            pose = pose_from_matrix(res.facial_transformation_matrixes[i]) if res.facial_transformation_matrixes else None
            out.append(Cand(box=box_of(xy), kps5=kps, pose=pose, blend=blend,
                            extra={"mp_mouth_open": _mouth_ratio(xy)}))
        return out

    def detect(self, frames: list[np.ndarray]) -> list[list[Cand]]:
        if self._pool is None:
            return [self._one(f) for f in frames]
        return list(self._pool.map(self._one, frames))

    def blend_on_crop(self, crops: list[np.ndarray]) -> list[Cand | None]:
        """Cross-check use: run on face crops; returns the largest face per crop (coordinates in the crop)."""
        res = self.detect(crops)
        return [max(r, key=lambda c: c.h) if r else None for r in res]

    def close(self) -> None:
        for lm in self._all:
            lm.close()
        if self._pool is not None:
            self._pool.shutdown()


def _mouth_ratio(xy: np.ndarray) -> float:
    """Inner-lip gap (13-14) over face height (10-152) on the MediaPipe mesh."""
    face_h = float(np.linalg.norm(xy[10] - xy[152]))
    return float(np.linalg.norm(xy[13] - xy[14]) / face_h) if face_h > 0 else float("nan")


class InsightFaceDetector:
    """InsightFace FaceAnalysis (buffalo_l: SCRFD-10GF detector, ArcFace R50 embedding, 3D-68 landmarks for
    pose) on ONNX Runtime. Non-commercial research weights."""

    name = "insightface"

    def __init__(self, root: Path, pack: str = "buffalo_l", det_size: int = 640, det_thresh: float = 0.5,
                 providers: list[str] | None = None, device: str = "cuda", recognition: bool = True) -> None:
        from insightface.app import FaceAnalysis

        mods = ["detection", "landmark_3d_68"] + (["recognition"] if recognition else [])
        prov = _providers(providers, device)
        self.app = FaceAnalysis(name=pack, root=str(root), allowed_modules=mods, providers=prov)
        self.app.prepare(ctx_id=0 if "CUDAExecutionProvider" in prov else -1, det_thresh=det_thresh,
                         det_size=(det_size, det_size))
        self.providers = prov

    def detect(self, frames: list[np.ndarray]) -> list[list[Cand]]:
        out = []
        for rgb in frames:
            faces = self.app.get(np.ascontiguousarray(rgb[:, :, ::-1]))  # insightface expects BGR
            cands = []
            for f in faces:
                pose = None
                if f.pose is not None:  # insightface 3D-68 pose: pitch + = up; its yaw/roll + = subject's left
                    pose = (float(f.pose[0]), -float(f.pose[1]), -float(f.pose[2]))  # (checked against MediaPipe)
                emb = f.normed_embedding
                cands.append(Cand(box=np.asarray(f.bbox, np.float32), score=float(f.det_score),
                                  kps5=None if f.kps is None else np.asarray(f.kps, np.float32), pose=pose,
                                  emb=None if emb is None else np.asarray(emb, np.float32)))
            out.append(cands)
        return out

    def embed(self, frames: list[np.ndarray], cands: list[list[Cand]]) -> None:
        """ArcFace embeddings for candidates found by another detector (needs kps5)."""
        from insightface.app.common import Face

        rec = self.app.models.get("recognition")
        if rec is None:
            raise RuntimeError("insightface recognition model not loaded")
        for rgb, cs in zip(frames, cands):
            bgr = np.ascontiguousarray(rgb[:, :, ::-1])
            for c in cs:
                if c.emb is None and c.kps5 is not None:
                    f = Face(bbox=c.box, kps=c.kps5, det_score=c.score)
                    rec.get(bgr, f)
                    c.emb = np.asarray(f.normed_embedding, np.float32)

    def close(self) -> None:
        pass


class SFaceEmbedder:
    """SFace (MobileFaceNet, OpenCV Zoo, Apache-2.0) on 112x112 ArcFace-aligned crops; ONNX Runtime.
    Preprocessing as OpenCV FaceRecognizerSF: RGB, 0-255, no mean/std. Cosine >= 0.363 = same person (OpenCV)."""

    name = "sface"
    default_threshold = 0.363

    def __init__(self, model_path: Path, providers: list[str] | None = None, device: str = "cpu") -> None:
        import onnxruntime as ort

        so = ort.SessionOptions()
        so.log_severity_level = 3  # the zoo export triggers one initializer warning per constant
        so.intra_op_num_threads = int(os.environ.get("OMP_NUM_THREADS", "1") or 1)
        self.sess = ort.InferenceSession(str(model_path), sess_options=so, providers=_providers(providers, device))
        self.inp = self.sess.get_inputs()[0].name

    def embed_crops(self, aligned: list[np.ndarray]) -> np.ndarray:
        if not aligned:
            return np.zeros((0, 128), np.float32)
        x = np.stack(aligned).astype(np.float32).transpose(0, 3, 1, 2)
        e = np.concatenate([self.sess.run(None, {self.inp: x[i:i + 1]})[0] for i in range(len(x))])  # batch 1 graph
        return (e / np.linalg.norm(e, axis=1, keepdims=True).clip(1e-9)).astype(np.float32)

    def embed(self, frames: list[np.ndarray], cands: list[list[Cand]]) -> None:
        todo = [(c, align112(rgb, c.kps5)) for rgb, cs in zip(frames, cands) for c in cs
                if c.emb is None and c.kps5 is not None]
        for (c, _), e in zip(todo, self.embed_crops([a for _, a in todo])):
            c.emb = e

    def close(self) -> None:
        pass


# ------------------------------------------------------------------ expression models
class EmotiEff:
    """EmotiEffLib (ex-HSEmotion) enet_b0_8_va_mtl: 8 AffectNet expression probabilities + valence/arousal.
    Weights trained on AffectNet: non-commercial research use."""

    name = "emotiefflib"

    def __init__(self, model_name: str, engine: str = "torch", device: str = "cuda", expand: float = 1.1,
                 weights: Path | None = None) -> None:
        import emotiefflib.facial_analysis as efa

        if weights is not None and engine == "torch":  # pinned, prefetched file instead of ~/.emotiefflib
            efa.get_model_path_torch = lambda name, _p=str(weights): _p
        self.rec = efa.EmotiEffLibRecognizer(engine=engine, model_name=model_name,
                                             device=device if engine == "torch" else "cpu")
        self.expand, self.engine = expand, engine
        self.mtl = "_mtl" in model_name
        self.labels = [v.lower() for _, v in sorted(self.rec.idx_to_emotion_class.items())]
        dummy = np.zeros((64, 64, 3), np.uint8)
        self.predict([dummy] * 4, [np.array([0, 0, 64, 64], np.float32)] * 4)  # CUDA/cuDNN warm-up off the clock

    def predict(self, frames: list[np.ndarray], boxes: list[np.ndarray]) -> list[dict[str, float]]:
        if not boxes:
            return []
        crops = [crop(f, b, self.expand) for f, b in zip(frames, boxes)]
        if self.engine == "torch":
            import torch

            with torch.inference_mode():
                _, scores = self.rec.predict_emotions(crops, logits=False)
        else:
            _, scores = self.rec.predict_emotions(crops, logits=False)
        out = []
        n = len(self.labels)
        for s in np.asarray(scores, np.float64):
            d = {f"ex_{lab}": float(s[i]) for i, lab in enumerate(self.labels)}
            if self.mtl:
                d["ex_valence"], d["ex_arousal"] = float(s[n]), float(s[n + 1])
            out.append(d)
        return out

    def close(self) -> None:
        pass


class PyFeat:
    """py-feat Detectorv2 (RetinaFace + face_multitask_v2): 20 AU probabilities, 7 emotions, valence/arousal,
    gaze, head pose and 52 blendshapes from one model; ArcFace identity optional. Separate environment
    (env/environment-pyfeat.yml). Weights research-only; ArcFace weights from InsightFace (non-commercial)."""

    name = "pyfeat"

    def __init__(self, device: str = "cuda", weights: str | None = None, identity: bool = False, amp: bool = True,
                 det_threshold: float = 0.5, blendshapes: bool = False) -> None:
        from feat import Detectorv2

        self.det = Detectorv2(device=device, face_detection_threshold=det_threshold,
                              identity_model="arcface" if identity else None, multitask_weights=weights,
                              amp=amp if device == "cuda" else False)
        self.threshold, self.identity, self.blendshapes = det_threshold, identity, blendshapes
        self.detect([np.zeros((540, 960, 3), np.uint8)] * 2)  # CUDA/cuDNN warm-up off the clock

    @staticmethod
    def _batch(frames: list[np.ndarray]) -> dict[str, Any]:
        import torch

        img = torch.from_numpy(np.stack(frames)).permute(0, 3, 1, 2).contiguous()  # uint8 [B, 3, H, W]
        b = img.shape[0]
        z = torch.zeros(b)
        return {"Image": img, "Scale": torch.ones(b), "Padding": {"Left": z, "Top": z, "Right": z, "Bottom": z}}

    def _rows(self, df: Any) -> list[tuple[np.ndarray, Cand | None]]:
        """Per-face Cand from py-feat's wide output (~1,500 columns incl. the mesh): column arrays, no iterrows."""
        cols = {str(c): c for c in df.columns}
        aus = [c for c in cols if c.startswith("AU")]
        emos = [str(e) for e in self.det.multitask.emotion_names]
        bs_cols = [c for c in cols if c in _MP_BLEND_SET] if self.blendshapes else []
        id_cols = [c for c in cols if c.startswith("Identity_")] if self.identity else []
        a = {c: df[cols[c]].to_numpy(np.float64) for c in
             ["FaceRectX", "FaceRectY", "FaceRectWidth", "FaceRectHeight", "FaceScore", "valence", "arousal",
              "gaze_pitch", "gaze_yaw", "Pitch", "Yaw", "Roll", *aus, *emos, *bs_cols] if c in cols}
        lx = df[[cols[f"x_{i}"] for i in range(68)]].to_numpy(np.float64) if "x_0" in cols else None
        ly = df[[cols[f"y_{i}"] for i in range(68)]].to_numpy(np.float64) if "y_0" in cols else None
        ids = df[[cols[c] for c in id_cols]].to_numpy(np.float32) if id_cols else None
        out: list[tuple[np.ndarray, Cand | None]] = []
        for i in range(len(df)):
            x, y, w, h = (a[k][i] for k in ("FaceRectX", "FaceRectY", "FaceRectWidth", "FaceRectHeight"))
            if not np.isfinite(x):
                out.append((np.full(4, np.nan), None))
                continue
            box = np.array([x, y, x + w, y + h], np.float32)
            extra = {f"au{c[2:].zfill(2)}": float(a[c][i]) for c in aus}
            extra.update({f"pf_{e.lower()}": float(a[e][i]) for e in emos if e in a})
            extra.update(pf_valence=float(a["valence"][i]), pf_arousal=float(a["arousal"][i]),
                         pf_gaze_pitch=math.degrees(a["gaze_pitch"][i]), pf_gaze_yaw=math.degrees(a["gaze_yaw"][i]),
                         pf_pitch=math.degrees(a["Pitch"][i]), pf_yaw=math.degrees(a["Yaw"][i]),
                         pf_roll=math.degrees(a["Roll"][i]))
            extra.update({f"pf_bs_{_bs_name(c)}": float(a[c][i]) for c in bs_cols})
            emb = None
            if ids is not None and np.isfinite(ids[i]).all():
                emb = ids[i] / max(float(np.linalg.norm(ids[i])), 1e-9)
            kps5 = None
            if lx is not None and ly is not None and np.isfinite(lx[i]).all() and np.isfinite(ly[i]).all():
                pts = np.stack([lx[i], ly[i]], 1)
                kps5 = np.array([pts[36:42].mean(0), pts[42:48].mean(0), pts[30], pts[48], pts[54]], np.float32)
            # blend=None: bs_* columns always come from MediaPipe (detector or cross-check), never mixed sources
            out.append((box, Cand(box=box, score=float(a["FaceScore"][i]) if "FaceScore" in a else 1.0, kps5=kps5,
                                  pose=(extra["pf_pitch"], extra["pf_yaw"], extra["pf_roll"]), blend=None,
                                  emb=emb, extra=extra)))
        return out

    def detect(self, frames: list[np.ndarray]) -> list[list[Cand]]:
        batch = self._batch(frames)
        faces = self.det.detect_faces(batch["Image"], face_detection_threshold=self.threshold)
        df = self.det.forward(faces, batch)
        rows, i, out = self._rows(df), 0, []
        for f in faces:
            n = int(f["faces"].shape[0])
            out.append([c for _, c in rows[i:i + n] if c is not None])
            i += n
        return out

    def on_boxes(self, frames: list[np.ndarray], boxes: list[np.ndarray]) -> list[Cand | None]:
        """Multitask outputs for given chair boxes (skips RetinaFace)."""
        import torch

        if not frames:
            return []
        batch = self._batch(frames)
        faces = self.det.crop_faces_from_boxes(batch["Image"], [torch.as_tensor(b[None], dtype=torch.float32)
                                                                 for b in boxes])
        df = self.det.forward(faces, batch)
        return [c for _, c in self._rows(df)]

    def close(self) -> None:
        pass


_MP_BLEND_SET = {
    "_neutral", "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight", "cheekPuff",
    "cheekSquintLeft", "cheekSquintRight", "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft", "eyeLookDownRight",
    "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight", "eyeLookUpLeft", "eyeLookUpRight",
    "eyeSquintLeft", "eyeSquintRight", "eyeWideLeft", "eyeWideRight", "jawForward", "jawLeft", "jawOpen", "jawRight",
    "mouthClose", "mouthDimpleLeft", "mouthDimpleRight", "mouthFrownLeft", "mouthFrownRight", "mouthFunnel",
    "mouthLeft", "mouthLowerDownLeft", "mouthLowerDownRight", "mouthPressLeft", "mouthPressRight", "mouthPucker",
    "mouthRight", "mouthRollLower", "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper", "mouthSmileLeft",
    "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight", "mouthUpperUpLeft", "mouthUpperUpRight",
    "noseSneerLeft", "noseSneerRight",
}
#: Blendshapes driven by the brows, eyes and cheeks (not by speech): the upper-face primary set.
UPPER_FACE_BLENDS = tuple(sorted(n for n in _MP_BLEND_SET if n.startswith(("brow", "eye", "cheekSquint"))))
UPPER_FACE_AUS = ("au01", "au02", "au04", "au05", "au06", "au07", "au43")


def _bs_name(name: str) -> str:
    return "neutral" if name == "_neutral" else name
