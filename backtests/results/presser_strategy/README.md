# Press-conference trades as strategy-level series

**What this is.** The pre-registered press-conference trades (H1-primary and BENCH-R) shown as daily strategy return
series, with the in-sample and out-of-sample metrics the Gator Quant Hacks rules ask for. It is a **presentation of
trades that were already fixed** by their own pre-registrations (`../../../preregistration/presser_ADDENDUM.md`,
`presser_DEVIATION_D1.md`, `presser_team_FINAL_PLAN.md`), done under the last section of
`../../../preregistration/v2_DEVIATION_D3_OOS.md` (sha256 `97585d3c...af1c69`).

- **No position, sample or rule changed.** Every trade is a row of the committed suite output
  (`../presser_h1/`). The script checks each position against the frozen positions file
  (`backtests/presser/backtest/positions/`, sha256 manifest). It also checks that the suite's own gross, measured-cost
  and fixed-tick rows, the G3 sample (n = 20, mean +0.50 ticks) and the BENCH-R era means come out the same
  (`qa.json`).
- **G3 stays NO-GO.** Powell 2023-2026 confirmation sample: n = 20, mean +0.50 ticks gross (USD 3.91), one-sided
  sign-flip p = 0.45, 90% block-bootstrap CI [-4.06, 5.30] ticks. Nothing here can change that verdict.
- **The plan did not want these numbers.** The team plan says there is no net Sharpe on H1 (the plan calls H1
  non-executable) and that BENCH-R eras are never averaged into one Sharpe. These Sharpes exist only because the
  competition asks for IS/OOS strategy metrics and D-3 allows them as a presentation. To respect the era rule, BENCH-R
  in-sample is also shown split into 2016-2019 and 2020-2024.
- **The out-of-sample window is a calendar split, not an unseen holdout.** The 2024-10-03 .. 2026-10-02 trades were
  already part of the press-conference results reported on 2026-10-03: 12 of the 20 G3 meetings, plus the BENCH-R
  yearly and 2024-10..2026-09 decay tables. Nothing was fitted on the in-sample window except the position size N.
  The H1 residual regression is point-in-time and uses only earlier meetings.
- **No price levels** appear in any file here: only ticks, dollars of P&L per contract, returns, half-spreads in
  ticks, sizes in contracts and aggregate notionals.

## Result

Neither strategy covers its costs **in-sample on its pre-registered instrument (ZT)**:

- **H1-primary ZT:** net 1x Sharpe -0.17 in-sample and -1.33 out of sample. Gross it is 0.19 in-sample and -0.79 out
  of sample.
- **BENCH-R ZT:** net 1x Sharpe -0.51 in-sample and +0.18 out of sample, which falls to -0.02 at 2x costs. In-sample
  it has two different eras: +0.20 net in 2016-2019 and -0.81 net in 2020-2024.

The robustness symbols tell the same story, with one exception: BENCH-R ES (net 1x 0.12 in-sample, 0.71 out of
sample). ES is one of eight series looked at here. It is a robustness row and not the designated instrument, and it
carries no inferential weight.

![H1-primary ZT](equity_h1primary_ZT.png)

![BENCH-R ZT](equity_benchr_ZT.png)

Small multiples for ZF, ZN and ES: `equity_h1primary_all_symbols.png`, `equity_benchr_all_symbols.png`.

### Headline: ZT

