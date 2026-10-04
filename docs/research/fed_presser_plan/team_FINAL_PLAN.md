FINAL PLAN — FOMC presser multimodal research (hardened)

Python + uv. Sample specified by the team: 88 meeting videos, 2016 through October 2026 (87 scheduled/equivalent + extra 2–3 Mar 2020). That is 88 policy meetings, not 88 pressers. Q&A analysis is presser=1 only (~75 scheduled pressers through Oct 2026; 74 already held as of 2026-10-03; Oct 28 is in the 88 but has not happened yet). Kevin Warsh has been Chair since 2026-05-22. This document is the hardened plan after Phase 1 research, verification, plan_v0, 10 critic/patch iterations, and a merge of the iteration-1 critic/research agents. Details and URLs live in PHASE1_*.md and VERIFICATION_LOG.md. Holes: hole_register.md.

No AI attribution. No paid download until get_cost is printed and is inside remaining Databento credit.



A. Hardened plan

1. Bottom line

The papers we opened do not show tradable post-answer predictability net of latency and costs.





Gorodnichenko, Pham, Talavera (AER 2023): 36 pressers, 692 answers, 2011–2019. The ~75 bp SPY figure is a daily local projection over several days, not a same-minute fill. Minute-level impact is ~1 bp and imprecise. Do not cite 75 bp as an intraday edge.



Curti & Kazinnik (JME 2023): Azure face; contemporaneous minute-level co-movement. Exact “−0.53 bp / 3-min; dies in 5–10 min” is from discussant slides, not opened JME tables — UNVERIFIED as published coefficients. Azure emotion retired 2023-06-30 (new-user cut 2022-06-21).



Gómez-Cram & Grotteria (JFE 2022): 41 pressers through Jan 2020; 13:50–14:20 predicts the presser window (corr 0.58 medium Eurodollars, 0.44 S&P). Narain & Sangani (IJCB 2026) show that continuation reversed under Powell after COVID. BENCH-R must be split pre-2020 vs 2020–26; do not treat 2011–19 continuation as a 2026 rule.



Shah, Paturi, Chava (ACL 2023): combined F1 ≈ 0.71; presser-only F1 ≈ 0.53–0.55; CC BY-NC 4.0. QQQ story without fees. Hub card opened; a separate “gated weights” banner was not confirmed in the fetched page.



Alexopoulos et al.: testimonies, not pressers; some multi-day persistence — do not import.

strategies/01 daily hawk/dove → TLT is a NO-GO. Date-only speech HTML is not a t=0.

Realistic objects





BENCH-R (nearest to executable): at 14:20 ET the statement-window return is known without video. Hold that sign through presser-end on ZT. Cost with a dollar tick table, not TLT bps: ZT 1/8 of 1/32 = $15.625/contract; ES 0.25 = $12.50. Stress {2, 4} ticks/side (1 tick is a lower bound only). Replication of Gómez-Cram, not new alpha. Pre-register 2011–19 vs 2020–26. If the Powell-era sign flips (Narain–Sangani), report the break; do not average regimes into one Sharpe.



H1-primary (research residual): meeting-level Q&A hawkishness minus same-day statement, frozen FOMC-RoBERTa, ZT, one observation per meeting. Fill on 1m data = next bar open after answer-end τ (OHLC, associational). Position is residualized on 13:50–14:20. 5 s / 15 s / 30 s is not a 1m backtest knob — those delays collapse to the same or adjacent bar. Delay is a live timing measurement. H1-answer (next-open → +1 m / +5 m, then +15 m appendix) is a non-overlapping diagnostic only. Confirmation 2023–2026 Powell only for P&L language.



Weekend hackathon: event list, get_cost, two smoke meetings, write-up. Not an 88-video or ~75-presser multimodal Sharpe.

Voice/face are Powell-only secondaries with kill switches. Warsh: text only. RTX 4050, CUDA not installed: CPU Whisper-turbo default.

2. Pre-registered family (locked)







Id



Spec



Role





H1-primary



Meeting-level mean(hawk(Q&A)) − hawk(statement); Q&A only; ZT; next 1m open after τ; residual position after 13:50–14:20; chair dummy



Only residual GO/NO-GO





H1-answer



Next-open → +1m / +5m (then +15m appendix); non-overlapping; meeting cluster



Diagnostic only





BENCH-R



Sign(13:50–14:20) from 14:20 to presser-end; ZT; {2, 4} ticks/side; split at 2020



Replication / regime check





H1-Q



H1 + question hawkishness



