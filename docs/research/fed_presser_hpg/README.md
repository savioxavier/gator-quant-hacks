# fedpress: FOMC press-conference features on HiPerGator

`fedpress` turns the Federal Reserve's press-conference videos and transcripts into per-meeting feature
tables. The features are the chair's text stance (statement vs Q&A answers, reporters' questions), voice
proxies and face proxies. Every row carries `known_at`, the UTC time a live observer could have known it.
The defaults follow `research/fed_presser_plan/team_FINAL_PLAN.md` plus deviation D1 (stance model). The
`plan_v0.md` options are switches in `config.yaml` and are off by default.

| | Default | Options (off) |
|---|---|---|
| Sample | 2016-01..2026-10: 75 held pressers today (Yellen 8, Powell 64, Warsh 3); 2026-10-28 joins after `manifest/build_manifest.py` is re-run | 2011-2015 calibration pressers (`sample.include_calibration=true`, 95 in all) |
| Clock | Whisper large-v3-turbo (faster-whisper) times + the transcript PDF's words | official WebVTT captions (`turns.clock_source`) |
| Chair segments | transcript speaker labels, checked by an ECAPA chair-voice gate | pyannote 3.1 / community-1 (gated) |
| Text | walk-forward ChronoBERT stance (D1, labels re-dated to their source documents per D1a; trained in step 5), CentralBankRoBERTa sentiment, Loughran-McDonald, hedges; FOMC-RoBERTa cross-check once its gated weights are cached | embeddings novelty |
| Voice, Powell only | audeering wav2vec2 arousal/dominance/valence + parselmouth F0, 8 s chunks inside answers | emotion2vec+, 3loi, openSMILE |
| Face, Powell only | MediaPipe + EmotiEffLib at 1 fps, SFace identity gate | py-feat or InsightFace at 2-5 fps |
| Never | opening remarks as features, any LLM, Warsh voice/face, YouTube or C-SPAN copies, market data on HPG | |

Design and schemas: `docs/ARCHITECTURE.md`. Stage details: `docs/TEXT.md`, `docs/FACE.md`. HiPerGator facts
with sources: `docs/HIPERGATOR_NOTES.md`.

**Group rule: at most 2 GPUs at once.** Every script respects it. GPU steps run one after another. Each GPU
step is an array of one-GPU tasks throttled to `%2`, or one job holding at most 2 GPUs. fedpress itself
rejects `compute.max_gpus > 2`, and every GPU job refuses to start if it sees more than 2 GPUs.

---

## 1. Before you start (once, on your laptop)

1. **HiPerGator access** in group `jie.xu` (sponsor Prof. Jie Xu). You log in with your GatorLink and Duo.
2. **Hugging Face account and token (optional but recommended).** The default run needs no token. Two
   gated models need one:
   * `gtfintechlab/FOMC-RoBERTa` is the plan's registered stance model, now a cross-check under D1.
     Click "Request access" on https://huggingface.co/gtfintechlab/FOMC-RoBERTa. The authors approve it
     by hand, so request it now.
   * `pyannote/speaker-diarization-3.1` (+ `pyannote/segmentation-3.0`) or
     `pyannote/speaker-diarization-community-1` are needed only if you turn on pyannote. Accept the terms
     on each model page while logged in to your own account.

   Then create a token: huggingface.co → Settings → Access Tokens → type "Read". Do not paste it into any
   file of this package; section 4 shows where it goes.
3. **Loughran-McDonald dictionary (optional).** It has an academic licence, so download the Master
   Dictionary CSV by hand from https://sraf.nd.edu/loughranmcdonald-master-dictionary/ and copy it to HPG
   (section 4). Without it the `lm_*` columns are NaN, and the run still completes.

## 2. Copy the package to HiPerGator

From the folder that contains `fed_presser_hpg` (Windows PowerShell, macOS or Linux). Each `ssh`/`scp` asks for
your password and a Duo push. The `mkdir` matters when `jie.xu` is a secondary group: UFRC creates
`/blue/<group>/<user>` only for your primary group.

```bash
ssh <gatorlink>@hpg.rc.ufl.edu 'mkdir -p /blue/jie.xu/$USER'
tar -czf fed_presser_hpg.tgz --exclude=__pycache__ --exclude=.ruff_cache --exclude=.pytest_cache fed_presser_hpg
scp fed_presser_hpg.tgz <gatorlink>@hpg.rc.ufl.edu:/blue/jie.xu/<gatorlink>/
```

