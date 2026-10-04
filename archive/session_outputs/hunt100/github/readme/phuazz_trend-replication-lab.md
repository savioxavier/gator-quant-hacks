# trend-replication-lab

**Context: Personal** — systematic research study; a prospective engine for the Multi-Strategy
Portfolio stack.

**Dashboard:** <https://phuazz.github.io/trend-replication-lab/> — the Track B (ETF-native) result.

A faithful, documented replication of the diversified-CTA trend baseline published in
*Beyond Passive Investing*, "Trend following (1/4): Replicating your own program" (30 May 2026).
The point of the study is the **process**, not a headline Sharpe: take a clearly specified,
published methodology, reproduce it exactly, stress-test it, document where it can go silently
wrong, and record the result as defensible evidence of rules-based research.

This is Study 01 in what is intended to be a small library of reproduced systematic programs.

## Where this sits in the Multi-Strategy Portfolio architecture

The Multi-Strategy Portfolio stack separates **engines** (generate weights + backtest stats) from
the **valuation layer** (`multi-strategy-portfolio`, which marks published weights to market and
blends sleeves). See `multi-strategy-portfolio/DESIGN.md`. This repo is a prospective **engine /
research engine**: if the study graduates from research to a deployable sleeve, it would publish
the weekly contract (`weights`, `anchor_*`, `regime_state`, `backtest_stats`,
`cost_assumption_bps`) that the valuation layer consumes. It is **not** a deployment proposal at
this stage.

## Two tracks, one construction

The article's construction (4-horizon averaged-clipped momentum z-score, 63-day price-change vol,
two-stage sector→portfolio vol targeting, weekly rebalance with one-day delay) is encoded **once**
in `scripts/` and is data-source-agnostic, so the same engine serves:

- **Track A — futures-faithful.** Reproduce the published 62-market baseline (target Sharpe ~1.03
  gross / ~1.00 net, 1995–2026). **Gated on clean back-adjusted futures data** — see below.
- **Track B — ETF-native translation.** Express the same construction through a basket of liquid
  ETFs, which is the realistic deployable path for a personal book without futures prime brokerage
  and connects to the existing ETF engines (`breadth-thrust-etf`, `Global-ETF-Trend-Scanner`).

## Status — SCAFFOLD. Not run on real data.

- Construction encoded and unit-tested on **synthetic** price data (the maths is verified; the
  numbers are not).
- **Data gate (Track A): faithful reproduction is blocked until clean back-adjusted futures data
  is procured.** `commodity-futures-trend/README.md` documents why free Yahoo `=F` data fails
  (the cocoa −92% data-trust canary). Do not quote any Track-A Sharpe produced on `=F` data.
- Universe in `scripts/config.py` is **PROVISIONAL** — the sector structure is faithful, but the
  individual contracts are not yet two-source verified against the article's 62-name table.

## Run

```
pip install -r requirements.txt
pytest -q                       # verifies the construction on synthetic data
python -m scripts.backtest      # runs on the synthetic loader; prints costed metrics
```

Swap the loader in `scripts/config.py` once a real data source is wired (`scripts/data.py`).

## Provenance

Source: *Beyond Passive Investing*, "Trend following (1/4): Replicating your own program",
30 May 2026 — a public Substack post (beyondpassive.substack.com). Studying and reproducing a
published methodology for personal research is clean. This is **not** licensed third-party IP.

*Last updated: 2026-07-11. Status: scaffold; data-gated; not deployed.*
