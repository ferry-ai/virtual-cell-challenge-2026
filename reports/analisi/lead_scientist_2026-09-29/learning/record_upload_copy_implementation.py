"""Register the frozen repair code, without claiming its real copy succeeded."""
from datetime import datetime, timezone
import json
from pathlib import Path

import ledger

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RECOVERY = HERE.parent / 'candidate_generation_remote/recovery_r2'


def main():
    previous = HERE / 'incidents/E-20260929-007.r001.json'
    record = json.loads(previous.read_text(encoding='utf-8'))
    expected = {
        'copy_t28_chunked.py': '730fd206f2ecb85c137756228adb1b44c42a0a749dcdc153fc7aedbcd5a00c36',
        'test_copy_t28_chunked.py': 'fcb09043301a3a3e0cbc3dbd79916f9b9a8bfe241d8a06b30ae6ae9f0175e0cf',
    }
    for name, digest in expected.items():
        path = RECOVERY / name
        assert ledger.sha(path) == digest, 'Repair code changed after freeze'
        record['evidence'].append({
            'path': path.relative_to(REPO).as_posix(), 'sha256': digest,
            'bytes': path.stat().st_size,
            'supports': 'Codice congelato della correzione o della fixture; non ricevuta di esecuzione reale',
        })
    record.update({
        'revision': 2, 'previous_sha256': ledger.sha(previous),
        'recorded_utc': datetime.now(timezone.utc).isoformat(), 'state': 'implemented',
        'fix': 'Copier congelato: finestre da 64 MiB, letture da 8 MiB, handle richiuso a ogni finestra, massimo tre retry I/O aggiuntivi, partial conservato e ripresa esplicita. Budget disco, hash e dimensione finali sul file locale prima della promozione; runner di invio invariato.',
        'regression_test': 'Quattro fixture sono presenti: retry di una finestra senza append parziale; retry limitati con partial intatto; hash errato senza promozione; guardia disco e identità della sorgente. Questa revisione registra codice e contratto: non attribuisce ai file un esito di esecuzione.',
        'scope': 'Implementazione disponibile. Nessuna copia reale completata o upload è attestato in questa revisione; la chiusura richiede local_copy_complete.json con hash e dimensione esatti, seguita dalla validazione nel percorso reale usato dalla CLI.',
    })
    out = ledger.append(HERE / 'incidents', record)
    with (HERE / 'index_r9.json').open('x', encoding='utf-8') as stream:
        json.dump(ledger.index(HERE / 'incidents'), stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'record': str(out), 'state': record['state'], 'sha256': ledger.sha(out)}))


if __name__ == '__main__':
    main()
