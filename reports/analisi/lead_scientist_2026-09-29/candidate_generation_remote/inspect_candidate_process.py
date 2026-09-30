"""Bounded read-only Colab process diagnostics for the registered t28 job only.

No environment variables, file contents of input data, credentials or unrelated
process command lines are read. Output is a new small JSON in the run directory.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil

ROOT_PID = 29730
OUTPUT = Path('/content/drive/MyDrive/vcc2026/runs/lead_candidate_t28_diagnostic_2026-09-29_r1.json')
SCRATCH = Path('/content/lead_candidate_t28')
DRIVER = Path('/content/drive/MyDrive/vcc2026/runs/lead_candidate_t28_2026-09-29_r1_driver')


def status(pid):
    lines = (Path('/proc') / str(pid) / 'status').read_text().splitlines()
    keys = {'Name', 'State', 'PPid', 'VmRSS', 'VmSize', 'Threads'}
    return {key: value.strip() for key, value in (line.split(':', 1) for line in lines) if key in keys}


def main():
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    tree = {}
    for item in Path('/proc').iterdir():
        if not item.name.isdigit():
            continue
        try:
            tree[int(item.name)] = status(item.name)
        except (OSError, ValueError):
            pass
    chosen = {ROOT_PID}
    for _ in range(12):
        previous = set(chosen)
        chosen |= {pid for pid, record in tree.items() if int(record['PPid']) in chosen}
        if chosen == previous:
            break
    result = {'utc': datetime.now(timezone.utc).isoformat(), 'root_pid': ROOT_PID,
              'processes': {}, 'files': [], 'log_tails': {},
              'disk_free_bytes': shutil.disk_usage('/content').free}
    result['memory'] = {line.split(':')[0]: line.split(':')[1].strip()
                        for line in Path('/proc/meminfo').read_text().splitlines()
                        if line.startswith(('MemAvailable:', 'MemTotal:'))}
    for pid in sorted(chosen):
        if pid not in tree:
            continue
        base = Path('/proc') / str(pid)
        record = dict(tree[pid])
        for name in ('io', 'wchan'):
            try:
                record[name] = (base / name).read_text()[:2000]
            except OSError as error:
                record[name] = type(error).__name__
        try:
            record['open_paths'] = [os.readlink(p) for p in sorted((base / 'fd').iterdir())[:30]]
        except OSError as error:
            record['open_paths'] = type(error).__name__
        result['processes'][str(pid)] = record
    if SCRATCH.exists():
        for path in sorted(SCRATCH.rglob('*')):
            if path.is_file() and len(result['files']) < 120:
                result['files'].append({'path': str(path.relative_to(SCRATCH)), 'bytes': path.stat().st_size})
    for path in [DRIVER / 'stdout.log', SCRATCH / 'stage45.log', SCRATCH / 'stage48.log']:
        if path.is_file():
            with path.open('rb') as stream:
                stream.seek(max(0, path.stat().st_size - 6000))
                result['log_tails'][str(path)] = stream.read().decode('utf-8', errors='replace')
    with OUTPUT.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