Alternatives:
* `rsync -av --exclude __pycache__ fed_presser_hpg <gatorlink>@hpg.rc.ufl.edu:/blue/jie.xu/<gatorlink>/`
  (macOS/Linux/WSL).
* `git clone` on HPG if the package is in a repository you can reach (`module load git`).
* WinSCP or Cyberduck on Windows (not FileZilla).
* Globus: collection "UFRC HiPerGator". It is only worth it for bulk data such as the features coming back;
  the package itself is under 5 MB.

## 3. Log in and unpack

```bash
ssh <gatorlink>@hpg.rc.ufl.edu                # password, then Duo
cd /blue/jie.xu/$USER && tar -xzf fed_presser_hpg.tgz && cd fed_presser_hpg
bash slurm/00_setup.sh info                   # group, QOS limits, quota, internet: prints only
```

Check three things in that output:
* `jie.xu` is among your groups. If it is your secondary group, keep `ACCOUNT=jie.xu` (the default) and
  create `/blue/jie.xu/$USER` yourself if it does not exist.
* `showQos jie.xu` lists `gres/gpu=` 1 or more. If the cpu= or mem= values are smaller than the requests in
  section 6, lower them with `CPU_CPUS`, `CPU_MEM_GB` or `MEM_PER_GPU_GB`.
* `blue_quota` has about 110 GB free: about 52 GB of video for 75 meetings (67 GB for all 95), about 21 GB of
  frames, about 20 GB of models and environment, and about 3 GB of audio and features.

## 4. One-time setup (dev session, about 45 minutes)

Never build environments or download on a login node. Start a dev session first:

```bash
module load ufrc
srundev --time=04:00:00 --cpus-per-task=8 --mem=32gb
cd /blue/jie.xu/$USER/fed_presser_hpg

bash slurm/00_setup.sh env        # conda env at /blue/jie.xu/$USER/envs/fedpress (+ post-install fix-ups), 20-40 min
bash slurm/00_setup.sh token      # where the Hugging Face token goes (see below)
bash slurm/00_setup.sh models     # every enabled model at its pinned revision + stance labels, about 15 GB
bash slurm/00_setup.sh check      # CPU doctor: imports, ffmpeg, manifest, model cache
exit                              # leave the dev session
sbatch slurm/gpu_check.sbatch     # 5 min on one B200: driver, compute mode, torch on sm_100, CTranslate2, onnxruntime
```

**Hugging Face token** (only if you requested the gated models in section 1). Inside the dev session:

```bash
source env/activate.sh            # sets HF_HOME on /blue and HF_TOKEN_PATH=~/.cache/huggingface/token
hf auth login                     # paste the token; answer n to "add as git credential"; it goes to ~/.cache/huggingface/
bash slurm/00_setup.sh token      # sets the file to mode 600 (the value is never printed)
bash slurm/00_setup.sh models     # run again: now also fetches FOMC-RoBERTa / pyannote
```

The token stays in your home directory. /blue is readable by the whole group, so never put the token
there, in a job script or in `config.yaml`. GPU jobs run offline (`HF_HUB_OFFLINE=1`) from the cache, so
they never need the token.

**Loughran-McDonald:** copy the CSV to, for example, `~/data/LM_MasterDictionary.csv`, then add
`export FEDPRESS_LM_CSV=~/data/LM_MasterDictionary.csv` to `~/.bashrc`. Jobs inherit it.

Read `gpu_check`'s output in `fp-gpucheck_<jobid>.out`. Every line should be OK. A WARN on
`onnxruntime CUDA EP` is acceptable, because no default stage needs onnxruntime on the GPU. The
`compute_mode` should be `Default`; with `Exclusive_Process`, set `WORKERS_PER_GPU=1`.

## 5. Smoke test: one meeting

```bash
sbatch slurm/smoke.sbatch                                # 2025-09-17 (Powell), frames/face cut at 120 s
cat fp-smoke_<jobid>.out                                 # per-stage table at the end
```

The job runs every stage for one meeting on one GPU, in about 10-20 minutes plus queue wait. It downloads
the meeting first, so it needs the compute node's internet. Check the table at the end:

* `turns`: `timing_ok` true, `wer_proxy` below 0.35, `match_frac` above 0.8.
* `diarize`: `answer_verified_frac` near 1.
* `text`: a plausible `hawk_statement`.
* `aggregate`: `h1_gap` is printed.

`--max-seconds 120` (`MAX_SECONDS=120`) limits only frames and face. The opening remarks alone last 3-8
minutes, so with 120 s face enrols the chair but has no answer frames. Speech, text and aggregate always
process the whole meeting. Optional follow-ups:

```bash
MAX_SECONDS= sbatch slurm/smoke.sbatch                   # the whole meeting: the timings calibrate section 9
SMOKE_ID=20260916 sbatch slurm/smoke.sbatch              # plan gate G0: the Warsh meeting (text only for Warsh)
```

The `#SBATCH` lines of `smoke.sbatch` and `gpu_check.sbatch` ask for a B200. On another GPU type pass the partition
and GRES too: `GPU_TYPE=rtx6000 sbatch --partition=hpg-rtx6000 --gres=gpu:rtx-pro-6000:1 slurm/smoke.sbatch`
(`submit_all.sh` does this by itself).

Smoke outputs are real outputs. The full run reuses them, redoes the cut frames and face, and
re-aggregates. The stance models trained for the smoke meeting's year are also reused.

## 6. Full run

```bash
bash slurm/submit_all.sh --dry-run      # print the six sbatch commands, submit nothing
bash slurm/submit_all.sh                # submit the chain
```

| Step | Script | Resources (default) | Waits for |
|---|---|---|---|
| fetch | `01_fetch.sbatch` | CPU array of 4 tasks × 4 cores, 8 GB; outbound HTTPS | - |
| av | `02_audio_frames.sbatch` | CPU array of 4 × 16 cores, 48 GB | the matching fetch task (`aftercorr`) |
| speech | `03_speech.sbatch` | asr, turns, diarize, voice; GPU array `0-1%2`, 1 B200 + 14 cores + 88 GB per task, 6 workers per GPU | all of av (`afterok`) |
| face | `04_face.sbatch` | GPU array `0-1%2` (or a CPU array with `FACE_ON_CPU=1`) | all of speech |
| text | `05_text.sbatch` | 30 stance fine-tunes (shared queue), then the text stage; GPU array `0-1%2` | all of face |
| agg | `06_aggregate.sbatch` | CPU, 2 cores; `aggregate --all --force` then the panel files and status | all of text |

Each GPU array task takes a group of meetings (`--shard i/N`), and its `WORKERS_PER_GPU` processes drain
that group through a claim queue on its one GPU. A task releases its GPU when its group is done, so the
idle-GPU rule (a GPU at 0 % for 1 hour kills the job) cannot hit a finished GPU. `--time` requests are
computed from the measured rates (section 9) and the group size.

Why 2 tasks per GPU step by default, not one task per `workers_per_gpu` meetings: every array task waits in
the B200 queue separately, and UFRC warns that B200 waits are long. Two tasks use the 2-GPU allowance with
2 queue waits per step. `GROUP_SIZE=6 bash slurm/submit_all.sh` gives the other layout: 13 tasks of 6
meetings, one meeting per worker, still at most 2 running.

A job exits 0 when only some meetings fail. Those failures are recorded per meeting and do not stop the
chain. A fatal error does stop it: missing env, bad config, no network, or every meeting of a task failing
the same stage. Then the later steps are cancelled (`--kill-on-invalid-dep=yes`).

### Settings (environment variables; see `slurm/common.sh`)

