#!/usr/bin/env bash
# TEMPLATE ONLY. Fill hashes/paths after confirmation and preregistration; do not queue as-is.
set -euo pipefail
: "${LAUNCHER:?absolute path to the reviewed generate_candidate.py}"
: "${INPUT_MANIFEST:?absolute path to input_manifest_r1.json}"
: "${INPUT_MANIFEST_SHA256:?frozen full hash}"
: "${CONFIRMATION_SELECTION:?absolute path to completed confirmation/selection.json}"
: "${CONFIRMATION_SHA256:?frozen full hash}"
: "${PREDICTION_REGISTRATION:?absolute path to registered prediction.json}"
: "${REGISTRATION_SHA256:?frozen full hash}"
: "${TRIAL:?new trial ID selected by the lead}"
: "${PHI_SCALE:?0.5 or 1; must pass completed confirmation}"
: "${DESTINATION:?new relative Drive destination, e.g. runs/lead_candidate_tNN_r1}"
: "${EXECUTE_REVIEWED:?set to yes only after explicit approval of the concrete job}"
test "$EXECUTE_REVIEWED" = yes
python -u "$LAUNCHER" \
  --manifest "$INPUT_MANIFEST" --manifest-sha256 "$INPUT_MANIFEST_SHA256" \
  --confirmation "$CONFIRMATION_SELECTION" --confirmation-sha256 "$CONFIRMATION_SHA256" \
  --registration "$PREDICTION_REGISTRATION" --registration-sha256 "$REGISTRATION_SHA256" \
  --run-id "$TRIAL" --phi-scale "$PHI_SCALE" --destination "$DESTINATION" --execute
