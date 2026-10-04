# HiPerGator notes for the FOMC presser feature build

Checked on 2026-10-03 against https://docs.rc.ufl.edu (help.rc.ufl.edu now 301-redirects there). The cached
copy of the GPU Access page was byte-identical to the live page on that date.

Tags: **[doc]** stated in UFRC documentation (URL given). **[inferred]** follows from documented facts, not
stated outright. **[check]** not documented; confirm on HiPerGator with the command shown before relying on it.

Team rule (from the user, 2026-10-03): **at most 2 GPUs per job or session for group jie.xu.** Every script
in this package must request 2 GPUs or fewer.

---

## 0. What matters for this package

1. **B200 partition is `hpg-b200`; GRES type `b200`.** Use `--partition=hpg-b200 --gres=gpu:b200:N`
   (N <= 2). The partition is required. Without it Slurm gives you an L4. [doc]
2. **There are no A100s on HiPerGator anymore.** The DGX A100 nodes went back to the vendor at the end of
   June 2025 and DGX B200s replaced them. The docs list no A100 partition or GRES. The fallback variable should
   choose between `b200` / `rtx6000` / `l4`, not A100 (see section 3). [doc]
3. **Idle-GPU killer: a GPU at 0 % utilisation for 1 hour gets the job terminated. In a multi-GPU job, any one
   idle GPU kills the whole job.** Keep downloads, ffmpeg decoding and other CPU-only stages in separate
   CPU jobs, and drain the per-GPU work queues together. [doc]
4. **There is no burst QOS for GPUs.** GPU jobs run only under the investment QOS `jie.xu`. Use `jie.xu-b`
   (burst) for CPU-only stages only. [doc]
5. **The default walltime on `hpg-b200` is 10 minutes**, and a job with no requests gets 1 core and 600 MB. Always
   set `--time`, `--cpus-per-task` and `--mem`. The maximum walltime on `hpg-b200` is 14 days. [doc]
6. **The GPU pool is group-wide and shared by all GPU types.** One NGU = one GPU of any type. A QOS limit
   (`GrpTRES ... gres/gpu=N`) is shared by every member of the group, and the same QOS also caps the group's
   CPU cores and memory. Run `showQos jie.xu` before choosing `--cpus-per-task` and `--mem`. [doc + inferred]
7. **Scratch is `$TMPDIR`** (node-local flash, removed when the job ends). `$SLURM_TMPDIR` is deprecated
   since the Slurm update of 2026-06-29. [doc]
8. **Put caches on /blue.** /home has a 40 GB quota. Point `HF_HOME` and the other caches at
   `/blue/jie.xu/$USER/...`. **`HF_HOME` also moves the default token path** to `$HF_HOME/token`, so set
   `HF_TOKEN_PATH` (section 12). [doc]
9. **Compute nodes appear to have outbound internet.** UFRC's own `hpg-b200` sbatch example runs
   `ollama pull` inside the job, and the VS Code tunnel guide runs from a compute node. No page states it
   directly. Even so, download in a CPU job or dev session and run GPU jobs with `HF_HUB_OFFLINE=1`.
   [inferred, check]
10. **The B200 queue is slow.** UFRC: "Jobs requesting B200 GPUs must expect long job pending times"; L4 jobs
    usually start promptly. [doc]

---

## 1. Login, sessions, login-node rules

- Log in with `ssh <gatorlink>@hpg.rc.ufl.edu`, then your GatorLink password, then a Duo prompt (push or
  passcode). You land on a random `loginN` node. [doc] https://docs.rc.ufl.edu/access/mfa/
- **Login-node limits:** no more than 4 cores and 32 GB of RAM, and no more than 4 simultaneous instances of
  any process. Short tests only. The usage-policy page is looser (16 cores, 64 GB, at most 10 minutes); follow
  the stricter limit. Running analyses on login nodes is the main cause of account suspension. [doc]
  https://docs.rc.ufl.edu/quickstart/development_testing/ ,
  https://it.ufl.edu/rc/documentation/policies/hipergator-usage-policies/
- **Dev partition:** use `srundev` (needs `module load ufrc`) or
  `srun --partition=hpg-dev --mem=4gb --cpus-per-task=8 --time=04:00:00 --pty bash -i`. It is CPU-only,
  defaults to 10 minutes, allows up to 12 hours, and is not counted against group QOS limits. Use it to build
  environments and download files. [doc] https://docs.rc.ufl.edu/quickstart/development_testing/
- **Persistent sessions:** `ssh login7` from inside HPG to pick a fixed node, then `ml tmux` (or
  `ml screen`). Sessions exist per node and are lost if that login node reboots. [doc]
  https://docs.rc.ufl.edu/access/persistent_sessions/
