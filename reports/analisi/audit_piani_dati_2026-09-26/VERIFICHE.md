# Verifiche dell'audit

26 settembre 2026. Codice di produzione, ambiente, dataset e staging Git non modificati
da questo audit. Il checkout contiene modifiche concorrenti di Claude.

- `scripts/py.cmd -B reports/audit_piani_dati_2026-09-26/audit.py --out reports/audit_piani_dati_2026-09-26/r1`:
  completato; inventario, hash e controesempio in r1. Nessun refit.
- `scripts/py.cmd -B scripts/31_check_docs.py`: **OK**, 40 checkpoint,
  registro/decisioni/link coerenti e 197 percorsi archiviati riconosciuti.
- Riesecuzione mirata dopo la correzione di R-019:
  `scripts/py.cmd -B -m unittest discover -s tests -p test_doc_workflow.py`:
  **17 test passati**, 1,669 s.
- `scripts/py.cmd -B -m unittest discover -s tests`: 165 test in 232,651 s,
  due fallimenti e un errore. Non è una suite verde.

Dettaglio della suite:

1. `test_this_repository_is_consistent`: ha letto la prima versione di R-019,
   mentre mancavano cinque etichette obbligatorie della scheda. Corrette durante
   la sessione; successivo checker esplicito passato.
2. `test_the_reports_index_names_every_folder_once`: l'indice elenca la nuova
   cartella audit, ma la funzione `tracked` conta solo `git ls-files`.
   La cartella esiste ed è ancora untracked. Non si altera lo staging condiviso
   soltanto per soddisfare questo test; ricontrollare dopo l'aggiunta dei nuovi file.
3. `test_components_reproduce_the_scored_fidelity`: errore
   `ModuleNotFoundError: No module named 'cell_eval2.config'` in `de_tools.load_eval_config`.
   Non riguarda il codice dell'audit. Ambiente e dipendenze non sono stati riparati
   mentre l'altro agente lavora. Non si deduce che lo scorer cloud sia guasto.

La coerenza documentale non certifica la correttezza scientifica. Il controesempio
dimostra una dipendenza vietata nel calcolo delle medie, non il suo impatto numerico
sui guadagni riportati. La promozione del modello richiede una nuova valutazione.
