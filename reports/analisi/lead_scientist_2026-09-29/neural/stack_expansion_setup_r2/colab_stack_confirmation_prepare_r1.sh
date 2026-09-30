#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
SETUP="$DRIVE/runs/lead_stack_expansion_setup_2026-09-29_r2"
OUT="$DRIVE/runs/lead_stack_confirmation_prompts_2026-09-29_r1"
CODE=/content/lead_stack_confirmation_pack_r1
test ! -e "$OUT"
test ! -e "$CODE"
echo "344e204b77c2712a8e510cc30acdda87f2d299e6a24fd14b65e602c79630ee72  $SETUP/code_snapshot.tar.gz" | sha256sum -c -
mkdir -p "$OUT" "$CODE"
tar -xzf "$SETUP/code_snapshot.tar.gz" -C "$CODE"
export PYTHONPATH="$CODE/src"
cd "$CODE"
REPORT=reports/analisi/lead_scientist_2026-09-29/neural
python - "$OUT/resources.json" 2 <<'PY'
import json, shutil, sys
from pathlib import Path
info = {line.split(':')[0]: int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:', 'MemTotal:'))}
info['disk_free_bytes'] = shutil.disk_usage('/content').free
Path(sys.argv[1]).write_text(json.dumps(info, indent=2), encoding='utf-8')
assert info['MemAvailable'] >= int(sys.argv[2]) * 1024**3, 'Insufficient available RAM for preparation'
PY
python -m unittest discover -s "$REPORT" -p 'test_stack*pack.py' > "$OUT/contract_tests.log" 2>&1
ARGS=(--source "$DRIVE/data/raw/replogle/K562_gwps_raw_singlecell_01.h5ad"
  --pilot-bundle "$DRIVE/runs/lead_stack_2026-09-29_r2/bundle"
  --effects "$DRIVE/runs/lead_generator_2026-09-29_r3/prepared_effects.npz")
python -u "$REPORT/stack_confirmation_pack.py" plan "${ARGS[@]}"   --source-groups "$DRIVE/data/processed/k562_gwps_sc/x002/groups.csv"   --generator-manifest "$DRIVE/runs/lead_generator_2026-09-29_r3/target_manifest.json"   --registration "$REPORT/expansion_metadata_r1.json" --out "$OUT/plan.json"
python -u "$REPORT/stack_confirmation_pack.py" prepare "${ARGS[@]}" --plan "$OUT/plan.json" --out "$OUT/bundle"
python -m pip freeze > "$OUT/preparation_pip_freeze.txt"
sha256sum "$OUT/plan.json" "$OUT/bundle/bundle.json" > "$OUT/preparation_hashes.txt"
printf '%s\n' 'Prepared only: no weights, inference, scoring or upload.'
