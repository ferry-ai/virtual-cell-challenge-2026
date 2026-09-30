"""Add only a serialization probe, pinned Python and Drive sync guard to repair1."""
from datetime import datetime, timezone
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
REL = 'reports/analisi/lead_scientist_2026-09-29/neural'
BASE_SHA = '1c8631e601cf86a13c92046ddca6f9815e5335cababb2b0fdb758b041d38d661'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unexpected original launcher: ' + old)
    return text.replace(old, new)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    base = (HERE / 'stack_confirmation_repair_r1/code_snapshot.tar.gz').read_bytes()
    if sha(base) != BASE_SHA:
        raise ValueError('Original repair archive changed')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(base), mode='r:gz') as archive:
        for item in archive.getmembers():
            if item.isfile():
                files[item.name] = archive.extractfile(item).read()
    for name in ['stack_pack_runtime.py', 'test_stack_pack_runtime.py']:
        files[REL + '/' + name] = (HERE / name).read_bytes()
    args.out.mkdir(parents=True)
    archive_path = args.out / 'code_snapshot.tar.gz'
    with tarfile.open(archive_path, 'w:gz') as archive:
        for name, content in sorted(files.items()):
            item = tarfile.TarInfo(name); item.size = len(content); item.mtime = 0; item.mode = 0o644
            archive.addfile(item, io.BytesIO(content))
    archive_hash = sha(archive_path.read_bytes())
    text = (HERE / 'stack_confirmation_repair_r1/080_lead_stack_confirmation_prepare_r2.sh').read_text()
    text = replace_once(text, 'lead_stack_confirmation_repair_2026-09-29_r1', 'lead_stack_confirmation_repair_2026-09-29_r2')
    text = replace_once(text, f'echo "{BASE_SHA}  $SETUP/code_snapshot.tar.gz" | sha256sum -c -',
        f'''PY=/content/lead_candidate_environment_r2/venv/bin/python
test -x "$PY"
ready=0
for attempt in $(seq 1 45); do
  if test -f "$SETUP/code_snapshot.tar.gz" && echo "{archive_hash}  $SETUP/code_snapshot.tar.gz" | sha256sum -c -; then
    ready=1
    break
  fi
  echo "Waiting for complete reviewed preparation archive ($attempt/45)"
  sleep 20
done
test "$ready" -eq 1''')
    text = text.replace('\npython ', '\n"$PY" ')
    text = replace_once(text, f'REPORT={REL}\n', f'''REPORT={REL}
"$PY" "$REPORT/stack_pack_runtime.py" preflight "$OUT/runtime_preflight"
"$PY" -m unittest discover -s "$REPORT" -p 'test_stack_pack_runtime.py' > "$OUT/runtime_contract_tests.log" 2>&1
''')
    text = text.replace('"$REPORT/stack_confirmation_pack.py"', '"$REPORT/stack_pack_runtime.py"')
    with (args.out / '080_lead_stack_confirmation_prepare_r2.sh').open('x', encoding='utf-8', newline='\n') as f:
        f.write(text)
    record = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'code_frozen_no_remote_copy_or_queue',
        'archive_sha256': archive_hash, 'base_archive_sha256': BASE_SHA,
        'all_base_files_byte_identical': True,
        'python': '/content/lead_candidate_environment_r2/venv/bin/python',
        'archive_sync_guard': '45 attempts at20s, exact SHA before extraction',
        'runtime_change': 'allow_write_nullable_strings=True; small exact roundtrip before source extraction',
        'scientific_change': 'none', 'ab_selection_required_before_inference_or_scoring': True,
        'files': {name: {'sha256': sha(content), 'bytes': len(content)} for name, content in sorted(files.items())}}
    with (args.out / 'manifest.json').open('x', encoding='utf-8') as f:
        json.dump(record, f, indent=2); f.write('\n')
    print(json.dumps({'out': str(args.out), 'archive_sha256': archive_hash, 'files': len(files)}))


if __name__ == '__main__':
    main()
