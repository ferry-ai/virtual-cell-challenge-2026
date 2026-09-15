# Mappa del progetto — VCC 2026

**Questo è il punto di ingresso.** Se leggi una cosa sola, leggi questa pagina.
Aggiornata il 2026-09-15.

Le altre pagine del sistema: [checkpoint](checkpoints/INDICE.md) (cosa è successo e
quando), [decisioni](DECISIONI.md) (cosa abbiamo scelto e quando va riaperto),
[registro](REGISTRO.md) (di quali documenti e dati ci si può fidare).

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

| Fase | Stato |
|---|---|
| Ambiente, CLI, dati di controllo, writer di sottomissione verificato | fatto |
| Identificazione dei contesti e del contratto di punteggio | fatto |
| Audit delle sorgenti esterne candidate | fatto |
| Registry versionato delle sorgenti, con livelli di verifica | fatto |
| Pipeline verticale: registry → firme con incertezza → baseline → valutazione | fatto, su scala ridotta |
| Baseline di trasferimento calibrate e valutate fuori campione | fatto (spazio pseudobulk) |
| Scorer ufficiale eseguito end-to-end su un bundle a singola cellula | fatto, su un **nullo** |
| Contratto di sottomissione verificato sulle fonti ufficiali e sulla CLI | fatto ([SOTTOMISSIONE.md](SOTTOMISSIONE.md)) |
| Calibrazione annidata dell'ampiezza, selezione separata dal riporto | fatto ([CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.2) |
| Inferenza per A/B/C e due previsioni complete 300 × 400 × 3 | fatto, verificate sul file scritto |
| Packaging `.vcc` di trial-01 | fatto in locale, 0,52 GiB di picco ([CP-0005](checkpoints/0005-packaging-streaming-trial01.md)) |
| **Banco di prova predittivo (punteggio VCC su effetti veri)** | **bloccato: manca un dataset perturbato reale** |
| Prima sottomissione valutata | fatto: 0,045929, rango 446/920 ([CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md)) |
| Modello condizionato sul contesto (fase 3 del piano in `README.md`) | **non iniziato**: `LowRankRidge` esiste in `src/vcc2026/models.py`, ma non è testato, non è importato da nessuno stadio e non è mai stato eseguito (R-11) |
| Ensemble, miglioramento del punteggio | non iniziato |

**Il 13 settembre 2026 è stata inviata la prima sottomissione, ed è stata valutata:
punteggio 0,045929, posizione 446 su 920 squadre**
([CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md)). È il primo numero del
progetto sulla scala della gara. Fino a quel momento la riga qui sopra diceva «nessuna
sottomissione è stata inviata e non esiste alcun punteggio di leaderboard»: era vera
fino alle 01:12Z del 13 settembre.
Dal 12 settembre esistono però baseline misurate: trasferimento con ampiezza calibrata
su bersagli tenuti fuori ([CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md),
raffinata da [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md)).
Sono in spazio pseudobulk log2FC, **non** sono punteggi VCC, e la distinzione va tenuta:
lo scorer vuole conteggi a singola cellula contro controlli reali.

Esistono anche, dal 12 settembre, **due previsioni complete a forma di sottomissione**
per i contesti A/B/C — un ricampionamento dei controlli senza modello e il
trasferimento calibrato — generate in locale e verificate contro il contratto leggendo
il file scritto. Dal 13 settembre **`trial-01-transfer` è impacchettato**: un `.vcc` da
3,91 GiB, prodotto con un percorso che convalida e scrive senza materializzare la
matrice (0,52 GiB di picco contro i 33,5 del modello della CLI ufficiale), con tutte e
24 le convalide attive e il payload verificato bit a bit contro l'input
([CP-0005](checkpoints/0005-packaging-streaming-trial01.md)).

**Il server lo ha accettato**, il 13 settembre: la sottomissione è arrivata a
`published`, con l'md5 verificato e nessun errore. Resta vero che una convalida di
formato non dice nulla sulla qualità predittiva — ora misurata, e bassa.
`trial-00-controls` non è impacchettato e non va inviato (D-017).

