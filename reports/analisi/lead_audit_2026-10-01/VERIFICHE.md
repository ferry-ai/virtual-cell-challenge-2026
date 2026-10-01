# Verifiche e riproduzione

1 ottobre 2026. Analisi locale in Python dell'ambiente di progetto (`scripts/py.cmd`).
Nessuna dipendenza installata. Tutte le sei analisi sotto sono terminate con exit code 0;
ogni directory contiene output e manifest degli input. Gli script rifiutano destinazioni
già esistenti: per ripetere usare un suffisso nuovo, non sovrascrivere queste misure.

## Esecuzioni completate

Comandi dalla radice del repository (qui i nomi delle destinazioni originali):

```powershell
.\scripts\py.cmd reports/analisi/lead_audit_2026-10-01/analyze_outputs.py --out reports/analisi/lead_audit_2026-10-01/r1
.\scripts\py.cmd reports/analisi/lead_audit_2026-10-01/replay_sampler.py --out reports/analisi/lead_audit_2026-10-01/sampler_r1
.\scripts\py.cmd reports/analisi/lead_audit_2026-10-01/reproduce_findings.py --out reports/analisi/lead_audit_2026-10-01/counterexamples_r1
.\scripts\py.cmd reports/analisi/lead_audit_2026-10-01/analyze_hepg2.py --raw C:/Users/ferra/vcc2026-data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad --out reports/analisi/lead_audit_2026-10-01/data_r1
.\scripts\py.cmd reports/analisi/lead_audit_2026-10-01/analyze_design.py --raw C:/Users/ferra/vcc2026-data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad --out reports/analisi/lead_audit_2026-10-01/design_r1
.\scripts\py.cmd reports/analisi/lead_audit_2026-10-01/analyze_r3.py --out reports/analisi/lead_audit_2026-10-01/r3_followup_r1
```

- Replay: assert sul totale delle estrazioni e sulle estrazioni per chiave, uguali al log r2;
  50.172 batch riprodotti. I coefficienti della loss non sono norme dei gradienti.
- Controesempi: codice originale importato senza patch; fixture temporanea di shard per il
  prepass completo. Risultati in `counterexamples_r1/counterexamples.json` e log nella stessa
  cartella. Sono prove del meccanismo, non stime del danno predittivo sul corpus reale.
- HepG2: file di 850.590.740 byte, SHA256
  `1af2f7b3e692ad3d077e6027d68a1f800619e29aa3f7a0efa70146fb7223a4bf`;
  lettura integrale per blocchi e verifica dell'integralità dei valori. Nessuna copia del
  dataset nella repo. La ricostruzione dei controlli usa lo stesso file, manifest in `data_r1`.
- Codice cellnet: SHA256 di `cellnet.py`, `cell_data.py`, `train_cellnet.py` uguali a quelli
  registrati in `training_r2/train/config.json`; hash completi in `counterexamples_r1/manifest.json`.

## Stato esterno e fonti

Kaggle ha risposto `KernelWorkerStatus.RUNNING` durante la revisione per
`davidmaisterx/rlab-cellnet-r3`. È una lettura dello stato, non un'ispezione dei pesi ancora in
calcolo. La prima chiamata dal sandbox era impedita da Windows (`WinError 10013`); la lettura
con accesso di rete ha poi funzionato. Nessun job avviato, modificato o fermato.
La lettura successiva, avviata alle **14:38:18 CEST**, ha restituito `COMPLETE`. Gli output
locali arrivati durante l'audit sono ricalcolati in `r3_followup_r1`; non sono stati aperti
checkpoint binari del training. Il nuovo controesempio verifica il segno del gradiente della
miscela con clamp e con log-sigmoid stabile.

Pagine primarie della gara, metriche e modelli consultate online il 1 ottobre; URL e portata
nel [rapporto](REVISIONE.md). T29 letto come registrazione, non come risultato pubblicato.

## Verifiche finali del repository

- `scripts/31_check_docs.py`: **passa**, 53 checkpoint, registro, decisioni e link coerenti;
  197 percorsi archiviati riconosciuti. Verifica strutturale, non scientifica.
- Integrità: **42 voci di manifest / 27 input distinti** verificati, inclusi SHA del file
  raw e dei tre file della rete rispetto al config r2. Nessun artefatto dell'audit supera
  1 MB (massimo 298.600 byte alla verifica). Esito in [integrity_r1.json](integrity_r1.json).
- `git diff --check`: passa.
- Suite completa `-m unittest discover -s tests`: **287 test eseguiti**, 3 errori e un
  fallimento al primo passaggio. I tre errori sono `ModuleNotFoundError: cell_eval2.config`
  nei due smoke test di `test_bench_generator.TestStage73Smoke` e in
  `test_sc_pipeline.BenchComponentTests.test_components_reproduce_the_scored_fidelity`.
  Conferma indipendente in un nuovo processo: `cell_eval2.__file__` e
  `find_spec('cell_eval2.config')` entrambi `None`. L'ambiente dello scorer è incompleto;
  nessun modulo di produzione o dipendenza è stato cambiato da questa revisione.
- Il fallimento di `TestFolderMaps.test_reports_are_filed_by_category_and_each_folder_is_indexed_once`
  usa l'elenco Git: la nuova cartella dell'audit non era ancora indicizzata. Dopo l'aggiunta
  nominativa a Git, `-m unittest discover -s tests -p test_live_tree.py` passa: **11 test OK**,
  senza modifica al test. Ripetuto anche il controllo documentale: passa. Restano non
  verificati i tre test che richiedono il modulo scorer mancante; suite complessiva non verde.

## Limiti che restano

- Nessun nuovo punteggio ufficiale, nessuna verifica dell'effetto dei fix mediante training.
- Rianalisi a posteriori: HepG2 è sviluppo. H1 test non aperta.
- Un solo contesto per le nuove analisi cellulari, una divisione casuale per il confronto
  metà/metà; non repliche biologiche e non ceiling comparabile ai top-200 della rete.
- Il rapporto non quantifica quanto ogni difetto spieghi la perdita predittiva.
- Gli artefatti dell'altro agente restano suoi; questa revisione consegna evidenza e piano,
  non altera il processo in corso né ne sostituisce il protocollo.
