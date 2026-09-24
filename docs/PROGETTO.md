# Mappa del progetto — VCC 2026

**Questo è il punto di ingresso.** Il §0 dice dove siamo oggi, in una pagina; il resto è
riferimento. Come si esegue il lavoro sta in [LAVORO.md](LAVORO.md).

Aggiornata il 2026-09-23 con la pulizia di D-040:
- §0 è nuovo;
- §2, §5 e §6 sono riscritti. Gli strati datati dal 15 al 22 settembre stanno nei
  checkpoint, e la versione precedente di questa pagina è nel tag
  `archivio/pre-pulizia-2026-09-23`;
- §1, §3 e §4 sono invariati, salvo le voci 7 e 20 del §4.

La sera del 23 il §0 è stato aggiornato con il t11, il t12 e i piloti del t14
([CP-0031](checkpoints/0031-t11-punteggio-orion.md)).

## 0. Oggi — notte fra il 23 e il 24 settembre 2026

**Il migliore è il t11: +0,070777, rango 560**
([CP-0031](checkpoints/0031-t11-punteggio-orion.md)). Il set finale arriva il 22 ottobre:
- tre contesti nuovi (D, E, F) e 300 perturbazioni nuove;
- le sottomissioni chiudono il 5 novembre (§1).

### I punteggi ufficiali

| Invio | Che cosa cambia | Generatore | Media | Rango | Evidenza |
|---|---|---|---|---|---|
| trial-01 | trasferimento K562 (`ShrunkTransfer`) × 0,197 | trial-01 | +0,045929 | 446 | [CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) |
| t02 | K562 dalla singola cellula × 1 + termine cis | `ControlModel` | −0,092774 | 764 | [CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md) |
| t03 | come il t02, × 2 | `ControlModel` | +0,019692 | 576 | [CP-0022](checkpoints/0022-previsione-verificata-t03.md) |
| t07 | modello lineare condizionato su bersaglio e contesto | — | −0,016004 | 671 | [CP-0027](checkpoints/0027-t07-punteggio-ufficiale.md) |
| t08 | effetti K562 + CD4, γ = 1, grezzi × 0,197 | trial-01 | +0,060370 | 547 | [CP-0029](checkpoints/0029-t08-punteggio-ufficiale.md) |
| t10 | il t08 senza CD4 | trial-01 | +0,050191 | 570 | [CP-0030](checkpoints/0030-t10-attribuzione-cd4.md) |
| **t11** | il t08 + Orion HCT116, le tre sorgenti a pesi uguali | trial-01 | **+0,070777** | 560 | [CP-0031](checkpoints/0031-t11-punteggio-orion.md) |
| t14 | effetti del t08 × 2,5 | `ControlModel` | +0,064892 | 564 | [CP-0032](checkpoints/0032-t14-controlmodel-fedelta.md) |

In tutti gli invii:
- lo scalato della `mse` vale 0 (tosato);
- quello della fedeltà direzionale è negativo;
- il membro che porta il punteggio è `pds_cosine` (+0,530 scalato nel t11).

Le tabelle per membro stanno nei checkpoint citati.

### Che cosa è in corso

- **t12** = t11 + Orion HCT116 e HEK293T.
  - Ricetta, previsione e testi sono registrati prima della generazione e del punteggio del
    t11 (`reports/prediction_t12_2026-09-23/prediction.json`). La regola d'arresto non scatta:
    le proxy di HEK293T sono 0,78 con K562 e 0,59–0,62 con CD4.
  - Gli effetti per contesto sono pronti.
  - La generazione aspetta spazio su disco (vedi sotto).
- **t14** = `ControlModel` con gli effetti del t08 × 2,5, l'ampiezza scelta dai piloti.
  - Valutato: +0,064892, rango 564. Per la regola scritta prima è **non attribuibile**
    (+0,0045 sul t08).
  - Perde in `pds_cosine` e in fedeltà, guadagna in `nmae` e in `reach`
    ([CP-0032](checkpoints/0032-t14-controlmodel-fedelta.md)).
  - Il t09 (ampiezza 1) non si genera: con 4,5–20 chiamate pagherebbe il silenzio (D-035).
- **t15** = il t11 con ampiezza 0,394 invece di 0,197. Mette alla prova D-006 sul punteggio
  ufficiale: lo 0,197 minimizzava la MSE in pseudobulk, ma lo scalato della `mse` è tosato a 0 in
  tutti gli invii. Previsione registrata prima (+0,060…+0,095, contro il t11). Generazione e
  impacchettamento in corso; l'invio aspetta il via del proprietario.
- **t13** = dispersione per gene nel generatore di trial-01. Si è fermato per la sua regola:
  a effetto nullo fa 5 / 15 / 31 chiamate mediane in A / B / C
  (`reports/dispersion_2026-09-23/RISULTATO_NULLO.md`).
- **Disco:** il 23 sera il proprietario ha svuotato il Cestino, dopo che l'agente vi aveva
  spostato 19 GB rigenerabili (`reports/trial_2026-09-22/autorizzazioni.md`); ora c'è spazio
  per un candidato alla volta.

### Che cosa guida le scelte

