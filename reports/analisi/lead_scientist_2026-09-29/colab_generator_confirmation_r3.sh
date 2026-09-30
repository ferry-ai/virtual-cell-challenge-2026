#!/usr/bin/env bash
# Confirmation of the completed joint development, with the identical frozen code.
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export CODE_DIR=/content/lead_generator_confirmation_code_r3
export VCC2026_DATA_ROOT=/content/lead_generator_data_r3
export PYTHONPATH="$CODE_DIR/src"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export MKL_NUM_THREADS=2
OUT="$DRIVE/runs/lead_generator_2026-09-29_r3"
ARCHIVE="$DRIVE/runs/lead_generator_setup_2026-09-29_r3/code_snapshot.tar.gz"
test -f "$OUT/development/selection.json"
test ! -d "$OUT/confirmation"
echo "f7324778e5d7225552734e2c7303353f46dee6c01e9d455703adce3b9b105860  $ARCHIVE" | sha256sum -c -
mkdir "$CODE_DIR"
tar -xzf "$ARCHIVE" -C "$CODE_DIR"
cd "$CODE_DIR"
python -u - "$OUT" <<'PY'
from importlib.metadata import version
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys
out = Path(sys.argv[1])
manifest = json.loads((out / 'target_manifest.json').read_text())
selection = json.loads((out / 'development/selection.json').read_text())
assert manifest['design'] == 'joint_14_arms_amendment_02'
assert manifest['truth'] == 'full'
assert not set(manifest['development']) & set(manifest['confirmation'])
assert version('cell-eval2') == '0.16.0'
expected = json.loads((out / 'development_environment.json').read_text())['versions']
actual = {p: version(p) for p, v in expected.items() if v is not None}
assert all(actual[p] == v for p, v in expected.items() if v is not None), (expected, actual)
finalists = selection['shortlist']
assert len(finalists) <= 2
if not finalists:
    print('No finalist selected; confirmation not run.', flush=True)
    sys.exit(0)
# Restore only missing input files after a Colab restart; the frozen bench verifies hashes.
data = Path(os.environ['VCC2026_DATA_ROOT'])
drive_data = Path(os.environ['DRIVE']) / 'data'
for rel in ['raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad',
            'external/K562_gwps_raw_bulk_01.h5ad',
            'processed/banco_hepg2_v2_2026-09-26/t19like.npz',
            'processed/banco_hepg2_v2_2026-09-26/targets.txt']:
    target = data / rel
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(drive_data / rel, target)
arms = ['1:0'] + [f'bins:{a:g}' if g == 'bins' else f'{a:g}:{p:g}' for a, p, g in finalists]
command = [sys.executable, 'reports/analisi/lead_scientist_2026-09-29/generator_bench.py',
           '--phase', 'run', '--data-root', str(data), '--out', str(out),
           '--split', 'confirmation', '--arms', *arms]
with (out / 'confirmation_dispatch.json').open('x') as f:
    json.dump({'backend': 'Colab', 'reason': 'Kaggle dataset creation returned success but dataset remains inaccessible with 403',
               'code_sha256': 'f7324778e5d7225552734e2c7303353f46dee6c01e9d455703adce3b9b105860',
               'selection_sha256': hashlib.sha256((out / 'development/selection.json').read_bytes()).hexdigest(),
               'versions': actual, 'command': command}, f, indent=2)
subprocess.run(command, check=True)
PY
echo "lead generator confirmation complete $(date -u +%FT%TZ)"
