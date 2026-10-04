# trend_momentum_turtle_donchian (pre-registered 2026-10-03, before computing)

Common conventions: ../COMMON_SPEC.md.

## Source rule (in my words)
"The Original Turtle Trading Rules" (originalturtles.org, 2003),
https://oxfordstrat.com/coasdfASD32/uploads/2016/01/turtle-rules.pdf; supporting evidence Szakmary, Shen and Sharma
(2010, JBF) https://ideas.repec.org/a/eee/jbfina/v34y2010i2p409-426.html; breakout rule family in
https://github.com/robcarver17/pysystemtrade.
- N = 20-day exponential (Wilder) moving average of the true range: N_t = (19 N_{t-1} + TR_t) / 20.
- Unit = 1% of account equity per 1 N of price movement.
- System 1: enter when price exceeds the 20-day high (long) or 20-day low (short); exit longs at a 10-day low, shorts
  at a 10-day high. Skip a System 1 breakout if the last breakout in that market (taken or not, either direction)
  would have been a winner; a breakout is a loser if price moved 2N against it before a profitable 10-day exit.
  If a breakout was skipped, enter at the 55-day breakout instead (failsafe).
- System 2: enter at the 55-day high/low, exit at the 20-day low/high; all breakouts taken.
- Stops: 2N from entry; units added at +N/2 intervals up to 4 units, earlier stops raised so that all stops sit 2N from
  the latest unit.
- Turtles traded intraday at the breakout; no backtest numbers are given in the rules. Reported evidence: Szakmary et
  al. 2010: channel and dual-MA rules net of costs positive in at least 22 of 28 commodity futures over 48 years
  (1959-2007), robust across subperiods and data-snooping tests; breakout is one of the rule families in Carver's
  live multi-rule account (Sharpe 0.76, 2014-2025); Lemperiere et al.: very short trends faded after 2003.

## Our implementation (daily decisions, next_close)
- Channels on the close of the excess-return index: long entry when close_t > max(close over the prior 55 (S2) /
  20 (S1) sessions), short entry when close_t < the prior min; exit long when close_t < min of the prior 20 (S2) /
  10 (S1) closes, exit short when close_t > the prior max.
- N/close from the aggregated front-contract OHLC (true range with the same-contract previous close; Wilder EMA 20,
  seeded with the first 20-day mean TR), lagged one session. Reference (entry) price = the decision close of the
  index; stop level = ref * (1 - 2 * nrel) for longs, ref * (1 + 2 * nrel) for shorts, nrel = N/close at entry;
  stop checked on closes (exit when close_t crosses the stop).
- Raw weight per unit = 0.01 / nrel_entry (fixed at the unit's entry); weights of all markets then booked to 10%
  ex-ante every session (trailing 252-session covariance, gross <= 3).
- The state machine runs from the start of each index; weights are zero while a market is ineligible.
- System 1 skip filter: a hypothetical System 1 trade is opened at every System 1 breakout when no hypothetical trade
  is open; it closes at the 10-day exit (winner if the exit close is beyond the entry close in the trade direction,
  else loser) or at the 2N stop (loser). A real System 1 entry is taken only if the last closed hypothetical trade was a
  loser (or none exists); when the real book is flat and a 55-day breakout occurs, the failsafe entry is taken; real
  System 1 and failsafe positions exit at the 10-day exit or the 2N stop.

## Variants (all reported; headline = best in-sample net Sharpe 1x)
- V1: System 2 (55/20), single unit, 2N stop.
- V2: System 1 (20/10) with the skip filter and the 55-day failsafe, single unit, 2N stop.
- V3: System 2 with pyramiding: add one unit each time the close is >= N/2 beyond the previous unit's reference
  (several units in one day allowed, at the theoretical levels ref + k*N/2), max 4 units; all stops 2N from the latest
  unit; N fixed at the initial entry.

## Adaptations and likely effect
- Close-based channels and stops on the total-return-derived index instead of intraday highs/lows and stop orders on
  the outright contract: entries/exits one session later than intraday fills; usually costs a little performance in
  fast breakouts and avoids some intraday whipsaws.
- The 1%-per-N unit and the turtles' 12/10-unit portfolio limits are replaced by the 10% book scaling (the relative
  weights stay inverse to N/close).
- The failsafe (part of the source rule, not in the candidate one-liner) is included in V2.
- Expect correlation with S1 > 0.5 for V1/V3; System 1 is the faster rule the literature flags as decayed.