## 3. Cosa sappiamo, e cosa lo sostiene

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

## 4. Cosa non sappiamo

Queste sono le incertezze che contano. Nessuna è stata risolta.

1. **Quanto vale un punto.** Le ancore di replicato `r` restano ignote a noi, ma dal
   13 settembre c'è una strada che non richiede un bundle di valutazione: la classifica
   pubblica mostra, per ogni squadra e metrica, **il grezzo e lo scalato**, e due righe
   con grezzi diversi determinano `b` e `r` di `(u − b) / (r − b)`. Derivazione
   preliminare su due righe per `mse`: `b ≈ 0,996`, `r ≈ 0,022`, che riproduce il nostro
   1,231 → 0. **Non è ancora una misura**: va rifatta su molte righe e per tutte e sei
   le metriche ([CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) §3.5).
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
7. **Se esista Perturb-seq CRISPRi pubblico in linea T matura o squamosa.** La ricerca
   non è conclusa; la pista più vicina per C, GSE281860, espone conteggi di guide e non
   la matrice RNA.
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
15. **Contro quale origine ci misura lo scorer.** `README.md` riporta dalla specifica
    ufficiale che lo zero di ogni metrica è la **media dei costrutti perturbati**, non
    la media dei controlli. Se è così, tutte le nostre calibrazioni hanno ottimizzato
    contro l'origine sbagliata — misurano l'errore rispetto al profilo NTC — e la
    componente di risposta **comune** a ogni perturbazione, che le firme contengono e
    che α = 0,197 comprime, è esattamente ciò che separa le due origini. È
    un'**ipotesi** con una conseguenza misurabile su `mse` e `fid`, e la sua premessa è
    una lettura del README, **non una nostra verifica**: va confermata sulla specifica
    e sul codice di `cell-eval2` prima di costruirci sopra. Roadmap R-8.

## 5. Il prossimo passo

**Dal 15 settembre l'ordine di lavoro è quello di
[ROADMAP.md](ROADMAP.md) «Priorità dal 15 settembre».** Il primo punteggio ha spostato
la domanda: non più «riusciamo a consegnare», ma «perché quattro metriche su sei stanno
a zero o sotto». Le prime tre voci — ancore `b` e `r` dalla classifica, nullo
**generato** contro i controlli reali, ricentratura sulla baseline del punteggio — non
richiedono né acquisizioni né quota, e sono lì per separare tre cause che oggi non
sappiamo distinguere: l'artefatto del generatore, l'origine sbagliata della
calibrazione, e l'assenza di segnale trasferibile. Le acquisizioni qui sotto restano il
passo che sblocca tutto il resto, e non sono state fatte.

Il punto 1 e il punto 4 dell'elenco sotto sono **stati eseguiti** il 12 settembre
(CP-0003): le baseline elementari girano, sono calibrate su bersagli tenuti fuori e
hanno prodotto numeri. Restano i punti 2 e 3, che sono acquisizioni.

1. ~~Scegliere i bersagli supportati con `panel_coverage.csv`~~ — fatto; la selezione
   vive ora in `configs/sources.yaml` e nello stadio 1 della pipeline.
2. Acquisire da CD4 le righe di pseudobulk dei bersagli del pannello più gli NTC
   appaiati per donatore e condizione, con tetto di byte esplicito. Questo dà una
   **sorgente di trasferimento**: firme di risposta medie per bersaglio.
3. Acquisire, separatamente e con il proprio tetto di byte, un insieme limitato di
   **cellule perturbate vere più i loro NTC**, dello stesso studio e dello stesso
   batch. Questo, e solo questo, dà il **bundle di valutazione**.
4. ~~Far girare le baseline elementari~~ — fatto: nullo, trasferimento con shrinkage,
   trasferimento pesato e ridge a basso rango sono implementati in
   `src/vcc2026/models.py`; i primi due sono misurati in
   `reports/pipeline/transfer_experiment.json`.

