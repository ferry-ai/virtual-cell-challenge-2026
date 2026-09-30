#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export CODE_DIR=/content/lead_stack_score_code_r1
export PYTHONPATH="$CODE_DIR/src"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
SETUP="$DRIVE/runs/lead_stack_scoring_setup_2026-09-29_r1"
BUNDLE="$DRIVE/runs/lead_stack_2026-09-29_r2/bundle"
PREDICTION="${STACK_PREDICTION_DIR:-$DRIVE/runs/lead_stack_infer_2026-09-29_r1/prediction}"
OUT="$DRIVE/runs/lead_stack_score_2026-09-29_r1"
test -f "$PREDICTION/finished.json"
test ! -e "$OUT"
test ! -e "$CODE_DIR"
echo "e53b55fdca21466c605e3d033c0ddb25276b07d27fc1de4971f3587f60d3c9a6  $SETUP/scoring_snapshot.tar.gz" | sha256sum -c -
mkdir -p "$CODE_DIR"
tar -xzf "$SETUP/scoring_snapshot.tar.gz" -C "$CODE_DIR"
cd "$CODE_DIR"
REPORT=reports/analisi/lead_scientist_2026-09-29/neural
python -u "$REPORT/test_stack_remote.py"
python -u "$REPORT/score_stack_pilot.py" \
  --bundle "$BUNDLE" --prediction "$PREDICTION" \
  --truth "$DRIVE/data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad" \
  --anchors reports/gara/anchors_2026-09-17/anchors.json --out "$OUT"
python -m pip freeze > "$OUT/scoring_pip_freeze.txt"
