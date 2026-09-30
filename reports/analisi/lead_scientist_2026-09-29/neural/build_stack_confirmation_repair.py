"""Freeze a preparation-only repair for missing reserve transfer rows in job075."""
from datetime import datetime, timezone
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
REL = HERE.relative_to(REPO).as_posix()
BASE_SHA = '344e204b77c2712a8e510cc30acdda87f2d299e6a24fd14b65e602c79630ee72'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    with path.open('xb') as out:
        out.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    a = parser.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    base = (HERE / 'stack_expansion_setup_r2/code_snapshot.tar.gz').read_bytes()
    if sha(base) != BASE_SHA:
        raise ValueError('Frozen original preparation archive changed')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(base), mode='r:gz') as archive:
        for item in archive.getmembers():
            if item.isfile():
                files[item.name] = archive.extractfile(item).read()
    additions = [HERE / 'stack_confirmation_effects.py', HERE / 'test_stack_confirmation_effects.py',
                 HERE / 'PROTOCOLLO_STACK_AB.md', HERE / 'RIPARAZIONE_075.md',
                 HERE.parent / 'generator_bench.py', REPO / 'scripts/98_multisource_effects.py',
                 REPO / 'configs/config.yaml', *sorted((REPO / 'src/vcc2026').glob('*.py'))]
    for path in additions:
        relative, content = path.relative_to(REPO).as_posix(), path.read_bytes()
        if relative in files and files[relative] != content:
            raise ValueError('Attempted change to frozen dependency: ' + relative)
        files[relative] = content
    a.out.mkdir(parents=True)
    archive_path = a.out / 'code_snapshot.tar.gz'
    with tarfile.open(archive_path, 'w:gz') as archive:
        for name, content in sorted(files.items()):
            item = tarfile.TarInfo(name); item.size = len(content); item.mtime = 0; item.mode = 0o644
            archive.addfile(item, io.BytesIO(content))
    archive_hash = sha(archive_path.read_bytes())
    launcher = f'''#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
export VCC2026_DATA_ROOT="$DRIVE/data"
SETUP="$DRIVE/runs/lead_stack_confirmation_repair_2026-09-29_r1"
OUT="$DRIVE/runs/lead_stack_confirmation_prompts_2026-09-29_r2"
CODE=/content/lead_stack_confirmation_pack_r2
test ! -e "$OUT"
test ! -e "$CODE"
echo "{archive_hash}  $SETUP/code_snapshot.tar.gz" | sha256sum -c -
mkdir -p "$OUT" "$CODE"
tar -xzf "$SETUP/code_snapshot.tar.gz" -C "$CODE"
export PYTHONPATH="$CODE/src"
cd "$CODE"
REPORT={REL}
python -m unittest discover -s "$REPORT" -p 'test_stack_confirmation_effects.py' > "$OUT/effects_contract_tests.log" 2>&1
python -u "$REPORT/stack_confirmation_effects.py" \\
  --effects "$DRIVE/data/processed/banco_hepg2_v2_2026-09-26/t19like.npz" \\
  --bulk "$DRIVE/data/external/K562_gwps_raw_bulk_01.h5ad" \\
  --generator-manifest "$DRIVE/runs/lead_generator_2026-09-29_r3/target_manifest.json" \\
  --prepared-effects "$DRIVE/runs/lead_generator_2026-09-29_r3/prepared_effects.npz" \\
  --pilot-bundle "$DRIVE/runs/lead_stack_2026-09-29_r2/bundle" --out "$OUT/effects"
ARGS=(--source "$DRIVE/data/raw/replogle/K562_gwps_raw_singlecell_01.h5ad"
  --pilot-bundle "$DRIVE/runs/lead_stack_2026-09-29_r2/bundle"
  --effects "$OUT/effects/confirmation_effects.npz")
python -u "$REPORT/stack_confirmation_pack.py" plan "${{ARGS[@]}}" \\
  --source-groups "$DRIVE/data/processed/k562_gwps_sc/x002/groups.csv" \\
  --generator-manifest "$DRIVE/runs/lead_generator_2026-09-29_r3/target_manifest.json" \\
  --registration "$REPORT/expansion_metadata_r1.json" --out "$OUT/plan.json"
python -u "$REPORT/stack_confirmation_pack.py" prepare "${{ARGS[@]}}" --plan "$OUT/plan.json" --out "$OUT/bundle"
python -m pip freeze > "$OUT/preparation_pip_freeze.txt"
sha256sum "$OUT/plan.json" "$OUT/bundle/bundle.json" "$OUT/effects/manifest.json" > "$OUT/preparation_hashes.txt"
printf '%s\\n' 'Prepared only. AB selection required before any confirmation inference or scoring.'
'''
    write(a.out / '080_lead_stack_confirmation_prepare_r2.sh', launcher.encode())
    record = {'utc': datetime.now(timezone.utc).isoformat(), 'claim': 'Code frozen, no real execution or queue',
        'archive_sha256': archive_hash, 'base_archive_sha256': BASE_SHA,
        'scientific_change': 'none; missing transfer rows from same frozen t19like and evidence mask',
        'all_base_files_byte_identical': True, 'ab_selection_required_before_inference_or_scoring': True,
        'files': {name: {'bytes': len(content), 'sha256': sha(content)} for name, content in sorted(files.items())}}
    write(a.out / 'manifest.json', (json.dumps(record, indent=2) + '\n').encode())
    print(json.dumps({'out': str(a.out), 'archive_sha256': archive_hash, 'files': len(files)}))


if __name__ == '__main__':
    main()
