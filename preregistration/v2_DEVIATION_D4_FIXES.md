# v2 deviation D-4: two implementation fixes and matched benchmarks, after the results were seen

Written 2026-10-04 at about 05:30 UTC, after v2's in-sample results and its one D-3 out-of-sample evaluation were
seen, and after two external reviews. Nothing below changes the registered decision: v2 failed its decision rule and
that verdict stands. The committed results stay the first, reported results; everything computed under this note is
shown next to them and labelled corrected or descriptive.

## Defects (confirmed in the code)

1. **Sizing timing (E1).** `backtests/v2/v2lib.py`, `weights_E1`: the volatility used to size the position entered
   at the open of session t includes the open-to-open return ending at open t, which is the fill price, and the
   weight is stored as the decision of session t-1. An order for the opening auction cannot know that price.
   Inherited from strategy 01's construction ("Variant A exactly").
2. **Overnight drift (engine).** The shared engine (gqh-flow-clock `src/engine.py`, `simulate`, `exec="next_open"`)
   applies the previous open's target weights to the close-to-open return, ignoring how the previous day's intraday
   move changed the weights held at the close. This acts as an uncharged rebalance to target at every close; the
   turnover calculation also misses that intraday drift.

## Fixes

1. Size the position entered at the open of session t with volatility from returns that end no later than the close
   of session t-1 (the information available before the opening auction). Nothing else in the sizing changes
   (target, floor, clip, cap, band, FOMC rule).
2. Simulate holdings as shares and cash: the target set at the open is bought at the open, the shares drift with the
   intraday and overnight moves, and the next open's trade (and its cost) is measured from the drifted holdings.
   Borrow and the T-bill accrue as before.

Both fixes are switches; with them off, the committed results reproduce exactly. The frozen committed files are not
changed. The gqh-flow-clock repository is not changed; the fixed simulation lives in the team repository.

## What is computed (all descriptive; no combination is re-chosen)

- T4xE1 and Variant A (T0fxE1), in-sample windows and the out-of-sample window, with fix 1, fix 2 and both.
- The portfolio test with the corrected T4xE1 sleeve. The core_ER_6 sleeves are kept as committed (they come from
  other pipelines); this limitation is stated with the result.
- Matched component benchmarks, same documents, processing, sizing and costs as T4xE1's legs: the all-document
  lexicon signal alone (LEXALL x E1), the stance model alone on all documents (T2 x E1, already computed), and the
  2015-warm-up lexicon reference T0v2 x E1, each with and without the fixes, in- and out-of-sample.
- Simple benchmarks with the same sizing and costs: the rate-momentum signal used by T3 traded alone, and
  buy-and-hold of the same 75/25 TLT/UUP mix.
- Walk-forward selection (robustness, post hoc): at each year-end from 2020, choose the combination with the highest
  trailing net Sharpe among the registered eight and trade it for the next year; report the chained result.

These rows cannot change the verdict and carry no inferential weight for the registered hypothesis; they answer the
reviewers' questions about implementation and about what the stance model adds.