| strategy | window | dates | N | cost | n trades | ann. return | ann. vol | Sharpe (daily) | per-trade Sharpe | max DD | hit rate | contracts/yr | notional/yr | turnover (x capital/yr) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1-primary | IS | 2018-03-21..2024-10-02 | 4,788 | gross | 39 | 1.9% | 10.0% | 0.19 | 0.08 | -12.7% | 49% | 57,212 | $11.4bn | 1,144 |
| H1-primary | IS | 2018-03-21..2024-10-02 | 4,788 | net1x | 39 | -1.7% | 10.0% | -0.17 | -0.07 | -16.5% | 46% | 57,212 | $11.4bn | 1,144 |
| H1-primary | IS | 2018-03-21..2024-10-02 | 4,788 | net2x | 39 | -5.3% | 10.3% | -0.52 | -0.21 | -36.1% | 33% | 57,212 | $11.4bn | 1,144 |
| H1-primary | OOS | 2024-10-03..2026-10-02 | 4,788 | gross | 15 | -5.1% | 6.4% | -0.79 | -0.29 | -15.3% | 47% | 72,250 | $14.5bn | 1,445 |
| H1-primary | OOS | 2024-10-03..2026-10-02 | 4,788 | net1x | 15 | -9.3% | 7.0% | -1.33 | -0.53 | -20.8% | 40% | 72,250 | $14.5bn | 1,445 |
| H1-primary | OOS | 2024-10-03..2026-10-02 | 4,788 | net2x | 15 | -13.6% | 7.9% | -1.73 | -0.78 | -28.6% | 7% | 72,250 | $14.5bn | 1,445 |
| BENCH-R | IS | 2016-03-16..2024-10-02 | 1,916 | gross | 55 | -3.5% | 10.0% | -0.35 | -0.14 | -46.3% | 47% | 24,680 | $4.9bn | 494 |
| BENCH-R | IS | 2016-03-16..2024-10-02 | 1,916 | net1x | 55 | -5.1% | 10.1% | -0.51 | -0.20 | -54.9% | 44% | 24,680 | $4.9bn | 494 |
| BENCH-R | IS | 2016-03-16..2024-10-02 | 1,916 | net2x | 55 | -6.8% | 10.2% | -0.67 | -0.27 | -64.6% | 42% | 24,680 | $4.9bn | 494 |
| BENCH-R | OOS | 2024-10-03..2026-10-02 | 1,916 | gross | 15 | 3.2% | 8.5% | 0.38 | 0.14 | -10.7% | 53% | 28,912 | $5.8bn | 578 |
| BENCH-R | OOS | 2024-10-03..2026-10-02 | 1,916 | net1x | 15 | 1.5% | 8.4% | 0.18 | 0.06 | -11.7% | 47% | 28,912 | $5.8bn | 578 |
| BENCH-R | OOS | 2024-10-03..2026-10-02 | 1,916 | net2x | 15 | -0.2% | 8.4% | -0.02 | -0.01 | -12.7% | 47% | 28,912 | $5.8bn | 578 |

Sub-windows (ZT, Sharpe gross / net 1x / net 2x):

- H1, 2016-2022 sample (2018-03-21 .. 2022-12-31, 31 trades, clean under D1): 0.11 / -0.45 / -0.95.
- H1, G3 confirmation sample (2023-02-01 .. 2026-04-29, 20 trades, spans IS and OOS): 0.10 / -0.20 / -0.48.
- BENCH-R, era 2016-2019 (20 trades): 0.48 / 0.20 / -0.09.
- BENCH-R, era 2020 .. 2024-10-02 (35 trades): -0.69 / -0.81 / -0.93.

### Sharpe (daily, sqrt 252) by symbol

| strategy | symbol | N | IS trades | IS gross | IS net 1x | IS net 2x | OOS trades | OOS gross | OOS net 1x | OOS net 2x | OOS net 1x ex-Warsh |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1-primary | ZT | 4,788 | 39 | 0.19 | -0.17 | -0.52 | 15 | -0.79 | -1.33 | -1.73 | -1.23 |
| H1-primary | ZF | 4,033 | 39 | 0.14 | -0.68 | -1.32 | 15 | -0.55 | -1.64 | -2.18 | -1.71 |
| H1-primary | ZN | 3,072 | 39 | 0.24 | -0.13 | -0.48 | 15 | -0.48 | -0.94 | -1.33 | -0.64 |
| H1-primary | ES | 343 | 39 | -0.33 | -0.37 | -0.40 | 15 | -0.35 | -0.38 | -0.40 | 0.49 |
| BENCH-R | ZT | 1,916 | 55 | -0.35 | -0.51 | -0.67 | 15 | 0.38 | 0.18 | -0.02 | -0.48 |
| BENCH-R | ZF | 1,827 | 56 | -0.04 | -0.45 | -0.83 | 16 | 0.15 | -0.43 | -0.96 | -0.89 |
| BENCH-R | ZN | 1,413 | 56 | -0.09 | -0.27 | -0.45 | 16 | -0.11 | -0.34 | -0.57 | -0.76 |
| BENCH-R | ES | 265 | 55 | 0.14 | 0.12 | 0.09 | 16 | 0.75 | 0.71 | 0.68 | 1.05 |

