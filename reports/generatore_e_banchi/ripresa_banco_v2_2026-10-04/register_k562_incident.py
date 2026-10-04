"""Record the pre-scoring K562 exporter failure and the tested, separate repair."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
LEDGER = REPO / 'reports/analisi/lead_scientist_2026-09-29/learning'
sys.path.insert(0, str(LEDGER))
import ledger

root = Path('C:/Users/ferra/vcc2026-data/processed/ripresa_banco_v2_2026-10-04/error_k562_r1')
paths = []
for name in ('effects.log', 'kernel_done.json', 'resources.json'):
    dest = HERE / ('k562_r1_' + name)
    with dest.open('xb') as f:
        f.write((root / name).read_bytes())
    paths.append(dest)
paths += [HERE / 'EMENDAMENTO_K562.md', HERE / 'test_repair.py']
r = json.loads((LEDGER / 'incidents/E-20261004-002.r001.json').read_text(encoding='utf-8'))
r.update(eid='E-20261004-003', recorded_utc=datetime.now(timezone.utc).isoformat(), state='verified_locally',
         title='Banco v2 K562: guardia di copertura rifiuta target senza transfer di produzione',
         symptom='Preflight remoto passato; export fallisce prima dello scoring con prod: a target has no observed genes.',
         cause='La guardia nuova trattava le righe senza transfer come input corrotti; la baseline archiviata conserva quei target e genera dal basale.',
         cause_verified=True,
         fix='Esportatore r2 distinto: ammettere solo le righe realmente senza supporto della baseline prod, identiche nei due bracci; registrare i target e mantenerli tutti.',
         regression_test='test_repair.py: target non supportato mantenuto e nominato; target supportato mancante e riga vuota di all ancora rifiutati. Sei test piccoli passati.',
         next_guard='Distinguere assenza di supporto della baseline da asse o input mancante; nessun target eliminato per far passare il banco.',
         scope='Solo esportatore del retry K562; altri quattro job e regola scientifica invariati. Nessuno scoring K562 letto.',
         evidence=[dict(path=p.relative_to(REPO).as_posix(), bytes=p.stat().st_size, sha256=ledger.sha(p),
                        supports='Log del fallimento, risorse, emendamento o regressione della riparazione') for p in paths],
         remote_verification=None)
print(ledger.append(LEDGER / 'incidents', r))