| Variable | Default | Meaning |
|---|---|---|
| `GPU_TYPE` | `b200` | `b200`, `rtx6000` (`hpg-rtx6000`, 96 GB, Blackwell like the local 5090), `l4` (`hpg-turin`, 24 GB, starts fast), `a100` (needs `PARTITION=`: HiPerGator has had no A100s since June 2025) |
| `PARTITION`, `GRES_TYPE` | from `GPU_TYPE` | override the GPU partition / GRES type |
| `GPU_LAYOUT` | `array` | `job` = one job per GPU step holding `GPUS` (1 or 2) GPUs |
| `GPU_TASKS` / `GROUP_SIZE` | 2 / - | array tasks per GPU step / meetings per task |
| `WORKERS_PER_GPU` | 6 (b200), 4, 2, 1 | worker processes per GPU |
| `QOS_GPU` / `QOS_CPU` | `jie.xu` / `jie.xu` | `QOS_CPU=jie.xu-b` (burst) is allowed for CPU steps; GPUs have no burst QOS |
| `ACCOUNT` | `jie.xu` | Slurm account |
| `CPU_TASKS`, `CPU_CPUS`, `CPU_MEM_GB` | 4, 16, 48 | CPU arrays |
| `MEM_PER_GPU_GB`, `CPUS_PER_GPU` | 16 + 12 × workers, 14 | per GPU task |
| `FACE_PRESET` | `default` | `pyfeat2` / `pyfeat5` = plan_v0 py-feat at 2 / 5 fps (build its env first: `bash slurm/00_setup.sh env-pyfeat`) |
| `FACE_ON_CPU` | 0 | 1 = face step as a CPU array (it is CPU-bound at 1 fps; frees the B200 queue) |
| `FP_SET` | empty | extra config overrides for every stage, e.g. `FP_SET="sample.include_calibration=true"` for all 95 pressers, `FP_SET="diarize.pyannote.enabled=true"` |
| `TIME_FETCH`, `TIME_AV`, `TIME_SPEECH`, `TIME_FACE`, `TIME_TEXT`, `TIME_AGG` | computed | override a `--time` (HH:MM:SS) |
| `FEDPRESS_ROOT` | `/blue/jie.xu/$USER/fedpress` | data root |
| `FP_ENV` | `/blue/jie.xu/$USER/envs/fedpress` | conda env |
| `MAIL_USER` | empty | `<gatorlink>@ufl.edu` = mail on END/FAIL |
| `FP_STRICT` | 0 | 1 = any meeting failure fails the job |
| `FP_FORCE` | empty | steps to redo where already done, e.g. `"av face"` after switching `FACE_PRESET` |

Examples:

```bash
GPU_TYPE=rtx6000 bash slurm/submit_all.sh                      # if the B200 queue is too long
GPU_LAYOUT=job GPUS=2 bash slurm/submit_all.sh                 # one 2-GPU job per GPU step
bash slurm/submit_all.sh --from speech                         # resume (done meetings are skipped)
cp -r $FEDPRESS_ROOT/panel $FEDPRESS_ROOT/panel_default       # py-feat output replaces the default face tables
FACE_PRESET=pyfeat5 FP_FORCE="av face" bash slurm/submit_all.sh --only av,face,agg   # plan_v0 face option
FP_SET="sample.include_calibration=true" bash slurm/submit_all.sh # all 95 pressers (2011-2015 = calibration)
```

`submit_all.sh` refuses to start a second chain while `fp-*` jobs are queued, so two chains cannot push the
group past 2 GPUs or race on the same meetings. Override with `--allow-concurrent` only if you know why.

## 7. Monitoring

```bash
squeue --me                                    # PD = pending (Reason: Dependency, Priority, QOSGrpGRES ...)
sacct -X -S today -o JobID%20,JobName%16,State,Elapsed,ReqTRES%45,ExitCode
python slurm/status.py                         # meeting x stage matrix, totals, mean seconds, failures
python slurm/status.py --failed                # failures with their error line and log file
python slurm/status.py --jobs                  # also your fp-* jobs
module load ufrc; jobnvtop <jobid>             # GPU use of a running job
tail -f $FEDPRESS_ROOT/logs/slurm/fp-03-speech_<jobid>_0.out
```

Run `source env/activate.sh` before `python slurm/status.py`. Logs:

| What | Where |
|---|---|
| Slurm stdout/stderr | `$FEDPRESS_ROOT/logs/slurm/<job-name>_<jobid>_<task>.out` |
| Worker logs | `$FEDPRESS_ROOT/logs/launch/<run_id>/<stage>_wNN.log` |
| Per meeting and stage (JSON lines) | `$FEDPRESS_ROOT/logs/<stage>/<presser_id>.jsonl` |
| Done and failure markers | `$FEDPRESS_ROOT/meetings/<id>/_done/<stage>.json` and `<stage>.failed.json` (with the traceback) |
| Submissions | `$FEDPRESS_ROOT/logs/slurm/submit_<time>.tsv` |

