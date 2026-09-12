# Decisioni

Che cosa abbiamo deciso, perché, e **a quale condizione va riaperto**. Il motivo per
cui questo file esiste separato dai checkpoint: un checkpoint è una fotografia che non
cambia più, una decisione invece è viva e può essere rimessa in discussione. Qui si
tiene solo il minimo che serve per riconoscerla e per sapere quando riaprirla; il
ragionamento completo e le misure stanno nel materiale citato in "Sostenuta da".

> **Ricostruzione retrospettiva.** Fino al 12 settembre 2026 il progetto non teneva un
> registro delle decisioni. Le voci da D-001 a D-009 e D-011 sono state ricostruite
> leggendo i documenti e il codice esistenti: la data è quella del documento che le
> stabilisce, non quella in cui qualcuno le ha formalmente approvate. Nessuna
> approvazione umana è registrata, perché non ne esiste traccia negli artefatti.

| ID | Decisione | Stato | Dal | Sostenuta da |
|---|---|---|---|---|
| D-001 | I dati pesanti stanno fuori dal repository | attiva | 2026-09-11 | `configs/config.yaml`, `src/vcc2026/config.py` |
| D-002 | Servono dati perturbazionali esterni: la previsione è zero-shot | attiva | 2026-09-11 | `docs/data_strategy_2026-09-11.md` |
| D-003 | Prima un banco di prova locale, poi modelli più complessi | attiva | 2026-09-11 | `docs/data_strategy_2026-09-11.md` §6, `docs/revisione_analisi_2026-09-11.md` §6 |
| D-004 | Ordine di acquisizione: CD4, poi Orion HCT116, poi i benchmark | attiva | 2026-09-12 | `docs/candidate_adversarial_review_2026-09-12.md` §5 |
| D-005 | Nessun atlante completo e nessun servizio a pagamento su questa macchina | attiva | 2026-09-12 | `reports/candidate_verification/hardware.json` |
| D-006 | Postura di sottomissione: decidere sulla direzione, comprimere l'ampiezza | attiva | 2026-09-11, misurata 2026-09-12 | `reports/pipeline/transfer_experiment.json`, [CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §3.4 |
| D-007 | K562 resta come ablazione: non è scartata | attiva | 2026-09-12 | `docs/candidate_adversarial_review_2026-09-12.md` §3 |
| D-008 | Si valuta con `cell-eval2 0.16.0`, tutte e sei le metriche | attiva | 2026-09-11 | `reports/scorer/vcc2026_contract.json` |
| D-009 | Un gene non misurato ha una maschera, non uno zero | attiva | 2026-09-11 | `docs/data_strategy_2026-09-11.md` §4 |
| D-010 | Il progetto si documenta con mappa, checkpoint, decisioni e registro | attiva | 2026-09-12 | `docs/checkpoints/0001-ricostruzione-stato-2026-09-12.md` |
| D-011 | La validazione non si filtra per efficacia osservata delle guide | attiva | 2026-09-12 | `configs/candidate_ingestion.json` |
| D-012 | L'ampiezza si calibra su bersagli tenuti fuori, non si sceglie | attiva | 2026-09-12 | `reports/pipeline/transfer_experiment.json` |
| D-013 | Lo stato di una sorgente lo dichiara il registry versionato | attiva | 2026-09-12 | `configs/sources.yaml`, `src/vcc2026/registry.py` |
| D-014 | Il backend DE si registra accanto a ogni metrica | attiva | 2026-09-12 | `reports/pipeline/null_calibration_A.json` |

---

### D-001 — I dati pesanti stanno fuori dal repository

- **Perché:** il repository sta sul Desktop, che OneDrive sincronizza. Decine di GB di
  `.h5ad` sarebbero lenti da sincronizzare e consumerebbero la quota cloud.
- **Alternative scartate:** tenere i dati nel repository (sincronizzazione); usare
  soltanto una variabile d'ambiente senza valore predefinito (fragile).
- **Come è fatta:** `data_root: C:/Users/ferra/vcc2026-data` in `configs/config.yaml`,
  sovrascrivibile con `VCC2026_DATA_ROOT`. Tutto passa da `src/vcc2026/config.py`.
- **Riaprire se:** il progetto si sposta su un'altra macchina, o il Desktop esce da
  OneDrive.

### D-002 — Servono dati perturbazionali esterni

- **Perché:** la gara non fornisce alcun training set. I controlli ufficiali
  descrivono lo stato basale; da soli non identificano la risposta causale al
  knockdown.
- **Alternative scartate:** lavorare con i soli controlli ufficiali. Resta però vero
  che i 55.200 controlli servono per il modello di rumore, i moduli di co-espressione
  e le soglie di espressione: la decisione riguarda la *supervisione*, non l'uso dei
  controlli.
