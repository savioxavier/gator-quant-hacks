# Data: what we used, where it came from, and how to get it

Every dataset behind the study, how it was acquired, its licence, and whether it is in this repository. **Rule
followed throughout:** returns, ticks, P&L, spreads in ticks and statistics are published; licensed prices and quotes
(Databento, Yahoo Finance) are not. Those files stay private; this page says exactly how to obtain them and gives
the SHA-256 of the copies we used, so a rebuilt copy can be checked.

## Summary

| Dataset | Source | Licence | In the repo? | Where |
|---|---|---|---|---|
| Fed speeches, statements, minutes, press-conference transcripts | federalreserve.gov | US government work (public domain) | Yes | `data/text_corpus/`, `data/fomc_pressers/` |
| Press-conference videos and captions | federalreserve.gov (Brightcove video, WebVTT captions) | Public domain | Captions and transcripts yes; videos no (82 h, 63 GiB) | `data/fomc_pressers/`; download with `hpg/fetch_audio.sbatch` |
| Voice, face and speech feature tables | Our feature package run on the recordings | Ours (see model licences below) | Yes (local run, 64 Powell meetings) | `data/fedpress_features_local/` |
| Stance labels | gtfintechlab/fomc_communication (Hugging Face) | CC BY-NC 4.0 | Re-dated label index yes; the labels themselves are downloaded | `data/text_corpus/label_dates.parquet` |
| Stance base models | manelalab/chrono-bert-v1-*1231 (Hugging Face) | MIT | No (downloaded at run time) | `nlp/` |
| Feature models (speech, voice, face) | Hugging Face and vendor URLs, pinned revisions | MIT / Apache-2.0 / CC BY-NC-SA 4.0 | No (downloaded by `prefetch-models`) | `hpg/fedpress_pkg/config.yaml` |
| Treasury yields and T-bill | FRED (St. Louis Fed) | US government series, public | Yes | `backtests/v2/inputs/data/fred_daily.parquet`, `rf_daily.parquet` |
| VIX, high-yield spread | FRED (Cboe, ICE) | Restricted by their owners | **No** (not used by v2) | download yourself (below) |
| v2 work inputs (edge return series, FOMC dates, speech scores, combine code) | Our earlier research | Ours | Yes | `backtests/v2/inputs/work/` |
| ETF daily prices (TLT, UUP, ...) | Yahoo Finance via yfinance | Yahoo terms: no redistribution | **No** | private `etf_daily.parquet` |
| Futures daily and 16:00 series | Databento GLBX.MDP3 | Licensed | **No** | private `futures_daily.parquet`, `futures_1600.parquet` |
| Press-conference intraday bars and quotes | Databento GLBX.MDP3 | Licensed | **No** | private `ohlcv-1m/1s`, `bbo-1s` files |
| Monetary-policy event study (USMPD) | Federal Reserve Bank of San Francisco | Public download | Only derived checks | `backtests/results/presser_h1/benchr_usmpd_ust2y.csv` |
| Live TV caption timing | GDELT TV API, Internet Archive TV News | Public APIs | Derived event times only | `backtests/presser/events/events.csv` |

## Public data: how it was acquired

- **Fed text.** Speeches (2015-01-01..2026-10-02), FOMC statements, minutes and press-conference transcripts were
  collected from federalreserve.gov, with release times from the site's JSON feeds (`ne-speeches.json`,
  `ne-press.json`). The scored corpus is `data/text_corpus/docs_to_score.parquet`.
- **Press conferences.** `hpg/build_manifest.py` lists every conference page, transcript PDF, caption file and video
  link; `hpg/fetch_audio.sbatch` (or `hpg/fetch_audio.sh`) downloads the videos and extracts 16 kHz audio. The
  feature package (`hpg/fedpress_pkg`, run with `hpg/run_everything.sbatch`) turns them into the feature tables.
- **Labels.** `nlp/` downloads gtfintechlab/fomc_communication and re-dates every row to its source document
  (`nlp/build_label_dates.py`); the dataset's own year column was wrong for 2,336 of 2,480 rows.
- **Models.** The stance models start from manelalab/chrono-bert-v1 yearly checkpoints. The feature models are
  fetched at pinned revisions by `python -m fedpress.cli prefetch-models` (the HiPerGator jobs do this).
- **FRED.** Daily CSVs from `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>` for DTB3, DGS10, DGS2,
  DGS30 and T10Y2Y. The cash rate is DTB3 / 100 / 252 (`rf_daily.parquet`). The solo repository's
  `data/download.py` does this. The published `fred_daily.parquet` has those five series only; VIXCLS (Cboe) and
  BAMLH0A0HYM2 (ICE) carry owner restrictions, are not used by v2, and can be downloaded with the same URL if needed.
- **USMPD.** `USMPD.xlsx` from the San Francisco Fed (used to check our statement-window clock: correlation -0.995
  with the 2-year yield change).
- **TV caption timing.** GDELT Television API 2.0 (CNBC, FOX Business) and Internet Archive TV News item pages, used
  to anchor each conference's start time.

## Licensed and private data: how to obtain it

Not in the repository. Each needs your own access; the checksums identify the exact copies we used.

