"""Build immutable allowlisted Colab preparation snapshot. No upload/queue/run."""
from pathlib import Path
import argparse
import gzip
import hashlib
import io
import json
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    allow = json.loads((HERE / "STACK_ALLOWLIST.json").read_text())
    files = [HERE / f for f in allow["adapter_files"]] + [REPO / f for f in allow["local_module_files"]]
    files.append(HERE / "stack_plan_r1.json")
    entries, buffer = [], io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for path in sorted(files):
            data = path.read_bytes()
            rel = path.relative_to(REPO).as_posix()
            entry = tarfile.TarInfo(rel)
            entry.size, entry.mode, entry.mtime = len(data), 0o644, 0
            archive.addfile(entry, io.BytesIO(data))
            entries.append({"path": rel, "bytes": len(data), "sha256": digest(data)})
    payload = gzip.compress(buffer.getvalue(), mtime=0)
    archive_hash = digest(payload)
    plan_hash = digest((HERE / "stack_plan_r1.json").read_bytes())
    script = r'''#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export CODE_DIR=/content/lead_stack_code_r1
export PYTHONPATH="$CODE_DIR/src"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
SETUP="$DRIVE/runs/lead_stack_setup_2026-09-29_r1"
OUT="$DRIVE/runs/lead_stack_2026-09-29_r1"
ARCHIVE="$SETUP/code_snapshot.tar.gz"
test ! -e "$OUT"
test ! -e "$CODE_DIR"
echo "__ARCHIVE_HASH__  $ARCHIVE" | sha256sum -c -
mkdir -p "$CODE_DIR" "$OUT"
tar -xzf "$ARCHIVE" -C "$CODE_DIR"
cd "$CODE_DIR"
PILOT=reports/analisi/lead_scientist_2026-09-29/neural/stack_pilot.py
python -u "$PILOT" plan \
  --development-manifest "$DRIVE/runs/lead_generator_2026-09-29_r3/target_manifest.json" \
  --source-groups "$DRIVE/data/processed/k562_gwps_sc/x002/groups.csv" \
  --out "$OUT/plan.json"
echo "__PLAN_HASH__  $OUT/plan.json" | sha256sum -c -
python -u "$PILOT" prepare \
  --plan "$OUT/plan.json" \
  --source "$DRIVE/data/raw/replogle/K562_gwps_raw_singlecell_01.h5ad" \
  --destination "$DRIVE/data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad" \
  --effects "$DRIVE/runs/lead_generator_2026-09-29_r3/prepared_effects.npz" \
  --out "$OUT/bundle"
python -m pip freeze > "$OUT/preparation_pip_freeze.txt"
tar -czf "$OUT/bundle.tar.gz" -C "$OUT/bundle" .
sha256sum "$OUT/bundle.tar.gz" "$OUT/bundle/bundle.json" > "$OUT/bundle_hashes.txt"
printf '%s\n' 'Stack prompts prepared; no model download, inference or scoring.'
'''.replace("__ARCHIVE_HASH__", archive_hash).replace("__PLAN_HASH__", plan_hash)
    args.out.mkdir(parents=True)
    (args.out / "code_snapshot.tar.gz").write_bytes(payload)
    with (args.out / "colab_stack_prepare_r1.sh").open("x", encoding="utf-8", newline="\n") as f:
        f.write(script)
    manifest = {"code_archive_sha256": archive_hash, "code_archive_bytes": len(payload),
                "plan_sha256": plan_hash, "files": entries,
                "script_sha256": digest(script.encode()), "action": "prepare_only_no_model_no_scoring",
                "drive_setup": "runs/lead_stack_setup_2026-09-29_r1",
                "drive_output": "runs/lead_stack_2026-09-29_r1"}
    with (args.out / "setup_manifest.json").open("x", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps({k: v for k, v in manifest.items() if k != "files"}, indent=2))


if __name__ == "__main__":
    main()
