# Che cosa imparare dai vincitori VCC 2025

3 ottobre 2026, Codex. Ricerca su fonti primarie e rianalisi leggera di metadati già nel repository.
Snapshot locale e hash degli input in [audit_r1/audit.json](audit_r1/audit.json).
**Nessun nuovo training, download di dataset, job remoto o score VCC.** Le priorità sotto sono
proposte da valutare in [R-LEAD](../../../docs/piani/strategia-scientifica.md), che resta la sede operativa.

La conclusione è che conviene **far apprendere alle cellule una correzione del transfer,
misurare la specificità del bersaglio e aumentare i dati attraverso confronti controllati**.
Il 2025 non dimostra che una piccola rete basti, né che serva attraversare terabyte a ogni training.
L'archivio completo e il campione di un esperimento hanno scopi diversi.

| Materiale | Contenuto e tipo di evidenza |
|---|---|
| Questo rapporto | Fonti, interpretazioni e proposte; i numeri locali nuovi sono riconti descrittivi |
| [audit_metadata.py](audit_metadata.py) | Codice riproducibile: legge soltanto 12 piccoli file di metadati |
| [audit_r1/support.csv](audit_r1/support.csv) | Copertura per modalità e soglia di numerosità |
| [audit_r1/coarse_caps.csv](audit_r1/coarse_caps.csv) | Limiti inferiori delle numerosità con tetti per gruppo × bersaglio |
| [audit_r1/audit.json](audit_r1/audit.json) | Provenienza, dimensioni registrate, esposizioni e verdetti del pilot |
| [SORGENTI.md](SORGENTI.md) | Catalogo del pacchetto PRiMeFlow e delle caratteristiche ESM2; verifica e uso possibile |
| [VERIFICHE.md](VERIFICHE.md) | Controlli sui riconti, documentazione e suite; limiti del primo passaggio nel sandbox |

## 1. Che cosa hanno effettivamente vinto

**Dichiarato dagli organizzatori**, non replicato in questa analisi:

| Risultato 2025 | Metodo | Elemento documentato |
|---|---|---|
| 1° BioMap, BM_xTVC | xTrimoSCPerturb | scFoundation modificato, embedding proteici, frequenza DEG e medie esplicite; training pseudobulk e loss combinata |
| 2° XLearning Lab | X | Rete fully connected, controlli aggregati, ESM2, indicatore UMI; previsione residua |
| 3° Outlier | TransPert | Statistiche aggregate e test Wilcoxon; combinazione delle sorgenti, predizione DEG e calibrazione della scala |
| Premio Generalist, Altos | go-with-the-flow | Generatore flow matching con U-Net, premiato sul rango medio di sette metriche |

