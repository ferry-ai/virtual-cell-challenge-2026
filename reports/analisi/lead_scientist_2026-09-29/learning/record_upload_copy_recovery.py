"""Archive small copy receipts and close only the local recovery part of E007."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import ledger

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SOURCE = Path('C:/Users/ferra/vcc2026-data/artifacts/t28_local_upload_r1')
TRIAL = REPO / 'reports/invii/trial_2026-09-29'
EXPECTED_SHA = '0d70ba92d68817b46383b11c53d513a41c85329230b9ff5524ac51f7bd110b32'
EXPECTED_BYTES = 4161126400


def evidence(path, supports):
    return {'path': path.relative_to(REPO).as_posix(), 'sha256': ledger.sha(path),
            'bytes': path.stat().st_size, 'supports': supports}


def main():
    payloads = {name: (SOURCE / name).read_bytes()
                for name in ['copy_state.json', 'local_copy_complete.json']}
    state = json.loads(payloads['copy_state.json'])
    complete = json.loads(payloads['local_copy_complete.json'])
    assert complete['status'] == 'verified_local_copy_not_uploaded'
    assert complete['file'] == {'bytes': EXPECTED_BYTES, 'sha256': EXPECTED_SHA}
    assert complete['state_sha256'] == hashlib.sha256(payloads['copy_state.json']).hexdigest()
    assert complete['metadata_sha256'] == state['metadata_sha256']
    assert len(complete['metadata_sha256']) == 8
    assert state['expected_bytes'] == EXPECTED_BYTES and state['expected_sha256'] == EXPECTED_SHA
    assert complete['resume_started_at_bytes'] == 3019898880
    output = HERE / 'upload_copy_recovery_r1'
    output.mkdir()
    inventory = []
    for name, raw in payloads.items():
        target = output / name
        with target.open('xb') as stream:
            stream.write(raw)
        assert target.read_bytes() == raw, 'Small receipt copy readback differs'
        inventory.append({'source': str(SOURCE / name), 'destination': target.relative_to(REPO).as_posix(),
                          'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    now = datetime.now(timezone.utc).isoformat()
    receipt = {
        'recorded_utc': now, 'claim_type': 'measured_receipt_copy', 'files': inventory,
        'receipt_consistency': 'PASS', 'copy_completed_utc': complete['utc'],
        'container_reread_by_this_collector': False,
        'scope': 'Byte-exact copies of the original copier receipts; full container SHA is attested by that completed copier, not recomputed by this collector.',
        'upload_status_attested': False,
    }
    readback = output / 'receipt_readback.json'
    with readback.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    previous = HERE / 'incidents/E-20260929-007.r002.json'
    record = json.loads(previous.read_text(encoding='utf-8'))
    record.update({
        'revision': 3, 'previous_sha256': ledger.sha(previous), 'recorded_utc': now,
        'state': 'verified_locally',
        'fix': 'Copia reale completata sul volume locale con il copier congelato, riprendendo da 3.019.898.880 byte dopo l\'arresto della guardia spazio. Ricevuta finale alle 22:28:32.001922 UTC: 4.161.126.400 byte, SHA256 atteso e otto hash metadata coerenti. Runner di invio separato e immutato.',
        'regression_test': 'Ricevuta di quattro test locali PASS conservata. La copia reale verifica inoltre ripresa del partial, SHA e dimensione completi e lettura dei metadata; non equivale a un test della CLI o della rete di upload.',
        'scope': 'Chiuso soltanto il recupero mediante copia locale verificata. La guardia spazio ha fermato il primo tentativo senza promuovere il partial; il resume completa il file. Non si attesta avvio, completamento o score dell\'upload. La validazione del runner sul percorso locale rimane una fase separata e qui non viene riletta.',
        'resolution': {'closed': True, 'scope': 'recovery_copy_only', 'verified_in': 'local copier runtime',
                       'observed_utc': complete['utc'], 'upload_verified': False},
    })
    record['evidence'] += [
        evidence(output / 'copy_state.json', 'Contratto originale del copier, copiato byte per byte'),
        evidence(output / 'local_copy_complete.json', 'Ricevuta originale del full SHA/size e degli otto metadata, non upload'),
        evidence(readback, 'Inventario e readback delle due piccole ricevute, nessuna ricopia del contenitore'),
        evidence(HERE / 'upload_copy_disk_stop_r1.json', 'Arresto precedente della guardia spazio e partial conservato'),
        evidence(TRIAL / 't28_local_copy_resume1.stdout.log', 'Log originale del resume e completamento della copia'),
        evidence(TRIAL / 't28_local_copy_resume1.stderr.log', 'Stderr originale del resume'),
        evidence(HERE.parent / 'candidate_generation_remote/recovery_r2/chunk_copy_tests_r1.json', 'Ricevuta dei quattro test locali del copier'),
    ]
    record['remote_verification'] = None
    incident = ledger.append(HERE / 'incidents', record)
    with (HERE / 'index_r10.json').open('x', encoding='utf-8') as stream:
        json.dump(ledger.index(HERE / 'incidents'), stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'incident': str(incident), 'sha256': ledger.sha(incident),
                      'state': record['state'], 'closed_scope': 'recovery_copy_only',
                      'upload_verified': False}))


if __name__ == '__main__':
    main()
