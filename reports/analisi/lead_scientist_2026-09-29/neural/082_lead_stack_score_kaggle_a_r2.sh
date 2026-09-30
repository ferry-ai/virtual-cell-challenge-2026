#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export CODE_DIR=/content/lead_stack_score_kaggle_a_code_r2
export PYTHONPATH="$CODE_DIR/src"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
PY=/content/lead_candidate_environment_r2/venv/bin/python
SETUP="$DRIVE/runs/lead_stack_scoring_setup_2026-09-29_r1"
BUNDLE="$DRIVE/runs/lead_stack_2026-09-29_r2/bundle"
PREDICTION="$DRIVE/runs/lead_stack_kaggle_a_prediction_2026-09-29_r1"
OUT="$DRIVE/runs/lead_stack_score_kaggle_a_2026-09-29_r2"
test -x "$PY"
test ! -e "$OUT"
test ! -e "$CODE_DIR"
inputs_ready() {
  test -f "$PREDICTION/finished.json" || return 1
  test -f "$PREDICTION/inference_manifest.json" || return 1
  echo "4baa9e71184fcf365a13860843a5700fdcfed245f5e7d51a212b850d6c2d1255  $PREDICTION/prediction_stack.h5ad" | sha256sum -c - || return 1
  echo "0210a9ffb131ee9f0412b89b70ea4e6d9aa0ea7c39d63b2276ab86e7dbd55828  $PREDICTION/prediction_transfer.h5ad" | sha256sum -c - || return 1
  echo "9f89e6380704210adac7445199ca15117e85138193fd55c3cd6de8749a681f65  $SETUP/scoring_snapshot.tar.gz" | sha256sum -c - || return 1
}
for attempt in $(seq 1 45); do
  if inputs_ready; then break; fi
  echo "Waiting for complete Drive inputs, attempt $attempt/45"
  sleep 20
done
inputs_ready
mkdir -p "$CODE_DIR"
tar -xzf "$SETUP/scoring_snapshot.tar.gz" -C "$CODE_DIR"
cd "$CODE_DIR"
REPORT=reports/analisi/lead_scientist_2026-09-29/neural
"$PY" -u "$REPORT/test_stack_remote.py"
"$PY" -u "$REPORT/score_stack_pilot.py" \
  --bundle "$BUNDLE" --prediction "$PREDICTION" \
  --truth "$DRIVE/data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad" \
  --anchors reports/gara/anchors_2026-09-17/anchors.json --out "$OUT"
"$PY" -m pip freeze > "$OUT/scoring_pip_freeze.txt"
