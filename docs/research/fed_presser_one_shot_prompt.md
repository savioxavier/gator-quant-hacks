ultracode — use a multi-agent workflow for this.

GOAL
Build a robust, research-backed plan to find a trading edge from Federal Reserve press conferences (the FOMC chair's press conference at 14:30 ET after the 14:00 ET statement; 8 meetings a year; pressers every meeting since 2019, quarterly 2011-2018). Signals come from three channels in the recordings: the chair's FACIAL EXPRESSIONS, VOICE TONE, and WORD CHOICE. Then stress-test the plan through 10 red-team-and-patch iterations and deliver the final hardened plan.

MY SETUP
- Windows 11 PC, RTX 5090 (32 GB) + RTX 5080 (16 GB), Python. Everything should run locally where possible.
- Databento API key in .env (CME futures; 1-second/1-minute bars and ticks available).
- Never pull paid data without asking me first. Use the free metadata.get_cost to price pulls.

PHASE 1 — RESEARCH (parallel agents, cite a URL for every claim, mark anything unopened as unverified)
1. Evidence: Curti & Kazinnik "Let's Face It" (facial expressions in FOMC pressers); Gorodnichenko, Pham & Talavera "The Voice of Monetary Policy" (AER 2023); Alexopoulos et al. "More than words" (testimonies: text + voice + face); Shah, Paturi & Chava "Trillion Dollar Words" (ACL 2023); Gómez-Cram & Grotteria (real-time price discovery while the chair speaks); press-conference information effects; any 2024-2026 multimodal or LLM work on Powell. For each: sample, method, effect size, horizon, and whether the effect is CONTEMPORANEOUS (the market moves while he speaks) or PREDICTIVE (a signal at time t predicts returns after t, net of costs and latency). State how fast prices absorb the information.
2. Voice models:
   - ASR with word timestamps: Whisper large-v3/turbo, WhisperX, faster-whisper, Parakeet/Canary.
   - Diarization: pyannote 3.x (note gated licenses), NeMo.
   - Speech emotion: dimensional arousal/valence/dominance (e.g. audeering wav2vec2 MSP-dim), emotion2vec+, WavLM/HuBERT fine-tunes.
   - Prosody: openSMILE eGeMAPS, parselmouth.
   - Audio LLMs: Qwen2.5-Omni etc.
   Give exact model ids, licenses, benchmark numbers (MSP-Podcast/IEMOCAP), GPU needs and Windows support.
3. Face models:
   - Detection and tracking: RetinaFace/SCRFD, MediaPipe with blendshapes.
   - Identity filter: ArcFace.
   - Action units: OpenFace 2/3, LibreFace, py-feat.
   - Expression and valence/arousal: HSEmotion/EmotiEffLib, POSTER++.
   - Head pose, gaze, blinks; video LLMs as a cross-check.
   Note that Azure Face emotion, used by earlier Fed work, was retired in 2022. Give licenses (research-only vs commercial), benchmarks (AffectNet, DISFA/BP4D), and validity limits.
4. NLP:
   - FOMC-specific classifiers: gtfintechlab FOMC-RoBERTa, CentralBankRoBERTa, FinBERT variants.
   - Rubric-based LLM scoring, run locally.
   - Dictionaries: Loughran-McDonald uncertainty, hawkish/dovish lexicons.
   - Novelty vs the written statement and vs prior pressers; stance by topic; evasiveness.
   Explain how to avoid look-ahead from LLMs trained on post-meeting commentary.
5. Data and markets:
   - Every presser's video and transcript for 2011-2026 (federalreserve.gov, YouTube, C-SPAN; US government works).
   - Exact start times; aligning video time to market time to the second (broadcast delay).
   - Presser count per chair.
   - Instruments: ES, NQ, ZT, ZF, ZN, SR3, 6E, 6J, GC.
   - Price 1-second and 1-minute bars for the 13:30-16:30 ET windows on presser days via get_cost.
   - Realistic latency for a student pipeline; spreads during FOMC.
6. Existing projects and datasets on GitHub, Hugging Face and Kaggle (FOMC transcripts, Fed speech corpora, earnings-call vocal-cue work such as MAEC), with reusable parts and licenses.
Then an adversarial verifier re-checks every paper, model id, license and number, marking each confirmed, corrected, refuted or unverifiable.

PHASE 2 — PLAN v0 (Markdown, about 2,000 words)
1. Bottom line: what is realistic.
2. Pre-registered hypotheses: few and specific, e.g. text hawkishness surprise during Q&A → ZT/SR3 and ES returns over the next N minutes and into the close; vocal arousal / negative valence vs his OWN baseline; facial negative affect; combined vs text-only.
3. Model stack table: primary and cross-check model per channel, features, per-speaker normalisation.
4. Data plan: event list, sources, market data and cost, time alignment.
5. Pipeline: offline first, then real-time. Ingest → diarize → ASR → segment answers → features → per-answer and per-30-60s aggregates → signals.
6. Evaluation:
   - Targets after each segment end, from presser end to the close, and next day.
   - Leave-one-meeting-out and expanding windows; block bootstrap by meeting; multiple-testing control.
   - Costs and latency assumptions.
   - Benchmarks: the statement surprise and the 14:00-14:30 move.
   - Power analysis for about 110 pressers and about 2,000 answers.
7. Staged roadmap with go/no-go gates, ending in forward paper-trading on the next live meetings (list the remaining 2026 and the 2027 FOMC dates).
8. Risks and mitigations, including a CHAIR CHANGE (Powell's term as chair ended May 2026: check who gives the pressers now and how per-speaker baselines transfer), ethics and licensing.
9. Budget, and what to do on day one.

PHASE 3 — 10 RED-TEAM / PATCH ITERATIONS (sequential; each iteration runs 5 critics in parallel, then 1 patcher)
Critic lenses, one agent each, every iteration:
  (1) statistics and overfitting: sample size, leakage, multiple testing, test design, power;
  (2) market microstructure and execution: broadcast delay, latency, FOMC spreads and slippage, whether prices absorb the signal before we can act, instrument choice;
  (3) data and engineering: alignment to the second, diarization and ASR errors, camera cuts and occlusion, missing videos, reproducibility, real-time reliability;
  (4) model validity: emotion-model validity on a Fed chair, domain shift, baselines, chair change, LLM look-ahead, label noise, licenses;
  (5) economic logic and confounds: is it just the statement surprise; reporters' questions driving his tone; reverse causality (the market move causing the tone); information already in the transcript.
Critics receive the current plan plus the full HOLE REGISTER so far. They must find NEW holes or show an earlier patch is inadequate. Each hole gets: id, title, severity (critical/high/medium/low), evidence, suggested patch.
The patcher revises the plan to fix every new critical and high hole (and medium ones where cheap), and may run quick checks (cost queries, model-card lookups). It updates the HOLE REGISTER table (id, hole, severity, patch, residual risk, iteration found and patched) and saves plan_v{i}.md.
Log per iteration: holes found by severity and holes patched. All 10 iterations run even if few new holes appear.

PHASE 4 — FINAL
Consolidate into FINAL_PLAN.md: the hardened plan, the full hole register, a convergence table (critical/high holes found per iteration), the top 5 residual risks, and a one-page "first two weeks" checklist.

OUTPUT FILES (in a new folder, e.g. ./fed_presser_plan/)
- research notes with URLs
- verification log
- plan_v0..plan_v10.md
- FINAL_PLAN.md

RULES
- Cite sources and give exact model ids.
- Never claim a paper shows tradable predictability unless it does.
- No paid data or API spend without asking me first.
- Respect model licenses.
- Do not copy long text or code from papers or repositories.
- No AI attribution in any file or commit.
