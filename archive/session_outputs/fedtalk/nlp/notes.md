# fedtalk / nlp: source log (2026-10-03)

Working notes behind the structured answer. Numbers are as reported by each source. [V] means opened and read; [U] means not opened (unverified).

## Regime fact
- [V] Kevin Warsh sworn in as Fed Chair on 2026-05-22. Powell no longer chairs pressers. https://federalreserve.gov/newsevents/pressreleases/other20260522a.htm
- [V] 2026 pressers so far: Jan 28, Mar 18, Apr 29 (Powell); Jun 17, Jul 29, Sep 16 (Warsh). https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- [V] Sep 2026 presser used about 29% fewer words than July and about 33% fewer than June. Warsh has moved away from forward guidance (AOL/Yahoo, 2026-09-30). https://aol.com/articles/feds-chairman-lot-less-chart-115238000.html
- [V] Transcript PDFs are posted per meeting, e.g. /mediacenter/files/FOMCpresconf20260617.pdf. https://www.federalreserve.gov/monetarypolicy/fomcpresconf20260617.htm

## Classifiers (HF API metadata pulled 2026-10-03)
| id | license | size | last mod | gated | FOMC numbers |
|---|---|---|---|---|---|
| gtfintechlab/FOMC-RoBERTa | cc-by-nc-4.0 | 1.42 GB (RoBERTa-large) | 2023-09-12 | manual | TDW paper: weighted F1 0.7171 combined, 0.5517 press conf (PC), 0.7150 minutes, 0.7169 speeches; time split 1996-2019 train / 2020-22 test gives 0.7114 |
| gtfintechlab/model_federal_reserve_system_stance_label | cc-by-nc-sa-4.0 | 355M params (card says roberta-base; the size says large) | 2025-08-15 | no | WCB paper: FOMC stance F1 RoBERTa-large 0.749, base 0.747, GPT-4o 0.584, Llama-3-70B 0.599 (minutes only, 1996-2024, 1k sentences, random 700/150/150 split) |
| gtfintechlab/model_federal_reserve_system_certain_label / _time_label | cc-by-nc-sa-4.0 | 355M | 2025-05-12 | manual | WCB aggregate: uncertainty F1 0.846 (large), temporal 0.868 (base) |
| gtfintechlab/model_WCB_stance_label | cc-by-4.0 | 355M | 2025-08-25 | manual | aggregate WCB |
| Moritz-Pfeifer/CentralBankRoBERTa-sentiment-classifier | MIT | 499 MB (RoBERTa-base) | 2024-11-15 | no | acc/F1 0.88 (binary positive/negative for agents; Fed speech sentences, 6,683 labeled) |
| Moritz-Pfeifer/CentralBankRoBERTa-agent-classifier | MIT | 499 MB | 2024-01-10 | no | acc/F1 0.93 (5 agents) |
| ZiweiChen/FinBERT-FOMC | none on card | 439 MB | 2024-10-05 | no | GitHub: acc 88.3% vs FinBERT 84.0% (pos/neg/neutral, minutes 2006-2023) |
| Wonseong/FinBERT-FOMC-aspects | apache-2.0 | 110M | 2026-04-22 | no | holdout acc 0.879, macro-F1 0.798 (growth/employment/inflation; labels from gpt-oss-20b zero-shot) |
| ProsusAI/finbert | Apache-2.0 (GitHub LICENSE) | 438 MB | 2023-05-23 | no | TDW: FinBERT-base fine-tuned F1 0.4631 PC, 0.6325 combined |
| yiyanghkust/finbert-tone | Apache-2.0 (GitHub yya518/FinBERT) | 439 MB | 2022-10-17 | no | generic tone, no FOMC benchmark |
| FutureMa/Eva-4B-V2 | apache-2.0 | 4.0B (Qwen3-4B-Instruct-2507) | 2026-02-10 | no | EvasionBench macro-F1 84.9% (earnings calls; vs <assistant> Opus 4.5 84.4%, GPT-5.2 80.9%) |
| gtfintechlab/SubjECTiveQA-{CLEAR,RELEVANT,CAUTIOUS,...} | cc-by-4.0 | 110M BERT | 2024-12-17 | auto | 49,446 annotations; transfer to White House briefings avg weighted F1 65.97% |
| manelalab/chrono-bert-v1-YYYY1231 (1999-2024) | MIT | 150M ModernBERT | 2025-06 | no | time-clean pretraining, GLUE above BERT |
| manelalab/chrono-gpt-instruct-v1-YYYY1231 | MIT | 1.55B, ctx 1,792 | 2025-12 | no | time-clean instruct LLM |

