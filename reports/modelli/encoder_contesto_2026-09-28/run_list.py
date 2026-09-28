"""Run the commands of a runs.json in order, for one shard, skipping what is done (a Kaggle or Colab session).
Standard library only.

    python run_list.py --runs runs.json --shard 0 --keep-small           the whole shard
    python run_list.py --runs runs.json --shard 0 --dry-run              print what would run
    python run_list.py --runs runs.json --shard 1 --kinds pca,pretrain   only some kinds
    python run_list.py --runs runs.json --shard 1 --max-runs 5           stop after five runs

A run is done when its `done` file exists; a run whose `after` runs are not done is skipped as blocked. Each run
writes its own folder (the scripts refuse an existing one); a failed run's folder is renamed <out>.failed<n>, kept
as evidence, so that the list can be run again. Output goes to WORK/logs/<id>.log and a line per run to
WORK/status.jsonl (exit code, start time, seconds: measured, for the next budget). With --keep-small the
files of a finished run up to --keep-max-bytes are copied under KEEP, mirroring their path under WORK (the large
predictions stay on the scratch disk; compare.py writes the seed-averaged ones under KEEP).
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def copy_small(out: Path, work: Path, keep: Path, limit: int) -> int:
    try:
        rel = out.resolve().relative_to(work.resolve())
    except ValueError:
        return 0
    n = 0
    for p in out.rglob("*"):
        if p.is_file() and p.stat().st_size <= limit:
            dst = keep / rel / p.relative_to(out)
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
                n += 1
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--shard", type=int, default=None)
    ap.add_argument("--kinds", default="", help="comma-separated kinds to run (default: all)")
    ap.add_argument("--max-runs", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stop-on-error", action="store_true")
    ap.add_argument("--keep-small", action="store_true")
    ap.add_argument("--keep-max-bytes", type=int, default=20_000_000)
    args = ap.parse_args(argv)
    runs_path = args.runs.resolve()
    spec = json.loads(runs_path.read_text(encoding="utf-8"))
    work, keep = Path(spec["paths"]["work"]), Path(spec["paths"]["keep"])
    kinds = {k.strip() for k in args.kinds.split(",") if k.strip()}
    by_id = {r["id"]: r for r in spec["runs"]}
    todo = [r for r in spec["runs"] if (args.shard is None or r["shard"] == args.shard) and (not kinds or r["kind"] in kinds)]
    if not args.dry_run:
        (work / "logs").mkdir(parents=True, exist_ok=True)
    failed, ran = [], 0
    for r in todo:
        if Path(r["done"]).exists():
            print(f"done     {r['id']}", flush=True)
            continue
        blockers = [d for d in r.get("after", []) if not Path(by_id[d]["done"]).exists()]
        if blockers:
            print(f"blocked  {r['id']}: {blockers} not done", flush=True)
            continue
        argv_run = [sys.executable if a == "{python}" else a.replace("{runs_json}", str(runs_path)) for a in r["argv"]]
        if args.dry_run:
            print("would run " + " ".join(shlex.quote(a) for a in argv_run), flush=True)
            continue
        started = datetime.now(timezone.utc).isoformat()
        t0 = time.time()
        log_path = work / "logs" / (re.sub(r"[^A-Za-z0-9_.+-]", "_", r["id"]) + ".log")
        print(f"running  {r['id']} (log {log_path})", flush=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"# {started} {' '.join(shlex.quote(a) for a in argv_run)}\n")
            fh.flush()
            rc = subprocess.run(argv_run, stdout=fh, stderr=subprocess.STDOUT).returncode
        ok = rc == 0 and Path(r["done"]).exists()
        rec = {"id": r["id"], "kind": r["kind"], "exit": rc, "ok": ok, "started_utc": started,
               "seconds": round(time.time() - t0, 1), "log": str(log_path)}
        with open(work / "status.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"{'ok' if ok else 'FAILED':8s} {r['id']} in {rec['seconds']} s (exit {rc})", flush=True)
        if ok and args.keep_small:
            copy_small(Path(r["out"]), work, keep, args.keep_max_bytes)
            lk = keep / "logs" / log_path.name
            lk.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(log_path, lk)
        ran += 1
        if not ok:
            failed.append(r["id"])
            out = Path(r["out"])
            if out.exists():                 # kept as evidence, out of the way of a rerun
                n = 1
                while out.with_name(f"{out.name}.failed{n}").exists():
                    n += 1
                out.rename(out.with_name(f"{out.name}.failed{n}"))
                print(f"         {out} renamed to {out.name}.failed{n}", flush=True)
            if args.stop_on_error:
                break
        if args.max_runs and ran >= args.max_runs:
            break
    print(f"{ran} runs executed, {len(failed)} failed: {failed}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