ZF has no quotes, so its "net" rows use 2 ticks/side plus the fee (see Costs). Every window, cost row and symbol, with
annualised return, volatility, drawdown, turnover, hit rate and mean P&L, is in `tables.md` and `metrics.csv`.

## Conventions

**Trades.**
- **H1-primary:** `h1primary_trades.csv` rows with signal `H1`, clock `primary`, exit `exit_1600` (ADDENDUM 3).
  There are 54 meetings per symbol from 2018-03-21 (end of the burn-in) to 2026-09-16: 31 from the 2016-2022 sample,
  20 from the confirmation sample and 3 Warsh meetings. Only timing-eligible meetings are included, as the rule
  requires.
- **BENCH-R:** `tables/benchr_per_meeting_<SYM>.csv`, the primary exit at the next 1m open after tau_end_upper
  (ADDENDUM 5). That gives ZT 70 meetings (three have a zero sign and no trade), ZF and ZN 72, and ES 71; ES uses its
  own 13:50-14:20 sign.
- **Positions:** +/-1 per meeting, as frozen. The plan's live rule of half size for Warsh is not applied, because the
  frozen positions are +/-1. Out-of-sample rows without the three Warsh meetings are reported as a sensitivity.

**Windows.**
- In-sample runs from the strategy's first trade (H1 2018-03-21, BENCH-R 2016-03-16) to 2024-10-02.
- Out-of-sample runs from 2024-10-03 to 2026-10-02.
- Every metric is computed on its own window, and drawdowns restart at the window start.

**Sizing.**
- Capital is $10m. Each trade is N contracts, constant for that strategy and symbol.
- N = round(0.10 / annualised vol of the in-sample daily **gross** series of one contract), so the in-sample
  volatility is 10% (9.98% to 10.01% after rounding, `sizing.csv`).
- The same N is used out of sample and for every cost row.
- P&L and costs are linear in N, so the Sharpe ratios and hit rates do not depend on N. N sets only the levels of
  return, volatility, drawdown and turnover.

**Daily series** (`daily_returns.csv`).
- Return on a trade day = N x trade P&L / $10m, and 0 on every other trading day. Each strategy has one trade per
  meeting day, opened and closed the same afternoon.
- The calendar is the NYSE trading days, taken from the dates of the free Yahoo ^GSPC series in the gqh cache. Every
  trade date is checked to be in it.

**Costs, per contract.**
- **Gross:** trade prints from the 1m bars (ADDENDUM 7, C0). This is associational and not an executable mid.
- **Net 1x:** the measured half-spread at the entry second plus the measured half-spread at the exit second (bbo-1s,
  ADDENDUM 1.3 and 7, row CM), plus a fee of $2.00 per side (A-04, an **unverified** broker estimate).
  - The ZT market was one tick wide at every fill, so ZT net 1x = 1 tick + $4 per round trip: $11.81 from 2019 and
    $19.63 in 2018.
  - ZN: 1 tick + $4 at every fill. ES: 1 to 2.5 ticks (mean 1.1) + $4.
- **Net 2x:** twice the net 1x cost.
- **ZF:** the suite has no ZF quotes, so ZF net 1x is the suite's C2+F row (2 ticks/side + $2/side), and net 2x is
  4 ticks/side + $4/side.
- **Fixed-tick rows** for every symbol (`fixed1x` = C2+F; `fixed2x` = 4 ticks/side + $4/side) are in `tables.md` and
  `metrics.csv`. They are much harsher than the measured half-spread: H1 ZT in-sample net Sharpe is -0.85 at
  fixed 1x.

**Metrics** (`metrics.csv`).
- Annualised return = mean daily return x 252. This is arithmetic, with no reinvestment, because N is constant.
- Annualised volatility = sd of daily returns x sqrt(252).
- Sharpe = their ratio. Futures P&L is an excess return, so no risk-free rate is subtracted, and interest on the
  collateral is not included.
- Per-trade Sharpe = mean / sd of the per-trade P&L per contract, not annualised. `metrics.csv` also gives it
  annualised (x sqrt(trades per year)) and the t-statistic (x sqrt(n)).
- Max drawdown is computed on the additive equity curve 1 + cumulative return: min(equity / running peak - 1).
  - A value below -100% means that the constant N would have lost more than the $10m.
  - This happens only at fixed 2x costs, and for H1 ZF at net 2x.
