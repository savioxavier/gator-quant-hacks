#!/bin/bash
# matrix.sh: run every stage script through the harness in bare and submit_all-like envs
SP=<scratch>
TEAM=$SP/team_push
RUN=$SP/hpgtest/run_stage.sh
export TMPDIR=$SP/hpgmatrix/tmp
fail=0; total=0
for envkind in bare submitall; do
 for gt in b200 l4; do
  for foc in 0 1; do
   for s in 01_fetch 02_audio_frames 03_speech 04_face 05_text 06_aggregate gpu_check smoke; do
    case "$gt" in b200) gpart=hpg-b200 ;; l4) gpart=hpg-turin ;; esac
    case "$s" in
      01_fetch|02_audio_frames|06_aggregate) part=hpg-default ;;
      04_face) [ "$foc" = 1 ] && part=hpg-default || part=$gpart ;;
      *) part=$gpart ;;
    esac
    out=$(
      unset WORKERS_PER_GPU GPU_PARTITION GPU_GRES CPUS_PER_GPU MEM_PER_GPU_GB GPU_SPEED PARTITION
      export GPU_TYPE=$gt FACE_ON_CPU=$foc SLURM_ARRAY_TASK_ID=1 FP_NSHARDS=4 SLURM_JOB_PARTITION=$part
      [ "$s" = 06_aggregate ] && unset SLURM_ARRAY_TASK_ID FP_NSHARDS
      if [ "$envkind" = submitall ]; then
        export FP_PKG=$TEAM/hpg/fedpress_pkg USER=tester FP_GROUP=ai-workshop
        set +u; source "$TEAM/hpg/fedpress_pkg/slurm/common.sh"; fp_gpu_profile || exit 9
      fi
      bash "$RUN" "$TEAM" "$s.sbatch" 2>&1
    )
    total=$((total+1))
    ex=$(grep -o 'EXIT [0-9]*' <<< "$out" | tail -1)
    nparse=$(grep -c '^PARSE ' <<< "$out")
    bad=$(grep -E '"ok": false|"empty_args": \[[0-9]|unbound variable|syntax error|command not found' <<< "$out" | grep -v nvidia-smi)
    # expected exits: 0 everywhere
    if [ "$ex" != "EXIT 0" ] || [ -n "$bad" ]; then
      fail=$((fail+1)); echo "FAIL env=$envkind gpu=$gt face_on_cpu=$foc $s -> $ex"; echo "$out" | sed 's/^/    /' | tail -15
    else
      echo "ok   env=$envkind gpu=$gt face_on_cpu=$foc $s -> $ex parses=$nparse $(grep '^PARSE ' <<< "$out" | grep -o '"set": \[[^]]*\]' | tr '\n' ' ')"
    fi
   done
  done
 done
done
echo "TOTAL $total FAIL $fail"
