# carry_value hunt: notes (2026-10-03)

Scope: carry, value and term structure. 26 candidates in `candidates_full.json` (summary list in `candidates.json`).
These rules, with at most three pre-declared variants each and the primary marked, were written before this
agent computed any return of them, so they serve as the pre-registration for the backtest stage. Choose among
variants on in-sample data only (through 2024-10-02).

## STD conventions (referenced by every rule)

* Instrument volatility sigma_i: EWMA of squared daily excess returns, centre of mass 60 sessions, annualised.
* Risk unit: 0.10 / sigma_i. Book rescaled to 10% annualised ex-ante volatility with the sample covariance of
  the trailing 252 daily excess returns of the held instruments (min 60), scale factor capped at 4. Spread books:
  add a per-leg notional cap of 3x NAV per root.
* Decisions at the close of the last NYSE session of the month unless the rule says weekly or daily;
  `engine.simulate(exec="next_close")` (held from the close of d+1). Rules using a 15:30 ET Friday COT release
  decide on the release session with `exec="next_open"`, or on the next session with next_close.
* Costs: the task map (ES/NQ/YM 1 bp, RTY 2, ZT 0.5, ZF 0.7, ZN 1, ZB/UB 1.5, FX 1, CL/GC/SI/HG 2, NG/HO/RB/PL 3,
  grains/livestock 4; ETFs 3/5/10 bp with 30 bp/yr borrow on shorts); 2x as stress; roll days one extra round
  trip; calendar spreads pay both legs at outright cost (no exchange-spread discount assumed).
* Near/far legs: from `edges/carry/contracts.parquet` (date, root, rank 0/1, instrument_id, close,
  deliv_year/month; symbology already resolved with the free endpoint). Near = earlier delivery, far = later
  delivery of the two most liquid contracts, gap at most 12 months. Same-contract daily leg return =
  close_t / close_{t-1} - 1 of the same instrument_id, using its previous close if it printed in either rank on
  t-1; otherwise the leg return is missing that day (spread return 0, position re-established).
* COT point-in-time: a report (Tuesday positions) is usable from the first NYSE session after its release
  (normally Friday 15:30 ET; 273 of 2,585 releases since 2010 were late). HF `ZipLime/commitments-of-traders`
  carries `release_at`; CFTC `deacot{YYYY}.zip` is the fallback (assume Friday, shift for federal holidays).
* Universes: COM15 = CL HO RB NG GC SI PL HG ZC ZS ZW ZL ZM LE HE; FX6 = 6E 6J 6B 6A 6C 6S;
  RATES5 = ZT ZF ZN ZB UB; EQ4 = ES NQ YM RTY.

CFTC contract market codes (legacy report; verify the market name when loading): CL 067651, HO 022651,
RB 111659, NG 023651, GC 088691, SI 084691, PL 076651, HG 085692, ZC 002602, ZS 005602, ZW 001602, ZL 007601,
ZM 026603, LE 057642, HE 054642; 6E 099741, 6J 097741, 6B 096742, 6A 232741, 6C 090741, 6S 092741;
ES 13874A, NQ 209742, YM 124603, RTY 239742; ZT 042601, ZF 044601, ZN 043602, ZB 020601, UB 020604.

## Evidence found (numbers verified from full text unless marked)

* Commodity curve spread (long deferred/short front): independent GitHub backtest `jjj1231978/QIS_Commodities`,
  17 CME BCOM roots, Databento, 2015-06-08..2026-05-04, net: carry F3-F0 Sharpe 1.15 (7.7%/yr, vol 6.7%,
  maxDD -7.2%), value 0.64, trend 0.08, congestion (Goldman-roll pre-roll) -0.30, basis momentum (63-day) -0.41.
  The repo quotes an unnamed bank QIS report: F3-F0 1.75, F6-F0 1.58, F6-F0 beta-hedged 1.86. Our data has only
  F0/F1, where the term premium per unit spread is smaller.