**1. Databento, CME Globex (GLBX.MDP3).** A Databento account and API key (keep it in a local `.env` as
`DATABENTO_API_KEY`; never commit it).

| File | Request | Size | SHA-256 |
|---|---|---|---|
| `futures_daily.parquet` | schema `ohlcv-1d`, `stype_in="continuous"`, symbols `<root>.v.0` and `<root>.v.1` (volume-ranked front and second contract) for the futures universe, 2010-06-06..2026-10-03; built into within-contract daily returns with roll flags | 6,330,114 B | `71db580de202e9288788f16257e73154fdc6407073ffdacd0f83478c676eb17d` |
| `futures_1600.parquet` | schema `ohlcv-1h` for ES and ZN (the 16:00 ET series) | 443,912 B | `aef98c9982406dc7cc0c5d552a4f6b03121ab41df20f96c4ac202d0fe6d28ebc` |
| `ohlcv-1m__all_2016_2026.parquet` | schema `ohlcv-1m`, symbols `ZT.v.0`, `ZF.v.0`, `ZN.v.0`, `ES.v.0`, 13:30-16:30 ET on each of the 75 press-conference dates 2016-2026 | 811,105 B | `268aa049e1c3cc5076809d3add3e3376b49a357687c24165f75dc946818baefa` |
| `ohlcv-1s__all_2016_2026.parquet` | schema `ohlcv-1s`, same symbols and windows | 18,551,710 B | `4081e89b25d0baa9841497eea2330652790b04431781816187aaf940ee4613af` |
| `bbo-1s__all_2016_2026.parquet` | schema `bbo-1s` (best bid/offer each second), `ZT.v.0`, `ZN.v.0`, `ES.v.0` (no ZF quotes), same windows | 50,067,512 B | `8b3c1804d58bd4ff8de1f431f58fd9c2b3315e87a84b258c1b1b95eeea4c277c` |

The daily and hourly files are built by the solo repository (github.com/minh-stakc/gqh-flow-clock, commit 1587f25):
`python data/download_databento.py --batch` (batch download, then `build_daily` / `build_hourly_1600`). The intraday
press-conference files were pulled with the Databento Python client and combined into the three `__all_2016_2026`
files; the original pull script is not in this repository, but the request is the one in the table, for example:

```python
import databento as db
client = db.Historical()                       # reads DATABENTO_API_KEY
df = client.timeseries.get_range(
    dataset="GLBX.MDP3", schema="ohlcv-1s", stype_in="continuous",
    symbols=["ZT.v.0", "ZF.v.0", "ZN.v.0", "ES.v.0"],
    start="2024-12-18T13:30:00-05:00", end="2024-12-18T16:30:00-05:00",
).to_df()
```

Check the price with `client.metadata.get_cost(...)` first: the full intraday set (all three schemas, 75 days) cost
about $8.53 in October 2026. The volume-ranked contract (`.v.0`) is used rather than the calendar front (`.c.0`),
which is the illiquid delivery-month contract on many meeting days.

**2. Yahoo Finance (via yfinance).** Free, but its terms do not allow redistribution.

| File | Request | Size | SHA-256 |
|---|---|---|---|
| `etf_daily.parquet` | daily OHLCV, `auto_adjust=True` (total-return adjusted), from 2003-01-01, for the ETF list in the solo repository's `data/download.py` (TLT and UUP are the ones v2 trades) | 8,848,939 B | `7086babddd0e22b1538e3f7cf79340e5923c4256456cdca9b3e3c54874a0712b` |

Adjusted Yahoo prices are revised when distributions are re-adjusted, so a fresh download may not match this
checksum exactly; small differences in v2's numbers can come from that alone.

**3. Full FRED file (optional).** `fred_daily.parquet` with VIXCLS and BAMLH0A0HYM2 added (324,773 B,
`8efeca56f3f1950642237ab826ee0d745e9d60ece978289fb50f0ba75cf8b02d`). v2 does not need the two extra series.

## Putting it together for a full rerun

| Variable | Point it at |
|---|---|
| `GQH_REPO` | a clone of github.com/minh-stakc/gqh-flow-clock at commit 1587f25 (the backtest engine) |
| `GQH_DATA_DIR` | a folder with `etf_daily.parquet`, `futures_daily.parquet`, `futures_1600.parquet` (private) and `fred_daily.parquet`, `rf_daily.parquet` (from `backtests/v2/inputs/data/`) |
| `V2_WORK_ROOT` | `backtests/v2/inputs/work/` in this repository |
| `GQH_MARKET_DIR` | a folder with the three Databento intraday files (press-conference stages) |
| `FEDPRESS_ROOT` | the feature tables (H2/H3/H4), e.g. `data/fedpress_features_local/` |

Then `bash backtests/run_all_backtests.sh` (see `backtests/README.md` and `docs/reproduction.md`), or on HiPerGator
`sbatch hpg/backtest_all.sbatch`. A stage whose inputs are absent is reported as skipped or refused in the summary at the end of the run; count a run as a reproduction only when every stage you need reports that it reproduces the committed results (v2, D-4, presser) or completed (h234).
