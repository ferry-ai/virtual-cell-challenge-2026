# Addendum: A549 (knockout) come decimo gruppo sorgente

5 ottobre 2026, verso le 18:20 CEST. Claude Code per Alfredo, che ha chiesto in chat di procedere in locale («vai in
locale»).

**Registrato prima di costruire la tabella e prima di ogni numero su A549.** Le soglie non si spostano dopo i
risultati.

## Perché

L'[esito dello stadio 1](ESITO.md) §3.3 mostra che il coseno del profilo aggregato con la verità sale di circa +0,01
per ogni linea sorgente in più, senza saturare a 8. A549 è l'unica linea nuova fra i dati rlab che leggiamo.

**Il dataset:** `davidmaisterx/rlab-a549`, studio `a549_liu_hillsley2026`, 606.075 cellule, 31 frammenti, una sola
condizione. I frammenti sono stati scaricati il 5/10 e la parità della ricevuta è `parity_ok`.

**La modalità è knockout (KO), non CRISPRi.** Anche il KO è una perdita di funzione, ma va dichiarato. Il registro di
Davide lo tiene fuori dal banco per questo motivo.

## Come

- **Tabella `a549_ko`, gruppo `A549`**, sulle sole chiavi del cubo. Il simbolo del bersaglio è mappato alla chiave
  del cubo con la mappa simbolo→chiave del cubo; i simboli ambigui restano fuori.
- **Una sola lettura dei 31 frammenti:**
  - somme dei conteggi per bersaglio e per i controlli NTC sui geni del cubo (asse ufficiale, mapping `unique`,
    `measured`);
  - poi raw = ln(frazione del bersaglio) − ln(frazione dei controlli);
  - SE con le formule di `banco_tipo.key_effects` (φ = 0,2, controlli contati almeno 1.000);
  - shrunk = `z_shrink(raw, SE, 4)`;
  - NaN sui geni non misurati o con frazione dei controlli sotto 1e-6.

  Sono le formule della strada C, non lo stimatore dell'universo di Davide: la differenza è dichiarata.
- **Basale:** log1p della CPM dei controlli NTC di A549 sui geni del cubo.
- **Cubo esteso:** un nuovo layout con link fisici alle 34 tabelle originali più `a549_ko`, il manifest con la tabella
  aggiunta e un `basal.npz` riscritto con la chiave in più. Le tabelle originali non si toccano.

## Misura e regola

- **Stesso codice** ([guadagno.py](guadagno.py): `transfer`, `truth`, `measures`, bootstrap), stesse 5 linee tenute
  fuori, stessi bersagli valutati (scelti con l'hash; il supporto di `all` non cambia la scelta perché A549 si
  aggiunge solo alle sorgenti).
- **Due bracci:** `all` (cubo originale) e `all_a549` (cubo esteso).
- **A549 entra nel candidato di produzione solo se:**
  - la media sulle cinque linee di `all_a549 − all` nel coseno è ≥ **+0,005**;
  - su almeno 3 linee su 5 il limite inferiore all'IC 90% della differenza di coseno è > 0;
  - su nessuna linea l'indice di discriminazione scende di più di **0,005**.

  Altrimenti A549 resta fuori.
- **Si riportano:** la copertura (quanti bersagli valutati A549 misura per linea) e il coseno di A549 da solo sui
  bersagli coperti.

## Previsione (soggettiva)

- **`all_a549 − all`, coseno:** da +0,000 a +0,012, media +0,005. Diluito dalla copertura: A549 non misura tutti i
  bersagli.
- **Fiducia 0,4** che la regola passi.
