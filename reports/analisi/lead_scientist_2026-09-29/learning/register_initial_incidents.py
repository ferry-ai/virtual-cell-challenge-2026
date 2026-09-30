"""Register five evidence-backed incidents; never read matrices or change jobs."""
from datetime import datetime, timezone
import json
from pathlib import Path
import ledger

HERE = Path(__file__).resolve().parent
LEAD = HERE.parent
REPO = HERE.parents[3]
DRIVE = Path('G:/Il mio Drive/vcc2026')


def evidence(path, supports):
    path = Path(path)
    label = path.relative_to(REPO).as_posix() if path.is_relative_to(REPO) else path.as_posix()
    return {'path': label, 'sha256': ledger.sha(path), 'bytes': path.stat().st_size, 'supports': supports}


def record(number, title, symptom, cause, fix, test, guard, scope, items, state='verified_remotely', remote=None):
    obj = {'schema_version': 1, 'eid': f'E-20260929-{number:03d}', 'revision': 1,
        'previous_sha256': None, 'recorded_utc': datetime.now(timezone.utc).isoformat(),
        'claim_type': 'operational_incident', 'title': title, 'symptom': symptom,
        'cause': cause, 'cause_verified': True, 'fix': fix, 'regression_test': test,
        'next_guard': guard, 'scope': scope, 'evidence': items, 'state': state,
        'remote_verification': remote}
    ledger.append(HERE / 'incidents', obj)


