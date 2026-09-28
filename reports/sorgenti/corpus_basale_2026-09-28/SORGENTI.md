# Le sorgenti dell'encoder di contesto: una decisione per ciascuna

28 settembre 2026, notte. Scrive il lead (Claude, sessione del proprietario); gli orari sono letti da `date`.

**La richiesta del proprietario** (27/09 sera):
- per ogni sorgente il ruolo, il sottoinsieme, il modo d'integrazione, che cosa è stato davvero eseguito e l'eventuale
  ostacolo;
- se una sorgente non si riesce a provare, resta un esperimento esplicito e motivato, e non si presenta come usata.

**Dove sono il resto:**
- il disegno dell'encoder e della prova:
  [`../encoder_contesto_2026-09-28/DISEGNO.md`](../encoder_contesto_2026-09-28/DISEGNO.md);
- la regola, fissata prima delle corse, e gli esiti:
  [`../encoder_contesto_2026-09-28/RISULTATI.md`](../encoder_contesto_2026-09-28/RISULTATI.md).

Etichette: **misurato**, **interpretazione**, **ipotesi**, **proposta**.

**Stato del documento:** aggiornato durante la notte. Quello che non è scritto qui come misurato non è stato eseguito.

## Tabella

| Sorgente | Ruolo | Sottoinsieme | Integrazione | Eseguito (misurato) | Ostacolo o passo seguente |
|---|---|---|---|---|---|
| Controlli delle nostre sorgenti CRISPRi | pre-addestramento dell'encoder; per K562, CD4, HCT116, HEK293T, KOLF2.1J (r1) e K562 essenziale, VIPerturb-seq, RPE1, HIPSCI (r2) anche contesti della rete | solo controlli: guide non miranti di Replogle (K562 genome-wide ed essenziale, RPE1); righe non miranti CD4 per donatore e condizione; pool NTC di HCT116, HEK293T, KOLF2.1J, A549, VIPerturb-seq (Flex), Southard Hs27 e HIPSCI (in pool e 19 linee) | corpus `ours`, condizione `ours` | corpus: 3.326 profili in 32 contesti (03:18); corse in «Prove» | — |
| Controlli di A, B, C (gara) | pre-addestramento; in produzione, l'embedding dei contesti di gara | 46 sottoinsiemi casuali disgiunti di 400 cellule per contesto (18.400 cellule ciascuno) | nel corpus di `ours`; mai contesti di prova nei disegni E1/E2 | corpus: 138 profili | nessuno |
| DepMap 24Q4 (bulk) | ampiezza: molte linee per le direzioni di variazione basale | 1.667 linee. Escluse alla costruzione A549, HCT116, HEK TE, HepG2, Jurkat e K562; poi le liste di ogni disegno: per CD4 le linee T, per K562 anche P2URK562 | nel corpus di `ours` (piattaforma `bulk`) | corpus: 1.667 profili | bulk: un profilo per linea, nessuna replica dentro il contesto |
| Tahoe-100M, controlli DMSO | ampiezza a cellula singola: 50 linee tumorali, 14 piastre | `drug == DMSO_TF`, somme per linea × piastra da un frammento ogni cinque; gruppi con almeno 50 cellule | corpus `tahoe`, condizione `ours+tahoe` contro `ours` | 434.966 cellule, 650 profili in 48 linee (03:42); corse in «Prove» | l'estrazione completa (tutti i 3.388 frammenti) gira ancora su Kaggle |
| Tahoe-100M, bracci farmacologici | ruolo distinto: la stessa perturbazione in molte linee, per misurare se lo stato basale predice come cambia la risposta, a una scala che il CRISPRi non ha | 73 farmaci con un solo bersaglio annotato che gli schermi CRISPRi silenziano, più controlli positivi; DMSO della stessa piastra | banco T1 ridotto (linee tenute fuori, vicini nello stato basale contro media cieca e scambio); banco T2 (ponte col knockdown) solo disegnato | estratti 10.325 bracci (48 linee con DMSO della stessa piastra); T1 ridotto **non passa** (vicini − cieco −0,137, vicini − scambio +0,060) | non entra nell'encoder; per decisione del proprietario (28/09 mattina) i dati farmacologici non devono prevalere nei dati di addestramento, almeno all'inizio |
| scBaseCount | ampiezza di contesti umani a cellula singola, primari e linee | proposta: umano, 10x, campioni non trattati con provenienza verificabile, tetto per studio | condizioni `ours+scbasecount` e `ours+both` | **nulla**: non è stato scaricato niente | accesso solo da un progetto Google Cloud abbonato al dataset sul Marketplace: serve il proprietario |

## Note per sorgente

### Controlli delle nostre sorgenti CRISPRi (misurato)

