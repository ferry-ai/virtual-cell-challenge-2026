# piani — schede operative modificabili

L'indice è [PIANI.md](../PIANI.md). Qui si legge e si aggiorna soltanto la scheda
del lavoro scelto. Si applicano CLAUDE alla radice e [docs/CLAUDE.md](../CLAUDE.md).

| Scheda | Ambito |
|---|---|
| [dati-affidabilita.md](dati-affidabilita.md) | R-DATI: sorgenti, controlli, repliche, rumore e dati ponte |
| [trasferimento-modelli.md](trasferimento-modelli.md) | R-MODELLI: programmi, contesto, bersagli nuovi, confronti |
| [switch-distribuzioni.md](switch-distribuzioni.md) | R-SWITCH: soglie, intensità e quote di cellule rispondenti |
| [invii-finale.md](invii-finale.md) | S-INVII: prove di validazione e preparazione del set finale |

## Regole delle schede

- Stati ammessi: **aperto**, **in corso**, **in attesa** (dipendenza esplicita),
  **chiuso** (evidenza ed esito richiesti). «Promettente» è una priorità di ricerca,
  non uno stato di validazione. Non dedurre stato o assegnatario da un vecchio report.
- Ogni scheda mantiene ID, data di aggiornamento, stato, assegnazione, prossimo
  passo concreto, dipendenze, criterio di chiusura, evidenze e alternative.
- Prima della presa in carico seguire PIANI §3. Se il piano è condiviso, aggiungere
  una riga per sottoattività disgiunta; non sostituire l'assegnatario di un altro agente.
- Non copiare punteggi, comandi o intere analisi: collegare la fonte competente.
  I protocolli congelati e le misure vanno in report nuovi; la scheda non li riscrive.
- Nuove schede: scegliere un ID e un nome non occupati, controllare di nuovo prima
  di crearli, aggiungere il link qui e nell'indice. La voce `docs/piani/` nel registro
  copre queste schede omogenee; una chiusura va annotata anche nella nota del registro.
- Conservare le schede chiuse con esito e condizione di riapertura. Nessuna
  archiviazione di file, modifica del codice o riattivazione di sottosistemi è implicita.
