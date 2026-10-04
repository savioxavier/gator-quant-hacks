# trend_momentum_sector_rs: sector relative-strength rotation (Faber 2010) on SPDR sector ETFs

Pre-registered 2026-10-03 before computing. Common conventions: ../COMMON_SPEC.md.

## Source rule (in our words)
Faber (2010, "Relative Strength Strategies for Investing", SSRN 1585517): each month-end rank the ten US
industry sectors (French 10 industries) by trailing total return - the headline ranking averages the 1, 3, 6, 9
and 12-month returns - and hold the top 1, 2 or 3 sectors equally weighted for the next month. An optional
trend filter holds T-bills instead when the market is below its 10-month simple moving average.

- URLs: https://c.mql5.com/forextsd/forum/213/Relative%20Strength%20Strategies%20for%20Investing.pdf ;
  https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/10_Industry_Portfolios_CSV.zip
- Source sample: French 10 industry portfolios, 1928-2009.
- Reported: relative-strength portfolios beat buy-and-hold in about 70% of years; top-3 rotation earns a few
  percent per year above the equal-weight sector index with similar volatility; the trend filter cuts
  drawdowns.
- Our calc on French 10 VW industries (gross, hunt): top3 minus EW10 Sharpe 0.43 for 1928-2009, 0.30 for
  2010-01..2026-08 (post-publication), 0.47 for 2016-01..2024-09; top3 excess Sharpe 0.89 vs EW10 0.84
  post-2010, 0.82 vs 0.70 over 2003-2024-09; Moskowitz-Grinblatt 6m top3-bottom3 0.42 (1963-95) vs 0.25
  after 1999-08.

## Our implementation
- Universe: XLB XLE XLF XLI XLK XLP XLU XLV XLY (adjusted OHLC, etf_daily; engine history from 2005-01-03).
- Month-end t: score_i = mean over k in {1,3,6,9,12} of (close_i(t) / close_i(month-end k months before t) - 1),
  using month-end adjusted closes. Rank all 9 (all have data from 2005).
- V1: long the top 3 at 1/3 each, 100% invested, natural sizing (no vol scaling).
- V2: V1, but hold T-bills (all weights 0) when SPY's month-end close is below the mean of its last 10
  month-end closes (including the current one).
- V3: top 3 at +1/3 each minus bottom 3 at -1/3 each, book to 10% (trailing 252-session covariance of ETF daily
  excess returns, gross cap 2); shorts pay 30 bp/yr borrow.
- All: decisions at the month-end close, next_open fills, ETF cost map (sector SPDRs 5 bp one-way).
- First decision needs a month-end 12 months earlier inside the engine history (first month-end 2005-01-31):
  first decision 2006-01-31; common start =
  first session on which all variants hold positions (V2 can be in T-bills; its start is counted by V1).
- Headline: best in-sample net Sharpe of V1-V3.

## Adaptations and likely effect
- 9 SPDR sectors (S&P 500 sector definitions, cap-weighted, no telecom/real estate after 2018 changes) instead
  of the French 10 industries; XLK/XLY/XLC membership shifted in 2018 (GICS change) -> minor.
- Sample 2006-2024 is post-publication for the last 15 years; sector momentum has weakened post-publication
  in French data (0.30 vs 0.43 relative Sharpe).
- V1/V2 are long-only equity strategies; their Sharpe mostly reflects the equity premium, so the relevant
  comparison is against holding the equal-weight sector basket (reported as a diagnostic, not a variant).
