#!/usr/bin/env bash
# Joint 14-arm development; confirmation runs separately on frozen disjoint targets.
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export CODE_DIR=/content/lead_generator_code_r1
export VCC2026_DATA_ROOT=/content/lead_generator_data_r1
export PYTHONPATH="$CODE_DIR/src"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export MKL_NUM_THREADS=2
OUT="$DRIVE/runs/lead_generator_2026-09-29_r1"
ARCHIVE="$DRIVE/runs/lead_generator_setup_2026-09-29_r1/code_snapshot.tar.gz"
mkdir -p "$CODE_DIR" "$VCC2026_DATA_ROOT"
tar -xzf "$ARCHIVE" -C "$CODE_DIR"
cd "$CODE_DIR"
echo "lead generator development start $(date -u +%FT%TZ)"
free -g
python - <<'PY'
from importlib.metadata import version
from pathlib import Path
import os, shutil
assert version('cell-eval2') == '0.16.0', version('cell-eval2')
source = Path(os.environ['DRIVE']) / 'data'
dest = Path(os.environ['VCC2026_DATA_ROOT'])
for rel in ['raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad',
            'external/K562_gwps_raw_bulk_01.h5ad',
            'processed/banco_hepg2_v2_2026-09-26/t19like.npz',
            'processed/banco_hepg2_v2_2026-09-26/targets.txt']:
    target = dest / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(target)
    print('copy', rel, (source / rel).stat().st_size, flush=True)
    shutil.copyfile(source / rel, target)
print('versions', {p: version(p) for p in ['cell-eval2', 'numpy', 'scipy', 'pandas', 'h5py', 'scanpy']}, flush=True)
PY
BENCH=reports/analisi/lead_scientist_2026-09-29/generator_bench.py
python -u "$BENCH" --phase prepare --truth full --data-root "$VCC2026_DATA_ROOT" --out "$OUT"
python -u "$BENCH" --phase run --data-root "$VCC2026_DATA_ROOT" --out "$OUT" --split development
echo "lead generator development complete $(date -u +%FT%TZ)"