La classifica principale favoriva soprattutto discriminazione e DEG; MAE sotto il riferimento
non penalizzava ulteriormente. **Inferenza:** il risultato non identifica da solo l'architettura
più fedele alla distribuzione cellulare. [Fonte ufficiale Arc, 6 dicembre 2025](https://arcinstitute.org/news/virtual-cell-challenge-2025-wrap-up).

Per i primi tre non ho trovato, nelle ricerche mirate di questa sessione, un'implementazione
completa verificabile della soluzione di gara. Questo è un limite della ricerca, non prova che
non esista. Il [paper del gruppo Outlier sul PDS](https://arxiv.org/abs/2511.16954) studia distanza
e scala della metrica: non è la specifica completa di TransPert. Le
[slide di Du del 13 gennaio 2026](https://www.scifac.hku.hk/f/event/9250/24208/10.%20Prof.%20Jinhong%20DU_PDS-20260113.pdf)
offrono ulteriore contesto, senza sostituire codice, iperparametri e ablation.

### Il cambiamento che impedisce una copia diretta

Nel 2025 erano disponibili perturbazioni della linea H1 destinataria. Nel 2026 vengono forniti
controlli non perturbati di linee nuove: il trasferimento del contesto è quindi parte del problema,
non solo quello del bersaglio. [Descrizione ufficiale Arc, 1 ottobre 2026](https://arcinstitute.org/news/behind-the-data-virtual-cell-challenge-2026).

**Interpretazione:** la calibrazione su risposte H1 del 2025 non si trasferisce automaticamente.
Oggi pesi delle sorgenti, ampiezza e arresto del training devono essere scelti su altre linee
interamente escluse dal fit, senza usare le risposte dei contesti di gara. Conserviamo inoltre
la distinzione C (bersaglio visto, contesto nuovo) / J (entrambi nuovi).

### PRiMeFlow è il riferimento pubblico più concreto

Il [paper PRiMeFlow v2, 13 maggio 2026](https://arxiv.org/html/2604.13986v2), appendice B,
descrive 6.975.767 cellule, sette dataset pubblici e uno proprietario; quota pubblica 89%.
La tabella 4 riporta:

| Versione | DES ↑ | PDS ↑ | MAE ↓ |
|---|---:|---:|---:|
| Pretraining | 0,210 | 0,695 | 0,074 |
| Fine-tuning 250pts | 0,228 | 0,747 | 0,086 |

Il fine-tuning usa le perturbazioni H1 ammesse e quelle dei target di test **in altre sorgenti**,
non le etichette nascoste H1. La generazione usa guidance differente per perturbati/controlli,
normalizzazione e azzeramento finale del gene bersaglio. Sono risultati e scelte degli autori.

**Interpretazione:** il miglioramento di DES/PDS con peggioramento MAE mostra un compromesso;
non isola l'effetto dell'architettura. Per noi guidance, scala, varianza, knockdown e architettura
vanno confrontati separatamente. Azzerare ogni bersaglio non è una stima misurata dell'efficacia
CRISPRi nei nuovi contesti.

Nel [config VCC pubblico](https://raw.githubusercontent.com/altoslabs/primeflow/main/src/primeflow/configs/experiment/primeflow/vcc/flow_matching_gaussian_source_multifile_h5.yaml)
la sorgente è gaussiana, il modello è una U-Net con caratteristiche ESM2, e il training predefinito
usa 6 GPU per nodo su 2 nodi. È una configurazione di riproduzione, **non un minimo hardware dimostrato**.
Per usare un simile generatore sui nostri contesti serve verificare un condizionamento ottenibile
dai soli controlli nuovi; un'etichetta categorica di linea, da sola, non specifica tale trasferimento.

## 2. Che cosa sappiamo già nel nostro progetto

**Risultati locali preesistenti**, distinti dai nuovi riconti:

1. Le correzioni semplici del transfer tramite espressione basale e interazioni a basso rango
   hanno dato `no_benefit` secondo il protocollo su sette gruppi. Non riproporrei la sola pesatura
   per somiglianza dei controlli come idea nuova. Questo esito riguarda quelle forme e quel banco,
   non ogni possibile uso del contesto. [Risultati P2–P3](../generalizzazione_contesti_2026-10-02/RISULTATI.md).
2. Nel pilot cellulare r3, Q1 (stato cellulare rispetto alla media dei controlli) passa, Q2
   (vantaggio sul transfer) fallisce in entrambe le corsie. La clausola di espansione B è falsa.
   Il JSON A conserva però `expand_on_lane_A=true`: è un campo di una regola diversa e non va
   trasformato in «il modello batte il transfer». I due esiti sono riportati integralmente in
   [audit.json](audit_r1/audit.json), da `decision_r3/decision.json` e
   `decision_laneB_r3/decision_lane_b.json` del pilot.
3. La rete v3 [ancorata al transfer](../../modelli/rete_ancorata_2026-10-03/README.md) implementa
   già la direzione ibrida principale. Non è un'idea nuova di questo rapporto e qui non ne è
   certificato alcun vantaggio. La [revisione del 3/10](../revisione_ancorata_codex_2026-10-03/README.md)
   documenta dipendenze indirette delle ancore dai target nascosti e disallineamenti dei confronti.
   La chiusura verificata di questi rilievi è necessaria prima di interpretare J e il confronto B.

**Stato documentale:** il registro descrive ancora il protocollo v3 come bozza senza training,
mentre la README lo dichiara congelato. Questa analisi non usa tale discrepanza per dedurre lo
stato dei job. Una descrizione di lancio non è un risultato validato.

### Nuovo riconto: la copertura utile dipende dalla profondità

I seguenti sono bersagli C del banco r3 con **al massimo due gruppi sorgente**. Si conta un gruppo
solo se ha almeno il numero indicato di cellule del bersaglio. I gruppi non sono donatori indipendenti.

| Linea esclusa | Bersagli C | Tutte le modalità, ≥1 cellula | CRISPRi, ≥1 | CRISPRi, ≥20 | CRISPRi, ≥50 |
|---|---:|---:|---:|---:|---:|
| H1 | 151 | 97 | 98 | 100 | 105 |
| HepG2 | 1.748 | 0 | 0 | 125 | 561 |
| RPE1 | 1.794 | 0 | 0 | 143 | 820 |

**Misurato sui metadati:** [support.csv](audit_r1/support.csv), ricostruito dai CSV della matrice
per gruppo; input identificati con SHA256. Include i casi senza alcun gruppo sopra soglia.
20 e 50 sono sensibilità descrittive, non soglie biologiche validate. Nel passaggio a CRISPRi
la numerosità dei gruppi cambia, ma per HepG2/RPE1 è soprattutto la soglia di cellule a cambiare
il conteggio della tabella. Non attribuire tutto alla commistione di modalità.

**Interpretazione:** «ogni target compare in almeno tre linee» non implica tre misure affidabili.
Al contrario, questa tabella non dimostra che aggiungere una quarta linea migliori la previsione:
bersagli con diverso supporto differiscono anche per biologia e studio. Occorre variare le
sorgenti sugli stessi bersagli e mantenere fermo il test.

### Nuovo riconto: milioni di cellule già viste

Le ricevute `coverage.json` del pilot r3 dichiarano rispettivamente **3.850.952, 3.970.762 e
3.887.913 cellule distinte viste** per H1, HepG2 e RPE1, due epoche. Non sono tre insiemi disgiunti
da sommare. L'attesa dei dati registrata è 37,7%, 36,1%, 39,3% del tempo.
[Valori e manifest](audit_r1/audit.json).

**Interpretazione:** la carenza non è dimostrata dal solo numero di cellule; resta possibile che
manchino combinazioni informative. L'attesa suggerisce di profilare anche accesso e preparazione
dei batch. Non è una misura di sola latenza disco e non permette di promettere un'accelerazione
equivalente eliminando l'I/O.

## 3. Approfondimenti proposti, in ordine di utilità

Sono ipotesi e confronti da preregistrare, **non una nuova coda di job**. Il mandato corrente
mantiene la supervisione delle reti sulle cellule; le statistiche aggregate servono da baseline,
ancore, descrittori e diagnostica, senza sostituire quella supervisione.

| Priorità | Contrasto concreto | Che cosa deve chiarire |
|---|---|---|
| 1. Valutare correttamente la v3 già implementata | Ancora sola, rete con la stessa ancora, transfer storico distinto; stessa generazione e supporto | Quanto aggiunge l'apprendimento cellulare, separato dal cambio di sorgenti o generatore |
| 2. Affidabilità per gene e sorgente | Ancora attuale contro correzione regolarizzata con incertezza e concordanza dei segni; stessi dati | Se errori sistematici del transfer dipendono da misure poco affidabili, non solo dalla somiglianza basale |
| 3. Specificità del bersaglio nella loss | Loss cellulare corrente contro aggiunta di un termine contrastivo su perturbazioni diverse dello stesso contesto | Se si può preservare la distinzione dei target senza guadagnare solo sulla risposta comune |
| 4. Descrittori proteici congelati | Descrittori attuali contro attuali + ESM2, e sostituzione a dimensione comparabile | Se l'informazione di sequenza aggiunge capacità in J, oltre a GO/STRING e profili basali |
| 5. Correzione della distribuzione | Generatore attuale contro piccolo modulo residuo, a effetto medio e controlli comparabili | Se resta un errore di distribuzione che giustifichi un flow matching più complesso |

**Priorità 2.** Stimare affidabilità da repliche/guide, variabilità entro sorgente, ripetibilità del
segno e quantità di informazione; la sola frequenza di significatività aumenta anche con profondità
e potenza del test. Una statistica «gene spesso DEG» va comparata con una basata sulla sola
espressione e con il modello senza prior. Il prior si stima nel training di ciascun fold; le
statistiche di target/linee escluse non devono entrarvi neppure tramite medie globali. Il peso
può dipendere dal gene di risposta: è un'ipotesi diversa da un solo peso basale per sorgente,
ma resta da verificare. Non confondere disaccordo biologico con bassa qualità tecnica.

**Priorità 3.** Il termine ausiliario può confrontare le risposte medie predette del minibatch,
mantenendo la loss sulle singole cellule. L'ablation deve includere bersagli scambiati e risposta
generica, con la stessa scala: altrimenti l'amplificazione può simulare specificità. Il
[paper PDS di Outlier](https://arxiv.org/abs/2511.16954) motiva il controllo della scala, non
l'adozione di un particolare fattore sullo scorer 2026. Pesare una sola metrica senza guardie
su segno, ampiezza e distribuzione ripeterebbe il compromesso del 2025.

**Priorità 4.** Il [costruttore dei descrittori v3](../../modelli/rete_ancorata_2026-10-03/target_descriptors.py)
elenca GO, STRING, HGNC, GENCODE e DepMap; ESM2 non è uno dei blocchi lì costruiti.
La prova utile è l'incremento rispetto a questi descrittori, non «embedding contro niente».
Congelare mapping gene/proteina, isoforme, maschere di assenza, versione e provenienza.
Riduzione dimensionale appresa solo dove ammesso dal fold; una rappresentazione preaddestrata
su etichette perturbazionali escluse non sarebbe una prova pulita di J.

**Priorità 5.** Prima diagnosticare per contesto errori di varianza, frazione di zeri e sottostati,
confrontando anche la variabilità fra replicati reali. Se il problema principale resta il segno
dell'effetto, un generatore più ricco non ha ancora una motivazione misurata. Se si prova un flow,
iniziare da un modulo condizionato sui controlli disponibili, non dal rifacimento del pretraining
Altos completo. Non si propone ora una nuova architettura come già superiore.

## 4. Gestire i dati senza trasformare ogni esperimento in un archivio

**Decisione già esistente:** rimane l'acquisizione completa delle cellule idonee, CD4 incluso.
La [strategia inoltrata dal proprietario](../../sorgenti/ingestione_completa_2026-10-03/STRATEGIA_DATI_TRAINING.md)
separa archivio e campioni. Le indicazioni seguenti precisano quella proposta, senza cambiare
ingestion o job concorrenti.

### Tre prodotti distinti

| Prodotto | Contenuto | Uso |
|---|---|---|
| Archivio verificato | Originali/localizzatori, shard cellulari idonei, metadati, esclusioni e ricevute | Conservazione e possibilità di costruire viste nuove |
| Banca degli effetti | Medie, numerosità, variabilità, segni/test DE, controlli e maschere per sorgente e contesto | Transfer, ancore, audit di affidabilità; derivati costruiti rispettando gli split |
| Corpus di un training | Cellule e controlli selezionati, indici annidati, shard, fold e manifest immutabile | Esperimento riproducibile che può essere ampliato |

Il manifest P0 r2 registra **468 file, 17,836 GB decimali (16,611 GiB)**: sono gli input del banco,
inclusi file ausiliari, non il corpus cellulare completo. Il totale è ricalcolato dai byte del
manifest; gli hash dei file pesanti non sono stati ricalcolati qui. Per questa analisi sono stati
letti **716.534 byte di metadati**. [Audit](audit_r1/audit.json).

Il [rilascio pubblico PRiMeFlow](https://github.com/altoslabs/primeflow) indica circa 244 GB compressi,
di cui 198 GB CD4; indica anche come usare i restanti circa 47 GB. **Non documenta equivalenza
prestazionale del sottoinsieme.** Inoltre il rilascio esclude dati proprietari ed elenca CD4,
mentre l'atlante descritto nell'appendice B del paper non lo elenca. Quindi i byte del pacchetto
odierno non misurano il minimo necessario alla soluzione vincente. La [scheda sorgente](SORGENTI.md)
registra questa distinzione ed evita di trattare un ripacchettamento come nuova biologia.

### Quanto possono ridursi le viste: un limite inferiore, non una promessa

Nella matrice di training H1 ci sono 3.609.008 cellule perturbate con target singolo e 16.559
coppie gruppo × bersaglio, sommando le modalità. Il costruttore della matrice esclude i controlli;
questo totale non è il denominatore della ricevuta completa da 3.850.952 cellule.

| Tetto grossolano per gruppo × bersaglio | Cellule risultanti | Quota del totale di questa matrice |
|---|---:|---:|
| 32 | 515.744 | 14,3% |
| 64 | 964.709 | 26,7% |
| 128 | 1.651.809 | 45,8% |

**Calcolo descrittivo:** somma di `min(n, tetto)` su gruppi e bersagli, senza estrarre cellule.
[Tutti i fold e variante solo CRISPRi](audit_r1/coarse_caps.csv).
I gruppi aggregano donatori, stati, studi e guide. Applicando tetti distinti a strati più fini si
ottiene almeno questa numerosità: la tabella è un **limite inferiore**. Controlli, nuovi ingressi
e vincoli di rappresentanza la aumentano. Non dimensionare GPU/disco con questi numeri e non
attribuire loro una qualità predittiva già misurata.

### Contratto minimo prima di preparare i campioni

Proposta da integrare negli adattatori e nei manifest del piano dati:

- Una riga di inventario per `(linea, donatore, stato, tempo, studio, modalità, bersaglio,
  guida, libreria)`, con cellule prima/dopo QC, motivi di esclusione e disponibilità dei controlli.
  Un ID sorgente/versione/libreria/barcode evita collisioni; una tabella di equivalenza fra
  rilasci evita che la stessa cellula, rinominata, venga conteggiata come replica nuova.
- Assi genici e unità espliciti, counts e dimensione di libreria conservati quando disponibili;
  geni non misurati mascherati. Non confrontare CPM su pannelli diversi come se avessero lo
  stesso denominatore; stimare e versionare ogni trasformazione.
- Indici 32 ⊂ 64 ⊂ 128 deterministici per strato, con guide/repliche rappresentate e deroghe
  esplicite dove il tetto sarebbe troppo piccolo. Nessuna selezione delle cellule in base alla
  forza dell'effetto. Pool separati di controlli per contesto/libreria, conservando gli stati.
- Separare probabilità di campionamento e peso della loss. Registrare celle uniche viste,
  numero di riusi, esposizioni per target/stato e quote effettive della loss. Il corpus CD4 può
  essere grande senza avere un peso proporzionale alla sua numerosità.
- Preparare shard selezionati vicino ai dati e verificare gli hash prima del training;
  misurare un passaggio breve di lettura, memoria e attesa prima di scegliere chunk e cache.
  Preprocessing CPU secondo PROCEDURE §3; training GPU su Kaggle; portatile per questi audit piccoli.
  Non trasferire il corpus intero a ogni variazione di modello.

Non serve creare contemporaneamente copie dense, normalizzate e compresse di ogni versione:
conservare un riferimento verificato e materializzare i derivati necessari, sempre su nuove
destinazioni. Qualsiasi futura eliminazione resta una decisione separata con verifica di recupero.

## 5. Il confronto che renderebbe interpretabile «servono più dati»

La proposta 32/64/128 già presente è sensata come scala sperimentale, **non come numero sufficiente
dimostrato**. Manteniamo linea esclusa, target di valutazione, modello, ancore e generatore fissi;
confrontiamo prima a pari aggiornamenti/batch, annotando anche costo e cellule uniche viste.
Una seconda domanda, separata, riguarda la convergenza con training più lungo. Campioni ruotati
fra tranche costituiscono un altro contrasto, non una sostituzione silenziosa del corpus.

Per separare apprendimento cellulare e miglioramento delle ancore:

| | Ancora con dati iniziali | Ancora con dati ampliati |
|---|---|---|
| Campione cellulare iniziale | Riferimento | Effetto del miglioramento statistico |
| Campione cellulare ampliato | Effetto dell'esposizione cellulare | Effetto congiunto e possibile interazione |

Tutte le ancore rispettano il fold. Il primo confronto non richiede l'esecuzione immediata di
ogni casella: serve a non attribuire alle cellule ciò che deriva da una nuova ancora.

La priorità dei nuovi dati va letta in tre colonne separate: **combinazioni target × contesto
aggiunte**, collegamenti dello stesso target fra contesti, incremento di ripetibilità sulle
combinazioni già presenti. Conservare anche target fuori pannello e contesti lontani; il loro
valore può essere in J o nella rappresentazione, anziché nel transfer immediato. Linee/studi
ponte a protocollo comparabile possono aiutare a separare biologia e chimica: è un'ipotesi,
non una classifica di utilità già misurata per le sorgenti in acquisizione.

Per la promozione servono le sei metriche del banco cellulare, supporto C/J separato, confronto
con transfer e generico, risultati per contesto e incertezza fra target/gruppi. Le soglie e
regressioni ammesse vanno congelate **prima** delle nuove misure. Il proxy sugli effetti non
diventa uno score ufficiale. Le linee già esplorate restano sviluppo; H1 test resta chiusa.
Nessuna conclusione causale sulla quantità di dati da un confronto fra target diversi.

## 6. Riproduzione e limiti

```powershell
.\scripts\py.cmd reports/analisi/lezioni_vcc2025_2026-10-03/audit_metadata.py --out reports/analisi/lezioni_vcc2025_2026-10-03/audit_r2
```

Scegliere sempre una destinazione nuova. Lo script rifiuta output già esistenti; legge CSV/JSON,
non matrici di espressione. Il manifest identifica gli input e il commit, ma non certifica la
disponibilità remota né la deduplicazione degli archivi originali. I numeri esterni sono
dichiarazioni degli autori; nessun vincitore è stato replicato qui. Le pagine web sono state
consultate il 3 ottobre 2026; il repository PRiMeFlow su `main` può cambiare, mentre il paper
citato è la versione v2. Le raccomandazioni non costituiscono evidenza che un modello sia migliore.
