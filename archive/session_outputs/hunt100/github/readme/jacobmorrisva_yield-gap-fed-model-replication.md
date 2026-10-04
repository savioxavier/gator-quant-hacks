# Yield Gap / "Fed Model" Replication

An independent research project for FNAN 498 (Contemporary Topics in Finance) at
George Mason University, replicating and extending Maio (2013) to test whether
the "yield gap," the S&P 500 earnings yield minus the 10-year Treasury yield,
predicts future U.S. stock market returns.

## Research question

Does the yield gap between equity earnings yields and Treasury yields predict
future stock market returns across multiple forecast horizons?

## Data

Monthly U.S. financial market data, January 2005 through November 2025:

- **Earnings yield (E/P)** — constructed from S&P 500 earnings and price data,
  Robert Shiller's online data library
- **10-year Treasury yield** — FRED (DGS10 series)
- **Market returns** — Kenneth French Data Library (Mkt-RF and risk-free rate)

## Methodology

Followed Maio (2013)'s predictive regression framework:

```
Future Return_t = α + β(Yield Gap_t) + ε_t
```

Regressions and correlation analysis were run across five forecast horizons: 1,
3, 6, 9, and 12 months, using compounded future returns for the multi-month
horizons.

## Finding

The yield gap held a **positive but statistically insignificant** relationship
with future returns at every horizon tested, a notably weaker result than
earlier studies (including the original Maio 2013 paper) found. R-squared values
stayed below 1% even at the 12-month horizon. The paper discusses why this
predictive relationship has weakened in modern markets, pointing to prolonged
low interest rate policy and quantitative easing since the 2008 financial
crisis as a likely explanation, rather than treating the null result as a dead
end.

## Contents

- `Yield_Gap_Fed_Model_Presentation.pptx` — presentation summary
- `Yield_Gap_Fed_Model_Research_Paper.docx` — full research paper (literature
  review, methodology, regression results, discussion)
- `Data/` — all source data used in the analysis
- `Reference Source/` — the Maio (2013) paper this project replicates

## Tools

Excel (regression analysis, descriptive statistics)

---
Jacob Morris
