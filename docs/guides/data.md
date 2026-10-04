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
| `FEDPRESS_ROOT` | the feature tables (H2/H3/H4), e.g. `$PWD/data/fedpress_features_local` |
| `H234_OUT_DIR` | with the local feature tables, `$PWD/backtests/presser/backtest_h234_local` (git-ignored), so the committed HiPerGator reference run in `backtests/presser/backtest_h234/` is not overwritten |

Then `bash backtests/run_all_backtests.sh` (see [running-backtests.md](running-backtests.md), [reproduction.md](reproduction.md) and the exact commands in [reproduction_commands.md](../submission/reproduction_commands.md)), or on HiPerGator
`sbatch hpg/backtest_all.sbatch`. A stage whose inputs are absent is reported as skipped or refused in the summary at the end of the run; count a run as a reproduction only when every stage you need reports that it reproduces the committed results (v2, D-4, presser) or completed (h234).

## What is in the data folders

These sections describe the committed data in place; the files themselves stay in their folders.

### Press-conference transcripts and captions (`data/fomc_pressers/`)

All 95 FOMC press conferences from 2011-04-27 to 2026-09-16 (Bernanke 12, Yellen 16, Powell 64, Warsh 3).

| Folder | Contents |
|---|---|
| `data/fomc_pressers/transcripts/` | `FOMCpresconfYYYYMMDD.pdf`: the official transcript PDFs, with speaker labels for the chair and reporters. `.txt` holds the extracted text of each PDF. |
| `data/fomc_pressers/captions/` | `YYYYMMDD.vtt`: the official WebVTT caption files from the Board's video player. There are 83 of them, and cue times are relative to the start of the video. `data/fomc_pressers/missing_captions.txt` lists the 12 meetings without a caption file. |

**Source:** federalreserve.gov, from the press-conference pages linked from the FOMC calendars. These are works of the US federal government and are in the public domain. Retrieved 2026-10-03.

**Timing convention:** published work treats video time zero as 14:30:00 ET. The real start varies, because the greeting falls 0.6-144 s into the video. Estimate a per-meeting offset before any timing-sensitive test, and drop meetings whose start is uncertain by more than 30 s (see the team plan).

#### Not in this repository

- **Video and audio recordings** (95 MP4s, about 65 GB). They are too large for GitHub, whose limit is 100 MB per file. The HiPerGator pipeline downloads them from federalreserve.gov using a manifest of the video URLs. Derived chair-only voice and face features (small parquet files) can be added here after that run.
- **Futures market data** (Databento). It is licensed and must not be redistributed, so it stays in each user's local cache.

### Local feature tables (`data/fedpress_features_local/`)

Per-meeting tables written by the feature package `hpg/fedpress_pkg` (code version 0.1.0+src.df22a2d52e78) for
every Powell press conference from 2018-03-21 to 2026-04-29. They were computed on one local RTX 5090 between
2026-10-03 23:45:57 and 2026-10-04 00:44:44 UTC, after the exploratory H2/H3/H4 pre-registration was public (see
`preregistration/presser_H2H3H4_NOTE1.md`). They feed the **local replication** of H2/H3/H4
(`docs/results/h234-local-summary.md`). The HiPerGator tables, which feed the reference run
(`backtests/presser/backtest_h234/`), were produced by the same code and model revisions and stay on HiPerGator; the
two runs agree (H2 p 0.438 vs 0.439, H4 p 0.244 vs 0.243).

#### Layout

`data/fedpress_features_local/meetings/<presser_id>/` holds, per meeting:

| Folder | Tables | What |
|---|---|---|
| `asr/` | `words.parquet`, `segments.parquet`, `asr.json` | Whisper large-v3-turbo transcript with word times |
| `turns/` | `turns.parquet`, `words.parquet`, `anchor.json` | speaker turns aligned to the transcript PDF; clock anchor; `known_at` |
| `diarize/` | `chair_check.parquet` | ECAPA check that a window is the chair's voice |
| `voice/` | `voice_chunks.parquet` | 8 s chunks of the chair's answers: arousal, dominance, valence, prosody, identity flags |
| `face/` | `face_frames.parquet`, `face_turns.parquet`, `enroll.json` | 1 fps chair frames: blendshapes, expression scores, identity and quality gates |
| `_done/` | one JSON per stage | status, outputs with sha256, code version, config hash, overrides |