**Rerun failures:** `bash slurm/rerun_failed.sh` prints the failures and resubmits from the earliest step
with unfinished work. Finished meetings are skipped, so only failed meetings and their downstream stages run
again. Read the log before rerunning: a meeting that fails twice the same way needs a fix, not a third try.
To redo meetings that finished but are wrong, run the stage with `--force` (in a job). Then run `agg`
again; it always runs with `--force`.

## 8. Outputs

```
$FEDPRESS_ROOT/
  meetings/<presser_id>/raw/        video.mp4, transcript.pdf, statement.html, captions.vtt, fetch.json
                       audio/ frames/ asr/                     media artefacts (no known_at)
                       turns/       turns.parquet, words.parquet, anchor.json      (known_at from here on)
                       diarize/ voice/ face/ text/            per-stage tables
                       features/    answers.parquet, meeting.parquet, windows.parquet
  panel/   answers.parquet  meetings.parquet (88-meeting calendar, has_presser)  windows.parquet
           text_units.parquet  answers_causal_z.parquet  meetings_causal_z.parquet  status.parquet
           dataset_meta.json  status.txt  status_report.txt
  models/stance_walkforward/<key>/seed<s>/                    the 30 fine-tuned stance models + registry.json
```

Every table from `turns` on has `presser_id, meeting_date, chair, sample_role, t_start_s, t_end_s,
t_end_utc, known_at, latency_s, anchor_source, anchor_unc_s`. `known_at = t_end_utc + 30 s`. Rows also carry
`t_end_utc`, so another latency needs no rerun. Statement rows use the scheduled release time. The anchor
defaults to "greeting = scheduled presser minute", with unknown uncertainty (`anchor_unc_s` = NaN). Add
measured start times to `manifest/anchors.csv` (format: `manifest/anchors.example.csv`) before the
predictive tests. The plan drops meetings whose start uncertainty exceeds 30 s.

**Copy the features back** (about 0.5-1 GB without the media):

```bash
# on the laptop; one Duo prompt per command
scp -r <gatorlink>@hpg.rc.ufl.edu:/blue/jie.xu/<gatorlink>/fedpress/panel ./fedpress_panel
rsync -av --exclude='raw/' --exclude='audio/' --exclude='frames/' --exclude='asr/' --include='*/' \
  --include='*.parquet' --include='*.json' --exclude='*' \
  <gatorlink>@hpg.rc.ufl.edu:/blue/jie.xu/<gatorlink>/fedpress/meetings/ ./fedpress_meetings/   # macOS/Linux/WSL
```

For many files, Globus is faster: collection "UFRC HiPerGator", path `/blue/jie.xu/<gatorlink>/fedpress/panel`.

**Market data is not part of this package.** Do not put a Databento key on HiPerGator. Join ZT/ZF/ZN/ES 1-minute
bars on the local machine as a separate step. First print `get_cost` for the exact window (presser days,
13:30-16:30 ET) and confirm it fits the remaining credit; download nothing before that. Then join on
`known_at` with the plan's rule (next 1-minute open after τ).

## 9. Expected wall-clock and GPU-hours

**Measured** on the local RTX 5090 (Windows, torch 2.8.0+cu128, sm_120), one process per stage and meeting,
small batches (`asr.batch_size=4`, `voice.batch_size=4`, `diarize.ecapa.batch_size=16`; peak 391 W). Each
time includes imports and model loading. Meetings: 2019-05-01 (Powell, 41.2 min of video) and 2020-03-03
(Powell, 13.9 min):

