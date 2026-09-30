# Registro degli errori e controlli riusabili

Guida autorevole: [docs/ERRORI.md](../../../../docs/ERRORI.md). Questa cartella
conserva incidenti e prove, senza duplicare la pipeline o avviare job.

Il primo censimento comprende cinque incidenti del 29 settembre. È una
ricostruzione da log, codice e ricevute, non un registro scritto all'istante
dei guasti. Ogni JSON distingue `recorded_utc` dai tempi osservati dell'evidenza.

| EID | Guasto | Stato al censimento | Criterio circoscritto |
|---|---|---|---|
| [E-20260929-001](incidents/E-20260929-001.r001.json) | 071: pooch assente nel percorso Stack/scvi | `verified_remotely` | Import reale riuscito dopo correzione; non implica efficacia del modello |
| [E-20260929-002](incidents/E-20260929-002.r001.json) | 072: indice H5AD nullable non scrivibile | `verified_remotely` | Roundtrip e due H5AD completi con hash verificati nel retry Kaggle |
| [E-20260929-003](incidents/E-20260929-003.r001.json) | 070: predizione non persistita prima della perdita del runtime | `verified_remotely` | Stage45 recuperato su Drive, SHA123ce93f… identico; packaging non certificato da questo record |
| [E-20260929-004](incidents/E-20260929-004.r001.json) | 075: NPZ144 privo dei12 target riservati | `verified_locally` | Codice/test passati;080 verifica già effetti144+12pilot, bundle completo ancora da verificare in questa revisione |
| [E-20260929-005](incidents/E-20260929-005.r001.json) | 081/082: marker visibile, H5AD e snapshot ancora assenti | `verified_remotely` | 082 supera tutti gli hash prima dello scoring e termina; il risultato del modello resta negativo |

Questa tabella descrive la revisione iniziale. Per lo stato corrente usare
`ledger.py index --directory <questa-cartella>/incidents`; `index_r1.json` è
una fotografia derivata. Le revisioni nuove non riscrivono la tabella storica.

- `preflight.py`: valida i contratti dei job sui percorsi locali o del runtime;
  snapshot congelato per l'applicazione al prossimo scoring B:
  SHA256 `1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744`.
- `test_preflight.py`: nove test su input mancanti, hash/dimensioni, target di
  riserva, nuovi output, ambiente, serializzazione e manifest mutato.
- `ledger.py`, `test_ledger.py`: revisioni append-only, catena degli hash e
  rifiuto di attestazioni remote senza evidenza; due test.
- `register_initial_incidents.py`: ricostruzione iniziale riproducibile; rifiuta
  una cartella incidenti già esistente. Non usarlo per aggiornare stati.
- `evidence_stack_071_072.json`: dettaglio dei log tecnici e verifiche dei due
  primi incidenti, compilato dall'agente generatore e collegato nei record.

Undici test locali superati prima del congelamento del preflight. La peer review
dell'agente generatore ha richiesto due guardie aggiunte prima del freeze:
output duplicati/annidati rifiutati e nuova verifica del manifest prima della
ricevuta. Il confronto del percorso Python conserva il nome del virtualenv:
risolvere il symlink al binario di sistema poteva confondere ambienti diversi.

Applicazione concreta prevista: job084, scoring B. Deve dichiarare le quattro
predizioni/metadata, snapshot scientifico, bundle, controlli, effetti, truth e
validatore; usare ricevute distinte locale/runtime prima del calcolo. La
preparazione del binder non è prova che questo job sia partito o abbia superato
il preflight: la ricevuta reale verrà collegata con una nuova evidenza.

Il validatore controlla solo input dichiarati e capacità del proprio processo.
Non configura altri processi Python, non certifica correttezza scientifica,
non concede autorizzazioni e non richiede di ripetere quelle già ricevute.
