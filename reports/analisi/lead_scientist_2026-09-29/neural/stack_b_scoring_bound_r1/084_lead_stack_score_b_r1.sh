#!/usr/bin/env bash
set -euo pipefail
INPUT_RECEIPT_BOUND=true
if test "$INPUT_RECEIPT_BOUND" != true; then
  echo 'UNBOUND TEMPLATE: require approved complete B input paths/hashes before queueing.' >&2
  exit 64
fi
export DRIVE=/content/drive/MyDrive/vcc2026
export CODE_DIR=/content/lead_stack_score_b_code_r1
export PYTHONPATH="$CODE_DIR/src"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
PY=/content/lead_candidate_environment_r2/venv/bin/python
SETUP="$DRIVE/runs/lead_stack_scoring_b_setup_2026-09-29_r1"
BUNDLE="$DRIVE/runs/lead_stack_2026-09-29_r2/bundle"
PREDICTION="/content/drive/MyDrive/vcc2026/runs/lead_stack_kaggle_b_prediction_2026-09-29_r1"
STACK_SHA="7dc7cf11c36ad97ff13f20be9e5dc4c70085fa024c8b0f8d87cf0eeb8ae3c790"
TRANSFER_SHA="0210a9ffb131ee9f0412b89b70ea4e6d9aa0ea7c39d63b2276ab86e7dbd55828"
FINISHED_SHA="e418cf42523d055080d5c910019f365fa522d53e05d10447cd114bd981d88cbf"
INFERENCE_SHA="27a783d617e8bfcc07a9c6c9572a0745343ee44211c6b9463a2635611d00512d"
OUT="$DRIVE/runs/lead_stack_score_b_2026-09-29_r1"
case "$PREDICTION" in /content/drive/MyDrive/vcc2026/runs/*) ;; *) echo 'Invalid/unbound prediction path' >&2; exit 64;; esac
for digest in "$STACK_SHA" "$TRANSFER_SHA" "$FINISHED_SHA" "$INFERENCE_SHA"; do
  [[ "$digest" =~ ^[0-9a-f]{64}$ ]] || { echo 'Invalid/unbound input SHA256' >&2; exit 64; }
done
test -x "$PY"
test ! -e "$OUT"
test ! -e "$CODE_DIR"
inputs_ready() {
  echo "1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  $SETUP/preflight.py" | sha256sum -c - || return 1
  echo "00ed6f7e57fc4644e62871d3f7a90e2ef2c700a2430c0c929159534251a0a1dc  $SETUP/job_contract.json" | sha256sum -c - || return 1
  test -f "$PREDICTION/finished.json" || return 1
  test -f "$PREDICTION/inference_manifest.json" || return 1
  test -f "$PREDICTION/prediction_stack.h5ad" || return 1
  test -f "$PREDICTION/prediction_transfer.h5ad" || return 1
  test -f "$SETUP/scoring_snapshot.tar.gz" || return 1
  echo "$FINISHED_SHA  $PREDICTION/finished.json" | sha256sum -c - || return 1
  echo "$INFERENCE_SHA  $PREDICTION/inference_manifest.json" | sha256sum -c - || return 1
  echo "$STACK_SHA  $PREDICTION/prediction_stack.h5ad" | sha256sum -c - || return 1
  echo "$TRANSFER_SHA  $PREDICTION/prediction_transfer.h5ad" | sha256sum -c - || return 1
  echo "6e216f900a606656c182bb7f520e351bb7805358a0e2943a226ce3a105071dcb  $SETUP/scoring_snapshot.tar.gz" | sha256sum -c - || return 1
}
for attempt in $(seq 1 45); do
  if inputs_ready; then break; fi
  echo "Waiting for complete reviewed B inputs, attempt $attempt/45"
  sleep 20
done
inputs_ready
echo '16cf30126a7c46ec651c8ed8262b19353e1a3ab07c4dd445590a8a040e36fc29'"  $BUNDLE/bundle.json" | sha256sum -c -
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/job_contract.json" --site runtime --receipt "$SETUP/preflight_runtime_receipt.json" --attempts 45 --interval-seconds 20
mkdir -p "$CODE_DIR"
tar -xzf "$SETUP/scoring_snapshot.tar.gz" -C "$CODE_DIR"
cd "$CODE_DIR"
REPORT=reports/analisi/lead_scientist_2026-09-29/neural
"$PY" -u "$REPORT/test_stack_remote.py"
"$PY" -u "$REPORT/score_stack_input_axis.py" \
  --bundle "$BUNDLE" --prediction "$PREDICTION" \
  --truth "$DRIVE/data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad" \
  --anchors reports/gara/anchors_2026-09-17/anchors.json --out "$OUT"
"$PY" -m pip freeze > "$OUT/scoring_pip_freeze.txt"
