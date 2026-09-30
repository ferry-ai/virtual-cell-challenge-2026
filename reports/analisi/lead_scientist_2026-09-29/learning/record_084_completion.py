"""Record completed084 technical evidence separately from negative model results."""
from datetime import datetime, timezone
import json
from pathlib import Path

import ledger

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
NEURAL = HERE.parent / 'neural'


def main():
    inventory = NEURAL / 'stack_b_scoring_r1_files.json'
    receipt = json.loads(inventory.read_text())
    assert receipt['dispatcher_completion'] == '2026-09-29T21:25:06 finished 084_lead_stack_score_b_r1.sh rc=0'
    assert len(receipt['files']) == 10
    for item in receipt['files']:
        path = NEURAL / 'stack_b_scoring_r1' / item['name']
        assert ledger.sha(path) == item['sha256'] and path.stat().st_size == item['bytes']
    comparison_path = NEURAL / 'stack_b_scoring_r1' / 'pilot_comparison.json'
    comparison = json.loads(comparison_path.read_text())
    assert comparison['proceed_to_distinct_confirmation'] is False
    assert comparison['delta_projection'] < 0 and comparison['delta_pds_raw'] < 0
    prior = HERE / 'incidents' / 'E-20260929-005.r003.json'
    row = json.loads(prior.read_text())
    row['revision'] = 4; row['previous_sha256'] = ledger.sha(prior)
    row['recorded_utc'] = datetime.now(timezone.utc).isoformat()
    for path, supports in [(inventory, 'Job084rc0 e inventario10report completi conhashreadback'),
                           (comparison_path, 'Esito scientifico negativo distinto da successo tecnico')]:
        row['evidence'].append({'path': path.relative_to(REPO).as_posix(), 'bytes': path.stat().st_size,
                                'sha256': ledger.sha(path), 'supports': supports})
    row['guard_applications'].append({
        'event_id': 'E-20260929-005.guard-job084-completion-r1', 'state': 'verified_remotely',
        'job_id': '084_stack_b_development_scoring_r1', 'observed_utc': '2026-09-29T21:25:06+00:00',
        'site': 'runtime', 'evidence_path': inventory.relative_to(REPO).as_posix(),
        'measured': 'Job084 termina rc0 dopo preflight runtime;10report finali copiati conhashesatti.',
        'scientific_result': 'CandidatoB negativo secondo la regola di sviluppo; non e un incidente operativo.'})
    row['scope'] += '084completo rc0: applicazione remota del guard verificata; esito scientificoB negativo conservato separatamente.'
    record = ledger.append(HERE / 'incidents', row)
    with (HERE / 'index_r5.json').open('x', encoding='utf-8') as stream:
        json.dump(ledger.index(HERE / 'incidents'), stream, indent=2, ensure_ascii=False); stream.write('\n')
    print(json.dumps({'record': str(record), 'sha256': ledger.sha(record)}))


if __name__ == '__main__':
    main()