| Stage | 2019-05-01 (41 min) | 2020-03-03 (14 min) | Rate used below |
|---|---|---|---|
| fetch (HTTPS; 565 / 190 MB) | 21 s | 42 s | 4.5-27 MB/s per stream |
| audio (CPU) | 17.9 s | 7.0 s | 26 s per video-hour |
| frames, 1 fps (CPU) | 24.7 s | 9.0 s | 36 s per video-hour (Powell) |
| asr, turbo fp16 | 13.0 s | 24.8 s (first CUDA run) | 19 s per video-hour |
| turns | 0.6 s | 0.4 s | 1 s per video-hour |
| diarize, ECAPA (651 / 212 windows) | 7.9 s | 18.1 s (first run) | 11.5 s per video-hour |
| voice (176 / 54 chunks) | 8.1 s | 8.2 s | 11.8 s per video-hour (Powell) |
| face, default 1 fps (1,566 / 562 frames; 52 / 44 fps) | 32.8 s | 15.5 s | 48 s per video-hour (Powell) |
| text (CentralBankRoBERTa + 3 stance seeds; 128 sentences) | - | 7.3 s | 10 s per meeting |
| one stance fine-tune (1,654 rows, early stop at 6-7 epochs) | 40-69 s, mean 56 s | | 56 s per fine-tune |
| aggregate | 0.6 s | 0.6 s | 1 s per meeting |

**Projection.** The default sample is 75 meetings: 63.1 video-hours, of which Powell is 64 meetings and 53.4
hours (voice, face and frames run for Powell only). All 95 meetings are 82.4 video-hours with the same Powell
hours. Stance training is 30 fine-tunes for 75 meetings and 45 for 95.

Assumed speed ratios:
* **5090 with 2 workers:** 1.6 × one process. Measured: 3 fine-tunes ran in 112 s with 2 workers, against
  170 s one after another.
* **B200, inference stages:** one worker process on a B200 ≈ 0.8 × one 5090 process. Most of a stage's time
  is CPU-side work (decoding, VAD, feature extraction, model loading, MediaPipe), and a node's Xeon 8570
  cores are slower per core than a desktop CPU. Six workers per B200 give 2.5-4.8 × one 5090 process
  (the low end if the 14 cores saturate).
* **B200, stance training:** 2 × one 5090 process per GPU. Training runs in fp32 with TF32 off (fixed
  settings), and B200 fp32 CUDA-core throughput is no higher than a 5090's.
* **Fixed costs not shown below:** about 3 minutes of startup per GPU job (imports, model loads from /blue),
  and the B200 queue wait, which is often longer than the run itself.

Default team stack (face = MediaPipe + EmotiEffLib, 1 fps), 75 meetings:

| Stage | RTX 5090 (2 workers) | 1 × B200 | 2 × B200 | B200 GPU-hours |
|---|---|---|---|---|
| fetch, 52 GB (CPU array) | 35 min at 25 MB/s | 10-40 min | same | 0 (about 8 core-h) |
| audio + frames (CPU array) | 15 min (8 workers) | 5-15 min | same | 0 (about 10 core-h) |
| asr | 12 min | 4-8 min | 2-4 min | |
| turns + diarize | 8 min | 3-5 min | 1.5-3 min | |
| voice | 7 min | 2-4 min | 1-2 min | |
| **speech step (03)** | **27 min** | **9-17 min** | **5-9 min** | 0.2-0.4 |
| **face step (04)** | **27 min** | **9-17 min** | **4.5-8.5 min** | 0.15-0.3 |
| stance training (30 fine-tunes) | 18 min | 14 min | 7 min | |
| text | 8 min | 2.5-5 min | 1.5-2.5 min | |
| **text step (05)** | **26 min** | **17-19 min** | **8.5-10 min** | 0.3-0.35 |
| aggregate + panel (CPU) | 2 min | 2 min | 2 min | 0 |
| **GPU steps in total** (plus about 10 min of startup) | **about 1.3 h** | **about 45-65 min** | **about 30-40 min** | **about 0.8-1.2** |

All 95 meetings (`FP_SET="sample.include_calibration=true"`): asr, diarize and text grow by 30 %, and stance
training to 45 fine-tunes. GPU steps: RTX 5090 about 1.6 h, 1 × B200 about 55-75 min, 2 × B200 about 35-45 min
(1.0-1.4 B200 GPU-hours). Fetch moves 67 GB.

plan_v0 face option (py-feat from its own env, frames decoded in the face step; replaces the face row above):

| Face preset | RTX 5090 (2 workers) | 1 × B200 | 2 × B200 | B200 GPU-hours |
|---|---|---|---|---|
| default, 1 fps | 27 min | 9-17 min | 4.5-8.5 min | 0.15-0.3 |
| `pyfeat2` (2 fps) | 1.5 h | 30-60 min | 15-30 min | 0.5-1.0 |
| `pyfeat5` (5 fps) | 3.8 h | 1.3-2.4 h | 40-75 min | 1.3-2.5 |

