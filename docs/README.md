# Documentation

Every guide, report and results write-up for the project is in this folder. For the overview, setup and run commands,
see the [root README](../README.md).

## Read in this order

1. **[Report](report/REPORT.md)**: the full team report. It covers the hypothesis, data, method, results,
   robustness, failed and exploratory work, and limitations. Teammates compile the PDF from it.
2. **[Results guide](guides/results-guide.md)**: what Sharpe, net 1x/2x, NO-GO, "not detected" and the other terms
   mean here.
3. **[Pre-registration log](../preregistration/PREREG_LOG.md)**: what was committed, and when, before each result.
4. **[Reproduction](guides/reproduction.md)**: what can be reproduced, and from which inputs.

## Folders

### `report/`

| File | What it is |
|---|---|
| [REPORT.md](report/REPORT.md) | the full report |
| [REPORT_DRAFT.md](report/REPORT_DRAFT.md) | the earlier draft, kept for reference |

### `submission/`

| File | What it is |
|---|---|
| [devpost_description.md](submission/devpost_description.md) | the Devpost page text: elevator pitch, project story, built-with tags |
| [submission_status.md](submission/submission_status.md) | the status of every submission item, reporting conventions, and which commits hold the results |
| [reproduction_commands.md](submission/reproduction_commands.md) | the two reproduction paths (public replay, full backtest), their inputs and exact commands |

### `guides/`

| File | What it covers |
|---|---|
| [data.md](guides/data.md) | every dataset: source, licence, whether it is committed, how to obtain the private files (with SHA-256), and what each data folder holds |
| [running-backtests.md](guides/running-backtests.md) | `backtests/run_all_backtests.sh`: stages, environment variables, local and HiPerGator runs, data rules |
| [reproduction.md](guides/reproduction.md) | which workflow needs which inputs; reading the frozen records |
| [saved-result-replay.md](guides/saved-result-replay.md) | `results_2/replay/replay.py`: the public replay of the headline tables |
| [v2-strategy.md](guides/v2-strategy.md) | the v2 strategy: verdict, deviations D-3 and D-4, the one-shot out-of-sample lock, implementation choices |
| [stance-model.md](guides/stance-model.md) | the walk-forward chrono-BERT stance model: label dating, training, scoring, runtimes |
| [stance-score-wiring.md](guides/stance-score-wiring.md) | how stance scores are wired into the v2 and press-conference backtests |
| [hipergator.md](guides/hipergator.md) | HiPerGator jobs: recordings download, feature build, stance-model chain |
| [results-guide.md](guides/results-guide.md) | how to read the results |

### `results/`

| File | What it is |
|---|---|
| [strategy-results.md](results/strategy-results.md) | every strategy result, with its source file |
| [sharpe-summary.md](results/sharpe-summary.md) | one page of Sharpe ratios |
| [reviewer-gap-coverage.md](results/reviewer-gap-coverage.md) | each external-review point, the file that resolves it, and its status (the `results_2/` analyses) |
| [h234-local-summary.md](results/h234-local-summary.md) | the local replication of the exploratory H2/H3/H4 tests |

### `research/`

Supporting work: planning, reviews, literature surveys and data-feasibility notes. The report and the
pre-registrations are the authoritative statements of the final design and claims.

| Path | Contents |
|---|---|
| [research/fed_presser_plan/](research/fed_presser_plan/) | press-conference study plans, gap report, merged plans and deviation notes |
| [research/fed_presser_hpg/](research/fed_presser_hpg/) | notes and reviews for the HiPerGator feature package |
| [research/fed_report/](research/fed_report/) | report review notes and drafts |
| [research/fedspeak_v2/](research/fedspeak_v2/) | working notes for v2 (the operative pre-registration is in `preregistration/`) |
| [research/data_feasibility.md](research/data_feasibility.md) | data availability and feasibility checks |
| `research/idea_literature.md`, `high_sharpe_literature.md`, `scholar_hf_findings.md` | literature searches and findings |
| `research/github_repos.md`, `local_strategies.md` | repository and local-strategy surveys |

## Markdown that stays next to code or results

These files are deliberately not in `docs/`:

| Where | Why it stays |
|---|---|
| `preregistration/*.md` | frozen plans; the runners check their SHA-256 |
| `backtests/presser/ADDENDUM.md` | frozen execution rules; every press-conference step checks its hash |
| `backtests/results/*/README.md`, `metrics.md`, `tables.md`, `summary.md`, `v2_oos/RUN_LOG.md` | result records written by the runners next to their results (the v2 reproduction reads `RUN_LOG.md`) |
| `results_2/*/` (`metrics.md`, `SPEC.md`, `ATTRIBUTION.md`, `TURNOVER_CAPACITY.md`) | written by the results_2 scripts. `attribution.py` checks the hash of `SPEC.md` |
| `backtest_snapshot/`, `archive/`, `strategies/01/` | frozen history |
| `hpg/fedpress_pkg/` (README, REVIEW, docs/) | the feature package's own manual |
| `backtests/README.md`, `backtests/v2/README.md`, `nlp/README.md` | one-line pointers to the guides here, kept because script messages name these paths |
