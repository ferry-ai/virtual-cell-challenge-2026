"""Probe: how many kernel outputs can one Kaggle kernel mount, and how long do they take to attach (D-053 training).

The training on the expanded corpus must mount every source's compact twins (kernel outputs of davideferrante11, up to
20 GB each), the prepass state, the anchors and the code. This pushes a CPU kernel that only lists /kaggle/input:
for each mount, its files and bytes, and the seconds since the kernel started. Nothing is read beyond the listing.
The push answer (accepted or refused, with Kaggle's message) is the first measurement; the listing is the second.

    python sonda_montaggi.py --config-dir <dir> --owner davideferrante11 --stage <new dir> --slug vcc-probe-mounts-r1 \
        --kernels <slug> ... [--datasets <owner/slug> ...] --launch-log <jsonl> [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

KERNEL = r'''
import json, os, time
from pathlib import Path
t0 = time.time()
INPUT = Path("/kaggle/input")
OUT = Path("/kaggle/working")
rows = []
tops = sorted(p for p in INPUT.glob("*") if p.is_dir())
nested = sorted(p for p in INPUT.glob("*/*/*") if p.is_dir() and p.parts[-3] in ("datasets", "notebooks"))
for d in nested + [t for t in tops if t.name not in ("datasets", "notebooks")]:
    files = [f for f in d.rglob("*") if f.is_file()]
    rows.append({"mount": str(d.relative_to(INPUT)), "files": len(files),
                 "bytes": sum(f.stat().st_size for f in files), "seconds": round(time.time() - t0, 1)})
(OUT / "mounts.json").write_text(json.dumps({"mounts": rows, "seconds": round(time.time() - t0, 1),
                                             "cpus": os.cpu_count()}, indent=1))
print(json.dumps({"mounts": len(rows), "seconds": round(time.time() - t0, 1)}))
'''


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--kernels", nargs="+", default=[])
    p.add_argument("--datasets", nargs="+", default=[])
    p.add_argument("--launch-log", type=Path)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    a.stage.mkdir(parents=True)
    (a.stage / "run.py").write_text(KERNEL, encoding="utf-8", newline="\n")
    meta = {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False, "dataset_sources": a.datasets,
            "kernel_sources": [f"{a.owner}/{k}" for k in a.kernels], "competition_sources": []}
    (a.stage / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    record = {"slug": f"{a.owner}/{a.slug}", "stage": a.stage.as_posix(), "kernel_sources": len(a.kernels),
              "dataset_sources": len(a.datasets), "sources": meta["kernel_sources"] + a.datasets,
              "run_sha256": hashlib.sha256((a.stage / "run.py").read_bytes()).hexdigest()}
    if a.dry_run:
        print(json.dumps(record))
        return
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
    r = subprocess.run([exe, "kernels", "push", "-p", str(a.stage)], capture_output=True, text=True,
                       env={**os.environ, "KAGGLE_CONFIG_DIR": a.config_dir})
    answer = ((r.stdout or "") + (r.stderr or "")).strip()
    record.update(pushed_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), returncode=r.returncode,
                  accepted=r.returncode == 0 and "successfully pushed" in answer, answer=answer[-800:])
    print(json.dumps({k: record[k] for k in ("slug", "kernel_sources", "dataset_sources", "accepted", "answer")}))
    if a.launch_log:
        with open(a.launch_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    main()
