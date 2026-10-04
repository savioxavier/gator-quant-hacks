# v2 out-of-sample evaluation: run log (deviation D-3)

Deviation: `preregistration/v2_DEVIATION_D3_OOS.md`, sha256 97585d3ca3e7f5764d16e24787486c51ca298dd95ca57ad82d27e1ba30af1c69
(pinned: 97585d3ca3e7f5764d16e24787486c51ca298dd95ca57ad82d27e1ba30af1c69).
Pre-registration: `preregistration/HYPOTHESIS_v2.md`, sha256 464f8a5bad37e6466ccde42e8941fa1836323600324792d4d53dcc0c50eb8a2e.

This file was written before the run started; the end time and exit status were appended when the process
exited, before any output number was read. The evaluation is run once.

## Command

```
cd <team repo>
GQH_REPO=D:/AUTOMATION/gqh-systematic GQH_DATA_DIR=C:/Users/hoang/.cache/gqh V2_WORK_ROOT=<v2 work root> \
  V2_OOS_DEVIATION=preregistration/v2_DEVIATION_D3_OOS.md PYTHONIOENCODING=utf-8 \
  C:/Users/hoang/.venvs/gqh-systematic/Scripts/python.exe backtests/v2/run_v2_chrono.py \
  --doc-scores backtests/v2/score/doc_scores.parquet --out backtests/results/v2_oos/run
```

GQH_OOS_UNLOCK unset. `<team repo>` is this repository; `<v2 work root>` is the original local v2 work root
(inputs not in git, see `backtests/v2/README.md`). stdout and stderr: `run/run_stdout.log` (local paths replaced
by these placeholders).

## Code and inputs

- git HEAD 1c8c9e1 (branch review/strategy-01); uncommitted D-3 unlock in
  `backtests/v2/run_v2.py` and `backtests/v2/run_v2_chrono.py` (git diff sha256 0294728ce6e1ed295435acd3e5af097dfd87bb6f76a5a537c07422d2749e756a)
- `backtests/v2/run_v2.py` sha256 3102317b9e1f9576bfb1b7b0fe05f9011022f4838f8e155995ecae0711558802
- `backtests/v2/run_v2_chrono.py` sha256 6c215d275a78148840c7a6482855ab9ce07d5aa36a4637d456d7ae996989d137
- `backtests/v2/v2lib.py` sha256 bfd9bae4b58263be836ff32d4d9d8342788aedc77e2764a47478b21a75149cf6
- `backtests/wire/wirelib.py` sha256 93881859af9de384d74add1c68632b526ca69f0f868e42e2c548f9cdb1d8f5fc
- `backtests/v2/report_v2_oos.py` sha256 299bf7e0242fa82bda0992c8fe7af061ce46eb5c66459a6646724a400c10ceeb
- `backtests/v2/score/doc_scores.parquet` sha256 0e0c1ca7c0fd5ed0b229db2ae745039c383e8e50f64ba524ad3c688d59873ba0
- report script `backtests/v2/report_v2_oos.py` (metric definitions) was written and tested on synthetic
  series before this run; its hash above is the version used for the report
- `<v2 work root>/fedspeak_v2/corpus/fomc_dates.csv` sha256 41072c60695a0938f30107376c110da7758066d646513f4e12be07d7ecbf175c
- `<v2 work root>/fedspeak_v2/corpus/fomc_dates_variantA_style.csv` sha256 5670a1e765ee7b0f1402558f350fe9deee8ee7cb86412b4a9154a906433e8ffb
- `<v2 work root>/savio_gqh/strategies/01/data/processed/fomc_dates.csv` sha256 5555f7f41d95db6680421f03dc86bdeadb2c6b1f24ee01e0207d1924daac9b6a
- `<v2 work root>/savio_gqh/strategies/01/trials/log.csv` sha256 2a17a241f0647435b0312375c6d8d2910bfc683630fe59e9952274bd56aae5b9
- `<v2 work root>/fedspeak/extend/speech_scores_2011_2026.csv` sha256 523b8594756cbb1f5e07dee3405ff69166bc07d822cc54a753b611f5a0200e8a
- `<v2 work root>/edges/combine/combine.py` sha256 5150cb8a7d0bbb463ee6ba9f4a82f3205101578bf417f988cd304175d92f42e7
- `<v2 work root>/edges/series/PORT_core_ER_6.parquet` sha256 9bfd6882d3361d5fa81a49ea5d4a170296a510cd43fe3e2f99ca3ba275237816
- data cache `etf_daily.parquet` sha256 7086babddd0e22b1538e3f7cf79340e5923c4256456cdca9b3e3c54874a0712b
- data cache `futures_daily.parquet` sha256 71db580de202e9288788f16257e73154fdc6407073ffdacd0f83478c676eb17d
- data cache `futures_1600.parquet` sha256 aef98c9982406dc7cc0c5d552a4f6b03121ab41df20f96c4ac202d0fe6d28ebc
- data cache `fred_daily.parquet` sha256 8efeca56f3f1950642237ab826ee0d745e9d60ece978289fb50f0ba75cf8b02d
- data cache `rf_daily.parquet` sha256 03877682a85f32cce9cf8a1764aa01d51491fd77e051487501189d1b8a8bc515
- gqh-flow-clock HEAD 1587f25; src/engine.py sha256 74ac9fdb27243e228a9069f1edc7fb37d0bfbd16afdb8a728fe7d9ae14b785e6

