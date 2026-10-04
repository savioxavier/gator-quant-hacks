# Fed speech tone consensus: independent replication (label "replicate")

This is our own implementation of "Variant A" from savioxavier/gator-quant-hacks, strategies/01. Their code
(HYPOTHESIS.md, config.py, score.py, backtest.py, run_sim.py, download_*.py) was read but never executed,
imported or installed. Their processed CSVs serve only as data: speech_scores.csv, fomc_dates.csv,
markets.csv and fred_DGS2.csv.

## Files

| file | role |
|---|---|
| `fedsignal.py` | signal, sizing, open-to-open simulator, statistics (pure functions) |
| `common.py` | paths, loaders for their CSVs and our caches, read-only access to `src/engine.py` |
| `step1_their_data.py` | full rebuild on their CSVs, compared day by day with their `outputs/equity_is.csv`; also rebuilds their trial 1 |
| `step2_data_check.py` | their markets.csv, DGS2, FOMC and speech files checked against our `etf_daily` / `fred_daily` |
| `step3_our_data_engine.py` | the same rule on our data: stand-alone simulator, `engine.simulate`, sensitivities, yearly table, writes `signal.parquet` |
| `step4_bridge.py` | moves from the stand-alone Sharpe to the engine Sharpe one accounting change at a time |
| `step5_summary.py` | headline table, monthly-sampled Sharpe, `results.json` |
| `signal.parquet` | reusable daily signal and weights (schema below) |
| `signal_session_full.parquet` | the same, indexed by entry session, with vol, FOMC flags, traded flag and clipped z |
| `out/` | per-step outputs (CSV/JSON) |

Run order (repo root as working directory is not required):
`GQH_DATA_DIR=<home>/.cache/gqh PYTHONIOENCODING=utf-8 <venv python> step1_their_data.py`, then step2 to step5.
Nothing is written to the repo: no `results/`, no `run_backtest` or `log_trial` calls, and the OOS unlock stays off.

## Specification as implemented

Sessions: the NYSE calendar starting 2010-01-04. Our calendar (SPY dates) matches their markets.csv dates exactly
(3,712 sessions to 2024-10-02). We take the session index t to be the open where a position is entered. That
position is held from open(t) to open(t+1).

1. **Documents.** We use rows of `speech_scores.csv` with `kept == True` (H+D >= 5 lexicon hits), a non-null
   `speech_date` and a score `s = (H - D) / (H + D + 1)`. For in-sample runs, speech_date must be on or before
   2024-10-02, which leaves 368 docs. The file contains 378 kept docs in total, the last dated 2024-12-03. We do
   not re-score the text: the raw HTML is not in their repo. We did check that `s` matches H and D to 1e-16.
2. **Timing.** Speeches carry a date and no time. A doc dated d therefore enters at the first session strictly
   after d, which is the next open. That covers weekend dates and several docs on one date, whose scores add up.
3. **Consensus.** `C_t = lam * C_{t-1} + inj_t` with `lam = 2^(-1/20)` (half-life of 20 sessions) and `C = 0`
   before the first doc. It is computed as a linear IIR filter (`scipy.signal.lfilter`).
4. **Expanding z.** Only sessions on or after 2011-01-03 count. Mean and std (ddof=1) are expanding, using
   cumulative sums. z is NaN until 252 observations and wherever the std is 0. The first valid z falls on session
   2011-12-30.
5. **Risk.** `mix_t = -0.75 r_TLT,t + 0.25 r_UUP,t`, where r is the open-to-open return on adjusted opens.
   `vol_t = 0.5 * std20 + 0.5 * std60` of `mix` lagged one session (returns ending at open t), annualised with
   sqrt(252) and floored at 4%.
6. **Sizing.** `pos = clip(z, -2, 2)`, `k = 0.10 / vol`, `w_TLT = -0.75 pos k`, `w_UUP = +0.25 pos k`. Weights
   scale down so that |w_TLT| + |w_UUP| <= 1.5. On an FOMC announcement session, w_TLT is halved and w_UUP
   is not.
7. **No-trade band.** The current weights are kept when the L1 change is below 10% of current gross. A trade is
   forced on FOMC sessions, on the session after one, and when the book is flat. Where z or vol is NaN, the
   previous weights carry forward (zero before 2011-12-30).
8. **FOMC sessions.** These come from their `fomc_dates.csv` (117 dates). A date that is not a session maps to
   the next session; 2020-03-15 becomes 2020-03-16. Their file stops at the cut, so for the post-IS rows of
   `signal.parquet` we added the scheduled decisions of 2024-11-07 and 2024-12-18.