The py-feat rates come from docs/FACE.md: about 30 frames/s per worker on the 5090, against 52 measured for the
default path. HiPerGator investment allocations are counted in GPUs held (NGUs), not in charged SUs; the
GPU-hour column is what the run takes out of the group's 2-GPU allowance. Replace these projections with
the `s/video-h` and `mean s` columns that `python slurm/status.py` prints after the smoke test or the
first run.

## 10. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Job pending with `QOSGrpGRES` / `QOSGrpCpuLimit` / `QOSGrpMemLimit` | The group's pool is in use (labmates' jobs count too) or the request exceeds `showQos jie.xu`. Wait, or lower `MEM_PER_GPU_GB`, `CPUS_PER_GPU`, `CPU_CPUS`. |
| B200 jobs pending for hours (`Priority`, `Resources`) | Expected. `GPU_TYPE=rtx6000` (same commands) or `GPU_TYPE=l4` (24 GB, `WORKERS_PER_GPU=2`). `FACE_ON_CPU=1` takes the face step off the GPU queue. |
| `Job violates accounting/QOS policy` | `--account/--qos` do not match your groups (`showAssoc $USER`), or the request exceeds a QOS limit. |
| `01_fetch` exits 4: "no outbound HTTPS" | Compute nodes cannot reach the internet. `srundev --time=06:00:00 --cpus-per-task=4 --mem=8gb`, then `bash slurm/00_setup.sh fetch`, then `bash slurm/submit_all.sh --from av`. |
| `fetch` fails with a size mismatch | Brightcove changed the rendition or the download broke. Rerun; the MP4 resumes with HTTP Range. If the size changed for good, rebuild the manifest (`manifest/build_manifest.py`). |
| A stage fails with `LocalEntryNotFoundError` | A model is not in the cache (GPU jobs are offline). Run `bash slurm/00_setup.sh models` in a dev session. |
| `text` fails: "walk-forward model ... missing" | Step 5 trains the models before scoring. A meeting scored outside step 5 needs `python -m fedpress.train.stance_walkforward train --years <Y>` (GPU) first. |
| `aggregate` fails: voice/face pending | `aggregate.wait_for`: voice or face is not finished for that meeting. Finish them, or rerun `agg` after them. |
| A job is killed for an idle GPU | A GPU sat at 0 % for an hour: usually a hung download or a CPU-only step on a GPU node. Check the job's `.out` and the worker logs. Never run fake loads (that gets the account suspended). |
| `CUDA error: no kernel image` / `sm_100` | The env is not the cu128 build. Run `python -c "import torch; print(torch.cuda.get_arch_list())"`; it must list `sm_100`. Rebuild with `FORCE=1 bash slurm/00_setup.sh env`. |
| Out of host memory with 6 workers | Use `WORKERS_PER_GPU=4` or `MEM_PER_GPU_GB=128`. |
| `Disk quota exceeded` | `blue_quota`. Set `frames.jpeg_quality=85` or delete `meetings/*/frames` after the face step (about 21 GB). Raw videos can go after all steps (about 52 GB). |
| `05_text` stops: "stance models trained with other labels or settings" | The labels or training settings changed after those fine-tunes were made (for example labels built before the D1a re-dating). The job prints one `rm -rf .../seed<s>` line per stale model; run them, then `bash slurm/submit_all.sh --from text`. |
| A rerun skips meetings as claimed (`C` in `status.py`) | A killed job (time limit, out of memory, `scancel`) leaves claim files. They are taken over automatically once Slurm no longer lists that job, or after `runtime.claim_ttl_s` (6 h) if `squeue` cannot tell. |
| `sbatch: error: Batch script contains DOS line breaks` or `$'\r': command not found` | The scripts were saved with Windows line endings on the way over (an editor or `git` with `core.autocrlf`). Fix in the package folder: `sed -i 's/\r$//' slurm/*.sh slurm/*.sbatch env/*.sh env/*.yml`. |
| `stage.stale` warnings | The config changed since that output was made. The meeting is still skipped; add `--force` to redo it. |
| Login-node warning or kill | Heavy commands belong in `srundev` or jobs. `submit_all.sh`, `status.py` and `rerun_failed.sh` are light. |