- Hit rate = share of trades with P&L > 0. Zero-P&L trades count as misses; `zero_share` gives their share (6 of the
  54 H1 ZT trades moved 0 ticks, most of them in 2020-2021).

**Turnover.**
- Contracts per year = 2 x N x trades / years, counting both entry and exit, with years = trading days / 252.
- Notional per year is the same count times the notional per contract:
  - Treasury futures at face value: ZT $200k, ZF and ZN $100k.
  - ES at 50 x the S&P 500 close on the trade date (free Yahoo series; a proxy that ignores the futures basis).
- Turnover (x capital) = notional per year / $10m.

## Capacity and realism (read before quoting a net number)

- **Leverage.** At N contracts, the face notional of one H1 ZT trade is 96x the capital ($958m on $10m). For BENCH-R
  ZT it is 38x. Margin is not modelled.
- **Displayed liquidity** (`capacity_top_of_book.csv`). This is the size shown at the touch on the side the trade
  takes, at the fill second, under the suite's quote rule.
  - H1 ZT: N = 4,788 against a median of 518 contracts at entry and about 1,330 at exit.
  - BENCH-R ZT: N = 1,916 against about 617 at entry and 593 at exit.
  - H1 ES: N = 343 against about 22 at entry.
- The measured half-spread is therefore the cost of a small order at the top of the book. The net rows include no
  market impact for N contracts, so at the stated size they are optimistic.
- **Execution clock.** Entries use the upper-bound clock of ADDENDUM 1.1, with an 11 s TV delay assumed and no true
  wall clock. The plan calls H1 non-executable until a live latency measurement exists.
- **Sample size.** The out-of-sample window has 15 or 16 trades per series. Over two years, the standard error of an
  annualised Sharpe is about 0.7; over the 6.5 to 8.5 in-sample years it is about 0.35 to 0.4. The H1 ZT
  out-of-sample net t-statistic is -2.06 and the in-sample one is -0.43.
- **BENCH-R is non-blind** (ADDENDUM 12): its era correlations were seen before the addendum.
- **Warsh.** The three Warsh meetings are a chair change and a domain shift for the text model (plan).
- **H4 is not included.** The exploratory H2/H3/H4 stage has not run (its features are pending), and D-3 adds it only
  once it has run.

## Files

| file | content |
|---|---|
| `build_presser_strategy.py` | builds everything below, except the capacity table, from committed files plus the free Yahoo calendar; reads no licensed data |
| `capacity_top_of_book.py` | optional; reads displayed sizes (not prices) from the licensed bbo-1s file and writes `capacity_top_of_book.csv` |
| `per_trade.csv` | one row per trade: window, sample, chair, position, entry and exit time (ET), hold, tick era, $ per tick, gross ticks, half-spreads in ticks, cost basis, net ticks, gross/net 1x/net 2x/fixed $ per contract, N, position P&L |
| `daily_returns.csv` | daily return series (fraction of $10m), gross/net 1x/net 2x, per strategy and symbol |
| `metrics.csv` | every metric for every strategy x symbol x variant (all, ex_warsh) x window x cost |
| `tables.md` | the same, as markdown tables |
| `key_metrics.json` | IS/OOS x gross/net 1x/net 2x headline metrics per strategy and symbol |
| `sizing.csv` | N per strategy and symbol, with the in-sample vol at one contract and at N |
| `equity_*.png` | equity curves (cumulative P&L in % of $10m; the shaded area is out of sample) |
| `qa.json` | input checks: pre-registration hashes, frozen positions, reconciliation with the suite rows, G3 and BENCH-R era means reproduced, calendar coverage |
| `run_meta.json` | input files with sha256, conventions, N |

The frozen positions manifest was written on Windows with CRLF line endings, while git stores the files with LF. The
script accepts a file whose hash matches either as stored or after converting LF to CRLF (`qa.json` records which).

## Reproduce

From the repository root:

```
PY=<python with pandas, numpy, matplotlib, pyarrow> GQH_DATA_DIR=<gqh cache holding index_daily.parquet> \
  $PY backtests/results/presser_strategy/build_presser_strategy.py
# optional, needs the licensed quotes (never commit them):
GQH_MARKET_DIR=<folder with bbo-1s__all_2016_2026.parquet> \
  $PY backtests/results/presser_strategy/capacity_top_of_book.py
```
