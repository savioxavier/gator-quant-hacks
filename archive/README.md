# Archive: working outputs of the whole project

Everything the project produced that is safe to publish, kept for transparency. **These are working outputs, not the
submission's evidence**: the evidence is in `backtests/`, `preregistration/` and `report/REPORT.md`, which cite only
committed, reproducible files. Many folders here are exploratory, superseded or failed ideas (see the report's
failed-ideas list), and some scripts expect local data that is not in git.

`MANIFEST.tsv` lists every file with its size. `session_outputs/<folder>/` keeps each working folder's structure:

| Folder | What it is |
|---|---|
| `fedspeak/`, `savio_gqh/` | strategy 01 (speech-lexicon tone) replication, extension and analysis |
| `wire/`, `results_final/`, `report_final/` | stance-model wiring, the combined results summary, the report's fact sheet |
| `presser_bt/`, `presser_bt_h234/` | press-conference backtest (H1, BENCH-R) code and outputs as run, and the H2/H3/H4 stage before consolidation |
| `h234_run/`, `h234_s1_check/`, `h234_extra/`, `si_check/` | H2/H3/H4 runs, the stage-1 diagnostic, extra descriptive rows and strategy metrics, the 64 kbps re-encode check |
| `placebo_chain/`, `placebo_features/`, `ship_placebo_h234_test/` | placebo and positive-control runs used to test the pipelines (fake scores and features) |
| `v2_oos_build/`, `rerun_direct/`, `rerun_tamper/` | v2 in-sample reproduction before the one D-3 run; reproduction and tamper-test reports |
| `verify_v2/`, `verify_presser/`, `verify_h234/`, `verify_chain2/`, `verify_ld/`, `audit_verify_presser_1/`, `hpg_emul3/`, `hpgmatrix/` | independent recomputations and audits |
| `edges/`, `auction/`, `intraday_study/`, `gtaa_study/`, `hunt100/`, `kit_native/`, `ft2_review/`, `fwd2_synth/`, `pct_review/`, `rev/`, `before/` | earlier strategy research: edge sleeves and the core portfolio, Treasury auction cycle, intraday and overnight effects, tactical allocation, a 100-strategy screen, organiser starter-kit runs, forward-test reviews |
| `fedtalk/`, `gapdata/`, `it1_*`, `r1_*`, `r2*`, `r3_build/`, `final_parts/`, `econ_stmt/` | press-conference planning checks, data-gap studies and plan-review iterations |

**What was left out, and why.** Licensed Databento market data and any table holding price levels (338 files with
price columns and 17 wide price tables were dropped automatically); files that matched a key or password pattern;
virtual environments, model weights and caches; clones of this and other repositories; downloaded papers and
third-party repositories; raw recordings; files over 5 MB. Local machine paths in text files are replaced by
placeholders (`<home>`, `<scratch>`, `<solo-repo>`, `<fedpress-root>`, `/blue/<group>/<user>`).
