#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export CODE_DIR=/content/lead_stack_code_r2
export PYTHONPATH="$CODE_DIR/src"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
SETUP="$DRIVE/runs/lead_stack_setup_2026-09-29_r1"
OUT="$DRIVE/runs/lead_stack_2026-09-29_r2"
ARCHIVE="$SETUP/code_snapshot.tar.gz"
test ! -e "$OUT"
test ! -e "$CODE_DIR"
echo "a2e407961e2aefacd634f17541440bfd1e7035a036658f63cb655a33a9926698  $ARCHIVE" | sha256sum -c -
mkdir -p "$CODE_DIR" "$OUT"
tar -xzf "$ARCHIVE" -C "$CODE_DIR"
cd "$CODE_DIR"
PILOT=reports/analisi/lead_scientist_2026-09-29/neural/stack_pilot.py
python -u "$PILOT" plan \
  --development-manifest "$DRIVE/runs/lead_generator_2026-09-29_r3/target_manifest.json" \
  --source-groups "$DRIVE/data/processed/k562_gwps_sc/x002/groups.csv" \
  --out "$OUT/plan.json"
python - "$OUT/plan.json" "$(dirname "$PILOT")/stack_plan_r1.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as f:
    actual = json.load(f)
with open(sys.argv[2], encoding="utf-8") as f:
    expected = json.load(f)
if actual != expected:
    raise SystemExit("Plan fields differ from frozen registration")
print("Plan semantic equality verified: every field and upstream hash unchanged.")
PY
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
