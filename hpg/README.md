# HiPerGator quick start: recordings and audio

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
- The video and caption links are signed and expire after a few hours, so the job rebuilds the manifest every time it starts (`build_manifest.py`, standard-library Python only).
- If `jie.xu` is a secondary group for you, keep `--account=jie.xu` (already set).
- If the burst QOS `jie.xu-b` is busy, edit the sbatch file to use `--qos=jie.xu`.
- The recordings are public-domain works of the US government (federalreserve.gov). They stay on /blue and are not committed to git.
- The voice, face and text feature stages, which use the B200s with at most 2 GPUs, follow in this folder next. They read `audio/`, `video/`, `captions/` and `transcripts/` from the same root.

## Text stance model (hawkish / dovish)

`bash hpg/submit_nlp.sh` trains the 36 walk-forward stance models (2015-2026, 3 seeds) and scores every document, as four chained jobs
under account and QOS `ai-workshop` (outputs in `/blue/ai-workshop/$USER/chrono`). Details, options and the
label-year choice: `nlp/README.md`.

## Everything at once: `sbatch hpg/run_everything.sbatch`

One CPU job that starts the full feature build on HiPerGator, from the repo root:

```bash
cd /blue/ai-workshop/$USER/gator-quant-hacks && git pull && sbatch hpg/run_everything.sbatch
```

1. **Links the recordings** already downloaded by `fetch_audio.sbatch` into the feature package's layout, so nothing is downloaded twice (`hpg/link_fetched.py`).
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