## Run

- start (UTC): 2026-10-04T01:22:55Z
- end (UTC): 2026-10-04T01:22:57Z
- exit status: 0

## Outputs (sha256)

- `run/by_chair_is.csv` b5a7b2a28b9cbd93389495929df8552ff757b682103f5f176b84e635311442e5
- `run/by_chair_oos.csv` 1d591c835e448bcab4f809d17c177813bd42c8621ffbc9913aa5b6e36a73d800
- `run/daily_T4xE1_full.parquet` 2473204a43ad99e956d1b5105286b8d8d4729ddf28171f6eec52e332dddfc260
- `run/daily_T4xE1_is.parquet` a26643661de4a6b492b199b8bea30a29ead1dad846f1f6291efdcb98d0907121
- `run/daily_VariantA_frozen_T0fxE1_full.parquet` dd7216c4e3485ec6b89ed3349a1d4e1ca124a67a469b7fbc9198512e6bf12f7f
- `run/daily_excess_all_combos_is.parquet` 39ea19aec05be58c19b7e4399f18c734ad69dc72fc7a2de0586e45e95db883e2
- `run/daily_portfolio_full.parquet` 70e7c6eac94db045c9fe7af68fb9b2ee2b34b5e2d1db5d81e13208a426188537
- `run/oos_chosen.json` 7a0b57b9ee08ab0f9c9b55f0ba6914ebee27967b5b2d429f0ace3a75e253f520
- `run/portfolio.csv` ebcddfebab44a7622cc4654efab83c9b10c8c9cfdd71add3f939dda1f339694a
- `run/portfolio_info.json` 443b1b4420c4cc0b11405e52df25f1226fae3465385297810ea4ec3d82460d57
- `run/portfolio_info_oos.json` 10def1ad9e21f1a1cbf5ca0c57e4ca916a21c885a4382a7d1f87f9b63434b59a
- `run/portfolio_oos.csv` 6286c88aa35905edaba7babd950ecbedd914b4d42b781b44ceb56e628fa7f7de
- `run/selection.csv` 69b653d71a6f861a358b3b482f99cf47f53939ad1433a2cceebcd346cf579039
- `run/sens_scheduled_only_is.csv` c103d7f459808ca652d0972bad7bf676d65f2ab6db41a40941b4249c93eef3b1
- `run/sens_scheduled_only_oos.csv` d29c69a4fba79e3235a43d52fe4519108e0c41b5d5d37e85201eff08fdc546e0
- `run/signals_entry_session.parquet` 9ce6fcc59f23367133f9d970ec8e620dea88b03d9fac973ad3dda30adde36f74
- `run/summary_is.json` 80c6a39b078a31675362a85c6fd8213bd0e7a77516046f97dd7fb3e139ea8906
- `run/windows_all.csv` dd6ce0daacc7e241f5bc7273ae2623e4d5eab8e6e81eadf3002ae8ce29a2d8aa

## After the run (appended once the numbers had been read)

- `backtests/v2/report_v2_oos.py` (sha256 299bf7e0242fa82bda0992c8fe7af061ce46eb5c66459a6646724a400c10ceeb, the same file as before the run) wrote `metrics.csv`, `metrics.md`,
  `daily_returns.csv/.parquet`, `consistency.json` and the three equity PNGs from `run/` only. Consistency: the
  in-sample windows of the full-period series match the committed tables to 1e-16; the OOS rows match
  `run/oos_chosen.json` and `run/portfolio_oos.csv` exactly.
- `backtests/tools/compare_results.py`: the run's in-sample files agree with `backtests/results/v2` (7/7) and with
  `backtest_snapshot/fedspeak_v2/backtest` (10/10).
- `backtests/v2/describe_v2_oos.py` (sha256 27c6f59c8d495fd8c86c7c304003a2d84ba73fba539e3618280e1fc5ec313fdc) was written after the result was seen. It is descriptive only and
  wrote `oos_concentration.csv`.
- `run/run_stdout.log` holds the run's stdout and stderr, with local paths replaced by placeholders. It was written
  after the hash list above.
