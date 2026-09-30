#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
SETUP="$DRIVE/runs/lead_stack_infer_setup_2026-09-29_r2"
test ! -e "$DRIVE/runs/lead_stack_infer_2026-09-29_r2"
test -x /content/lead_stack_scratch_r1/venv/bin/python
echo "ccbf39e6339389a6aae53aa005b0a62f2fc4605abde504cfdfb1ab5a5c983ce3  $SETUP/colab_stack_infer_r2.py" | sha256sum -c -
python -u "$SETUP/colab_stack_infer_r2.py"
