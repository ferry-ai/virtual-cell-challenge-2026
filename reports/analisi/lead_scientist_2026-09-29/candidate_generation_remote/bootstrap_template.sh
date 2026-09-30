#!/usr/bin/env bash
# REVIEW TEMPLATE: prepares only a venv. Never generates or submits a prediction.
set -euo pipefail
: "${BOOTSTRAP:?path to reviewed bootstrap_candidate_env.py}"
: "${ENVROOT:?new directory under /content, e.g. /content/lead_candidate_env_tNN_r1}"
: "${BOOTSTRAP_APPROVED:?set to yes only after explicit review}"
test "$BOOTSTRAP_APPROVED" = yes
DRIVE=/content/drive/MyDrive/vcc2026
python -u "$BOOTSTRAP" --phase create --out "$ENVROOT" \
  --expected-environment "$DRIVE/runs/lead_generator_2026-09-29_r3/development_environment.json" \
  --code-archive "$DRIVE/runs/lead_generator_setup_2026-09-29_r3/code_snapshot.tar.gz"
test -f "$ENVROOT/ready.json"
echo "Prepared interpreter for BOTH stage45 and stage48: $ENVROOT/venv/bin/python"
echo "Generation remains separate, conditional on confirmed selection and registered prediction."
