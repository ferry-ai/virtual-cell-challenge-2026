# Review del generatore da profili Stack

**Revisione statica, 29 settembre 2026.** Letti `stack_profiles_to_cells.py`,
`test_stack_profiles_to_cells.py`, il produttore `stack_production_infer.py` e
`src/vcc2026/submission.py`. Nessun test, campionamento o job eseguito dall'autore
di questa review. La lead riporta separatamente due test passati.

**Richieste di correzione prima del congelamento:**

1. **P2, identità del contesto.** `read_context` verifica assi e hash ma non
   confronta `complete.json.context` con la chiave usata dal writer. Per ispezione,
   `generate({'B': path_A}, ...)` accetta la fixture A e scrive etichette B.
   I controlli CLI intercettano un percorso diverso da quello registrato; non
   intercettano una registrazione che abbia associato al contesto sbagliato il
   relativo hash. Passare il contesto atteso a `read_context`, verificarne
   l'uguaglianza e aggiungere un test di rifiuto prima della creazione dell'output.
2. **P2, identità del codice di campionamento.** Il controllo di registrazione
   confronta l'hash del generatore, ma `rng_for`, `N_OUTPUT` e `sample_counts`
   provengono da import esterni. Il produttore dei profili controlla già il
   `PILOT_SHA`; questo endpoint non lo controlla. Legare alla registrazione o
   al launcher congelato almeno il helper e il modulo di campionamento effettivi,
   e conservarne gli hash nel manifest. Il test di parità attuale usa lo stesso
   import su entrambi i lati: verifica il percorso di campionamento, non può da
   solo rilevare un cambiamento comune della dipendenza.

La lettura preventiva di tutti i profili rifiuta assi riordinati, byte cambiati,
uscite fuori dal supporto comune, fallback non identico e massa non conservata.
Il writer conserva l'ordine dei geni, scrive blocchi da 400 cellule e adegua la
larghezza degli offset CSR al numero di elementi. Il profilo e la matrice completa
non sono accumulati in memoria; il rename finale avviene soltanto dopo la chiusura
del writer. Il comando CLI richiede registrazione e conferma concatenate ai
manifest. Non sono stati rilevati altri difetti concreti nel percorso previsto.

La review non costituisce una decisione scientifica di promozione né autorizza
produzione: riguarda esclusivamente l'integrità della conversione già registrata.