- **SSH multiplexing** (one Duo prompt per 8 h) works from Linux and macOS through `ControlMaster auto` /
  `ControlPersist 8h`. Windows OpenSSH does not support it; Bitvise and Tabby do. [doc]
  https://docs.rc.ufl.edu/access/ssh_multiplexing/
- **Attach to a running job's node:** `srun --pty --overlap --jobid <JOBID> bash`. Plain ssh to a node where
  you have a job also works, and Slurm adopts that session into the job. [doc]
  https://docs.rc.ufl.edu/scheduler/temp_directories/

## 2. GPU hardware and partitions

| | NVIDIA B200 | NVIDIA RTX PRO 6000 | NVIDIA L4 |
|---|---|---|---|
| Slurm partition | `hpg-b200` | `hpg-rtx6000` | `hpg-turin` (default if a GPU is requested; also `gpu`, `hwgui`) |
| GRES type / feature | `b200` | `rtx-pro-6000` | `l4` |
| VRAM per GPU | 180 GB | 96 GB | 24 GB |
| GPUs per node | 8 | 8 | 3 |
| CPU cores per node / per GPU | 112 / 14 | 128 / 16 | 96 / 4 reserved per GPU |
| Host RAM per node | 2 TB (`nodeInfo`: 2010 GB) | 1,536 GB | 753 GB |
| CPU | Intel Xeon Platinum 8570 (Emerald Rapids) | AMD EPYC 9555 | AMD EPYC 9655P (Turin) |
| OS feature | `el9` | `el9` | `el9` |
| CUDA arch | sm_100 [doc] | sm_120 [inferred: Blackwell RTX PRO, same arch as the local RTX 5090] | sm_89 [doc] |

Sources: https://docs.rc.ufl.edu/resources/gpus/ , https://docs.rc.ufl.edu/scheduler/node_features/ ,
https://docs.rc.ufl.edu/software/apps/cuda/

- **B200 count:** the docs table shows 31 B200 hosts (SuperPOD SU1, 248 GPUs). The UFIT HiPerGator page
  lists "504 Blackwell B200 GPUs (180 GB VRAM) in 63 NVIDIA DGX B200 nodes", after SU2 arrived in July 2025.
  https://it.ufl.edu/rc/hipergator/
- **A100 removed:** RCAC minutes from June 2025: "The remaining 80 DGX A100 nodes will be returned in the end of
  June, which will trigger delivery of the remaining 31 DGX B200 nodes." No current docs page mentions A100.
  https://it.ufl.edu/media/itufledu/documents/research-computing/RCAC_minutes_2025-06-2.docx
- The UFIT page also lists 32 L40 GPUs (48 GB). No docs page gives a partition for them, so do not target them.

## 3. Exact SLURM syntax

**Request forms** [doc] https://docs.rc.ufl.edu/scheduler/gpu_access/

```bash
#SBATCH --partition=hpg-b200
#SBATCH --gpus=2                 # or
#SBATCH --gres=gpu:2             # or, typed (preferred):
#SBATCH --gres=gpu:b200:2
```

- Request at least 1 CPU core per GPU, or the scheduler rejects the job. [doc]
- With `--gpus=`, GPU usage does **not** appear in `slurmInfo`. Use `--gres=gpu:b200:N` so the group can see
  usage. [doc]
- `--gpus-per-task` also works (PyTorch page). [doc]
- No `--mem-per-gpu` or `--cpus-per-gpu` defaults are documented. Set `--cpus-per-task` and `--mem`
  explicitly. To read the partition's configured defaults, run `scontrol show partition hpg-b200`
  (`DefMemPerGPU`, `DefCpuPerGPU`, `MaxTime`). [check]

**Pattern A: one job holding 2 B200s, with many worker processes**

```bash
#!/bin/bash
#SBATCH --job-name=fp-gpu
#SBATCH --account=jie.xu
#SBATCH --qos=jie.xu                # investment QOS; GPUs cannot use jie.xu-b
#SBATCH --partition=hpg-b200
#SBATCH --gres=gpu:b200:2           # team limit: <= 2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=28          # <= 14 per GPU on B200; must fit `showQos jie.xu` cpu=
#SBATCH --mem=400gb                 # host RAM; must fit `showQos jie.xu` mem=
#SBATCH --time=12:00:00             # default would be 10 min; max 14-00:00:00
#SBATCH --output=logs/%x_%j.out
```

Every GPU must stay busy until the job exits (section 5). Workers need one shared work queue (work
stealing), so that neither GPU sits idle for an hour while the other finishes.

**Pattern B: job array of 1-GPU shards, never more than 2 running** [doc for syntax]

```bash
#SBATCH --partition=hpg-b200
#SBATCH --gres=gpu:b200:1
#SBATCH --cpus-per-task=14
#SBATCH --mem=200gb
#SBATCH --time=08:00:00
#SBATCH --array=0-5%2               # 6 shards, at most 2 running = at most 2 GPUs
#SBATCH --output=logs/%x_%A_%a.out  # always use both %A and %a
```

