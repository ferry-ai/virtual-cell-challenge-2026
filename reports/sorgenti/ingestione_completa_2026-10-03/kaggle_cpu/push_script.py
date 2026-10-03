"""Push one standalone script as a private Kaggle CPU kernel (a probe, a measurement), and record the push.

The script is copied as it is into a new stage folder with its metadata; nothing is generated. One command, typed by
the session, per kernel (incident E-20261003-001). The CLI exits 0 on a refused push: the answer decides.

    python push_script.py --config-dir <dir> --owner davideferrante11 --script <file.py> --stage <new dir> \
        --slug vcc-dld1-probe-r1 [--kernels <slug> ...] [--datasets <owner/slug> ...] [--launch-log <jsonl>]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_orion_kaggle_r2 import kaggle, sha256_file  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--script", type=Path, required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--kernels", nargs="*", default=[])
    p.add_argument("--datasets", nargs="*", default=[])
    p.add_argument("--launch-log", type=Path)
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    compile(a.script.read_text(encoding="utf-8"), str(a.script), "exec")
    a.stage.mkdir(parents=True)
    shutil.copyfile(a.script, a.stage / "run.py")
    (a.stage / "kernel-metadata.json").write_text(json.dumps(
        {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
         "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False, "enable_internet": True,
         "dataset_sources": a.datasets, "kernel_sources": [f"{a.owner}/{s}" for s in a.kernels],
         "competition_sources": []}, indent=1))
    r = kaggle(["kernels", "push", "-p", str(a.stage)], a.config_dir)
    answer = ((r.stdout or "") + (r.stderr or "")).strip()
    accepted = r.returncode == 0 and "successfully pushed" in answer and "not valid" not in answer
    record = {"slug": f"{a.owner}/{a.slug}", "script": a.script.as_posix(), "script_sha256": sha256_file(a.script),
              "stage": a.stage.as_posix(), "kernels": a.kernels, "datasets": a.datasets,
              "pushed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "returncode": r.returncode,
              "accepted": accepted, "answer": answer[-600:]}
    if a.launch_log:
        with open(a.launch_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    if not accepted:
        sys.exit("the push failed")


if __name__ == "__main__":
    main()
