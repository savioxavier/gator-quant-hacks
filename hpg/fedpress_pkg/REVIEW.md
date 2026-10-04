# Review of the fedpress HiPerGator package (2026-10-03)

An adversarial review of everything under `fed_presser_hpg/`: Slurm scripts against `docs/HIPERGATOR_NOTES.md`,
environment pins on Blackwell (B200 sm_100), paths and `$FEDPRESS_ROOT`, idempotency and resume, secrets,
licences, causality, chair identification, the caption-less meetings, the two unscheduled 2020 pressers, and
the README walked through as a first-time HiPerGator user. Clear errors were fixed in place; the rest is listed
under remaining risks.

## How it was checked

| Check | Result |
|---|---|
| `python -m compileall fedpress slurm manifest tests` | clean |
| `pytest` | 62 passed (59 before, plus 3 new tests: D1a label dating, the claim takeover, LF line endings) |
| `bash -n` on every `slurm/*.sh`, `*.sbatch` and `env/*.sh`; `submit_all.sh --dry-run` (default, `FACE_ON_CPU=1`, `GROUP_SIZE=6`, a fake `showQos`) | clean; at most 2 GPUs per step, `%2` throttle, `aftercorr` only between the two CPU arrays |
| `uv pip compile` of the pip sections of both env files for Linux x86_64 / CPython 3.11 with the cu128 index | both resolve; saved as `env/resolved-uv-{main,pyfeat}-linux-cp311.txt` |
| PyPI and cu128-index wheel metadata for the key packages; ELF `NEEDED` entries of the torchcodec cu128 wheels | see issue 2 |
| Transcript parser over all 95 PDFs (roles, labels, header remnants) | chair found in 95/95, including the typos CHAIRIMAN/CHAIMRAN POWELL, CHAIRMAN BERNAKE, CHARIMAN WARSH; see issue 4 |
| `stance_walkforward prepare` with the real HF dataset and GitHub files, then a 1-epoch CPU fine-tune | all 2,480 rows dated; model meta records `train_max_source_date` 2019-11-01 for the 2020 model |
| Local GPU run | not done: the RTX 5090 was already at 493 W / 93 % from another process (12VHPWR guard) |

## Issues found and fixed