Prefer a few shards over one task per meeting. Every array task waits in the B200 queue separately, and UFRC
warns that many short tasks bog down the scheduler. A finished shard releases its GPU straight away, so a
slow sibling shard cannot trip the idle-GPU killer on it.
https://docs.rc.ufl.edu/scheduler/submitting_arrays/ , https://docs.rc.ufl.edu/scheduler/job_arrays/

**Interactive** [doc]

```bash
module load ufrc
sruni --partition=hpg-b200 --gpus=2 --mem=300gb --time=3:00:00 --ntasks=1   # verbatim doc example
srun  --partition=hpg-b200 --gres=gpu:b200:1 --cpus-per-task=8 --mem=64gb --time=1:00:00 --pty bash -i
```

Interactive sessions are limited to 12 hours, and the idle-GPU killer applies to them as well. [doc]

**Chain CPU stages to GPU stages** (UFRC's recommended way to keep GPUs from idling) [doc]

```bash
prep=$(sbatch --parsable slurm/cpu_prep.sbatch)              # downloads, ffmpeg, transcripts
sbatch --dependency=afterok:$prep slurm/gpu_wave.sbatch
```

**Fallback via one variable** (fill these from the table in section 2):

| `GPU_PROFILE` | `--partition` | `--gres` | VRAM | cores/GPU | note |
|---|---|---|---|---|---|
| `b200` (default) | `hpg-b200` | `gpu:b200:N` | 180 GB | 14 | long queue |
| `rtx6000` | `hpg-rtx6000` | `gpu:rtx-pro-6000:N` | 96 GB | 16 | Blackwell, cu128 stack identical to the local 5090 |
| `l4` | `hpg-turin` (or omit) | `gpu:l4:N` | 24 GB | 4 | usually starts promptly; Ada sm_89; cu128 wheels run there too |

All three types come out of the same group GPU pool (NGU = "1 general purpose GPU of any type").
https://docs.rc.ufl.edu/resources/types/

## 4. Time limits

| Context | Default | Max | Source |
|---|---|---|---|
| `hpg-b200`, `hpg-rtx6000`, `hpg-turin` | 10 min | 14 days | https://docs.rc.ufl.edu/scheduler/partition_limits/ |
| `hpg-default`, `hpg-milan`, `bigmem` (CPU) | 10 min | 31 days | same |
| `hpg-dev` | 10 min | 12 h | same |
| Investment QOS | 10 min | 31 days (partition cap applies) | same |
| Burst QOS (CPU only) | 10 min | 4 days | same |
| Interactive GPU shell (`sruni`/`srun --pty`) | 10 min | 12 h | https://docs.rc.ufl.edu/scheduler/gpu_access/ |
| Open OnDemand GPU session | | 12 h | same, and partition_limits |

Requests with long time limits are harder to schedule. Request about 1.5 times the measured runtime.
https://docs.rc.ufl.edu/scheduler/limit_types/

## 5. GPU usage policy (idle GPUs)

- "Automated systems are now in place to terminate jobs where GPU utilization falls below a defined
  threshold... currently set to 0% utilization for 1 hour." [doc]
- Multi-GPU jobs: "If any GPU allocated to a job is idle, the job will be terminated." [doc]
- L4: the policy applies, but jobs on L4s are not currently cancelled. [doc]
- Running fake loads to keep a GPU busy leads to a 2-week account suspension and a referral (SCCR for
  students). [doc]
- Monitor with `jobnvtop` (ufrc module), or `nvidia-smi` from `srun --overlap`. [doc]
- The usage policy says jobs that request GPUs but do not use them "will result in job termination and account
  suspension". [doc]

https://docs.rc.ufl.edu/scheduler/idle_gpu_policy/ ,
https://it.ufl.edu/rc/documentation/policies/hipergator-usage-policies/

What this means for the package [inferred]:
- Never download videos or weights inside a GPU job.
- Decode audio and frames in a CPU job, or overlap decoding with GPU work so no GPU sits at 0 % for an hour.
- End the GPU job as soon as either GPU's queue is empty, or use pattern B.

## 6. Accounts and QOS: `jie.xu` and `jie.xu-b`

- Each group account has two QOS levels:
  - `<group>`: investment QOS, high priority, up to 31 days.
  - `<group>-b`: burst QOS, 9 times the CPU and memory, about 1/40 of the base priority, up to 4 days, start
    not guaranteed.
  [doc] https://docs.rc.ufl.edu/scheduler/qos_limits/ , https://docs.rc.ufl.edu/scheduler/limit_types/
- **There is no burst QOS for GPU jobs or GPU partitions.** GPU jobs run under `--qos=jie.xu` only. [doc]
- GPUs need an active NGU allocation on the group. The scheduler treats CPU, memory and GPUs as trackable
  resources in one QOS pool, e.g. `GrpTRES cpu=9,gres/gpu=0,mem=32400M`. The pool is shared by all group
  members. [doc] https://docs.rc.ufl.edu/resources/gpus/ , https://docs.rc.ufl.edu/scheduler/limit_types/
  - So if a labmate holds one of the group's GPUs, a 2-GPU job pends. [inferred]
  - A GPU job's cores and memory count against the same `jie.xu` CPU and memory limits, so a large
    `--cpus-per-task` or `--mem` can push a job over the QOS limit. That gives an immediate "Job violates
    accounting/QOS policy" error or a pending reason `QOSGrpCpuLimit` / `QOSGrpMemLimit`. [inferred]
- Is B200 covered by the jie.xu QOS? NGUs are not tied to a GPU type, so B200s are covered as long as
  `showQos jie.xu` shows `gres/gpu` > 0. The lab's own Slurm example uses
  `--partition=hpg-b200 --gres=gpu:b200:1`. [doc + check]
- **Secondary group:** if `id` shows jie.xu as a secondary group, every job needs **both**
  `--account=jie.xu --qos=jie.xu`, or the job falls back to the primary group. UFRC creates
  `/blue/<group>/<user>` only for the primary group; create it yourself in a secondary group's tree.
  JupyterHub always uses the primary group. [doc] https://docs.rc.ufl.edu/scheduler/secondary_resources/ ,
  https://docs.rc.ufl.edu/quickstart/practical_storage/
- `qos_to_burst <jobid>` / `qos_to_main <jobid>` move a pending job between QOS levels (CPU jobs only).
  [doc] https://docs.rc.ufl.edu/software/ufrc_tools/

Commands to run on first login:

```bash
id; showAssoc $USER                       # which accounts/QOS you have
module load ufrc; slurmInfo jie.xu         # allocation, running/pending, GPU use
showQos jie.xu; showQos jie.xu-b           # GrpTRES: cpu=, mem=, gres/gpu=
sacctmgr show qos format="name%-20,priority,maxwall,grptres%60" jie.xu jie.xu-b
scontrol show partition hpg-b200           # DefMemPerGPU / DefCpuPerGPU / MaxTime
```

## 7. Job arrays and job counts

- At most 3,000 jobs per user in the queue, and the highest array task ID is 3,000. For larger values, offset
  in bash (`TASK=$((SLURM_ARRAY_TASK_ID + 3000))`). [doc]
- Throttle with `--array=0-N%K`. Change a running array with
  `scontrol update ArrayTaskThrottle=K JobId=<id>` (0 removes the limit). [doc]
- Rerun selected tasks with `sbatch --array=4,8,15 job.sbatch`. Command-line options override `#SBATCH`. [doc]
- Batches of more than 10,000 jobs need prior approval. Avoid arrays of very short tasks; loop inside a few
  tasks instead. [doc]
- Mail: `--mail-type=END,FAIL` sends one mail per array. Add `ARRAY_TASKS` for one mail per task. [doc]

https://docs.rc.ufl.edu/scheduler/job_arrays/ , https://docs.rc.ufl.edu/scheduler/submitting_arrays/ ,
https://docs.rc.ufl.edu/scheduler/array_indexes/

## 8. Several processes per GPU and CUDA MPS

- **No UFRC page covers CUDA MPS or GPU sharing between processes.** A search of the full docs index
  found nothing. [check]
- Processes may use only the GPUs Slurm allocated to the job. Inside an allocation, several processes on one
  GPU are permitted: the policy restricts using unallocated resources, not how you use your own. [inferred]
  https://it.ufl.edu/rc/documentation/policies/hipergator-usage-policies/
- Before packing workers onto a GPU, check the compute mode inside a job. `Default` allows many processes per
  GPU through time-slicing; `Exclusive_Process` does not.

  ```bash
  nvidia-smi --query-gpu=name,driver_version,compute_mode,memory.total --format=csv
  ```

  [check]
- Optional MPS, started and stopped inside the job, nothing system-wide. Treat it as experimental and keep
  it off by default. [check]

  ```bash
  export CUDA_MPS_PIPE_DIRECTORY=$TMPDIR/mps_pipe CUDA_MPS_LOG_DIRECTORY=$TMPDIR/mps_log
  mkdir -p $CUDA_MPS_PIPE_DIRECTORY $CUDA_MPS_LOG_DIRECTORY
  nvidia-cuda-mps-control -d          # serves the GPUs visible to the job
  # ... launch workers ...
  echo quit | nvidia-cuda-mps-control
  ```

- Apptainer on GPU nodes: use `--nv` always, and add `--ipc=host` or `--bind /dev/shm` for multi-GPU
  RTX6000/B200 jobs. [doc] https://docs.rc.ufl.edu/software/gpus/

## 9. CUDA, drivers and modules

- **Driver:** "The cuda-toolkit package ensures compatibility with the NVIDIA drivers on HPG (currently or
  CUDA 13 and 12)." [doc] https://docs.rc.ufl.edu/software/gpus/
  - CUDA 13 support implies an R580-or-newer driver, which also runs PyTorch cu128/cu129/cu130 wheels
    (cu128 needs R570 or newer). [inferred]
  - The exact version is not published. Run `nvidia-smi` inside a B200 job. [check]
  - The May 6-7, 2026 full downtime included OS, CUDA, Slurm and Open OnDemand updates. [doc]
    https://docs.rc.ufl.edu/services/announcements/
