# Verifiche della sessione

24 settembre 2026.

- `scripts/31_check_docs.py`: superato, 35 checkpoint, registro e link coerenti.
- `test_audit.py`: quattro test numerici superati (scala, orientamento delle
  coppie, offset Pearson, norma nulla e controllo a bersagli diversi).
- Controllo numerico di `analyze_mixscale.metrics`: Pearson +1 per trasformazione
  affine positiva, −1 per inversione, segni coerenti sui primi 100 geni.
- Suite completa: 147 test in 179,943 secondi; un errore di importazione
  `ModuleNotFoundError: No module named 'cell_eval2.config'` nel test
  `test_components_reproduce_the_scored_fidelity`; un fallimento dell'indice
  report perché `git ls-files` non vedeva i file ancora non registrati.
- Registrati i nuovi file con `git add -N`, senza commit o push.
  Rieseguito `test_live_tree.py`: tutti gli 11 test superati.
  L'errore della dipendenza dello scorer rimane aperto; non sono stati modificati
  lo scorer o le sue dipendenze.

Le analisi hanno letto i dati originali senza modificarli. L'archivio Mixscale
è stato scaricato nella radice dati esterna e verificato tramite MD5 pubblico.
Nessuna sottomissione o attività Colab eseguita.
