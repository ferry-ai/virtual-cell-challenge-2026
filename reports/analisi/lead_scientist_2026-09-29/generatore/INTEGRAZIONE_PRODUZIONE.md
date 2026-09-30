# Integrazione opzionale nello stadio 45

29 settembre 2026. Implementazione autorizzata dalla sessione principale dopo
le misure sui soli controlli; nessun punteggio del generatore a bin era stato
usato per cambiare griglie, smoothing o campionamento.

## Comportamento

- `--depth-bins` attiva `vcc2026.depth_generator.DepthGenerator`.
- Senza il flag rimane il ramo pooled preesistente; resta disponibile anche
  `--gene-dispersion-scale`, introdotto dalla sessione principale.
- Il flag a bin rifiuta `--gene-dispersion` e `--overdispersion`: il braccio
  registrato ha dispersione residua zero e una phi stimata sul pooled
  conterebbe nuovamente una parte dell'eterogeneità spiegata dai bin.
- `fit_h5ad` legge i controlli in un passaggio aggiuntivo, a blocchi di 256
  righe, utilizzando le library già lette dal basal reader. Verifica che
  librerie e somme geniche siano ancora quelle dei controlli letti prima.
- Le due griglie, il criterio RMSE sui controlli e lo smoothing 1% coincidono
  con il candidato sperimentale preregistrato. Un test confronta direttamente
  fit e cellule prodotte con `DepthCandidate` della cartella di ricerca.
- Lo stadio 45 continua a costruire il profilo con `predicted_profile`,
  prima di chiamare il generatore. La maschera observed, gli zeri osservati,
  il clipping e lo spostamento composizionale restano quelli produttivi.
- Diagnostiche: griglia selezionata e RMSE di entrambe, errore pooled al nullo,
  iterazioni/residuo IPF, celle che incontrano i cap, variazione attesa sui
  geni non osservati. Nessuna somma dei gruppi campionati viene prefissata.

## Verifiche eseguite

1. `test_depth_generator.py`: **8 test passati**, 11,336 secondi. Fit streaming
   contro il braccio preregistrato, maschere, supporto nullo, fattibilità IPF,
   rifiuto di dati cambiati, conteggi interi e stocastici, cap, flag e file
   prodotti dallo stadio.
2. `test_bench_generator.py`: **11 test passati**, 15,775 secondi. Conserva
   anche il generatore trial-01 e le modalità esistenti dei banchi.
3. `check_production_parity.py`: pilot **sintetico**, due contesti × tre
   perturbazioni × 37 cellule × 50 geni; tre coppie prima/dopo per Poisson,
   dispersione scalare e dispersione per gene. **Tutti i byte dei tre H5AD
   sono identici**, non soltanto le matrici. Risultato:
   [default_parity_r1/parity.json](default_parity_r1/parity.json).
   Sorgente prima: [production_before_depth.py](production_before_depth.py),
   SHA256 `3f101339af03104cab79dc3c22e8b0598422f1e9aca7d6b82cc2aee40e0757d6`.
4. `test_live_tree.py`: tutti i controlli su moduli/import/chiamanti passano.
   Il solo fallimento dei 11 test è l'indice della cartella di questo report,
   perché il checker considera `git ls-files` e la nuova cartella non è
   ancora in stage. Nessun errore di indice del nuovo modulo.

Nessun pilot su controlli reali o nuovo banco è stato avviato da questa
integrazione. L'uguaglianza verificata della previsione predefinita non
dimostra un vantaggio del nuovo flag sullo score.