def main():
    if (HERE / 'incidents').exists():
        raise FileExistsError('Initial incidents already registered; append revisions instead')
    stack = json.loads((HERE / 'evidence_stack_071_072.json').read_text(encoding='utf-8'))
    for number, item in enumerate(stack['incidents'], 1):
        ev = [{**stack['evidence'][key], 'supports': key} for key in item['evidence_ids']]
        marker = '072_import_success' if number == 1 else 'kaggle_completion'
        record(number, f"Job {item['job']}: " + ('dipendenza pooch assente' if number == 1 else 'H5AD nullable non serializzabile'),
            item['observed_error'], item['causal_claim'], item['implemented_fix'],
            'learning/test_preflight.py: import assente e roundtrip H5AD; ' + item['verification'],
            item['prevention'], 'Correzione tecnica verificata; non prova qualità scientifica del modello.', ev,
            remote={'evidence_path': stack['evidence'][marker]['path'], 'observed_utc': stack['recorded_utc'],
                    'criterion': item['verification']})
    diag = LEAD / 'candidate_generation_remote/t28_diagnostic_r1.json'
    recovery = LEAD / 'candidate_generation_remote/recovery_r2'
    complete = recovery / 'stage45_receipt/complete.json'
    receipt = json.loads(complete.read_text())
    items = [evidence(diag, 'Il primo runtime aveva completato stage45 e avviato stage48, hash123ce nel log preservato'),
        evidence(recovery / 'RECUPERO.md', 'Diagnosi owner19:58:07: processi, file e mount assenti; causa del distacco non accertata'),
        evidence(LEAD / 'candidate_generation_remote/generate_candidate.py', 'Il primo runner copiava solo il pacchetto concluso; H5AD temporaneo non preservato su Drive'),
        evidence(recovery / 'generate_candidate_r2.py', 'Checkpoint completo su Drive prima del packaging'),
        evidence(recovery / 'review.json', 'Test di recupero e invariance'),
        evidence(complete, 'SHA completo della predizione recuperata identico al primo runtime')]
    record(3, 'Job070: artefatto completo rimasto nel runtime perso',
        'Generazione terminata, poi runtime non più disponibile prima di un pacchetto durabile.',
        'La copia persistente della predizione era rinviata dopo stage48. La ragione della perdita della sessione non è dimostrata.',
        'Stessa ricetta/semi, nuovo run; copia .partial, SHA completo e rename del checkpoint stage45 prima di stage48.',
        'Quattro test in recovery_r2/review.json: copia, no overwrite, partial, AST/order invariance.',
        'Checkpoint durabile con ricevuta hash dopo ogni fase costosa riutilizzabile, prima della successiva.',
        'Chiuso solo il recupero stage45: 4213225652 byte, SHA123ce93f…; non certifica packaging o submission.', items,
        remote={'evidence_path': items[-1]['path'], 'observed_utc': receipt['utc'],
                'criterion': 'full_sha256_verified true e SHA della stessa predizione uguale al primo runtime'})
    items = [evidence(DRIVE / 'runs/jobs/075_lead_stack_confirmation_prepare_r1.log', 'ValueError target mancante prima creazione bundle'),
        evidence(DRIVE / 'runs/lead_stack_confirmation_prompts_2026-09-29_r1/plan.json', 'Dodici target riserva corretti, effects deriva dal banco144'),
        evidence(LEAD / 'neural/RIPARAZIONE_075.md', 'Diagnosi e correzione senza refit'),
        evidence(LEAD / 'neural/stack_confirmation_effects.py', 'Guarda parità esatta144+pilot12 prima di salvare riserva'),
        evidence(LEAD / 'neural/test_stack_confirmation_effects.py', 'Test di mappatura, maskzero e target mancanti'),
        evidence(DRIVE / 'runs/lead_stack_confirmation_prompts_2026-09-29_r2/effects/manifest.json', '080 ha verificato effetti144+12pilot; non attesta completamento del bundle cellulare')]
    record(4, 'Job075: effetti derivati senza i target riservati',
        'Frozen transfer lacks a confirmation target dopo il piano dei dodici target.',
        'prepared_effects del banco comprende48+96target, mentre la riserva12 è disgiunta per costruzione.',
        'Recupero valori t19like congelati e stessa maskstage98; parità esatta sui144 e12pilot. Pack scientifico immutato.',
        'test_stack_confirmation_effects.py e test_preflight.py: riserva assente rifiutata prima del lavoro.',
        'Controllare required⊆targets dell’NPZ durante preflight prima di estrazione costosa.',
        '080 ha prodotto effetti verificati e piano; bundle completo non ancora verificato in questa revisione.', items,
        state='verified_locally')
    items = [evidence(DRIVE / 'runs/jobs/081_lead_stack_score_kaggle_a_r1.log', 'Manifest visibile ma H5ADstack ancora assente sul runtime'),
        evidence(DRIVE / 'runs/jobs/082_lead_stack_score_kaggle_a_r2.log', 'Attende transfer, poi snapshot assente; tutti hash OK al tentativo29 e scorer termina'),
        evidence(LEAD / 'neural/082_lead_stack_score_kaggle_a_r2.sh', 'Attesa fullhash di tutte le predizioni e dello snapshot'),
        evidence(LEAD / 'neural/stack_a_scoring_r2/evaluation_manifest.json', 'Processo scoring avviato dopo verifica'),
        evidence(LEAD / 'neural/RISULTATI_STACK_A.md', '082rc0 20:53:18 e risultato scientifico negativo distinto dal guasto'),
        evidence(HERE / 'preflight.py', 'Inventario completo, size/hash nel runtime e attesa'),
        evidence(HERE / 'test_preflight.py', 'Marker esistente non nasconde input assente')]
    record(5, 'Job081/082: input parzialmente sincronizzati e snapshot mancante',
        '081 si ferma H5AD assente;082 attende poi lo snapshot del codice assente nel mount.',
        'Il marker non dimostrava sincronizzazione dei file grandi; anche lo snapshot necessario non era disponibile al runtime. I log non distinguono da soli omissione copia e ritardo sync.',
        'Inventario completo inclusivo snapshot; copia e attesa dei SHA completi di ogni input prima extraction/scoring.',
        'test_preflight.py: marker presente/file assente, hash errato a stessa dimensione e output nuovo.',
        'Manifest input completo; ricevuta locale distinta da runtime; mai usare marker o glob di altri run come prova di completezza.',
        'Guasto tecnico risolto nel082. A perde il confronto scientifico: ciò non riapre questo incidente né autorizza una promozione.', items,
        remote={'evidence_path': items[1]['path'], 'observed_utc': '2026-09-29T20:53:18+00:00',
                'criterion': 'Tutti SHA richiesti OK prima estrazione,8testPASS e scoring completo; rc0 attestato nel reportroot'})
    with (HERE / 'index_r1.json').open('x', encoding='utf-8') as stream:
        json.dump(ledger.index(HERE / 'incidents'), stream, indent=2, ensure_ascii=False); stream.write('\n')
    print('Registered five incidents; no job or scientific code changed.')


if __name__ == '__main__':
    main()
