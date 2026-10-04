# Projects / datasets (part 2) -- checked 2026-10-03

## B. Audio/text datasets of FOMC pressers (ready-made segmentation)

### Kaggle davidgauthier/fomc-conferences
- https://www.kaggle.com/datasets/davidgauthier/fomc-conferences (metadata from Kaggle public API https://www.kaggle.com/api/v1/datasets/view/davidgauthier/fomc-conferences)
- Apache 2.0; ~7.5 GB compressed (totalBytes 12.9e9 reported); v1 2022-11-06; 45 downloads; usability 0.875.
- Answer-level audio files per press conference 2015-2022 + responses.txt separated by "RESPONSE:"; folder per chair+date. Kaggle login needed to download (user action).
- Reuse: pre-cut chair-answer clips for voice-model experiments; check cut accuracy.

### Voice of Monetary Policy package (Gorodnichenko, Pham, Talavera, AER 113(2) 2023)
- Replication: https://doi.org/10.3886/E178302V1 (openICPSR 178302; page 403 to fetcher, link confirmed on https://www.aeaweb.org/articles?id=10.1257/aer.20220129).
- README (copy in reecehuff/Lets-Face-It docs/README_The_voice_of_monetary_policy.pdf, read): voice model trained on RAVDESS + TESS acted-emotion speech; FOMC audio April 2011 - June 2019 from Fed YouTube playlist PL159CD41EB36CFE86, manually cut into remarks/questions/answers; audio NOT shared (YouTube ToS); FED_text.xlsx Q/A split text; fomc_all.xlsx predicted voice emotions per answer; FED_QA_timing.dta per-answer timestamps; Stata + Python; training took 72 h on CPU server.
- Inspected data (from mirror): 692 answers / 36 pressers; emotion labels happy 375 / sad 282 / neutral 30 / angry 3.
- VoxEU/NBER summary (search snippets; VoxEU page 403): positive voice tone -> SPY up, response builds over days (~100 bp after 5 days per unit tone). UNVERIFIED number (snippet only).

### FOMCBench (HF fomcbench/fomcbench)
- https://huggingface.co/datasets/fomcbench/fomcbench  CC-BY-4.0 (card), created 2026-05-05, 33 downloads; anonymous authors (paper under review).
- 2,154 Q-A pairs from 89 pressers 2011-04-27..2025-12-10; evasion labels direct/intermediate/fully_evasive + Bavelas mechanism + 12 Bull tactics + evasion score 1-5; train 1,554 silver (LLM consensus), dev 200 human (kappa 0.859), test_std 200 (kappa 0.676), test_challenge 200. Powell ~75% of pairs. Eval code in code/src/fomcbench. Text only, no timestamps.
- Reuse: answer-level evasiveness classifier (train on silver, evaluate on human gold), aligned to Q&A turns.

### Trillion Dollar Words (gtfintechlab)
- Repo https://github.com/gtfintechlab/fomc-hawkish-dovish  76 stars, 24 forks, pushed 2024-12-17, CC BY-NC 4.0 (README/LICENSE.md). Folders: code_market_analysis, code_model, data, training_data/test-and-training (3 seeds), look_ahead_bias, llm_prompt_test_labels.
- HF dataset gtfintechlab/fomc_communication: 2,480 sentences (minutes 1,132, press conf 322, speeches 1,026), CC BY-NC 4.0, updated 2024-12-16, 675 downloads. Labels 0 dovish / 1 hawkish / 2 neutral.
- Model gtfintechlab/FOMC-RoBERTa (RoBERTa-large), CC BY-NC 4.0, last modified 2023-09-12, gated=manual (author approval needed; card not readable unauthenticated). Reported F1 0.7113 combined, 0.5346 on press-conference subset (per ar5iv HTML of arXiv 2305.07972; verify in Table). QQQ stance strategy 673% vs 510% buy-hold through Sep 2022 (in-sample; repo later added look_ahead_bias folder).
- tim9510019/FOMC-RoBERTa: ungated card-less re-upload (7,255 downloads, no license tag) -- licence risk, do not use.

