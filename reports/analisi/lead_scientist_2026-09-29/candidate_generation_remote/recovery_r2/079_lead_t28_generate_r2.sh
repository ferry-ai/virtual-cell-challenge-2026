#!/usr/bin/env bash
# Registered t28 generation and complete package verification. No submission.
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="$DRIVE/runs/lead_candidate_t28_setup_2026-09-29_r2"
ENVROOT=/content/lead_candidate_environment_r2
DRIVER="$DRIVE/runs/lead_candidate_t28_2026-09-29_r2_driver"
while ! test -f "$DRIVE/runs/queue/078_lead_candidate_environment_r3.sh.done"; do sleep 10; done
test -f "$ENVROOT/ready.json"
test ! -e "$DRIVER"
mkdir -p "$DRIVER"
trap 'rc=$?; printf "%s\n" "$rc" > "$DRIVER/returncode.txt"' EXIT
echo "83911b5851b702e3a50cfed6a19b232c58a3848de457279dddb0c8baef5544bf  $SETUP/generate_candidate_r2.py" | sha256sum -c -
"$ENVROOT/venv/bin/python" -u "$SETUP/generate_candidate_r2.py" \
  --manifest "$SETUP/input_manifest_r1.json" \
  --manifest-sha256 18dc29195d818cbfc8cb4a5442850e4e9581b60d8cba585afad65daf85a99bae \
  --confirmation "$SETUP/confirmation_selection.json" \
  --confirmation-sha256 35471a773ae2e51759d946682c3223b5a2a72f53eb03c83559c7a9e463f9c41c \
  --registration "$SETUP/prediction_t28.json" \
  --registration-sha256 a2081b9cd615a1020a962def21eafa54d7116db79285887f56c775033d61e192 \
  --run-id t28r2 --phi-scale 1 \
  --destination runs/lead_candidate_t28_2026-09-29_r2 --execute \
  > "$DRIVER/stdout.log" 2>&1
