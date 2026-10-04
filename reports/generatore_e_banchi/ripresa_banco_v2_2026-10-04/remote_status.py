"""Read existing Kaggle jobs and quota once; never launch or stop a job."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[3]
CONFIGS = {"davideferrante11": ".kaggle-davideferrante11", "davidmaisterx": ".kaggle",
           "codex": ".kaggle-codex"}


def call(owner, args):
    env = {**os.environ, "KAGGLE_CONFIG_DIR": str(Path.home() / CONFIGS[owner])}
    r = subprocess.run([str(Path(sys.executable).with_name("kaggle.exe")), *args], env=env,
                       capture_output=True, text=True, timeout=60)
    return {"owner": owner, "args": args, "returncode": r.returncode,
            "stdout": r.stdout.strip(), "stderr": r.stderr.strip(),
            "utc": datetime.now(timezone.utc).isoformat()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--job", action="append", default=[])
    a = p.parse_args()
    jobs = a.job or [json.loads(s)["slug"] for s in
                    (REPO / "reports/sorgenti/ingestione_completa_2026-10-03/kaggle_cpu/lancio_cd4_r1.jsonl")
                    .read_text().splitlines() if '"accepted": true' in s]
    jobs = sorted(set(j for j in jobs if "-d3-" in j or "-d4-" in j)) if not a.job else jobs
    tasks = [(j.split('/')[0], ["kernels", "status", j]) for j in jobs]
    tasks += [(o, ["quota"]) for o in CONFIGS]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda t: call(*t), tasks))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    for r in results:
        print(r["owner"], r["stdout"] or r["stderr"])


if __name__ == "__main__":
    main()
