# Verifiche della consegna

3 ottobre 2026, Codex. Sono verifiche del rapporto e della struttura del repository;
non validano le ipotesi sui modelli.

| Controllo | Esito | Evidenza |
|---|---|---|
| Audit dei metadati | Eseguito: 12 input, 716.534 byte; nessuna matrice cellulare aperta | [audit.json](audit_r1/audit.json), [script](audit_metadata.py) |
| Integrità durante il riconto | I 12 hash SHA256 ricalcolati dopo la scrittura coincidono con il manifest | Controllo in sessione sugli stessi percorsi del manifest |
| Confronto indipendente della copertura | 12 distribuzioni coincidono con `eval_support.csv`: 3 fold × 2 modalità × C/J, soglia 1 | [support.csv](audit_r1/support.csv); confronto con le colonne `training_groups_any` e `training_groups_CRISPRi` originali |
| Documentazione | OK: 57 checkpoint, registro, decisioni e link coerenti | [docs_check_r1.txt](docs_check_r1.txt) |
| Suite completa nel sandbox | 287 test: 283 passati, 3 errori, 1 fallimento | [tests_r1.txt](tests_r1.txt) |
| Ripetizione dei quattro casi falliti | 4/4 passati, stesso Python fuori dal sandbox, nuova cartella già nell'indice Git | [tests_r2_failed_native.txt](tests_r2_failed_native.txt) |

La suite completa è stata lanciata con:

```powershell
.\scripts\py.cmd -m unittest discover -s tests
```

I tre errori riguardano l'import di `cell_eval2.config` nei due smoke test dello stadio 73 e
nel test di coerenza delle componenti di fidelity. Il limite di visibilità nel sandbox era
già documentato nella [verifica del runtime del 1/10](../handoff_teammate_2026-10-01/VERIFICHE.md#correzione-scorer).
La ripetizione nativa ha importato lo scorer ed eseguito quei test senza installazioni o cambi
di dipendenze. Non è stata rieseguita l'intera suite fuori dal sandbox: la tabella distingue
esplicitamente le due esecuzioni.

Il quarto caso legge `git ls-files`: nel primo passaggio l'indice non conteneva ancora la nuova
cartella citata dall'indice delle analisi. Dopo lo staging nominativo passa senza modificare
il test. Sono stati ripetuti esattamente:

- `test_live_tree.TestFolderMaps.test_reports_are_filed_by_category_and_each_folder_is_indexed_once`
- `test_bench_generator.TestStage73Smoke.test_g0_arms_are_scored_once_per_generator_seed`
- `test_bench_generator.TestStage73Smoke.test_without_the_new_flags_the_old_stage_is_reproduced`
- `test_sc_pipeline.BenchComponentTests.test_components_reproduce_the_scored_fidelity`

I numeri prodotti dallo scorer nei log sono su fixture sintetiche dei test, non risultati VCC
del progetto. Nessuna modifica al codice attivo dei modelli, alle sorgenti cellulari o ai job.
