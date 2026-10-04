# verify_literature: adversarial check of literature / data_markets / projects claims (2026-10-03)

Method: opened each paper (local PDF text from the URLs in the claims, plus RePEc/AEA/Crossref/IJCB pages),
reran Databento get_cost (free, no data), re-queried the HF API, Brightcove playback API, Kaggle API, the
Fed transcripts and USMPD.xlsx. GitHub API was rate limited; raw.githubusercontent used instead.

## Corrections found
1. Gomez-Cram & Grotteria "prices absorb spoken info within ~1 minute": the paper says only that, heuristically,
   one-minute aggregation is adequate to capture the response to words (p.21-22, fn 17). It is a data
   aggregation choice, not a measured absorption speed. Their headline result is the opposite of fast
   absorption: statement news keeps being priced through the presser (slow belief aggregation).
   Source: https://lbsresearch.london.edu/id/eprint/2203/1/SSRN-id3613702.pdf
2. Curti & Kazinnik: 2,518 observations are minute-level rows with OVERLAPPING 3-minute windows (signal = prior
   3 min, return = next 3 min), not 2,518 non-overlapping 3-minute blocks. Overlap plus 3 chair clusters
   makes the p-values fragile. https://conference.nber.org/conf_papers/f156264/f156264.pdf (Sec 3, eq. 2)
3. Azure emotion: new customers cut 2022-06-21; EXISTING customers kept access until 2023-06-30 (projects note
   said "by end-2022"). https://learn.microsoft.com/javascript/api/overview/azure/cognitiveservices-face-readme
4. Neuhierl-Weber: the momentum starts up to 25 days BEFORE expansionary shocks; post-announcement leg is a
   15-day short after contractionary shocks. 4.5% spread and Sharpe 0.31 -> 0.46 confirmed (digest only).
   https://nber.org/digest/sep18/w24748.shtml
5. USMPD rule replication (own rerun on USMPD.xlsx): split by calendar year gives n=40/53 (agent had 41/52),
   SPFUT corr +0.459 (t 1.97, hit 62%) vs -0.071 (t -0.03, hit 49%). Same conclusion.
6. FOMC-RoBERTa is gated: manual approval (HF API gated='manual') - literature item omitted this.
7. Databento: my 4-day rerun reproduces the agent's per-day costs to the cent (2013-06-19 $0.1011,
   2025-09-17 $0.1014 incl SR3); extrapolating only my 4 days x95 gives $9.80 vs agent's full-list $8.60
   (sample days are busier than the median). bbo-1s ES/ZN/ZT ~$0.040/day -> ~$3.8.

## Confirmed (key numbers re-read in the source)
- C&K JME 139(C) 2023 110-126; 46 pressers (12/16/18); Azure 8 classes; 2-s frames; -0.528 bp SPY (=1.060 x -0.499),
  VIX +3.73, EURUSD -0.184; 5-min -0.711 (p .000), 10-min -0.438 (p .067); chair clustering; dissipates 5-10 min.
- GPT AER 113(2) Feb 2023 548-84; 68 meetings/36 pressers/692 answers; RAVDESS+TESS 84%; BERT 81%; ~100 bp per unit
  tone after ~5 days (~75 bp per SD), 10% sig; intraday ~1 bp on impact, nothing in next minute; 90% BCa CIs.
  Replication sheet QA_identifier: 692 rows, 36 dates (downloaded myself).
- Alexopoulos et al. (BoC SWP 2022-20; JME 142 2024 per search): 32 testimonies, C-SPAN, Praat F0, Azure Video
  Indexer + FaceReader 29.97 fps, Happy excluded; 1/2/5 bp S&P; VIX -3/-12 bp; 90/60 bp within 1-2 weeks,
  "not always statistically significant"; face ~0 at daily.
- GCG JFE 143(3) 2022 993-1025; 41 pressers; 54m47s; 58%/44%; Table 4: stocks 12.66 bp [2.30], FX 8.14 [2.57],
  ED 1.16/1.02; no transaction costs in text; video lags audio ~3 s; 7.5% statement minutes.
  Their Table 1 time 14:36:34.096 = Fed VTT cue 06:34.096 + 14:30:00 (checked).
