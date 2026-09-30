"""Record the actual safe disk-guard stop; never resume or close the incident."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import ledger

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
TRIAL = REPO / 'reports/invii/trial_2026-09-29'
DESTINATION = Path('C:/Users/ferra/vcc2026-data/artifacts/t28_local_upload_r1')


def evidence(path, supports):
    try:
        name = path.relative_to(REPO).as_posix()
    except ValueError:
        name = path.as_posix()
    return {'path': name, 'sha256': ledger.sha(path), 'bytes': path.stat().st_size,
            'supports': supports}


def main():
    stdout = TRIAL / 't28_local_copy_r1.stdout.log'
    stderr = TRIAL / 't28_local_copy_r1.stderr.log'
    started = TRIAL / 't28_local_copy_r1.started.json'
    copy_state = DESTINATION / 'copy_state.json'
    rows = [json.loads(line) for line in stdout.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    last = rows[-1]
    assert last['phase'] == 'copied_window'
    assert last['bytes'] == 3019898880 and last['free_bytes'] == 591491072
    error = stderr.read_text(encoding='utf-8-sig')
    assert 'Insufficient free disk: 591491072 bytes; need 603979776' in error
    assert 'read_window' in error and 'disk_guard(volume, reserve+size)' in error
    state = json.loads(copy_state.read_text(encoding='utf-8-sig'))
    partial = DESTINATION / 'prediction.vcc.partial'
    assert partial.stat().st_size == last['bytes']
    assert not (DESTINATION / 'copy.lock').exists()
    assert not (DESTINATION / 'prediction.vcc').exists()
    assert not (DESTINATION / 'local_copy_complete.json').exists()
    now = datetime.now(timezone.utc).isoformat()
    proof = {
        'eid': 'E-20260929-007', 'event': 'copy_stopped_by_disk_guard',
        'claim_type': 'measured_local_observation', 'recorded_utc': now,
        'last_completed_window_utc': last['utc'], 'partial_bytes': partial.stat().st_size,
        'expected_bytes': state['expected_bytes'],
        'remaining_bytes': state['expected_bytes'] - partial.stat().st_size,
        'free_bytes_at_guard_failure': 591491072, 'required_bytes_for_next_window': 603979776,
        'free_bytes_at_observation': shutil.disk_usage(DESTINATION.anchor).free,
        'copy_lock_exists': False, 'final_file_exists': False, 'copy_complete_receipt_exists': False,
        'copier_sha256': state['copier_sha256'],
        'partial_content_hashed_by_this_observation': False,
        'partial_preservation_claim': 'Existence and byte length observed; complete integrity will require final full SHA.',
        'cause_scope': 'The immediate stop is the explicit disk guard before opening the next source window. This does not establish the cause of the earlier OSError 22.',
        'action_taken': 'Read and record only; no resume, source change, deletion, hash of the large partial or CLI invocation.',
        'incident_closed': False,
        'evidence': [
            evidence(stdout, 'Original copied-window records and free-space observations'),
            evidence(stderr, 'Original disk-guard traceback before next source read'),
            evidence(started, 'Original worker-start receipt'),
            evidence(copy_state, 'Frozen source, expected full SHA/size and resume contract'),
        ],
    }
    path = HERE / 'upload_copy_disk_stop_r1.json'
    with path.open('x', encoding='utf-8') as stream:
        json.dump(proof, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'receipt': str(path), 'sha256': ledger.sha(path), 'incident_closed': False}))


if __name__ == '__main__':
    main()
