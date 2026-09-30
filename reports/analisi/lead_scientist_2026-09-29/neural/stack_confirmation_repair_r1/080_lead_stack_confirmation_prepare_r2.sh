#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
export VCC2026_DATA_ROOT="$DRIVE/data"
SETUP="$DRIVE/runs/lead_stack_confirmation_repair_2026-09-29_r1"
OUT="$DRIVE/runs/lead_stack_confirmation_prompts_2026-09-29_r2"
CODE=/content/lead_stack_confirmation_pack_r2
test ! -e "$OUT"
test ! -e "$CODE"
echo "1c8631e601cf86a13c92046ddca6f9815e5335cababb2b0fdb758b041d38d661  $SETUP/code_snapshot.tar.gz" | sha256sum -c -
mkdir -p "$OUT" "$CODE"
tar -xzf "$SETUP/code_snapshot.tar.gz" -C "$CODE"
export PYTHONPATH="$CODE/src"
cd "$CODE"
REPORT=reports/analisi/lead_scientist_2026-09-29/neural
python -m unittest discover -s "$REPORT" -p 'test_stack_confirmation_effects.py' > "$OUT/effects_contract_tests.log" 2>&1
python -u "$REPORT/stack_confirmation_effects.py" \
  --effects "$DRIVE/data/processed/banco_hepg2_v2_2026-09-26/t19like.npz" \
  --bulk "$DRIVE/data/external/K562_gwps_raw_bulk_01.h5ad" \
  --generator-manifest "$DRIVE/runs/lead_generator_2026-09-29_r3/target_manifest.json" \
  --prepared-effects "$DRIVE/runs/lead_generator_2026-09-29_r3/prepared_effects.npz" \
  --pilot-bundle "$DRIVE/runs/lead_stack_2026-09-29_r2/bundle" --out "$OUT/effects"
ARGS=(--source "$DRIVE/data/raw/replogle/K562_gwps_raw_singlecell_01.h5ad"
  --pilot-bundle "$DRIVE/runs/lead_stack_2026-09-29_r2/bundle"
  --effects "$OUT/effects/confirmation_effects.npz")
python -u "$REPORT/stack_confirmation_pack.py" plan "${ARGS[@]}" \
  --source-groups "$DRIVE/data/processed/k562_gwps_sc/x002/groups.csv" \
  --generator-manifest "$DRIVE/runs/lead_generator_2026-09-29_r3/target_manifest.json" \
  --registration "$REPORT/expansion_metadata_r1.json" --out "$OUT/plan.json"
python -u "$REPORT/stack_confirmation_pack.py" prepare "${ARGS[@]}" --plan "$OUT/plan.json" --out "$OUT/bundle"
python -m pip freeze > "$OUT/preparation_pip_freeze.txt"
sha256sum "$OUT/plan.json" "$OUT/bundle/bundle.json" "$OUT/effects/manifest.json" > "$OUT/preparation_hashes.txt"
printf '%s\n' 'Prepared only. AB selection required before any confirmation inference or scoring.'