- **Misurato.** Il t11 guadagna +0,0104 sul t08, quasi tutto in `pds_cosine` (0,710 → 0,739
  grezzo). Per la regola scritta prima, Orion aggiunge informazione.
  - L'attribuzione non è pulita: insieme a HCT116 sono cambiati i pesi di K562 e CD4, da
    0,433 : 0,567 a 1 : 1 ([CP-0031](checkpoints/0031-t11-punteggio-orion.md)).
- **Misurato.** CD4 porta +0,0102 dei +0,0144 guadagnati dal t08.
  - È una descrizione, non un verdetto: la regola scritta prima dà «non attribuibile», per
    0,0002.
  - CD4 è l'unico fattore che migliora insieme PDS, MSE e `reach`
    ([CP-0030](checkpoints/0030-t10-attribuzione-cd4.md)).
- **Misurato.** La fedeltà direzionale non si muove con gli effetti: vale 0,458–0,461 in
  trial-01, t10, t08 e t11, sotto la base ufficiale di 0,5123.
  - Nel t11 il generatore di trial-01 chiama in mediana 543 / 582 / 764 geni per bersaglio
    in A / B / C, per l'83–85% «in su» (`reports/prediction_calls_2026-09-23/`).
  - A effetto nullo ne chiama 462 / 453 / 684 (`reports/generator_null_2026-09-17/`);
    `ControlModel` 0 (piloti del t14).
- **Contraddetto dal t14.** Si pensava che in questa famiglia la fedeltà misurasse la
  precisione delle chiamate spurie del generatore, e che si spostasse cambiando il generatore.
  Con `ControlModel` le chiamate spurie sono quasi zero, ma la fedeltà scende a 0,447
  ([CP-0032](checkpoints/0032-t14-controlmodel-fedelta.md)). Restano aperte due letture: il
  segno dei nostri effetti trasferiti sui geni chiamati, o il silenzio sui bersagli con molti
  geni veri.
- **Misurato.** Chi non chiama geni prende fedeltà 0 (D-035). Un generatore pulito serve
  solo insieme a effetti che producano chiamate con il segno giusto.
- **Misurato.** La gara è letta con 10x Flex, a sonde. A, B e C si somigliano fra loro più
  che alle sorgenti pubbliche in 3' ([CP-0028](checkpoints/0028-cd4-sorgente-flex-trasferimento.md)).
  Le identità di linea sono ipotesi.

### Il prossimo passo

**Proposta**, da [CP-0030](checkpoints/0030-t10-attribuzione-cd4.md) §6,
[CP-0031](checkpoints/0031-t11-punteggio-orion.md) §6 e dalle regole già scritte:

1. **Inviare il t15**, con il via del proprietario: dice se l'ampiezza da sola alza `nmae` e
   `reach` senza perdere `pds_cosine`, come col t14.
2. **Misurare la direzione degli effetti**, per bersaglio, sui geni che chiamiamo. Il t14 mostra
   che la fedeltà non dipende solo dal generatore. Si fa nello spazio degli effetti fra
   sorgenti, e con i banchi su cellule vere.
3. **Il t12** (+ HEK293T), e l'ablazione che pulisce l'attribuzione del t11: il t08 con K562 e
   CD4 a pesi uguali.
4. **Preparare il set finale.** Il 22 ottobre bersagli e contesti cambiano, e il percorso di
   [LAVORO.md](LAVORO.md) §1 va rieseguito su di essi:
   - stadi 97 e 102 sulla nuova lista di bersagli (D-039, D-041). Lo stadio 102 legge per
     intero i file di Orion: alcune ore per linea;
   - identità dei contesti con gli stadi 85 e 99.

Ogni invio consuma quota e passa dall'autorizzazione del proprietario.

## 1. Il problema

Bisogna prevedere come cambia l'espressione genica di una cellula quando si spegne uno
di 300 geni, in tre tipi cellulari (A, B, C) mai visti prima. Della gara riceviamo solo
le cellule **non perturbate** dei tre contesti: 18.400 cellule ciascuno. Nessun esempio
di perturbazione, in nessuno dei tre. Si chiama previsione *zero-shot*: bisogna
imparare altrove e trasferire qui.

La classifica finale dipende solo dal set finale, su tre contesti diversi (D, E, F) e
300 perturbazioni nuove, rilasciato il 22 ottobre 2026. Le sottomissioni chiudono il
5 novembre 2026. Formato, metriche e setup: `README.md`.

## 2. Dove siamo

