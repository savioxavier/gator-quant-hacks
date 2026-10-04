# HiPerGator jobs

Every job is submitted from the repository root of a clone on `/blue`, after you log in yourself (GatorLink and Duo).

| Job | Command | Section |
|---|---|---|
| Download the press-conference recordings and audio | `sbatch hpg/fetch_audio.sbatch` | [Recordings and audio](#recordings-and-audio-hpgfetch_audiosbatch) |
| Stance model: 36 fine-tunes, scoring, merge | `bash hpg/submit_nlp.sh` | [Text stance model](#text-stance-model-hawkish--dovish) |
| Voice, face and speech features (with the stance chain) | `sbatch hpg/run_everything.sbatch`, then `sbatch hpg/pack_features.sbatch` | [Everything at once](#everything-at-once-sbatch-hpgrun_everythingsbatch) |
| Every backtest stage | `sbatch hpg/backtest_all.sbatch` | [Backtests](#backtests-hpgbacktest_allsbatch-and-hpgv2_oossbatch) |
| v2 only: in-sample, D-3 out-of-sample and D-4 | `sbatch hpg/v2_oos.sbatch` | [Backtests](#backtests-hpgbacktest_allsbatch-and-hpgv2_oossbatch) |

## Recordings and audio (`hpg/fetch_audio.sbatch`)

This job downloads every FOMC press-conference recording (95 videos, 2011-2026, about 65 GB) and extracts 16 kHz mono audio (FLAC, about 2-3 GB). It also fetches the caption files and transcript PDFs. Everything runs on CPU nodes, so it never waits in the B200 queue.

## Run it (about 30-60 minutes)

Log in yourself (Duo), then run:

```bash
ssh <gatorlink>@hpg.rc.ufl.edu
```

```bash
mkdir -p /blue/jie.xu/$USER && cd /blue/jie.xu/$USER
```

```bash
git clone -b review/strategy-01 https://github.com/savioxavier/gator-quant-hacks.git && cd gator-quant-hacks
```

```bash
sbatch hpg/fetch_audio.sbatch
```

Watch it:

```bash
squeue -u $USER
```

```bash
tail -f fedpress_fetch_*.log
```

## Output, under /blue/jie.xu/$USER/fedpress

| Folder | Contents |
|---|---|
| `video/` | `YYYYMMDD.mp4`, the Board's recording (largest rendition up to 960x540) |
| `audio/` | `YYYYMMDD.flac`, 16 kHz mono, the input for the voice models |
| `captions/` | Official WebVTT files (83 meetings have them) |
| `transcripts/` | Official transcript PDFs |
| `manifest/` | `pressers.csv` (one row per press conference: chair, times, URLs, sizes), `fetch_report.csv` (audio duration per meeting) |

## Settings

- `ONLY_STUDY=1` downloads only the 2016+ study sample (75 press conferences).
- `NPAR` sets the number of parallel downloads and ffmpeg processes.
- `FEDPRESS_ROOT` changes the output root.

For example:

```bash
sbatch --export=ALL,ONLY_STUDY=1 hpg/fetch_audio.sbatch
```

## Notes

- The first run builds a small conda environment on /blue (python, ffmpeg, aria2). Later runs reuse it.
- The job is re-runnable. Finished files are skipped and partial downloads resume.
- The video and caption links are signed and expire after a few hours, so the job rebuilds the manifest every time it starts (`hpg/build_manifest.py`, standard-library Python only).
- If `jie.xu` is a secondary group for you, keep `--account=jie.xu` (already set).
- If the burst QOS `jie.xu-b` is busy, edit the sbatch file to use `--qos=jie.xu`.
- The recordings are public-domain works of the US government (federalreserve.gov). They stay on /blue and are not committed to git.
- The voice, face and text feature stages, which use the B200s with at most 2 GPUs, are run by `hpg/run_everything.sbatch` (below). They read `audio/`, `video/`, `captions/` and `transcripts/` from the same root.

## Text stance model (hawkish / dovish)

`bash hpg/submit_nlp.sh` trains the 36 walk-forward stance models (2015-2026, 3 seeds) and scores every document, as four chained jobs
under account and QOS `ai-workshop` (outputs in `/blue/ai-workshop/$USER/chrono`). Details, options and the
label-year choice: `docs/guides/stance-model.md`.

## Everything at once: `sbatch hpg/run_everything.sbatch`

One CPU job that starts the full feature build on HiPerGator, from the repo root:

```bash
cd /blue/ai-workshop/$USER/gator-quant-hacks && git pull && sbatch hpg/run_everything.sbatch
```

1. **Links the recordings** already downloaded by `hpg/fetch_audio.sbatch` into the feature package's layout, so nothing is downloaded twice (`hpg/link_fetched.py`).
2. **Builds the feature package's environment** on /blue if it is missing (`hpg/fedpress_pkg/slurm/00_setup.sh env`).
3. **Submits two chains, 2 GPUs each (4 at once):**
   - Features: small files -> audio + frames -> speech (Whisper timing, chair voice) -> face. The steps are `hpg/fedpress_pkg/slurm/submit_all.sh --only fetch,av,speech,face`.
   - Text: 36 chrono-BERT fine-tunes -> 12 scoring tasks -> merge (`hpg/submit_nlp.sh`, corrected label dates).

Options: the default GPU type is now b200 (rtx6000 was rejected with "Requested node configuration is not available"); `GPU_TYPE=rtx6000` switches back, and `SKIP_NLP=1` skips the text chain.

### When to run it

The press-conference text gate (G3, H1-primary on the registered 2023-2026 Powell sample) came out NO-GO on 2026-10-03. The team plan says voice and face (H2/H3) are not to be tested after a NO-GO. Use this build for a new, separately pre-registered forward test (for example, the 2026-10-28 press conference), not to mine the past sample.

Before running it, two things are needed:
- HiPerGator accounts are personal, and group allocations need the sponsor's approval (UF acceptable-use policy). Run it from the account holder's own login, with the `ai-workshop` sponsor's OK.
- Read `hpg/fedpress_pkg/README.md` and `hpg/fedpress_pkg/REVIEW.md` first.

## Backtests: `hpg/backtest_all.sbatch` and `hpg/v2_oos.sbatch`

Both are CPU jobs under account and QOS `ai-workshop`. The first run builds a Python 3.12 environment on /blue from
`hpg/backtest_requirements.txt`, which is pinned to the versions that produced the committed results.

**Every stage** (`backtests/run_all_backtests.sh all`: v2, press conference, H2/H3/H4):

1. Copy the three licensed Databento files to your home directory:
   `scp <market dir>/*__all_2016_2026.parquet <gatorlink>@hpg.rc.ufl.edu:`. Files sent in parts (`<name>.part01`,
   `.part02`, ...) are joined. `SHA256SUMS_market`, if present, is checked.
2. On HiPerGator, from the repository root, run `sbatch hpg/backtest_all.sbatch`.

The job moves the market files to `$GQH_DATA/market` (default `/blue/ai-workshop/$USER/gqh_data/market`). It reads
the feature tables from `FEDPRESS_ROOT` (default `/blue/ai-workshop/$USER/fedpress`). It packs the results into
`~/gqh_backtest_results.tgz`, leaving out the trade logs that carry price levels. `STAGE=presser`, `STAGE=h234` or
`STAGE=v2` runs one stage, for example `sbatch --export=ALL,STAGE=presser hpg/backtest_all.sbatch`.

**v2 only** (`sbatch hpg/v2_oos.sbatch`, the same job with `STAGE=v2`). It needs no market files. It needs the v2
input bundle `~/gqh_v2_bundle.tgz` (or its parts `.part01`, `.part02`, ... and `gqh_v2_bundle.tgz.sha256`). The bundle
holds the backtest engine and the private daily price files; the public part is in `backtests/v2/inputs/` (see
[data.md](data.md)).

The job recomputes the in-sample run and the one D-3 out-of-sample evaluation, then D-4. It compares every number
with `backtests/results/v2/`, `backtests/results/v2_oos/` and `backtests/results/v2_d4/` to 1e-9 relative and prints
PASS or FAIL. It chooses nothing and writes no decision record.

Read the log (`gqh-backtest_<job id>.log` or `v2-oos_<job id>.log`) for the stage summary at the end. A run counts as a
reproduction only when every stage you need reports that it reproduces the committed results (v2, D-4, presser) or
completed (h234).
