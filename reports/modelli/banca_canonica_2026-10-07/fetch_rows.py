"""Fetch only the small rows.csv of every pinned bank unit and verify it against the bank receipt.

No matrix is downloaded. A unit whose rows cannot be verified stays named in the output, it is
not dropped. Usage: fetch_rows.py <new_out_dir>
"""
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REUSE = REPO / 'reports/modelli/percorso_riusabile_2026-10-05'
EXPECTED = REPO / 'reports/analisi/riconciliazione_banca_2026-10-05/frozen/expected_r3.json'
EXPECTED_SHA = '304e8a660d7f69952c62c2e6ccf3a990da48647a186e179db4584941b4b21a30'
sys.path.insert(0, str(REUSE))
from preflight_slots_fast_v1 import call  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def banks(expected):
    """(unit, part, kernel, relative_path, rows pin) for every bank in the frozen coverage."""
    out = []
    for unit, record in expected['expected_storage_units'].items():
        if 'bank' in record:
            parts = [(None, record['bank'])]
        else:
            parts = [(name, part['bank']) for name, part in sorted(record['verified_parts'].items())]
        for part, bank in parts:
            out.append(dict(unit=unit, part=part, kernel=bank['kernel'],
                            relative_path=bank.get('relative_path') or 'bank/' + unit,
                            pin=(bank.get('files') or {}).get('rows.csv')))
    return out


def fetch(job):
    kernel, target = job
    owner = kernel.split('/')[0]
    target.mkdir(parents=True, exist_ok=True)
    try:
        rc, answer = call(owner, ['kernels', 'output', kernel, '-p', str(target), '--file-pattern', r'rows\.csv$'])
    except Exception as error:  # timeouts stay recorded, never silently skipped
        rc, answer = None, repr(error)
    return kernel, dict(returncode=rc, answer=answer[-600:])


def main():
    out = HERE / sys.argv[1]
    out.mkdir(exist_ok=False)
    assert sha(EXPECTED) == EXPECTED_SHA, 'frozen coverage changed'
    units = banks(json.loads(EXPECTED.read_text(encoding='utf-8')))
    kernels = sorted({u['kernel'] for u in units})
    jobs = [(k, out / k.replace('/', '__')) for k in kernels]
    with ThreadPoolExecutor(3) as pool:
        answers = dict(pool.map(fetch, jobs))
    records = []
    for u in units:
        path = out / u['kernel'].replace('/', '__') / u['relative_path'] / 'rows.csv'
        record = dict(u, path=path.relative_to(HERE).as_posix(), present=path.exists())
        if path.exists():
            record.update(bytes=path.stat().st_size, sha256=sha(path))
            record['verified'] = bool(u['pin']) and u['pin']['sha256'] == record['sha256']
            record['pin_available'] = bool(u['pin'])
        records.append(record)
    state = dict(utc=datetime.now(timezone.utc).isoformat(), expected_sha256=EXPECTED_SHA,
                 kernels=answers, units=records,
                 scope='rows.csv metadata only; matrices stay in the cloud and are hashed by the consumer')
    (out / 'state.json').write_text(json.dumps(state, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(dict(units=len(records), present=sum(r['present'] for r in records),
                          verified=sum(bool(r.get('verified')) for r in records),
                          failed_kernels=[k for k, a in answers.items() if a['returncode']])))


if __name__ == '__main__':
    main()