### World Central Banks (gtfintechlab, 2025)
- gtfintechlab/federal_reserve_system dataset: 1,000 Fed minutes sentences, 3 seeds (700/150/150), stance (hawkish/dovish/neutral/irrelevant), temporal, certainty labels; CC BY-NC-SA 4.0; updated 2025-05-15.
- gtfintechlab/model_federal_reserve_system_stance_label: 355M params (RoBERTa-large size despite card saying roberta-base), CC BY-NC-SA 4.0, updated 2025-08-15, ungated.
- gtfintechlab/model_WCB_stance_label: 355M, CC-BY-4.0, updated 2025-08-25, gated=manual. Also certain/time label models. WCB_380k_sentences dataset (CC BY-NC-SA 4.0).
- Paper: "Words That Unite The World: A Unified Framework for Deciphering Global Central Bank Communications" (Shah, Sukhani, Pardawala et al. 2025).

### Other Fed text corpora
- aufklarer/central-bank-communications (HF): CC-BY-4.0, updated 2026-10-03 (live), 226,512 annotated sentences, Fed 2,167 docs / 40,553 sentences 1995-02..2026-09 including press_conference; 12-way policy-signal label + topic. Annotation method not stated on card (likely model-generated) -> treat as silver.
- ZipLime/fomc-events (HF): Apache-2.0, updated 2026-10-02; point-in-time FOMC event table 2007-> scheduled to Dec 2027; 571 information arrivals, 184 meetings, statements with exact embargo time (from 2013), minutes release dates, SEP/dot plot, votes; card notes press conference page never carries a time.
- brishen/fomc-meeting-transcripts (HF): 373 verbatim meeting transcripts 1976-2020, ~15.8M words, US gov work, 2026-09-09.
- BoostedJonP/jerome-powell-press-release-QA (HF, MIT, 40 rows, 2025-08-25) and Kaggle jonathanpaserman/fed-press-release-text (MIT, 2.3 MB, updated 2026-03-28): Powell presser transcripts 2018+ with name tags; scraper repo BigJonP/fed-press-conference-dataset (MIT, pushed 2026-03-28).
- Papavero-sh/fed-scraper (GitHub, 1 star, pushed 2026-06-29): Board speeches 2006+ and presser transcripts 2011+ to txt + metadata CSV, resumable.
- vtasca/fed-statement-scraping (32 stars, pushed 2026-09-17, no license file; HF/Kaggle mirrors CC0): statements + minutes 2000+, auto-updated via GitHub Actions.
- yukit-k/centralbank_analysis (76 stars, pushed 2026-05-19, no license): scrapers for statement/minutes/presconf_script/meeting_script/speech/testimony + NLP pipeline (FedSpeak Medium post).
- samchain/bis_central_bank_speeches (Apache-2.0, 19,376 speeches 1997-2025) / tpark-bis/central_bank_speeches (CC BY-NC 4.0, 19,742 rows).
- Moritz-Pfeifer/CentralBankRoBERTa (34 stars) + HF models CentralBankRoBERTa-sentiment-classifier (MIT, acc/F1 0.88 per card) and -agent-classifier; dataset Moritz-Pfeifer/CentralBankCommunication (MIT, 6,205 agent + 6,683 sentiment sentences from Fed speeches 1948-2023).
- yuuki20001/FOMC-sentiment-path (4 stars, pushed 2026-01-13, no license): AAAI 2026 "Interpreting Fedspeak with Confidence", Qwen3-14B LoRA SFT via ms-swift + uncertainty-aware decoding; GT_data folder.
- Op-Fed (arXiv 2509.13539): 1,044 annotated sentences from FOMC meeting transcripts, hierarchical opinion/stance schema; code/data location not found (UNVERIFIED).