| # | Severity | Issue | Fix |
|---|---|---|---|
| 0 | Critical (nothing would run) | `slurm/common.sh`, which every job and helper sources, had Windows CRLF line endings, as did 26 other files (config.yaml, most of `fedpress/`, tests). On Linux, sourcing it fails (`$'\r': command not found`, functions and variables carry a trailing CR). The local tests passed only because Git Bash ignores CR. | Converted every text file in the package to LF. Added `.gitattributes` (`eol=lf` for scripts, Python and YAML) and a test that fails on any CR in `slurm/` or `env/` scripts. README troubleshooting gives the `sed` fix in case an editor or `core.autocrlf` brings CRLF back. |
| 1 | High (look-ahead) | Deviation D1a / fedspeak_v2 Amendment 3 was not implemented. `fedpress/train/labels.py` used the dataset's `year` column, which differs from the source document's year for 2,336 of 2,480 rows. "Labels <= Y-1" therefore let 123 (2022 model) to 486 (2016 model) deduplicated rows from documents dated Y or later into every 2016-2022 stance model, and the A-14 held-out gate tested on the wrong rows. The team's own check (`fed_presser_plan/checks_r3_validity/r3_label_dates.out`) names this file. | Shipped the team's re-dating table as `manifest/label_dates.parquet` (+ `_meta.json`, sha256 `16a54100...` pinned in `config.yaml`) and its builder as `manifest/build_label_dates.py` (constants inlined, pinned-commit checkout added). New `train.stance_walkforward.data.redate` (on by default): `year` becomes the source-document year, `dataset_year` keeps the original value, and undated rows get 2022 (kept out of every 2015-2022 model). `doc_type` comes from the table, so it is known for all rows (mm 1,074, sp 1,009, pc 322). Labels built without re-dating are rebuilt by `prepare` and refused by `train` and the text stage. Model `meta.json` records `train_max_source_date` and `year_basis`. Docs: TEXT.md section 3, ARCHITECTURE.md, README, manifest/README.md. |
| 2 | High (env) | The torchcodec cu128 wheels (0.7.0 in the main env, 0.11.1 in the py-feat env) link `libnppicc.so.12`, but nothing installed NPP. torchcodec's native core would not load, which breaks pyannote 4 audio decoding (and whisperx through it) and py-feat's torchcodec import. | Pinned `nvidia-npp-cu12==12.3.3.100` (the NPP of CUDA 12.8) in both env files and in the `torch` extra. `env/activate.sh` already puts `site-packages/nvidia/*/lib` on `LD_LIBRARY_PATH`. `doctor` now checks that the torchcodec core loads. |
| 3 | High (setup) | `00_setup.sh env` ran `tool=$(load_conda)`, so `module load conda` happened in a subshell and its PATH change was lost. `mamba`/`conda` would then be "command not found" unless conda was already on PATH. It also passed `-y` to `conda env create`, which older conda rejects. | `load_conda` now runs in the calling shell and sets `CONDA_TOOL`; `-y` is passed only to mamba. |
| 4 | Medium (text) | The page-header regex missed pypdf variants ("Powe ll's", "P ress Conference", "PressConference", "Press Conference Call"). Header text leaked into 5 transcripts: chair labels like "FINAL CHAIR YELLEN" (still matched by the fuzzy rule), and on 2020-03-15 "FINAL MICHELLE SMITH" was parsed as a reporter, which created a fake question and shifted `qa_idx`. Header words were also glued into turn texts. | Made `HEADER_RE` robust and strip a leading `FINAL ` from labels. The re-check over all 95 PDFs found no header remnants and no FINAL labels, and 2020-03-15 now has 17 moderator turns and 19 questions. |
| 5 | Medium (resume) | Claims left by a job killed by its time limit, out of memory or `scancel` sit on another node, so the pid check cannot see them. They blocked those meetings, and the stance fine-tunes, for `claim_ttl_s` = 6 h after a resubmit. The check treated claimed meetings as "not failed", so the chain went on with them blocked. | `io.claim_is_stale` also takes over a claim whose Slurm job `squeue` no longer lists. Any doubt (no squeue, an error) falls back to the TTL. Training claims now record the job id and use the same rule. Covered by a new test. |
| 6 | Medium (Slurm) | `04_face.sbatch` had `#SBATCH --gres=gpu:b200:1`. With `FACE_ON_CPU=1`, `submit_all.sh` overrides the partition to hpg-default but not the GRES, so the CPU job would ask hpg-default for a B200 and be rejected. | Removed the header GRES. `submit_all.sh` always passes it for the GPU face step. |
| 7 | Medium (README) | The CPU "check" in the dev session ran `doctor` with the b200 profile, so it printed FAIL lines for CUDA on a node without a GPU. | `00_setup.sh check` runs `doctor --set compute.gpu_type=cpu`. |
| 8 | Medium (B200) | The CTranslate2 check only counted devices, which passes even when the wheel has no kernels for sm_100. | `doctor` (run by `gpu_check.sbatch`) now decodes 2 s through the cached Whisper model on the GPU, as a hard check. |
| 9 | Low | A finished stance model made with other labels or settings was skipped silently (`train` never overwrites without `--force`). Step 5 then waited 20 min for "todo" models. | `stance_walkforward status` prints `stale`. Step 5 stops at once and prints the `rm -rf .../seed<s>` lines to run (README troubleshooting). |
| 10 | Low | CPU-profile workers took their thread count from the profile (16), not the job: 4 fetch workers on 4 cores ran 4 threads each. | Threads come from `SLURM_CPUS_PER_TASK`. |
| 11 | Low | A job submitted from outside the package folder failed with confusing undefined-function errors. | Each `*.sbatch` checks for `slurm/common.sh` and tells the user to `cd` to the package. |
| 12 | Low | `06_aggregate` redirected into `panel/` before that folder had to exist. | `mkdir -p`. |
| 13 | Low (README) | If `jie.xu` is a secondary group, `/blue/jie.xu/<user>` may not exist, so the first `scp` fails. Smoke and GPU-check jobs on another GPU type need `--partition` and `--gres` on the command line. | README section 2 creates the folder first. Section 5 and the smoke header show the rtx6000 command. |
| 14 | Low | Setting `turns.clock_source=vtt` makes the 7 default-sample meetings without captions fail, and the config comment even suggested disabling ASR. | The comment now recommends `vtt_then_asr` with ASR left on. |
| 15 | Low | No warning when a GPU task asks for more cores than the group QOS allows (it would pend forever). | `submit_all.sh` warns from `showQos` (best effort) when cores exceed `cpu=` or when `gres/gpu=0`. |

## Verified correct (no change needed)

* **Slurm names and syntax** match the notes: `hpg-b200` + `--gres=gpu:b200:N`, `hpg-rtx6000` + `rtx-pro-6000`,
  `hpg-turin` + `l4`, CPU `hpg-default`, `--account=jie.xu --qos=jie.xu` on every job, no burst QOS on GPU jobs,
  `--array=0-N%2`, `afterok` between GPU steps (an `aftercorr` there could hold 4 GPUs), `--kill-on-invalid-dep`,
  14 cores per B200, `--mem=<n>gb` as in UFRC's examples, `$TMPDIR` scratch. The 2-GPU cap is enforced in
  config, `plan_slots`, `submit_all.sh` and every GPU job.
* **Environment** on Blackwell: torch 2.8.0+cu128 (sm_100 and sm_120 kernels, cuDNN 9.10); CTranslate2 4.8.2
  (CUDA 12, cuDNN 9); onnxruntime-gpu 1.26.0 (cp311 manylinux_2_28; compute_90 PTX JIT on sm_100, and no default
  stage needs it on the GPU); pyannote.audio 4.0.7 and whisperx 3.8.6 (both on torch 2.8); py-feat 2.1.3 in its
  own torch 2.11+cu128 env; insightface 2.0 and emotiefflib 1.1.1 ship pure wheels; mediapipe 1.0.1 has a
  manylinux_2_28 wheel (el9 glibc 2.34). Both envs resolve (uv).
