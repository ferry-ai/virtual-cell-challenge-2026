# Verifica finale del repository e limiti

**Misurato localmente il 29 settembre 2026, registrazione alle 22:08 UTC.**
La suite generale non è interamente verde. Il controllo della documentazione
passa; gli esiti scientifici dei job remoti restano quelli dei rispettivi report.

## Controlli eseguiti

| Comando | Esito |
|---|---|
| `.\scripts\py.cmd scripts/31_check_docs.py` | PASS, codice 0: 51 checkpoint, registro, decisioni e collegamenti coerenti; 197 percorsi storici accettati |
| `.\scripts\py.cmd -m unittest discover -s tests` | Codice 1: 282 test in 180,244 secondi, 3 errori e 2 failure |

La fonte è l'output del tool della sessione `69164`, completata con codice 1.
Non è stato salvato un log stdout originale. La
[trascrizione strutturata](learning/final_repo_tests_r1.json) conserva comando,
conteggi, tempo riferito da unittest e nomi dei casi falliti. Il momento di
registrazione non è presentato come l'istante esatto di fine della suite.

## Errori e failure completi

I tre errori hanno lo stesso traceback terminale:
`ModuleNotFoundError: No module named 'cell_eval2.config'`.
Il percorso passa da `Bench.__init__` a `scorer_config` e `load_eval_config`.

1. `test_bench_generator.TestStage73Smoke.test_g0_arms_are_scored_once_per_generator_seed`.
2. `test_bench_generator.TestStage73Smoke.test_without_the_new_flags_the_old_stage_is_reproduced`.
3. `test_sc_pipeline.BenchComponentTests.test_components_reproduce_the_scored_fidelity`.

Le altre due failure provengono da
`test_live_tree.TestFolderMaps.test_reports_are_filed_by_category_and_each_folder_is_indexed_once`:

- Categoria `invii/`: l'indice elenca `prediction_t28_2026-09-29/`, assente
  dall'inventario usato dal test.
- Categoria `sorgenti/`: stessa discrepanza per `basali_asse_2026-09-29/`.

Entrambe le cartelle esistono fisicamente, verificato dopo il test. Il controllo
usa un inventario Git: queste failure non attestano perdita dei file. Non sono
state corrette aggiungendo file a Git durante questa verifica.

## Portata

Non si attribuisce automaticamente questi errori alle modifiche della sessione,
né si dichiara verificata una causa più specifica dell'import mancante. Non è
stata ripetuta la suite, installato un pacchetto o cambiato il codice degli stadi
per forzare il verde. Questo ambiente locale è distinto dagli ambienti congelati
dei job scientifici: il suo errore di import non dimostra che gli scorer remoti
abbiano usato un'altra formula.

La coerenza documentale è un controllo di struttura, non una verifica della
correttezza dei claim. Il confronto Stack A/B è invece chiuso dalle ricevute,
dai report completi e dal selettore congelato:
[risultati e limiti](neural/RISULTATI_STACK_AB.md). Entrambi sono negativi;
il ricontrollo numerico non cambia i loro delta.

Questa verifica non certifica l'upload del t28. Il guasto di lettura prima della
CLI e il copier preparato sono separati in
[E007 r001](learning/incidents/E-20260929-007.r001.json) e
[r002](learning/incidents/E-20260929-007.r002.json). Una copia in corso, i test
del copier o un hash precedente non equivalgono a copia completa, invio riuscito
o score VCC. Gli aggiornamenti successivi devono avere nuove ricevute e revisioni
del ledger, senza riscrivere questa fotografia.