| Fase | Stato | Evidenza |
|---|---|---|
| Ambiente, CLI, dati di controllo, contratto di sottomissione e di punteggio | fatto | [SOTTOMISSIONE.md](SOTTOMISSIONE.md), `reports/scorer/vcc2026_contract.json` |
| Impacchettamento in memoria limitata (stadio 48) | fatto: 0,52 GiB di picco contro i 33,5 di `vcc prep` | [CP-0005](checkpoints/0005-packaging-streaming-trial01.md) |
| Prima sottomissione, trial-01 | +0,045929 | [CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) |
| Pipeline a singola cellula su Colab: K562 letto per intero, `ControlModel`, DE veloce identico allo scorer, banchi a sei metriche | fatto | [CP-0020](checkpoints/0020-singola-cellula-cis-generatore.md), [CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md) |
| Ancore ufficiali risolte da due invii valutati | fatto; reggono su sei invii | [CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md), [CP-0029](checkpoints/0029-t08-punteggio-ufficiale.md) |
| Predittore neurale condizionato | scartato dalla sua regola; il lineare inviato (t07) peggiora | [CP-0026](checkpoints/0026-predittore-neurale-condizionato.md), [CP-0027](checkpoints/0027-t07-punteggio-ufficiale.md) |
| Contesti A/B/C: saggio 10x Flex, impronte genetiche | misurato; le identità di linea restano ipotesi | [CP-0028](checkpoints/0028-cd4-sorgente-flex-trasferimento.md) |
| Trasferimento dello stesso bersaglio da più sorgenti (K562, CD4, Orion) | t11 migliore (+0,070777); t12 registrato prima, da generare | [CP-0028](checkpoints/0028-cd4-sorgente-flex-trasferimento.md), [CP-0029](checkpoints/0029-t08-punteggio-ufficiale.md), [CP-0030](checkpoints/0030-t10-attribuzione-cd4.md), [CP-0031](checkpoints/0031-t11-punteggio-orion.md) |
| Generatore, cioè la fedeltà direzionale | aperto: t13 fermato dalla sua regola; t09 e t14 in coda su Colab | `reports/dispersion_2026-09-23/` |
| Esperimenti in pseudobulk (benchmark modulare, GO slim, SVD, gate) e infrastruttura degli agenti (orchestratore, catena di cicli) | chiusi; codice archiviato | [CP-0011](checkpoints/0011-primo-benchmark-modulare.md)–[CP-0019](checkpoints/0019-catena-cicli-guardiano.md), [ARCHIVIO.md](ARCHIVIO.md) |
| Set finale D/E/F | esce il 22 ottobre; invii fino al 5 novembre | §1 |

## 3. Cosa sappiamo, e cosa lo sostiene

La tabella raccoglie le misure fino al 17 settembre; quelle successive stanno nel §0 e nei
checkpoint da [CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md) in poi.

La colonna "tipo" è la parte importante. Una **misura** è un numero che si può
ricalcolare. Un'**interpretazione** è una lettura di quel numero. Un'**ipotesi** non è
stata ancora messa alla prova.