- **CUDA modules:**
  - The installed-apps list shows `cuda` 12.9.1, 13.0.2 and 13.2.1 (up to the three latest shown).
  - The older CUDA page lists 12.4.1, 12.8.1 and 12.9.1.
  - Check with `module spider cuda`. Pip wheels bring their own CUDA runtime and need only the driver; load
    the module only to compile.
  - `HPC_CUDA_DIR`, `HPC_CUDA_LIB` and `HPC_CUDA_BIN` are set by the module.

  [doc] https://docs.rc.ufl.edu/software/installed_applications/ , https://docs.rc.ufl.edu/software/apps/cuda/
- **cuDNN module:** 9.6.0 only. Prefer the cuDNN pip wheels that PyTorch cu128 and onnxruntime-gpu pull in
  over the module. [doc for version]
- **PyTorch modules:** `pytorch` 1.13.0, 2.7 and 2.8.0. `ngc-pytorch` (read-only NGC container) 2.3.0, 2.5.0
  and 2.10.0 (`ml purge; ml ngc-pytorch/<ver>`); you cannot add packages to it. [doc]
  - The PyTorch and TensorFlow app pages still show the retired `--partition=gpu`; ignore that.
  - For TensorFlow on B200, the docs say use `tensorflow/2.17.0`.
