# Share-repurchase 8-K and covered call

Notebook: `gator-quant-hacks-8k-options-challenge.ipynb`.

The judge must run all cells from the top.
For the sealed test, call `run_study` with tag `share_repurchase_program`, a start date, and an end date.

## 1. Hypothesis

The category is `share_repurchase_program`.
The company is in `TOP_100`.

After this 8-K, the market trade is to buy an at-the-money call.
A test of that trade failed.
Costs removed the edge.

After the 8-K, the chain gives an implied move of 13 percent to expiry.
The realized move to expiry is 10 percent.

Do not buy the call.
If you hold the stock, sell one call.
The call is 5 percent out of the money.
This strategy is the covered call.
`ENTRY` is `post`.
The expiry bucket is `3-6m`.
`OTM_PCT` is 0.05.
Do not change this strategy after the scoreboard.

## 2. Method

One event is one pair of `cik` and `filing_date` on `TOP_100`.

The notebook reads the chain on `t_pre`.
A mark is the last trade.
A mark is not valid after 3 sessions.
Spot is from put-call parity.

Profit and loss is the change of the strategy for each 1 of spot.
The notebook calculates all five strategies and all eight horizons.

The placebo uses 120 sessions for the same companies.
Each placebo session is 30 days or more from an 8-K.

In-sample: 2024-01-01 to 2025-12-31.
Out-of-sample: 2026-01-01 to 2026-08-31.
`RUN_HOLDOUT` is false.

If EDGAR accepts the 8-K at 16:00 ET or after, `t_0` is the next NYSE session.
`run_study` uses the same rule.
20 of 36 in-sample events moved (56 percent).
9 of 14 out-of-sample events moved (64 percent).

## 3. Result

The in-sample set has 31 events.
The out-of-sample set has 13 events at short horizons and 7 events to expiry.

The table shows the average profit and loss of the covered call for each 1 of spot.
A star means that the 95 percent interval does not contain 0.

| Horizon | In-sample average | In-sample 95 percent interval | Difference from placebo | Out-of-sample average |
|---|---:|---:|---:|---:|
| 1 | +0.44%* | [+0.00, +0.88] | +0.16% | +0.18% |
| 2 | +0.14% | [-0.48, +0.74] | -0.38% | +0.37% |
| 3 | +0.05% | [-0.58, +0.68] | -0.65% | +0.18% |
| 5 | -0.12% | [-0.92, +0.66] | -1.04%* | -0.47% |
| 10 | -0.19% | [-1.42, +0.99] | -1.25% | -0.59% |
| 21 | +0.04% | [-1.50, +1.61] | -1.71% | -1.68% |
| 42 | +3.55%* | [+1.77, +5.32] | +0.81% | -4.23% |
| 63 | +3.98%* | [+1.01, +6.43] | -0.17% | -8.13%* |
| expiry | +6.38%* | [+3.31, +9.13] | +1.35% | -3.92% |

At horizon 21 the in-sample average is 0.04 percent.
The 95 percent interval contains 0.
The difference from the placebo is -1.71 percent.

The long call is worse than the placebo at horizons 2, 3, 5, 10, 21, and 63.
The notebook does not change to the collar.

In 2026 the covered call is below 0.
The covered call is above the stock and above the long call.

A cost of 5 percent of premium on each side is 0.48 percent of spot.
The net average at horizon 21 is -0.44 percent.

## 4. Failure modes

The sealed window will not show extra profit at horizon 21 against other days.

Causes:
- More than half of these 8-Ks are accepted after 16:00 ET.
- The placebo test fails at horizon 21.
- The sample is small. Near 30 events in-sample. Near 10 events out-of-sample. 26 companies.
- The 2024-2025 increase to expiry does not occur in 2026.
- Last-trade marks. No dividend. No earnings flag. Fixed `TOP_100`.

## 5. Trade rule

Do not buy a call on this 8-K.

If you hold the stock:

1. Enter at the close of `t_0` after the acceptance-time rule.
2. Sell the call that is 5 percent above spot. Use an expiry of 90 to 180 days.
3. Do not sell more than 10 percent of the volume of that session.
4. Hold 42 sessions or to expiry. Do not exit at 21 sessions.

If you do not hold the stock, do not trade the event.