| Cosa sappiamo | Tipo | Evidenza |
|---|---|---|
| I controlli ufficiali sono 18.400 × 18.533 per contesto, conteggi interi, UMI mediani 20.109 / 19.946 / 20.034 | misura | `reports/data_audit/audit.json` |
| Il pannello dei 300 bersagli è espresso in tutti e tre i contesti: 288/300 sopra 5 CPM, solo 3 sotto 1 CPM in almeno uno | misura | `reports/candidate_verification/coverage_summary.json`, `docs/revisione_analisi_2026-09-11.md` §2 |
| Nessuno dei 300 bersagli compare nei pannelli *essential* di K562 e RPE1 (0/300, per simbolo e per ENSG), dove il caso ne farebbe attendere una trentina | misura | come sopra |
| Selezionare sorgenti esterne per "perturbazioni forti" seleziona sull'esito: sovrarappresenta gli effetti facili e gonfia quello che il modello sembrerà saper fare | interpretazione | `docs/data_strategy_2026-09-11.md` §3 |
| A è di lignaggio linfoide T, B epiteliale-mesenchimale, C epiteliale squamoso | interpretazione (su marcatori misurati) | `reports/context_identity/markers.csv` |
| Nessuno dei tre contesti è eritroide o pluripotente: K562, H1, KOLF2.1J e HIPSCI sono tutti di lignaggio non corrispondente | interpretazione | come sopra |
| K562 genome-wide copre 272/300 bersagli, ma la risposta stimabile è povera: mediana 5 geni DE per riga, 37 righe a zero | misura | `docs/revisione_analisi_2026-09-11.md` §4 |
| Quattro delle sei metriche misurano direzione o ordinamento; la MSE normalizzata non scende sotto 0, la NMAE si ferma a −6 | misura, dal pacchetto installato | `reports/candidate_verification/scorer_clamp_check.json` |
| L'effetto predetto è misurato contro le cellule di controllo **reali** (`control_source: real`): una differenza sistematica fra cellule generate e NTC reali diventa DE fittizio in tutte e 300 le perturbazioni | misura (configurazione) + interpretazione | `reports/scorer/vcc2026_contract.json` |
| CD4 (GSE314342) ha 297/300 bersagli in libreria e 293 osservati, ma solo 239 con almeno 30 cellule e 147 con almeno 100 | misura | `reports/candidate_verification/panel_coverage.csv` |
| Orion HCT116 ha 300/300 in libreria e 168 osservati nel solo Batch1, tutti sotto le 30 cellule | misura | `reports/candidate_verification/coverage_summary.json` |
| H1 2025 condivide 25/300 bersagli, e localmente non c'è la matrice RNA: solo quattro CSV di metadati | misura | `C:/Users/ferra/vcc2026-data/external/vcc2025/` |
| La macchina ha 8,4 GB di RAM; il disco libero oscilla (28,1 GB l'11 settembre, 33,7 GB il 12): gli atlanti completi non ci stanno comunque | misura | `reports/candidate_verification/hardware.json`, `reports/grok_verification/hardware.json` |
| L'estrazione remota mirata funziona: 64 cellule CD4 estratte con 92 MB di traffico | misura | `reports/candidate_verification/pilot/cd4_D1_Rest_64.manifest.json` |
| **Trasferire una risposta a piena ampiezza è peggio che non prevedere nulla**: MSE 1,162 volte quella del nullo da K562 a RPE1, 1,535 fra due esperimenti nella stessa linea K562 | misura | `reports/pipeline/transfer_experiment.json` |
| All'ampiezza calibrata su bersagli tenuti fuori (α = 0,25 fuori linea, 0,50 stessa linea) l'MSE scende a 0,990 e 0,922 del nullo: il guadagno c'è, ed è dell'1,0% e del 7,8% | misura | come sopra |
| L'α scelto in validazione incrociata coincide con l'α oracolo (0,25 vs 0,216; 0,50 vs 0,472): il protocollo di calibrazione funziona | misura | come sopra |
| La correlazione cross-lineage held-out è 0,0947 [0,0891–0,0997]; quella di stessa linea 0,1693 [0,1589–0,1816]. Il trasferimento fuori lignaggio conserva circa il 56% di un tetto già basso | misura (bootstrap su bersagli) | come sopra |
| L'accordo di segno sui geni con \|log2FC\|≥0,5 è 0,555 fuori lignaggio e 0,650 nella stessa linea | misura | come sopra |
| Nel pseudobulk gli effetti **non** sono piccoli: il 23,3% delle coppie bersaglio-gene in RPE1 supera 0,5 log2FC (8,1% in K562) | misura | [CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §3.3 |
| In tutte e tre le fonti locali l'effetto mediano è **più piccolo del proprio errore standard** (\|Δ\|/SE fra 0,795 e 0,945) | misura | `reports/pipeline/signature_qc.json` |
| I file `*_raw_bulk_01.h5ad` contengono **medie per cellula**, non somme: `X × num_cells_filtered` torna intera. Leggerli come conteggi gonfia l'errore di Poisson di ~13× | misura | [CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §3.1 |
| Su dati reali NTC-contro-NTC lo scorer non produce quasi falsi positivi: 5 perturbazioni su 6 escluse per "empty gate", Jaccard 0,000, PDS esattamente 0,500 | misura, scorer ufficiale | `reports/pipeline/null_calibration_A.json` |
| **Codice e pesi non si consegnano.** Solo i finalisti devono pubblicare una descrizione di alto livello del metodo. Le sottomissioni sono **due** al giorno, una sola in volo per squadra | misura (regolamento ufficiale, letto il 2026-09-12) | [SOTTOMISSIONE.md](SOTTOMISSIONE.md) §1 |
| L'α di trasferimento K562 → RPE1 è 0,1974, non 0,25: il valore precedente era il punto di griglia più vicino. MSE fuori campione 0,98991 del nullo, IC95 [0,98866, 0,99114]; a piena ampiezza 1,16228 | misura (CV annidata, 2.350 bersagli) | `reports/trial_2026-09-12/calibration_c002.json` |
| Lo **shrinkage per gene è quasi inattivo**: `prior_sd` = 4 batte «nessuno shrinkage» di 0,00003 in MSE cross-validata. La compressione utile è tutta nell'ampiezza globale | misura | come sopra |
| Una previsione completa a densità realistica pesa 2,08·10⁹ valori memorizzati, 5.789 per cellula: il **44% del tetto**, non il 90% che darebbe submettere il profilo medio | misura | `reports/trial_2026-09-12/resources.json` |
| `vcc prep` carica l'intera matrice in memoria: 8,60 byte per valore memorizzato misurati, 22,19 GiB di picco per trial-00 secondo il modello della CLI stessa, contro 7,81 GiB totali di macchina. **`prep_memory_warning` non scatta su Windows** perché dimensiona contro `os.sysconf` | misura | [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.5 |
| Quel limite è di `vcc prep`, non del problema: convalidando e scrivendo a blocchi, trial-01 si impacchetta con **0,519 GiB di picco** contro i 33,49 del modello, sulla stessa macchina, con le stesse 24 convalide | misura | [CP-0005](checkpoints/0005-packaging-streaming-trial01.md) §3.1 |
| Il payload del `.vcc` porta `X/data`, `X/indices` e `X/indptr` **identici bit a bit** all'input; l'unica trasformazione è l'indice di `obs`, sostituito con `'0'..'n-1'`, che è ciò che fa anche `vcc prep` | misura | come sopra, §3.3 |
| La regola ufficiale «nessuna perturbazione tutta a zero» è **globale, non per contesto**: `vcc prep` accetta un bersaglio azzerato in un solo contesto | misura, sul comportamento di `prep` | come sopra, §3.5 |
| Gli offset CSR di una sottomissione completa arrivano al 97% del tetto di int32: `SubmissionWriter` li scriveva in int32 e avrebbe avvolto in silenzio su una previsione un filo più densa | misura, difetto corretto | [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.6 |
| Il generatore produce il 4–6% di geni rilevati in più dei controlli reali **anche a effetto previsto zero**, mentre i CV di libreria e di rilevazione coincidono. Il log2FC efficace mediano dopo calibrazione è 0,0246 (1,7%), il massimo su un gene 0,776 (1,71×) | misura | `reports/trial_2026-09-12/q01pilot_generation_diagnostics.json` |
| Un contesto scambiato è rilevabile: somiglianza col proprio basale 0,999999 contro 0,888–0,928 fra basali diversi. La convalida di formato non se ne accorgerebbe | misura | `reports/trial_2026-09-12/q00full_validation.json` |
| Su 160 bersagli casuali, K562 → RPE1, MSE/nullo di modular_frozen 0,976 e 0,974 contro 0,994 e 0,996 di ShrunkTransfer (due seed); RPE1 → K562 a α prefissato 1 tutti i bracci sopra 1; universo 6700/18533; picco RSS 0,47 GiB. Non è un punteggio VCC | misura | `reports/benchmark_2026-09-14/comparison_table.md`, [CP-0011](checkpoints/0011-primo-benchmark-modulare.md) |
| Con tre contesti (K562, RPE1, HepG2) la differenza appaiata modular_frozen − ShrunkTransfer e **positiva in tutti e tre i fold** (+0,441 / +0,082 / +0,295, IC95 senza zero): il segno misurato in CP-0011 su due contesti si inverte. Universo 6477/18533; 2.315 bersagli condivisi dai tre contesti (JSON della singola esecuzione) | misura | `reports/benchmark_3ctx_2026-09-14/summary.json`, [CP-0013](checkpoints/0013-hepg2-terzo-contesto.md) |
| Su cellule HepG2 reali, cambiare il **solo** generatore porta il Jaccard sui geni significativi da 0,003 a 0,120 su un predittore nullo, e azzera la direction fidelity; il predittore domina invece la PDS (0,738 contro 0,425). Metriche grezze, 25 bersagli, nessuna ancora | misura | `reports/hepg2_2026-09-14/generator_x_predictor.json`, [CP-0013](checkpoints/0013-hepg2-terzo-contesto.md) |
| Il braccio con le 140 colonne GO **permutate** fra i geni va come quello con l'annotazione vera (|differenza| <= 0,023 sulla base congelata): il legame gene-annotazione non porta segnale in questo disegno | misura | `reports/go_slim_2026-09-15/summary.json`, [CP-0014](checkpoints/0014-go-slim-e-gpu.md) |
| Su matrici di risposta reali una SVD randomizzata di rango 16 e 11,9x piu veloce a 320 righe e 42,2x a 1.280, con l'1,3-1,6% di errore sui valori singolari; il rango 16 cattura il 25-30% della varianza | misura | `reports/gpu_2026-09-15/gpu_readiness.json`, [CP-0014](checkpoints/0014-go-slim-e-gpu.md) |
| Sulla matrice di training 320 × 6.477 del fold K562+RPE1 → HepG2, rango 16: randomizzata 9,74× sulla sola SVD, errore rel. sui valori singolari 1,05%, ma le due ricostruzioni di rango 16 differiscono del 18,5% (angolo max 39°); il rango 16 cattura il 50% della varianza di *questa* matrice | misura | `reports/svd_2026-09-15/factorization_comparison.json`, [CP-0015](checkpoints/0015-svd-randomizzata-e-rango.md) |
| Sostituzione randomizzata vs esatta sulle predizioni (48 righe, stessi split): 4 fold fuori dalla banda prefissata 0,01, tutti frozen con contesto, segni misti. Verdetto: non compatibile come drop-in. Orologio 331 s → 207 s; picco RSS ~456 MiB in entrambi | misura | `reports/svd_2026-09-15/prediction_comparison.json` |
| Griglia di rango {16,32,64,128}: il lowrank sceglie 64 su tutti i fold seen e perde 0,14–0,35 di MSE/nullo sul test contro {8,16}, IC senza zero nei tre contesti. Il frozen "sceglie" 128 su una griglia interna piatta | misura | `reports/rank_2026-09-15/rank_summary.json` |
| Il gate di espressione non passa la sua regola: «batte ShrunkTransfer in tutti i fold» vale in **1 split su 6** per tutte e tre le varianti. Il permutato batte il gate vero in 2 split su 6 (G1), e il gate costruito sulla sorgente lo batte in 4 su 6 (G1) | misura | `reports/expression_gate_2026-09-16/decision.json` |
| La scelta del gate non è stabile fra due seed che differiscono solo per i 32 bersagli di validazione interna: identità scelta in 23 righe su 27 con seed 2026 e in 7 su 27 con seed 2027 | misura | `reports/expression_gate_2026-09-16/gate_rows.json` |
| Nell'universo del banco (6.477 geni) i geni spenti non ci sono: 0–2 sotto 5 CPM per contesto, minimo 4,3–8,6 CPM. Nei contesti ufficiali è l'opposto: 8.409–8.923 geni su 18.533 sotto 5 CPM e 2.317–2.853 esattamente a zero | misura | `reports/expression_gate_2026-09-16/splits/`, `reports/expression_gate_2026-09-16/context_presence.json` |
| Un gene a 1 CPM è contato 368–389 volte nei controlli di un contesto ufficiale (3,68–3,89·10⁸ molecole su 18.400 cellule): su quella scala uno zero è quasi sempre biologia, non strumento | misura | `reports/expression_gate_2026-09-16/context_presence.json` |
| Le 54 righe dei nove bracci originali del run `x001` sono identiche a quelle di `m002`, differenza assoluta massima 0,0: stesso protocollo, stessi split, stessa metrica | misura | `reports/expression_gate_2026-09-16/decision.json`, campo `reproduction` |
| Il file K562 genome-wide a singola cellula pesa 65.830.941.948 byte, cioè **61,31 GiB** (65,83 GB). Il «61,3 GB» del profilo è la stessa dimensione in GiB, come il 9,9 e l'8,1 degli altri due file Replogle a singola cellula. L'etichetta «65,8 GiB» usata in alcuni documenti è un errore di unità | misura (aritmetica sui byte) | `src/vcc2026/external.py`, [CP-0018](checkpoints/0018-drive-storage-confermato.md) §3.3, [R-013](REGISTRO.md#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb) |
| Le copie su Drive mostrano 61,31 GB e 811,2 MB: coerenti con i byte del catalogo letti in unità binarie. Nessun md5 è stato calcolato su di esse | dichiarazione del proprietario (non misurata dal progetto) + misura (aritmetica) | `configs/remote_catalog.yaml`, [CP-0018](checkpoints/0018-drive-storage-confermato.md) §3.2 |
| Un run remoto vede i file solo sotto `<VCC2026_DATA_ROOT>/raw/`. `skip_complete` ricalcola l'md5 dell'intero file a ogni esecuzione, e con `FETCH_BLOCKS = None` la selezione salta i file presenti e scarica il blocco successivo | interpretazione (codice letto, non eseguito) | `src/vcc2026/remote_catalog.py`, [CP-0018](checkpoints/0018-drive-storage-confermato.md) §3.4–3.6 |

## 4. Cosa non sappiamo

Queste sono le incertezze che contano. Nessuna è stata risolta.

1. **Quanto vale un punto.** Le ancore di replicato `r` restano ignote a noi, ma dal
   13 settembre c'è una strada che non richiede un bundle di valutazione: la classifica
   pubblica mostra, per ogni squadra e metrica, **il grezzo e lo scalato**, e due righe
   con grezzi diversi determinano `b` e `r` di `(u − b) / (r − b)`. Derivazione
   preliminare su due righe per `mse`: `b ≈ 0,996`, `r ≈ 0,022`, che riproduce il nostro
   1,231 → 0. **Non è ancora una misura**: va rifatta su molte righe e per tutte e sei
   le metriche ([CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) §3.5).
   Il 16 settembre la stima è stata estesa alle sei metriche su undici righe
   (`reports/leaderboard_2026-09-16/snapshot.md`): resta un'interpretazione, con i
   limiti scritti lì, finché non viene rifatta su più righe e per contesto.
2. ~~**Se comprimere l'ampiezza convenga davvero**~~ — **parzialmente risolta il
   2026-09-12.** Misurato: a piena ampiezza il trasferimento è peggio del nullo, e
   l'ottimo sta intorno a un quarto dell'ampiezza fuori lignaggio
   ([CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §3.4,
   D-006, D-012). **Resta aperto** il pezzo che conta davvero: la misura è in spazio
   pseudobulk log2FC su K562 e RPE1, non sulle sei metriche VCC e non sui contesti
   A/B/C. Trasferibile è il metodo di calibrazione, non il valore, che rimisurato
   con selezione continua e validazione annidata è **0,1974** e non 0,25
   ([CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.2).
3. **Quanto sono grandi gli effetti da prevedere.** Non lo sappiamo. Che i 300
   bersagli non compaiano in due pannelli *essential* è una misura; dedurne che siano
   non essenziali nei contesti della gara è un passaggio non verificato, e dedurne che
   le risposte siano piccole ne è un secondo. L'essenzialità riguarda la sopravvivenza
   della cellula, non l'ampiezza del cambiamento di espressione: un gene non essenziale
   può muovere molti geni. La mediana di 5 geni DE per riga misurata in K562 dice
   quanto segnale riusciamo a **stimare lì**, con 168 cellule mediane per riga, non
   quanto ce ne sia in A, B o C. Scheda
   [R-004](REGISTRO.md#r-004--docsrevisione_analisi_2026-09-11md).
4. **Se l'asse genico ufficiale sia ricostruibile in identificatori Ensembl.** Due
   documenti dicono il contrario: contraddizione aperta, scheda
   [R-004](REGISTRO.md#r-004--docsrevisione_analisi_2026-09-11md).
5. **Se il CD4 primario trasferisca ad A**, che è un contesto T ma con marcatori
   immaturi (DNTT, RAG1). Ipotesi, non misura.
6. **Se la co-espressione nei controlli predica la direzione della risposta.** È il
   modello a costo zero più attraente, ed è anche quello contestato: la correlazione
   non è causalità, e il segno può venire da regolatori comuni o dalla normalizzazione.
   **Prima misura, 17 settembre:** su 243 bersagli HepG2 la correlazione con l'effetto
   è nulla, 0,0015 di mediana dopo aver tolto 20 PC
   (`reports/coexpression_2026-09-17/summary.json`). Resta non provata sui bersagli non
   essenziali.
7. **Se esista Perturb-seq CRISPRi pubblico in linea T matura o squamosa.** La ricerca
   non è conclusa; la pista più vicina per C, GSE281860, espone conteggi di guide e non
   la matrice RNA. L'incarico preparato il 14 settembre per l'orchestratore,
   `configs/orchestrator/briefs/ricerca-perturbseq-t-squamoso.yaml`, non è mai stato
   avviato ed è archiviato con l'orchestratore (D-040): la domanda resta aperta.
8. **L'efficienza di knockdown nei tre contesti ufficiali**, che non è disponibile.
9. **Se la licenza CC-BY-NC-SA-4.0 di Orion** sia compatibile con le regole della gara.
   Registrata, non verificata.
10. **Quale backend DE useremo davvero.** `cell-eval2` sceglie gpudge (con CUDA), poi
    pdex, poi scanpy, e avverte che i numeri differiscono fra engine. Su questa
    macchina si risolve a `scanpy`. Quattro delle sei metriche ne dipendono, quindi la
    scelta va fatta una volta e dichiarata prima di confrontare una serie di run
    (D-014). Non è ancora stata misurata l'entità dello scarto fra engine.
11. **Se l'α calibrato su K562/RPE1 valga per CD4.** L'α misurato è una proprietà della
    coppia sorgente-destinazione; una sorgente di lignaggio vicino potrebbe darne uno
    molto diverso, ed è il primo controllo da fare quando CD4 sarà ingerito.
12. **Se l'artefatto del generatore superi il segnale che iniettiamo.** Misurato: le
    cellule generate rilevano il 4–6% di geni in più dei controlli reali anche a
    effetto previsto zero, e il log2FC efficace mediano dopo calibrazione è 1,7%.
    Sono quantità diverse e dello stesso ordine; quale domini le quattro metriche DE
    dipende da come lo scorer aggrega, e non è stato misurato. È la ragione principale
    per cui il punteggio di `trial-01-transfer` non è prevedibile da ciò che sappiamo
    ([CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.8).
13. **Se un ricampionamento dei controlli sia ammesso dalle regole.** Le regole dicono
    che i controlli scaricati sono soltanto input del modello e che le previsioni
    devono essere generate soltanto da modelli di machine learning. `trial-00-controls`
    passa la convalida di formato ma non è la previsione di un modello. Registrata in
    D-017, **non risolta**: serve un chiarimento da help@virtualcellchallenge.org o una
    decisione esplicita del proprietario.
14. **Quanto costi davvero `vcc prep` su una macchina adeguata.** Il picco di 22–33 GiB
    viene dal modello di dimensionamento della CLI, non da un'esecuzione nostra: la
    misura che abbiamo è il costo di lettura di anndata, 8,60 byte per valore
    memorizzato. Il numero va confermato la prima volta che `prep` gira per davvero.
15. **Se la decomposizione modulare convenga.** Misurato un proxy su 160 bersagli
    K562/RPE1 ([CP-0011](checkpoints/0011-primo-benchmark-modulare.md)): nella sola
    direzione K562 → RPE1 la base congelata ha un MSE/nullo un po' più basso di
    ShrunkTransfer, con IC che esclude zero su due seed; nella direzione inversa,
    a ampiezza prefissata 1, tutti i bracci perdono contro il nullo. Due contesti
    non identificano `z_c`. Non è un punteggio VCC. Resta **inconcludente**.
16. ~~**Se lo slim GO aggiunga qualcosa al solo basale sui bersagli mai visti.**~~
    **Risolta il 2026-09-15 in senso negativo** ([CP-0014](checkpoints/0014-go-slim-e-gpu.md), D-028):
    B1 non batte B0 e B3 (permutato) va come B1.
17. **Se `n_iter` > 2 della SVD randomizzata basti a rientrare nella banda
    sulle predizioni del frozen.** Misurato solo `n_iter=2`. Non adottata.
18. **Se 2.315 bersagli invece di 160 cambino la selezione di rango.** Il
    disaccordo inner/outer a 160 è già grande; non eseguito.
19. **Se una regola di presenza aiuti dove i geni spenti esistono davvero.** Nel banco
    a tre contesti l'universo non ne contiene (0–2 geni sotto 5 CPM per contesto),
    quindi il gate è stato misurato dove poteva esserlo, non dove servirebbe. Nei
    contesti ufficiali ce ne sono migliaia, ma lì non esistono risposte perturbate con
    cui misurare, e lo scorer dichiara comunque un filtro a 5 CPM
    ([CP-0017](checkpoints/0017-gate-espressione-destinazione.md)).
20. **Se le copie su Drive siano leggibili in tempi utili.** Integrità e percorso sono
    risolti: md5 verificato al download del 15 settembre, nei percorsi attesi
    ([CP-0020](checkpoints/0020-singola-cellula-cis-generatore.md) §3.1). **Risolta il
    17 settembre:** lo stadio 71 ha letto l'intero file dal mount di Colab in 2.548 s
    (24,6 MiB/s), con l'md5 uguale al catalogo
    (`reports/k562_sc_2026-09-17/stage71_x002_report.json`).
21. **Quante chiamate DE servono in `val`.** La FID premia le chiamate con il segno
    giusto e punisce il silenzio. Le docstring dello scorer indicano che il 12–30% dei
    bersagli ha meno di 10 geni significativi e che alcuni ne hanno più di 500. Quale
    ampiezza del predittore dia un numero di chiamate adeguato è da misurare nei banchi
    73 e 75 (D-035).

## 5. Il prossimo passo

Sta nel §0. Fino al 22 settembre qui si accumulavano i passi datati, uno sopra l'altro. La
loro storia è nei [checkpoint](checkpoints/INDICE.md); il testo com'era si legge con
`git show archivio/pre-pulizia-2026-09-23:docs/PROGETTO.md`.

## 6. Percorso di lettura

Per lavorare bastano i primi tre punti. Gli altri servono quando un compito li richiede.

1. Questa pagina, §0.
2. [LAVORO.md](LAVORO.md): il percorso vivo, i comandi, le regole dell'invio e di Colab.
3. [CP-0028](checkpoints/0028-cd4-sorgente-flex-trasferimento.md),
   [CP-0029](checkpoints/0029-t08-punteggio-ufficiale.md) e
   [CP-0030](checkpoints/0030-t10-attribuzione-cd4.md): sorgenti per bersaglio, Flex, t08
   e t10.
4. [CP-0020](checkpoints/0020-singola-cellula-cis-generatore.md) e
   [CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md): la pipeline a singola
   cellula, le ancore ufficiali, e perché il numero di chiamate decide la fedeltà.
5. [CP-0026](checkpoints/0026-predittore-neurale-condizionato.md) e
   [CP-0027](checkpoints/0027-t07-punteggio-ufficiale.md): il predittore condizionato
   scartato, e il limite dello stadio 84 per una famiglia di modelli nuova.
6. [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md),
   [CP-0005](checkpoints/0005-packaging-streaming-trial01.md),
   [CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) e
   [SOTTOMISSIONE.md](SOTTOMISSIONE.md): il contratto, l'impacchettamento, il primo
   punteggio.
7. [CP-0001](checkpoints/0001-ricostruzione-stato-2026-09-12.md) e
   [CP-0002](checkpoints/0002-correzioni-dopo-revisione-umana.md): come il progetto ricostruisce
   la propria storia e si corregge. Servono per il metodo, non per lo stato.

I documenti di analisi più vecchi (`docs/data_strategy_2026-09-11.md`,
`docs/revisione_analisi_2026-09-11.md`, `docs/candidate_adversarial_review_2026-09-12.md`,
`docs/revisione_grok_2026-09-12.md`, `docs/BENCHMARK_MODULARE.md`,
`docs/BENCHMARK_TRE_CONTESTI.md`) si leggono con il [registro](REGISTRO.md) accanto:
contengono materiale valido e conclusioni già corrette.

## 7. Come si tiene aggiornato questo sistema

Quattro regole, più due file che le servono: [LAVORO.md](LAVORO.md) si aggiorna quando
cambia il percorso vivo, [ARCHIVIO.md](ARCHIVIO.md) quando un file esce dall'albero (D-040).

1. **Un checkpoint quando succede qualcosa di significativo**, non a ogni modifica.
   Significativo vuol dire: un dataset adottato o scartato, un benchmark completato,
   un'ipotesi contraddetta, un cambio di strategia di modellazione o validazione.

   ```bash
   python scripts/30_new_checkpoint.py --slug benchmark-cd4 --title "Primo benchmark su CD4"
   ```

   Lo script numera da sé, non sovrascrive nulla e aggiorna l'indice. Poi si compila il
   file seguendo le otto sezioni del modello.

2. **I checkpoint non si riscrivono.** Se una conclusione risulta sbagliata si scrive
   un checkpoint nuovo e si compila la colonna "Corretto da" nell'indice. Il
   disaccordo storico resta visibile: serve a capire perché si è cambiata idea.

3. **Questa mappa si aggiorna** quando cambiano lo stato, le incertezze o il prossimo
   passo. Non deve diventare un riassunto di tutto: qui stanno le conclusioni, con un
   link all'evidenza.

4. **Il registro si aggiorna** quando un documento o un dato cambia stato. Se un
   materiale viene contraddetto, si apre una scheda che elenca le affermazioni
   contestate, non si butta via il documento intero.

Controllo di coerenza prima di chiudere una sessione di lavoro:

```bash
python scripts/31_check_docs.py
```

Verifica che i percorsi citati esistano, che ogni checkpoint abbia le sue otto
sezioni, che l'indice corrisponda ai file, e che ogni voce del registro segnata
`da-verificare` o `superato` abbia una scheda compilata.