- **NCCL:** 2.27.5. `nvhpc` 25.3, 25.9 and 26.3. [doc]
- **Python environments:** `module load conda`. The module includes **conda, mamba, pixi and uv**
  (`conda` 25.7.0 and 26.7). [doc] https://docs.rc.ufl.edu/software/apps/conda/
  - On first load, conda sets `envs_dirs` and `pkgs_dirs` to `/blue/<group>/<user>/.conda/...` (primary
    group only; otherwise use `conda config --prepend ...`). [doc]
    https://docs.rc.ufl.edu/software/conda_configuration/
  - Create path-based envs on /blue: `conda create -p /blue/jie.xu/$USER/envs/fp python=3.11`. In job
    scripts, `export PATH=<env>/bin:$PATH` instead of activating. [doc]
    https://docs.rc.ufl.edu/software/conda_creation/
  - uv: move the cache to /blue (UFRC recommends symlinking `~/.cache` to `/blue/<group>/<user>/.cache`, or
    setting `UV_CACHE_DIR`). The doc example installs torch with `--index https://download.pytorch.org/whl/cu129`.
    For this package, pin `.../whl/cu128` (torch >= 2.7). [doc] https://docs.rc.ufl.edu/software/uv/
  - Avoid `pip install --user` into `~/.local`, which can produce GLIBC-incompatible wheels; use an isolated
    env. [doc] https://docs.rc.ufl.edu/support/apps_faq/
  - Run installs in a GPU or dev session, not on a login node. Conda detects the GPU when run in a GPU
    session. [doc] https://docs.rc.ufl.edu/software/gpus/
- **ffmpeg module:** `ffmpeg` n4.4.6, n6.1, n7.2 (`module spider ffmpeg`; `HPC_FFMPEG_BIN`). [doc]
  https://docs.rc.ufl.edu/software/apps/ffmpeg/
- **Apptainer:** 1.3.5, 1.4.1, 1.4.2.
  - `apptainer pull docker://...` / `apptainer build x.sif docker://...`.
  - Inside containers, set `APPTAINERENV_TMPDIR`.
  [doc] https://docs.rc.ufl.edu/software/apps/apptainer/ , https://docs.rc.ufl.edu/scheduler/temp_directories/
- **Other modules:** `git` 2.51.1, `aria2` 1.35.0, `rclone` 1.65.2, `tmux` 3.5, `screen` 4.9.1,
  `globus` CLI 3.18.0, `opencv` 4.7.0, `sox` 14.4.2. [doc]
- **Not provided as modules:** whisper, pyannote, mediapipe and parselmouth. Install them into the project
  env. [doc: absent from list]

## 10. Storage

