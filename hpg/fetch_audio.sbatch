#!/bin/bash
#SBATCH --job-name=fedpress_fetch
#SBATCH --account=jie.xu
#SBATCH --qos=jie.xu-b
#SBATCH --partition=hpg-default
#SBATCH --cpus-per-task=16
#SBATCH --mem=32gb
#SBATCH --time=06:00:00
#SBATCH --output=fedpress_fetch_%j.log
# CPU only: downloads and ffmpeg never touch the B200 queue. If the burst QOS is busy, try --qos=jie.xu.
# Override the output root with: sbatch --export=ALL,FEDPRESS_ROOT=/blue/jie.xu/$USER/fedpress hpg/fetch_audio.sbatch
export NPAR="${NPAR:-12}"
bash "$SLURM_SUBMIT_DIR/hpg/fetch_audio.sh"