- **Riaprire se:** la gara rilasciasse dati perturbati per i contesti ufficiali.

### D-003 — Prima un banco di prova locale, poi modelli più complessi

- **Perché:** con due sottomissioni al giorno, senza valutazione locale fedele si
  possono provare al massimo due idee al giorno. E un punteggio locale calcolato su
  metriche grezze non è il punteggio della gara: servono baseline e ancore misurate
  sugli stessi dati.
- **Alternative scartate:** iterare direttamente sulla leaderboard (troppo lento e si
  adatta al set di validazione); usare solo le metriche grezze di `compute_metrics`
  senza ancore (non confrontabile con la scala della gara).
- **Blocco attuale:** manca un *bundle reale*, cioè conteggi perturbati **a singola
  cellula** più i loro NTC in un qualunque contesto. Il candidato indicato, H1 2025,
  localmente ha solo quattro CSV di metadati e nessun RNA.
- **Attenzione, errore facile:** il pseudobulk non sblocca questa decisione. Aggrega le
  cellule e perde la loro distribuzione; serve per le firme di risposta medie, non per
  la valutazione completa, che richiede conteggi per cellula, controlli reali e una
  dispersione realistica. Acquisire pseudobulk e considerare il benchmark risolto
  lascerebbe il collo di bottiglia intatto mentre sembra chiuso. Le due acquisizioni
  sono passi distinti in `docs/PROGETTO.md`, sezione "Il prossimo passo".
- **Riaprire se:** non va riaperta, va sbloccata.

### D-004 — Ordine di acquisizione: CD4, poi Orion HCT116, poi i benchmark

- **Perché:** è l'ordine che massimizza copertura del pannello **misurata** e
  vicinanza di lignaggio, sotto il vincolo di disco. CD4 copre 297/300 in libreria e
  293 osservati; Orion 300/300 in libreria; entrambi hanno molti più geni di output in
  comune con l'asse ufficiale (17.772 e 18.106 su 18.533) delle sorgenti Replogle
  (8.260–9.024).
