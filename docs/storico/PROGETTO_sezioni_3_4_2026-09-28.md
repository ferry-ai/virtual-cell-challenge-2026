# PROGETTO.md, §3 e §4 com'erano fino al 28 settembre 2026

Queste due sezioni stavano in [PROGETTO.md](../PROGETTO.md) dal 12 settembre: la tabella delle
misure fino al 17 settembre (§3) e le 21 incertezze numerate (§4). Il 28 settembre, con la
riorganizzazione di D-046, sono state spostate qui **senza cambiare il testo**; sono cambiati
solo i percorsi, per seguire lo spostamento dei report e di questo file. In PROGETTO restano un
§3 e un §4 nuovi e più corti, con lo stato di ciascuna incertezza al 28 settembre e il rimando
al numero che aveva qui.

- **Stato:** `storico`. Le misure restano vere per ciò che misuravano; diverse righe
  riguardano il pseudobulk e l'infrastruttura del 12–17 settembre, poi archiviati (D-040).
- **Da leggere con:** il [registro](../REGISTRO.md) e i checkpoint citati riga per riga.

## 3. Cosa sappiamo, e cosa lo sostiene

La tabella raccoglie le misure fino al 17 settembre; quelle successive stanno nel §0 e nei
checkpoint da [CP-0021](../checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md) in poi.

La colonna "tipo" è la parte importante. Una **misura** è un numero che si può
ricalcolare. Un'**interpretazione** è una lettura di quel numero. Un'**ipotesi** non è
stata ancora messa alla prova.

