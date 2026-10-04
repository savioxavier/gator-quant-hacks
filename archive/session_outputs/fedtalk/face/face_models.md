# Face channel: models, validity, baseline design (research notes, 2026-10-03)

Status legend: [V] opened and checked at the cited URL on 2026-10-03; [P] partially verified (secondary source or summary only); [U] not opened / unverified.

## 0. Facts that change the plan

- [V] Powell is no longer chair. Last Powell presser: 2026-04-29 ("Chair Powell's Press Conference"). Kevin Warsh gave the 2026-06-17, 2026-07-29 and 2026-09-16 pressers ("Chairman Warsh's Press Conference").
  https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20260429.pdf
  https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20260617.pdf
  https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20260916.pdf
  [P] Warsh sworn in 2026-05-22 (news summary): https://seekingalpha.com/news/4596371-kevin-warsh-is-sworn-in-as-federal-reserve-chair (403 to fetch; search snippet only)
  Consequence: any live face signal must work for a chair with 3 pressers of baseline. A Powell-only model is a historical study.
- [V] 2025: all 8 meetings had pressers; 2026 so far: Jan, Mar, Apr, Jun, Jul, Sep. https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- [V] Fed presser pages embed a Brightcove player and link youtube.com/federalreserve; transcripts are PDFs at /mediacenter/files/FOMCpresconfYYYYMMDD.pdf. https://www.federalreserve.gov/monetarypolicy/fomcpresconf20260916.htm
- [V] Azure Face emotion attribute retired (June 2022 announcement; existing customers until 2023-06-30; API now returns 403 UnsupportedFeature for emotion).
  https://learn.microsoft.com/azure/ai-services/face/whats-new-face#june-2022
  https://learn.microsoft.com/azure/ai-services/face/reference-face-error-codes#common-error-codes
  https://learn.microsoft.com/javascript/api/overview/azure/cognitiveservices-face-readme?view=azure-node-latest

## 1. Prior Fed face research (what was measured, how big)

| Paper | Tool | Sample | Finding | Type of effect |
|---|---|---|---|---|
| Curti & Kazinnik, "Let's Face It", JME 139 (2023) 110-126 | Microsoft Azure Emotion API, frames every 2 s, chair-only frames, 3-min aggregation, negative = anger+disgust+fear scaled by chair's own average | 46 presser videos 2011-Sep 2020; SPY, VIX, EURUSD 1-min | 1 SD more negative emotion -> SPY -0.528 bp in the same 3-min interval; effect dissipates within 5-10 min | Contemporaneous |
| Alexopoulos, Han, Kryvtsov, Zhang, "More than words" (BoC SWP 2022-20; JME 2023) | Azure Video Indexer for face id + Noldus FaceReader (commercial) for AU-based emotions at 29.97 fps; speech AUs (lips, mouth, cheeks) excluded; Q&A rounds with face in <15% of frames dropped (wide angle, head tilted down, side camera) | 32 congressional testimonies 2010-2017 (Bernanke, Yellen) | Higher face/voice/text emotion -> S&P up, VIX down; effects "add up and propagate after the testimony" | Mostly contemporaneous; some post-event drift (testimonies, not pressers) |
| Ng, "Strategic Control of Facial Expressions by the Fed Chair", arXiv 2410.20214 | "facial recognition technology" (tool not identified in abstract) + deepfake experiment | Pressers Apr 2011-Dec 2020 | Negative expressions rise with tenure; chairs do not strategically control expressions | Contemporaneous |
| "Beyond Words: Fed Chairs' facial cues on global stock performance" (CEIBS) | "machine learning" facial sentiment index (tool not stated on page) | 70 pressers 2011-2023, 50 equity markets | Positive facial sentiment raises international stocks | Event-level |

Sources: [V] https://conference.nber.org/conf_papers/f156264/f156264.pdf (SSRN 3782239 draft, text extracted locally); [V] https://ideas.repec.org/a/eee/moneco/v139y2023icp110-126.html (search result); [V] https://www.bankofcanada.ca/wp-content/uploads/2022/05/swp2022-20.pdf; [V] https://arxiv.org/abs/2410.20214; [P] https://www.ceibs.edu/node/27977
Cost context: 0.53 bp per SD per 3 min is about one ES tick at current index levels (1 tick = 0.25 pt). It is contemporaneous, so it is not a tradable edge by itself.