| Path | Quota | Use | Backup |
|---|---|---|---|
| `/home/$USER` (`~`) | 40 GB (`home_quota`) | dotfiles, scripts, small envs; **never job I/O** | daily snapshots for 1 week in `~/.snapshot/` |
| `/blue/jie.xu/$USER` | group quota from the investment (`blue_quota`) | **all job input and output**, envs, caches, videos | none |
| `/blue/<group>/<user>` | same group quota | group-writable shared area | none |
| `/orange/jie.xu` | only if the group bought Orange (`orange_quota`) | archive, gentle serial reads | none |
| `$TMPDIR` (= `/tmp`, `/var/tmp` in a job) | node-local flash | many small files, decoded frames and audio | deleted at job end (kept briefly if the job fails) |

Sources: https://docs.rc.ufl.edu/quickstart/practical_storage/ , https://docs.rc.ufl.edu/domain/file_quotas/ ,
https://docs.rc.ufl.edu/scheduler/temp_directories/ , https://docs.rc.ufl.edu/scheduler/variables/

- Run jobs from a /blue working directory (`pwd`). Blue is Lustre: good for large streaming files, poor for
  millions of small files. [doc]
- /blue and /orange are automounted: `ls /blue/jie.xu` mounts them. [doc]
- **Permissions:** by default, "group members have read access to other group member folders" on /blue.
  Keep secrets (HF token) out of /blue, or `chmod 600` them. [doc + inferred]
- Quota exceeded gives "Disk quota exceeded". Each group may get one temporary quota increase per 12 months,
  for up to 3 months, through a support ticket. [doc]
- Disk usage: `ncdu` (`TERM=xterm ncdu` per the lab notes); quota commands are listed in the table above. [doc]
- Size estimate for this project, not from the docs: about 75 MP4s of about 1 hour each, so roughly
  0.1 to 0.25 TB of video depending on rendition, plus audio and features. Compare with `blue_quota` before
  downloading.

## 11. Internet access from compute nodes, and downloads

- UFRC documents downloading with `wget` or `curl` from an HPG terminal. For transfers to or from remote sites
  from inside HPG, it says "use the login nodes. Transfers can also be made from within developmental
  sessions." [doc] https://docs.rc.ufl.edu/data_transfer/overview/
- Evidence that compute nodes reach the internet:
  - UFRC's Ollama sbatch example (`--partition=hpg-b200 --gpus=1`) runs `ollama pull mistral` inside the
    batch job. https://docs.rc.ufl.edu/software/apps/ollama/
  - The VS Code guide runs `code tunnel` from a compute node, which needs outbound connections to
    GitHub/Microsoft. https://docs.rc.ufl.edu/domain/vscode_development/
  - [inferred]
- Quick test before relying on it [check]:
  `srun -p hpg-dev -t 5 --mem=1gb curl -sI https://www.federalreserve.gov | head -1`, plus the same for
  `https://huggingface.co`.
- Recommended pattern for this package:
  1. Download the federalreserve.gov/Brightcove MP4s, transcript PDFs and model weights in a **CPU-only**
     job (`hpg-default` or `hpg-milan`, optionally `--qos=jie.xu-b`) or in an `srundev` session. Do not use
     a login node: 10-minute and 4-core limits.
  2. Then run the GPU stages offline (`HF_HUB_OFFLINE=1`) so no GPU waits on the network.
- If a test ever shows no outbound access, download through the login node within its limits, or transfer
  from a laptop with Globus or rsync (section 13).

## 12. Hugging Face cache on /blue (gated pyannote)

UFRC documents setting `export HF_HOME="/path/to/new/huggingface_cache"` in the shell or in `~/.bashrc`.
[doc] https://docs.rc.ufl.edu/support/apps_faq/

Facts from huggingface_hub [doc]
https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables :
- `HF_HUB_CACHE` defaults to `$HF_HOME/hub`.
- **`HF_TOKEN_PATH` defaults to `$HF_HOME/token`**, so moving `HF_HOME` to /blue also moves the expected token
  file there.
- The `HF_TOKEN` environment variable overrides the stored token.
- `HF_HUB_OFFLINE=1` makes no HTTP calls and uses only the cache.
- If `HF_HOME` is unset and `XDG_CACHE_HOME` is set, the cache moves to `$XDG_CACHE_HOME/huggingface`.
- Variables are read when `huggingface_hub` is imported.
- `hf_transfer` is deprecated; downloads go through `hf-xet`, and `HF_XET_HIGH_PERFORMANCE=1` is the fast mode.

```bash
export FP_ROOT=/blue/jie.xu/$USER/fed_presser
export HF_HOME=$FP_ROOT/cache/huggingface           # models on /blue
export HF_TOKEN_PATH=$HOME/.cache/huggingface/token # token stays in home (package contract)
export TORCH_HOME=$FP_ROOT/cache/torch
export XDG_CACHE_HOME=$FP_ROOT/cache                # mediapipe/emotiefflib/etc. that use ~/.cache
export PIP_CACHE_DIR=$FP_ROOT/cache/pip UV_CACHE_DIR=$FP_ROOT/cache/uv
# GPU jobs, after the CPU pre-download stage:
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
```

