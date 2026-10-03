# Pre-registration log (Fed communication strategy)

These files fix the hypotheses, rules and deviations before the results they govern. They were written and hashed during the session of Sat 2026-10-03, which is when the times below were recorded, in local files outside git. They are committed here publicly at about 23:15 UTC.

**Disclosure:** the public commit comes AFTER the v2 in-sample backtest had run (about 23:10 UTC). That run applied the decision rule, which failed, so v2's out-of-sample window was not evaluated. The commit comes BEFORE anyone viewed the press-conference H1 results.

## Timeline (UTC, 2026-10-03)

| Time (UTC) | Event | SHA-256 at that time |
|---|---|---|
| 19:52 | v2 pre-registration written (HYPOTHESIS_v2.md, before any v2 backtest) | 2a368566...a893ab |
| 19:53 | v2 Amendment 1: evaluation from 2016 (Yellen, Powell, Warsh) | 6083d3ef...7ced910 |
| 21:12 | v2 Amendment 2 and press-conference Deviation D1: walk-forward chrono-BERT replaces the gated FOMC-RoBERTa | 802a95af...55fa30 (v2); 580279a9...51433c (D1) |
| 21:35 | v2 clarification: 2015 warm-up documents scored with the 2015 model | f93b63eb...b95f2c |
| 21:45 | Press-conference ADDENDUM written: exits, latency, costs, samples; no return computed | (file below) |
| 21:50 | v2 Amendment 3 and D1a: label dates corrected from source documents | 464f8a5b...ebd79 (v2); 660d06a8...9ebd79 (D1) |
| 22:40 | v2 DEVIATIONS.md (D-1 unscheduled de-risk dates; D-2 T3 scaling), before any v2 return | 48e6643d...e4796a |
| about 23:10 | v2 in-sample backtest run; decision rule failed; out-of-sample not evaluated | |
| about 23:15 | this commit | |

## Files and current SHA-256

| File | SHA-256 |
|---|---|
| HYPOTHESIS_v2.md (v2, with Amendments 1-3 and the clarification) | 464f8a5bad37e6466ccde42e8941fa1836323600324792d4d53dcc0c50eb8a2e |
| DEVIATIONS.md (v2) | 48e6643d47c2c6422890616d9e862f7695fb407e6f6be81bde8d4ea117e4796a |
| presser_team_FINAL_PLAN.md (the team's locked family) | 88cc54a869e7cf540d561a257a3203524392cd1cbe18d25560f397b926651846 |
| presser_DEVIATION_D1.md (with D1a) | 660d06a85a434328a5ec28f0d45611457bb44e7fcd4c4a6fef28bb843d9ebd79 |
| presser_ADDENDUM.md | 1921b2ca1dc6e646b95ee1d1bbc3e3ef7f6a864c06cd724956df7c6569de2dc4 |
