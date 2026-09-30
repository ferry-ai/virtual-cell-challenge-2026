"""Prepare085 paired deterministic rescoring; never copy to Drive or queue.

All scientific code/data stay byte-identical. The new runtime contract records
thread settings and independently checks the exact prior scientific versions.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SETUP_NAME = 'lead_stack_paired_scoring_setup_2026-09-29_r1'
RESULT_NAME = 'lead_stack_paired_score_2026-09-29_r1'
LOCAL_RUNS = Path('G:/Il mio Drive/vcc2026/runs')
RUNTIME_RUNS = '/content/drive/MyDrive/vcc2026/runs'
OUT = HERE / 'stack_paired_scoring_setup_r1'
SNAPSHOT_SHA = '6e216f900a606656c182bb7f520e351bb7805358a0e2943a226ce3a105071dcb'
PREFLIGHT_SHA = '1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744'
THREADS = {'PYTHONHASHSEED': '0', **{k: '1' for k in ['POLARS_MAX_THREADS', 'OMP_NUM_THREADS',
    'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'NUMBA_NUM_THREADS']}}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    archive = HERE / 'stack_b_scoring_setup_r1' / 'scoring_snapshot.tar.gz'
    guard = HERE.parent / 'learning' / 'preflight.py'
    amendment = HERE / 'EMENDAMENTO_NUMERICO_STACK_AB_01.md'
    assert sha(archive) == SNAPSHOT_SHA and sha(guard) == PREFLIGHT_SHA
    with tarfile.open(archive) as tar:
        for name, expected in [('score_stack_pilot.py', '2d4dc6503c5ac58c6ca8ad2f3002b5d37c6293818a2179559c3fa68a0537ff37'),
                               ('score_stack_input_axis.py', '74607f249fc36642e74a374e45c32157391b875888efe715163642674045b28c')]:
            member = next(m for m in tar.getmembers() if m.name.endswith('/' + name))
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == expected
    original = json.loads((HERE / 'stack_b_scoring_bound_r1' / 'job_contract.json').read_text())
    contract = deepcopy(original)
    contract['job_id'] = '085_stack_ab_paired_deterministic_rescore_r1'
    contract['incident_ids'] = ['E-20260929-005', 'E-20260929-006']
    contract['runtime_environment_variables'] = THREADS
    runtime_versions = json.loads((HERE / 'stack_b_scoring_runtime_r1' / 'preflight_runtime_receipt.json').read_text())['environment']['packages']
    freeze = dict(line.split('==', 1) for line in (HERE / 'stack_b_scoring_r1' / 'scoring_pip_freeze.txt').read_text().splitlines() if '==' in line)
    runtime_versions |= {key: freeze[key] for key in ['polars', 'numba', 'numexpr']}
    contract['required_runtime_versions'] = runtime_versions
    contract['inputs'] = []
    for variant in ('A', 'B'):
        prediction_dir = LOCAL_RUNS / f'lead_stack_kaggle_{variant.lower()}_prediction_2026-09-29_r1'
        old_manifest = json.loads((HERE / ('stack_a_scoring_r2' if variant == 'A' else 'stack_b_scoring_r1') / 'evaluation_manifest.json').read_text())
        for name in ('prediction_stack.h5ad', 'prediction_transfer.h5ad', 'finished.json', 'inference_manifest.json'):
            path = prediction_dir / name
            digest = sha(path)
            if name.startswith('prediction_'):
                assert digest == old_manifest['prediction_hashes'][name.removeprefix('prediction_').removesuffix('.h5ad')]
            contract['inputs'].append({'id': variant + '_' + name,
                'paths': {'local': str(path), 'runtime': RUNTIME_RUNS + '/' + prediction_dir.name + '/' + name},
                'bytes': path.stat().st_size, 'sha256': digest})
    for item in original['inputs'][4:]:
        item = deepcopy(item)
        if item['id'] in ('scoring_snapshot', 'preflight_code'):
            name = 'scoring_snapshot.tar.gz' if item['id'] == 'scoring_snapshot' else 'preflight.py'
            item['paths'] = {'local': str(LOCAL_RUNS / SETUP_NAME / name), 'runtime': RUNTIME_RUNS + '/' + SETUP_NAME + '/' + name}
        contract['inputs'].append(item)
    contract['inputs'].append({'id': 'numerical_amendment', 'paths': {
        'local': str(LOCAL_RUNS / SETUP_NAME / amendment.name), 'runtime': RUNTIME_RUNS + '/' + SETUP_NAME + '/' + amendment.name},
        'bytes': amendment.stat().st_size, 'sha256': sha(amendment)})
    contract['outputs'] = [{'id': variant, 'paths': {'local': str(LOCAL_RUNS / RESULT_NAME / variant),
        'runtime': RUNTIME_RUNS + '/' + RESULT_NAME + '/' + variant}, 'must_be_absent': True} for variant in ('A', 'B')]
    OUT.mkdir()
    for path in (archive, guard, amendment):
        shutil.copyfile(path, OUT / path.name)
        assert sha(path) == sha(OUT / path.name)
    write_json(OUT / 'job_contract.json', contract)
    contract_sha = sha(OUT / 'job_contract.json')
    body = f'''#!/usr/bin/env bash
set -euo pipefail
export {' '.join(k+'='+v for k,v in THREADS.items())}
export PYTHONUNBUFFERED=1
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="$DRIVE/runs/{SETUP_NAME}"
CODE_DIR=/content/lead_stack_paired_score_code_r1
OUT="$DRIVE/runs/{RESULT_NAME}"
PY=/content/lead_candidate_environment_r2/venv/bin/python
test -x "$PY"
test ! -e "$OUT"
test ! -e "$CODE_DIR"
bootstrap_ready() {{
  echo "{PREFLIGHT_SHA}  $SETUP/preflight.py" | sha256sum -c - || return 1
  echo "{contract_sha}  $SETUP/job_contract.json" | sha256sum -c - || return 1
}}
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
reports={{arm:hashlib.sha256((out/arm/'pilot_comparison.json').read_bytes()).hexdigest() for arm in ['A','B']}}
with (out/'complete.json').open('x') as stream:
    json.dump({{'status':'both_scores_complete','utc':datetime.now(timezone.utc).isoformat(),'comparisons':reports,'scope':'Same predictions; deterministic numerical rescore; selection remains separate'}},stream,indent=2)
print('Both numerical rescoring runs complete',flush=True)
PYDONE
'''
    launcher = OUT / '085_lead_stack_paired_rescore_r1.sh'
    with launcher.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(body)
    transfers = [{'source': str(OUT / name), 'destination': str(LOCAL_RUNS / SETUP_NAME / name),
                  'bytes': (OUT / name).stat().st_size, 'sha256': sha(OUT / name)}
                 for name in ['scoring_snapshot.tar.gz', 'preflight.py', amendment.name, 'job_contract.json']]
    write_json(OUT / 'publish_plan.json', {'transfers': transfers, 'launcher': str(launcher),
        'launcher_sha256': sha(launcher), 'queue': str(LOCAL_RUNS / 'queue' / launcher.name),
        'local_preflight_required_before_queue': True, 'runtime_preflight_required_before_scoring': True,
        'authorization': 'Parent approved preparation of mechanical085; publication follows review using existing user authorization'})
    publisher = (HERE / 'publish_stack_b_scoring.ps1').read_text().replace("'084 queued", "'085 queued")
    with (OUT / 'publish.ps1').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(publisher)
    write_json(OUT / 'review.json', {'status': 'prepared_not_published_not_queued', 'snapshot_sha256': SNAPSHOT_SHA,
        'manifest_sha256': contract_sha, 'amendment_sha256': sha(amendment), 'launcher_sha256': sha(launcher),
        'input_count': len(contract['inputs']), 'runtime_versions': runtime_versions, 'thread_settings': THREADS,
        'changes': 'Thread settings and newoutput paths only; scientific code and data unchanged'})
    print((OUT / 'review.json').read_text())


if __name__ == '__main__':
    main()
