"""Register measured guard006 failure and a prepared, not-yet-verified repair."""
from datetime import datetime, timezone
import json
from pathlib import Path
import ledger

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
NEURAL = HERE.parent / 'neural'


def main():
    evidence = []
    for relative, supports in [
        ('stack_ab_selector_attempt1.json', 'Ricostruzione del lead dal risultato tool9431; non un file stdout originale'),
        ('stack_ab_numerical_diagnostic_r1/csv_difference.json', 'Una differenza reale11ULP su105valori; aggregati/config/versioni uguali'),
        ('stack_ab_numerical_diagnostic_r1/polars_probe.json', 'Fixture locale cambia ordine gruppi con piu thread ma non valori; causa esatta non dimostrata'),
        ('test_stack_numerical_incident.py', 'Riproduce il rifiuto del selettore leggendo i CSV completi originali'),
        ('EMENDAMENTO_NUMERICO_STACK_AB_01.md', 'Singolo ricontrollo sequenziale fissato, soglie e selector invariati'),
        ('stack_paired_scoring_setup_r1/review.json', '085preparato coninput/codice congelati e pinversioni; nessuna esecuzione attestata'),
        ('test_stack_paired_rescore.py', 'Controlli equivalenza codice/input, preflight e sequenzialita del pacchetto'),
    ]:
        path = NEURAL / relative
        evidence.append({'path': path.relative_to(REPO).as_posix(), 'sha256': ledger.sha(path),
                         'bytes': path.stat().st_size, 'supports': supports})
    row = {'schema_version': 1, 'eid': 'E-20260929-006', 'revision': 1,
        'previous_sha256': None, 'recorded_utc': datetime.now(timezone.utc).isoformat(),
        'claim_type': 'operational_incident', 'state': 'implemented',
        'title': 'Selettore A/B: uguaglianza esatta rifiuta una differenza numerica di11ULP',
        'symptom': 'Il selettore congelato rifiuta transferSETD1A/NMAE; nessun manifest di selezione scritto.',
        'cause': 'Misurata discrepanza1.2212453270876722e-15 su105valori, con6aggregati identici. Origine specifica dei11ULP ancora ignota; riduzioni/join paralleli plausibili, non dimostrati.',
        'cause_verified': False,
        'fix': 'Preparato un solo job085 sequenziale conhashseed0 e thread1,stessiinput/scorer/versioni; il selettore esatto rimane immutato.',
        'regression_test': 'test_stack_numerical_incident.py riproduce il fallimento reale;3testpacket085 e bash-n verificano solo il setup. La fixture Polars locale non riproduce variazione nei valori.',
        'next_guard': 'Fissare thread/versioni prima import e misurare parita numerica ripetuta prima di pretendere baseline bit-identica. Non ampliare tolleranze dopo risultati senza prova e preregistrazione distinta.',
        'scope': 'Implementazione preparata, non correzione verificata. I risultati scientifici A/B negativi non sono il guasto operativo e non autorizzano di forzare una selezione.',
        'evidence': evidence, 'remote_verification': None}
    path = ledger.append(HERE / 'incidents', row)
    with (HERE/'index_r6.json').open('x', encoding='utf-8') as stream:
        json.dump(ledger.index(HERE/'incidents'), stream, indent=2, ensure_ascii=False); stream.write('\n')
    print(json.dumps({'record': str(path), 'state': row['state'], 'cause_verified': row['cause_verified'], 'sha256': ledger.sha(path)}))


if __name__ == '__main__':
    main()
