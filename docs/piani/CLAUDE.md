# piani — schede operative modificabili

L'indice è [PIANI.md](../PIANI.md). Qui si legge e si aggiorna soltanto la scheda
del lavoro scelto. Si applicano CLAUDE alla radice e [docs/CLAUDE.md](../CLAUDE.md).

L'elenco delle schede, con priorità e dipendenze, è la tabella del §2 di [PIANI](../PIANI.md): non
si ripete qui. Lo stato e l'assegnazione di un piano stanno nell'intestazione della sua scheda, e
solo lì.

Keep only the current mandate, next step, dependencies and closure in a live card.
Dated execution instructions go to `docs/storico/`, with provenance and registry metadata.
R-LEAD owns the implementation sequence; other cards and prompts link to it.

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
  di crearli, aggiungere la riga nella tabella del §2 di PIANI. La voce `docs/piani/` nel registro
  copre queste schede omogenee; una chiusura va annotata anche nella nota del registro.
- Conservare le schede chiuse con esito e condizione di riapertura. Nessuna
  archiviazione di file, modifica del codice o riattivazione di sottosistemi è implicita.