`MANIFEST.sha256` lists every file; `data/fedpress_features_local/models_lock.json` lists the model revisions (Whisper 0a363e91, ECAPA 0f99f2d0,
audeering 6eba34a2, MediaPipe face landmarker 64184e22, EmotiEffLib enet_b0_8_va_mtl b7b9522e, SFace 0ba9fbfa).
Settings: the package's default config (voice and face for Powell only, face at 1 fps); the only overrides were the
compute type and batch sizes (see each `_done/*.json`). Every table carries `known_at`, the time the row could have
been known live.

#### Known issues

- **2023-06-14:** the recording the Federal Reserve publishes for this meeting is the 2023-07-26 press conference,
  so these tables describe the July meeting (`preregistration/presser_H2H3H4_NOTE2.md`). Do not use them for June.
- **2020-03-03 and 2020-03-15** are unscheduled meetings; on 2020-03-15 face enrolment failed (no usable frames).
- Fifteen meetings, mostly 2018-2020, have lower voice identity (0.81-0.90) and face gate (0.75-0.89) rates; use the
  tables' own gate columns.

#### Sources and licences

The videos, captions and transcripts are works of the US federal government (public domain). The features come from
these models: Whisper (MIT), SpeechBrain ECAPA (Apache-2.0), audeering wav2vec2 MSP-dim (CC BY-NC-SA 4.0, so these
voice features are for non-commercial use), MediaPipe (Apache-2.0), EmotiEffLib (Apache-2.0) and OpenCV SFace
(Apache-2.0). No market data are in `data/fedpress_features_local/`.

### Public v2 inputs (`backtests/v2/inputs/`)

The public part of the v2 input bundle. Point `V2_WORK_ROOT` at `backtests/v2/inputs/work/` and copy `backtests/v2/inputs/data/fred_daily.parquet` and
`backtests/v2/inputs/data/rf_daily.parquet` into your `GQH_DATA_DIR` next to the private price files (see `docs/guides/data.md` for how to
obtain those and their checksums). `backtests/v2/inputs/MANIFEST.sha256` lists every file there.

| Path | What it is |
|---|---|
| `backtests/v2/inputs/work/edges/series/*.parquet` | daily net 1x / net 2x / gross return series of the edge sleeves, including `PORT_core_ER_6` (returns only) |
| `backtests/v2/inputs/work/edges/combine/combine.py` | the portfolio builder used for the core_ER_6 portfolio test (`combine.build`); its line `REPO = Path(...)` is a local default from the original machine and is not used when `GQH_REPO` is set; kept byte-identical so its SHA-256 matches `backtests/results/v2_oos/RUN_LOG.md` |
| `backtests/v2/inputs/work/edges/combine/existing*.parquet`, `comparators_native.parquet`, `existing_meta.json` | return series of the reference strategies the builder reads |
| `backtests/v2/inputs/work/fedspeak/extend/speech_scores_2011_2026.csv` | strategy 01's lexicon scores of Board speeches (Variant A input) |
| `backtests/v2/inputs/work/fedspeak/replicate/signal.parquet` | strategy 01's replicated signal and weights (cross-check) |
| `backtests/v2/inputs/work/fedspeak_v2/corpus/fomc_dates*.csv`, `backtests/v2/inputs/work/savio_gqh/strategies/01/data/processed/fomc_dates.csv` | FOMC announcement date lists used for the de-risk rule |
| `backtests/v2/inputs/work/savio_gqh/strategies/01/trials/log.csv` | strategy 01's logged trials (used in the Deflated Sharpe) |
| `backtests/v2/inputs/data/fred_daily.parquet` | FRED DTB3, DGS10, DGS2, DGS30, T10Y2Y (the restricted VIXCLS and BAMLH0A0HYM2 columns of the original file are removed; v2 does not use them) |
| `backtests/v2/inputs/data/rf_daily.parquet` | daily cash rate from DTB3 |
