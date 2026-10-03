"""Push the next kernels of the ingestion queue into the CPU sessions Kaggle has free, once.

Kaggle runs 5 batch CPU sessions at a time. The queue below is the order decided on 3/10 at 18:30; a kernel already
accepted (the launch logs say so) is skipped, the others are pushed in order until Kaggle refuses one. The command is
run by the session each time a kernel ends: it is not a monitor and nothing calls it on its own (incident
E-20261003-001, where monitors pushed GPU kernels by themselves).

The Orion parts listed here are the r2 parts again, with the part rule (`-r3`): a kernel that ended in ERROR is not a
valid source for another kernel ("not valid kernel sources", 3/10 18:27), so the five r2 parts, complete as data,
cannot be mounted by a training or by the line verification.

    python fill_sessions.py --config-dir <dir> --owner davideferrante11 --stages <data-root folder> [--max N] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMMIT_ORION = "0fa011530c2a4556d46fd27d3a93e7fbe4f8f909"            # the commit of the Orion code snapshot (r1)
CD4_FILES = [f"D{d}_{c}" for d in (1, 2, 3, 4) for c in ("Rest", "Stim8hr", "Stim48hr")]


def orion(line: str, part: str) -> dict:
    return {"kind": "orion", "line": line, "part": part,
            "slug": f"vcc-orion-{line.lower()}-p{part.replace('/', 'of')}-r3"}


def cd4(file: str, part: str) -> dict:
    return {"kind": "cd4", "file": file, "part": part,
            "slug": f"vcc-cd4-{file.lower().replace('_', '-')}-p{part.replace('/', 'of')}-r1"}


QUEUE = ([orion("HCT116", "2/4")] + [cd4("D1_Rest", p) for p in ("0/2", "1/2")]
         + [orion("HCT116", "1/4"), orion("HCT116", "3/4")]
         + [cd4(f, p) for f in CD4_FILES[1:3] for p in ("0/2", "1/2")]
         + [orion("HEK293T", f"{i}/8") for i in (0, 1, 2)]
         + [cd4(f, p) for f in CD4_FILES[3:] for p in ("0/2", "1/2")])


def accepted() -> set[str]:
    done = set()
    for log in HERE.glob("lancio_*.jsonl"):
        for line in log.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("accepted", "successfully pushed" in r.get("answer", "")):
                done.add(r["slug"].split("/", 1)[1])
    return done


def command(e: dict, a) -> list[str]:
    base = ["--config-dir", a.config_dir, "--owner", a.owner, "--slug", e["slug"]]
    stage = a.stages / f"kernel_{e['slug']}"
    if e["kind"] == "orion":
        return [sys.executable, str(HERE / "build_orion_kaggle_r2.py"), *base, "--stage", str(stage), "--code-stage",
                str(a.stages / "kaggle_code_r1"), "--line", e["line"], "--part", e["part"], "--commit", COMMIT_ORION,
                "--part-rule", "--launch-log", str(HERE / "lancio_orion_r2.jsonl"),
                *(["--repush"] if stage.exists() else [])]
    k = 0
    while stage.exists():                                           # a refused attempt keeps its folder
        k += 1
        stage = a.stages / f"kernel_{e['slug']}_{k}"
    return [sys.executable, str(HERE / "build_cd4_kaggle.py"), "kernel", *base, "--stage", str(stage), "--code-stage",
            str(a.stages / "kaggle_code_cd4_r1"), "--file", e["file"], "--part", e["part"], "--readahead", "8",
            "--launch-log", str(HERE / "lancio_cd4_r1.jsonl")]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--stages", type=Path, required=True)
    p.add_argument("--max", type=int, default=5)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    done = accepted()
    todo = [e for e in QUEUE if e["slug"] not in done]
    print(f"{len(QUEUE) - len(todo)} of {len(QUEUE)} already accepted; next: {[e['slug'] for e in todo[:6]]}")
    pushed = 0
    for e in todo[: a.max]:
        cmd = command(e, a)
        if a.dry_run:
            print(" ".join(cmd[1:]))
            continue
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            print(f"{e['slug']}: not accepted ({(r.stdout + r.stderr).strip()[-160:]})")
            break
        pushed += 1
        print(f"{e['slug']}: pushed")
    print(f"pushed {pushed}; {len(todo) - pushed} left in the queue")


if __name__ == "__main__":
    main()
