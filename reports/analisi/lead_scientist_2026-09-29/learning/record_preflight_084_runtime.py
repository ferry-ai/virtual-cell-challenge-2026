"""Collect a complete runtime084 preflight receipt, verify it, and append proof.

No scientific outcomes or counts are read. This verifies preflight only, not
scoring completion or model utility. It never queues or starts a remote job.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import ledger

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
NEURAL = HERE.parent / 'neural'
REMOTE = Path('G:/Il mio Drive/vcc2026/runs/lead_stack_scoring_b_setup_2026-09-29_r1/preflight_runtime_receipt.json')
OUT = NEURAL / 'stack_b_scoring_runtime_r1'
VALIDATOR_SHA = '1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744'


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    if REMOTE.stat().st_size > 100000:
        raise ValueError('Unexpected receipt size')
    raw = REMOTE.read_bytes()
    receipt = json.loads(raw)
    contract_path = NEURAL / 'stack_b_scoring_bound_r1' / 'job_contract.json'
    contract = json.loads(contract_path.read_text())
    assert receipt['status'] == 'PASS' and receipt['site'] == 'runtime'
    assert receipt['job_id'] == contract['job_id'] == '084_stack_b_development_scoring_r1'
    assert receipt['manifest_sha256'] == ledger.sha(contract_path)
    assert receipt['validator_sha256'] == ledger.sha(HERE / 'preflight.py') == VALIDATOR_SHA
    actual = {r['id']: r for r in receipt['inputs']}
    expected = {r['id']: r for r in contract['inputs']}
    assert len(actual) == len(expected) == len(receipt['inputs']) == 10 and actual.keys() == expected.keys()
    for key, item in expected.items():
        assert actual[key]['path'] == item['paths']['runtime']
        assert actual[key]['bytes'] == item['bytes'] and actual[key]['sha256'] == item['sha256']
    assert receipt['new_outputs'] == [r['paths']['runtime'] for r in contract['outputs']]
    assert receipt['target_checks'] == [{'input_id': 'transfer.npz', 'npz_key': 'targets',
                                       'required_count': 12, 'available_count': 12}]
    env = receipt['environment']
    assert env['executable'] == contract['environment']['python']['paths']['runtime']
    assert set(env['imports_passed']) == set(contract['environment']['imports'])
    assert env['probes_passed'] == ['h5ad_nullable_roundtrip']
    assert 'This process only' in env['configuration_scope']
    assert raw == REMOTE.read_bytes()
    OUT.mkdir()
    copied = OUT / REMOTE.name
    with copied.open('xb') as stream:
        stream.write(raw)
    digest = hashlib.sha256(raw).hexdigest()
    assert ledger.sha(copied) == digest
    evidence = {'path': copied.relative_to(REPO).as_posix(), 'sha256': digest,
                'bytes': len(raw), 'supports': 'Preflight084 PASS nel runtime; non prova scoring completo'}
    verification = {'observed_utc': datetime.now(timezone.utc).isoformat(),
                    'source': str(REMOTE), 'file': copied.name, 'sha256': digest,
                    'bytes': len(raw), 'receipt_checked_utc': receipt['checked_utc'],
                    'status': 'runtime_preflight_verified', 'model_outcomes_read': False,
                    'scope': 'Ten input identities, target membership, runtime environment and new output only'}
    with (OUT / 'verification.json').open('x', encoding='utf-8') as stream:
        json.dump(verification, stream, indent=2); stream.write('\n')
    prior = HERE / 'incidents' / 'E-20260929-005.r002.json'
    row = json.loads(prior.read_text())
    row['revision'] = 3; row['previous_sha256'] = ledger.sha(prior)
    row['recorded_utc'] = verification['observed_utc']
    row['evidence'].append(evidence)
    row['guard_applications'].append({
        'event_id': 'E-20260929-005.guard-job084-runtime-r1', 'state': 'verified_remotely',
        'job_id': receipt['job_id'], 'observed_utc': receipt['checked_utc'], 'site': 'runtime',
        'receipt_path': evidence['path'], 'receipt_sha256': digest,
        'manifest_sha256': receipt['manifest_sha256'], 'validator_sha256': VALIDATOR_SHA,
        'measured': 'Preflight completo PASS nel runtime:10 input,12target,output nuovo,ambiente e probe.',
        'not_verified': 'Scoring completo084 e utilita scientifica non dimostrati dal preflight.'})
    row['scope'] += ' Nuova ricevuta: preflight084 verificato nel runtime; nessuna conclusione sullo scoring084.'
    record = ledger.append(HERE / 'incidents', row)
    with (HERE / 'index_r3.json').open('x', encoding='utf-8') as stream:
        json.dump(ledger.index(HERE / 'incidents'), stream, indent=2, ensure_ascii=False); stream.write('\n')
    print(json.dumps(verification | {'record': str(record), 'record_sha256': ledger.sha(record)}))


if __name__ == '__main__':
    main()