- Accept the pyannote Hub terms in a browser first (the user does this). Then run `hf auth login` once in a
  dev session; it writes to `$HF_TOKEN_PATH`. Afterwards run
  `chmod 700 ~/.cache/huggingface; chmod 600 ~/.cache/huggingface/token`.
- If `~/.cache` is a symlink into /blue (the UFRC uv advice), the token is on group-readable /blue unless
  you set those modes. [inferred]
- Never place the token in a job script, a URL or the repository.

## 13. Moving code and data in and out

| Method | When | Notes |
|---|---|---|
| Globus | large data | managed collection **"UFRC HiPerGator"** (/home, /blue, /orange); Globus Connect Personal on the laptop; resumes automatically. Fastest. https://docs.rc.ufl.edu/data_transfer/globus/ |
| rsync / scp / sftp to `hpg.rc.ufl.edu:22` | most cases | Duo applies; on Windows use WinSCP, Bitvise or Cyberduck, **not FileZilla**. https://docs.rc.ufl.edu/data_transfer/overview/ |
| OOD Files / Jupyter upload | small files only | slow over a few GB; Jupyter upload is capped below 2 GB |
| `git clone` on HPG | the package code | `module load git` |

## 14. Jupyter and Open OnDemand

- **Open OnDemand:** https://ood.rc.ufl.edu (also https://ondemand.rc.ufl.edu).
  - Offers Files, Job Composer, HPG Shell, Desktop, Jupyter, and custom account/QOS/partition/`--gres`
    fields.
  - For B200 choose partition `hpg-b200` with gres `gpu:1`.
  - GPU sessions are limited to 12 h.
  [doc] https://docs.rc.ufl.edu/interfaces/ood/ , https://docs.rc.ufl.edu/scheduler/gpu_access/
  - The older Jupyter-via-OOD page says 72 h for GPU notebooks. That conflicts with the 12 h stated on the
    GPU Access and partition pages; assume 12 h.
- **JupyterHub:** https://jupyterhub.rc.ufl.edu.
  - Preset resource profiles; primary group's investment QOS only.
  - If the job does not start within 5 minutes, the session fails, which is likely with B200 queues.
  [doc] https://docs.rc.ufl.edu/interfaces/jupyterhub/
- Stop sessions when done: idle GPUs are killed after 1 h. [doc]

## 15. Queue behaviour and monitoring

- Expect long pending times for B200 jobs; L4 jobs usually start promptly. [doc]
  https://docs.rc.ufl.edu/support/faq/
- A job also waits when all of the group's allocated GPUs are in use, or when it asks for more GPUs than one
  node has (8 B200s, 3 L4s). [doc]
- Investment-QOS priority example: 36000, against 900 for burst. Priority grows while a job waits. [doc]
  https://docs.rc.ufl.edu/scheduler/limit_types/
- Pending reasons:
  - `QOSGrpCpuLimit` / `QOSGrpMemLimit` (group pool used up)
  - `Priority`, `Resources`, `Dependency`, `QOSResourceLimit`
  - For GPUs, Slurm normally reports `QOSGrpGRES` [inferred]
  [doc] https://docs.rc.ufl.edu/scheduler/qos_limits/ , https://docs.rc.ufl.edu/support/faq/
- Tools (ufrc module):
  - `slurmInfo [-g group]`, `showQos`, `showAssoc`, `nodeInfo`
  - `squeuemine`, `squeue_pending`, `showstart <job>`, `slurm_exit_info <job>`
  - `jobhtop`, `jobnvtop`
  - `sacct -S MMDD -o JobIDRaw,JobName,NCPUS,MaxRSS,Elapsed`, `sstat -j <job>.batch -o maxrss`
  [doc] https://docs.rc.ufl.edu/software/ufrc_tools/ , https://docs.rc.ufl.edu/scheduler/status_commands/
- Memory: slightly over-request (10-20 %). Over-requesting does not speed anything up and blocks the group's
  pool. [doc] https://docs.rc.ufl.edu/scheduler/sample_job_scripts/
- Sample scripts are on the cluster at `/data/training/Slurm/`. [doc]

## 16. Conflicting or stale documentation (seen 2026-10-03)