9. **Stand-alone simulator (their accounting).** Gross `w_t . r_t`, open to open. Cost
   `|dw_t| x (1.5 bp TLT, 5 bp UUP)`, with the entry trade costed. rf = 0, so cash earns nothing and shorts earn
   nothing. Sharpe = mean/std(ddof=1) x sqrt(252). Turnover = mean(|dw_TLT| + |dw_UUP|) x 252. The sample runs
   from the first valid z (2011-12-30) to the last return that does not need a post-cut open (2024-10-01), 3,208 days.
10. **Engine.** `engine.simulate(w_dec, load_ohlc(["TLT","UUP"], "IS"), rf, exec="next_open",
    cost_bps={"TLT":1.5,"UUP":5.0})` with `w_dec[d] = w_session[session after d]`. We checked that the engine's
    held weight on day t equals our session weight for t, to 0.0. We report two Sharpe definitions:
    "their definition" passes an rf of 0; "ours" passes the T-bill and computes Sharpe on net minus T-bill. The
    engine window is 2011-12-30 to 2024-10-02, 3,209 days.

### `signal.parquet` schema (engine convention)

The index `date` is a decision date d. It runs from 2010-01-04 to 2024-12-31, the last date before their corpus
runs out. Columns `consensus`, `z`, `w_TLT`, `w_UUP` (float64) hold the values for the session after d, so
`engine.simulate(signal[["w_TLT","w_UUP"]].rename(columns=lambda c: c[2:]), ohlc, rf, exec="next_open")` fills
them at the open of d+1 and reproduces the positions above. z is NaN before 2011-12-29; the weights are 0 there.
The values can use information that arrives after the close of d but before the open of d+1: speeches dated d
or on a weekend, and the open price of d+1 inside the vol estimate. That is fine for a fill at the open, but it
is not strictly information from the close of d. The sensitivities below put a size on it.

## Reproduction results (in-sample 2011-12-30 to 2024-10-01/02)

| metric | published | ours, their CSVs | ours, our data, stand-alone | engine, rf=0 | engine, excess over T-bill |
|---|---|---|---|---|---|
| Sharpe gross | 0.2547 | 0.2547 | 0.2547 | 0.2393 | 0.2717 |
| Sharpe 1x cost | 0.2053 | 0.2053 | 0.2053 | 0.1774 | 0.2098 |
| Sharpe 2x cost | 0.1559 | 0.1559 | 0.1559 | 0.1292 | 0.1617 |
| TLT sleeve 1x | 0.2141 | 0.2141 | 0.2141 | 0.1874 | 0.2385 |
| UUP sleeve 1x | 0.0016 | 0.0016 | 0.0016 | -0.0154 | -0.1196 |
| 2022 only 1x | 1.1941 | 1.1941 | 1.1941 | 1.1807 | 1.2449 |
| all other years 1x | 0.0655 | 0.0655 | 0.0655 | 0.0317 | 0.0602 |
| corr(C, DGS2 t-2) | 0.5289 | 0.5289 | 0.5289 | | |
| turnover /yr | 23.44 | 23.44 | 23.44 | 24.50 | 24.50 |
| max DD 1x | -32.9% | -32.9% | -32.9% | -33.6% | -32.8% |
| holdout 2021-01..2024-10 1x | | 0.693 | 0.693 | 0.611 | 0.691 |
| holdout without 2022 | | | | 0.329 | 0.419 |

On their CSVs every daily column (C, z, pos, vol_mix, w_tlt, w_uup, r_gross, r_1x, r_2x, fomc_derisk) matches
their `equity_is.csv` to within 2.4e-14. Their trial 1 (z clock started at the first market session, so 2010
contributed zero padding) also reproduces exactly: 1x 0.4134, gross 0.4584, 3,454 days, first z on
2011-01-10. Of the two, trial 2 matches the spec in config.py (clock from 2011-01-03), and the fix lowered the
Sharpe.

### Why the columns differ

* **Their data vs ours.** Their markets.csv uses yfinance unadjusted plus Adj Close, with
  `adjopen = Open x AdjClose / Close`. That is the same method as our `auto_adjust=True` cache, on the same
  adjustment anchor: the close ratio is 1.0000 and the largest daily open-to-open gap is 0.024 bp (TLT) and
  0.005 bp (UUP). DGS2 matches FRED exactly. The weights differ by at most 4e-5 and the Sharpe ratios by 1e-6.
  Their returns rightly use adjusted opens. Unadjusted opens would leave out TLT's 2.7%/yr distributions and
  raise the 1x Sharpe to 0.25, which is the "unadjusted close" construction error their HYPOTHESIS warns about.
