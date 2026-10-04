# SPEC: factor attribution of v2 and paired bootstrap of the portfolio increment

Fixed on 2026-10-04 before `attribution.py` computed any regression, correlation or bootstrap resample. The script
refuses to run unless this file's sha256 equals the value it carries, so a later edit to this file shows.

**Status: exploratory, post-result.** v2's in-sample result, its one D-3 out-of-sample (OOS) evaluation and the D-4
corrected rows were all published and read before this was written, including the Sharpe ratios that enter the
observed differences below. This note fixes the method before this script computes anything. It does not make the
analysis confirmatory, and it carries no inferential weight for the registered hypothesis. The registered verdict
stands: v2 FAILED its decision rule.

No backtest is run or rerun. Only committed daily return series are read. Outputs hold statistics of published
strategy and benchmark return series only: no price levels and no raw asset return series.

## Inputs (read only)

| file | use |
|---|---|
| `backtests/results/v2_d4/daily_returns.parquet` | every series below (full-period run, daily excess returns over the 3-month T-bill) |
| `backtests/results/v2_d4/metrics.csv` | cross-check: published n_days, Sharpe and Newey-West t |
| `backtests/results/v2_oos/daily_returns.parquet` | cross-check: the frozen D-3 originals must equal the `original` columns used here |

If any input is missing, the script exits non-zero and writes nothing. It also exits non-zero if a cross-check
fails: window row counts or dates differ from `metrics.csv`, an original series differs from the frozen D-3 file
by more than 1e-12, or a recomputed published Sharpe or NW t differs by more than 1e-9.

## Windows

- **full IS:** rows labelled `selection` or `validation`, 2016-01-04 .. 2024-10-02 (2202 sessions expected).
- **OOS:** rows labelled `oos`, 2024-10-03 .. 2026-10-02 (501 sessions expected).

The one `pre_selection` row (2015-12-31) is excluded. Each window is analysed on its own; the two are never pooled.

## Part A: factor attribution of v2

**Dependent variables.** Daily net-1x excess return of T4xE1 (v2):

- `original`: `T4xE1|original|net_1x`, which must equal the frozen D-3 series;
- `both`: `T4xE1|both|net_1x`, the D-4 both-fixes series.

**Factors, primary set** (the same set for both dependents, all net 1x):

