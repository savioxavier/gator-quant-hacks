# data_markets: data, timing and market logistics for FOMC press-conference analysis

Working notes, 2026-10-03. Every claim carries a URL; "UNVERIFIED" marks anything not opened or not confirmed.
Local evidence files are in this folder (scripts/, *.csv, pdf/, vtt/, usmpd/, lit/).

## 0. Headline facts that change the plan

* The chair is no longer Jerome Powell. The Board page lists Kevin Warsh as Chairman and Jerome H. Powell as Governor
  (https://www.federalreserve.gov/aboutthefed/bios/board/default.htm, page updated 2026-05-28). Swearing-in reported
  2026-05-22 (news only: https://seekingalpha.com/news/4596371-kevin-warsh-is-sworn-in-as-federal-reserve-chair
  returned 403, so the date is UNVERIFIED from a primary source). Official transcripts confirm "Chairman Warsh's Press
  Conference" on 2026-06-17, 2026-07-29 and 2026-09-16
  (https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20260916.pdf). Last Powell presser as chair: 2026-04-29.
  Remaining 2026 meetings: Oct 27-28 and Dec 8-9 (https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm).
* Sample size is 95 press conferences (2011-04-27 to 2026-09-16), not ~110. By end-2026: 97.
* All 95 have an official video on federalreserve.gov (Brightcove) and 83 have official WebVTT captions that are a
  forced alignment of the transcript, including speaker labels. That gives in-video timestamps for every answer free of
  charge (no ASR needed for history), but NOT wall-clock time.
* The best-known second-level paper (Gomez-Cram and Grotteria, JFE 2022) has timestamps that equal the official caption
  cue times plus exactly 14:30:00 (their Table 1, July 31 2019, "14:36:34.096" vs caption cue "06:34.096"). So the
  literature effectively assumes video time zero = scheduled start. Wall-clock alignment error is unknown.
* The published intraday regularity (statement-window move predicts press-conference-window move) replicates in
  2011-2019 on the free SF Fed USMPD but is zero in 2020-2026 (section 4).

## 1. Recordings and transcripts

Pages and files (all from the Board; public domain "unless otherwise indicated", attribution requested,
https://www.federalreserve.gov/disclaimer.htm):
* Presser page: https://www.federalreserve.gov/monetarypolicy/fomcpresconfYYYYMMDD.htm (Jan 2026 uses the typo
  `fomcpressconf20260128.htm`). Listing pages: fomccalendars.htm (2021+) and fomchistoricalYYYY.htm (2011-2020).
* Transcript PDF: https://www.federalreserve.gov/mediacenter/files/FOMCpresconfYYYYMMDD.pdf (all 95 downloaded, 200 OK).
* Video: Brightcove account 66043936001 embedded on each page; the player's public playback API returns MP4
  (H.264; 960x540 at ~1.8 Mbit/s for 2012-12 onward mostly, some 640x360, 720x404 in 2011, 1280x720 once), HLS and
  DASH, plus a WebVTT caption track. Metadata for all 95 in video_meta.csv (no media downloaded).
  Total 82.4 hours, mean 52 min; 2026 mean 44 min; the 2026-09-16 Warsh presser is 28.7 min.
* Captions: 83/95 have captions (missing: 20110427, 20111102, 20120125, 20120620, 20131218, 20221214, 20230614,
  20230726, 20231101, 20231213, 20240320, 20251210). 82 have >=10 chair speaker-label cues (vtt_summary.csv).
  Greeting ("Good afternoon/day") occurs 0.6-144 s into the video, median 11.8 s.
* YouTube (channel id UCAzhpt9DmG6PnHXjmJTvRGQ, RSS https://www.youtube.com/feeds/videos.xml?user=FedReserveBoard):
  presser videos are uploaded after the event ("isLiveContent": false; 2026-09-16 upload 15:40 ET, 1722 s, same as
  Brightcove). So YouTube's liveStreamingDetails.actualStartTime cannot anchor them. YouTube ToS restricts downloading;
  use the federalreserve.gov copies.
* Live: https://www.federalreserve.gov/live-broadcast.htm (Brightcove player). Live latency UNVERIFIED (measure it).
* C-SPAN: carries the pressers; its policy allows non-commercial copying/sharing of coverage of federal government events
  with attribution and forbids unlicensed commercial use (secondary sources:
  https://www.tvtechnology.com/news/cspan-expands-access-to-video-content ; c-span.org returned 403, UNVERIFIED there).

## 2. Counts per chair and segments (transcript parse, scripts/count_segments.py, presser_segments.csv)

| Chair | Pressers | Dates | Chair answer turns | >=40 words | Mean opening words |
|---|---|---|---|---|---|
| Bernanke | 12 | 2011-04-27..2013-12-18 | 288 | 265 | 1,462 |
| Yellen | 16 | 2014-03-19..2017-12-13 | 317 | 285 | 1,567 |
| Powell | 64 | 2018-03-21..2026-04-29 | 1,797 | 1,619 | 1,163 |
| Warsh | 3 | 2026-06-17..2026-09-16 | 62 | 57 | 945 |
| Total | 95 | | 2,464 | 2,226 | |

Turns include short follow-ups; parse is regex-based (all-caps speaker labels) and approximate.
Per year: 3,5,4,4,4,4,4,4 (2011-2018), 8 (2019), 9 (2020 incl. 2 unscheduled), 8 each 2021-2025, 6 so far in 2026.
Literature cross-checks: 41 pressers 2011-2020, mean 54m47s, opening 10m17s, ~23 questions (Gomez-Cram and Grotteria,
https://lbsresearch.london.edu/id/eprint/2203/1/SSRN-id3613702.pdf); 692 answers in 36 pressers, 12-26 per presser,
mean 19 (Gorodnichenko, Pham, Talavera, https://eml.berkeley.edu/~ygorodni/VoiceMP.pdf).

## 3. Times and alignment

* 2011-04-27..2012-12-12 (8 pressers): statement ~12:30 ET, presser 14:15 ET
  (https://www.federalreserve.gov/newsevents/pressreleases/monetary20110324a.htm).
* From 2013-03-20: statement 14:00 ET, presser "approximately 2:30 p.m."
  (https://www.federalreserve.gov/newsevents/pressreleases/monetary20130313a.htm).
* Unscheduled: 2020-03-03 presser 11:00 ET; 2020-03-15 (Sunday) 18:30 ET (USMPD timestamps).
* USMPD press-conference timestamps are the scheduled minute (85 x 14:30, 8 x 14:15, 11:00, 18:30).
* Brightcove `created_at` is an upload time (median 15.8 min after scheduled start; same-day IQR 8.8-24.0 min), the
  VOD HLS has no EXT-X-PROGRAM-DATE-TIME tags, YouTube copies are not live archives. No official second-level
  wall-clock anchor exists for history.
* Gomez-Cram and Grotteria: "align the beginning and the end of the press conference with the times published by
  Bloomberg"; video feed lags audio by about 3 s (footnote 17). Their Table 1 equals VTT + 14:30:00.

## 4. Market reaction (free USMPD; scripts/usmpd_baseline.py)

USMPD: https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/
(xlsx https://www.frbsf.org/wp-content/uploads/USMPD.xlsx, last update 2026-09-17; paper
https://www.frbsf.org/wp-content/uploads/wp2025-30.pdf). Windows: statement -10/+20 min; presser -10/+60 min from
presser start; tick data from LSEG. Assets: FF1-6, ED1-8 (SOFR later), OIS1Y/2Y, UST 3M-30Y, TIPS, SP500, SPFUT,
DXY, EURUSD, USDJPY. 95 pressers, identical dates to ours.

Std of window moves (scheduled pressers): SPFUT statement 0.43% / presser 0.49% (2011-18) vs 0.41% / 0.78% (2019-26);
UST2Y 4.0 / 2.3 bp vs 4.8 / 5.7 bp; UST10Y 4.2 / 2.9 bp vs 2.5 / 3.6 bp.

Statement-sign baseline (long if statement-window move > 0, held over presser window):
* 2011-2019 (n=41): SPFUT corr +0.46, mean +0.127%, t=1.86, hit 61%; SP500 corr +0.51, t=2.05.
* 2020-2026 (n=52): SPFUT corr -0.07, mean +0.001%, t=0.01, hit 50%; UST2Y corr -0.06; USDJPY corr -0.20.

## 5. Databento costs (free metadata.get_cost; no data pulled) -- see section appended below

## 6. Absorption speed, latency, costs

* Macro releases: SPY/ES respond within 5 ms (Chordia, Green, Kottimukkalur 2018 RFS,
  https://ideas.repec.org/a/oup/rfinst/v31y2018i12p4650-4687..html).
* Treasury market: near-instant price jump, spreads widen at release then a prolonged high-volume stage (Fleming and
  Remolona 1999 JF, https://ideas.repec.org/a/bla/jfinan/v54y1999i5p1901-1915.html).
* ES around FOMC: depth hits ~20% of control-day level right before the statement; spread elevated before, normal
  right after (Rosa 2016 Economics Letters, https://ideas.repec.org/a/eee/ecolet/v138y2016icp5-8.html).
* ES/ZN spreads stayed near one tick 2013-2016 even in volatile periods; market makers cut size, not price (CFTC
  Fett and Haynes 2017, https://www.cftc.gov/sites/default/files/idc/groups/public/@economicanalysis/documents/file/oce_liquidityfuturesmarkets.pdf).
* Latency: YouTube low latency <10 s, ultra-low <5 s (https://support.google.com/youtube/answer/7444635) but the Fed
  does not live-stream pressers there; Brightcove low-latency live 5-10 s
  (https://brightcove.com/?p=805); streaming Whisper 3.3 s (https://arxiv.org/abs/2307.14743).
* Ticks: ES 0.25 = $12.50; ZN 1/2 of 1/32 = $15.625; ZT 1/8 of 1/32 = $7.8125 (CME specs via search; cmegroup.com
  timed out / 403 for direct fetch).
* Cost vs volatility (scripts/power.py, 2019-2026 USMPD presser windows, 1-tick spread + ~$2-2.5/side fees assumed,
  ES at 7776.5 from our cache, DV01s approximate): round trip / sd of a 2-minute slice: ES 3.4%, 6E 11.9%, ZT 31%,
  ZF 31%, ZN 46%, SR3 (4th quarterly) 54%.

## 7. Evaluation (scripts/power.py, power_full.txt)

MDE correlation (80% power, alpha .05): n=93 -> 0.287; 2019-2026 n=61 -> 0.352; alpha .001 -> 0.41 / 0.50.
Answer level (2,226 answers, ~23/presser): MDE 0.059 if independent, 0.107 at ICC 0.1, 0.139 at ICC 0.2.
Per-event Sharpe for t=2 with n=93: 0.21 (0.59 annualised at 8/yr); t=3: 0.31 (0.88).
Live confirmation at t=2 of SR/event 0.2 needs 100 events = 12.5 years.

## 5 (filled). Databento costs, FREE metadata.get_cost only (scripts/cost_query.py, cost_extras.py, cost_summary.txt)

Dataset GLBX.MDP3 (all schemas incl. ohlcv-1s/bbo-1s/tbbo/mbp-1 from 2010-06-06; mbo from 2017-05-21). Unit prices
($/GB, historical): ohlcv-1s/1m 70, tbbo/trades 28, bbo-1s 18, mbp-1 1.8, mbp-10 0.5 (metadata.list_unit_prices).
Use volume-ranked continuous symbols (`ES.v.0`): calendar `.c.0` picks the expiring contract during roll weeks
(2025-09-17: ES.c.0 1s bars 8,621 for 5 symbols vs ES.v.0 alone 9,509).

Windows: 13:30-16:30 ET on all 95 presser days (2020-03-03 10:30-13:30; 2020-03-15 17:30-20:30).
* ohlcv-1s, ES/ZN/ZT/ZF/6E .v.0 + SR3.v.0, all 95 days: **$8.60** (2.35 M records); per day median $0.0875 for 5 fronts.
* ohlcv-1m, same: **$0.33**.
* 2011-2012 era-correct window (12:00-16:15, statement 12:30) adds about $0.21 (1s).
Extras, priced on 12 sample days and extrapolated to all applicable presser days:
* bbo-1s (1-second best bid/offer) ES+ZN+ZT: ~$3.6  <- cheapest way to measure spreads during pressers
* tbbo ES+ZN+ZT: ~$62; mbp-1 ES+ZN+ZT: ~$42; mbp-10 ES: ~$53
* ohlcv-1s NQ+6J+GC: ~$6.4; ZQ v.0-3: ~$0.5; GE (Eurodollar) v.0-7, 67 days to 2023-03: ~$2.8; SR3 v.1-7, 66 days
  since 2018-05: ~$1.5
* VIX futures are on XCBF.PITCH (Cboe Futures Exchange) from 2018-11-04 only: VX v.0-1 ohlcv-1s ~$50, ohlcv-1m ~$5.5.
Suggested bundle: 1s fronts + bbo-1s + SR3/GE strips + NQ/6J/GC + VX 1m ~= $28.

## 4b. Which instruments react (USMPD, sd presser / sd statement window)
2011-18 ratio < 1 for rates and FX (presser mattered less); 2019-26 ratio > 1 for every asset: SPFUT 1.90, UST10Y 1.49,
TIPS10Y 1.39, DXY 1.36, EURUSD 1.32, USDJPY 1.29, UST5Y 1.26, ED8 1.25, ED4 1.23, UST2Y 1.19, FF4 1.14.
Presser-window moves 2019-26 are one factor: corr with UST2Y move: ED4 0.99, TIPS10Y 0.91, UST10Y 0.89, DXY 0.88,
USDJPY 0.86, EURUSD -0.85, SPFUT -0.73.

## 8. Latency budget for a student pipeline (estimates; components cited where possible)
| Stage | Estimate | Basis |
|---|---|---|
| Room -> public video | ~3 s audio-video skew on the Fed feed; live HLS standard latency UNVERIFIED (Brightcove low-latency mode 5-10 s) | Gomez-Cram and Grotteria fn 17; brightcove.com/?p=805 |
| Streaming ASR | ~3.3 s (whisper_streaming) | arXiv 2307.14743 |
| Face/voice feature window | 2-3 s of frames/audio before a score exists | design assumption |
| Model + decision | <0.1 s on the 5090 | assumption |
| Order to CME via retail API | 0.1-1 s | assumption, UNVERIFIED |
| Total behind the room | ~8-20 s | sum |
Professional desks hear the room within seconds and macro-news prices move within milliseconds (Chordia et al. 2018), so
the first reaction to any sentence is not capturable; only continuation after ~10-60 s can be traded.

## 9. Evaluation design (recommended)
1. Two targets, never mixed: (a) contemporaneous: return over [answer start, answer end + 5 s]; (b) predictive: return over
   [answer end + L, answer end + L + H], L in {10, 30, 60 s} (latency), H in {1, 5, 15 min, presser end, 16:00}.
   Only (b) can be traded; report (a) only as a measurement-validity check.
2. Units: presser (n=93 scheduled) for presser-level signals; answer (2,226) for within-presser signals with meeting
   clusters. Always include meeting fixed effects or demeaning and the statement-window move as a control
   (Gomez-Cram and Grotteria baseline) so features must beat "the statement already told you".
3. Cross-validation: leave-one-meeting-out (or leave-one-year-out) for every learned step, including feature scaling,
   chair baselines, thresholds. Leave-one-chair-out to test transfer (train Bernanke+Yellen+Powell, test Warsh).
   Sealed test: all pressers from 2024-01 onward (or from 2025-01) never touched until a frozen pipeline exists;
   then live paper-trading on Warsh pressers from 2026-10-28.
4. Inference: meeting-block bootstrap (resample whole pressers) or wild cluster bootstrap (Cameron, Gelbach, Miller 2008,
   https://www.nber.org/papers/t0344); report t on meeting-level P&L.
5. Multiple testing: one pre-registered primary (one instrument, one horizon, one signal), t > 3 hurdle (Harvey, Liu,
   Zhu 2016, https://www.nber.org/papers/w20592); Holm or Romano-Wolf for secondaries; deflated Sharpe ratio for any
   strategy chosen after search (Bailey and Lopez de Prado 2014, https://papers.ssrn.com/abstract=2460551).
6. Placebos: shift timestamps by +/- 2, 5, 10 min; shuffle answers within presser; run the same features on
   non-presser FOMC statement days and on Fed speeches; reverse-time check (feature measured after the return).
7. Pre-registration: freeze code, data hashes, feature list, primary hypothesis, and stopping rule in a dated public
   registry (OSF or AsPredicted) before touching the sealed test.
8. Expect decay: published anomalies return 26% less out of sample and 58% less after publication (McLean and Pontiff,
   https://Www.Gwern.net/doc/economics/2016-mclean.pdf); the statement-sign presser effect above went to zero after 2019;
   the pre-FOMC drift disappeared after 2015 (Kurov, Wolfe, Gilbert 2021,
   https://www.skidmore.edu/economics/documents/KurovWolfeGilbert-TheDisappearingPre-FOMC-Announce-Drift-200914.pdf).
