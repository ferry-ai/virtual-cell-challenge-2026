# Verifiche della sessione — 24 settembre 2026

**Misurato:** esecuzioni locali, Codex; nessuna modifica al codice di produzione.

- `scripts/py.cmd reports/audit_stato_2026-09-24/audit.py`: completato, exit 0.
  Output `measurements.json`, hash degli input e risultati per bersaglio conservati.
- `scripts/py.cmd scripts/31_check_docs.py`: passa dopo la registrazione dei nuovi
  materiali e la correzione dei campi obbligatori della scheda R-016; 34 checkpoint.
- `scripts/py.cmd -m unittest discover -s tests`: 142 test, 295,716 secondi;
  1 fallimento documentale e 1 errore del banco, gli altri 140 senza errori.
  Il controllo documentale è partito prima che venisse completata la registrazione
  della cartella di audit, e segnalava i due file allora non registrati.
- Dopo la registrazione: `scripts/py.cmd -m unittest discover -s tests -p test_doc_workflow.py`:
  tutti i 16 test passano, 1,115 secondi.

**Problema ancora aperto:**
`test_sc_pipeline.BenchComponentTests.test_components_reproduce_the_scored_fidelity`
non riesce a costruire `Bench`: `src/vcc2026/de_tools.py:39` importa
`cell_eval2.config.EvalConfig`, ma l'ambiente restituisce
`ModuleNotFoundError: No module named 'cell_eval2.config'`.
La suite completa quindi non è verde. Il problema non riguarda il calcolo sulle cache
usato da questo audit, che non richiama `Bench`. Prima di eseguire i banchi proposti,
occorre verificare e ripristinare l'ambiente dello scorer e ripetere il test di parità.
Non è stata tentata un'installazione o modifica delle dipendenze durante l'analisi.

L'ispezione della formula FID nel report si riferisce al codice del progetto e agli
artefatti precedenti; la sua parità eseguibile con lo scorer non è stata riconfermata
in questa sessione a causa dell'errore sopra.
