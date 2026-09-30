"""Freeze only reviewed code and small metadata; never read expression matrices."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
REL = "reports/analisi/lead_scientist_2026-09-29/neural"


def sha(content):
    return hashlib.sha256(content).hexdigest()


def write(path, content):
    with path.open("xb") as stream:
        stream.write(content)


def shell(kind, archive_hash, setup_revision):
    is_prod = kind == "production"
    prefix = f"""#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
SETUP="$DRIVE/runs/lead_stack_expansion_setup_2026-09-29_{setup_revision}"
OUT="$DRIVE/runs/lead_stack_{kind}_prompts_2026-09-29_r1"
CODE=/content/lead_stack_{kind}_pack_r1
test ! -e "$OUT"
test ! -e "$CODE"
echo "{archive_hash}  $SETUP/code_snapshot.tar.gz" | sha256sum -c -
mkdir -p "$OUT" "$CODE"
tar -xzf "$SETUP/code_snapshot.tar.gz" -C "$CODE"
export PYTHONPATH="$CODE/src"
cd "$CODE"
REPORT={REL}
python - "$OUT/resources.json" {4 if is_prod else 2} <<'PY'
import json, shutil, sys
from pathlib import Path
info = {{line.split(':')[0]: int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:', 'MemTotal:'))}}
info['disk_free_bytes'] = shutil.disk_usage('/content').free
Path(sys.argv[1]).write_text(json.dumps(info, indent=2), encoding='utf-8')
assert info['MemAvailable'] >= int(sys.argv[2]) * 1024**3, 'Insufficient available RAM for preparation'
PY
python -m unittest discover -s "$REPORT" -p 'test_stack*pack.py' > "$OUT/contract_tests.log" 2>&1
"""
    if is_prod:
        command = """ARGS=(--source "$DRIVE/data/processed/k562_gwps_sc/x002"
  --controls "$DRIVE/data/raw/controls"
  --effects "$DRIVE/data/processed/effects_t25_2026-09-27"
  --registration "$REPORT/expansion_metadata_r1.json")
python -u "$REPORT/stack_production_pack.py" plan "${ARGS[@]}" --out "$OUT/plan.json"
python -u "$REPORT/stack_production_pack.py" prepare "${ARGS[@]}" --plan "$OUT/plan.json" --out "$OUT/bundle"
"""
    else:
        command = """ARGS=(--source "$DRIVE/data/raw/replogle/K562_gwps_raw_singlecell_01.h5ad"
  --pilot-bundle "$DRIVE/runs/lead_stack_2026-09-29_r2/bundle"
  --effects "$DRIVE/runs/lead_generator_2026-09-29_r3/prepared_effects.npz")
python -u "$REPORT/stack_confirmation_pack.py" plan "${ARGS[@]}" \
  --source-groups "$DRIVE/data/processed/k562_gwps_sc/x002/groups.csv" \
  --generator-manifest "$DRIVE/runs/lead_generator_2026-09-29_r3/target_manifest.json" \
  --registration "$REPORT/expansion_metadata_r1.json" --out "$OUT/plan.json"
python -u "$REPORT/stack_confirmation_pack.py" prepare "${ARGS[@]}" --plan "$OUT/plan.json" --out "$OUT/bundle"
"""
    return prefix + command + """python -m pip freeze > "$OUT/preparation_pip_freeze.txt"
sha256sum "$OUT/plan.json" "$OUT/bundle/bundle.json" > "$OUT/preparation_hashes.txt"
printf '%s\\n' 'Prepared only: no weights, inference, scoring or upload.'
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--setup-revision", choices=("r1", "r2"), default="r1")
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    frozen = HERE / "stack_setup_r1" / "code_snapshot.tar.gz"
    original = frozen.read_bytes()
    if sha(original) != "a2e407961e2aefacd634f17541440bfd1e7035a036658f63cb655a33a9926698":
        raise ValueError("Frozen original code archive differs")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(original), mode="r:gz") as archive:
        for member in archive.getmembers():
            if member.isfile() and (member.name.startswith("src/") or member.name == REL + "/stack_pilot.py"):
                files[member.name] = archive.extractfile(member).read()
    if sha(files[REL + "/stack_pilot.py"]) != "b259371df3d0d515003597c4d9ce5755c25840f0d36fc96d8ac390ffe1275508":
        raise ValueError("Frozen pilot helper differs")
    if args.setup_revision == "r2":
        scorer_archive = (HERE / "stack_scoring_setup_r3/scoring_snapshot.tar.gz").read_bytes()
        if sha(scorer_archive) != "9f89e6380704210adac7445199ca15117e85138193fd55c3cd6de8749a681f65":
            raise ValueError("Frozen scorer helper snapshot differs")
        with tarfile.open(fileobj=io.BytesIO(scorer_archive), mode="r:gz") as archive:
            for member in archive.getmembers():
                if member.isfile() and (member.name.startswith("src/") or member.name == REL + "/score_stack_pilot.py" or member.name.endswith("/anchors.json")):
                    content = archive.extractfile(member).read()
                    if member.name in files and files[member.name] != content:
                        raise ValueError("Frozen inference and scorer dependencies differ: " + member.name)
                    files[member.name] = content
    for name in ("stack_production_pack.py", "stack_confirmation_pack.py", "test_stack_production_pack.py",
                 "test_stack_confirmation_pack.py", "PROPOSTA_STACK_ESTENSIONE.md", "expansion_metadata_r1.json", "subset_spotcheck_r2.json"):
        files[REL + "/" + name] = (HERE / name).read_bytes()
    if args.setup_revision == "r2":
        for name in ("PROTOCOLLO_STACK_CONFERMA.md", "stack_confirmation_infer.py", "stack_confirmation_score.py", "test_stack_confirmation_infer.py", "test_stack_confirmation_score.py"):
            files[REL + "/" + name] = (HERE / name).read_bytes()
    metadata = json.loads(files[REL + "/expansion_metadata_r1.json"])
    args.out.mkdir(parents=True)
    archive_path = args.out / "code_snapshot.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for name, content in sorted(files.items()):
            item = tarfile.TarInfo(name)
            item.size, item.mode, item.mtime = len(content), 0o644, 0
            archive.addfile(item, io.BytesIO(content))
    archive_hash = sha(archive_path.read_bytes())
    for kind in ("production", "confirmation"):
        write(args.out / f"colab_stack_{kind}_prepare_r1.sh", shell(kind, archive_hash, args.setup_revision).encode())
    targets = {"claim": "Frozen target registration only; source cell plan/real extraction not run",
        "production_targets": metadata["production_targets_subset_ge64"],
        "production_fallback": metadata["production_fallback_targets"],
        "confirmation_targets": metadata["confirmation_targets_original"],
        "source_counts": metadata["counts_per_panel_target"],
        "metadata_sha256": sha(files[REL + "/expansion_metadata_r1.json"])}
    write(args.out / "target_registration.json", (json.dumps(targets, indent=2) + "\n").encode())
    manifest = {"status": "prepared_code_not_executed_on_real_data", "utc": datetime.now(timezone.utc).isoformat(),
        "setup_revision": args.setup_revision,
        "code_archive_sha256": archive_hash, "code_archive_bytes": archive_path.stat().st_size,
        "files": [{"path": k, "bytes": len(v), "sha256": sha(v)} for k, v in sorted(files.items())],
        "tests": "7 synthetic tests passed; source-cell row order, duplicate genes, explicit masks, disjointness and byte-identical controls",
        "production_cells_including_ntc": metadata["io"]["production_selected_cells_with_ntc"],
        "confirmation_new_source_cells": metadata["io"]["confirmation_original_selected_cells_with_ntc"] - 512,
        "production_memory_guard_gib": 4, "confirmation_memory_guard_gib": 2,
        "inference_or_jobs_authorized": False}
    write(args.out / "setup_manifest.json", (json.dumps(manifest, indent=2) + "\n").encode())
    hashes = {p.name: {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in sorted(args.out.iterdir())}
    write(args.out / "artifact_hashes.json", (json.dumps(hashes, indent=2) + "\n").encode())
    print(json.dumps({"out": str(args.out), "archive_sha256": archive_hash, "archive_bytes": archive_path.stat().st_size}))


if __name__ == "__main__":
    main()