* **Stand-alone to engine at rf=0 (0.2053 to 0.1774).** Step 4 bridge, on identical weights:
  1. Re-booking the same P&L on the engine's day boundaries, as yesterday's position overnight plus today's
     position intraday: -0.018. The mean is unchanged and vol rises from 10.4% to 11.2%. TLT's open-to-open
     daily vol (14.0%) sits below its close-to-close vol (14.8%) because the intraday move and the next
     overnight gap are negatively correlated (-0.09), a reversal around the open print. Monthly vols are almost
     equal (13.1% vs 13.3%). On monthly sampling the two accountings give 0.198 and 0.212, so the gap is
     sampling, not edge.
  2. The engine compounds the overnight leg into the intraday leg: +0.003.
  3. Their |dw| costs: -0.046. The engine's drift-adjusted trades add turnover (24.5 vs 23.4 per year): -0.002.
  4. Short borrow of 30 bp/yr on short ETF weights, which their model omits: -0.014. That is 0.15%/yr.
* **Engine, rf=0 vs T-bill (0.1774 to 0.2098).** Their rf=0 accounting has a short TLT position pay the fund's
  distributions while earning nothing on the proceeds. A long UUP position, meanwhile, keeps the T-bill yield on
  its collateral for free. Our excess return is `sum w_i (r_i - rf) - costs`. The book is net short on average
  (mean net weight -0.13), which adds 0.36%/yr, and the UUP sleeve falls to -0.12 because its long-USD periods
  (2022-23) no longer collect the 4-5% cash yield.

### Yearly Sharpe (1x)

| year | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 (to Oct) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stand-alone | 0.17 | -0.11 | -1.28 | 0.48 | -1.55 | -0.25 | 0.64 | 0.88 | 0.64 | 0.37 | 1.19 | 0.34 | 1.11 |
| engine excess | 0.15 | -0.09 | -1.38 | 0.46 | -1.50 | -0.32 | 0.68 | 0.76 | 0.63 | 0.31 | 1.24 | 0.28 | 1.21 |

### Sensitivities (stand-alone, our data; descriptive only, nothing selected)

| variant | 1x | 2022 | rest | holdout 2021-24 |
|---|---|---|---|---|
| as specified | 0.205 | 1.19 | 0.065 | 0.693 |
| vol lagged one more session (no open(t) price) | 0.209 | 1.17 | 0.073 | 0.688 |
| consensus lagged one more session | 0.295 | 1.29 | 0.157 | 0.706 |
| FOMC de-risk only on policy decisions (6 press-release dates dropped) | 0.202 | 1.19 | 0.061 | 0.693 |
| FOMC de-risk only on pre-announced dates (6 unscheduled 2019-20 dates dropped) | 0.203 | 1.19 | 0.063 | 0.693 |
| no FOMC de-risk | 0.179 | 1.30 | 0.021 | 0.618 |
| no-trade band off | 0.195 | 1.22 | 0.051 | 0.690 |

An extra day of lag raises the Sharpe, so the result does not depend on reacting quickly to speeches. It
behaves like a slow state variable, consistent with its 0.53 correlation with the 2-year yield level.

## Audit notes and caveats

* Within the in-sample window the published numbers are arithmetically correct and reproducible; there was no
  lookahead in the signal. Two small uses of hindsight: the vol estimate uses open(t), the price at which the
  trade is made (removing it moves the Sharpe from 0.205 to 0.209, so it did not help); and FOMC de-risking
  applies on 6 unscheduled 2019-20 dates (removing them moves the Sharpe from 0.205 to 0.203). Neither changes
  any conclusion.
* By the author's own falsifier ("all 1x Sharpe concentrated in 2022"), this is a 2022 result. The other years
  combined give 0.07 (0.06 in excess terms), with -1.3 in 2014 and -1.5 in 2016. The NW t-stat of the in-sample
  excess return is 0.80.
* Holdout 2021-01 to 2024-10-02 (descriptive, since the rule is frozen and the window is in-sample): 0.69 in
  their accounting and 0.69 as excess over T-bill in our engine (0.61 at rf=0). That is just under the 0.7 bar,
  and it falls to 0.33 to 0.42 without 2022.
* **OOS (2024-10-03 to 2026-10-02) cannot be evaluated from their corpus.** The last kept speech is dated
  2024-12-03. Running past that point with no new documents decays C toward 0, which sits above its historical
  (dovish) mean. The result is z > 0 on 95% of 2025-26 days (mean +0.71) and a near-permanent short-TLT book
  (mean w_TLT -0.66): an artifact, not a signal. A genuine OOS test needs the 2025-2026 Board speeches scored
  with the frozen lexicon and the same keep rule (H+D >= 5). The author could have seen 2024-26 market history
  before freezing the rule.
* The lexicon scoring itself (tokeniser, 5-token negation window, H+D >= 5) is not re-verified here. The raw
  HTML is not published, and only 378 of 825 docs pass the hit floor (median hits per doc: 3).
* Their trial log has three rows. Row 3 repeats trial 2's numbers under the label "trial 1", because run_sim.py
  hard-codes trial=1. It is a bookkeeping error, not a third variant.
