# Strategy 01: independent review

An independent replication and stress test of strategy 01 (Variant A, frozen at commit `5ff6084`): Fed Board speech tone from the frozen 20+20 hawk/dove lexicon, decayed consensus, TLT/UUP at the next open.

**Verdict: drop.** See [VERDICT.md](VERDICT.md) for the full result.

- **Reproduction is exact.** Every daily column of `outputs/equity_is.csv` matches to 3e-14, as does every published statistic.
- **Out of sample (2024-10-03 .. 2026-10-02), the rule was evaluated once, frozen:** Sharpe -0.46 over the T-bill (-0.24 in the original rf=0 accounting). Scoring the 203 later speeches used the same lexicon.
- **Cause:** the consensus is a decayed sum. As the number of speeches grew, it drifted, and the book stayed long bonds while yields rose.
- **In-sample:** 2022 supplies 75% of the P&L. Against a 2-year-yield momentum control, the tone adds 2.3%/yr (t 0.84), which is not significant.

## Layout

| Folder | What it does |
|---|---|
| `replicate/` | Two re-implementations of Variant A from the spec: on the strategy's own CSVs, and through the gqh-flow-clock engine. Includes the bridge between the two accountings. `SPEC_OURS.md` documents every definition. |
| `extend/` | Fetches the Board speech index and pages for 2024-2026 (polite, cached), re-implements the frozen scorer, and validates it against `data/processed/speech_scores.csv` (144 of 144 checked documents identical). Writes `speech_scores_2011_2026.csv` in the same format as the original file. |
| `analyse/` | Out-of-sample evaluation of the frozen rule, a rate-momentum control, the 2022 dependence, a futures version (ZN / short 6E) and the pre-declared portfolio test. `PREDECLARED.md` was written before the results. |
| `verify/` | Independent recomputation of the headline numbers, plus an audit of scores and timing. |

## Running it

1. Clone `https://github.com/minh-stakc/gqh-flow-clock` next to this repository, or set `GQH_REPO` to its path. Build its data cache with `python data/download.py`, and set `GQH_DATA_DIR` to that cache.
2. Install pandas, numpy, scipy, statsmodels, pyarrow, requests, beautifulsoup4 and lxml.
3. Run the stages in order:
   - `replicate/step1_their_data.py` .. `step5_summary.py`
   - `extend/fetch_all.py`, then `extend/score_all.py` (downloads about 200 federalreserve.gov pages, 1-2 s apart; the raw pages are not committed)
   - `analyse/run_analyse.py`, then `run_extras.py`
   - `verify/v1_reproduce.py` .. `v5_repeats.py`

The portfolio test needs the edge-search artifacts (the core_ER_6 portfolio and its sleeves). They are not in this folder. Set `GQH_EDGES_DIR` to them if you have them; the results are already saved in `analyse/t5_portfolio_test.csv` and `verify/out/v4_portfolio.csv`.

## Next on this branch

Version 2 will follow on this branch once its verification finishes: FOMC-RoBERTa scoring on all Board/FOMC communication, 2016 onward. It was pre-registered before any v2 backtest, and it is a separate strategy, so Variant A stays frozen.
