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
| D-004 | Ordine di acquisizione: CD4, poi Orion HCT116, poi i benchmark — **sostituita da D-031 per l'ordine operativo** | superata | 2026-09-12 | `docs/candidate_adversarial_review_2026-09-12.md` §5, [CP-0016](checkpoints/0016-piano-operativo-audit-protocollo.md) |
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
| D-015 | Il vincolo compositivo si assorbe sui geni supportati, non su quelli mascherati | attiva | 2026-09-12 | `src/vcc2026/inference.py`, [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.3 |
| D-016 | Non si riduce la densità della previsione per far entrare `vcc prep` nella RAM locale — **sostituita da D-018** | superata | 2026-09-12 | [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.5, [CP-0005](checkpoints/0005-packaging-streaming-trial01.md) §3.1 |
| D-017 | `trial-00-controls` non si invia finché la conformità alle regole non è chiarita | attiva | 2026-09-12 | `docs/SOTTOMISSIONE.md` §2 |
| D-018 | Il packaging si fa a memoria limitata, non su una macchina più grande | attiva | 2026-09-13 | `src/vcc2026/packaging.py`, [CP-0005](checkpoints/0005-packaging-streaming-trial01.md) §3.1 |
| D-019 | La parità con `vcc prep` si dimostra con fixture a forma ufficiale e rifiuti bilaterali | attiva | 2026-09-13 | `tests/test_packaging_parity.py`, [CP-0005](checkpoints/0005-packaging-streaming-trial01.md) §3.5 |
| D-020 | L'oracolo numerico è autonomo: ricalcola, non giudica biologia, e il candidato non è fidato | attiva | 2026-09-13 | `docs/oracle/CONTRATTO.md`, [CP-0007](checkpoints/0007-oracle-pairwise-loss.md), [CP-0009](checkpoints/0009-oracle-json-number-csv-error.md) |
| D-021 | Le consultazioni multi-modello passano da un orchestratore locale che avvii tu — **dal 2026-09-16 anche la catena di cicli, quando Grok lo chiede, al massimo tre campagne per ciclo** | attiva | 2026-09-13, aggiornata 2026-09-16 | `docs/ORCHESTRATORE.md`, `reports/orchestrator/prova-a-secco-2026-09-13/`, `docs/CICLO_GIORNALIERO.md`, [CP-0019](checkpoints/0019-catena-cicli-guardiano.md) |
| D-022 | Un posto vuoto si copre con una seconda sessione del servizio ancora attivo, dichiarata prima e marcata dopo | attiva | 2026-09-14 | `docs/ORCHESTRATORE.md` §9-ter-ter, `configs/orchestrator/orchestrator.yaml`, `tests/test_orchestrator.py` (`StandInTests`) |
| D-023 | La ricerca scientifica è una modalità separata: i livelli di provenienza non si promuovono, le piste le sceglie una regola, le contraddizioni non si chiudono | attiva | 2026-09-14 | `docs/RICERCA_SCIENTIFICA.md`, [CP-0010](checkpoints/0010-modalita-ricerca-scientifica.md), `tests/test_orchestrator_research.py` |
| D-024 | Nel confronto modulare l'universo genico è l'intersezione dei geni effettivamente misurati, non il riempimento a zero | attiva | 2026-09-14 | [CP-0011](checkpoints/0011-primo-benchmark-modulare.md), `src/vcc2026/benchmark/universe.py`, D-009 |
| D-025 | Metrica primaria del pilot modulare: `pooled_mse_vs_null` in spazio proxy; non inferiorità non dichiarata; LOCO a due contesti = trasferimento, non apprendimento generale del contesto | attiva | 2026-09-14 | [CP-0011](checkpoints/0011-primo-benchmark-modulare.md), `configs/benchmark.yaml` |
| D-026 | Tre contesti perturbati: il descrittore di contesto e misurabile, non ancora utile | attiva | 2026-09-14 | [CP-0013](checkpoints/0013-hepg2-terzo-contesto.md), `configs/benchmark_3ctx.yaml` |
| D-027 | Le metriche della gara non si sommano fra generatore e predittore | attiva | 2026-09-14 | [CP-0013](checkpoints/0013-hepg2-terzo-contesto.md), `reports/hepg2_2026-09-14/generator_x_predictor.json` |
| D-028 | Il GO slim non entra nei descrittori: il controllo permutato va come quello vero | attiva | 2026-09-15 | [CP-0014](checkpoints/0014-go-slim-e-gpu.md), `reports/go_slim_2026-09-15/` |
| D-029 | Nessun porting su GPU prima di aver sostituito la SVD completa con una randomizzata | attiva | 2026-09-15 | [CP-0014](checkpoints/0014-go-slim-e-gpu.md), [CP-0015](checkpoints/0015-svd-randomizzata-e-rango.md), `reports/svd_2026-09-15/` |
| D-030 | La griglia di rango della base resta {8, 16}; 32/64/128 non diventano il default | attiva | 2026-09-15 | [CP-0015](checkpoints/0015-svd-randomizzata-e-rango.md), `reports/rank_2026-09-15/` |
| D-031 | Ordine operativo: audit Jiang, poi Jurkat come quarto contesto; CD4 rinviato — **la parte su CD4 è superata da D-039** | attiva | 2026-09-15 | [CP-0016](checkpoints/0016-piano-operativo-audit-protocollo.md), `docs/PIANO_OPERATIVO_2026-09-15.md` |
| D-032 | Protocollo di valutazione congelato; i fold del 14–15 settembre sono sviluppo | attiva | 2026-09-15 | [CP-0016](checkpoints/0016-piano-operativo-audit-protocollo.md), `configs/eval_protocol.yaml` |
| D-033 | Il gate di espressione non è adottato: la regola non è soddisfatta e i due controlli indicano un filtro di rumore, non una regola di contesto | attiva | 2026-09-16 | [CP-0017](checkpoints/0017-gate-espressione-destinazione.md), `reports/expression_gate_2026-09-16/decision.json` |
| D-034 | Il generatore delle sottomissioni è `ControlModel`: cellule nuove, apprese dai controlli del contesto, nessuna cellula di controllo copiata — **proposta del lead, da confermare dal proprietario** | da-verificare | 2026-09-17 | [CP-0020](checkpoints/0020-singola-cellula-cis-generatore.md) §3.3, `reports/generator_null_smoke_2026-09-17/` |
| D-035 | Nessun invio con un generatore pulito se il predittore non produce chiamate: la FID vale `k / max(n_pred, N_conf)` e il silenzio vale 0 | attiva | 2026-09-17 | [CP-0020](checkpoints/0020-singola-cellula-cis-generatore.md) §3.2 |
| D-036 | Il predittore contiene il termine cis (vicini misurati dalla sorgente, prior per distanza altrove); la co-espressione nei controlli non entra | attiva | 2026-09-17 | `reports/cis_2026-09-17/cis_effect.json`, `reports/coexpression_2026-09-17/summary.json` |
| D-037 | Nei banchi il DE è `fast_scorer_de`, verificato identico al percorso scanpy dello scorer | attiva | 2026-09-17 | `reports/fast_de_2026-09-17/parity.json`, `tests/test_sc_pipeline.py` |
| D-038 | Le misure si confrontano con le ancore ufficiali risolte, e non si sottomette senza sapere in quale regime della fedeltà siamo | attiva | 2026-09-17 | `reports/anchors_2026-09-17/anchors.json`, [CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md) |
| D-039 | CD4 entra come sorgente per bersaglio dal pseudobulk letto per righe; primo test a un solo fattore contro trial-01 (t08) | attiva | 2026-09-22 | [CP-0028](checkpoints/0028-cd4-sorgente-flex-trasferimento.md), `reports/cd4_rows_2026-09-22/manifest.json` |

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
- **Aggiornamento 2026-09-12 (CP-0004).** Rimisurato con selezione continua invece che
  su griglia: α = 0,1974, non 0,25. Il valore 0,25 era il punto di griglia più vicino.
  La differenza è praticamente irrilevante (0,98964 contro 0,98929 di MSE/nullo sul
  primo fold) ma il numero da citare è 0,197. Misurato anche che lo **shrinkage per
  gene è quasi inattivo**: `prior_sd` = 4 batte «nessuno shrinkage» di 0,00003 in MSE
  cross-validata. La compressione utile è tutta nell'ampiezza globale.
  Evidenza: `reports/trial_2026-09-12/calibration_c002.json`.
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
- **Aggiornamento 2026-09-12 (CP-0004).** Il protocollo è stato rafforzato in
  `scripts/44_calibrate_transfer.py`: validazione incrociata **annidata**, ciclo
  interno per selezionare e ciclo esterno per riportare, e il bootstrap ricampiona
  solo previsioni fuori campione. Lo stadio 41 calcolava l'intervallo su **tutti** i
  bersagli con i parametri già scelti, che descrive i dati di training. I numeri
  coincidono nella sostanza; è l'intervallo a essere onesto solo nella versione nuova.
  α selezionato su cinque fold indipendenti varia fra 0,1947 e 0,2006.
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

### D-015 — Il vincolo compositivo si assorbe sui geni supportati, non su quelli mascherati

- **Perché:** i conteggi di una cellula sono una composizione, quindi non possono
  salire tutti. Riscalare `basale × 2^Δ` a una dimensione di libreria divide via un
  fattore globale, e quel fattore cade su **ogni** gene — compresi i 10.852 che la
  sorgente non misura e che per D-009 non dovrebbero portare alcuna previsione. Senza
  correzione, una sorgente che copre 7.681 geni su 18.533 farebbe scivolare gli altri
  in una direzione sistematica, su tutte e 300 le perturbazioni, con un'ampiezza pari
  al fattore di riscalatura.
- **Come è fatta:** `compositional_shift` risolve in forma chiusa lo scalare `c` che
  conserva la massa totale, `c = log2(Σ_oss b / Σ_oss b·2^Δ)`, e lo applica **solo**
  ai geni osservati. Dopo la riscalatura un gene non osservato conserva esattamente la
  sua quota di composizione, cioè un log2FC realizzato di 0. Lo scalare è registrato
  per bersaglio nelle diagnostiche, perché è una modifica reale della previsione, non
  un dettaglio numerico.
- **Alternative scartate:** lasciare che la riscalatura sposti tutti i geni (inventa
  evidenza sui geni mascherati, esattamente ciò che D-009 vieta); applicare uno
  scalare globale a tutti i geni (matematicamente identico al caso precedente: uno
  scalare uniforme si cancella nella composizione e non risolve nulla); normalizzare a
  somma fissa senza dichiararlo (l'errore silenzioso).
- **Misurato:** lo spostamento è piccolo — mediana 0,0021 log2, massimo 0,0097 sui
  blocchi del pilot — ma la sua direzione era sistematica e la correzione è esatta.
- **Riaprire se:** si adotta un modello che prevede anche la dimensione di libreria,
  invece della sola composizione. In quel caso il vincolo cambia forma.

### D-016 — Non si riduce la densità della previsione per far entrare `vcc prep` nella RAM locale

> **Sostituita il 2026-09-13 da [D-018](#d-018--il-packaging-si-fa-a-memoria-limitata-non-su-una-macchina-più-grande).**
> La parte da non fare resta valida e vale ancora: non si riduce la densità. La parte
> sulla macchina più grande è caduta — il packaging gira qui, con 0,52 GiB di picco
> ([CP-0005](checkpoints/0005-packaging-streaming-trial01.md) §3.1). La scheda resta
> leggibile perché il ragionamento che la sostiene è ancora quello giusto.

- **Perché:** `vcc prep` carica l'intera matrice in memoria prima di validare
  (`vcc/prep.py`, `adata = read_h5ad(input_path)`), e il suo stesso modello di
  dimensionamento — `vcc/sizing.py`, tarato su 254 esecuzioni di produzione del
  servizio di scoring — dà un picco di 22,2 GiB per una previsione da 2,09·10⁹ valori
  memorizzati e 33,5 GiB per una da 2,17·10⁹. Questa macchina ha 7,81 GiB **totali**.
  Per farci stare il packaging servirebbe scendere a circa 1.150 valori per cellula
  contro i circa 5.800 dei dati reali: cellule quattro volte più sparse del vero, che
  cambierebbero le quattro metriche DE su sei in un modo che non abbiamo misurato.
- **Come è fatta:** la previsione si genera alla densità che il modello produce, il
  contratto si verifica localmente con un lettore a blocchi
  (`scripts/46_validate_package.py`), e il packaging ufficiale si rimanda a una
  macchina con RAM sufficiente. Il collo di bottiglia si dichiara come misura, non si
  aggira.
- **Alternative scartate:** ridurre la densità (falsa il modello per far entrare uno
  strumento); passare `--max-nnz -1` o `--no-check-cell-counts` (non è questo il
  limite che morde, e aggirare la convalida sposta l'errore sulla quota giornaliera);
  costruire il `.vcc` a mano — è un tar con `pred.h5ad.zst` e un `meta.json`, quindi
  sarebbe tecnicamente possibile, ma salterebbe il validatore ufficiale, che è
  l'unica autorità sul formato.
- **Riaprire se:** arriva una macchina con almeno 48 GiB di RAM (vedi
  `docs/ESECUZIONE_REMOTA.md`), oppure `vcc prep` acquisisce un percorso a blocchi che
  non richiede la matrice residente.

### D-017 — `trial-00-controls` non si invia finché la conformità alle regole non è chiarita

- **Perché:** il trial ricampiona le cellule di controllo reali e le etichetta con le
  perturbazioni richieste. `vcc prep` lo accetterebbe — non contiene righe
  `non-targeting` — ma due frasi delle regole ufficiali lo riguardano: «The control
  cells you downloaded are model inputs only — do not copy them into your prediction»
  (pagina Evaluation) e «your predictions must be generated solely by one or more
  machine learning models you use» (Rules, §Machine Learning Predictions Only). Un
  ricampionamento non è la previsione di un modello.
- **Come è fatta:** il trial si genera, si verifica e si conserva come controllo
  operativo e come riferimento di dispersione — le sue cellule sono reali, quindi la
  variabilità fra cellule è giusta per costruzione e rende visibili gli artefatti del
  generatore. Non si carica. La riserva è scritta in `configs/trials.yaml`, campo
  `not_this`, e in `docs/SOTTOMISSIONE.md` §2.
- **Alternative scartate:** inviarlo comunque perché il validatore lo accetta (il
  validatore controlla il formato, non le regole); scartare il trial (perderebbe
  l'unico riferimento di dispersione reale che abbiamo).
- **Riaprire se:** help@virtualcellchallenge.org chiarisce che un baseline di questo
  tipo è ammesso, oppure il proprietario del progetto decide diversamente in modo
  esplicito.

### D-018 — Il packaging si fa a memoria limitata, non su una macchina più grande

- **Sostituisce D-016**, di cui conserva la metà che regge: la densità della
  previsione non si tocca. Cade l'altra metà, «serve una macchina da 32–48 GiB».
- **Perché:** `vcc prep` chiede circa 33,5 GiB per trial-01 perché carica l'intera
  matrice prima di validare (`vcc/prep.py` riga 1104), non perché il problema lo
  richieda. Le convalide si fanno a blocchi di righe e gli array CSR si copiano da
  dataset a dataset. **Misurato: 0,519 GiB di picco**, sulla stessa macchina da 7,81
  GiB, sullo stesso file, con tutte e 24 le convalide attive
  ([CP-0005](checkpoints/0005-packaging-streaming-trial01.md) §3.1).
- **Come è fatta:** `src/vcc2026/packaging.py` e `scripts/48_package_prediction.py`.
  Le convalide sui metadati **sono** le funzioni ufficiali, importate e chiamate su
  un oggetto che espone il solo `.obs` che leggono; quelle sulla matrice sono
  equivalenti a blocchi, negli stessi ordini e con le stesse soglie; otto controlli
  di integrità CSR in più, che servono perché questo percorso copia gli array invece
  di ricostruirli.
- **Confine dichiarato:** vale per gli input che il packager accetta. Matrice densa,
  CSC, dtype diverso da float32, geni fuori ordine, percorso log-normalizzato,
  colonna di tipo cellulare: **rifiutati esplicitamente**, con `vcc prep` indicato
  come lo strumento che li gestisce. Approssimarli in silenzio sarebbe peggio che
  fermarsi.
- **Alternative scartate:** ridurre la densità (falsa il modello per far entrare uno
  strumento — era già la conclusione di D-016); noleggiare una macchina da 48 GiB
  (spesa e attivazione per un lavoro che gira qui); costruire il `.vcc` a mano
  saltando le convalide (sposterebbe l'errore sulla quota giornaliera).
- **Riaprire se:** una previsione futura arriva in un layout che il packager rifiuta,
  o una versione nuova di `vcc-cli` cambia le convalide. In entrambi i casi la strada
  è rifare la parità, non allentare i controlli.

### D-019 — La parità con `vcc prep` si dimostra con fixture a forma ufficiale e rifiuti bilaterali

- **Perché:** un packager alternativo che sia *quasi* d'accordo con lo strumento
  ufficiale è un packager che spedisce una sottomissione che il server rifiuta. E
  l'ispezione del codice non basta: il primo payload scritto qui codificava le
  etichette come `nullable-string-array` invece di `categorical`, differenza
  invisibile a qualunque confronto sui valori, causata da un passaggio — il
  costruttore di `AnnData` — che nel codice di `prep` non si vede
  ([CP-0005](checkpoints/0005-packaging-streaming-trial01.md) §3.4).
- **Come è fatta:** `tests/test_packaging_parity.py`. I fixture hanno la **forma
  ufficiale completa** — 300 × 400 × 3, 18.533 geni, le liste vere, ogni limite
  attivo — e densità sintetica per costare secondi. Per ogni regola un fixture che la
  viola, con l'asserzione che **entrambe** le implementazioni lo rifiutino: un
  rifiuto solo nostro blocca una sottomissione valida, uno solo di `prep` ne
  spedisce una invalida. Più i confronti di codifica e dtype HDF5 elemento per
  elemento, e due test che verificano che la verifica stessa **fallisca** su un
  valore o un'etichetta alterati.
- **Che cosa i fixture non coprono:** la densità. Un valore memorizzato per cellula
  contro i circa 6.000 reali; la densità è esercitata dal controllo sul tetto e dal
  run reale, e va detto invece di lasciarlo intendere.
- **Riaprire se:** cambia la versione di `vcc-cli`. I test importano `vcc.prep` e
  falliranno da soli se una convalida cambia; è il segnale che serve rifare il
  lavoro, non silenziare i test.

### D-020 — L'oracolo numerico è autonomo: ricalcola, non giudica biologia, e il candidato non è fidato

- **Perché:** un orchestratore multiagente può far convergere due modelli su un
  numero sbagliato. Serve un verificatore che rifà i conti dai dati, senza
  LLM in mezzo, e che non prenda dal candidato le soglie o le formule. Il
  primo tipo di affermazione è un confronto di loss su casi appaiati, piccolo
  abbastanza da collaudare il contratto prima di allargarlo.
- **Come è fatta:** `src/oracle/`, contratto in `docs/oracle/CONTRATTO.md`.
  Aritmetica razionale esatta (`fractions.Fraction`) dalla versione 0.2.0;
  le stringhe decimali del report sono solo visualizzazione. Dalla 0.2.1
  i campi numerici del JSON (candidato e configurazione) sono numeri
  JSON, non stringhe, e un `csv.Error` del parser è un esito `error`.
  CLI `python -m oracle`. Il JSON candidato può dichiarare medie,
  differenza e conclusione; le chiavi di autorità (`abs_tol`,
  `equivalence_threshold`, `formula`, …) sono ignorate. L'esito `pass`
  richiede che tutti i controlli richiesti siano stati completati.
- **Che cosa non è:** non valuta se A generalizza, se è statisticamente
  superiore, se è biologicamente più corretto, o se il protocollo di
  valutazione è valido. Non esegue test statistici. Non importa
  `orchestrator` né `vcc2026`. Non è stato eseguito su loss della gara.
- **Alternative scartate:** far giudicare l'ipotesi da un modello (circolare);
  far scrivere al candidato il vincitore "corretto" (il verificatore deve
  derivarlo); mettere il prototipo dentro `src/orchestrator/` (accoppierebbe
  due lavori ancora instabili).
- **Riaprire se:** si vuole un secondo tipo di affermazione, un test
  statistico, o una chiamata esplicita dall'orchestratore. L'allaccio non
  deve avvenire con un import silenzioso.
### D-021 — Le consultazioni multi-modello passano da un orchestratore locale che avvii tu

- **Perché:** più modelli su una stessa domanda producono molto testo e poche prove. Senza
  un registro di che cosa è stato chiesto, a chi, in che ordine, e perché ci si è fermati,
  resta una catena di riassunti — cioè il modo esatto in cui questo progetto ha già perso
  dei caveat (CP-0002). Serviva anche un limite: un ciclo «fino a convergenza» senza tetto
  consuma quote gratuite senza produrre evidenza.
- **Come è fatta:** `src/orchestrator/`, avviata solo a mano con `orch start`. Nessuno
  scheduler. Instradamento, contatori, timeout e condizioni di arresto sono codice
  deterministico che legge solo la configurazione; una risposta di un modello può riempire
  campi previsti e non può cambiare una regola. Prompt e risposte si scrivono una volta
  sola e non si sovrascrivono. L'accordo fra due modelli è registrato come
  `proposals_converged`, che non è `verified_complete`: quest'ultimo richiede controlli il
  cui valore atteso stava nell'incarico prima della domanda.
- **Il codice prodotto dai modelli non si esegue.** Finisce in `steps/*/quarantine/` come
  artefatto da revisionare; `execution.model_code: run` è rifiutato dal caricatore della
  configurazione. Eseguire richiede un meccanismo separato, che non esiste.
- **Alternative scartate:** chiamare le API a pagamento dei quattro servizi (fuori da
  D-005: nessun servizio a pagamento su questa macchina); estrarre i token di sessione dal
  browser per interrogare endpoint privati (fragile e fuori dai termini d'uso: una pagina
  guidata fallisce visibilmente, un endpoint copiato fallisce in silenzio); lasciare il
  ciclo a un agente che decide da sé quando ripartire.
- **Che cosa non è ancora dimostrato:** che gli adattatori verso i servizi reali sappiano
  inviare e leggere. Al 13 settembre 2026 il motore è stato eseguito con risposte preparate
  a mano, e DeepSeek e Kimi sono stati solo **aperti e osservati** nel browser, da profili
  non autenticati (`reports/orchestrator/sonde-2026-09-13/`). Nessun messaggio è stato
  inviato a nessun servizio.
- **Riaprire se:** un servizio cambia interfaccia al punto da rendere inaffidabile il
  canale web; oppure se diventa disponibile un accesso programmatico compreso negli
  abbonamenti, che renderebbe superflua l'automazione del browser.
- **Aggiornata il 2026-09-16, per scelta del proprietario.** Il testo sopra resta com'era
  al 13 settembre. Da oggi valgono due cambiamenti.
  1. Grok non passa più dal browser. È disponibile Grok Build, un CLI compreso
     nell'abbonamento SuperGrok, installato qui (`grok 1.0.30`) e usato dalla catena di
     cicli in sola lettura: è la seconda condizione di riapertura qui sopra. Il profilo
     web di Grok resta `verified: false` e non viene usato. DeepSeek e Kimi restano sul
     web.
  2. L'orchestratore non lo avvia più soltanto il proprietario: nella fase 4 di ogni ciclo
     **Grok decide se servono campagne e lo script le avvia**, fino a **tre per ciclo**.
     È l'alternativa che la versione del 13 settembre scartava («un agente che decide da
     sé quando ripartire»). Il proprietario l'ha scelta con questi paletti:
     - Grok compila solo i campi di testo di un modello fisso; percorso `deep_kimi`,
       limiti e regole li mette lo script;
     - lo script valida l'incarico con `orch brief` prima di avviarlo;
     - gli allegati vengono solo da estratti preparati dallo script;
     - dopo ogni campagna Grok legge il rapporto e può chiederne un'altra, entro il
       tetto;
     - il codice prodotto dai modelli resta non eseguito.

  `orch start` a mano resta possibile. Contratto: `docs/CICLO_GIORNALIERO.md` §6;
  registrazione: [CP-0019](checkpoints/0019-catena-cicli-guardiano.md).
- **Che cosa non è ancora dimostrato, dopo l'aggiornamento:** nessuna campagna è mai
  partita dalla catena. Le prove usano un orchestratore simulato
  (`tests/test_daily_cycle.py`); con quello vero è stata fatta solo la validazione di un
  incarico generato, che non contatta nessun servizio.
- **Riaprire anche se:** una campagna avviata dalla catena consuma quote senza produrre
  un rapporto utile, oppure Grok chiede campagne per abitudine. In quel caso si abbassa
  il tetto o si spegne l'avvio (`orchestratore.abilitato` in
  `configs/ciclo_giornaliero/ciclo.json`).

### D-022 — Un posto vuoto si copre con una seconda sessione del servizio ancora attivo

- **Perché:** la sera del 13 settembre Kimi ha risposto «troppo traffico» a ripetizione. Con
  la sola politica dell'assenza il ciclo prosegue a una voce e, dopo due round di fila, si
  ferma: corretto quando il servizio manca davvero, sprecato quando l'altro sta lavorando
  bene. Una seconda sessione del servizio che risponde tiene due voci nel round.
- **Perché *quello attivo*:** una seconda Kimi troverebbe lo stesso sovraccarico che ha
  fermato la prima. La riserva ha senso solo se è del servizio che sta ancora consegnando,
  quindi — con due risolutori — quella del compagno. Il caricatore rifiuta una riserva
  della stessa famiglia del titolare, così l'errore non si scopre a run avviato.
- **Come è fatta:** `stand_in:` nella route, mappa ruolo → servizio, letta prima
  dell'avvio. Una riserva riusa la mappa di selettori già verificata (`profile`) e ha una
  cartella di sessione sua (`profile_dir`), perché Chrome non apre due volte lo stesso
  profilo e serve comunque un accesso separato. Al superamento di `absence_tolerance` il
  posto passa alla riserva (`seat_reassigned`) invece di far fallire il run; se la riserva
  non è raggiungibile il round prosegue a una voce, come se non ci fosse.
- **Il prezzo, e dove è scritto:** due sessioni dello stesso modello non sono due modelli, e
  un accordo fra loro è un modello che concorda con sé stesso. La convergenza decisa su un
  round coperto esce con motivo `..._same_model`; la frase a schermo lo dice; il rapporto lo
  ripete sotto le proposte finali e fra le decisioni che restano all'operatore. Alla riserva
  viene detto che sta subentrando e che la proposta lasciata nel ruolo non è sua; al
  compagno viene detto che sta leggendo il proprio stesso modello e che deve valutarlo con
  più severità.
- **Alternative scartate:** sostituire in silenzio (contro la regola dell'operatore, e
  renderebbe il rapporto falso); fermare tutto a ogni assenza (spreca un servizio che
  funziona); una seconda istanza del servizio caduto (stessa coda, stesso blocco);
  chiedere all'operatore che fare a ogni assenza, con una domanda bloccante a schermo (un
  run non presidiato si fermerebbe ad aspettare una persona, che è ciò che il progetto
  vuole evitare).
- **Riaprire se:** i round coperti da una riserva diventano la norma invece dell'eccezione
  — a quel punto il ciclo non è più un confronto fra modelli diversi e va ripensato — oppure
  se si aggiunge un terzo servizio, che renderebbe la riserva una scelta fra più famiglie
  invece che l'unica disponibile.

### D-023 — La ricerca scientifica è una modalità separata, e non promuove nulla

- **Perché separata dal ciclo di debug:** quel ciclo porta due modelli a convergere su una
  proposta, e il suo esito migliore è l'accordo. Una campagna di ricerca che ottimizzasse
  l'accordo produrrebbe la cosa peggiore possibile: due modelli che si confermano a
  vicenda una rassegna della letteratura scritta a memoria. Qui il successo è una sintesi
  **tracciabile** — che cosa è stato cercato, che cosa trovato, che cosa sostiene o
  contraddice un'ipotesi, che cosa resta da verificare — e l'accordo non ne fa parte.
- **Come è fatta:** `mode: scientific_research` nell'incarico sceglie
  `src/orchestrator/research/`, che riusa il motore esistente e cambia la forma della
  campagna in tre fasi: ricerca indipendente, confronto e piste, ricerca mirata e sintesi.
  La vista di ogni fase è costruita una volta sola prima di interrogare chiunque, così
  l'ordine dei contatti non dà nulla al secondo. Gli incarichi senza `mode:` valgono
  `debug` e si comportano esattamente come prima.
- **I livelli di provenienza non si promuovono.** Una query è *proposta*, *dichiarata dal
  worker*, o *osservata negli artefatti del canale*. Il livello lo assegna il programma,
  mai la risposta; e il terzo **non è raggiungibile da nessun percorso di codice**, perché
  il browser mostra che l'interruttore di ricerca era acceso e non quali query siano state
  eseguite. Un test fallisce il giorno in cui qualcuno ne aggiunge uno senza l'artefatto
  che lo giustifichi. Lo stesso vale per le fonti: *trovata in un elenco*, *abstract*,
  *testo o sezione*, *non accessibile* sono livelli **dichiarati**, perché non abbiamo
  guardato nessuno leggere.
- **Le fonti si deduplicano su un identificatore, mai sulla somiglianza.** DOI normalizzato
  o URL normalizzato; mancando entrambi, corrispondenza esatta di titolo, autori e anno.
  Due titoli che si assomigliano sono di regola due articoli, e una fusione sbagliata
  distrugge il record di chi ha trovato cosa. Lo stesso paper trovato da entrambi è una
  fonte sola, ma i livelli di consultazione restano separati per worker.
- **Le piste le sceglie una regola, non un modello:** la prima pista ben formata di ciascun
  worker — ipotesi, evidenze di partenza, spiegazione alternativa, ricerca che le distingue
  — ordinate per ruolo, deduplicate, al massimo due. Nessun ripescaggio: se i due propongono
  la stessa pista, la pista è una sola, e il fatto che coincidano è un'informazione.
  Nessun modello viene interrogato su come spendere il budget residuo.
- **Il programma non chiude nessuna contraddizione, e non inventa una sintesi.** Non è in
  grado di leggere la fonte che deciderebbe un disaccordo; il dossier conserva le due
  sintesi separate e verbatim. Una sintesi affidata a un LLM resta un'opzione futura
  esplicita, con un budget proprio. Le dichiarazioni di saturazione dei worker restano
  dichiarazioni attribuite: «non abbiamo trovato evidenze nelle ricerche registrate» non
  diventa «non esistono evidenze».
- **L'oracolo numerico non entra qui.** `src/oracle/` ricalcola confronti di loss da CSV e
  non è un verificatore della letteratura (D-020): un test verifica che la modalità non lo
  importi affatto.
- **Alternative scartate:** un solo ciclo con un prompt diverso (l'esito resterebbe
  `proposals_converged`, cioè accordo, che qui è il segnale sbagliato); far scegliere le
  piste a uno dei due worker o a Claude (metterebbe un giudizio nel punto in cui si spende
  il budget); far scrivere il dossier a un terzo modello (una sintesi consensuale nasconde
  proprio i disaccordi che la campagna deve consegnare); chiudere una contraddizione quando
  un worker dichiara di averla risolta (sarebbe una parte in causa che si autoassolve).
- **Che cosa non è ancora dimostrato:** che DeepSeek o Kimi rispondano a un prompt di
  ricerca, e che le distinzioni reggano su risposte vere. Al 14 settembre 2026 esiste solo
  una prova a secco con risposte scritte a mano
  (`reports/orchestrator/prova-a-secco-ricerca-2026-09-14/`). **Kimi non ha un controllo di
  ricerca osservato**, quindi una campagna reale gira oggi con un canale che cerca e uno
  che pianifica, e il rapporto lo dichiara.
- **Riaprire se:** una campagna reale mostra che i worker riempiono i livelli di
  consultazione senza riguardo, nel qual caso il contratto va stretto o la modalità va
  ripensata; oppure se un canale comincia a esporre le query eseguite, che renderebbe
  raggiungibile `observed_in_channel` e cambierebbe il valore di tutto il registro.

### D-024 — Universo genico = intersezione misurata, non riempimento a zero

- **Perché:** LowRankRidge riempie i geni non osservati a zero prima della SVD.
  Quello zero è letto come «nessun effetto», che è una previsione plausibile, e
  inventa evidenza (D-009). Fra K562 e RPE1 i pannelli non coincidono: riusarlo
  indiscriminatamente mescolerebbe assenze di misura con assenze biologiche.
- **Come è fatta:** `src/vcc2026/benchmark/universe.py` tiene l'AND delle maschere
  `observed`. SVD e loss vedono solo quell'universo. Un array ancora largo
  18.533 viene rifiutato. La copertura persa è scritta in
  `reports/benchmark_2026-09-14/gene_universe.json` (6700/18533 con k562_essential,
  6714 senza).
- **Alternative scartate:** zero-fill (non neutrale); fattorizzazione con loss
  mascherata (implementabile, non usata in questo pilot: si riapre se serve
  recuperare i geni esclusi senza inventare zeri).
- **Riaprire se:** si implementa una fattorizzazione mascherata e si misura che
  recupera i geni fuori intersezione senza trattarli come invariati.

### D-025 — Metrica primaria proxy, niente non-inferiorità, LOCO a due contesti = trasferimento

- **Perché:** senza metrica fissata prima si sceglie dopo aver visto il test. Senza
  un margine di non inferiorità misurato sulla ripetibilità della baseline, «non
  inferiore» è una frase vuota. Con due contesti perturbati, tenere fuori uno
  lascia un solo contesto di training: il descrittore di contesto non varia, e
  il test non identifica una dipendenza generale dal contesto.
- **Come è fatta:** `configs/benchmark.yaml` fissa `pooled_mse_vs_null` in spazio
  log2FC pseudobulk, `non_inferiority_margin: null`, e
  `context_dependence_identifiable: false` sulle direzioni. Alpha 0,1974 è
  rifiutato nel codice. I NTC del contesto di test sono ammessi e condivisi fra
  i bracci. Nessuna variante è scelta sul test esterno.
- **Misurato:** [CP-0011](checkpoints/0011-primo-benchmark-modulare.md). Esito del
  confronto architetturale: inconcludente per l'adozione. Low-rank con e senza
  contesto: MSE identica a quattro decimali.
- **Riaprire se:** esiste un terzo contesto perturbato locale con bersagli
  condivisi, che renderebbe `z_c` variabile in training; oppure un bundle a
  singola cellula che permetta di fissare la metrica primaria sulle sei metriche
  VCC e un margine di non inferiorità dalla ripetibilità della baseline.

### D-026 — Tre contesti perturbati: il descrittore di contesto è misurabile, non ancora utile

- **Perché:** D-025 si riapre alla sua stessa condizione — «esiste un terzo
  contesto perturbato locale con bersagli condivisi». HepG2 Nadig è stato
  acquisito, verificato e trasformato in firme con la stessa definizione delle
  altre. Da qui in poi ogni fold esterno addestra su due contesti, quindi il
  descrittore di contesto varia in training e il confronto con/senza contesto
  diventa **identificabile**. Identificabile non vuol dire conclusivo: con due
  valori il modello può distinguere i contesti, non può imparare come la risposta
  dipenda dal contesto in generale, e ogni contesto viene da un esperimento solo,
  quindi biologia e provenienza restano confuse.
- **Come è fatta:** `configs/benchmark_3ctx.yaml` fissa tre fold esterni
  (K562+RPE1 → HepG2, K562+HepG2 → RPE1, RPE1+HepG2 → K562), lascia fuori
  `k562_essential` così che i due dataset K562 non possano finire su lati
  opposti, tiene la metrica primaria e il margine `null` di D-025, e fissa
  **prima dei run** la regola con cui il trasferimento combina due sorgenti: peso
  uguale per contesto biologico, diviso fra i dataset di quel contesto
  (`context_equal_weights`). L'ampiezza si calibra su una coppia interna al
  training fra due contesti diversi, etichettata `cross_context_within_training`;
  alpha 0,1974 resta rifiutato nel codice.
- **Misurato:** [CP-0013](checkpoints/0013-hepg2-terzo-contesto.md). Il
  descrittore di contesto non aiuta in modo sistematico (media della differenza
  con − senza: +9,73 sulla MLP unica, +0,02 sul low-rank, −0,05 sulla base
  congelata); la differenza appaiata favorevole alla base congelata misurata in
  CP-0011 cambia segno in tutti e tre i fold.
- **Riaprire se:** esiste un **quarto** contesto perturbato, di lignaggio diverso
  dai tre, con bersagli condivisi: è la prima configurazione in cui un fold lascia
  tre contesti in training e «il descrittore non porta informazione» diventa
  distinguibile da «due valori non bastano a stimarne l'uso». Oppure se compare un
  modo di separare biologia e batch dentro un contesto solo.

### D-027 — Le metriche della gara non si sommano fra generatore e predittore

- **Perché:** sulle cellule HepG2 reali, cambiare **solo** il generatore porta il
  Jaccard sui geni significativi da 0,003 a 0,120 su un modello che predice
  *nessun cambiamento*, e azzera contemporaneamente la direction fidelity. Il
  predittore invece domina la PDS (0,738 contro 0,425 del nullo). Un guadagno sul
  punteggio complessivo non dice quale dei due fattori l'ha prodotto, e una
  metrica che premia il realismo del generatore può essere alzata senza alcuna
  capacità predittiva.
- **Come è fatta:** ogni misura sulle sei metriche dichiara **quale generatore** e
  **quale predittore** l'ha prodotta, e i due non si variano insieme. Il confronto
  fra generatori usa gli stessi controlli reali in tutti i bundle
  (`control_source: real`) e le stesse cellule di riferimento. Per un dataset
  esterno si riportano metriche grezze, senza inventare ancore: nessuna
  normalizzazione e nessun punteggio di leaderboard
  (`scripts/57_generator_x_predictor.py`).
- **Misurato:** [CP-0013](checkpoints/0013-hepg2-terzo-contesto.md) §3, tabella
  generatore × predittore su 25 bersagli.
- **Riaprire se:** una misura con più bersagli e con intervalli mostra che le due
  direzioni non si contraddicono, oppure se la gara pubblica ancore che rendano le
  sei metriche confrontabili fra loro su un dataset esterno.

### D-028 — Il GO slim non entra nei descrittori, e il controllo permutato dice perché

- **Perché:** la regola era scritta in `docs/ENCODER_INPUTS.md` §6 prima che il run
  esistesse, e le sue due condizioni di scarto sono scattate entrambe. B1 (basale +
  contesto + 140 bit GO) non batte B0 (basale + contesto): è peggio in 10 confronti
  appaiati su 12. E B3, che usa le **stesse** 140 colonne con i valori mescolati fra
  i geni a seed fisso, va come B1. Il legame gene↔annotazione non porta segnale in
  questo disegno; le colonne si comportano come 140 colonne qualsiasi della stessa
  sparsità.
- **Come è fatta:** il codice resta, spento. `DescriptorBank.include_go_slim` è
  `false` per impostazione predefinita; la tabella congelata
  (`<data_root>/artifacts/g001/go_slim_table.npz`) e `scripts/58_build_go_slim_table.py`
  restano, con gli sha256 delle quattro fonti nel manifesto, perché un esperimento
  negativo deve poter essere rifatto. `configs/benchmark_go_slim.yaml` è il
  protocollo eseguito, non una proposta.
- **Misurato:** [CP-0014](checkpoints/0014-go-slim-e-gpu.md) §3.2, run `g002`,
  `reports/go_slim_2026-09-15/`.
- **Non segue da questa decisione:** che l'annotazione funzionale sia inutile in
  generale, né che convenga passare a un embedding più grande. La riserva (ProtT5,
  ESM-2, gene2vec) **non** si apre: se l'annotazione curata non batte la propria
  permutazione, un vettore più grande non risponde a questa domanda.
- **Riaprire se:** il disegno cambia in modo che l'annotazione possa agire — per
  esempio con un quarto contesto perturbato, o con un decoder che condivida
  parametri fra geni della stessa categoria invece di trattare i bit come colonne
  indipendenti; oppure se un run con tutti i 2.315 bersagli condivisi, invece dei
  160 del pilot, mostra un effetto che qui era sotto la risoluzione.

### D-029 — Nessun porting su GPU prima di aver tolto la SVD completa

- **Perché:** il codice attuale non può usare una GPU — ogni decoder è numpy scritto
  a mano, `torch` non è nemmeno una dipendenza, e l'unico `import torch` del
  progetto serve a chiedere se esiste CUDA per lo scorer. E anche potendo, al
  formato del pilot l'aritmetica è 1,3 s su 223: non c'è niente da accelerare.
  Quando il formato crescerà, il passo che esplode è la SVD, e lì la leva è
  algoritmica: `MaskedLowRank.fit` calcola **tutti** i valori singolari per
  tenerne 16. Misurato su matrici di risposta reali, una SVD randomizzata di rango
  16 vale 11,9× a 320 righe e 42,2× a 1.280, con l'1,3–1,6% di errore sui valori
  singolari — più di quanto una GPU darebbe su queste forme, su CPU, per una
  funzione.
- **Come è fatta:** `requirements-gpu.txt` esiste e **non contiene torch**:
  contiene `gpudge` e `pdex`, cioè i backend di differential expression che
  accelerano lo scorer, che è l'unico punto con un percorso GPU già scritto.
  `docs/CONSEGNA_GPU.md` dice che cosa trasferire e quali comandi lanciare, e
  quale comando usa davvero la scheda (uno solo: l'esperimento sulle sei
  metriche). `scripts/59_gpu_readiness.py` rimisura tutto sulla macchina di
  destinazione, e `de_backend_resolved` va letto: se dice ancora `scanpy`, la GPU
  non sta entrando.
- **Misurato:** [CP-0014](checkpoints/0014-go-slim-e-gpu.md) §3.4,
  `reports/gpu_2026-09-15/gpu_readiness.json`.
- **Aggiornamento 2026-09-15 (CP-0015).** La randomizzata esiste, è
  configurabile, ed è stata rimisurata **sulle predizioni**, non solo sui
  valori singolari. La regola di sostituzione scritta prima dei run (banda
  0,01 sul pooled appaiato, ogni fold) **non** è soddisfatta: 4 fold su 48
  escono dalla banda, tutti `modular_frozen` con contesto, segni misti.
  L'1% di errore sui valori singolari convive con un 18% di differenza fra
  le due ricostruzioni di rango 16. Metodo predefinito: `exact`.
  `randomized` resta un flag. Il risparmio reale su questo formato è 124 s
  di orologio su 331 s, non 9,7×, e il picco RSS non si muove. Nessun
  porting GPU ne segue.
- **Riaprire se:** la randomizzata viene adottata come default dopo una
  misura che soddisfa una regola prefissata sulle predizioni, e la SVD non
  è più il collo di bottiglia; oppure se si decide di addestrare un modello
  generativo di conteggi, che è l'unico lavoro previsto in cui una GPU
  sarebbe il primo strumento e non l'ultimo (R-4, `ESECUZIONE_REMOTA.md` §4).

### D-030 — La griglia di rango resta {8, 16}

- **Perché:** allargare a {16, 32, 64, 128} fa scegliere 64 al lowrank su
  tutti e tre i fold seen, e quel 64 **peggiora** il test esterno di
  0,14–0,35 di MSE/nullo contro la griglia {8, 16}, IC senza zero. Il frozen
  "sceglie" 128 su una griglia interna piatta (differenze ~10⁻⁴): non è una
  selezione. Il rango 16 cattura il 50% della varianza di *questa* matrice
  di training; il 128 ne cattura l'87% e non è per questo il migliore in
  trasferimento.
- **Come è fatta:** `configs/benchmark.yaml` e `configs/benchmark_3ctx.yaml`
  restano a `rank_grid: [8, 16]`. `configs/benchmark_rank.yaml` è il
  protocollo eseguito, non una proposta. Nessun yaml storico è stato
  riscritto.
- **Misurato:** [CP-0015](checkpoints/0015-svd-randomizzata-e-rango.md) §3.3,
  `reports/rank_2026-09-15/rank_summary.json`.
- **Riaprire se:** un run con tutti i 2.315 bersagli condivisi, o un quarto
  contesto, mostra che un rango >16 scelto internamente **trasferisce** sul
  test; oppure se la validazione interna diventa un vero fold
  cross-context con abbastanza bersagli da distinguere 16 da 32 sul frozen.

### D-031 — Ordine operativo: Jiang, poi Jurkat; CD4 rinviato

- **Perché:** il piano approvato il 15 settembre mette in testa la diversità
  di contesto (sei linee Jiang, Jurkat T) sugli studi già consigliati dal
  profilo della gara. CD4 resta la migliore copertura del pannello 300
  (297/300 in libreria) ma i single-cell pesano 1,7 TB: non è il primo
  download. Orion resta condizionato alla licenza.
- **Come è fatta:** Jiang è `metadata_verified`, non abilitato, RDS non
  aperti. Jurkat è candidato quarto contesto sul mirror da 1,29 GB, file
  non aperto oggi. Entrambi i blocchi grandi vanno su un runtime che abbia
  misurato disco e persistenza: questa macchina il 15 settembre aveva
  11,3 GiB liberi e non può tenere il pavimento da 10 GiB se scarica TGFB.
- **Evidenza:** [CP-0016](checkpoints/0016-piano-operativo-audit-protocollo.md),
  `reports/jiang_2026-09-15/jiang_probe.json`,
  `reports/nadig_reconcile_2026-09-15/nadig_reconciliation.json`,
  `reports/runtime_2026-09-15/runtime_inventory.json`.
- **Cosa resta di D-004:** CD4 è ancora la pista di copertura e di lignaggio
  verso A. Non è scartata; è dopo l'audit dei dataset esplicitamente
  consigliati. Non contare GEO, Zenodo e S3 come tre fonti distinte.
- **Riaprire se:** Jiang non ha NTC abbinabili o counts grezzi; Jurkat
  mirror non è lo stesso esperimento GEO; oppure una sorgente CRISPRi in
  linea T matura o squamosa diventa scaricabile sotto tetto di byte.

### D-032 — Protocollo di valutazione congelato

- **Perché:** i fold del 14–15 settembre (m001–m004, g001–g002, s001–s002,
  r001, generatore×predittore HepG2) sono già stati consultati. Un seed
  nuovo sulle stesse tre linee non è una replica biologica. Senza un
  protocollo scritto prima, ogni confronto successivo diventa sviluppo
  camuffato da conferma.
- **Come è fatta:** `configs/eval_protocol.yaml` è `frozen: true`. Due
  compiti (`new_context_seen_target`, `new_context_unseen_target`). NTC
  del contesto query ammessi; risposte perturbate del query vietate.
  Seed di conferma **4242**, non ancora aperto. Seed 2026 e 2027 =
  sviluppo. Ancore locali con cellule disgiunte; la media perturbativa
  ufficiale è un'ancora, non un predittore. Sei metriche grezze, mai
  mediate. Promozione solo se l'IC95 appaiato su dati di conferma è
  interamente favorevole e non ci sono danni oltre tolleranza.
- **Misurato:** 12 split esistenti, 0 fallimenti di leakage algebrico,
  tutti etichettati sviluppo.
  `reports/eval_protocol_2026-09-15/split_audit.json`.
- **Riaprire se:** arriva un quarto contesto con split già congelati, o
  ancore ufficiali `b`/`r` per un dataset esterno, o si decide una
  submission diagnostica senza conferma indipendente (resta esplorativa).

### D-033 — Il gate di espressione non è adottato, e i controlli dicono perché

- **Perché:** la regola era scritta in `configs/benchmark_expression_gate.yaml` prima
  che il run esistesse, e non è soddisfatta. «Batte ShrunkTransfer in tutti e tre i
  fold» vale in **1 split su 6** per tutte e tre le varianti. Soprattutto: il gate
  costruito sulla **sorgente** batte quello costruito sulla destinazione in 4 split su 6
  (G1), e il gate **permutato** batte quello vero in 2 su 6. Quel poco che si guadagna
  non viene dal legame gene-contesto, ma dal comprimere i geni poco espressi in
  generale: è un filtro di rumore, e va chiamato così. In più la selezione è instabile —
  identità in 23 righe su 27 con un seed e in 7 su 27 con l'altro, dove i due seed
  cambiano solo i 32 bersagli di validazione interna.
- **Come è fatta:** il codice resta, spento. `src/vcc2026/presence.py` e
  `src/vcc2026/benchmark/gate.py` girano solo se una configurazione dichiara
  `expression_gate`; `configs/benchmark_3ctx.yaml` è invariato e i suoi risultati
  riprodotti riga per riga (54 righe, differenza assoluta 0,0). Un braccio gate è
  `shrunk_transfer` moltiplicato per un peso, con alpha e prior_sd non ricalibrati, e il
  run si ferma se la base non coincide con la riga di `shrunk_transfer`.
- **Misurato:** [CP-0017](checkpoints/0017-gate-espressione-destinazione.md) §3, run
  `x001`, `reports/expression_gate_2026-09-16/`.
- **Non segue da questa decisione:** che l'idea sia sbagliata. Nel banco l'universo
  genico è l'intersezione di tre pannelli e non contiene geni spenti (0–2 sotto 5 CPM
  per contesto); nei contesti ufficiali ce ne sono 8.409–8.923 su 18.533. La regola è
  stata misurata dove poteva esserlo, non dove conterebbe.
- **Riaprire se:** esiste un banco in cui la destinazione porta l'asse genico intero,
  cioè in cui i geni spenti esistono e hanno una risposta osservata con cui confrontarsi;
  oppure se si misura il gate con l'ampiezza ricalibrata insieme al peso, che qui è stata
  tenuta fissa per far variare un fattore solo.

### D-034 — Il generatore delle sottomissioni è `ControlModel` (proposta)

- **Perché:** il generatore di trial-01 disegna ogni cellula dallo stesso profilo medio, e
  a effetto zero lo scorer vi trova 93 geni significativi per pseudo-bersaglio da 100
  cellule, l'89% «in su», contro 0,0 delle cellule reali. `ControlModel` (stati KDE) ne
  trova 0,0 e rileva 5.926 geni per cellula contro 5.925 reali
  ([CP-0020](checkpoints/0020-singola-cellula-cis-generatore.md) §3.3).
- **Come è fatta:** per ogni contesto, PCA dei geni variabili dei controlli; stato nuovo
  campionato vicino a uno stato osservato; composizione decodificata come media dei 30
  controlli più vicini; dispersione per gene adattata agli zeri o alla varianza; conteggi
  Gamma-Poisson nuovi. Nessuna cellula di controllo entra nella previsione, e il test
  `test_counts_are_new_integers_on_the_same_axis` lo verifica. È la lettura del progetto
  della frase «the control cells you downloaded are model inputs only».
- **Perché è una proposta:** è la stessa zona grigia di D-017 e di O2 del piano del 16. Il
  proprietario può rovesciarla, e una domanda a help@virtualcellchallenge.org la
  chiuderebbe.
- **Riaprire se:** gli organizzatori dicono che un generatore costruito sui controlli non
  è ammesso; oppure la calibrazione nulla a scala piena (72, run `n001` su Colab) mostra
  chiamate spurie molto sopra il reale-contro-reale.

### D-035 — Un generatore pulito non si invia senza chiamate informative

- **Perché:** in `cell_eval2` 0.16.0 la FID vale `k / max(n_pred, N_conf)`. Una
  previsione che non chiama nulla prende 0 su ogni bersaglio con geni significativi nel
  riferimento, cioè −1,71 in scala con le ancore stimate il 16 settembre, circa −0,29 sul
  complessivo. Le docstring riportano che in `val` tra il 70% e l'88% dei bersagli ha
  almeno 10 geni significativi.
- **Come è fatta:** ogni braccio dei banchi 73 e 75 riporta `sig/t`, il numero di
  chiamate per bersaglio, accanto alle sei metriche. Un candidato si invia solo se `sig/t`
  è confrontabile con quello della replica del banco, oppure se la differenza è motivata
  per iscritto.
- **Riaprire se:** cambia la definizione della FID, oppure un banco mostra che la FID
  resta sopra la baseline con poche chiamate.

### D-036 — Termine cis sì, co-espressione no

- **Perché:** entro 1 kb dal TSS del bersaglio, gli effetti K562 e HepG2 degli stessi
  bersagli correlano 0,57, e il segno coincide nel 97,5% delle 122 coppie con |log2FC K562|
  > 0,5; tra 1 e 5 kb la correlazione è 0,72
  (`reports/cis_2026-09-17/cis_effect.json`). La co-espressione con il bersaglio nei
  controlli non predice l'effetto del knockdown: correlazione mediana 0,0015 dopo aver
  tolto 20 PC, su 243 bersagli HepG2 (`reports/coexpression_2026-09-17/summary.json`).
- **Come è fatta:** in `assemble_log_fc`, un vicino entro 5 kb che la sorgente ha
  misurato prende `a_cis_measured` volte il proprio effetto K562; gli altri vicini prendono
  `a_cis` volte la mediana per distanza, adattata sui bersagli K562 fuori pannello.
- **Riaprire se:** i banchi mostrano che il termine peggiora PDS o REACH; oppure una
  misura su bersagli non essenziali contraddice il trasferimento.

### D-037 — Il DE dei banchi è quello veloce, finché resta identico

- **Perché:** il percorso CPU dello scorer ricalcola i ranghi dei controlli per ogni
  bersaglio: su 272 bersagli sono ore per braccio. `fast_scorer_de` confronta ogni gruppo
  con i controlli ordinati una volta sola, con chiavi complesse che conservano l'ordine
  esatto. Su dati HepG2 reali restituisce le stesse 76.648 righe, differenze 0,0 su
  p-value e log2FC e le stesse 7.916 chiamate, in 12 s invece di 88
  (`reports/fast_de_2026-09-17/parity.json`).
- **Come è fatta:** i banchi passano a `compute_metrics` entrambe le tabelle DE; tutto il
  resto lo calcola lo scorer. Il backend del server non è noto (D-014).
- **Riaprire se:** cambia la versione di `cell_eval2` o di scanpy; il controllo da rifare
  è lo script 79.

### D-038 — Ancore ufficiali come metro, e nessuna sottomissione al buio

- **Perché:** `vcc status --json` pubblica il valore **grezzo** di ogni membro accanto al
  suo scalato. Due sottomissioni sullo stesso pannello e la stessa `anchor_version` danno
  due equazioni in base e replica, e il sistema si risolve esattamente (stadio 82,
  `reports/anchors_2026-09-17/anchors.json`). Finché non le avevamo, i banchi locali
  confrontavano i bracci con ancore **proprie**, calcolate in un regime diverso da quello
  ufficiale: è così che `h002` ha dato +0,63 di fedeltà scalata su un file che il server
  ha valutato −0,87.
- **Come è fatta:** ogni misura locale riporta la forma grezza dei sei membri; il confronto
  con base e replica si fa contro `anchors.json`, mai contro le ancore di un banco. Le
  ancore valgono per `vcc2026-val-1` e per questa `anchor_version`, non oltre.
- **La seconda metà:** `direction_fidelity_yield_raw = k / max(n_pred, n_conf)` misura due
  cose diverse a seconda del regime — la precisione delle nostre chiamate quando
  `n_pred ≥ n_conf`, la copertura quando `n_pred < n_conf` — e le due letture chiedono
  interventi opposti. `n_pred` si misura con le sole cellule di controllo (stadio 83);
  `k` e `n_conf` no. Non si sottomette un file costruito per curare un regime prima di
  aver misurato di trovarsi in quel regime.
- **Riaprire se:** cambia `panel_id` o `anchor_version` (le ancore vanno ririsolte); oppure
  una terza sottomissione non riproduce lo scalato che le ancore predicono dal suo grezzo,
  il che falsificherebbe la soluzione.

### D-039 — CD4 entra come sorgente per bersaglio, dal pseudobulk letto per righe

- **Perché:** il pseudobulk CD4 copre 297 bersagli su 300, con una mediana di 1.478 cellule
  per bersaglio; K562 genome-wide ne copre 272, con circa 150 cellule. CD4 porta anche un
  lignaggio T vicino ad A. La ragione di D-031 per rinviarlo, cioè gli 1,7 TB delle cellule
  singole, non vale per il pseudobulk: i suoi blocchi non sono compressi e le righe del
  pannello costano 1,33 GiB.
- **Come è fatta:**
  - lo stadio 97 legge le righe per intervalli esatti di byte e verifica ogni riga contro il
    suo `total_counts`;
  - lo stadio 98 stima gli effetti per donatore contro i controlli dello stesso donatore e
    li media;
  - ogni sorgente riceve lo stesso shrinkage locale (`z_shrink`, k = 4);
  - la matrice sta sotto la radice dati;
  - per il pannello finale del 22 ottobre si rilancia lo stadio 97 sulla nuova lista di
    bersagli.
- **Evidenza:** [CP-0028](checkpoints/0028-cd4-sorgente-flex-trasferimento.md),
  `reports/cd4_rows_2026-09-22/manifest.json`, `reports/multisource_2026-09-22/r3/`.
- **Che cosa non segue:**
  - che CD4 migliori il punteggio: nello spazio degli effetti mediare K562 e CD4 non alza la
    discriminazione, e gene per gene i segni concordano al 55%;
  - che il lignaggio T aiuti A: non è misurato.

  Il primo test è il t08, a un solo fattore contro trial-01.
- **Riaprire se:**
  - il t08 va sotto trial-01;
  - una sorgente più vicina ai contesti (Orion) domina CD4 sulle stesse proxy;
  - gli autori cambiano o ritirano il file pubblico.