Robustness (collider risk)





H2/H3



vocal_proxy / expression_proxy; prior-meeting same-chair z; Powell only; 4-meeting burn-in; variance floor; identity gate



Secondary; off for Warsh





H4



Combined vs text on 2023–2026 Powell after H1 frozen + code hash



Secondary





Lexicon



Frozen strategies/01 20+20



Negative control

Opening remarks excluded. 2016–2022 RoBERTa scores are classifier-contaminated (ACL data through 2022); confirmation = 2023–2026 Powell. 2022 vs rest and SEP dummy are robustness. Next-day not primary. No LLM in the primary path. No 1s bars without a new user-approved quote. Primary rates name = ZT.c.0. Do not use SR3.c.0 as the Gómez-Cram 60-month Eurodollar analogue (front SR3 is ~one quarter; dated 5th–8th SR3 post-2018 is robustness only). ES window = τ → presser end; 16:00 ET is equity-only robustness. No extra symbols (NQ, FX, GC) unless H1 GO.

3. Stack







Channel



Primary



Cross-check



Notes





Text



gtfintechlab/FOMC-RoBERTa



Moritz-Pfeifer/CentralBankRoBERTa-* (MIT); Loughran-McDonald uncertainty (academic)



CC BY-NC — disclose





Clocks



openai/whisper-large-v3-turbo via faster-whisper, CPU



Fed PDF



PDF = words; ASR = time; drop bad WER-proxy meetings





Diarization



Transcript labels



pyannote 3.1 only if Hub terms accepted



Not required





Vocal_proxy



audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim



parselmouth F0



CC BY-NC-SA; not “emotion of the Chair”





Expression_proxy



MediaPipe + EmotiEffLib @ 1 fps



—



Apache; not Azure; OpenFace not in demo

4. Data and clocks

Statement 14:00 ET, presser ~14:30 ET (2027 FOMC PR). Board site public domain unless marked. C-SPAN is not.

Databento GLBX.MDP3 ohlcv-1m, continuous ZT (primary), ZF/ZN/ES robustness, 13:30–16:30 ET presser days, volume-max expiry check. Unit sheet: OHLCV-1s and 1m both $70/GB historical — 1s is more bytes. Quote get_cost first. Fill = next minute open. Until MBP-1, all 1m results are associational on OHLC, not executable mids.

Record a start-time source per meeting (Bloomberg if available, else first PDF-matching audible open). Drop the meeting from (P) tests if start uncertainty > 30 s.

Fleming & Piazzesi: cash Treasury spreads stay wide 30 min–2 h after FOMC — the presser is still inside the 14:00 stress window. Do not reuse strategies/01 TLT 1.5/5.0 bps. Frozen assumption until MBP-1: {2, 4} ticks/side on the dollar tick table above. No net Sharpe on H1.

5. Pipeline

Board video + transcript PDF
→ CPU turbo word times
→ Q&A segments (Chair only)
→ frozen RoBERTa on statement vs answers
→ optional Powell vocal/expression proxies
→ join ZT **next 1m open after τ**
→ H1-primary + H1-answer diagnostic + BENCH-R (regime-split)

Live path: time Fed/YouTube vs CME on a held presser; freeze delay = max(measured p90, 30 s); 60 s pessimistic appendix. If p90 > 60 s, kill live (G4/G5) and ship measurement-only. Warsh live = half-size text. Offline 1m tests do not retune 5/15/30 s.

6. Evaluation and power

n ≈ 75 presser meetings inside the 88-meeting archive, not 2,000 iid answers and not n=88. Underpowered for small H2/H3. Block bootstrap + wild cluster. Holm not needed for a single primary; secondaries cannot be promoted after looking.

Report (A) BENCH-R costed and (B) H1 non-executable separately.

7. Gates and calendar







Gate



Go



No-go





G0



CPU ASR + RoBERTa on one Powell and 2026-09-16 Warsh



No video/ASR





G1



get_cost under credit



Shrink window/symbols; ask before 1s





G2



Event list; missingness vs VIX table



Crisis MNAR + imputed video





G3



H1-primary on confirmation sample



Stop; do not mine H2





G4



H2/H3 variance/identity gates on Powell



Ship text-only





G5



Paper-trade text, half-size on Warsh, only if live p90 delay ≤ 60 s



Kill live; measurement-only

Remaining pressers: 2026-10-28, 2026-12-09; 2027-01-27, 03-17, 04-28, 06-09, 07-28, 09-15, 10-27, 12-08.

8. Licenses and ethics

