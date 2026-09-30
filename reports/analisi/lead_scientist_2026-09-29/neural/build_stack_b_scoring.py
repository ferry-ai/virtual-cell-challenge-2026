"""Freeze B CPU scoring from immutable A scoring; no predictions/truth are read."""
from datetime import datetime, timezone
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
REL = 'reports/analisi/lead_scientist_2026-09-29/neural'
BASE_SHA = '9f89e6380704210adac7445199ca15117e85138193fd55c3cd6de8749a681f65'
ADDITIONS = {
    'stack_input_axis_pilot.py': 'a85b752dbd5042fde45611e80a6a942733bb19de6c4a00a03ab71db33a90d2a4',
    'score_stack_input_axis.py': '74607f249fc36642e74a374e45c32157391b875888efe715163642674045b28c',
    'PROTOCOLLO_STACK_AB.md': '181d7a00b1f5957948e2daf9fcd1f66fae9adb35dbf78aab59a5b2c006133506',
}


def sha(content):
    return hashlib.sha256(content).hexdigest()


def read_archive(content):
    with tarfile.open(fileobj=io.BytesIO(content), mode='r:gz') as archive:
        files = {}
        for entry in archive.getmembers():
            if not entry.isfile() or entry.name in files:
                raise ValueError('Unexpected archive member')
            files[entry.name] = archive.extractfile(entry).read()
    return files


def make_payload():
    original = (HERE / 'stack_scoring_setup_r3/scoring_snapshot.tar.gz').read_bytes()
    if sha(original) != BASE_SHA:
        raise ValueError('Frozen A scoring snapshot changed')
    base = read_archive(original)
    files = dict(base)
    for name, digest in ADDITIONS.items():
        key = REL + '/' + name
        content = (HERE / name).read_bytes()
        if sha(content) != digest or key in files:
            raise ValueError('Unexpected B addition: ' + name)
        files[key] = content
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode='w') as archive:
        for name, content in sorted(files.items()):
            entry = tarfile.TarInfo(name)
            entry.size, entry.mode, entry.mtime = len(content), 0o644, 0
            archive.addfile(entry, io.BytesIO(content))
    return gzip.compress(raw.getvalue(), mtime=0), base, files


def launcher(snapshot_sha):
    # Intentionally non-runnable until root binds an approved complete receipt.
    # All five placeholders must be resolved, not supplied by ambient env vars.
    return r'''#!/usr/bin/env bash
set -euo pipefail
INPUT_RECEIPT_BOUND=false
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
PREDICTION="__APPROVED_COMPLETE_B_PREDICTION_DIR__"
STACK_SHA="__PREDICTION_STACK_SHA256__"
TRANSFER_SHA="__PREDICTION_TRANSFER_SHA256__"
FINISHED_SHA="__FINISHED_JSON_SHA256__"
INFERENCE_SHA="__INFERENCE_MANIFEST_SHA256__"
OUT="$DRIVE/runs/lead_stack_score_b_2026-09-29_r1"
case "$PREDICTION" in /content/drive/MyDrive/vcc2026/runs/*) ;; *) echo 'Invalid/unbound prediction path' >&2; exit 64;; esac
for digest in "$STACK_SHA" "$TRANSFER_SHA" "$FINISHED_SHA" "$INFERENCE_SHA"; do
  [[ "$digest" =~ ^[0-9a-f]{64}$ ]] || { echo 'Invalid/unbound input SHA256' >&2; exit 64; }
done
test -x "$PY"
test ! -e "$OUT"
test ! -e "$CODE_DIR"
inputs_ready() {
  test -f "$PREDICTION/finished.json" || return 1
  test -f "$PREDICTION/inference_manifest.json" || return 1
  test -f "$PREDICTION/prediction_stack.h5ad" || return 1
  test -f "$PREDICTION/prediction_transfer.h5ad" || return 1
  test -f "$SETUP/scoring_snapshot.tar.gz" || return 1
  echo "$FINISHED_SHA  $PREDICTION/finished.json" | sha256sum -c - || return 1
  echo "$INFERENCE_SHA  $PREDICTION/inference_manifest.json" | sha256sum -c - || return 1
  echo "$STACK_SHA  $PREDICTION/prediction_stack.h5ad" | sha256sum -c - || return 1
  echo "$TRANSFER_SHA  $PREDICTION/prediction_transfer.h5ad" | sha256sum -c - || return 1
  echo "__SNAPSHOT_SHA__  $SETUP/scoring_snapshot.tar.gz" | sha256sum -c - || return 1
}
for attempt in $(seq 1 45); do
  if inputs_ready; then break; fi
  echo "Waiting for complete reviewed B inputs, attempt $attempt/45"
  sleep 20
done
inputs_ready
echo '16cf30126a7c46ec651c8ed8262b19353e1a3ab07c4dd445590a8a040e36fc29'"  $BUNDLE/bundle.json" | sha256sum -c -
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
'''.replace('__SNAPSHOT_SHA__', snapshot_sha)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    a = parser.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    payload, base, files = make_payload()
    script = launcher(sha(payload)).encode()
    a.out.mkdir(parents=True)
    for name, content in [('scoring_snapshot.tar.gz', payload), ('084_lead_stack_score_b_r1.sh.template', script)]:
        with (a.out / name).open('xb') as f:
            f.write(content)
    manifest = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'frozen_code_unbound_inputs_no_execution',
        'snapshot_sha256': sha(payload), 'snapshot_bytes': len(payload), 'base_snapshot_sha256': BASE_SHA,
        'all_base_files_byte_identical': True, 'base_file_count': len(base), 'total_file_count': len(files),
        'added_files': {REL + '/' + k: v for k, v in ADDITIONS.items()},
        'code_files': [{'path': k, 'bytes': len(v), 'sha256': sha(v)} for k, v in sorted(files.items())],
        'template_sha256': sha(script), 'builder_sha256': sha(Path(__file__).read_bytes()),
        'python': '/content/lead_candidate_environment_r2/venv/bin/python',
        'pending_before_execution': ['Approved complete B prediction directory',
            'SHA256 of both H5AD files, finished.json and inference_manifest.json',
            'New bound launcher and input receipt reviewed by lead'],
        'scope': 'CPU scoring only; same A truth/bundle/science; no remote copy, queue, model or outcome read'}
    with (a.out / 'scoring_manifest.json').open('x', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2); f.write('\n')
    print(json.dumps({k: manifest[k] for k in ['status', 'snapshot_sha256', 'base_file_count', 'total_file_count']}))


if __name__ == '__main__':
    main()
