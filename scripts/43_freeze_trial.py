"""Freeze one trial: the exact state the run was executed from.

A manifest records what a stage read and wrote. This records what the *machine*
and the *repository* were, before anything runs, so a number produced today can
be re-derived or discredited later: the commit, whether the tree was dirty and
what differed, the locked dependency versions as actually installed, the
fingerprints of every input dataset, the resolved trial configuration, and the
seed.

The uncommitted diff is stored as a patch beside the freeze rather than
summarised. "There were local changes" is not reproducible; the patch is.

Freezes are never overwritten, for the same reason manifests are not: a freeze
is the evidence that a given run happened under a given state.

    scripts/py.cmd scripts/43_freeze_trial.py --run-id t001 --trial trial-01-transfer
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.manifest import (
    RunManifest,
    environment_fingerprint,
    file_fingerprint,
    snapshot_source,
)
from vcc2026.resources import snapshot
from vcc2026.trials import load_trial, trial_ids

REPO = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str | None:
    """Run git and return stdout, decoded as UTF-8.

    The encoding is explicit because it has already broken this script once:
    `text=True` decodes with the locale codec, which on this machine is cp1252,
    and `git diff` of the Italian documentation carries bytes cp1252 cannot
    represent. The decode then raises inside subprocess's reader thread, leaving
    `stdout` as None and taking down the freeze -- before any compute, but also
    before any record of it.
    """
    try:
        out = subprocess.run(
            ["git", *args], cwd=REPO, capture_output=True, timeout=120,
            encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"<git unavailable: {type(exc).__name__}: {exc}>"
    if out.returncode != 0:
        return None
    return (out.stdout or "").strip()


def code_state(run: Path, *, allow_overwrite: bool) -> dict:
    status = _git("status", "--porcelain")
    dirty = bool(status)
    state = {
        "commit": _git("rev-parse", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "commit_date": _git("log", "-1", "--format=%cI"),
        "describe": _git("describe", "--always", "--dirty"),
        "dirty": dirty,
        "status_porcelain": status.splitlines() if status else [],
    }
    if dirty:
        patch = _git("diff", "HEAD")
        untracked = _git("ls-files", "--others", "--exclude-standard")
        patch_path = run / "uncommitted.patch"
        if patch_path.exists() and not allow_overwrite:
            raise SystemExit(f"{patch_path} exists; use a new --run-id")
        patch_path.write_text(patch or "", encoding="utf-8")
        state["uncommitted_patch"] = str(patch_path)
        state["uncommitted_patch_bytes"] = patch_path.stat().st_size
        files = untracked.splitlines() if untracked else []
        state["untracked_files"] = files
        # A patch against HEAD does not contain a file git has never seen, so an
        # untracked module would leave the freeze unable to identify the code
        # that ran. Fingerprint the ones that can change behaviour.
        state["untracked_code_fingerprints"] = {
            rel: file_fingerprint(REPO / rel)
            for rel in files
            if rel.startswith(("src/", "scripts/", "configs/", "tests/"))
        }
        state["note"] = (
            "The tree was NOT clean. The diff against HEAD is stored beside this "
            "freeze; untracked files under src/, scripts/, configs/ and tests/ "
            "are fingerprinted because a patch cannot contain them."
        )
    return state


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--trial", required=True)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--signature-run", default=None,
                   help="run id whose signatures this trial uses (default: from trials.yaml)")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--allow-overwrite", action="store_true")
    args = p.parse_args()

    try:
        trial = load_trial(args.trial)
    except KeyError:
        raise SystemExit(f"unknown trial {args.trial!r}; known: {trial_ids()}")
    seed = args.seed if args.seed is not None else int(trial["seed"])
    run = args.out or config.run_dir(args.run_id)
    run.mkdir(parents=True, exist_ok=True)

    out = run / "freeze.json"
    if out.exists() and not args.allow_overwrite:
        raise SystemExit(
            f"{out} exists; a freeze is evidence of one run. Use a new --run-id."
        )

    paths = config.paths()
    inputs: dict[str, dict] = {}
    for rel in trial.get("source_data", []):
        inputs[rel] = file_fingerprint(paths.data_root / rel)
    for name in ("gene_names.csv", "pert_counts.csv", "manifest.json"):
        inputs[f"raw/controls/{name}"] = file_fingerprint(
            paths.raw / "controls" / name
        )

    sig_run = args.signature_run or trial.get("model", {}).get("signature_run")
    signatures = {}
    if sig_run:
        sig_dir = config.artifact_root() / sig_run / "signatures"
        signatures["dir"] = str(sig_dir)
        signatures["exists"] = sig_dir.exists()
        if sig_dir.exists():
            for npz in sorted(sig_dir.glob("*.npz")):
                signatures[npz.stem] = file_fingerprint(npz)

    # The code itself, not a description of it. A freeze whose untracked modules
    # exist only as sha256 values identifies code that cannot be recovered.
    snapshot_path = run / "source_snapshot.tar.gz"
    if snapshot_path.exists() and not args.allow_overwrite:
        raise SystemExit(f"{snapshot_path} exists; use a new --run-id")
    if snapshot_path.exists():
        snapshot_path.unlink()
    source = snapshot_source(snapshot_path, repo_root=REPO)

    lock = REPO / "requirements.lock.txt"
    freeze = {
        "source_snapshot": source,
        "run_id": args.run_id,
        "trial": trial,
        "seed": seed,
        "code": code_state(run, allow_overwrite=args.allow_overwrite),
        "environment": environment_fingerprint(),
        "requirements_lock": file_fingerprint(lock),
        "configs": {
            rel: file_fingerprint(REPO / "configs" / rel)
            for rel in ("config.yaml", "sources.yaml", "trials.yaml")
        },
        "data_identifiers": inputs,
        "signatures": signatures,
        "resources_before_run": snapshot(config.artifact_root()).as_dict(),
        "roots": {
            "data_root": str(paths.data_root),
            "artifact_root": str(config.artifact_root()),
            "run_dir": str(run),
        },
        "declared": {
            "uploaded": False,
            "leaderboard_score": None,
            "note": (
                "Local training, inference and packaging only. No submission has "
                "been uploaded and no submission quota has been consumed."
            ),
        },
    }
    out.write_text(json.dumps(freeze, indent=2, default=str), encoding="utf-8")

    man = RunManifest(run_id=args.run_id, stage="43_freeze_trial",
                      config={"trial": args.trial, "seed": seed}, seed=seed)
    for name, fp in inputs.items():
        if fp.get("exists"):
            man.add_input(name, fp["path"])
    man.add_output("freeze", out)
    man.add_output("source_snapshot", snapshot_path)
    man.note("Freeze written before any compute; a dirty tree is captured as a patch.")
    man.write(run / "manifest_43_freeze_trial.json",
              allow_overwrite=args.allow_overwrite)

    code = freeze["code"]
    print(f"trial       : {trial['id']} ({trial['kind']})")
    print(f"commit      : {code['commit']} dirty={code['dirty']}")
    print(f"seed        : {seed}")
    print(f"source      : {source['n_files']} files -> {snapshot_path.name} "
          f"({source['bytes'] / 1024:.0f} KB)")
    print(f"inputs      : {sum(1 for v in inputs.values() if v.get('exists'))}"
          f"/{len(inputs)} present")
    if sig_run:
        print(f"signatures  : {signatures.get('dir')} exists={signatures.get('exists')}")
    res = freeze["resources_before_run"]
    print(f"resources   : RAM avail {res['ram_available_gib']:.2f} GiB, "
          f"disk free {res['disk_free_gib']:.2f} GiB")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
