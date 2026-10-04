# verify_models - adversarial check of voice/face/NLP model claims (2026-10-03)

Raw evidence in this folder: hf_meta.json (HF API metadata for 66 ids), cards/ (model cards), gh/ (GitHub READMEs/licences),
oal_short.csv + oal_long.csv (Open ASR leaderboard data repos, fetched today), wagner.txt, tdw.txt, vox.txt, 6d.txt, yao.html.

## All 66 HF ids resolve. Corrections / flags
- nyrahealth/CrisperWhisper -> redirects to nyralabs/CrisperWhisper (renamed). v1 card: superseded, "no longer actively maintained". https://huggingface.co/nyralabs/CrisperWhisper
- nyralabs/CrisperWhisper2.0_large licence = "nyra-health-non-commercial-research" (not just "other"). https://huggingface.co/nyralabs/CrisperWhisper2.0_large
- pyannote/speaker-diarization-precision-2 -> redirects to pyannote/speaker-diarization-precision; pyannote README says precision-2 also has a (premium) self-hosted version. https://github.com/pyannote/pyannote-audio
- pyannote 3.1 DER in README table: VoxConverse 11.2, AMI-IHM 18.8, DIHARD3 21.4 (voice detail text said 11.3/21.7; 3.1 card gated, not readable).
- whisperX issue #1211: error shown is a missing cudnn_ops_infer64_8.dll, not CUBLAS_STATUS_NOT_SUPPORTED; issue closed, fixed by PR #1182 (newer deps). https://github.com/m-bain/whisperX/issues/1211
- NeMo README: Python 3.12+ / PyTorch 2.7+, but PyPI requires_python >=3.10. Linux-first confirmed (uv, source .venv/bin/activate).
- py-feat/l2cs card says Gaze360 ~3.92 / MPIIFaceGaze ~4.16; paper abstract: MPIIGaze 3.92, Gaze360 10.41 -> card mislabelled (face agent was right).
- gtfintechlab/model_federal_reserve_system_stance_label: card says roberta-base, safetensors 355,363,844 params (roberta-large size); card code loads from dataset id. Confirmed.
- gtfintechlab/fomc_communication columns: index, sentence, year, label, orig_index -> no document-type field, so the press-conference subset cannot be isolated from the HF copy.
- hsemotion PyPI last release 0.3.0 on 2022-12-17 (stale); use emotiefflib 1.1.1 (2025-09-10).
- OpenFace-3.0 repo last push 2025-06-10; pip name is openface-test 0.1.26 (2025-06-11).
- Yao et al. (arXiv 2508.08001): 0.7327 combined / 0.6672 PC / GPT-4.1 0.6662 / Qwen3-14B zero-shot 0.5135 confirmed in Table 1; "AAAI-26" not stated on arXiv HTML (unverified).
- ProsusAI/finbert and yiyanghkust/finbert-tone have no licence on HF card; GitHub LICENSE files are Apache-2.0.

## Confirmed numbers (selection)
- OAL short avg: Qwen3-ASR-1.7B-hf 4.31, canary-qwen 4.43, parakeet-v2 4.70, v3 4.86, canary-1b-v2 5.71, whisper-v3 5.78, turbo 6.36, Voxtral-Mini 5.54.
- OAL long-form earnings21/22: whisper-v3 9.71/13.16, turbo 9.84/13.10, parakeet-v2 10.75/13.25, v3 9.96/14.58, canary-qwen 9.60/13.59, cohere-transcribe 8.70/12.66.
- Qwen3-ForcedAligner AAS (ms) English raw: NFA 107.5, WhisperX 92.1, Qwen 37.5; Concat-300s: 226.7, 227.2, 58.6.
- pyannote README (3.1/community-1/precision-2): AMI-IHM 18.8/17.0/12.9; DIHARD3 21.4/20.2/14.7; VoxConverse 11.2/11.2/8.5; community-1 31 s per hour on H100.
- Wagner et al.: arousal/dominance .745/.634 MSP, .663/.518 IEMOCAP; valence .638 (abstract), .448 IEMOCAP.
- MSP IS2025: attribute SAIL .6076 (V .6829, A .642, D .498), baseline .5797; categorical NTUA .4316, baseline .3293.
- 3loi: Test3 V/D/A .577/.577/.405; Dev .652/.688/.579.  ECAPA EER 0.80.  Vox-Profile Table 4 consistent with claim (layout-extracted).
- Step-Audio-2-mini paralinguistic avg 80.00 (GPT-4o Audio 43.45, Kimi 49.64, Qwen-Omni 44.18). SpeechParaling-Bench 43.3%.
- Qwen2.5-Omni-7B MELD .570, BF16 15 s video 31.11 GB; Qwen3-Omni BF16 78.85 GB, MMAU 77.5, MMSU 69.0; GGUF Q4_K_M 18.56 GB, mmproj Q8_0 1.33 GB.
- py-feat multitask_v2 card: all quoted numbers match; default weights face_multitask_v28.safetensors present.
- OpenFace 3.0 paper; LibreFace paper (PCC .63 vs .59, BP4D 62.0, AffectNet 49.71, RAF 82.79, GPU 6.07 ms); EmotiEffLib table; POSTER V2; DAN; EmoNet (CC BY-NC-ND); buffalo_l; SCRFD; 6DRepNet 3.97/3.47 - all match.
- TDW Table: RoBERTa-large 0.7171 comb / 0.5517 PC etc.; 315 PC sentences (322 split); look-ahead 0.7114. WCB Fed stance 0.749/0.747/0.584/0.599. FLaME FOMC numbers match.
- CentralBankRoBERTa 0.88/0.93; Eva-4B-V2 84.9; Qwen3-Embedding-8B 70.58 (2025-06-05); FinBERT-FOMC-aspects acc 0.8790 / macro-F1 0.7981; FinBERT-FOMC 88.3 vs 84.0; ChronoBERT 26 checkpoints 1999-2024, ChronoGPT ~1.55B ctx 1,792.
