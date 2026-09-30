# Scoring CPU B: codice congelato, input ancora da collegare

29 settembre 2026. **Preparato, non eseguito.** Nessuna lettura di predizioni,
truth o risultati; nessuna copia su Drive e nessuna coda.

`scoring_snapshot.tar.gz`, SHA256
`6e216f900a606656c182bb7f520e351bb7805358a0e2943a226ce3a105071dcb`,
deriva dallo snapshot A `9f89e6380704210adac7445199ca15117e85138193fd55c3cd6de8749a681f65`.
Tutti i suoi **17 file** sono conservati byte per byte. Le uniche tre aggiunte sono:

- `stack_input_axis_pilot.py`, SHA256
  `a85b752dbd5042fde45611e80a6a942733bb19de6c4a00a03ab71db33a90d2a4`;
- `score_stack_input_axis.py`, SHA256
  `74607f249fc36642e74a374e45c32157391b875888efe715163642674045b28c`;
- `PROTOCOLLO_STACK_AB.md`, SHA256
  `181d7a00b1f5957948e2daf9fcd1f66fae9adb35dbf78aab59a5b2c006133506`.

La lista completa con dimensioni e hash è in `scoring_manifest.json`. Nessun
modulo `src` è aggiornato. Le funzioni di calcolo dello scorer B sono identiche
a quelle A: cambia soltanto l'import dell'adapter e la verifica della sua
provenienza. Lo scoring resta full truth sui dodici development del pilot,
cinque membri con pendenze ufficiali / sei; MSE separata.

`084_lead_stack_score_b_r1.sh.template` usa il Python già pronto
`/content/lead_candidate_environment_r2/venv/bin/python`, stessi bundle A,
truth e ancore, due thread. Attende fino a 45 tentativi distanziati di 20 secondi
gli hash completi di entrambi gli H5AD, `finished.json`, `inference_manifest.json`
e snapshot. Verifica poi l'hash del bundle A. Tutto precede creazione di codice
estratto e output di scoring. Non installa pacchetti nel runtime base.

**Il template termina intenzionalmente con exit 64 prima di accedere agli input.**
Non va copiato in coda come job. Dopo che B è approvato e completo occorrono:

1. Ricevuta concreta con percorso remoto B e SHA256 dei quattro file di input.
2. Nuovo launcher derivato che sostituisce i cinque segnaposto e attiva
   `INPUT_RECEIPT_BOUND=true`, registrando l'hash della ricevuta e del launcher.
3. Revisione del lead prima di copia/accodamento. Usare sempre output nuovi.

I percorsi proposti di setup/output nel template non costituiscono ricevuta
di copia o prova di disponibilità degli input.

Due test locali superati (`test_stack_b_scoring.py`): tutti i 17 file originali
identici, solo tre aggiunte, parità AST delle funzioni di calcolo; sintassi Bash
valida e rifiuto del template prima dell'I/O. Il builder è
`../build_stack_b_scoring.py`; non avvia il modello o lo scorer.

Questo è esclusivamente il **pilot development B**. L'eventuale conferma distinta
del candidato selezionato usa un altro adapter/protocollo e attende il manifest
completo di selezione A/B; questo pacchetto non autorizza una conferma o un invio.
