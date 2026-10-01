# Il caricatore dei lotti dopo il primo training: dove va il tempo, e la correzione

1 ottobre 2026, Claude Code (sessione `07ebf08b`). Nasce dall'incidente `E-20261001-001`: nel primo training su GPU
(`rlab-cellnet-r1`, [ESITO](../../cellnet_tecnico_2026-10-01/ESITO.md)) la GPU ha aspettato i dati per l'87% del tempo
e il braccio `ident` è stato ucciso per memoria.

| File | Che cosa |
|---|---|
| `profile_loader.py` | La misura: codice di un kernel Kaggle **CPU** (nessuna quota GPU) sugli shard di training del pre-passo r3 |
| `esito_profilo_r1/` | `profile.json` e il log del kernel `rlab-loader-profile-r1` (01:16-01:30 UTC), con manifest e metadati |
| `esito_prova_cpu_r1/` | La prova del codice corretto su Kaggle CPU (`rlab-cellnet-smoke-r1`, 01:46-02:12 UTC, commit `d4a29e5`): un processo, due bracci, tre processi di caricamento, sugli shard reali del primo training; output piccoli con manifest |

## La prova su CPU del codice corretto (misurato)

- Il kernel finisce con codice 0, e i due bracci scrivono `eval.json` e `model.pt`. Memoria del processo principale:
  picco 5,4 GB.
- Il training non fa passi. Su CPU la riserva della valutazione, 3.898 s, supera il budget di 30 minuti: il calcolo
  dei modelli su CPU costa circa 21 ms per cellula, contro le letture.
- La valutazione con tre processi di caricamento gira sugli shard veri (64.861 cellule in 1.136 s), ma su CPU si ferma
  alla scadenza: 305 gruppi T su 400 non raggiunti.
- Ne segue una correzione prima del secondo training. Le cellule T (bersagli nascosti nei contesti di training) stanno
  a poche centinaia per shard, e la valutazione leggeva ogni shard per intero. Ora uno shard con le cellule di
  valutazione entro l'8% delle sue si legge riga per riga (`cellnet.read_csr_rows`, stessa matrice). La riserva si
  stima dai byte che la valutazione decomprime, al ritmo misurato dalla sonda, e dal calcolo per cellula dopo il primo
  blocco.

## Che cosa è stato misurato

Su shard reali di HIPSCI targeted (244 MB, 20.000 cellule, circa 113 milioni di valori non nulli, gzip) e sui flussi di
lotti del codice del primo training (`profile.json`). Ogni misura usa shard che nessuna misura precedente aveva letto.

| Misura | Valore |
|---|---|
| Lettura grezza dei file | 118 MB/s da sola, 385 MB/s con quattro letture insieme: il disco non limita |
| `h5py` legge `X` (decompressione gzip), per shard | 6,1-10,0 s |
| `read_csr` com'era (COO, somma, ordinamento), per shard | 14,1-16,7 s |
| `read_csr` con il filtro diretto del CSR, per shard | 7,8-10,7 s, stessa matrice (`same_matrix` vero su 3 shard) |
| Flusso in un processo, `read_csr` com'era | 932 cellule/s; letture il 97% del tempo |
| Flusso in un processo, filtro diretto | 2.025 cellule/s (2.316 nella seconda metà della finestra) |
| Flusso con 2 processi di caricamento, filtro diretto | 2.408 cellule/s (2.672); memoria dei processi 7,7 GB |
| Flusso con 3 processi di caricamento, filtro diretto | 2.786 cellule/s (3.328); memoria dei processi 11,4 GB |

## Che cosa ne segue

- Misurato: il passaggio per COO e l'ordinamento costava 6-8 s per shard. Ora il costo è quasi tutto la decompressione
  gzip, su un core per processo.
- Interpretazione: nel primo training due bracci, ciascuno con due processi di caricamento, si dividevano 4 CPU. Ogni
  braccio riceveva circa 630 cellule/s, cioè circa 1.260 in tutto, in linea con quattro processi a meno di un core
  ciascuno del lettore com'era.
- Correzione, nel codice di
  [risposta_biologica_2026-09-30](../../risposta_biologica_2026-09-30/train_cellnet.py):
  - `cellnet.read_csr` col filtro diretto;
  - i bracci in un solo processo sugli stessi lotti (`--arm NAME=CODICE@DEVICE`), così ogni shard si legge una volta
    per tutti i bracci e la memoria non si raddoppia;
  - la valutazione legge gli shard con processi di caricamento (`--eval-workers`);
  - la riserva della valutazione è stimata separando le letture dal resto;
  - il throughput del piano si misura a regime, non sul buffer iniziale.
- Attesa, non misura, per il secondo training: circa 3.000 cellule/s per **ciascun** braccio con 3 processi di
  caricamento, contro le circa 630 del primo. La GPU da sola ne regge circa 3.700 per braccio. Il numero vero sarà nel
  `plan.json` e nel `coverage.json` del secondo training.
