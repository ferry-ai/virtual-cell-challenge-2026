# Verifiche dell'analisi e del piano

4 ottobre 2026. Verifiche locali su ricevute già presenti e piccoli dati sintetici; nessun training o job cloud.

## Prove specifiche

| Prova | Esito |
|---|---|
| `audit_prepass.py`, ricevuta `audit_r1.json` | Superata: con 29 controlli il contesto sintetico perde tutte le 49 cellule; con 30 controlli tutte le 50 entrano nel training. Hash dei sorgenti verificati prima/dopo, nessuna modifica al trainer. La prova non dimostra la sufficienza biologica di 29 controlli. |
| `audit_score.py`, ricevuta `score_audit_r1.json` | Superata: media dei sei membri, pannello/versione ancore, differenze t30–t25 e t30–t28 e ramo della regola verificati sui tre status originali. |
| `audit_timing.py`, ricevuta `timing_audit_r1.json` | Superata: 365 ricevute di prima lettura e 365 di seconda; intervallo di 6.677 secondi fra ultima prima lettura e prima seconda lettura. Non è una misura isolata del tempo della pianificazione globale. |

## Controlli del repository condiviso

Eseguita `scripts/py.cmd -m unittest discover -s tests`: **290 test in 616,550 secondi**, con due fallimenti di sotto-test dell'indice e tre errori d'importazione. Non si dichiara la suite interamente verde.

I tre errori erano `ModuleNotFoundError: No module named 'cell_eval2.config'`. Seguendo il precedente documentato CP-0054, gli stessi tre test sono stati ripetuti con lo stesso interprete fuori dal sandbox, senza installazioni: **3 test superati in 19,933 secondi**.

- `test_bench_generator.TestStage73Smoke.test_g0_arms_are_scored_once_per_generator_seed`
- `test_bench_generator.TestStage73Smoke.test_without_the_new_flags_the_old_stage_is_reproduced`
- `test_sc_pipeline.BenchComponentTests.test_components_reproduce_the_scored_fidelity`

Il test `test_live_tree.TestFolderMaps.test_reports_are_filed_by_category_and_each_folder_is_indexed_once` è stato ripetuto dopo aver tracciato l'indice della nuova cartella. Il problema della categoria `analisi/` è risolto. Resta un fallimento della categoria `invii/`: le cartelle già committate `prediction_t30_2026-10-04/` e `trial_2026-10-04/` non sono elencate in `reports/invii/README.md`. La chiusura degli indici dell'invio è affidata a Claude1 nel prompt; questa sessione non modifica i suoi report.

Il controllo documentale `scripts/py.cmd scripts/31_check_docs.py` è passato anche dopo la creazione di questo resoconto: 61 checkpoint, registro, decisioni, 10 strade e collegamenti coerenti; 197 percorsi riconosciuti come archiviati. Anche `git diff --check` è passato. Il limite della suite generale riguarda l'indice dell'invio t30 ancora da completare, non un test del nuovo trainer: qui non è stato implementato né modificato un trainer.