## C. Earnings-call audio projects to adapt
- GeminiLn/EarningsCall_Dataset (158 stars, pushed 2022-08-04, no license): Qin & Yang ACL 2019 MDRM; S&P 500 2017 calls, sentence-segmented text + audio; Google Drive folder alive (HTTP 200 on 2026-10-03).
- Earnings-Call-Dataset/MAEC... (107 stars, CC-BY-SA-4.0, pushed 2024-02-15): CIKM 2020; S&P 1500 transcripts + low-level audio features (147.7 MB in repo) + 59 GB MFCC .npy on Drive (link returned HTTP 404); Iterative Forced Alignment code (Aeneas, Python 3.5).
- revdotcom/speech-datasets (139 stars): Earnings-21 (39 h, 9 sectors) and Earnings-22 (119 h, accented), CC BY-SA 4.0, token-level timestamps; HF Revai/earnings21. Use to benchmark ASR on financial speech before trusting word timestamps.
- gtfintechlab/SubjECTive-QA: 2,747 earnings-call QA pairs (120 NYSE firms 2007-2021) with 6 labels Assertive, Cautious, Optimistic, Specific, Clear, Relevant (0/1/2), CC-BY-4.0, gated=auto; six fine-tuned models gtfintechlab/SubjECTiveQA-* (BERT/RoBERTa-base, CC-BY-4.0). Transfer to chair answers.
- gmarti/EarningsCallVoice (HF, Apache-2.0, 2026-08-17): Core-100, 100 human-verified executive reference clip + answer clip units with transcripts; paralinguistics benchmark.
- OuyangKun10/MANAGER (7 stars, pushed 2025-03-23, no license): LREC-COLING 2024 FinNLP; HuBERT audio + FinDKG knowledge graph on MONOPOLY.
- Not useful: sohomghosh/MiMIC (Indian earnings-call slides/images, no audio).

## D. Platform note
- Papers with Code sunset 2025-07-24/25; domain redirects to Hugging Face trending papers; leaderboards gone (https://www.codesota.com/papers-with-code/shutdown, hyper.ai news 42900 -- search results, not opened).

## E. Context that changes the plan
- Kevin Warsh sworn in as Fed chair 2026-05-22; first presser 2026-06-17 (JPMorgan insight page dated 2026-06-08). He did not commit to a presser after every meeting at his confirmation hearing. Powell's last presser was 2026-04-29 (transcript https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20260429.pdf; term ended 2026-05-15 per Kiplinger/news search results). Transcript URL pattern FOMCpresconfYYYYMMDD.pdf. Rough Powell count: 4 in 2018 + 8/yr 2019-2025 + 3 in 2026 = about 63 (estimate, not enumerated). Fed presser pages exist for 2026-06-17 and 2026-07-29 (federalreserve.gov fomcpresconf20260729.htm: transcript PDF + embedded video, chair not named on page).
- Curti & Kazinnik (JME 2023) used Microsoft Azure Emotion API on frames every 2 s, sample to 2020-09-16; 1 SD negative emotion -> -0.53 bp SPY over 3 min, VIX +3.75 bp, EURUSD -0.18 bp; no significant reversal (paper PDF in reecehuff repo docs). Azure retired emotion inference: new users denied June 2022, existing users by end-2022 (techzine 2022-06-22). So exact replication is impossible; DeepFace / open FER models are substitutes.
- Gomez-Cram & Grotteria (JFE 143(3) 2022): millisecond word timestamps from presser video; statement-window price move predicts presser-window move (corr 58% Eurodollar futures, 44% S&P 500) -- per alphaarchitect summary (search snippet). Baseline any multimodal signal must beat.
- Bodilsen, Eriksen, Gronborg (JBF 128, 2021, 106163): replication MATLAB in JonasNygaard/Asset-pricing-FOMC-press-conferences (1 star, pushed 2025-01-20, no license); press-conference days 2011-2018 show stronger beta-return relation and positive stock-bond correlation.
- Hunter Ng, arXiv 2410.20214 (2024): facial expressions 2011-04..2020-12, negative expressions rise with tenure; no code link.