- Narain & Sangani IJCB 22(1) Jan 2026 pp 313-389; 73 scheduled pressers to 2024-03-20; >3x volatility; opposite moves post-COVID.
- Byun-Fees-Jacobson-Walker Jul 2026: slope insignificant under Powell 2018-2025; DeBERTa used.
- USMPD WP 2025-30 (Aug 2026): PC 4.1 vs STMT 3.5 bp post-liftoff; 1.6 vs 2.0 before; corr -0.27 (Mar 2022-2024),
  +0.23 (Apr 2011-Jan 2022), +0.44 (2015-19), -0.14 (Apr 2011-2024); 2.8 vs 1.1 bp at 81 vs 35 meetings.
- TDW arXiv 2305.07972, "Accepted ... ACL 2023 (main)"; RoBERTa-large PC 0.5517 (combined-trained) / 0.5346 (split-trained);
  overall 0.7171/0.7113; QQQ 673.29% vs 509.89%. HF: cc-by-nc-4.0, 1,421,588,461 B, lastModified 2023-09-12, 1,382 dl.
- Lucca-Moench: 49 bp, ~80%, Sharpe 1.14, none in Treasuries. Kurov-Wolfe-Gilbert FRL 40 2021: "essentially disappeared after 2015".
- Schmeling-Wagner JFQA 60(1) 2025 36-67; 241 ECB pressers. Ehrmann-Fratzscher IJCB 2009: PCs larger effect, lower volatility.
- Bauer-Wasserburger SF Fed EL 2026-03-31: 87 pressers, 10 bp hawkish -> ~6 bp lower inflation compensation.
- Chordia-Green-Kottimukkalur RFS 31(12) 2018: 5 ms, >100x, $19k/$50k. Rosa EL 138 2016: depth ~20% pre-release.
- Machacek et al. arXiv 2307.14743: 3.3 s latency.
- JRFM 19(8) 2026 (Crossref abstract): 84 pressers, Gemini 2.5 Flash, 11,156 segments, hesitations/speech rate r<=0.92 vs Praat,
  firmness/emotion lack acoustic grounding. Descriptive, no market test in the abstract.
- Ng arXiv 2410.20214: DeepFace + deepfakes, Apr 2011-Dec 2020, chairs do not strategically control expressions.
- Anastasiou et al. CEPR DP20308 (30 May 2025): voice sentiment and bank crash risk.
- Warsh: Fed Board page lists Warsh Chairman, Powell Governor (updated 2026-05-28); transcripts 2026-06-17/07-29/09-16 headed
  "Chairman Warsh's Press Conference", 2026-04-29 "Chair Powell's"; 9/16 hike to 3-3/4 to 4%. Sworn in 2026-05-22 (local-TV
  syndication via search only). Fewer pressers / no forward guidance / communications task force: news via search only.
- Counts: USMPD 95 pressers, by year 3,5,4,4,4,4,4,4,8,9,8,8,8,8,8,6; times 85x14:30, 8x14:15, 11:00, 18:30.
- Times: 2011-03-24 release: statement ~12:30, briefing 14:15; 2013-03-13 release: 14:00 statement, ~14:30 presser.
- Video: Brightcove playback API for 2026-09-16 (id 6405157968112): 1722.5 s, MP4 960x540 1.824 Mbit/s, en captions track.
  Fed disclaimer: public domain, cite the Board.
- FOMCBench card: 2,154 pairs, 89 pressers 2011-2025, three chairs, kappa 0.859/0.676, CC-BY-4.0.
- Kaggle davidgauthier/fomc-conferences: Apache 2.0, 12.9e9 bytes, 45 downloads, updated 2022-11-06.
- LucasKSJang README: r=0.42 p=.020, placebo 0.45, 0.25->0.02 p=.62, max-T p .27, bitrate 32%, MIT.
- Power: MDE r 0.287 at n=93 (Fisher z), SR/event 0.207 for t=2, 100 events for SR 0.2 (arithmetic rechecked).

## Unverifiable here
- "Hawkish by Voice" SSRN 7367160 (403, not found by search). Boguth et al. JFQA only abstract-level.
- Broker fees, CME tick specs pages, C-SPAN policy, Brightcove live latency.
- Own ES pre-FOMC result (internal).
