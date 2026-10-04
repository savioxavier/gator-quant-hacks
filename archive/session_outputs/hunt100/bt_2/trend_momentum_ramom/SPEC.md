# trend_momentum_ramom: pre-registration (written 2026-10-03, before any computation of this strategy)

## Source rule (in my words)
Source: Dudler, Gmuer, Malamud, "Risk-Adjusted Time Series Momentum", Swiss Finance Institute RP 14-71 (2014,
revised 2015), https://ideas.repec.org/p/chf/rpseri/rp1471.html (SSRN 2457647). Only the abstract was retrievable in
this session (SSRN returns 403 to scripted downloads; the OpenAlex and Semantic Scholar APIs were rate-limited), so the
exact normalisation below is the hunt's pre-registered reading of the abstract:
RAMOM strategies "are based on averages of past futures returns, normalized by their volatility"; tested on 64 liquid
futures; they beat the Moskowitz-Ooi-Pedersen TSMOM for almost all look-back/holding combinations, with about 40%
lower dollar turnover, and have built-in exposure to MKT, HML and UMD.

## Source sample and reported numbers
64 liquid futures (commodities, equity indices, bonds, currencies), period to about 2013. Reported (abstract): RAMOM >
TSMOM for almost all (look-back, holding) pairs; dollar turnover about 40% lower than TSMOM. No Sharpe numbers were
retrievable; no post-publication record found.

## Our implementation (futures, gqh engine)
* Universe: the 30 CME futures; data from 2010-06-07 (RTY from 2017-07-10).
* At each month-end close t (last NYSE session), for each eligible future and look-back L sessions:
  z_L = sum of the last L daily excess returns / (sample std of those L returns * sqrt(L))  (t-stat of the mean);
  x_L = clip(z_L / 2, -1, 1)  (scale constant 2 fixed a priori).
* w_i = x_i * 0.40 / sigma_i / N_eligible, sigma_i = sqrt(252 EWMA(r^2, com 60)); book rescaled to 10% ex-ante vol
  with the trailing 252-session covariance (min 60), gross <= 3; filled next_close; held to the next month-end.
* Eligibility: >= 260 sessions of history, positive EWMA vol, traded in the last 10 sessions, and at least L
  non-missing returns in the look-back.
* Costs: realistic one-way map of the hunt task, roll days add a round trip; 2x stress reported.

## Pre-declared variants (all reported)
* V1: L = 252.
* V2: L = 63.
* V3: x = average of x_L over L in {21, 63, 126, 252}.
* Non-selectable diagnostic: MOP sign TSMOM with L = 252 (x = sign of the 252-session cumulative excess return, same
  sizing) to check the source's relative claims (Sharpe and the about 40% lower turnover). Never selected.
* Selection for the standard series: highest in-sample net Sharpe (1x costs).

## Windows
In-sample: first live session (decisions from 2011-06-30) through 2024-10-02. 2024-10-03..2026-10-02 descriptive only.

## Adaptations and likely effects
* 30 CME futures from 2011 instead of 64 futures from the 1980s; post-2011 trend returns were weak industry-wide,
  so expect low absolute Sharpe whatever the signal.
* The clipped continuous t-stat is our implementation of "average returns normalised by volatility"; if the paper
  uses EWMA volatility or a different holding period the numbers will differ somewhat, the ranking vs sign-TSMOM
  should not.
* Book scaling to 10% ex-ante vol is our common framework (the paper's sizing is not known to us).