| Contesto | Profili | Cellule | Tipo di profilo |
|---|---|---|---|
| K562 genome-wide (Replogle) | 514 | 75.328 | guida non mirante |
| K562 essenziale | 97 | 10.691 | guida non mirante |
| RPE1 | 113 | 11.485 | guida non mirante |
| CD4, tre condizioni | 800 ciascuna | 63.739–69.535 | donatore × guida |
| HCT116, HEK293T | 8 ciascuno | 165.777 e 218.838 | pool |
| KOLF2.1J | 8 | 146.747 | pool |
| A549 (knockout) | 8 | 45.320 | pool |
| VIPerturb-seq (Flex) | 8 | 7.949 | pool |
| Southard Hs27 | 8 | 11.834 | pool |
| HIPSCI in pool (schermi genome-wide) | 2 | 499.998 | pool |
| HIPSCI, 19 linee dello schermo mirato | 8 ciascuna | 86–668 per linea | pool |

- Le guide di Replogle con meno di una cellula filtrata restano fuori (71 su 585 nel K562 genome-wide).
- Geni che una sorgente non misura: NaN, mai 0 (D-009).

### A, B, C

46 sottoinsiemi disgiunti di 400 cellule per contesto, estratti con il seme 20260928. Nei disegni E1/E2 non sono
contesti di prova: sono controlli dati dalla gara (DISEGNO §7, punto 8). In produzione l'encoder li incorpora, ed è un
uso trasduttivo.

### DepMap

Espressione bulk (log1p TPM dei geni codificanti, riportata a TPM), un profilo per linea. Le linee tolte da ogni
disegno sono nel `manifest.json` di ciascun encoder (`pattern_hits`). Nella prova a vuoto delle 03:18:
- il disegno K562 toglie anche `P2URK562`;
- il disegno CD4 toglie 12 linee T.

### Tahoe DMSO

**Misurato.**
- 678 frammenti su 3.388 (uno ogni cinque, in ordine di piastra), letti con richieste a intervalli di byte: 2,69 GB.
- L'estrattore è verificato al bit su un frammento contro un ciclo per cellula.
- Delle 50 linee, 48 hanno almeno una piastra con 50 o più cellule DMSO.
- Nelle linee di Tahoe-100M non c'è HCT116 (la tabella dei metadati ne elenca 102, i dati ne hanno 50); ci sono A549
  e HepG2/C3A.

**Decisione.** Entra come braccio d'ablazione `ours+tahoe`, mai nella scelta dei geni: i geni li scelgono i corpora
`ours`, così ogni condizione ha gli stessi.

### Tahoe, bracci farmacologici (proposta con una prova in corso)

**Perché un ruolo distinto.**
- I DMSO descrivono lo stato di una linea.
- I bracci misurano la stessa perturbazione in 50 linee, cioè esattamente la variabilità della risposta fra contesti
  che il CRISPRi ci dà solo su 4–7 contesti.
- Non diventano etichette CRISPRi: un farmaco non è un knockdown (bersagli fuori obiettivo, dose, tempo).
- Il disegno completo di codex è in [`../tahoe_bracci_2026-09-28/DISEGNO.md`](../tahoe_bracci_2026-09-28/DISEGNO.md):
  T1, differenze fra linee tenute fuori; T2, ponte col knockdown dello stesso bersaglio.

**Stanotte:** l'estrazione, poi T1 ridotto con la regola scritta prima
([RISULTATI](../tahoe_bracci_2026-09-28/RISULTATI.md)).

### scBaseCount (esperimento esplicito, non eseguito)

**Accesso (misurato sulla documentazione ufficiale).**
- Il bucket vecchio `gs://arc-scbasecount` è chiuso dal 31/03/2026.
- I dati stanno nel bucket del Marketplace `gs://arc-institute-virtual-cell-atlas`, a carico di chi legge
  («Requester Pays»).