* **Paths:** `FEDPRESS_ROOT` defaults to `/blue/jie.xu/$USER/fedpress` the same way in `config.yaml`,
  `common.sh`, `activate.sh` and the Apptainer definition. Package-relative manifest paths resolve via
  `cfg.pkg_path`.
* **Secrets:** no token or key in any file. The HF token comes from `$HF_TOKEN` or `~/.cache/huggingface/token`
  (`HF_TOKEN_PATH` is pinned back to `$HOME`, and huggingface_hub 0.36 puts `stored_tokens` next to it, not on
  /blue). The Brightcove policy key is read at run time and kept in memory only. The manifest's `fastly_token`
  URLs are expired public CDN signatures. No file carries an AI-attribution line.
* **Causality:**
  * `known_at` = anchor + (segment end − anchor media time) + 30 s, enforced non-null by `write_table`.
  * Statement rows use the scheduled release time.
  * Sentence end times round later, never earlier.
  * Frame slots show the latest frame at or before the slot time.
  * `loudnorm` is off; voice chunks are normalised only by their own statistics.
  * ECAPA and face enrolment use the opening remarks only, which come before every Q&A row.
  * Running means use only answers that have already ended.
  * `causal_z` uses strictly earlier meetings of the same chair, with a 4-meeting burn-in.
* **Chair identification:** labels come from the transcript of each meeting and the chair from the manifest
  (all 95 agree). ECAPA enrolls a voiceprint per meeting from the opening, so Warsh's 3 meetings need no history.
  Voice and face are Powell-only, so Bernanke and Yellen need no references.
* **Caption-less meetings** (12; 7 in the sample): the default ASR clock does not need captions, `vtt_check` is
  skipped, and fetch records the caption as absent.
* **Unscheduled 2020 pressers:**
  * Times: 10:00/11:00 ET on 2020-03-03 and 17:00/18:30 ET on Sunday 2020-03-15. The 2020-03-03 meeting date
    is 03-02.
  * Both are in the sample and in the 88-meeting calendar.
  * 2020-03-15 was an audio-only call. The face stage handles a failed enrolment: rows get `identity_ok` false
    and the meeting does not fail.

## Remaining risks (not fixable from here)

1. **Clock anchor (look-ahead risk).** The default anchor is "first chair word = scheduled presser minute"
   (team-plan fallback). A presser that starts d seconds late gets every `known_at` d seconds too early, and
   pressers often start 0-3 min late. `manifest/anchors.csv` is empty and `anchor_unc_s` is NaN, so the plan's
   30 s rule cannot be applied yet. Until measured start times exist, treat the 60 s appendix latency as the
   minimum robustness check and say so in the write-up.
2. **Nothing has run on HiPerGator yet.** Unverified there: the conda/pip build (pip's resolver may be slow;
   `env/resolved-uv-*.txt` is a fallback), CTranslate2 and onnxruntime on sm_100, compute mode (needed for 6
   workers per GPU), compute-node internet, `aftercorr` and `%2` behaviour, and the jie.xu QOS cpu/mem pool.
   The first steps are `00_setup.sh info`, then `gpu_check.sbatch` (now a real Whisper decode), then
   `smoke.sbatch` (plus `SMOKE_ID=20260916` for gate G0).
3. **Inputs still owed by the team:**
   * FOMC-RoBERTa access (gated, manual approval; it is a cross-check under D1).
   * The Loughran-McDonald CSV.
   * Pre-registered values for the placeholders: stance gate `min_heldout_macro_f1`, score, seeds, weighting,
     WER/match, face gates and masks, ECAPA calibration.
4. **Label dating** relies on the team's table. It uses the earliest containing document, as Amendment 3
   prescribes, and matches on substrings of 6 or more words, so a generic sentence can be dated to an earlier
   document than the one it was labelled from. The local check used the actual HF files: all 2,480 rows matched
   the table.
5. **Flags that use the whole meeting:** `timing_ok`, WER-proxy and `match_frac`. Use them only as
   pre-registered exclusions, never as an adaptive filter. The text is the edited official transcript, not what
   a live listener had.
6. **Transcript structure:**
   * Follow-up questions get their own `qa_idx`.
   * Transcripts before 2020 have no moderator labels, so the chair's call on the next reporter ("Steve.")
     stays at the end of the answer text (a word or two per answer).
7. **Local scratch data** under `hpg_build/integrate/root` still has labels and stance models made with the old
   dating rule. fedpress now refuses them (rebuild with `prepare --force`). This does not affect HiPerGator.
8. **Licences:** non-commercial components are audeering (CC BY-NC-SA), the EmotiEffLib weights (AffectNet),
   FOMC-RoBERTa, the TDW labels, label dates and the fine-tunes built from them (CC BY-NC), and the py-feat and
   InsightFace weights. praat-parselmouth is GPL-3.0. All are listed in the README; they must be disclosed in
   any write-up.
9. `graphify update .` was not run: it writes outside this folder.
