"""Run the whole walk-forward stance pipeline on one local GPU: prepare -> all (year, seed) fine-tunes -> score -> merge.

    python nlp/run_local.py                      # 12 years (2015-2026) x 3 seeds, 2 trainings at a time
    python nlp/run_local.py --concurrency 3      # more processes on the same GPU
    python nlp/run_local.py --years 2020 --seeds 42 --max-epochs 1 --root <dir> --no-publish   # smoke test
    python nlp/run_local.py --label-year dataset # an older label-year rule (default true: source-document dates)

Resumable: a (year, seed) whose models/<Y>/seed_<S>/metrics.json says done (with the same epoch cap and label-year
rule) is skipped, and
a half-written model (seed_<S>.tmp) is simply retrained. Each training writes its own log in <root>/logs/.
Training processes run with HF_HUB_OFFLINE=1, because `prepare` has already cached the base models.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chrono_stance as cs  # noqa: E402


def stamp(*a) -> None:
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def run(cmd: list[str], env: dict, log_path: Path | None = None) -> int:
    stamp("$", " ".join(cmd[1:]))
    if log_path is None:
        return subprocess.call(cmd, env=env)
    with open(log_path, "w", encoding="utf-8") as f:
        return subprocess.call(cmd, env=env, stdout=f, stderr=subprocess.STDOUT)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=None, help="work root (default $CHRONO_ROOT or nlp/work)")
    ap.add_argument("--years", type=cs.parse_years, default=cs.YEARS)
    ap.add_argument("--seeds", type=int, nargs="+", default=cs.SEEDS)
    ap.add_argument("--concurrency", "-n", type=int, default=2, help="training processes at once on the GPU")
    ap.add_argument("--max-epochs", type=int, default=cs.HP["max_epochs"], help="spec: 8; lower only for a smoke test")
    ap.add_argument("--skip-prepare", action="store_true")
    ap.add_argument("--rescore", action="store_true", help="re-score years that already have scores")
    ap.add_argument("--no-publish", action="store_true", help="do not copy merged tables into the repo")
    ap.add_argument("--label-year", choices=cs.LABEL_YEAR_RULES, default=cs.LABEL_YEAR_DEFAULT,
                    help="label-year rule (default $CHRONO_LABEL_YEAR or true; see nlp/README.md, Label years)")
    ap.add_argument("--python", default=sys.executable)
    a = ap.parse_args()

    root = cs.get_root(a.root)
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    script = str(HERE / "chrono_stance.py")
    base = [a.python, script, "--root", str(root)]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", HF_HUB_DISABLE_SYMLINKS_WARNING="1",
               CHRONO_LABEL_YEAR=a.label_year)
    rule = ["--label-year", a.label_year]
    stamp(f"label-year rule: {a.label_year}")
    t_all = time.time()

    if not a.skip_prepare:
        if run(base + ["prepare", "--years", ",".join(map(str, a.years))] + rule, env) != 0:
            raise SystemExit("prepare failed")
    off = dict(env, HF_HUB_OFFLINE="1")

    jobs = [(y, s) for y in a.years for s in a.seeds if not cs.model_done(root, y, s, a.max_epochs, a.label_year)]
    done0 = len(a.years) * len(a.seeds) - len(jobs)
    stamp(f"training: {len(jobs)} to run, {done0} already done, concurrency {a.concurrency}")
    running: dict[tuple[int, int], tuple[subprocess.Popen, float, object]] = {}
    failed, durations = [], []
    queue = list(jobs)
    try:
        while queue or running:
            while queue and len(running) < a.concurrency:
                y, s = queue.pop(0)
                f = open(logs / f"train_{y}_seed{s}.log", "w", encoding="utf-8")
                cmd = base + ["train", "--year", str(y), "--seed", str(s), "--max-epochs", str(a.max_epochs)] + rule
                running[(y, s)] = (subprocess.Popen(cmd, env=off, stdout=f, stderr=subprocess.STDOUT),
                                   time.time(), f)
                stamp(f"start train {y} seed {s}")
            time.sleep(2)
            for key, (p, t0, f) in list(running.items()):
                rc = p.poll()
                if rc is None:
                    continue
                f.close()
                dt = time.time() - t0
                del running[key]
                if rc == 0 and cs.model_done(root, key[0], key[1], a.max_epochs, a.label_year):
                    durations.append(dt)
                    stamp(f"done  train {key[0]} seed {key[1]} in {dt:.0f}s "
                          f"({len(durations)}/{len(jobs)}; log {logs / f'train_{key[0]}_seed{key[1]}.log'})")
                else:
                    failed.append(key)
                    stamp(f"FAILED train {key[0]} seed {key[1]} (exit {rc}); see the log")
    except KeyboardInterrupt:
        for p, _, f in running.values():
            p.terminate()
            f.close()
        raise SystemExit("interrupted; rerun the same command to resume")
    if durations:
        stamp(f"training wall time {sum(durations):.0f}s of process time, mean {sum(durations) / len(durations):.0f}s "
              f"per fine-tune")
    if failed:
        raise SystemExit(f"{len(failed)} training(s) failed: {failed}; rerun to retry them")

    for y in a.years:
        out = root / "scores" / f"{y}_docs.parquet"
        newest_model = max((cs.model_dir(root, y, s) / "metrics.json").stat().st_mtime for s in a.seeds)
        # skip only a complete scoring made with these models, seeds, epoch cap and label-year rule
        fresh = out.exists() and out.stat().st_mtime > newest_model and not cs.score_problems(
            cs.read_score_meta(root, y), a.max_epochs, a.seeds, a.label_year)
        if fresh and not a.rescore:
            stamp(f"score {y}: up to date, skipped (use --rescore)")
            continue
        cmd = base + ["score", "--year", str(y), "--max-epochs", str(a.max_epochs), "--seeds", *map(str, a.seeds),
                      *rule]
        if run(cmd, off, logs / f"score_{y}.log") != 0:
            raise SystemExit(f"score {y} failed; see {logs / f'score_{y}.log'}")
    cmd = base + ["merge", "--years", ",".join(map(str, a.years))] + (["--no-publish"] if a.no_publish else [])
    if run(cmd, env) != 0:
        raise SystemExit("merge failed")
    stamp(f"all done in {time.time() - t_all:.0f}s; outputs in {root / 'scores'}")


if __name__ == "__main__":
    main()