## 11. Licences

Non-commercial models are allowed for this research build. Disclose them in any write-up.

| Model / data | Use | Licence |
|---|---|---|
| openai/whisper-large-v3-turbo (CTranslate2 conversion mobiuslabsgmbh/faster-whisper-large-v3-turbo) | clocks | MIT |
| manelalab/chrono-bert-v1-<year>1231, fine-tuned here on gtfintechlab/fomc_communication | primary stance (D1) | MIT base; CC BY-NC 4.0 labels, so the fine-tunes are non-commercial |
| `manifest/label_dates.parquet` (label sentences re-dated from github.com/gtfintechlab/fomc-hawkish-dovish files, D1a) | training-label dates | CC BY-NC 4.0 (derived from the TDW repository and dataset) |
| gtfintechlab/FOMC-RoBERTa | stance cross-check | CC BY-NC 4.0, gated (manual approval) |
| Moritz-Pfeifer/CentralBankRoBERTa-sentiment-classifier | agent sentiment | MIT |
| Loughran-McDonald Master Dictionary | word counts | free for academic use |
| audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim | vocal_proxy | CC BY-NC-SA 4.0 |
| speechbrain/spkrec-ecapa-voxceleb | chair voice check | Apache-2.0 |
| pyannote speaker-diarization-3.1 (+ segmentation-3.0, wespeaker) / community-1 | optional diarization | MIT / CC BY 4.0; gated (accept terms) |
| MediaPipe Face Landmarker | expression_proxy | Apache-2.0 |
| SFace (OpenCV Zoo) | face identity gate | Apache-2.0 |
| EmotiEffLib enet_b0_8_va_mtl | expression_proxy | code Apache-2.0; weights trained on AffectNet (non-commercial research) |
| py-feat face_multitask_v2 / InsightFace buffalo_l | plan_v0 options | research-only / non-commercial weights |
| emotion2vec+, 3loi WavLM, Qwen3-Embedding, all-MiniLM-L6-v2, Qwen3-ForcedAligner, wav2vec2-xlsr-53-english | options | FunASR model licence / MIT / Apache-2.0 / Apache-2.0 / Apache-2.0 / Apache-2.0 |
| praat-parselmouth | F0 | GPL-3.0 |
| openSMILE | option | audEERING research licence |
| Fed videos, transcripts, statements (federalreserve.gov, Brightcove player) | input | US government works, public domain; attribute the Board |

Pinned revisions and sha256 values are in `config.yaml` → `models:`. `prefetch-models` records what it fetched in
`$FEDPRESS_ROOT/cache/models_lock.json`.

## 12. Decide before looking at results

These are placeholders in `config.yaml`. Pre-register them before any feature is joined to returns:

* stance gate `train.stance_walkforward.gate.min_heldout_macro_f1` (null now; the 2020 models scored 0.58-0.60
  held-out macro-F1 in the local test);
* score `text.score` (share, D1) vs prob (A-10); seeds 3 (D1) vs 5 (A-14); weighting `aggregate.h1_weighting`;
* alignment `turns.align.max_wer_proxy` 0.35, `min_matched_frac` 0.80;
* face gates and masks (`face.gates`, `face.masks`), checked against hand-labelled frames before H3;
* diarize calibration (`diarize.ecapa.*`);
* per-meeting start times in `manifest/anchors.csv`: without them `anchor_unc_s` is unknown and the plan's 30 s
  rule cannot be applied.

## 13. Local test on a Windows RTX 5090 (optional)

The HiPerGator path is Linux. On Windows the same code ran end to end with these adjustments:

* Use a venv with Python 3.11 or 3.12, and torch 2.8.0+cu128 from `https://download.pytorch.org/whl/cu128`.
* Paths over 260 characters break pip and the Hugging Face cache. Keep `FEDPRESS_ROOT` and `HF_HOME` short,
  e.g. `D:\fp`, or map a drive with `subst`.
* Set `HF_HOME` before Python starts (`env/activate.sh` does this on Linux). Without symlink rights, Hugging
  Face copies files instead of linking them.
* Run with `--set compute.gpu_type=local5090` (2 workers) and small batches if the card is power-limited.
* There is no conda ffmpeg; the `imageio-ffmpeg` binary is used.