| Cosa sappiamo | Tipo | Evidenza |
|---|---|---|
| I controlli ufficiali sono 18.400 × 18.533 per contesto, conteggi interi, UMI mediani 20.109 / 19.946 / 20.034 | misura | `reports/storico/data_audit/audit.json` |
| Il pannello dei 300 bersagli è espresso in tutti e tre i contesti: 288/300 sopra 5 CPM, solo 3 sotto 1 CPM in almeno uno | misura | `reports/storico/candidate_verification/coverage_summary.json`, `docs/storico/revisione_analisi_2026-09-11.md` §2 |
| Nessuno dei 300 bersagli compare nei pannelli *essential* di K562 e RPE1 (0/300, per simbolo e per ENSG), dove il caso ne farebbe attendere una trentina | misura | come sopra |
| Selezionare sorgenti esterne per "perturbazioni forti" seleziona sull'esito: sovrarappresenta gli effetti facili e gonfia quello che il modello sembrerà saper fare | interpretazione | `docs/storico/data_strategy_2026-09-11.md` §3 |
| A è di lignaggio linfoide T, B epiteliale-mesenchimale, C epiteliale squamoso | interpretazione (su marcatori misurati) | `reports/gara/context_identity/markers.csv` |
| Nessuno dei tre contesti è eritroide o pluripotente: K562, H1, KOLF2.1J e HIPSCI sono tutti di lignaggio non corrispondente | interpretazione | come sopra |
| K562 genome-wide copre 272/300 bersagli, ma la risposta stimabile è povera: mediana 5 geni DE per riga, 37 righe a zero | misura | `docs/storico/revisione_analisi_2026-09-11.md` §4 |
| Quattro delle sei metriche misurano direzione o ordinamento; la MSE normalizzata non scende sotto 0, la NMAE si ferma a −6 | misura, dal pacchetto installato | `reports/storico/candidate_verification/scorer_clamp_check.json` |
| L'effetto predetto è misurato contro le cellule di controllo **reali** (`control_source: real`): una differenza sistematica fra cellule generate e NTC reali diventa DE fittizio in tutte e 300 le perturbazioni | misura (configurazione) + interpretazione | `reports/gara/scorer/vcc2026_contract.json` |
| CD4 (GSE314342) ha 297/300 bersagli in libreria e 293 osservati, ma solo 239 con almeno 30 cellule e 147 con almeno 100 | misura | `reports/storico/candidate_verification/panel_coverage.csv` |
| Orion HCT116 ha 300/300 in libreria e 168 osservati nel solo Batch1, tutti sotto le 30 cellule | misura | `reports/storico/candidate_verification/coverage_summary.json` |
| H1 2025 condivide 25/300 bersagli, e localmente non c'è la matrice RNA: solo quattro CSV di metadati | misura | `C:/Users/ferra/vcc2026-data/external/vcc2025/` |
| La macchina ha 8,4 GB di RAM; il disco libero oscilla (28,1 GB l'11 settembre, 33,7 GB il 12): gli atlanti completi non ci stanno comunque | misura | `reports/storico/candidate_verification/hardware.json`, `reports/storico/grok_verification/hardware.json` |
| L'estrazione remota mirata funziona: 64 cellule CD4 estratte con 92 MB di traffico | misura | `reports/storico/candidate_verification/pilot/cd4_D1_Rest_64.manifest.json` |
| **Trasferire una risposta a piena ampiezza è peggio che non prevedere nulla**: MSE 1,162 volte quella del nullo da K562 a RPE1, 1,535 fra due esperimenti nella stessa linea K562 | misura | `reports/storico/pipeline/transfer_experiment.json` |
| All'ampiezza calibrata su bersagli tenuti fuori (α = 0,25 fuori linea, 0,50 stessa linea) l'MSE scende a 0,990 e 0,922 del nullo: il guadagno c'è, ed è dell'1,0% e del 7,8% | misura | come sopra |
| L'α scelto in validazione incrociata coincide con l'α oracolo (0,25 vs 0,216; 0,50 vs 0,472): il protocollo di calibrazione funziona | misura | come sopra |
| La correlazione cross-lineage held-out è 0,0947 [0,0891–0,0997]; quella di stessa linea 0,1693 [0,1589–0,1816]. Il trasferimento fuori lignaggio conserva circa il 56% di un tetto già basso | misura (bootstrap su bersagli) | come sopra |
| L'accordo di segno sui geni con \|log2FC\|≥0,5 è 0,555 fuori lignaggio e 0,650 nella stessa linea | misura | come sopra |
| Nel pseudobulk gli effetti **non** sono piccoli: il 23,3% delle coppie bersaglio-gene in RPE1 supera 0,5 log2FC (8,1% in K562) | misura | [CP-0003](../checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §3.3 |
| In tutte e tre le fonti locali l'effetto mediano è **più piccolo del proprio errore standard** (\|Δ\|/SE fra 0,795 e 0,945) | misura | `reports/storico/pipeline/signature_qc.json` |
| I file `*_raw_bulk_01.h5ad` contengono **medie per cellula**, non somme: `X × num_cells_filtered` torna intera. Leggerli come conteggi gonfia l'errore di Poisson di ~13× | misura | [CP-0003](../checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §3.1 |
| Su dati reali NTC-contro-NTC lo scorer non produce quasi falsi positivi: 5 perturbazioni su 6 escluse per "empty gate", Jaccard 0,000, PDS esattamente 0,500 | misura, scorer ufficiale | `reports/storico/pipeline/null_calibration_A.json` |
| **Codice e pesi non si consegnano.** Solo i finalisti devono pubblicare una descrizione di alto livello del metodo. Le sottomissioni sono **due** al giorno, una sola in volo per squadra | misura (regolamento ufficiale, letto il 2026-09-12) | [SOTTOMISSIONE.md](../SOTTOMISSIONE.md) §1 |
| L'α di trasferimento K562 → RPE1 è 0,1974, non 0,25: il valore precedente era il punto di griglia più vicino. MSE fuori campione 0,98991 del nullo, IC95 [0,98866, 0,99114]; a piena ampiezza 1,16228 | misura (CV annidata, 2.350 bersagli) | `reports/invii/trial_2026-09-12/calibration_c002.json` |
| Lo **shrinkage per gene è quasi inattivo**: `prior_sd` = 4 batte «nessuno shrinkage» di 0,00003 in MSE cross-validata. La compressione utile è tutta nell'ampiezza globale | misura | come sopra |
| Una previsione completa a densità realistica pesa 2,08·10⁹ valori memorizzati, 5.789 per cellula: il **44% del tetto**, non il 90% che darebbe submettere il profilo medio | misura | `reports/invii/trial_2026-09-12/resources.json` |
| `vcc prep` carica l'intera matrice in memoria: 22,19 GiB di picco per trial-00 secondo il modello della CLI stessa, contro 7,81 GiB totali di macchina. **`prep_memory_warning` non scatta su Windows** perché dimensiona contro `os.sysconf` | misura | [CP-0004](../checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.5 |
| Quel limite è di `vcc prep`, non del problema: convalidando e scrivendo a blocchi, trial-01 si impacchetta con **0,519 GiB di picco** contro i 33,49 del modello, sulla stessa macchina, con le stesse 24 convalide | misura | [CP-0005](../checkpoints/0005-packaging-streaming-trial01.md) §3.1 |
| Il payload del `.vcc` porta `X/data`, `X/indices` e `X/indptr` **identici bit a bit** all'input; l'unica trasformazione è l'indice di `obs`, sostituito con `'0'..'n-1'`, che è ciò che fa anche `vcc prep` | misura | come sopra, §3.3 |
| La regola ufficiale «nessuna perturbazione tutta a zero» è **globale, non per contesto**: `vcc prep` accetta un bersaglio azzerato in un solo contesto | misura, sul comportamento di `prep` | come sopra, §3.5 |
| Gli offset CSR di una sottomissione completa arrivano al 97% del tetto di int32: `SubmissionWriter` li scriveva in int32 e avrebbe avvolto in silenzio su una previsione un filo più densa | misura, difetto corretto | [CP-0004](../checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.6 |
| Il generatore produce fra il **2,1% e il 6,3%** di geni rilevati in più dei controlli reali **anche a effetto previsto zero**, con mediana 4,1% (pilota) e 3,7% (run completo) sui 12+12 blocchi campionati — *corretto il 24 settembre: si leggeva «4–6%», la metà alta del range; la correzione del 15 (`fa0b1c6`) non era mai stata unita*, mentre i CV di libreria e di rilevazione coincidono. Il log2FC efficace mediano dopo calibrazione è 0,0246 (1,7%), il massimo su un gene 0,776 (1,71×) | misura | `reports/invii/trial_2026-09-12/q01pilot_generation_diagnostics.json`, `reports/invii/trial_2026-09-12/q01full_generation_diagnostics.json` |
| Un contesto scambiato è rilevabile: somiglianza col proprio basale 0,999999 contro 0,888–0,928 fra basali diversi. La convalida di formato non se ne accorgerebbe | misura | `reports/invii/trial_2026-09-12/q00full_validation.json` |
| Su 160 bersagli casuali, K562 → RPE1, MSE/nullo di modular_frozen 0,976 e 0,974 contro 0,994 e 0,996 di ShrunkTransfer (due seed); RPE1 → K562 a α prefissato 1 tutti i bracci sopra 1; universo 6700/18533; picco RSS 0,47 GiB. Non è un punteggio VCC | misura | `reports/storico/benchmark_2026-09-14/comparison_table.md`, [CP-0011](../checkpoints/0011-primo-benchmark-modulare.md) |
| Con tre contesti (K562, RPE1, HepG2) la differenza appaiata modular_frozen − ShrunkTransfer e **positiva in tutti e tre i fold** (+0,441 / +0,082 / +0,295, IC95 senza zero): il segno misurato in CP-0011 su due contesti si inverte. Universo 6477/18533; 2.315 bersagli condivisi dai tre contesti (JSON della singola esecuzione) | misura | `reports/storico/benchmark_3ctx_2026-09-14/summary.json`, [CP-0013](../checkpoints/0013-hepg2-terzo-contesto.md) |
| Su cellule HepG2 reali, cambiare il **solo** generatore porta il Jaccard sui geni significativi da 0,003 a 0,120 su un predittore nullo, e azzera la direction fidelity; il predittore domina invece la PDS (0,738 contro 0,425). Metriche grezze, 25 bersagli, nessuna ancora | misura | `reports/storico/hepg2_2026-09-14/generator_x_predictor.json`, [CP-0013](../checkpoints/0013-hepg2-terzo-contesto.md) |
| Il braccio con le 140 colonne GO **permutate** fra i geni va come quello con l'annotazione vera (|differenza| <= 0,023 sulla base congelata): il legame gene-annotazione non porta segnale in questo disegno | misura | `reports/storico/go_slim_2026-09-15/summary.json`, [CP-0014](../checkpoints/0014-go-slim-e-gpu.md) |
| Su matrici di risposta reali una SVD randomizzata di rango 16 e 11,9x piu veloce a 320 righe e 42,2x a 1.280, con l'1,3-1,6% di errore sui valori singolari; il rango 16 cattura il 25-30% della varianza | misura | `reports/storico/gpu_2026-09-15/gpu_readiness.json`, [CP-0014](../checkpoints/0014-go-slim-e-gpu.md) |
| Sulla matrice di training 320 × 6.477 del fold K562+RPE1 → HepG2, rango 16: randomizzata 9,74× sulla sola SVD, errore rel. sui valori singolari 1,05%, ma le due ricostruzioni di rango 16 differiscono del 18,5% (angolo max 39°); il rango 16 cattura il 50% della varianza di *questa* matrice | misura | `reports/storico/svd_2026-09-15/factorization_comparison.json`, [CP-0015](../checkpoints/0015-svd-randomizzata-e-rango.md) |
| Sostituzione randomizzata vs esatta sulle predizioni (48 righe, stessi split): 4 fold fuori dalla banda prefissata 0,01, tutti frozen con contesto, segni misti. Verdetto: non compatibile come drop-in. Orologio 331 s → 207 s; picco RSS ~456 MiB in entrambi | misura | `reports/storico/svd_2026-09-15/prediction_comparison.json` |
| Griglia di rango {16,32,64,128}: il lowrank sceglie 64 su tutti i fold seen e perde 0,14–0,35 di MSE/nullo sul test contro {8,16}, IC senza zero nei tre contesti. Il frozen "sceglie" 128 su una griglia interna piatta | misura | `reports/storico/rank_2026-09-15/rank_summary.json` |
| Il gate di espressione non passa la sua regola: «batte ShrunkTransfer in tutti i fold» vale in **1 split su 6** per tutte e tre le varianti. Il permutato batte il gate vero in 2 split su 6 (G1), e il gate costruito sulla sorgente lo batte in 4 su 6 (G1) | misura | `reports/storico/expression_gate_2026-09-16/decision.json` |
| La scelta del gate non è stabile fra due seed che differiscono solo per i 32 bersagli di validazione interna: identità scelta in 23 righe su 27 con seed 2026 e in 7 su 27 con seed 2027 | misura | `reports/storico/expression_gate_2026-09-16/gate_rows.json` |
| Nell'universo del banco (6.477 geni) i geni spenti non ci sono: 0–2 sotto 5 CPM per contesto, minimo 4,3–8,6 CPM. Nei contesti ufficiali è l'opposto: 8.409–8.923 geni su 18.533 sotto 5 CPM e 2.317–2.853 esattamente a zero | misura | `reports/storico/expression_gate_2026-09-16/splits/`, `reports/storico/expression_gate_2026-09-16/context_presence.json` |
| Un gene a 1 CPM è contato 368–389 volte nei controlli di un contesto ufficiale (3,68–3,89·10⁸ molecole su 18.400 cellule): su quella scala uno zero è quasi sempre biologia, non strumento | misura | `reports/storico/expression_gate_2026-09-16/context_presence.json` |
| Le 54 righe dei nove bracci originali del run `x001` sono identiche a quelle di `m002`, differenza assoluta massima 0,0: stesso protocollo, stessi split, stessa metrica | misura | `reports/storico/expression_gate_2026-09-16/decision.json`, campo `reproduction` |
| Il file K562 genome-wide a singola cellula pesa 65.830.941.948 byte, cioè **61,31 GiB** (65,83 GB). Il «61,3 GB» del profilo è la stessa dimensione in GiB, come il 9,9 e l'8,1 degli altri due file Replogle a singola cellula. L'etichetta «65,8 GiB» usata in alcuni documenti è un errore di unità | misura (aritmetica sui byte) | `src/vcc2026/external.py`, [CP-0018](../checkpoints/0018-drive-storage-confermato.md) §3.3, [R-013](../REGISTRO.md#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb) |
| Le copie su Drive mostrano 61,31 GB e 811,2 MB: coerenti con i byte del catalogo letti in unità binarie. Nessun md5 è stato calcolato su di esse | dichiarazione del proprietario (non misurata dal progetto) + misura (aritmetica) | `configs/remote_catalog.yaml`, [CP-0018](../checkpoints/0018-drive-storage-confermato.md) §3.2 |
| Un run remoto vede i file solo sotto `<VCC2026_DATA_ROOT>/raw/`. `skip_complete` ricalcola l'md5 dell'intero file a ogni esecuzione, e con `FETCH_BLOCKS = None` la selezione salta i file presenti e scarica il blocco successivo | interpretazione (codice letto, non eseguito) | `src/vcc2026/remote_catalog.py`, [CP-0018](../checkpoints/0018-drive-storage-confermato.md) §3.4–3.6 |

## 4. Cosa non sappiamo

Queste sono le incertezze che contano. Nessuna è stata risolta.

1. **Quanto vale un punto.** Le ancore di replicato `r` restano ignote a noi, ma dal
   13 settembre c'è una strada che non richiede un bundle di valutazione: la classifica
   pubblica mostra, per ogni squadra e metrica, **il grezzo e lo scalato**, e due righe
   con grezzi diversi determinano `b` e `r` di `(u − b) / (r − b)`. Derivazione
   preliminare su due righe per `mse`: `b ≈ 0,996`, `r ≈ 0,022`, che riproduce il nostro
   1,231 → 0. **Non è ancora una misura**: va rifatta su molte righe e per tutte e sei
   le metriche ([CP-0006](../checkpoints/0006-prima-sottomissione-e-punteggio.md) §3.5).
   Il 16 settembre la stima è stata estesa alle sei metriche su undici righe
   (`reports/gara/leaderboard_2026-09-16/snapshot.md`): resta un'interpretazione, con i
   limiti scritti lì, finché non viene rifatta su più righe e per contesto.
2. ~~**Se comprimere l'ampiezza convenga davvero**~~ — **parzialmente risolta il
   2026-09-12.** Misurato: a piena ampiezza il trasferimento è peggio del nullo, e
   l'ottimo sta intorno a un quarto dell'ampiezza fuori lignaggio
   ([CP-0003](../checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §3.4,
   D-006, D-012). **Resta aperto** il pezzo che conta davvero: la misura è in spazio
   pseudobulk log2FC su K562 e RPE1, non sulle sei metriche VCC e non sui contesti
   A/B/C. Trasferibile è il metodo di calibrazione, non il valore, che rimisurato
   con selezione continua e validazione annidata è **0,1974** e non 0,25
   ([CP-0004](../checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.2).
3. **Quanto sono grandi gli effetti da prevedere.** Non lo sappiamo. Che i 300
   bersagli non compaiano in due pannelli *essential* è una misura; dedurne che siano
   non essenziali nei contesti della gara è un passaggio non verificato, e dedurne che
   le risposte siano piccole ne è un secondo. L'essenzialità riguarda la sopravvivenza
   della cellula, non l'ampiezza del cambiamento di espressione: un gene non essenziale
   può muovere molti geni. La mediana di 5 geni DE per riga misurata in K562 dice
   quanto segnale riusciamo a **stimare lì**, con 168 cellule mediane per riga, non
   quanto ce ne sia in A, B o C. Scheda
   [R-004](../REGISTRO.md#r-004--docsrevisione_analisi_2026-09-11md).
4. **Se l'asse genico ufficiale sia ricostruibile in identificatori Ensembl.** Due
   documenti dicono il contrario: contraddizione aperta, scheda
   [R-004](../REGISTRO.md#r-004--docsrevisione_analisi_2026-09-11md).
5. **Se il CD4 primario trasferisca ad A**, che è un contesto T ma con marcatori
   immaturi (DNTT, RAG1). Ipotesi, non misura.
6. **Se la co-espressione nei controlli predica la direzione della risposta.** È il
   modello a costo zero più attraente, ed è anche quello contestato: la correlazione
   non è causalità, e il segno può venire da regolatori comuni o dalla normalizzazione.
   **Prima misura, 17 settembre:** su 243 bersagli HepG2 la correlazione con l'effetto
   è nulla, 0,0015 di mediana dopo aver tolto 20 PC
   (`reports/storico/coexpression_2026-09-17/summary.json`). Resta non provata sui bersagli non
   essenziali.
7. **Se esista Perturb-seq CRISPRi pubblico in linea T matura o squamosa.** La ricerca
   non è conclusa; la pista più vicina per C, GSE281860, espone conteggi di guide e non
   la matrice RNA. L'incarico preparato il 14 settembre per l'orchestratore,
   `configs/orchestrator/briefs/ricerca-perturbseq-t-squamoso.yaml`, non è mai stato
   avviato ed è archiviato con l'orchestratore (D-040): la domanda resta aperta.
   **Verifica del 24 settembre:** Jurkat ha la sottoserie pubblica GSE249595,
   con lettura mirata di 374 geni; non identifica A e non chiude la ricerca sui
   contesti squamosi. DLD-1 e Mixscale sono stati esaminati come contesti aggiuntivi,
   con copertura e primi confronti in [CP-0035](../checkpoints/0035-dld1-mixscale-audit.md).
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
    cellule generate rilevano il 2,1–6,3% di geni in più dei controlli reali anche a
    effetto previsto zero, e il log2FC efficace mediano dopo calibrazione è 1,7%.
    Sono quantità diverse e dello stesso ordine; quale domini le quattro metriche DE
    dipende da come lo scorer aggrega, e non è stato misurato. È la ragione principale
    per cui il punteggio di `trial-01-transfer` non è prevedibile da ciò che sappiamo
    ([CP-0004](../checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.8).
13. **Se un ricampionamento dei controlli sia ammesso dalle regole.** Le regole dicono
    che i controlli scaricati sono soltanto input del modello e che le previsioni
    devono essere generate soltanto da modelli di machine learning. `trial-00-controls`
    passa la convalida di formato ma non è la previsione di un modello. Registrata in
    D-017, **non risolta**: serve un chiarimento da help@virtualcellchallenge.org o una
    decisione esplicita del proprietario.
14. **Quanto costi davvero `vcc prep` su una macchina adeguata.** Il picco di 22–33 GiB
    viene dal modello di dimensionamento della CLI, non da un'esecuzione nostra: la
    misura che abbiamo dovrebbe essere il costo di lettura di anndata, 8,60 byte per
    valore memorizzato, ma quel numero non compare in nessun file di `reports/`
    (verificato il 15 settembre e di nuovo il 24). L'unico valore registrato è
    `scipy_bytes_per_nnz: 8` in `reports/invii/trial_2026-09-12/q00prep_validation.json`: la
    costante assunta dal modello della CLI, non una nostra misura. L'8,60 resta leggibile in
    [CP-0004](../checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.5, che non si riscrive,
    e va trattato come non tracciabile finché non lo si rimisura. Il numero va confermato la
    prima volta che `prep` gira per davvero.
15. **Se la decomposizione modulare convenga.** Misurato un proxy su 160 bersagli
    K562/RPE1 ([CP-0011](../checkpoints/0011-primo-benchmark-modulare.md)): nella sola
    direzione K562 → RPE1 la base congelata ha un MSE/nullo un po' più basso di
    ShrunkTransfer, con IC che esclude zero su due seed; nella direzione inversa,
    a ampiezza prefissata 1, tutti i bracci perdono contro il nullo. Due contesti
    non identificano `z_c`. Non è un punteggio VCC. Resta **inconcludente**.
16. ~~**Se lo slim GO aggiunga qualcosa al solo basale sui bersagli mai visti.**~~
    **Risolta il 2026-09-15 in senso negativo** ([CP-0014](../checkpoints/0014-go-slim-e-gpu.md), D-028):
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
    ([CP-0017](../checkpoints/0017-gate-espressione-destinazione.md)).
20. **Se le copie su Drive siano leggibili in tempi utili.** Integrità e percorso sono
    risolti: md5 verificato al download del 15 settembre, nei percorsi attesi
    ([CP-0020](../checkpoints/0020-singola-cellula-cis-generatore.md) §3.1). **Risolta il
    17 settembre:** lo stadio 71 ha letto l'intero file dal mount di Colab in 2.548 s
    (24,6 MiB/s), con l'md5 uguale al catalogo
    (`reports/sorgenti/k562_sc_2026-09-17/stage71_x002_report.json`).
21. **Quante chiamate DE servono in `val`.** La FID premia le chiamate con il segno
    giusto e punisce il silenzio. Le docstring dello scorer indicano che il 12–30% dei
    bersagli ha meno di 10 geni significativi e che alcuni ne hanno più di 500. Quale
    ampiezza del predittore dia un numero di chiamate adeguato è da misurare nei banchi
    73 e 75 (D-035).
