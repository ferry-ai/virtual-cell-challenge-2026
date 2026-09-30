# Emendamento prima dell'esecuzione: usare tutta la verità esclusa

29 settembre 2026, 18:52 CEST, prima di qualsiasi scoring della griglia di
`PROTOCOLLO_GENERATORE.md`. Motivo emerso dalla lettura del codice, non da un risultato.

Il vecchio banco divideva le cellule vere in due per costruire un'ancora di replica locale.
Qui la selezione usa pendenze ufficiali già congelate: dimezzare anche la verità riduce
la potenza DE senza proteggere da leakage, dato che nessuna risposta HepG2 entra nel
predittore o nei parametri generativi. Si useranno quindi **tutte le cellule disponibili
di ciascun bersaglio tenuto fuori**, con gli stessi 2.000 controlli in ogni braccio.

Restano invariati split di bersagli sviluppo/verifica, griglia, semi, 400 cellule previste,
metrica di ordinamento, bootstrap e regola di promozione. Si conservano tutti i sei grezzi.
Non si calcola un punteggio con ancore locali costruite dalla verità intera contro se stessa:
una simile "replica" non sarebbe indipendente. Eventuali misure separate metà-contro-metà
sono diagnostiche e non scelgono il candidato.

Questa scelta corregge un costo di potenza del disegno precedente. Non elimina i limiti
di contesto, pannello essenziale, asse genico o profondità sperimentale.
