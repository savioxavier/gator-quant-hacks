# trend_momentum_fx_xsmom: currency momentum across G10 FX futures (Menkhoff-Sarno-Schmeling-Schrimpf)

Pre-registered 2026-10-03 before computing. Common conventions: ../COMMON_SPEC.md.

## Source rule (in our words)
Menkhoff, Sarno, Schmeling & Schrimpf (2012, Journal of Financial Economics 106(3), "Currency momentum
strategies"; BIS WP 366): at the end of each month sort currencies on their past f-month excess return (spot
change plus interest differential), f = 1, 3, 6, 9, 12; go long the top portfolio (winners) and short the bottom
portfolio (losers), equal weights, hold h months. The 1-month formation / 1-month holding strategy is the
strongest.

- URLs: https://www.bis.org/publ/work366.pdf ; https://www.cxoadvisory.com/momentum-investing/momentum-investing-for-currencies
- Source sample: up to 48 currencies, January 1976 - January 2010, six portfolios.
- Reported: winner-minus-loser spread up to about 10%/yr gross; the best strategies about 4%/yr after
  transaction costs; returns concentrated in less liquid, higher-risk currencies; weak among developed
  currencies.
- Post-publication evidence: AQR VME FX momentum (gross, our calc) 0.33 for 1972-2011 vs -0.04 post-publication
  (2013-07..2026); AQR Century currencies momentum -0.14 for 2012-2026.

## Our implementation
- Universe: F_6E F_6J F_6B F_6A F_6C F_6S (futures excess returns embed the interest differential).
- Month-end t: rank eligible currencies (require all >= 4 eligible) by cumulative excess return over the
  formation window: 21 sessions (V1), 63 (V2), 252 (V3).
- Long the top 2, short the bottom 2, equal risk (w = +/- 0.40/sigma_i/4), book to 10% (gross cap 3), hold to
  next month-end, next_close. FX futures cost 1 bp one-way.
- Common eligibility (>= 260 sessions) for all three variants so they share one window.
- Headline: best in-sample net Sharpe of V1-V3.

## Adaptations and likely effect
- 6 liquid G10 USD crosses instead of 48 currencies; MSSS report the effect is weakest in developed, liquid
  currencies -> expect a Sharpe near zero. Top/bottom 2 of 6 = terciles, not quintiles.
- 2011-2024 is entirely post-publication.
