"""Record the observed local read failure without claiming a successful repair."""
from datetime import datetime, timezone
import json
from pathlib import Path

import ledger

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
TRIAL = REPO / 'reports/invii/trial_2026-09-29'
RUNNER = HERE.parent / 'candidate_generation_remote/recovery_r2/direct_t28_submission.py'


def evidence(path, supports):
    return {'path': path.relative_to(REPO).as_posix(), 'sha256': ledger.sha(path),
            'bytes': path.stat().st_size, 'supports': supports}


def main():
    started = TRIAL / 't28_direct_attempt_r1.worker_started.json'
    stdout = TRIAL / 't28_direct_attempt_r1.worker_stdout.log'
    stderr = TRIAL / 't28_direct_attempt_r1.worker_stderr.log'
    prior = TRIAL / 't28_in_place_validation_r1/validation.json'
    launch = json.loads(started.read_text(encoding='utf-8-sig'))
    old_receipt = json.loads(prior.read_text(encoding='utf-8-sig'))
    error = stderr.read_text(encoding='utf-8-sig')
    assert 'OSError: [Errno 22] Invalid argument' in error
    assert 'full_hash_checked' in error and 'f.read(8*1024**2)' in error
    assert launch['runner_sha256'] == ledger.sha(RUNNER)
    assert old_receipt['status'] == 'validated_in_place_not_submitted'
    assert old_receipt['uploaded'] is False
    output = Path(launch['output'])
    assert not output.exists(), 'The failed-attempt directory unexpectedly exists'
    now = datetime.now(timezone.utc).isoformat()
    observation = {
        'observed_utc': now,
        'attempt_output': str(output), 'attempt_output_exists': False,
        'submission_started_exists': (output / 'submission_started.json').exists(),
        'worker_started_utc': launch['started_utc'], 'worker_pid': launch['pid'],
        'last_stdout': stdout.read_text(encoding='utf-8-sig').strip(),
        'scope': 'Filesystem observation and original traceback. No claim about server state; this runner failed before its submit call.',
    }
    proof = HERE / 'upload_read_failure_observation_r1.json'
    with proof.open('x', encoding='utf-8') as stream:
        json.dump(observation, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    record = {
        'schema_version': 1, 'eid': 'E-20260929-007', 'revision': 1,
        'previous_sha256': None, 'recorded_utc': now,
        'claim_type': 'operational_incident', 'state': 'observed',
        'title': 'T28: lettura Drive fallita durante SHA prima della CLI di invio',
        'symptom': 'Il worker avviato alle 21:53:30 UTC termina con OSError 22 in f.read(8 MiB), durante il nuovo hash completo. Ultimo avanzamento registrato: 256 MiB. Non esistono directory del tentativo o submission_started.json.',
        'cause': 'Errore I/O di lettura dal percorso montato G: documentato. La causa precisa nel filesystem Drive, cache o handle non è verificata. Un hash completo precedente era riuscito alle 21:42:04 UTC e non garantisce la riuscita di una nuova lettura.',
        'cause_verified': False,
        'fix': 'Proposta in preparazione da un altro agente: copia locale a blocchi con riapertura del file, retry I/O limitati, budget disco e hash completo finale su C:, poi runner di invio invariato. Non ancora verificata in questo record.',
        'regression_test': 'Il traceback originale documenta il guasto. Test di retry, scritture parziali, budget disco e SHA errato sono richiesti alla correzione; il loro esito non è attestato qui.',
        'next_guard': 'Prima della CLI verificare il contenitore nel percorso realmente usato per l\'upload. Per file montati remoti, prevedere ripresa di lettura e copia su volume stabile con spazio esplicito; una vecchia ricevuta SHA non prova disponibilità futura.',
        'scope': 'Incidente aperto. Separare copia verificata, avvio upload, upload completo e score VCC. Nessuna di queste fasi è dimostrata dal solo fix scritto.',
        'evidence': [
            evidence(started, 'Ricevuta originale di avvio worker e hash del runner'),
            evidence(stdout, 'Ultimo avanzamento di hashing effettivamente registrato, non byte esatti al guasto'),
            evidence(stderr, 'Traceback originale: errore durante validazione, prima di submit'),
            evidence(prior, 'Hash completo precedente riuscito; uploaded=false'),
            evidence(RUNNER, 'validate viene chiamato prima di submit e crea output solo dopo la lettura completa'),
            evidence(proof, 'Osservazione locale di assenza output e marker di invio'),
        ],
        'remote_verification': None,
    }
    path = ledger.append(HERE / 'incidents', record)
    with (HERE / 'index_r8.json').open('x', encoding='utf-8') as stream:
        json.dump(ledger.index(HERE / 'incidents'), stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'record': str(path), 'state': record['state'], 'sha256': ledger.sha(path)}))


if __name__ == '__main__':
    main()