| name | column | meaning |
|---|---|---|
| DUR_USD | `BH7525hold\|hold\|net_1x` | long 75% TLT / 25% UUP, bought at the open of 2015-12-31, never rebalanced, unlevered. Duration and dollar exposure in one fixed long-long mix |
| MOM | `MxE1\|both\|net_1x` | the rate momentum signal of T3 (M) traded alone with E1 sizing and costs, both fixes. Same sign convention as v2: rising 2-year yields = hawkish = short TLT, long UUP |
| LEX | `LEXALLxE1\|both\|net_1x` | the lexicon-only matched series (all documents, same processing, sizing and costs as T4's lexicon leg), both fixes |

**Prespecified sensitivity S1 (original dependent only).** Factors with matching variants: `MxE1|original`,
`LEXALLxE1|original`, and DUR_USD unchanged. This is not run for the `both` dependent, where S1 equals the primary
set.

**Models.** OLS with an intercept, for each dependent, factor set and window:

- M0: intercept only. This gives the NW t of the mean, which must reproduce `metrics.csv` `nw_t`.
- M1: DUR_USD.
- M2: MOM.
- M3: LEX.
- M4: DUR_USD + MOM + LEX.

**Inference.** Newey-West HAC covariance, Bartlett weights 1 - k/(L+1) for k = 1..L, with
L = floor(4 (n/100)^(2/9)) and n the window's observation count. No small-sample degrees-of-freedom correction is
applied, which is the convention of `v2lib.nw_t`. Each t is the coefficient divided by its HAC standard error.

**Reported per model:**

- n, start and end dates, and L;
- alpha per day and alpha annualised (252 x daily intercept, arithmetic, excess-return units), with alpha's t;
- each beta and its t;
- R^2 and adjusted R^2, and residual vol annualised (sd x sqrt 252, ddof = number of regressors + 1);
- the dependent's arithmetic annualised mean, and alpha_ann / mean_ann.

**Correlations.** Pearson correlation matrix of the daily series, one per window: v2 original, v2 both, DUR_USD,
MOM (both), LEX (both), MOM (original) and LEX (original).

**Reading rules, fixed now.**

- Joint model M4: R^2 >= 0.50 reads as "mostly explained by these three series"; 0.10 <= R^2 < 0.50 as "partly
  explained"; R^2 < 0.10 as "mostly not explained".
- "v2 is mostly duration/dollar exposure" is said only if the M1 R^2 is >= 0.50. "Mostly momentum" needs the same of
  M2, and "mostly its lexicon leg" the same of M3.
- An alpha or beta with |t| < 1.96 is described as not distinguishable from zero. Nothing further is claimed from it.

**Known limitations, stated in advance.**

1. DUR_USD cannot separate duration from dollar. It is one fixed long-long mix, and the rules allow no raw TLT or UUP
   series in the outputs. TLT is far more volatile than UUP, so the mix mostly carries duration.
2. T4 is the average of the lexicon z and the stance z. LEX therefore shares half of v2's signal by construction. Its
   beta measures how much of v2 behaves like its own lexicon leg; it is not an external risk factor.
3. MOM and LEX are strategies with E1 sizing, not passive factors. The betas describe co-movement with those
   strategies.

## Part B: paired block bootstrap of the portfolio Sharpe increment

**Pair.** P1 = `core_ER_6+T4xE1|<variant>|<basis>` and P0 = `core_ER_6|as_committed|<basis>`, on the same dates:

- variants `original` and `both`;
- windows OOS (primary) and full IS (secondary).

**Statistic.** D = Sharpe(P1) - Sharpe(P0), with Sharpe = mean / sd (ddof 1) x sqrt(252), as in `v2lib.sharpe`.

**Resampling.** Circular block bootstrap (Politis and Romano 1992). For a window of n sessions and block length b,
each resample concatenates ceil(n/b) blocks of b consecutive rows and truncates the result to n rows. Each block
starts at an independent uniform position in 0..n-1 and wraps from the last row to the first. The same row indices
are applied to P1 and P0, so the daily rows are resampled as pairs.

- b = 20 sessions is primary; b = 10 and b = 40 are sensitivities.
- 10,000 resamples per configuration.
- For each (window, b), a fresh `numpy.random.Generator(PCG64(20261004))` draws the indices. The same indices serve
  both variants and both bases (common random numbers).
- Basis: net 1x is primary; net 2x is a sensitivity.

**Reported per configuration:**

- n, start and end dates;
- the observed Sharpe of P1 and P0 and the observed D;
- the bootstrap mean and sd of D;
- percentile intervals of D: 90% (5th to 95th percentile) and 95% (2.5th to 97.5th), using numpy's default linear
  quantiles;
- the share of resamples with D <= 0.

**Contrast, not a bootstrap.** NW t (same lag rule, same estimator) of the mean of P1, of P0 and of the daily
difference P1 - P0. The published `nw_t` of P1 and P0 in `metrics.csv` is cross-checked. The portfolio's own NW t
tests whether its mean excess return is above zero. D asks whether adding v2 raised the Sharpe ratio relative to
core_ER_6 alone. These are different questions, and the write-up keeps them apart.

**Reading rules, fixed now.**

- The increment is called distinguishable from zero at the 10% (5%) two-sided level only if the 90% (95%) percentile
  interval excludes 0.
- The share of resamples with D <= 0 is reported as a descriptive one-sided bootstrap proportion, not as a p-value.

## Outputs (written only to `results_2/attribution/`)

| file | content |
|---|---|
| `attribution.py` | the computation; run from the repository root |
| `factor_attribution.csv` | one row per dependent x factor set x window x model |
| `correlations.csv` | the correlation matrices, long format |
| `bootstrap.csv` | one row per window x variant x basis x block length |
| `ATTRIBUTION.md` | this SPEC verbatim at the top, then every result, labelled exploratory, post-result |
