# Verifiche e limiti della sessione

- Le fonti web citate in IPOTESI sono state consultate il 24 settembre 2026.
  Alcune pagine Nature, PMC e GEO hanno restituito blocchi di accesso; dove
  necessario sono stati letti estratti indicizzati delle fonti primarie.
  Non è stato completato un audit del codice di stima Mixscale.
- Le correlazioni STAT2/JAK1/STAT1 provengono dal CSV locale già prodotto nella
  sessione precedente; nessun nuovo esperimento su conteggi o training.
- Nessun dataset scaricato. Dimensioni e licenze ancora da verificare sono
  esplicitamente indicate; le raccomandazioni sono priorità di audit.
- Controllo documentale dopo le modifiche: superato, 36 checkpoint coerenti.
  `git diff --check`: superato.
- Suite: 147 test, un errore per `cell_eval2.config` assente e un fallimento
  dell'indice dei report, che usa solo file tracciati in Git. La nuova cartella
  della sessione precedente è ancora non tracciata. La suite era stata avviata
  prima della scrittura di IPOTESI; anche questa nuova cartella non è tracciata.
  Nessuna modifica a produzione o ambiente effettuata per questi esiti.
