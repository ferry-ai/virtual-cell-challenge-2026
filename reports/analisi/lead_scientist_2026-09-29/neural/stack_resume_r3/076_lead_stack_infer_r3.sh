#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
SETUP="$DRIVE/runs/lead_stack_infer_setup_2026-09-29_r3"
test ! -e "$DRIVE/runs/lead_stack_infer_2026-09-29_r3"
test -x /content/lead_stack_scratch_r1/venv/bin/python
echo "d231307b93177f9c5c2a261381c9d069b59330ae1f96c1b3a66ffe3d366a8aeb  $SETUP/colab_stack_infer_r3.py" | sha256sum -c -
python -u "$SETUP/colab_stack_infer_r3.py"
