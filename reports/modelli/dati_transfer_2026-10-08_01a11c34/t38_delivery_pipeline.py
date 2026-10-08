"""Wait for this exact authorized generation, verify it, and deliver one upload."""
import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from percorso import DATA, HERE, read, write_new, now
from quick_generation_cloud import api_for_owner
from collect_t38_generation import main as collect
from t38_submission import submit


def main(attempt, completion, generation_folder):
    if os.name != 'nt':
        raise ValueError('persistent Windows process required')
    folder = DATA / 'processed/dati_transfer_2026-10-08_01a11c34/submission_t38' / ('pipeline_' + attempt)
    folder.mkdir(parents=True, exist_ok=False)
    generation = HERE / generation_folder
    if not generation.resolve().is_relative_to(HERE):raise ValueError('folder outside owned scope')
    proof = read(generation / 'prepared.json')
    write_new(folder / 'started.json', dict(utc=now(), pid=os.getpid(), job=proof['slug'],
        attempt=attempt, completion=completion, deadline='2026-10-09T02:00:00+02:00'))
    def state(stage, **fields):
        (folder / 'state.json').write_text(json.dumps(dict(utc=now(), stage=stage, **fields), indent=2), encoding='utf-8')
    if not ctypes.windll.kernel32.SetThreadExecutionState(0x80000001):
        raise ValueError('sleep inhibition failed')
    try:
        api = api_for_owner(proof['owner'])
        consecutive_errors = 0
        while True:
            if datetime.now(timezone.utc) >= datetime(2026, 10, 9, tzinfo=timezone.utc):
                state('deadline_reached_before_generation_complete', new_upload_started=False)
                return 1
            try:
                status = str(api.kernels_status(proof['slug']).status).rsplit('.', 1)[-1].upper()
                consecutive_errors = 0
            except Exception as exc:
                consecutive_errors += 1
                state('status_connection_error', error_type=type(exc).__name__, consecutive_errors=consecutive_errors)
                if consecutive_errors >= 4:
                    return 1
                time.sleep(45)
                continue
            state('awaiting_generation', provider_status=status)
            if status == 'COMPLETE':
                break
            if status in ('ERROR', 'CANCELLED', 'FAILED'):
                state('generation_failed', provider_status=status, new_upload_started=False)
                return 1
            time.sleep(45)
        state('collecting_receipts')
        if collect(completion,generation) != 0:
            raise ValueError('receipt collection did not pass')
        state('delivery_started', delivery_state=str(folder.parent / attempt / 'state.json'))
        result = submit(generation / completion, attempt,generation/'prepared.json')
        state('delivery_returned', returncode=result)
        return result
    except BaseException as exc:
        state('error', error_type=type(exc).__name__, no_automatic_new_entry_retry=True)
        return 1
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--completion', required=True)
    parser.add_argument('--generation-folder', default='generation_recovery/r1')
    args = parser.parse_args()
    raise SystemExit(main(args.attempt, args.completion,args.generation_folder))