| Topic | Page A | Page B | Use |
|---|---|---|---|
| Job scratch variable | practical_storage: "Use `$SLURM_TMPDIR`" | temp_directories / variables: `$SLURM_TMPDIR` deprecated after the 2026-06-29 Slurm update | `$TMPDIR` |
| Login-node limits | development_testing: 4 cores / 32 GB | usage policy: 16 cores / 64 GB / 10 min | the stricter one |
| GPU notebook limit | jupyter_ood: 72 h | gpu_access, partition_limits: OOD GPU 12 h | 12 h |
| GPU partition name | pytorch, tensorflow app pages: `--partition=gpu` | gpu_access: `hpg-b200` / `hpg-rtx6000` / `hpg-turin` | the gpu_access names |
| B200 node count | resources/gpus: 31 hosts | it.ufl.edu/rc/hipergator: 63 nodes / 504 GPUs | irrelevant at a 2-GPU cap |
| CUDA versions | apps/cuda: 12.4.1, 12.8.1, 12.9.1 | installed_applications: 12.9.1, 13.0.2, 13.2.1 | `module spider cuda` |

## 17. Sources (all accessed 2026-10-03)

- GPU access and syntax: https://docs.rc.ufl.edu/scheduler/gpu_access/
- GPU hardware and partitions: https://docs.rc.ufl.edu/resources/gpus/
- Node features (`nodeInfo` table): https://docs.rc.ufl.edu/scheduler/node_features/
- Partition time limits: https://docs.rc.ufl.edu/scheduler/partition_limits/
- Account and QOS limits, burst: https://docs.rc.ufl.edu/scheduler/qos_limits/
- QOS limit types, showQos, GPU burst: https://docs.rc.ufl.edu/scheduler/limit_types/
- Secondary groups, showAssoc: https://docs.rc.ufl.edu/scheduler/secondary_resources/
- Idle GPU policy: https://docs.rc.ufl.edu/scheduler/idle_gpu_policy/
- Temporary directories: https://docs.rc.ufl.edu/scheduler/temp_directories/
- Slurm variables: https://docs.rc.ufl.edu/scheduler/variables/
- Job arrays: https://docs.rc.ufl.edu/scheduler/job_arrays/ , https://docs.rc.ufl.edu/scheduler/submitting_arrays/ ,
  https://docs.rc.ufl.edu/scheduler/array_indexes/
- Sample scripts: https://docs.rc.ufl.edu/scheduler/sample_job_scripts/
- Status commands: https://docs.rc.ufl.edu/scheduler/status_commands/
- Development and login nodes: https://docs.rc.ufl.edu/quickstart/development_testing/
- Storage: https://docs.rc.ufl.edu/quickstart/practical_storage/ , https://docs.rc.ufl.edu/domain/file_quotas/
- Data transfer: https://docs.rc.ufl.edu/data_transfer/overview/ , https://docs.rc.ufl.edu/data_transfer/globus/
- CUDA: https://docs.rc.ufl.edu/software/apps/cuda/ ; GPUs from apps: https://docs.rc.ufl.edu/software/gpus/
- Installed modules: https://docs.rc.ufl.edu/software/installed_applications/
- Conda / uv: https://docs.rc.ufl.edu/software/apps/conda/ , https://docs.rc.ufl.edu/software/conda_configuration/ ,
  https://docs.rc.ufl.edu/software/conda_creation/ , https://docs.rc.ufl.edu/software/uv/
- Apptainer: https://docs.rc.ufl.edu/software/apps/apptainer/ ; ffmpeg: https://docs.rc.ufl.edu/software/apps/ffmpeg/
- PyTorch modules: https://docs.rc.ufl.edu/software/apps/pytorch/ , https://docs.rc.ufl.edu/software/apps/ngc-pytorch/
- Ollama in-job download example: https://docs.rc.ufl.edu/software/apps/ollama/
- VS Code tunnel from compute node: https://docs.rc.ufl.edu/domain/vscode_development/
- HF_HOME / caches: https://docs.rc.ufl.edu/support/apps_faq/
- FAQ (GPU queue, pending reasons): https://docs.rc.ufl.edu/support/faq/
- ufrc tools: https://docs.rc.ufl.edu/software/ufrc_tools/
- Resource types (NGU): https://docs.rc.ufl.edu/resources/types/ ; trial (2 NGU default): https://docs.rc.ufl.edu/resources/trial/
- OOD / Jupyter: https://docs.rc.ufl.edu/interfaces/ood/ , https://docs.rc.ufl.edu/interfaces/jupyterhub/ ,
  https://docs.rc.ufl.edu/interfaces/jupyter_ood/
- MFA, multiplexing, persistent sessions: https://docs.rc.ufl.edu/access/mfa/ ,
  https://docs.rc.ufl.edu/access/ssh_multiplexing/ , https://docs.rc.ufl.edu/access/persistent_sessions/
- Announcements (May 2026 downtime): https://docs.rc.ufl.edu/services/announcements/
- Usage policies: https://it.ufl.edu/rc/documentation/policies/hipergator-usage-policies/
- Current hardware: https://it.ufl.edu/rc/hipergator/
- A100 return / B200 SU2: https://it.ufl.edu/media/itufledu/documents/research-computing/RCAC_minutes_2025-06-2.docx
- huggingface_hub environment variables: https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables
