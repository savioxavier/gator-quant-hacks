# TrendLab

The sequel to [MechLab](../mechlab). MechLab mechanized a hyped retail strategy (the
ICT/PB "mech model") and honestly killed it: zero pre-cost signal, −0.226R/trade after
costs, indistinguishable from random. TrendLab asks the natural next question: **what
does a strategy with a real edge look like, and can it survive the exact same rigor?**

The candidate wasn't picked by vibes: four contenders (trend following, dual momentum,
volatility risk premium, crypto funding carry) were argued by independent advocates and
scored by skeptical judges. See [docs/why-trend.md](docs/why-trend.md). Winner:
**diversified time-series momentum (trend following) on asset-class ETFs**, the
best-documented anomaly in empirical finance (Moskowitz-Ooi-Pedersen 2012; Hurst et
al. 2017: positive in every decade since 1880; live SG Trend Index since 2000).

## What it does

TrendLab backtests a long/flat trend-following strategy across 10 asset-class ETFs,
then puts it through six rigor gates designed to catch a fake edge, the same bar
MechLab used to kill the mech model. Every parameter is fixed **ex ante** from
published papers, so there is no tuning stage: if the strategy works, it works with
numbers someone else published years ago, and everything after 2013 is out-of-sample
by construction.

## How it works

**The strategy (pre-registered, zero tuning):**

- **Universe:** 10 asset-class ETFs: SPY, EFA, EEM (equities), IEF, TLT (Treasuries),
  LQD, HYG (credit), GLD (gold), DBC (commodities), VNQ (REITs).
- **Signal (monthly):** hold a sleeve if its trailing 12-month total return, skipping
  the most recent month, beats T-bills (MOP 2012; skip-month per Jegadeesh-Titman
  1993; T-bill hurdle per Antonacci). Otherwise that sleeve sits in T-bills.
- **Sizing:** inverse-volatility risk budgets, 25% cap per sleeve, no leverage, no
  shorting (Faber 2007 long/flat form).
- **Execution:** signals at month-end close, orders at the **next day's** close, 5bps
  one-way costs on all turnover. Cash earns the T-bill rate.

Every parameter above has a citation sitting next to it in [config.py](config.py),
one file, nothing hidden, nothing chosen after seeing the results.

**The six rigor gates (same bar MechLab had to clear):**

1. **Out-of-sample**: chronological holdout (last 35%) *plus* the post-publication
   window (2013+), which no parameter could have been fit to.
2. **Timing null**: 1,000 runs that circularly shift each sleeve's on/off signal,
   preserving exposure, switch frequency, sizing and costs, destroying only the
   *alignment* with returns. Gated on the **post-publication window** (pre-2013 is the
   literature's own discovery sample). Also: an exposure-matched always-in benchmark,
   answering the published critique (Huang et al., JFE 2020) that TSMOM is just scaled
   long bias.
3. **Robustness**: lookbacks 6/9/15m, SMA variant, vol windows, weight caps,
   execution lag, rebalance-day offsets (timing luck), and 3×/5× cost stress.
4. **Breadth**: per-sleeve timing value (trend vs static on each asset) and per-year
   consistency.
5. **Sample size**: floor on out-of-sample months.
6. **Monte Carlo**: block bootstrap of **daily** returns (126-day blocks), so the
   drawdown distribution has the same granularity as the headline maxDD: CIs on excess
   return, Sharpe, drawdown.

A strategy only "passes" if it clears every gate, same rule, stated before the code
ran, that MechLab used to say no.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run_trendlab.py backtest    # downloads free data on first run
.venv/bin/python tests/test_trendlab.py      # unit tests (or: pytest tests/)
```

The first `backtest` run downloads free daily data (Yahoo Finance adjusted closes +
FRED T-bill rates) and caches it under `data/cache/`. Delete that folder to force a
fresh download.

## Files

```
config.py                  every parameter, with its citation, pre-registered
run_trendlab.py             CLI entry point, runs the pipeline, writes reports/report.md
trendlab/data.py            downloads + caches Yahoo prices and FRED T-bill rates
trendlab/engine.py          the signal, sizing, and daily P&L simulation
trendlab/gates.py           the six rigor gates (null, robustness, breadth, ...)
trendlab/metrics.py         Sharpe, drawdown, Monte Carlo, and other stats
trendlab/report.py          turns results into the markdown report + verdict text
tests/test_trendlab.py      unit tests on synthetic data (signals, costs, no lookahead)
docs/why-trend.md           the record of how trend following was picked over 3 rivals
reports/                    generated output: report.md and the CSVs behind it
```

## Requirements

- Python 3.14 (this is what the project was built and tested on).
- `numpy`, `pandas` (pinned away from 3.0.4: that wheel crashes on `Timedelta`
  construction under CPython 3.14), `certifi`, `pytest`. See
  [requirements.txt](requirements.txt).
- No API keys needed. Data comes from Yahoo Finance's public chart endpoint and FRED's
  public CSV endpoint, both free, no signup.

## Verdict: 5 of 6 gates pass, a real premium, but the magic isn't the timing

**This negative-leaning verdict is the whole point of this project. It is not
softened or buried here. Read it before you read anything else.**

22.9 years (2003-2026), 10 sleeves, all numbers net of costs:

- **Strategy: Sharpe 0.70, +3.7%/yr over T-bills, maxDD −16.2%**, vs SPY buy-and-hold
  (Sharpe 0.57, maxDD −55%) and 60/40 (0.66, −31%). Bootstrap CI on excess return
  [+1.7%, +5.4%] excludes zero; 100% of parameter perturbations (including 5× costs)
  stay positive; positive in the holdout and post-publication windows.
- **The failed gate is the finding:** against 1,000 random-timing clones with identical
  exposure, sizing and costs, the trend signal's post-publication edge is +1.9% vs
  +1.8%/yr, p = 0.44. The timing itself is statistically indistinguishable from
  random on post-2013 data, exactly echoing Huang et al. (JFE 2020). Most of the
  return is diversified multi-asset beta + inverse-vol construction.
- **What the timing demonstrably buys is the tails:** GFC +6.9% vs SPY −46%; 2022
  −3.2% vs 60/40's −16.4%. The cost: lagging every V-shaped recovery (2020). Trend is
  a drawdown hedge with ~break-even expected cost, not a return enhancer.
- The code survived a 52-agent adversarial review (look-ahead, statistics, data
  integrity, plausibility); all confirmed findings were fixed in the strict direction,
  including moving gate G2 itself to the tougher post-publication statistic.

Full scoreboard, benchmarks, crisis windows, per-sleeve breadth, robustness grid, and
verdict: [reports/report.md](reports/report.md).

**Honest expectations (written before the results):** this is a **modest, real risk
premium**: think Sharpe ~0.4-0.7 net, not a money printer. It will lag buy-and-hold
equities for years at a stretch (2010-2019 was a famous desert), pays off in long bear
markets (2008, 2022), gets whipsawed in V-shaped crashes (2020), and its true cost is
the discipline to keep running it, which is precisely why the premium has survived
two centuries and publication. In taxable accounts expect ~1%/yr extra tax drag; an
IRA is the right home. If the backtest had shown Sharpe > 0.9, the pre-registered
conclusion was "find the bug."
