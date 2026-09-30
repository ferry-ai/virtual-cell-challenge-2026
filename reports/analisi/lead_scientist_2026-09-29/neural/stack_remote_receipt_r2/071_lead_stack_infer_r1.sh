#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
SETUP="$DRIVE/runs/lead_stack_infer_setup_2026-09-29_r1"
test ! -e "$DRIVE/runs/lead_stack_infer_2026-09-29_r1"
test ! -e /content/lead_stack_scratch_r1
echo "a9acc828d79aae8c6edd638ab2cb6de6a91d35f1f0e597a371423f9008e5e26a  $SETUP/colab_stack_infer_r1.py" | sha256sum -c -
echo "c28b36005da43ac286c316edf733dabbcc7bcbbeb0aea779b77c26411e9f0d17  $SETUP/review_manifest.json" | sha256sum -c -
python -u "$SETUP/colab_stack_infer_r1.py"