- Fino a 2 TB al mese sono gratuiti, ma solo da un progetto abbonato al dataset sul Marketplace
  ([README](https://github.com/ArcInstitute/arc-virtual-cell-atlas/blob/main/scBaseCount/README.md)).
- Il mirror LaminDB punta allo stesso bucket.

Nessuno di questi passi si può fare da qui senza il proprietario: serve un suo account, l'accettazione di termini e
la fatturazione del progetto.

**Metadati.** Per campione: `srx_accession`, organismo, tessuto, malattia, `cell_line`, `perturbation`, `lib_prep`,
chimica 10x, preparazione; il tipo cellulare è per cellula. Sono estratti da un agente (SRAgent). Il README avverte che
la malattia è annotata a livello di studio e può mescolare coorti.

**Il sottoinsieme proposto,** da applicare quando l'accesso ci sarà.
1. Umano; chimica 10x 3' o 5'; lettura dei soli metadati di campione (piccoli) prima di qualunque matrice.
2. Contesti pertinenti: linee cellulari (`cell_line` non vuoto), cellule staminali, cellule immunitarie primarie.
3. Trattamento verificabile. Si tiene un campione solo se `perturbation` è vuoto o «none» **e** il titolo e gli
   attributi SRA del campione non contengono parole di trattamento: treated, stimulated, knockout, CRISPR, siRNA,
   drug, infected, IFN, LPS, dose. «DMSO» e «vehicle» sono ammessi come controlli.
4. Provenienza verificabile: il campione deve avere un GEO GSM o un titolo SRA, e lo studio un GSE. Su un 5 % estratto
   a caso si controlla a mano la corrispondenza con GEO, e si registra il tasso d'errore prima di usare il resto.
5. Bilanciamento: al più 20 campioni e 5.000 cellule per studio; un profilo per campione più sottoinsiemi di 400
   cellule.
6. Esclusioni per disegno: le stesse liste esplicite dell'encoder (`corpus.PRESETS`), più un controllo d'impronta.
   Un campione la cui espressione correla con i controlli di una linea tenuta fuori oltre il massimo osservato fra
   linee diverse si toglie anche se il nome non la dice.
7. Controlli di coerenza: il sesso atteso (XIST, RPS4Y1) contro il donatore o la linea dichiarata; i marcatori di
   lignaggio contro il tipo dichiarato.

**Decisione.** Resta un esperimento esplicito, motivato come fonte di ampiezza a cellula singola alternativa a DepMap
(bulk) e a Tahoe (solo linee tumorali). Non è usato e non va presentato come usato.

### Altre sorgenti nominate dal proprietario

| Sorgente | Stato stanotte |
|---|---|
| HIPSCI | controlli nel corpus (in pool e 19 linee); le due schermate genome-wide sono contesti della rete r2; gli effetti per linea dello schermo mirato sono in stima (per le coppie E2 fra donatori) |
| VIPerturb-seq | nel corpus e contesto della rete r2; tetto di rumore misurato ([ponte Flex](../ponte_flex_2026-09-28/RISULTATI.md)) |
| Southard Hs27 | nel corpus; CRISPRa, quindi fuori dalla rete |
| HepG2 (Nadig) | banco F2 con lo scorer vero; fuori da DepMap per nome. Tahoe ha HepG2/C3A: va escluso quando HepG2 fa da prova |
| Jurkat | non ingerito stanotte |

## Prove (misurato, 28/09 mattina)

- **Prima tornata dell'encoder, parte Orion** ([RISULTATI](../encoder_contesto_2026-09-28/RISULTATI.md)):
  - non passa;
  - contro `none` i guadagni sono di un millesimo di skill (`ours+tahoe` +0,0011, `pca` +0,0012, `ours` +0,0003
    su HCT116);
  - con l'embedding di un'altra linea la rete sta **meglio** che con quello giusto, per ogni condizione;
  - E2 non passa.

  La parte K562 e CD4 è finita su Kaggle ma non era ancora scaricata alle 10:35.
- **T1 ridotto sui farmaci** ([RISULTATI](../tahoe_bracci_2026-09-28/RISULTATI.md)): lo stato basale porta
  informazione (vicini giusti meglio di quelli di un'altra linea), ma copiare le linee simili perde contro la media di
  tutte. Serve un modello che usi tutte le linee e impari solo la correzione.
- **La rete con più contesti CRISPRi (r2)**: in corsa su Kaggle dalle 10:06.

**Decisione per sorgente, allo stato di stamattina.**

| Sorgente | Decisione |
|---|---|
| Controlli CRISPRi, A/B/C, DepMap | restano il corpus di base |
| Tahoe DMSO | resta come braccio d'ablazione: su HCT116 aggiunge poco, senza che il contesto giusto conti |
| Tahoe, bracci farmacologici | fuori dall'encoder e senza peso dominante, per decisione del proprietario |
| scBaseCount | esperimento esplicito, bloccato dall'accesso |

## Aggiornamento del 28/09 pomeriggio (misurato)

- **La prima tornata dell'encoder è completa** e non passa la regola per nessuna condizione
  ([RISULTATI](../../modelli/encoder_contesto_2026-09-28/RISULTATI.md)):
  - su CD4, per tutte le condizioni, l'intervallo contro `none` sta sotto −0,002 (`ours` −0,055);
  - su HCT116 e K562 l'embedding di un'altra linea fa meglio di quello giusto.
- **Con i contesti di r2 l'encoder crolla**, `ours` − `none` −0,66 su HCT116
  ([r2](../../modelli/rete_contesti_r2_2026-09-28/RISULTATI.md)).
- **Tahoe DMSO:** l'estrazione completa di Kaggle è finita (2.205.786 cellule DMSO in 1.850 frammenti su 3.388,
  [RISULTATI](../tahoe_dmso_2026-09-28/RISULTATI.md)). Resta sul conto Kaggle; il corpus di stanotte usa il
  sottoinsieme.

**Decisione per sorgente, aggiornata.** Nessuna sorgente del corpus ha mostrato un contributo che passi dall'embedding
giusto. Il corpus resta utile, ma questo encoder congelato, innestato così, non è la via. La decisione su come usare
queste sorgenti (per esempio la rete relazionale della scheda R-V2, o l'azione 6 della scheda R-REV) è del
proprietario.