Disclose CC BY-NC (FOMC-RoBERTa, audeering). Loughran academic. pyannote gated. OpenFace/LibreFace research-only — not the public demo. Do not claim to read Warsh’s feelings. Features are proxies.

9. Budget

$0 APIs. Databento 1m presser windows only after quote. Laptop CPU path must work without the shared 5-GPU cluster.



B. Hole register (full)

See [hole_register.md](hole_register.md) for every id, patch, and residual. Counts below.



C. Convergence (new critical+high holes per iteration)







Iteration



New critical



New high



New C+H



Note





1



4



6



10



iid answers, test explosion, Warsh n, mids, 14:00 steal, 88 meetings vs ~75 pressers, CUDA, ASR/PDF, NC license, in-sample RoBERTa, opening/questions/reverse causality





2



2



5



7



H4 peeking; SEP; rolls; close clock; COVID face; FEDS horizon





3



1



4



5



burn-in z; SR3 panel; LLM lore; text-only GO





4



1



3



4



BENCH-R still not HFT-safe (patch: 14:20, no ASR); unscheduled; identity





5



0



3



3



hash freeze; missingness MNAR; collider





6



0



2



2



Warsh H2/H3 off; forbid 1s





7



0



2



2



meeting-level H1; alignment drop rule; continuation vs reversal





8



0



1



1



48h vs two-week scope; two reported Sharpes





9



0



1



1



explicit underpower; no Warsh voice claim





10



0



1



1



lock delay at 30 s (no retune)

Yield fell; all 10 iterations still ran. Residual criticals from iter 1 remain structurally true (small n, contemporaneous literature, Warsh) even after patches — that is what “residual risk” means.



D. Top 5 residual risks





Absorption vs 1-minute bars. Literature co-moves during the answer. Next-open after τ is already 1–4 minutes after speech onset. 5/15/30 s cannot be identified on ohlcv-1m. If (P) next-open dies and same-minute (C) lives, publish no-trade.



Statement continuation vs reversal. Gómez-Cram continuation is 2011–Jan 2020. Narain–Sangani: Powell post-COVID reversal. H1 may be zero once 14:00 is residualized; BENCH-R may be the only costed object, and its sign is not a 2016–2026 constant.



Chair change. Warsh n=3 held (4th in-window is Oct 28); voice/face off; even text H1 is a domain shift. Oct 28 / Dec 9 paper-trades can fail for that reason alone.



Licenses vs sponsors. FOMC-RoBERTa and audeering are non-commercial. Demo-legal fallback is MIT CentralBankRoBERTa + frozen lexicon, which is a weaker FOMC stance model.



Unmeasured costs and live delay. No billed get_cost; no 4050/YouTube timing; no 2024–2026 FOMC futures bid-ask. {2, 4} ticks/side is an assumption, not a measurement.



E. First two weeks — one-page checklist

Days 1–2 (hackathon weekend)





uv project, CPU torch, ffmpeg, faster-whisper turbo



Event spreadsheet: 2016–2026 meetings, presser flag, chair, URLs, missing video



Smoke Powell presser + 2026-09-16 Warsh: PDF + video, ASR clocks, RoBERTa surprise table vs that day’s statement



Print Databento get_cost for 1m ZT/ZF/ZN/ES, 13:30–16:30 ET, presser days (no download if over credit)



Write-up pages: H1 vs BENCH-R, 88 meetings vs ~75 pressers, Warsh rule, CC BY-NC, “mids ≠ fills”



Do not expand the lexicon, call 1s, or report a multimodal Sharpe

Days 3–7





Download 1m windows if quote OK



Align all available presser PDFs; drop high-mismatch meetings



Freeze code hash; run H1-primary on 2016–2022 (contaminated) and 2023–2026 Powell



BENCH-R with {2, 4} ticks/side (not TLT bps)



Missingness vs year/VIX



Optional: Powell vocal_proxy variance floor check (kill or keep H2)

Days 8–14





H1-Q robustness; 2022 split; SEP dummy — no new primaries



H3 only if identity gate works; else skip



Paper-trade protocol for 2026-10-28 and 2026-12-09: text surprise, half-size, timed delay, ZT; kill live if p90 delay > 60 s



Pin uv.lock; archive model hashes



If H1 dies: submit measurement + BENCH-R replication, not a fished Sharpe

Do not do in two weeks: Qwen-Omni on 88 videos; pyannote if ungated terms unsigned; OpenFace demo; 1s bars; Warsh face/voice trading; reviving daily TLT lexicon.