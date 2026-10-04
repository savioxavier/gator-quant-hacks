# Guide to the reported results

This page explains recurring terms in the [full report](../report/REPORT.md). It is a reading aid; the report, preregistration, and result files contain the full definitions and evidence.

## Study outcomes at a glance

- **Daily Fed-communication strategy (v2):** the selected T4xE1 combination did not pass its preregistered decision rule. Its full in-sample Sharpe at twice the modeled trading costs was 0.387, below the required 0.5. The out-of-sample window was evaluated once under deviation D-3 for reporting; that result cannot reverse the failed rule.
- **Press-conference H1:** the primary test received a NO-GO under its preregistered gate. The estimate was small and statistically uncertain; see the report and the detailed H1 tables for the sample, confidence interval, and p-value.
- **Voice and face H2-H4:** these were exploratory tests after H1's NO-GO. The report describes H2 and H4 as not detected and H3 as stopped by its variance gate. They do not overturn H1 or establish a trading strategy.

## Common terms

| Term | Meaning in this project |
|---|---|
| **Preregistration** | A dated record of hypotheses, choices, and decision rules committed before the relevant results were examined. Later changes and permitted analyses are recorded as amendments or deviations. |
| **In-sample (IS)** | The data used for strategy selection and validation under the registered design. For v2, selection is 2016-01-04 through 2020-12-31, validation is 2021-01-01 through 2024-10-02, and full IS combines them. |
| **Out-of-sample (OOS)** | A later period held outside the v2 selection and validation windows: 2024-10-03 through 2026-10-02. It was evaluated once for reporting under D-3 after the registered decision rule had failed. |
| **Sharpe** | In the result tables, annualized mean divided by standard deviation of daily excess returns. It summarizes risk-adjusted historical returns; it is not a guarantee or a significance test. |
| **Net 1x / net 2x costs** | Returns after modeled trading costs at the standard cost estimate or at twice that estimate. The project's exact cost rules, including which non-trading costs are not doubled, are in the backtest documentation. |
| **Gross** | Returns before modeled transaction and borrowing costs. Gross performance is not the same as an implementable result. |
| **NO-GO / failed gate** | The preregistered threshold for proceeding or claiming support was not met. A positive point estimate alone does not change that decision. |
| **Not detected** | The analysis did not find sufficient evidence under its specified test. This does not prove that the effect is exactly zero. |
| **Exploratory** | An analysis designated as exploratory in advance of its own feature/result stage; it is not confirmatory evidence and cannot rescue a failed primary test. |
| **Variance gate** | A preregistered quality check on the face feature. H3 failed this gate, so its composite was not treated as a valid detected effect. |

## Interpreting the v2 out-of-sample number

The report gives T4xE1 an OOS Sharpe of 0.607 net of standard costs and 0.544 at twice costs. Read those alongside the registered failure: the full-IS Sharpe at twice costs was 0.387, below the 0.5 threshold. The OOS period was opened once under D-3 for descriptive reporting, and the report notes that its positive return was concentrated late in the window. It is not a second chance to pass the failed gate.

## Where to verify

- Combined outcome tables: [`backtests/results/summary.md`](../backtests/results/summary.md)
- Detailed v2 tables and decision record: [`backtests/results/v2/`](../backtests/results/v2/)
- One-time OOS result and run record: [`backtests/results/v2_oos/`](../backtests/results/v2_oos/)
- H1 tables: [`backtests/results/presser_h1/`](../backtests/results/presser_h1/)
- Protocol and amendments: [`preregistration/`](../preregistration/)
- Full methods, interpretation, and limitations: [`report/REPORT.md`](../report/REPORT.md)
