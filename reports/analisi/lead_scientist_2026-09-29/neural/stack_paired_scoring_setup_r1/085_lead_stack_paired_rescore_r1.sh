#!/usr/bin/env bash
set -euo pipefail
export PYTHONHASHSEED=0 POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 NUMBA_NUM_THREADS=1
export PYTHONUNBUFFERED=1
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="$DRIVE/runs/lead_stack_paired_scoring_setup_2026-09-29_r1"
CODE_DIR=/content/lead_stack_paired_score_code_r1
OUT="$DRIVE/runs/lead_stack_paired_score_2026-09-29_r1"
PY=/content/lead_candidate_environment_r2/venv/bin/python
test -x "$PY"
test ! -e "$OUT"
test ! -e "$CODE_DIR"
bootstrap_ready() {
  echo "1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  $SETUP/preflight.py" | sha256sum -c - || return 1
  echo "dbc16fa15b37fb8601b0a4c63c12df50bf6b2ed1f426e321d02091ae5289f32b  $SETUP/job_contract.json" | sha256sum -c - || return 1
}
for attempt in $(seq 1 45); do
  if bootstrap_ready; then break; fi
  echo "Waiting for reviewed preflight contract, attempt $attempt/45"
  sleep 20
done
bootstrap_ready
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/job_contract.json" --site runtime --receipt "$SETUP/preflight_runtime_receipt.json" --attempts 45 --interval-seconds 20
export CONTRACT="$SETUP/job_contract.json"
"$PY" - <<'PYENV'
import importlib.metadata as metadata,json,os
from pathlib import Path
contract=json.loads(Path(os.environ['CONTRACT']).read_text())
for key,value in contract['runtime_environment_variables'].items():
    assert os.environ.get(key)==value,(key,os.environ.get(key),value)
for package,version in contract['required_runtime_versions'].items():
    assert metadata.version(package)==version,(package,metadata.version(package),version)
print('Frozen scientific versions and deterministic thread variables verified',flush=True)
PYENV
mkdir "$CODE_DIR"
tar -xzf "$SETUP/scoring_snapshot.tar.gz" -C "$CODE_DIR"
export PYTHONPATH="$CODE_DIR/src"
cd "$CODE_DIR"
REPORT=reports/analisi/lead_scientist_2026-09-29/neural
BUNDLE="$DRIVE/runs/lead_stack_2026-09-29_r2/bundle"
"$PY" -u "$REPORT/test_stack_remote.py"
"$PY" -u "$REPORT/score_stack_pilot.py" --bundle "$BUNDLE" --prediction "$DRIVE/runs/lead_stack_kaggle_a_prediction_2026-09-29_r1" --truth "$DRIVE/data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad" --anchors reports/gara/anchors_2026-09-17/anchors.json --out "$OUT/A"
"$PY" -m pip freeze > "$OUT/A/scoring_pip_freeze.txt"
"$PY" -u "$REPORT/score_stack_input_axis.py" --bundle "$BUNDLE" --prediction "$DRIVE/runs/lead_stack_kaggle_b_prediction_2026-09-29_r1" --truth "$DRIVE/data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad" --anchors reports/gara/anchors_2026-09-17/anchors.json --out "$OUT/B"
"$PY" -m pip freeze > "$OUT/B/scoring_pip_freeze.txt"
export PAIRED_OUT="$OUT"
"$PY" - <<'PYDONE'
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
out=Path(os.environ['PAIRED_OUT'])
reports={arm:hashlib.sha256((out/arm/'pilot_comparison.json').read_bytes()).hexdigest() for arm in ['A','B']}
with (out/'complete.json').open('x') as stream:
    json.dump({'status':'both_scores_complete','utc':datetime.now(timezone.utc).isoformat(),'comparisons':reports,'scope':'Same predictions; deterministic numerical rescore; selection remains separate'},stream,indent=2)
print('Both numerical rescoring runs complete',flush=True)
PYDONE