## 2. Model inventory

### 2a. Detection, tracking, identity

| Tool / id | License | Size | Last update | Reported numbers | Windows / GPU |
|---|---|---|---|---|---|
| InsightFace `buffalo_l` pack (SCRFD-10GF detector + ArcFace IResNet-50 trained on WebFace600K, 2d106/3d68 landmarks) via `pip install insightface` (v2.1, 2026-10-03) | Library code MIT; pretrained models non-commercial research only; commercial licensing for buffalo_l via recognition-oss-pack@insightface.ai | pack 326 MB | repo pushed 2026-10-03 | buffalo_l: LFW 99.83, CFP-FP 99.33, AgeDB-30 98.23, IJB-C(E4) 97.25, MR-ALL 91.25; SCRFD-10GF WIDER FACE val 95.16/93.87/83.05 (easy/med/hard), 4.9 ms | pip wheel py3-none-any; 1.0 (2026-05) removed C++ build requirement; ONNX Runtime CUDA |
| RetinaFace: `biubug6/Pytorch_Retinaface` | MIT | R50 29.5M params | 2023-06 | R50 WIDER 94.92/91.90/64.17 (as tabulated by SCRFD authors) | PyTorch, any OS |
| RetinaFace: `serengil/retinaface` (pip `retina-face` 0.0.18, 2026-06) | MIT | - | pushed 2026-10-03 | same weights as original insightface RetinaFace | TF / PyTorch / ONNX backends |
| MediaPipe Face Landmarker (`mediapipe` 1.0.1, 2026-08-14) | Apache-2.0 (models and code) | float16 bundle: BlazeFace short-range 192x192, Face Mesh V2 256x256, Blendshape V2 MLP-Mixer | 2026-08 | 478 3D landmarks, 52 blendshapes, transform matrix. Blendshape V2 card reports only fairness MAD 0.199 (sd 0.237) on 511 lab subjects; no FACS benchmark. Card limits: selfie-style, fails for >80 deg away, <50% visible, far faces; intended for AR | win_amd64 wheel; Python GPU delegate is Ubuntu-only, so CPU on Windows |
| YOLO-face: `akanametov/yolo-face`, `deepcam-cn/yolov5-face`, `derronqi/yolov8-face` | GPL-3.0 (Ultralytics-derived: AGPL-3.0 upstream) | - | 2026-09 / 2024-07 / 2024-10 | not needed: a single large frontal face is easy for any detector | PyTorch |
| PySceneDetect (`scenedetect` 0.7.1, 2026-07) | BSD-3-Clause (repo LICENSE: https://raw.githubusercontent.com/Breakthrough/PySceneDetect/main/LICENSE) | - | 2026-07 | shot boundary detection | pip |

Sources: [V] https://raw.githubusercontent.com/deepinsight/insightface/master/README.md ; [V] https://raw.githubusercontent.com/deepinsight/insightface/master/python-package/docs/model_zoo.md ; [V] https://raw.githubusercontent.com/deepinsight/insightface/master/detection/scrfd/README.md ; [V] https://pypi.org/pypi/insightface/json ; [V] https://github.com/biubug6/Pytorch_Retinaface ; [V] https://github.com/serengil/retinaface ; [V] https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker ; [V] https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Blendshape%20V2.pdf ; [P] https://developers.google.com/edge/api/mediapipe/python/mp/tasks/BaseOptions (GPU Ubuntu-only, via search summary) ; [V] https://pypi.org/pypi/mediapipe/json ; GitHub API metadata in github_meta.txt

### 2b. Action units and multi-task toolkits

| Tool / id | License | Size | Last update | Reported numbers | Windows / GPU |
|---|---|---|---|---|---|
| py-feat 2.1.3 (`cosanlab/py-feat`), `Detectorv2` with HF `py-feat/face_multitask_v2` -> `face_multitask_v28.safetensors` | Code MIT; multitask weights "research-only"; bundled ArcFace weights InsightFace non-commercial | ~30M params, ConvNeXt-V2-Tiny, 224x224 | PyPI 2026-09-07; weights 2026-09-06 | Self-reported, held-out: DISFA+ 12-AU macro-F1 0.682 (common-8 0.772); AffectNet-7 val acc 0.628; RAF-DB 0.869; VA CCC AffectNet 0.773/0.650, Aff-Wild2 0.376/0.477, AFEW-VA 0.687/0.548; gaze 13.04 deg Gaze360, 8.26 deg MPIIGaze. Cross-tool (same authors): DISFA+ common-8 F1 0.774 vs OpenFace 3.0 0.732 vs LibreFace 0.492; AffectNet-7 0.632 vs 0.587 vs 0.458. Known issue: AU20 F1 0.057, AU15 0.479, AU06 0.526; mouth occlusion -0.147 F1 | Python >=3.11, CUDA; pure PyTorch so Windows works [U not tested here] |
| OpenFace 3.0 (`CMU-MultiComp-Lab/OpenFace-3.0`, pip `openface-test` 0.1.26) | CMU academic/non-profit noncommercial research only | 29.4M params; RetinaFace + STAR landmarks + multitask head | repo pushed 2025-06-10 | arXiv 2506.02891 (FG 2025): AU F1 DISFA 59 / BP4D 59 (OpenFace 2.0: 50 / 53); AffectNet-8 acc 0.60 (SOTA 0.65), 58.64% on >45 deg faces; gaze MPII 2.56 deg, Gaze360 10.6 deg; 300W NME 2.87; 38 ms/frame CPU | PyTorch; Windows [U] |
| OpenFace 2.2.0 (`TadasBaltrusaitis/OpenFace`) | Academic noncommercial; commercial via CMU Flintbox | C++ | last push 2024-06; release 2.2.0 | 17 AU intensities + 18 AU presence incl. AU45 blink, head pose (mm, rad), per-eye gaze vectors, confidence/success. Video mode uses dynamic person-specific calibration over the whole video (use `-au_static` when comparing levels across videos or when signal must be causal) | Windows binaries are the primary distribution [P release page assets did not render] |
| LibreFace 2.0 (`ihp-lab/LibreFace`, pip `libreface` 0.2.0 2026-05-21) | USC research licence (educational/research/non-profit; commercial via USC Stevens) | ResNet-18 / RepVGG students, 22.5M (per OpenFace 3.0 paper) | 2026-06-19 | v1 (WACV 2024): DISFA AU-intensity PCC 0.63 vs OpenFace 2.0 0.59; BP4D AU F1 62.0; AffectNet 49.71%, RAF-DB 82.79%; CPU 37 ms full pipeline, GPU 6.07 ms (165 FPS). v2 (FG 2026) adds synthetic data + MediaPipe-landmark gaze; numbers only in figures | Python 3.9 + cmake; .NET NuGet/ONNX; Windows console app (CUDA mandatory) |
| FMAE-IAT (Ning, Salah, Onal Ertugrul, FG 2025, arXiv 2407.11243) | [U] | MAE ViT pretrained on Face9M | - | AU F1 BP4D 67.1, BP4D+ 66.8, DISFA 70.1 (research SOTA, not a toolkit) | [U] |

Sources: [V] https://huggingface.co/py-feat/face_multitask_v2/raw/main/README.md ; [V] https://raw.githubusercontent.com/cosanlab/py-feat/HEAD/README.md and LICENSE ; [V] https://pypi.org/pypi/py-feat/json ; [V] https://py-feat.org/ ; [V] https://raw.githubusercontent.com/CMU-MultiComp-Lab/OpenFace-3.0/HEAD/README.md and LICENSE ; [V] https://arxiv.org/html/2506.02891 ; [V] https://github.com/TadasBaltrusaitis/OpenFace/wiki/Output-Format ; [V] https://github.com/TadasBaltrusaitis/OpenFace/wiki/Action-Units ; [V] Copyright.txt in that repo ; [V] https://raw.githubusercontent.com/ihp-lab/LibreFace/HEAD/README.md and LICENSE.rst ; [V] https://arxiv.org/html/2308.10713 ; [V] https://arxiv.org/abs/2407.11243

### 2c. Expression / valence-arousal

| Tool / id | License | Size | Numbers | Notes |
|---|---|---|---|---|
| EmotiEffLib 1.1.1 (ex-HSEmotion; `sb-ai-lab/EmotiEffLib`, pip `emotiefflib`, `hsemotion` 0.3.0) | Code Apache-2.0 ("no limitation"); weights trained on AffectNet, whose dataset licence is non-commercial research only | enet_b0 16 MB, enet_b2 30 MB | AffectNet-8 / -7 val acc: enet_b0_8_va_mtl 61.93 / 64.94 (also outputs valence, arousal); enet_b2_8 63.03 / 66.29; enet_b2_8_best 63.125 / 66.51; ABAW-8 1st in expression recognition | VA CCC on AffectNet not in README [U]. PyTorch or ONNX, Windows fine |
| POSTER++ / POSTER V2 (`Talented-Q/POSTER_V2`) | MIT | 43.7M params, 8.4 GFLOPs | RAF-DB 92.21, AffectNet-7 67.49, AffectNet-8 63.77 | No VA; checkpoints via Drive; last push 2023-09 |
| POSTER (`zczcwh/POSTER`) | Apache-2.0 | - | superseded by V2 | 2023-08 |
| DAN (`yaoing/DAN`) | MIT | ResNet-18 + attention heads | AffectNet-8 62.09, AffectNet-7 65.69, RAF-DB 89.70 | No VA; 2023-11 |
| EmoNet (`face-analysis/emonet`, Nature MI 2021) | CC BY-NC-ND 4.0 | - | 8-class on "cleaned" AffectNet test: acc 0.75, valence CCC 0.82, arousal CCC 0.75 (different test protocol, not comparable to val-set numbers) | Good VA cross-check; ND licence forbids sharing modified versions |

Sources: [V] https://raw.githubusercontent.com/sb-ai-lab/EmotiEffLib/HEAD/README.md and LICENSE ; [V] https://pypi.org/pypi/emotiefflib/json ; [V] https://raw.githubusercontent.com/Talented-Q/POSTER_V2/HEAD/README.md ; [V] https://raw.githubusercontent.com/yaoing/DAN/HEAD/README.md ; [V] https://raw.githubusercontent.com/face-analysis/emonet/HEAD/README.md ; [P] AffectNet licence: https://studylib.net/doc/27680111/affectnet-agreement-v2-30mar2023 (secondary copy) and https://arxiv.org/abs/1708.03985

### 2d. Head pose, gaze, blinks

| Tool | License | Numbers | Use |
|---|---|---|---|
| 6DRepNet (`thohemp/6DRepNet`, pip `sixdrepnet` 0.1.6) | MIT | trained on 300W-LP: AFLW2000 MAE 3.97 deg, BIWI 3.47 deg | nod/shake velocity, pose gating |
| L2CS-Net (`Ahmednull/L2CS-Net`) | MIT code; Gaze360/MPIIFaceGaze data research-only | MPIIGaze 3.92 deg, Gaze360 10.41 deg (paper abstract). The py-feat re-host card quotes "Gaze360 ~3.92" which conflicts with the paper | coarse "eyes on notes vs on room" only |
| MediaPipe blendshapes eyeBlinkLeft/Right + eye-aspect-ratio from 478 mesh | Apache-2.0 | no published blink accuracy | blink rate; must be gated on head pitch (reading looks like a closed eye) |
| OpenFace 2.2 AU45 | academic | - | independent blink estimate |

Sources: [V] https://arxiv.org/pdf/2202.12555 (Table 1, extracted locally) ; [V] https://arxiv.org/abs/2203.03339 ; [V] https://huggingface.co/py-feat/l2cs/raw/main/README.md

### 2e. Video LLMs (descriptive cross-check only)

| Model | License | Size | Video | Notes |
|---|---|---|---|---|
| `Qwen/Qwen3.8-27B` (already in the local stack as qwen-drafter) | Apache-2.0 | 27.8B | native image+video; vLLM default fps=2 | Video through llama.cpp [U]; vLLM is Linux/WSL |
| `Qwen/Qwen3-VL-8B-Instruct` | Apache-2.0 | 8.8B | native video, timestamp alignment, 256K ctx | transformers on Windows (sdpa) |
| `Qwen/Qwen2.5-VL-7B-Instruct` | Apache-2.0 | 8.3B | Video-MME 65.1/71.6, MVBench 69.6 | older |
| Gemini API (3.x Flash models) | commercial API | - | default 1 fps, custom fps, ~100 tokens/s of video, YouTube URLs accepted (public videos) | cloud; outcome knowledge leakage risk |

Sources: [V] https://huggingface.co/Qwen/Qwen3.8-27B ; [V] https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct ; [V] https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct ; [V] https://ai.google.dev/gemini-api/docs/video-understanding

## 3. Validity limits

1. Emotion labels are not emotions. Barrett et al. 2019 (Psych. Sci. Public Interest 20(1)) find weak reliability and specificity of facial configurations for emotion categories. Use AU intensities, head and eye behaviour and VA as "facial behaviour" features, not "fear/anger". [V search] https://www.psychologicalscience.org/publications/emotional-expressions-reconsidered-challenges-to-inferring-emotion-from-human-facial-movements.html
2. Speech confound. The chair talks for most of the hour; jaw/lip AUs (AU10-AU28) follow phonemes. Image-trained classifiers read open mouths as surprise or fear. Alexopoulos et al. dropped speech AUs for this reason. Keep upper-face AUs (1, 2, 4, 5, 6, 7), smiles only at speech pauses, blinks, head and gaze.
3. Reading from notes. The opening statement is read: pitch down, eyes down, false blinks, AU43 confusion, useless gaze. Treat opening statement and Q&A as separate regimes; drop frames past a pitch threshold.
4. Camera and shot. Cutaways to reporters, wide shots, side cameras, zoom changes. Alexopoulos lost Q&A rounds with face in <15% of frames. Gate on identity, face size (interocular px), |yaw| (MediaPipe card: unusable beyond 80 deg; py-feat bs_to_au trained on |yaw|<=40, |pitch|<=30), blur.
5. Era and lighting domain shifts: SD-era video 2011-2013 [U], virtual pressers 2020-21 (different room, camera, light), chair changes (Bernanke, Yellen, Powell, Warsh). Era and chair fixed effects; luminance and blur covariates.
6. Posed vs spontaneous: AffectNet/RAF-DB are web stills with stronger, often posed expressions; DISFA/BP4D are lab-elicited spontaneous; a media-trained chair shows low-intensity expressions, so argmax will be "neutral" most of the time. Use continuous scores and changes.
7. In-the-wild degradation: py-feat VA CCC falls from 0.77/0.65 (AffectNet) to 0.38/0.48 (Aff-Wild2 video). ABAW-8 baselines on Aff-Wild2: VA CCC 0.24/0.20, AU F1 0.39. https://affective-behavior-analysis-in-the-wild.github.io/8th/
8. Age and appearance: older faces (wrinkles read as AU4/AU9), reading glasses on/off. Per-person baselines remove static offsets, not dynamics.
9. Benchmark comparability: numbers use different splits (AffectNet val vs "cleaned" test; DISFA vs DISFA+; 7 vs 8 classes); the py-feat cross-tool table comes from py-feat's own authors.
10. Whole-video normalization (OpenFace 2 dynamic calibration) and centered smoothing leak future frames; for predictability tests every feature must be causal.
11. Multiple testing: ~94 pressers 2011-2026 (46 through Sep 2020 per Curti-Kazinnik plus ~48 since), dozens of features x windows x assets.
12. Video LLM leakage: a model that knows the date, the chair and the market outcome can project hindsight into "tone". Use only for blind visual labels on muted, undated clips, or on events after the model's training cutoff.

## 4. Baseline design (own-face normalisation)

- Frame -> quality gates (identity cos-sim to enrolled chair embeddings, face height px, |yaw|, |pitch|, blur, luminance, shot id).
- Features per frame: upper AUs, AU12 at pauses, blink events (>=15 fps), head angular velocity (nod/shake), gaze-off proportion, landmark motion energy, VA.
- Nuisance regression per feature on pose, size, luminance, blur, speaking flag (from audio VAD), reading flag, segment, era; fit only on training pressers; keep residuals.
- Two baselines: (a) between-presser: robust z vs the same chair's previous K pressers, same segment, past only; (b) within-presser: deviation from the expanding mean since Q&A start (absorbs day-specific light and camera).
- New chair: hierarchical partial pooling toward a cross-chair prior; optional neutral baseline from other appearances (hearings, interviews), different setting [U usefulness].
- Reliability before markets: inter-tool agreement per feature at 1-10 s aggregation (py-feat vs OpenFace 3.0 vs MediaPipe geometry), split-half reliability within presser, 300-500 hand-labelled frames (AU1/2/4/12 presence, blink, reading, shot type). Drop features below a preset bar.
