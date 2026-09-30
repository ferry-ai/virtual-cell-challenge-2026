# Recupero t28 dopo perdita del runtime Colab

29 settembre 2026. **Misurato:** la diagnosi fornita dal proprietario alle
19:58:07 UTC trova assenti H5AD t28, VCC, ambiente Stack e mount Drive;
i processi 29730, 29734 e 37314 sono terminati. Il precedente job070 aveva
completato la generazione delle 360.000 cellule, ma nessun pacchetto finale è
stato recuperato. La diagnosi073 preservata documenta il punto raggiunto, non
la disponibilità attuale di quelle cellule. Il runtime è stato ricreato CPU;
il dispatcher è ripartito alle 20:02:07 UTC.

**Decisione operativa:** rigenerare lo stesso candidato già registrato, senza
modificare effetti, scala, dispersione, semi, numero di cellule, validatori o
criterio di lettura. Il job078 ricrea l'ambiente con il bootstrap r2 già
verificato, in un nuovo output Drive. Il job079 aspetta il termine di078 e
la sua ricevuta `ready.json`, poi esegue t28r2 in percorsi nuovi. Accodato
alle 20:05:16 UTC; accodamento non equivale a completamento.

**Correzione ingegneristica:** prima dello stadio48, la predizione H5AD completa
e i piccoli report di generazione vengono copiati su Drive in
`stage45_checkpoint/`. Ogni file usa una destinazione `.partial`, creazione
esclusiva, SHA256 completo dopo la copia e rinomina; `complete.json` si scrive
soltanto al termine. Anche un'ulteriore perdita del runtime dopo quel punto
consente di riprendere dal packaging. Il precedente tentativo non viene
sovrascritto o cancellato.

Quattro test passati: copia byte esatta, rifiuto di sovrascrittura, preservazione
di una copia parziale, identità AST degli argomenti scientifici agli stadi45/48
e ordine checkpoint prima del packaging. Gli hash sono in `review.json`.
Nessun comando di submission è presente. La copia di t27 già pronta rimane
disponibile; la sua precedente mancata autorizzazione all'invio resta valida.