**I passi 2 e 3 non sono lo stesso passo, ed è l'errore da non fare.** Il pseudobulk
aggrega molte cellule in una riga: serve a stimare l'effetto medio di un bersaglio, ma
ha perso la distribuzione fra cellule. Ricostruire somme intere di conteggi non
ricostruisce le cellule che le hanno prodotte. Lo scorer vuole conteggi a singola
cellula (`input_type: counts`), misura contro le cellule di controllo **reali**, e la
sua correzione del rumore di campionamento sulla MSE dipende dalla dispersione fra le
cellule previste. Con il solo pseudobulk si ottengono diagnostiche sulla media — utili,
ma da non chiamare punteggio VCC. Un'acquisizione riuscita del solo passo 2
lascerebbe il collo di bottiglia esattamente dov'è.

Scelta ancora aperta: da dove prendere le cellule del passo 3 — CD4, oppure
sottoinsiemi limitati di Jurkat, HepG2 o RPE1, che non hanno copertura del pannello ma
hanno cellule e NTC identificati. Va decisa e registrata in
[DECISIONI.md](DECISIONI.md).

### Il passo operativo, che è diverso e indipendente

Il collo di bottiglia del packaging, aperto il 12 settembre, è **chiuso dal 13**:
`trial-01-transfer` è un `.vcc` da 3,91 GiB, prodotto qui con 0,52 GiB di picco
([CP-0005](checkpoints/0005-packaging-streaming-trial01.md)). Non serviva una macchina
più grande; serviva non caricare la matrice.

Resta una cosa sola, e non è tecnica: il chiarimento sulle regole per
`trial-00-controls` (D-017). Un ricampionamento dei controlli reali non è la previsione
di un modello, e le regole dicono che i controlli sono soltanto input. Fino ad allora
quel trial non si impacchetta e non si invia.

L'altra — l'autorizzazione a consumare quota — è stata data e usata il 13 settembre:
i comandi di `docs/SOTTOMISSIONE.md` §3 e la lista di §6 sono stati eseguiti, il server
ha accettato e ha valutato
([CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md)). Ogni invio successivo
resta però una decisione del proprietario: la quota è di due sottomissioni al giorno,
una sola in volo.

Il piano ordinato, con ipotesi, criteri di successo e costi stimati, sta in
[ROADMAP.md](ROADMAP.md). L'architettura della pipeline è in [PIPELINE.md](PIPELINE.md);
come eseguirla su una macchina remota, con le stime di risorse, in
[ESECUZIONE_REMOTA.md](ESECUZIONE_REMOTA.md).

## 6. Percorso di lettura

Per capire il progetto, nell'ordine:

1. Questa pagina.
2. [CP-0001](checkpoints/0001-ricostruzione-stato-2026-09-12.md) — stato al
   12 settembre e tutte le correzioni avvenute finora.
2-bis. [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) — il primo trial
   locale: contratto di sottomissione verificato, calibrazione annidata, due previsioni
   complete, e il limite di memoria che blocca il packaging. Se devi capire *dove si è
   fermato il lavoro operativo*, è questo. I comandi stanno in
   [SOTTOMISSIONE.md](SOTTOMISSIONE.md).
3. `README.md` — compito, formato, metriche, setup. Leggi prima la sua scheda
   [R-001](REGISTRO.md#r-001--readmemd): alcune sue parti sono rimaste indietro.
4. `docs/candidate_adversarial_review_2026-09-12.md` — l'analisi più dettagliata sulle
   sorgenti candidate, su cui poggiano le decisioni attive.
5. `docs/revisione_grok_2026-09-12.md` — il documento più recente: verifica di un
   inventario esterno, con cinque piste nuove. **Le sue conclusioni non sono ancora
   decisioni**: nessuno le ha ancora confrontate con D-004, e servirà un checkpoint per
   farlo.

I due documenti più vecchi, `docs/data_strategy_2026-09-11.md` e
`docs/revisione_analisi_2026-09-11.md`, si leggono **dopo** e con il
[registro](REGISTRO.md) accanto: contengono materiale ancora valido e conclusioni già
corrette, e il registro dice quale è quale.

## 7. Come si tiene aggiornato questo sistema

Quattro regole, nient'altro.

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