- **Alternative scartate, con il motivo:**
  - H1 2025, KOLF2.1J, HIPSCI come priorità 1–3 (l'ordine del primo audit): sono tutti
    contesti iPSC/ESC, un solo lignaggio, che non corrisponde né ad A, né a B, né a C.
    Restano utili per ampiezza e variazione fra donatori.
  - Pisces: la scheda pubblica dice "Coming Soon", non ci sono matrici scaricabili.
  - Il sottoinsieme `Strong_Perturbations` di KOLF: selezionare per risposta forte
    significa selezionare sull'esito. Il sottoinsieme sovrarappresenta gli effetti
    facili e fa sembrare il modello migliore di quanto sia, qualunque sia l'ampiezza
    vera degli effetti del pannello 2026 — che non abbiamo misurato.
- **Incertezza dichiarata:** CD4 è T primario maturo, A è T-ALL con marcatori immaturi
  (DNTT, RAG1). La corrispondenza di lignaggio è un priore, non una regola di
  trasferimento.
- **Riaprire se:** (a) i 239 bersagli CD4 con almeno 30 cellule non bastano a stimare
  effetti utilizzabili; (b) esce una sorgente CRISPRi pubblica in linea linfoide T o
  squamosa, che avrebbe la precedenza; (c) Pisces rilascia le matrici; (d) la licenza
  CC-BY-NC-SA-4.0 di Xaira risulta incompatibile con le regole della gara — da
  verificare prima di usare Orion in una sottomissione.

### D-005 — Nessun atlante completo e nessun servizio a pagamento su questa macchina

- **Perché:** 8,4 GB di RAM totali e circa 28 GB di disco libero. Il solo pseudobulk
  CD4 pesa 44,6 GB; i dodici oggetti single-cell CD4 sommano 1,736 TB.
- **Come è fatta:** letture remote con budget di byte (`src/vcc2026/remote_ranges.py`),
  una sorgente alla volta, almeno 10 GiB di disco libero da preservare. Politica
  scritta in `configs/candidate_ingestion.json`, campo `resource_policy`.
- **Attenzione:** una frazione piccola di dati non implica un trasferimento piccolo.
  Estrarre 64 cellule ha richiesto 92 MB di traffico per 1,6 MB di output.
- **Riaprire se:** arriva un disco più capiente, oppure il proprietario del progetto
  autorizza esplicitamente spesa cloud. Nessun servizio a pagamento è stato attivato.

### D-006 — Postura di sottomissione: decidere sulla direzione, comprimere l'ampiezza

- **Stato: attiva dal 2026-09-12**, dopo la prima misura. Prima era `da-verificare`, e
  la versione precedente di questa scheda resta leggibile nella cronologia del file.
- **Che cosa è stato misurato** ([CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §3.4,
  `reports/pipeline/transfer_experiment.json`): trasferendo a piena ampiezza (α = 1)
  l'errore quadratico è **peggiore** che non prevedere nulla — 1,162 volte l'MSE nullo
  da K562 genome-wide a RPE1, e 1,535 perfino fra due esperimenti nella stessa linea
  K562. All'ampiezza scelta in validazione incrociata su bersagli tenuti fuori
  (α = 0,25 fuori linea, 0,50 stessa linea) l'MSE scende a 0,990 e 0,922.
- **Quindi la compressione è necessaria, ma non è "gratuita" e non è totale.**
  L'argomento del pavimento a zero resta quello corretto per la *forma* della
  decisione: il clamp è sullo score normalizzato, non sull'errore, e comprimere fino a
  zero perderebbe tutti i punti positivi della MSE. La misura aggiunge il numero
  mancante: l'ottimo sta intorno a un quarto dell'ampiezza della sorgente fuori
  lignaggio, non a zero e non a uno.
- **Attenzione a che cosa è stato misurato.** Questi α vengono da K562 e RPE1 in spazio
  pseudobulk log2FC. Non sono punteggi VCC e non sono stati verificati sui contesti
  A/B/C, dove nessuna perturbazione è osservabile. Ciò che si trasferisce è il metodo
  (D-012), non il valore.
- **Riaprire se:** esiste un bundle di valutazione a singola cellula che permetta di
  rifare la stessa scelta su tutte e sei le metriche VCC, oppure se una sorgente di
  lignaggio vicino (CD4) dà un α molto diverso.

### D-007 — K562 resta come ablazione: non è scartata

- **Perché:** è l'unica sorgente locale con copertura del pannello (272/300) e costa
  zero, perché è già sul disco. Le correlazioni fra effetti stimati verso RPE1 sono
  basse (mediana Pearson 0,0905 grezza) ma positive, e le coppie appaiate si
  distinguono da quelle non appaiate.
- **Alternative scartate:** dichiararla inutile perché di lignaggio sbagliato. Il
  lignaggio è un motivo per non farne la sorgente principale, non una misura del suo
  contributo marginale.
- **Limite noto:** la risposta stimabile è povera, mediana 5 geni DE per riga, e la
  numerosità limita la potenza: è un limite inferiore sul segnale, non una sua misura.
- **Riaprire se:** un'ablazione mostra che aggiungerla non migliora nulla.

### D-008 — Si valuta con `cell-eval2 0.16.0`, tutte e sei le metriche

- **Perché:** la strategia dipende dai clamp per metrica, che sono proprietà della
  versione installata. Bloccare versione, preset, backend DE e seed rende confrontabili
  due misure prese in giorni diversi.
- **Alternative scartate:** ottimizzare la sola metrica di discriminazione (PDS),
  scorciatoia attraente perché invariante di scala, ma le altre cinque dipendono
  dall'ampiezza e dalle chiamate DE.
- **Riaprire se:** cambia la versione di `cell-eval2`. In quel caso serve un
  checkpoint, non solo un aggiornamento: i clamp sono la base della strategia.

### D-009 — Un gene non misurato ha una maschera, non uno zero

- **Perché:** riempire con zero un gene che la sorgente non misura inventa evidenza, e
  la inventa nella direzione peggiore, perché "nessun effetto" è una previsione
  plausibile che il modello imparerebbe come osservazione.
- **Come è fatta:** conservare tutti i 18.533 geni di output anche quando l'encoder ne
  usa meno; mantenere una maschera dei geni osservati; registrare gli universi di
  feature di ogni sorgente.
- **Riaprire se:** mai, salvo che si dimostri il contrario. Vale anche per i log2FC
  assenti, non solo per i conteggi.

### D-010 — Il progetto si documenta con mappa, checkpoint, decisioni e registro

- **Perché:** tre documenti di strategia scritti in due giorni si correggevano a
  vicenda senza che il README lo dicesse, e alcune conclusioni corrette restavano
  leggibili come se fossero attuali. Il problema non era la qualità delle analisi ma
  la loro tracciabilità.
- **Alternative scartate:** riscrivere i documenti per renderli coerenti (cancella il
  disaccordo storico, che è informazione); tenere un solo documento aggiornato di
  continuo (si perde il perché dei cambi); un database o una dashboard
  (sproporzionati: qui bastano Markdown e due script).
- **Riaprire se:** il processo costa più di quanto rende, per esempio se i checkpoint
  diventano così frequenti da non essere più letti.

### D-011 — La validazione non si filtra per efficacia osservata delle guide

- **Perché:** scartare le guide che non hanno prodotto un effetto misurabile seleziona
  sull'esito. Il benchmark che ne risulta contiene solo i casi facili e sovrastima il
  modello. E i bersagli che non rispondono sono parte del problema reale: la gara chiede
  di prevedere tutti e 300 i bersagli, compresi quelli il cui effetto è nullo o troppo
  debole per essere chiamato.
- **Come è fatta:** i campi `keep_effective_guides` e `keep_for_DE` degli autori si
  conservano **come annotazioni**, non si usano come filtro di valutazione. Vedi
  `configs/candidate_ingestion.json`, campo `do_not_filter_evaluation_by`.
- **Riaprire se:** si vuole misurare, separatamente e dichiarandolo, quanto cambia il
  punteggio sul sottoinsieme delle guide efficaci.

### D-012 — L'ampiezza si calibra su bersagli tenuti fuori, non si sceglie

- **Perché:** l'ampiezza ottimale non è una proprietà delle metriche, che si possa
  dedurre leggendo i clamp: è una proprietà della *coppia* sorgente-destinazione, e
  cambia con essa. Misurata, vale circa 0,25 da K562 a RPE1 e circa 0,50 fra due
  esperimenti nella stessa linea K562
  (`reports/pipeline/transfer_experiment.json`). Una costante scelta a mano sarebbe
  stata giusta al più per una delle due.
- **Come è fatta:** i bersagli si dividono interi in fold — mai le cellule, e mai le
  guide dello stesso bersaglio su lati opposti; la griglia si cerca solo sui bersagli
  di training; il numero riportato è sui bersagli tenuti fuori. Il criterio di
  selezione è l'MSE aggregato rispetto al nullo, **non** la correlazione, che essendo
  invariante di scala non può scegliere un'ampiezza.
- **Verifica che il protocollo funzioni:** l'α scelto in validazione incrociata
  coincide con l'α oracolo calcolato a posteriori (0,25 contro 0,216; 0,50 contro
  0,472). Se i due divergessero, sarebbe il protocollo a essere rotto.
- **Alternative scartate:** fissare α a 1 (misurato peggiore del nullo); fissarlo a 0
  (equivale al nullo e butta via l'1,0–7,8% di riduzione dell'errore); sceglierlo sulla
  correlazione (non identificabile).
- **Riaprire se:** un bundle a singola cellula permette di calibrare direttamente sulle
  sei metriche VCC, che è la cosa che alla fine conta.

### D-013 — Lo stato di una sorgente lo dichiara il registry versionato

- **Perché:** "abbiamo il dataset" ha significato sei cose diverse nella storia di
  questo progetto — un'accessione che risolve, una dimensione letta, uno schema
  ispezionato, valori campionati, un pilot ingerito, un sottoinsieme utilizzabile su
  disco. Sono affermazioni diverse, e confonderle è il modo in cui una verifica
  diventa un'assunzione.
- **Come è fatta:** `configs/sources.yaml` assegna a ogni fonte un
  `VerificationLevel` ordinato e i percorsi di evidenza che lo sostengono;
  `src/vcc2026/registry.py` rifiuta un livello privo di evidenza, una fonte abilitata
  sotto `sample_verified`, e una copertura internamente incoerente. La copertura è
  scomposta in tre campi distinti — libreria, bersagli osservati, bersagli con
  abbastanza cellule — perché sono tre quantità diverse e il progetto le ha già
  confuse una volta.
- **Riaprire se:** il registry diventa più oneroso da mantenere del registro dei
  documenti che già esiste, o se duplica informazione invece di sostituirla.

### D-014 — Il backend DE si registra accanto a ogni metrica

- **Perché:** D-008 blocca la versione di `cell-eval2` perché i clamp sono proprietà
  della versione. Ma il backend DE **non** è fissato dalla versione: `de.backend='auto'`
  sceglie gpudge (con CUDA), poi pdex, poi scanpy, e il pacchetto stesso avverte che
  «DE numbers differ between engines». Quattro delle sei metriche dipendono da questa
  scelta, quindi due esecuzioni della stessa versione su macchine diverse possono
  produrre numeri non confrontabili.
- **Come è fatta:** `scorer_fingerprint()` in `src/vcc2026/evaluation.py` risolve e
  registra il backend accanto alla versione; finisce nel manifesto di ogni run. Su
  questa macchina si risolve a `scanpy` (pdex assente, nessuna CUDA):
  `reports/pipeline/null_calibration_A.json`.
- **Conseguenza per la macchina remota:** installare pdex o usare una GPU cambia i
  numeri DE. Va fatto una volta e dichiarato, non a metà di una serie di confronti.
- **Riaprire se:** una versione futura di `cell-eval2` fissa il backend, o se si
  misura che le differenze fra engine sono trascurabili rispetto alla variabilità che
  ci interessa.
