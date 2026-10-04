# v2 inputs that are not licensed

The public part of the v2 input bundle. Point `V2_WORK_ROOT` at `work/` and copy `data/fred_daily.parquet` and
`data/rf_daily.parquet` into your `GQH_DATA_DIR` next to the private price files (see `data/README.md` for how to
obtain those and their checksums). `MANIFEST.sha256` lists every file here.

| Path | What it is |
|---|---|
| `work/edges/series/*.parquet` | daily net 1x / net 2x / gross return series of the edge sleeves, including `PORT_core_ER_6` (returns only) |
| `work/edges/combine/combine.py` | the portfolio builder used for the core_ER_6 portfolio test (`combine.build`); its line `REPO = Path(...)` is a local default from the original machine and is not used when `GQH_REPO` is set; kept byte-identical so its SHA-256 matches `backtests/results/v2_oos/RUN_LOG.md` |
| `work/edges/combine/existing*.parquet`, `comparators_native.parquet`, `existing_meta.json` | return series of the reference strategies the builder reads |
| `work/fedspeak/extend/speech_scores_2011_2026.csv` | strategy 01's lexicon scores of Board speeches (Variant A input) |
| `work/fedspeak/replicate/signal.parquet` | strategy 01's replicated signal and weights (cross-check) |
| `work/fedspeak_v2/corpus/fomc_dates*.csv`, `work/savio_gqh/strategies/01/data/processed/fomc_dates.csv` | FOMC announcement date lists used for the de-risk rule |
| `work/savio_gqh/strategies/01/trials/log.csv` | strategy 01's logged trials (used in the Deflated Sharpe) |
| `data/fred_daily.parquet` | FRED DTB3, DGS10, DGS2, DGS30, T10Y2Y (the restricted VIXCLS and BAMLH0A0HYM2 columns of the original file are removed; v2 does not use them) |
| `data/rf_daily.parquet` | daily cash rate from DTB3 |
