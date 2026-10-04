# Forward test 2: pre-registration (frozen Sat 2026-10-03)

## Why this exists

Forward test 1 (`FORWARD_TEST.md`) tracks the submitted strategy and two close relatives. This second test registers the strategies that a literature review (`research/high_sharpe_literature.md`, kept local) found to have the **best live or post-publication evidence that daily, liquid data can reproduce**. The review's headline finding:
- No strategy has a verified out-of-sample net Sharpe of 1 or more over a full cycle in liquid markets.
- Live records cluster at 0.25–0.6 net.
- The backtest-to-live haircut is about 70%.

So the expectations below are deliberately modest. Nothing here was chosen or tuned on any backtest of ours: these strategies' history is computed only **after** this file and the code are committed and tagged (`forward-test-2-2026-10-03`), in a separate commit.

The 2024-10 to 2026-10 window has been seen and cannot validate anything. Only data from 2026-10-06 counts. Forward test 1's files (`src/forward.py`, `scripts/run_forward.py`, `FORWARD_TEST.md`) are untouched; this test lives in new files: `src/forward2.py` and `scripts/run_forward2.py`.

## Strategies (code: `src/forward2.py` at the tag)

| | Rule | Evidence that motivated it | Pre-registered realistic net Sharpe |
|---|---|---|---|
| **S1** | **Broad CME trend.** 30 futures (Databento GLBX.MDP3, front contract, within-contract returns, one round trip per roll).<br>• *Signal:* mean of the signs of the trailing 21/63/252-day excess returns.<br>• *Sizing:* weight = signal × 0.40/σ/N, where σ is EWMA volatility with a 60-day centre of mass.<br>• *Book:* scaled to 10% ex-ante volatility with the trailing 252-day covariance; gross ≤ 3.<br>• *Trading:* monthly decisions, next-close fills, 1.5 bp one-way (5 bp for the less liquid contracts). | Hurst, Ooi & Pedersen (2013, 2017): trend positive in every decade since 1880. Live trend indices: SG Trend 0.30 net, BTOP50 0.40–0.50 net. | 0.2–0.6 (central 0.4) |
| **S2 (primary)** | **Equity plus trend, equal risk.** 0.5 × (long ES at 10% ex-ante vol) + 0.5 × S1, rescaled to 10% ex-ante vol with the trailing 252-day instrument covariance; gross ≤ 3; monthly; next-close fills. | A 50/50 mix of US equities and live trend indices: 0.72 (1987–2024), against 0.55 for equities and 0.40 for trend alone. | 0.4–0.7 (central 0.6) |
| **S3** | **Faber GTAA.** 20% each in SPY, EFA, IEF, VNQ and DBC when the month-end adjusted close is above the mean of the last 10 month-end closes, otherwise T-bills; monthly; next-open fills; project ETF costs (Yahoo data). | Faber (2007): 0.73 gross 1973–2012; 0.61 after publication (2006–12). | 0.3–0.6 (central 0.45) |
| Benchmarks | **TSMOM_F** (forward test 1), the yardstick for S1; **ES_10VOL** (the S2 equity sleeve alone); **BH5** (equal 20% buy-and-hold of the S3 ETFs). | | |

**Data sources.** Futures come from Databento, because Hugging Face has no maintained continuous CME futures data (checked 2026-10-03). The ETFs and the T-bill come from free Yahoo and FRED data.

## Window, hypotheses and thresholds

- **Window.** Return days on or after **2026-10-06** (`config.FWD_START`, shared with forward test 1). Target positions for that day, computed from data through Fri 2026-10-02, are committed as `forward/positions2_for_2026-10-06.csv`.
- **Primary metric.** Annualised Sharpe of daily net returns over the T-bill. Also reported: annual return, volatility, maximum drawdown, cumulative return, a 21-day block-bootstrap 90% interval, and the standard error √(252/n).
- **H2-S2 (primary):** S2's forward Sharpe is positive. **H2-S1:** S1's forward Sharpe is positive; the S1 − TSMOM_F difference is reported but is not expected to be detectable. **H2-S3:** S3's forward Sharpe is above BH5's.
- **Tiers at 24 months.** ≥ the central value: consistent with the literature. 0 to central: weak. < 0: below expectations. The pre-registered 90% interval for a 24-month Sharpe at the central value is about −0.8 to +1.6 for S1, −0.7 to +1.9 for S2, and −0.75 to +1.7 for S3.
- **What a strong result means.** A 24-month Sharpe of 1 or more will be read as luck-assisted, not as validation.
- **Multiple testing.** α = 0.05/3 within this test, and 0.05/6 for any claim that spans both forward tests.
- **Implementation check (S1).** Weekly-return correlation with DBMF and AQMIX (public managed-futures funds) is reported. Below 0.5 in a six-month block flags the build for review; the frozen version still runs.

## Conduct

- **Frozen.** No changes to code, parameters, universes or costs.
- **Delisting.** A contract that stops trading or loses vendor coverage leaves the universe from that date, recorded in the report.
- **Quarterly reports.** One on the first business day after each quarter end (2027-01-04, 2027-04-01, …), with the verdict at 24 months. Each is committed whatever it shows; every evaluation is also appended to `forward/forward2_log.csv`.
- **Paper evaluation only.** Not investment advice.

## How to run

First refresh the free data:

```bash
python data/download.py
```

Then refresh the CME futures. Use a fresh `GQH_DATA_DIR` for this step.

```bash
GQH_DATA_END=<date> python data/download_databento.py
```

Then run the evaluation:

```bash
python scripts/run_forward2.py evaluate
```