Datasets: gtfintechlab/fomc_communication (cc-by-nc-4.0, open, 1,984 train / 496 test, has a year field); gtfintechlab/federal_reserve_system (cc-by-nc-sa-4.0); Moritz-Pfeifer/CentralBankCommunication (MIT).

## LLM zero-shot on TDW FOMC
- TDW: ChatGPT-3.5 F1 0.5872 combined / 0.4869 PC. https://arxiv.org/abs/2305.07972
- FLaME (ACL Findings 2025): <assistant> 3.5 Sonnet 0.674, DeepSeek R1 0.670, GPT-4o 0.664, Llama-3-70B 0.652, Gemma-2-27B 0.620, Qwen2-72B 0.605. https://gtfintechlab-flame.static.hf.space/
- Yao et al. AAAI-26 (2508.08001): GPT-4.1 zero-shot macro-F1 0.666; Qwen3-14B zero-shot 0.514; fine-tuned Qwen3-14B plus uncertainty decoding 0.733 combined / 0.667 PC.
- Tang & Yang 2603.14313 (DCS, frozen LLM plus temporal self-supervision): best macro-F1 0.74 (DeepSeek-R1-Distill-Qwen-14B), Spearman with CPI 0.62.
- Op-Fed 2509.13539: closed LLM zero-shot accuracy 0.61 on stance vs human 0.89; under 8% of transcript sentences are non-neutral.
- BIS CB-LMs (WP 1215): 84% FOMC stance vs RoBERTa 81%. No HF release found (HF search for CB-LM / cblm: nothing).

## Look-ahead
- Lopez-Lira, Tang, Zhu 2504.14765: LLMs recall pre-cutoff macro values; masking fails; no recall post-cutoff (GPT-4o 10y yield: 98.5% before cutoff vs 29.4% after).
- Glasserman & Lin 2309.17322: inside the training window, anonymized headlines outperform (the distraction effect is larger than look-ahead).
- He, Lv, Manela, Wu 2502.21206: ChronoBERT/ChronoGPT. Look-ahead in a news-return task is modest.
- Look-Ahead-Bench 2601.13770: standard LLMs show alpha decay; point-in-time models generalize better.
- Sclar et al. ICLR 2024 (2310.11324): prompt formatting alone moves accuracy by up to 76 points.
- gpt-oss knowledge cutoff June 2024 (third-party pages: OpenRouter mirrors; official card not opened [U]). Qwen3.6/3.8 cards state no cutoff.

## Dictionaries
- Loughran-McDonald Master Dictionary (Mar 2026 version, 1993-2025): Uncertainty, Weak/Strong Modal, Constraining. Free for academic use; commercial use needs a licence. https://sraf.nd.edu/loughranmcdonald-master-dictionary/
- Apel & Blix Grimaldi 2012 (Riksbank WP 261): noun+adjective pairs (inflation, growth, wages, price, oil price... x higher/lower, stronger/weaker, faster/slower, increasing/decreasing). Net Index = (hawk-dove)/(hawk+dove)+1. Predicts the next policy decision (Swedish minutes). http://www.riksbank.se/Documents/Rapporter/Working_papers/2012/rap_wp261_120426.pdf
- Gorodnichenko et al. dictionary (TDW Table 1) as the rule-based baseline: F1 0.49 PC, 0.50 combined.

## Market-reaction evidence relevant to NLP design
- Gomez-Cram & Grotteria (JFE 2022; LBS eprint): 41 pressers 2011-Jan 2020. The statement-window move predicts the presser move (corr 44% SPY, 58% 60m Eurodollar). It is realized only in the Q&A. Volatility spikes when the chair discusses statement changes. A strategy that trades presser direction = statement direction earns alpha 12.66 bp per event for stocks (t 2.30). No effect on no-presser days. https://lbsresearch.london.edu/id/eprint/2203/1/SSRN-id3613702.pdf
- De Pooter, FEDS Note 2021-10-12: presser about 6,280 words vs a 468-word statement; Q&A at roughly an 8th-grade reading level; LDA puts monetary policy at about 65% of Q&A.
- Ehrmann & Talmi (JME 2020; BoC SWP 2016-37): less similar statements bring more volatility, and more so after a run of similar ones (Bank of Canada data).

## Costs (Databento metadata.get_cost only, no data pulled)
- One FOMC afternoon 13:45-16:00 ET, ES/ZN/SR3/ZT continuous: ohlcv-1s $0.0252, ohlcv-1m $0.0005, trades $0.049.
