"""Verify the completed local job084 receipt and append a deployment event.

This does not re-run preflight, inspect model outcomes, or assert remote success.
Historical incident005 was already closed by job082; its new guard deployment
has a separate explicitly local status.
"""
from datetime import datetime, timezone
import json
from pathlib import Path

import ledger


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
BOUND = HERE.parent / 'neural' / 'stack_b_scoring_bound_r1'
VALIDATOR_SHA = '1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744'


def main():
    receipt_path, contract_path = BOUND / 'preflight_local_receipt.json', BOUND / 'job_contract.json'
    receipt = json.loads(receipt_path.read_text())
    contract = json.loads(contract_path.read_text())
    assert receipt['status'] == 'PASS' and receipt['site'] == 'local'
    assert receipt['job_id'] == contract['job_id'] == '084_stack_b_development_scoring_r1'
    assert receipt['manifest_sha256'] == ledger.sha(contract_path)
    assert receipt['validator_sha256'] == ledger.sha(HERE / 'preflight.py') == VALIDATOR_SHA
    expected = {x['id']: x for x in contract['inputs']}
    actual = {x['id']: x for x in receipt['inputs']}
    assert len(expected) == len(actual) == len(receipt['inputs']) == 10
    assert expected.keys() == actual.keys()
    for key, item in expected.items():
        assert item['paths']['local'] == actual[key]['path']
        assert item['sha256'] == actual[key]['sha256'] and item['bytes'] == actual[key]['bytes']
    assert receipt['new_outputs'] == [x['paths']['local'] for x in contract['outputs']]
    assert receipt['target_checks'] == [{'input_id': 'transfer.npz', 'npz_key': 'targets',
                                        'required_count': 12, 'available_count': 12}]
    assert len(contract['target_checks'][0]['required']) == 12
    assert receipt['environment']['executable'] == contract['environment']['python']['paths']['local']
    assert set(receipt['environment']['imports_passed']) == set(contract['environment']['imports'])
    assert receipt['environment']['probes_passed'] == ['h5ad_nullable_roundtrip']
    assert 'This process only' in receipt['environment']['configuration_scope']
    launcher = BOUND / '084_lead_stack_score_b_r1.sh'
    text = launcher.read_text()
    assert text.index('--site runtime') < text.index('tar -xzf') < text.index('score_stack_input_axis.py')
    assert '--attempts 45 --interval-seconds 20' in text
    assert receipt['manifest_sha256'] in text and VALIDATOR_SHA in text
    prior = HERE / 'incidents' / 'E-20260929-005.r001.json'
    row = json.loads(prior.read_text())
    row['revision'] = 2
    row['previous_sha256'] = ledger.sha(prior)
    row['recorded_utc'] = datetime.now(timezone.utc).isoformat()
    event = {
        'event_id': 'E-20260929-005.guard-job084-local-r1',
        'state': 'verified_locally', 'job_id': receipt['job_id'],
        'observed_utc': receipt['checked_utc'], 'site': 'local',
        'receipt_path': receipt_path.relative_to(REPO).as_posix(),
        'receipt_sha256': ledger.sha(receipt_path),
        'manifest_sha256': receipt['manifest_sha256'], 'validator_sha256': VALIDATOR_SHA,
        'measured': 'Ricevuta PASS sul laptop:10 input size/SHA,12 target presenti,output nuovo,import e roundtrip nullable.',
        'implemented': 'Il launcher richiede lo stesso preflight nel runtime prima di estrazione e scoring.',
        'not_verified': 'Disponibilita dei file nel runtime Colab,esecuzione084 e risultato scientifico non attestati da questa ricevuta.'}
    row['guard_applications'] = [event]
    row['scope'] += (' Evento aggiunto: il nuovo guard riusabile e applicato localmente a084;'
                     ' lo stato verified_remotely sopra continua a riferirsi solo alla chiusura storica082.')
    for path, supports in [
        (receipt_path, 'Uso reale del guard sul laptop; non prova remota'),
        (contract_path, 'Dieci input espliciti con percorsi locali/runtime e target richiesti'),
        (launcher, 'Guard runtime obbligatorio prima estrazione/scoring; non prova esecuzione'),
    ]:
        row['evidence'].append({'path': path.relative_to(REPO).as_posix(),
            'sha256': ledger.sha(path), 'bytes': path.stat().st_size, 'supports': supports})
    output = ledger.append(HERE / 'incidents', row)
    with (HERE / 'index_r2.json').open('x', encoding='utf-8') as stream:
        json.dump(ledger.index(HERE / 'incidents'), stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'record': str(output), 'record_sha256': ledger.sha(output),
                      'local_receipt_sha256': ledger.sha(receipt_path), 'runtime_verified': False}))


if __name__ == '__main__':
    main()
