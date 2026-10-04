# Project documentation

Use this page to follow the study from its questions and commitments through its methods and reported results. The root [README](../README.md) gives a short project and directory overview.

## Follow the research

1. **Understand the questions.** Read the [full team report](../report/REPORT.md) for the hypotheses, data, methods, findings, and limitations.
2. **See what was committed in advance.** Start with the [preregistration log](../preregistration/PREREG_LOG.md), then read the [v2 hypothesis](../preregistration/HYPOTHESIS_v2.md) and the press-conference [addendum](../preregistration/presser_ADDENDUM.md). Later deviations and exploratory plans are recorded alongside them in `preregistration/`.
3. **Understand the stance model.** The [NLP guide](../nlp/README.md) describes walk-forward model training, source-document dating for labels, scoring, and leakage checks.
4. **Read the results with context.** The [results guide](results-guide.md) defines common metrics and summarizes how the decision rules affect interpretation. Detailed combined tables are in [backtests/results/summary.md](../backtests/results/summary.md).
5. **Check reproducibility requirements.** The [reproduction guide](reproduction.md) explains the maintained backtest runner, external inputs, and reproduction records.

## Research notes

`research/` contains planning, reviews, literature surveys, and data-feasibility notes. These are supporting work products; the report and preregistration files above are the best entry points for the final study design and claims.

| Path | Contents |
|---|---|
| [`research/fed_presser_plan/`](research/fed_presser_plan/) | Press-conference study plans, gap report, merged plans, and deviation notes. |
| [`research/fed_presser_hpg/`](research/fed_presser_hpg/) | Notes and reviews for the HiPerGator feature package; the package is in `hpg/fedpress_pkg/`. |
| [`research/fed_report/`](research/fed_report/) | Report review notes and drafts. |
| [`research/fedspeak_v2/`](research/fedspeak_v2/) | Working notes for v2; the operative preregistration is in `preregistration/`. |
| [`research/data_feasibility.md`](research/data_feasibility.md) | Data availability and feasibility checks. |
| `research/idea_literature.md`, `high_sharpe_literature.md`, `scholar_hf_findings.md` | Literature searches and findings. |
| `research/github_repos.md`, `local_strategies.md` | Repository and local-strategy surveys. |

The report cites committed results. Some reproduction inputs, including licensed market data and local bundles, are not committed; see the reproduction guide before attempting a run.
