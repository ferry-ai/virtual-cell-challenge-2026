"""Wait until Kaggle has free CPU sessions among the kernels of the launch logs. It only reads statuses: it never pushes.

The kernels are those the launch logs record as accepted (`lancio_*.jsonl`), plus the slugs given with --also. It ends
when at least --need sessions are free, or when one has been free for --grace minutes, or after --max-minutes; the
session then runs fill_sessions.py itself (incident E-20261003-001: nothing pushes on its own).

    python wait_free.py --config-dir <dir> --owner davideferrante11 [--need 2] [--grace 10] [--max-minutes 120]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SESSIONS = 5


def status(slug: str, owner: str, config_dir: str) -> str:
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
    r = subprocess.run([exe, "kernels", "status", f"{owner}/{slug}"], capture_output=True, text=True,
                       env={**os.environ, "KAGGLE_CONFIG_DIR": config_dir})
    text = (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "UNKNOWN"
    return text.rsplit("KernelWorkerStatus.", 1)[-1].strip('" ') if "KernelWorkerStatus." in text else "UNKNOWN"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--also", nargs="*", default=[])
    p.add_argument("--need", type=int, default=2)
    p.add_argument("--grace", type=float, default=10.0, help="minutes one free session may wait for a second one")
    p.add_argument("--max-minutes", type=float, default=120.0)
    a = p.parse_args()
    slugs = list(a.also)
    for log in sorted(HERE.glob("lancio_*.jsonl")):
        for line in log.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("accepted", "successfully pushed" in r.get("answer", "")):
                slugs.append(r["slug"].split("/", 1)[1])
    slugs, ended, t0, first_free = list(dict.fromkeys(slugs)), {}, time.time(), None
    while True:
        running = []
        for s in slugs:
            if s in ended:
                continue
            st = status(s, a.owner, a.config_dir)
            if st in ("RUNNING", "QUEUED", "UNKNOWN"):
                running.append(s)
            else:
                ended[s] = st
        free = SESSIONS - len(running)
        print(f"{time.strftime('%H:%M:%S')} free={free} running={[s.removeprefix('vcc-') for s in running]}", flush=True)
        first_free = first_free or (time.time() if free >= 1 else None)
        waited = (time.time() - t0) / 60
        if free >= a.need or (first_free and (time.time() - first_free) / 60 >= a.grace) or waited >= a.max_minutes:
            print(f"free={free} ended={ended}", flush=True)
            return
        time.sleep(60)


if __name__ == "__main__":
    main()