* Basis-momentum: Boons-Porras Prado (1960-2014, 21 commodities) High4-Low4 nearby 18.38%/yr (t 6.73), spreading
  4.08%/yr (t 6.43), Sharpe about 0.9 for both. Sakkas-Tessaromatis (JBF 2020, 38 commodities, 1970-2018):
  long-short Sharpe BM 0.930, basis 0.811, momentum 0.718, HP 0.243, value 0.136, open interest -0.03.
  Jiang-Liu (EFMA 2024, 1985-2022): basis 0.48, momentum 0.36, BM 0.43, HP 0.08. GitHub `ddxmy/Basis-Momentum`
  Goldman-style F0/F6 (252-day, weekly, 5 bp): 2008-01..2026-07 Sharpe 0.65; annual Sharpe 2019..2025:
  -1.35, 1.01, -1.04, 0.17, 0.31, 0.21, 0.76 (post-publication about 0.1). Its liquidity-ranked L0-L1 (120-day)
  2019-2026 Sharpe 0.96 (universe unclear, "main contract" wording suggests Chinese futures; parameter not sourced).
* Speculative pressure (Fan et al. JFM 2020, 1992-2018): COM 0.61, FX 0.47, EQ 0.50, FI -0.28, everywhere 0.55.
* Kang-Rouwenhorst-Tang: quintile spread 0.21% days 1-4 (pre-release), 0.30% days 5-10 (t 3.62), 0.15% days
  11-20; most of the effect is tradable only after the Friday release.
* Dollar carry: LRV developed 5.60%/yr, Sharpe 0.66 net of bid-ask (1983-2010); DHL 2017 G10 carry 0.78 (1976-2013).
* Ang-Chen (1975-2009, thirds): Change 0.470 / 0.449 (G10), corr with carry 0.06; long-rate change 0.548 / 0.519;
  term reversed 0.809 / 0.667 (corr 0.73 with carry).
* Curve carry: Beekhuizen et al. global 10-country 0.68 (Eurocurrency funding) / 1.13 (T-bill); US 0.11 / 0.52.
* AQR VME post-publication (2013-07..2025-01, verifier calculations in `edges/value_reversal/vme_check.json`):
  commodity value 0.57, commodity momentum -0.20, FX value -0.19, FX momentum -0.04, bond value -0.18,
  country equity value -0.06.
* Edge-study results (verified by its verifier, journal wf_0c251a33-56f): carry_xs_global IS 0.03 / later 0.30;
  carry_ts_global 0.25 / -0.24; carry_xs_rates 0.42 / 0.01 (mostly a static short-ZT/long-ZB tilt);
  carry_xs_comm 0.21 / 1.04 (C12 versions about 0); VAL_ALL -0.09 / -1.20; COMBO_ALL 0.23 / -0.60;
  commodity-only AMP value sleeve (verifier diagnostic) 0.45 / -0.63.
* Weak or negative: country 3-year reversal (Quantpedia OOS negative); natural-gas storage (no directional edge
  2015-2026); forward-rate bond timing (Thornton-Valente: no OOS value); dividend-yield timing (GWZ 2024).
* Marked "as recalled" in the records (not re-verified, web search budget exhausted): Frazzini-Pedersen Treasury
  BAB Sharpe about 0.8; Duarte-Longstaff-Yu yield-curve arbitrage results.

## Overlaps and items dropped

* Goldman-roll front-running (Mou 2011) is `calendar_event_goldman_roll_spread`; extra evidence for it: the
  QIS_Commodities congestion sleeve, 2015-2026 net Sharpe -0.30.
* Outright basis-momentum is `trend_momentum_basis_momentum`; here only the curve-neutral spread version.
* FX cross-sectional momentum is `trend_momentum_fx_xsmom`; short-term basis reversal is
  `trend_momentum_basis_reversal`; Durham curve momentum is `trend_momentum_durham_curve_xsmom`.
* Dropped for lack of a sourced rule or evidence: FX carry with a volatility filter, TFF positioning
  (asset managers vs leveraged funds), FX basis-momentum (paper: basis beats BM in currencies), gold real-yield.

## Data checks (2026-10-03)

Reachable: CFTC history zips, HF ZipLime COT, EIA weekly xls, Shiller ie_data.xls, treasury.gov par curve CSV,
OECD SDMX CPI, Ken French, yfinance (country ETF dividends from 1996). FRED fredgraph.csv timed out from this
host (90 s), so DGS5/DGS7/DGS20 and foreign CPI/rates should come from treasury.gov, OECD or the Fed GSW file;
local fred_daily already has DTB3, DGS2, DGS10, DGS30, T10Y2Y.

## Files

* `candidates_full.json`: the 26 complete records (schema of the hunt).
* `candidates.json`: id/name/family/primary-variant list.
* `urls.txt`: every URL consulted and the data endpoints checked.
* `papers/`: PDFs and extracted text of the papers read in full.
