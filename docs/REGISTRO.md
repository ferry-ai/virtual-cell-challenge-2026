# Registro del ciclo di vita di documenti e dati

A che serve: dire, per ogni materiale del progetto, **se ci si può ancora contare**.
Un documento non diventa falso tutto insieme: di solito resta valido in gran parte e
sbaglia in due punti. Qui si segna lo stato del documento e, quando serve, si apre una
scheda che elenca le singole affermazioni in discussione.

Aggiornato il 2026-09-16 (ultime righe: CP-0019 e la catena di cicli con guardiano, collaudo e
controllo di Grok; prima CP-0018, i grezzi pesanti già su Google Drive, e la
scheda R-013 sull'unità di misura del file K562 a singola cellula; prima ancora i due workflow del
16 settembre e la fotografia della classifica; prima ancora gate di espressione, non
promosso, e audit di presenza dei contesti ufficiali). Compilazione
iniziale il 2026-09-12, vedi
[CP-0001](checkpoints/0001-ricostruzione-stato-2026-09-12.md).

## Stati

| Stato | Significato | Cosa deve fare chi legge |
|---|---|---|
| `attuale` | È la guida valida adesso | Seguilo |
| `da-verificare` | Contiene almeno un'affermazione in dubbio, ma il resto regge | Usalo leggendo prima la sua scheda |
| `superato` | Le sue conclusioni sono state sostituite da un materiale successivo, indicato per nome | Non usarlo come guida; leggilo per capire la storia |
| `storico` | Non è una guida: è una registrazione datata, o evidenza grezza | Usalo come prova di ciò che si vedeva allora, non come indicazione |

Tre regole che rendono il registro affidabile:

1. **`da-verificare` non diventa `superato` in silenzio.** Serve un materiale nuovo,
   citato per nome nella colonna "Sostituito da", e una riga nel checkpoint che lo
   stabilisce.
2. **Un documento più recente non è automaticamente più corretto.** Quando due
   documenti sono in disaccordo e nessuno dei due ha misure decisive, si registra la
   contraddizione come aperta (vedi [R-004](#r-004--docsrevisione_analisi_2026-09-11md)).
3. **Niente cancellazioni, e niente sovrascritture dell'evidenza.** Il registro cambia
   stato e aggiunge avvisi; non elimina documenti, report o dataset. Una nuova
   esecuzione di una sonda va in una destinazione distinta (`--out`), non sopra il
   risultato precedente: anche un tentativo fallito documenta che cosa si vedeva a
   quella data. Vedi [Revisione periodica](#revisione-periodica-e-pulizia).

### Che cosa copre una voce

Il controllo automatico usa questa convenzione, quindi conviene rispettarla:

| Forma della voce | Copre |
|---|---|
| `docs/PROGETTO.md` | esattamente quel file |
| `reports/data_audit/` (con `/` finale) | quella cartella e tutto ciò che contiene, sottocartelle comprese |
| `reports/candidate_verification/*.json` | i file che corrispondono al modello, senza scendere nelle sottocartelle |

Ogni file sotto `docs/` e `reports/` deve essere coperto da almeno una voce, a qualunque
profondità. Registrare una cartella intera copre anche i file che ci finiranno domani:
farlo solo quando il contenuto è omogeneo, per esempio una serie di sonde con lo stesso
manifest. Materiale di natura diversa merita una voce propria.

## Documenti, report e artefatti di codice

| Percorso | Stato | Sostituito da | Cosa resta utile / nota | Scheda |
|---|---|---|---|---|
| `reports/multisource_2026-09-22/` | attuale | — | Script 98. `PRIMA_DEI_RISULTATI.md` fissa la regola della ricetta t08 **prima** che esista un numero su CD4, con due emendamenti datati. `transfer.json`/`coverage.json` alla radice sono il **primo run, difettoso** (effetti CD4 ridotti a zero da un pavimento sbagliato dell'errore standard; proxy di discriminazione bloccata a 0,5): restano come evidenza, non si usano. `r2/` è il run corretto; `r3/` lo riproduce e aggiunge la miscela CD4 grezza nella cache. **Misura (r3):** fra K562 e CD4 sui bersagli del pannello, discriminazione ~0,67–0,69, correlazione per gene ~0,02, accordo di segno 55,5% sui geni \|z\| > 3 di K562; mediare le sorgenti non alza la discriminazione. Proxy nello spazio degli effetti, non punteggi VCC | — |
| `reports/orion_2026-09-23/` | attuale | — | Script 102 (Orion HCT116/HEK293T, pseudobulk per lotto GEM, licenza CC-BY-NC-SA-4.0). `PRIMA_DEI_RISULTATI.md` fissa la regola del t11 (t08 + Orion, pesi uguali, criterio d'arresto) **prima** di qualunque numero su Orion | — |
| `reports/trial_2026-09-23/` | attuale | — | Il t10 (il t08 senza CD4): testi della sottomissione scritti prima dell'invio, manifesti, output verbatim di `vcc` (entry `JvksJS5r08YNOP6jfP4Q`, +0,0502, rango 570) | — |
| `reports/trial_2026-09-22/` | attuale | — | Il t08: testi della sottomissione scritti prima dell'invio, manifesti di generazione e di impacchettamento, autorizzazioni del proprietario, output verbatim di `vcc submit` e `vcc status` (entry `NNUXtdhV4ByiETbolCKJ`, +0,0604, rango 547) | — |
| `reports/dispersion_2026-09-23/` | attuale | — | Generatore di trial-01 con dispersione per gene (`sampling.fit_gene_dispersion`, stadio 45 `--gene-dispersion`). `PRIMA_DEI_RISULTATI.md` fissa la regola del t13 (controllo nullo con criterio d'arresto, scelta dell'ampiezza per chiamate) **prima** dei piloti. `RISULTATO_NULLO.md`: a effetto nullo 5 / 15 / 31 chiamate mediane in A / B / C, sopra la soglia di 10 in B e C, quindi il t13 **non si costruisce** | — |
| `reports/prediction_calls_2026-09-23/` | attuale | — | Stadio 83 sul file del t11 (generatore di trial-01), 20 bersagli per contesto, 9.200 controlli di riferimento. **Misura:** n_pred mediano 543 / 582 / 764 in A / B / C, l'83–85% «in su». Con n_conf mediano stimato a 30–50 (docstring dello scorer), la fedeltà di questa famiglia è la precisione delle chiamate spurie del generatore | — |
| `reports/prediction_t11_2026-09-23/` | attuale | — | Previsione del t11 (t08 + Orion HCT116 a pesi uguali) registrata **prima** della generazione: banda +0,055…+0,075 e regola di lettura fissata prima | — |
| `reports/prediction_t10_2026-09-23/` | attuale | — | Previsione del t10 (il t08 senza CD4) registrata **prima** della generazione: banda +0,040…+0,060 e regola di lettura fissata prima (≤ 0,050: CD4 porta almeno due terzi del guadagno del t08; ≥ 0,056: il guadagno viene soprattutto da stimatore e centratura). `comparison.json`: esito +0,0502, dentro la banda; per la regola, non attribuibile (0,0002 sopra la soglia); descrittivamente CD4 porta +0,0102 dei +0,0144 | — |
| `reports/prediction_t08_2026-09-22/` | attuale | — | Previsione del t08 registrata **prima** dell'invio: banda del punteggio medio +0,03…+0,06 e direzione attesa di ogni membro rispetto a trial-01. Non viene dallo stadio 84, che non vale per una famiglia nuova (CP-0027), ma dalle misure di CP-0028. `comparison.json`: esito +0,0604, sul bordo superiore; tutti i grezzi nella direzione prevista | — |
| `reports/cd4_rows_2026-09-22/` | attuale | — | Script 97: righe pseudobulk CD4 (GSE314342) dei bersagli del pannello più 200 righe NTC per donatore × condizione, lette per intervalli di byte dal file pubblico su S3 (1,33 GiB). 297/300 bersagli, mediana 1.478 cellule per bersaglio; ogni riga verificata contro il proprio `total_counts`. La matrice sta sotto la radice dati (`external/cd4/`), non nel repository | — |
| `reports/context_fingerprints_2026-09-22/` | attuale | — | Script 99. **Misura:** l'asse ufficiale è quello di un pannello di sonde (18.533 geni contro i 18.532 di Flex v1.0.1; 0 RPL/RPS, 0 HLA, niente XIST/MALAT1/NEAT1), coerente con il 10x Flex dichiarato da Arc. I profili NTC di A/B/C correlano fra loro più che con K562/RPE1 in 3'. Impronte genetiche: sesso, zeri omozigoti, spostamenti per braccio cromosomico. **Le identità di linea sono ipotesi**, non misure | — |
| `reports/direzione_2026-09-19/` | attuale | — | Audit retrospettivo di main e refactor/pulizia, lettura delle sei note fornite dal proprietario e verifica di alcune righe AtlasShift della classifica. Proposta di trasferimento specifico del bersaglio con centratura e calibrazione delle quantità realizzate; nessun nuovo candidato o ciclo avviato. Suite rieseguite: errore comune di import cell_eval2.config; dettagli e limiti in VALUTAZIONE.md e VERIFICHE.md | — |
| `docs/checkpoints/0020-singola-cellula-cis-generatore.md` | attuale | — | Cambio di strategia verso le cellule singole su Colab. Misure: effetto cis trasferibile K562 → HepG2, co-espressione non predittiva, DE veloce identico allo scorer, generatore di trial-01 con 93 chiamate spurie per bersaglio a effetto zero. Corregge CP-0018 §3.1 e §4 (md5). **Nessun banco remoto e nessun invio eseguiti** | — |
| `reports/cis_2026-09-17/` | attuale | — | Script 77: curva effetto-distanza sul pseudobulk K562, coppie K562–HepG2 entro 5 kb, esposizione del pannello per contesto. Misura su bersagli HepG2 essenziali, non un punteggio | — |
| `reports/coexpression_2026-09-17/` | attuale | — | Script 78: la co-espressione nei controlli HepG2 non predice l'effetto del knockdown (correlazione parziale mediana 0,0015 su 243 bersagli). Un contesto, bersagli essenziali | — |
| `reports/fast_de_2026-09-17/` | attuale | — | Script 79: `fast_scorer_de` contro il percorso scanpy di `cell_eval2` su cellule HepG2: righe, p-value, log2FC e chiamate identici | — |
| `reports/generator_null_smoke_2026-09-17/` | storico | `reports/generator_null_2026-09-17/` | Script 72 in versione ridotta (contesto A, 3.000 controlli, 4 pseudo-bersagli da 100 cellule): chiamate spurie a effetto zero per cellule reali, generatore di trial-01 e `ControlModel`. Prova ridotta, non la calibrazione a scala piena | — |
| `reports/generator_null_2026-09-17/` | attuale | — | Calibrazione a effetto zero su A, B e C (run `n003`, 9.200 controlli per addestrare e 9.200 come riferimento, 20 pseudo-bersagli da 400 cellule): il generatore di trial-01 dichiara 462 / 453 / 684 geni significativi per bersaglio (82% «in su»), le cellule reali 0,1 / 0,0 / 0,1 e `ControlModel` 0,5 / 0,5 / 1,2. Sostituisce la prova ridotta di `reports/generator_null_smoke_2026-09-17/` | — |
| `reports/bench_2026-09-17/` | attuale | — | I due banchi a sei metriche del 17 settembre, girati su Colab: K562 del pannello (`b002`, 224 bersagli, mediana `N_conf` 3, oracolo dallo stesso bersaglio) e trasferimento K562 → HepG2 (`h002`, 300 bersagli, mediana `N_conf` 130). Scala **locale** (0 = baseline, 1 = replica del banco): confronta bracci, non è un punteggio VCC | — |
| `reports/trial02_decision_2026-09-17/` | attuale | — | Applicazione meccanica di `configs/trial02_rule.yaml` (script 81): scelto trasferimento ×2 + cis, riportato a ×1 dal tetto K562 → t02. `deviation_t03.json` documenta t03 (×2 + cis, senza tetto), deviazione a posteriori motivata dall'artefatto del Jaccard in K562 | — |
| `reports/k562_sc_2026-09-17/` | storico | — | Report e log dello stadio 71 (run `x002`, Colab, 17 settembre): prima lettura completa del K562 genome-wide a singola cellula, 1.989.578 cellule x 8.248 geni in 43 minuti (24,6 MiB/s dal mount Drive), md5 ricalcolato sui byte letti uguale al catalogo, 272 bersagli del pannello (28 assenti, elencati), 75.328 cellule NTC. Le uscite pesanti (parti, `group_stats.npz`) restano in `MyDrive/vcc2026/data/processed/k562_gwps_sc/x002/`. Il run `x001` e fallito all'avvio: la sua cartella contiene un `report.json` segnaposto che NON e un report | — |
| `reports/call_budget_2026-09-17/` | attuale | — | Script 80 sul contesto A reale (20 bersagli del pannello, 400 cellule, 1.500 controlli di riferimento, sorgente K562 pseudobulk): chiamate significative per bersaglio al variare delle ampiezze. Mediana 1 con il solo cis, 9 con trasferimento EB x1, 216 con EB x2, 27 con raw x0,25. Conta le chiamate, non ne misura il segno | — |
| `reports/drive_evidence_2026-09-17/` | storico | — | Copie dei sidecar `.fetch.json` e del `catalog_run.json` del run Colab del 15 settembre, più l'elenco dei file in `MyDrive/vcc2026` al 17 settembre: provano md5 e percorso delle copie su Drive | — |
| `src/vcc2026/sc_stream.py`, `src/vcc2026/generator.py`, `src/vcc2026/de_tools.py`, `src/vcc2026/sc_effects.py`, `src/vcc2026/predictor_sc.py`, `src/vcc2026/bench.py` | attuale | — | Pipeline a singola cellula: lettura a flusso con md5 e accumulatore numba; generatore appreso dai controlli; DE dello scorer in forma ufficiale e veloce; effetti con shrinkage EB; termine cis e composizione del log fold change; banco a sei metriche con ancore locali | — |
| `scripts/71_extract_k562_sc.py`, `scripts/72_generator_null.py`, `scripts/73_bench_k562_panel.py`, `scripts/74_fetch_gene_coordinates.py`, `scripts/75_bench_hepg2_transfer.py`, `scripts/76_generate_sc_prediction.py`, `scripts/77_cis_effect_report.py`, `scripts/78_coexpression_predictor_test.py`, `scripts/79_fast_de_parity.py`, `scripts/80_call_budget.py` | attuale | — | 71 e 73–76 provati solo su dati ridotti o finti in locale; 71, 72, 73 e 75 in coda su Colab e **non ancora eseguiti** a scala piena. 74 eseguito: coordinate GENCODE v50 per 18.447 dei 18.533 geni ufficiali. 77, 78, 79 e 80 eseguiti, con report | — |
| `notebooks/colab_sc_training.ipynb`, `notebooks/colab_jobs/` | attuale | — | Notebook Colab con dispatcher: esegue i job depositati in `MyDrive/vcc2026/runs/queue/` e scrive i log in `runs/jobs/`; `sync_to_drive.ps1` copia il codice su Drive. Mai eseguito su Colab al 17 settembre, 16:40 | — |
| `tests/test_sc_pipeline.py` | attuale | — | 8 test: flusso e accumulatore contro letture dirette, md5, rifiuto di X a blocchi, Mann-Whitney esatto con pareggi, BH, generatore senza copie e con conteggi interi, prior cis limitato alla distanza, shrinkage EB | — |
| `docs/checkpoints/0019-catena-cicli-guardiano.md` | attuale | — | Cambio di strategia: la catena diventa a cicli ripetibili, con guardiano, test di collaudo scritti da Codex prima di Claude e controllo di Grok con al massimo tre campagne dell'orchestratore. Implementato e provato con agenti simulati; **nessun ciclo eseguito dal vivo** | — |
| `reports/catena_2026-09-16/` | storico | — | Le uniche prove sui servizi veri per la catena: trascrizione della chiamata di prova a Grok Build (formato della risposta, costo nominale), validazione con `orch brief` di un incarico nel formato generato, esiti delle verifiche del 16 settembre | — |
| `docs/checkpoints/0018-drive-storage-confermato.md` | da-verificare | — | Dichiarazione del proprietario: `K562_gwps_raw_singlecell_01.h5ad` e `NadigOConner2024_hepg2.h5ad` sono già su Google Drive. Dimensioni coerenti con il catalogo in unità binarie. **Corretto da CP-0020:** le copie le ha scaricate il run Colab del 15 settembre nei percorsi attesi, con md5 verificato al download. Resta vero che nessun run ne ha letto il contenuto. Non adotta nessun dataset | [R-014](#r-014--cp-0018-md5-e-provenienza-delle-copie-su-drive) |
| `docs/CICLO_GIORNALIERO.md` | attuale | — | Contratto della catena di cicli: piano, revisione, implementazione, controllo; guardiano, casella, collaudo, campagne, permessi, comandi e limiti. Riscritto il 16 settembre (la versione a un giro al giorno è nel commit `4272b3b`). Provato con agenti simulati; nessuna esecuzione dal vivo | — |
| `reports/ciclo_giornaliero/` | storico | — | Registrazioni della catena, una cartella per giornata con `ciclo-NN/`: segnali JSON delle quattro fasi, revisione o dialogo, foglio, test di collaudo, esito di Claude, analisi e sintesi di Grok, campagne, resoconto. Documentano che cosa gli agenti hanno consegnato; non sono risultati scientifici. La cartella `2026-09-16` ha la forma piatta precedente, e il suo sigillo non corrisponde più ai piani modificati dopo ([CP-0018](checkpoints/0018-drive-storage-confermato.md)) | — |
| `scripts/32_daily_cycle.py`, `scripts/ciclo.cmd`, `configs/ciclo_giornaliero/`, `tests/test_daily_cycle.py` | attuale | — | La catena (solo libreria standard): guardiano, coda, cicli dal dialogo, collaudo prima e dopo, fase di Grok e campagne con tetto; wrapper per l'Utilità di pianificazione, impostazioni, schemi e testi fissi. 42 test con agenti simulati (Codex, Claude, Grok, orchestratore) in un repository git temporaneo | — |
| `.agents/skills/avvia-ciclo/`, `.agents/skills/revisione-piano/`, `.claude/skills/piano-mattutino/`, `AGENTS.md` | attuale | — | Istruzioni degli agenti della catena: dialogo e avvio dei cicli in Codex, revisione del ciclo 01 con i test di collaudo, piano del mattino che legge i resoconti dei cicli, regole comuni per Codex e Grok | — |
| `docs/PIANO_IMPLEMENTATIVO_2026-09-16.md` | attuale | — | Workflow 1 del 16 settembre: dieci incarichi paralleli con scadenze, regole di accettazione scritte prima dei risultati, cinque decisioni del proprietario (O1–O5), obiettivi di spinta dichiarati come non previsioni. Proposta: non attesta l'avvio di alcun incarico. Aggiornato alle 16:49 con CP-0018: in I-5 e I-6 il K562 a singola cellula si collega da Drive e non si scarica | — |
| `docs/PIANO_COMPRENSIONE_2026-09-16.md` | attuale | — | Workflow 2 del 16 settembre, per i ricercatori: stato per area da verificare, criticità C1–C12, studio biologico e informatico, domande di comprensione e disallineamenti noti. Proposta: non attesta l'avvio di alcun incarico. Aggiornato alle 16:49 con CP-0018: C8 declassata per l'ingestione, unità del file K562 corretta | — |
| `reports/leaderboard_2026-09-16/` | storico | — | Fotografia trascritta a mano della classifica pubblica alle 11:31Z: prime dieci righe e la nostra (rango 493), senza nomi di squadra. Contiene una **stima** delle ancore b/r per metrica da un adattamento lineare: interpretazione, non misura ufficiale | — |
| `docs/checkpoints/0017-gate-espressione-destinazione.md` | attuale | — | Gate di espressione G1/G2/G3 con controlli permutato e sorgente: implementato, eseguito e misurato. **Non promosso** dalla regola fissata prima del run. Non adotta niente | — |
| `configs/benchmark_expression_gate.yaml` | attuale | — | Protocollo del run `x001` e regola di decisione, scritti prima di qualunque risultato. `owner_confirmed: false`: la regola proposta nel brief non è stata confermata dal proprietario prima del run | — |
| `src/vcc2026/presence.py` | attuale | — | Presenza per gene dai controlli già letti (`inference.read_basal_profile`, `ControlProfile`) e peso logistico graduale; nessun secondo lettore di controlli. Un gene non misurato ha peso 1 (D-009) | — |
| `src/vcc2026/benchmark/gate.py` | attuale | — | I bracci gate: G1/G2/G3, i controlli C1 (permutato) e C2 (sorgente), la selezione sulla coppia interna al training e la valutazione meccanica della regola di decisione. Spento se la configurazione non lo dichiara | — |
| `tests/test_expression_gate.py` | attuale | — | 53 test: presenza non misurata contro misurata a zero, peso graduale e non a scalino, permutazione che conserva i valori, selezione che non legge il contesto di test, base che deve coincidere con `shrunk_transfer`, regola che non promuove su un confronto mancante | — |
| `scripts/69_expression_gate_decision.py`, `scripts/70_context_presence_audit.py` | attuale | — | 69 applica la regola già scritta e non sceglie nulla; 70 conta quanti geni e quanti bersagli sono poco espressi nei controlli ufficiali A/B/C. Eseguiti il 2026-09-16 | — |
| `reports/expression_gate_2026-09-16/` | attuale | — | Run `x001`: tabella comparativa, universo, riepilogo con i confronti appaiati, split con la distribuzione dei CPM, decisione applicata, righe dei gate, e l'audit di presenza dei contesti ufficiali. I pesi e `results.json` restano in `artifact_root` | — |
| `docs/RL/README.md` | attuale | — | Appunti RL rinviati su richiesta dell'utente: allocazione del calcolo, calibrazione e affinamento generativo; ipotesi e criteri di ripresa, nessuna adozione o esecuzione | — |
| `docs/checkpoints/0016-piano-operativo-audit-protocollo.md` | attuale | — | Audit Jiang/Jurkat, protocollo congelato, disco sotto soglia per TGFB, campagna orch avviata. Non adotta Jiang né Jurkat | — |
| `configs/eval_protocol.yaml` | attuale | — | Protocollo di valutazione congelato (D-032). Seed 4242 riservato. Non è un risultato | — |
| `src/vcc2026/eval_protocol.py`, `src/vcc2026/runtime.py`, `src/vcc2026/remote_job.py`, `src/vcc2026/source_card.py` | attuale | — | Protocollo, inventario runtime, fetch riprendibile, scheda sorgente | — |
| `scripts/61_probe_jiang.py`, `scripts/62_reconcile_nadig.py`, `scripts/63_runtime_preflight.py`, `scripts/64_source_cards.py`, `scripts/65_eval_protocol_pilot.py`, `scripts/66_primeflow_feasibility.py`, `scripts/67_remote_ingest.py`, `scripts/68_remote_catalog.py` | attuale | — | 67 = contratto HepG2; 68 = piano/catalogo multi-sorgente. 68 eseguito in locale **plan-only** (nessun file da 61,3 GiB sul portatile; la versione precedente di questa nota diceva «65,8 GiB», un errore di unità: [R-013](#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb)) | — |
| `tests/test_eval_protocol.py`, `tests/test_remote_job.py`, `tests/test_remote_ingest.py`, `tests/test_remote_catalog.py` | attuale | — | Leakage, fetch, gate Jiang, catalogo byte/md5, persistenza Colab, checkpoint immutabile | — |
| `src/vcc2026/remote_ingest.py` | attuale | — | Job HepG2: parità, resume, gate TGFB | — |
| `src/vcc2026/remote_catalog.py`, `configs/remote_catalog.yaml` | da-verificare | — | Catalogo blocchi con byte/md5 da evidenza: byte, md5, URL e `relpath` sono giusti, e il codice lavora in byte. **Non** è vero che il «61,3 GB» del profilo differisca dai 65.830.941.948 byte misurati: sono 61,31 GiB, la stessa dimensione. Errati `advertised_bytes`, `advertised_note` e l'etichetta «65,8 GiB» nelle docstring | [R-013](#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb) |
| `notebooks/remote_ingest_hepg2.ipynb` | da-verificare | — | Un solo notebook: preflight, selezione, fetch, QC, deriva. `FETCH_BLOCKS is None` auto-sceglie dopo il preflight (HepG2 se manca, poi K562 GW se Drive è montato). Vuoto `[]` resta plan-only. HepG2 si salta se size/md5 ok. Il run Colab `catalog_2026-09-15T143641Z` era plan-only per `FETCH_BLOCKS=[]`, non un fallimento del fetcher. **Dal 16 settembre** i due file sono già su Drive (CP-0018): per soltanto collegarli serve `FETCH_BLOCKS = []`, perché con `None` la selezione passa al blocco successivo e lo scarica | [R-013](#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb) |
| `reports/remote_catalog_2026-09-15/` | attuale | — | Piano locale. HepG2 complete (file già sul disco). Nessun download nuovo. Non è una prova Colab. Ripete `advertised_bytes` del catalogo, contestato in R-013 | — |
| `reports/remote_2026-09-15/` | da-verificare | — | Parità HepG2 ok, resume ok, Jiang skip per disco: misure valide. Le istruzioni in `COME_APRIRE.md` usano «65,8 GiB» (sono 61,31 GiB) e consigliano `FETCH_BLOCKS = None`, che con i file già su Drive porta a un download non voluto | [R-013](#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb) |
| `reports/jiang_2026-09-15/` | attuale | — | Record Zenodo, HEAD, file piccoli, scheda, proposta TGFB. Copertura pannello missing | — |
| `reports/nadig_reconcile_2026-09-15/` | attuale | — | HepG2 GEO=mirror per forma e NTC; Jurkat mirror 1,29 GB, 0/300 | — |
| `reports/runtime_2026-09-15/` | attuale | — | 7,81 GiB RAM, 11,3 GiB liberi; TGFB non sta sotto il pavimento da 10 GiB | — |
| `reports/source_cards_2026-09-15/` | attuale | — | Schede Replogle SC, H1, CD4, Srivatsan, McFaline, Tahoe, scBaseCount. Nella scheda Replogle SC, `profile_declared_sc` converte in byte decimali cifre del profilo che sono GiB; decisioni e altri campi non ne dipendono | [R-013](#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb) |
| `reports/eval_protocol_2026-09-15/` | attuale | — | 12 split, 0 fail, tutti sviluppo. Ancore HepG2: solo smoke su finestra, non un risultato | — |
| `reports/primeflow_2026-09-15/` | attuale | — | Fattibilità da preprint; codice/pesi missing; defer | — |
| `configs/orchestrator/briefs/vcc2026-jurkat-audit.yaml`, `configs/orchestrator/briefs/vcc2026-pharma-atlas-audit.yaml` | attuale | — | Incarichi preparati, non avviati: l'orchestratore serializza il browser | — |
| `docs/REGIA_PARALLELA_2026-09-15.md` | attuale | — | Mandato esplicito dell'utente: concentrare oggi tutti i filoni, solo training oltre oggi; otto incarichi, proprietà file, dipendenze e formato delle consegne. Avvio agenti a cura dell'utente | — |
| `docs/PIANO_OPERATIVO_2026-09-15.md` | attuale | — | Piano approvato: audit, elenco ufficiale, protocollo e incarichi. Jiang/Jurkat prioritari. La riga «nessun run dei worker» è superata da CP-0016 (campagna Jiang avviata). Nessun nuovo training | — |
| `configs/orchestrator/briefs/vcc2026-jiang-audit.yaml` | attuale | — | Audit Jiang; pannello allegato. Campagna live `20260915T115742Z-vcc2026-jiang-audit-v1-a81104`: DeepSeek 3 fasi, Kimi timeout ×2, fermata `service_unavailable`. Puntatore in `reports/orchestrator/jiang-audit-20260915.md` | — |
| `configs/orchestrator/briefs/vcc2026-validation-review.yaml`, `configs/orchestrator/briefs/vcc2026-primeflow-audit.yaml` | attuale | — | Incarichi delimitati preparati per review metodologica e ricerca primaria; non avviati | — |
| `docs/SVD_E_RANGO.md` | attuale | — | SVD randomizzata configurabile e confronto di rango 16/32/64/128. Implementato / eseguito / misurato / ipotizzato tenuti distinti. Non adotta la randomizzata né un rango >16 | — |
| `reports/ricerca_dataset_20260915.md` | attuale | — | Dossier di una campagna `scientific_research` dell'orchestratore (run `20260914T222203Z-campagna-dati-v1-037cbd`). Non è una misura di questo repository: i livelli di consultazione restano dichiarati (D-023). Non usato da CP-0015 | — |
| `docs/checkpoints/0015-svd-randomizzata-e-rango.md` | attuale | — | Misura della sostituzione esatta/randomizzata e del rango; regola di banda prefissata non soddisfatta | — |
| `reports/svd_2026-09-15/` | attuale | — | Fattorizzazione isolata, confronto predittivo s001/s002, tabelle e split. I `results.json` restano in `artifact_root` | — |
| `reports/rank_2026-09-15/` | attuale | — | Tabella, riepilogo, split e `rank_summary.json` del run r001 | — |
| `configs/benchmark_svd_exact.yaml`, `configs/benchmark_svd_randomized.yaml`, `configs/benchmark_rank.yaml` | attuale | — | Protocolli eseguiti: sostituzione SVD e confronto di rango. Non sono una proposta di default | — |
| `scripts/60_compare_factorization.py` | attuale | — | Confronto esatta/randomizzata su una matrice reale e, se dati due run, sulle predizioni | — |
| `tests/test_factorization.py` | attuale | — | Riproducibilità, forme, centratura, bootstrap pooled, aggregazioni di segno opposto | — |
| `src/vcc2026/benchmark/factorization.py` | attuale | — | Unico punto di SVD troncata del benchmark; `exact` predefinito | — |
| `docs/ENCODER_INPUTS.md` | attuale | — | Specifica degli input di contesto e bersaglio per il modo B (gene mai perturbato). Descrittori verificati su file. **La sua unica estensione, il GO slim, è stata eseguita e scartata il 2026-09-15** ([CP-0014](checkpoints/0014-go-slim-e-gpu.md)): il resto della pagina resta valido come specifica e inventario | — |
| `reports/encoder_inputs_2026-09-14/` | attuale | — | Probe isolato: HEAD, download, mapping HGNC, copertura GO/STRING. Cache pesante in `C:/Users/ferra/vcc2026-data/interim/encoder_inputs_2026-09-14/` | — |
| `scripts/56_probe_target_descriptors.py` | attuale | — | Probe dei descrittori di modo B. Eseguito il 2026-09-14; non modifica il benchmark. Numerato 56 perché 52–55 sono l'ingestione HepG2 in corso | — |
| `reports/hepg2_2026-09-14/` | attuale | — | Acquisizione (URL, byte, md5 verificato), audit del contenuto, tabella contesto×bersaglio e confronto generatore×predittore di HepG2 Nadig. Non modificati da CP-0012 | — |
| `docs/BENCHMARK_TRE_CONTESTI.md` | attuale | — | Benchmark a tre contesti (K562, RPE1, HepG2): implementato / eseguito / misurato / ipotizzato tenuti distinti. Non adotta un'architettura e non dichiara un vincitore | — |
| `reports/benchmark_3ctx_2026-09-14/` | attuale | — | Tabella comparativa, universi genici, riepilogo e manifesti del run m002 a tre contesti. Pesi e `results.json` restano in `artifact_root` | — |
| `configs/benchmark_3ctx.yaml` | attuale | — | Protocollo del benchmark a tre contesti: tre fold esterni, alpha vietato, universo per intersezione, regola di combinazione delle sorgenti fissata prima dei run | — |
| `configs/benchmark_3ctx_hepg2_predictions.yaml` | attuale | — | Derivato dal precedente: stesso protocollo, solo il fold con HepG2 fuori e le predizioni salvate, per l'esperimento generatore×predittore | — |
| `scripts/52_audit_hepg2.py`, `scripts/53_build_hepg2_signatures.py`, `scripts/54_context_target_table.py`, `scripts/55_control_profile.py` | attuale | — | Acquisizione e ingestione HepG2: audit, firme con controlli appaiati per batch, censimento contesto×bersaglio, profilo basale. Eseguiti il 2026-09-14 | — |
| `scripts/57_generator_x_predictor.py` | attuale | — | Confronto generatore×predittore sulle sei metriche, cellule HepG2 reali. Numerato 57 perché 56 è la sonda dei descrittori | — |
| `reports/go_slim_2026-09-15/` | attuale | — | Pilot dei descrittori GO slim (run g002): tabella comparativa, split, riepilogo con i confronti appaiati, e il riassunto della tabella congelata. Esito: estensione **scartata** dalla regola fissata prima ([CP-0014](checkpoints/0014-go-slim-e-gpu.md)) | — |
| `reports/gpu_2026-09-15/` | attuale | — | Audit di prontezza GPU: che cosa esegue ogni passo numerico, quanto costa alle forme reali, e lo scaling della SVD. Misure su questa macchina a carico scarico | — |
| `docs/CONSEGNA_GPU.md` | attuale | — | Pacchetto trasferibile per la macchina con GPU del compagno: file da copiare, dipendenze, comandi, e che cosa la GPU accelera davvero (il solo backend DE dello scorer) | — |
| `configs/benchmark_go_slim.yaml`, `requirements-gpu.txt` | attuale | — | Protocollo del pilot GO slim, con la regola decisionale e il braccio permutato; dipendenze aggiuntive per una macchina CUDA, deliberatamente senza torch | — |
| `scripts/58_build_go_slim_table.py`, `scripts/59_gpu_readiness.py` | attuale | — | Tabella congelata simbolo→140 bit GO con gli sha256 delle quattro fonti; audit GPU misurato. Eseguiti il 2026-09-15 | — |
| `docs/PROSPETTO_MODELLO_2026-09-14.md` | attuale | — | Proposta: ricostruzione trial, blocchi modulari, evidenze e protocollo comparativo. Nessun vantaggio misurato né architettura adottata. Il confronto è stato eseguito in [CP-0011](checkpoints/0011-primo-benchmark-modulare.md), esito inconcludente | — |
| `docs/BENCHMARK_MODULARE.md` | attuale | — | Primo confronto modulare: implementato / eseguito / misurato / ipotizzato tenuti distinti. Non adotta un'architettura | — |
| `reports/benchmark_2026-09-14/` | attuale | — | Inventario, split riassunti, tabella comparativa, specifica del bundle mancante, manifesti del pilot m001. I pesi e `results.json` restano in `artifact_root` | — |
| `src/vcc2026/benchmark/` | attuale | — | Protocollo comune, universo genico, modelli A–E, runner. Coperti da `tests/test_modular_benchmark.py` | — |
| `scripts/50_inventory_data.py`, `scripts/51_run_modular_pilot.py` | attuale | — | Inventario e pilot. Eseguiti il 2026-09-14; i risultati leggeri sono in `reports/benchmark_2026-09-14/` | — |
| `tests/test_modular_benchmark.py` | attuale | — | Maschere, leakage, alpha 0,1974, salvataggio/caricamento, identità delle predizioni | — |
| `configs/benchmark.yaml` | attuale | — | Protocollo del pilot: metrica primaria, alpha vietato, universo, seed, budget. Non è un risultato | — |
| `docs/PROGETTO.md` | attuale | — | Punto di ingresso: mappa dello stato | — |
| `docs/DECISIONI.md` | attuale | — | Decisioni attive e quando riaprirle | — |
| `docs/REGISTRO.md` | attuale | — | Questo file | — |
| `docs/checkpoints/0001-ricostruzione-stato-2026-09-12.md` | da-verificare | — | Stato e correzioni al 12 settembre; ricostruzione retrospettiva dichiarata. Tre affermazioni corrette da CP-0002: resta leggibile com'era, come tutti i checkpoint | [R-009](#r-009--docscheckpoints0001-ricostruzione-stato-2026-09-12md) |
| `docs/checkpoints/0002-correzioni-dopo-revisione-umana.md` | attuale | — | Le sei correzioni chieste dalla prima revisione umana, e da dove veniva ciascuna | — |
| `docs/checkpoints/` | attuale | — | Modello, indice e checkpoint. I checkpoint non si riscrivono: le correzioni stanno in quello successivo e nella colonna "Corretto da" dell'indice | — |
| `docs/revisione_grok_2026-09-12.md` | attuale | — | Verifica live di un inventario esterno fornito da Grok: correzioni di accessione e cinque piste nuove. Dichiara i propri limiti. **Le sue conclusioni non sono ancora entrate in `docs/DECISIONI.md`**: farlo richiede un checkpoint | — |
| `docs/candidate_adversarial_review_2026-09-12.md` | attuale | — | Analisi più recente: coperture misurate, correzioni di accessione, piano di acquisizione. Non è stata rivista da un umano e il suo §2 è in disaccordo aperto con la revisione dell'11 settembre sull'asse genico | — |
| `README.md` | da-verificare | — | Compito, formato, setup, autenticazione e scorer restano corretti; la tabella del piano e due affermazioni scientifiche sono rimaste indietro | [R-001](#r-001--readmemd) |
| `reports/scorer/vcc2026_contract.json` | superato | `reports/scorer_2026-09-12/vcc2026_contract.json` | Il dump di `official_config` e i clamp per metrica sono verificati e invariati; solo il campo `floor_note` è sbagliato. Resta come evidenza storica di che cosa diceva l'estrattore prima della correzione | [R-002](#r-002--reportsscorervcc2026_contractjson) |
| `docs/data_strategy_2026-09-11.md` | superato | `docs/revisione_analisi_2026-09-11.md`, `docs/candidate_adversarial_review_2026-09-12.md` | Il §4 (contratto di preprocessing) e il §1 (misure locali) restano validi e sono usati | [R-003](#r-003--docsdata_strategy_2026-09-11md) |
| `docs/revisione_analisi_2026-09-11.md` | da-verificare | — | Identità dei contesti, povertà di segnale in K562, tabella dei clamp e disegno del pannello restano validi e riusati | [R-004](#r-004--docsrevisione_analisi_2026-09-11md) |
| `reports/candidate_verification/cd4_readme.txt` | superato | `reports/candidate_verification/expanded/cd4_readme.txt` | Nulla: è il corpo di una risposta 404 | [R-005](#r-005--i-due-stub-404-di-candidate_verification) |
| `reports/candidate_verification/cd4_repo_tree.txt` | superato | `reports/candidate_verification/expanded/cd4_repo_tree.txt` | Nulla: è il corpo di una risposta 404 | [R-005](#r-005--i-due-stub-404-di-candidate_verification) |
| `reports/candidate_pdf_extracted.txt` | storico | — | Fonte esterna di affermazioni da verificare, non evidenza nostra: diverse sue tesi sono state smentite | [R-006](#r-006--reportscandidate_pdf_extractedtxt) |
| `reports/transfer_ceiling/` | da-verificare | — | I numeri sono corretti e riusati; è il nome della cartella a suggerire una conclusione che non è stata dimostrata | [R-007](#r-007--reportstransfer_ceiling) |
| `configs/candidate_ingestion.json` | attuale | — | Manifesto di piano e configurazione. Non è la prova che un runner l'abbia consumato: nessun addestramento è partito | — |
| `reports/context_identity/` | attuale | — | Marcatori e test di contrasto; le cautele sono scritte dentro `context_identity.json` | — |
| `reports/data_audit/` | attuale | — | Audit dei controlli ufficiali e copertura HIPSCI: misure ancora valide anche se HIPSCI è stata spostata più in basso nelle priorità | — |
| `reports/candidate_verification/coverage_summary.json` | attuale | — | Coperture per sorgente; ricontato il 2026-09-12 | — |
| `reports/candidate_verification/panel_coverage.csv` | attuale | — | Tabella per bersaglio: il file su cui si sceglie cosa è supportato | — |
| `reports/external_compat/` | attuale | — | Struttura delle guide NTC e contratto di compatibilità esterna | — |
| `reports/candidate_verification/` | attuale | — | Sonde remote del 11–12 settembre con manifest, byte e sha256: `expanded/`, `annotations/`, `context_c_lead/`, `pilot/` e i file di primo livello. Fotografie datate di endpoint pubblici, non conclusioni | — |
| `reports/grok_verification/` | attuale | — | Sonde e campioni prodotti da `scripts/27_verify_grok_leads.py` e `scripts/28_probe_grok_files.py`, spiegati da `docs/revisione_grok_2026-09-12.md`. Contiene `multiome.zip`, che `.gitignore` esclude: è locale, non versionato | [R-008](#r-008--reportsgrok_verification) |
| `scripts/` (01–28, analisi) | attuale | — | Esistono e sono documentati come eseguiti; l'esistenza di uno script non è prova di esecuzione né di risultato | — |
| `scripts/30_new_checkpoint.py`, `scripts/31_check_docs.py`, `tests/test_doc_workflow.py` | attuale | — | Utilità di questo sistema: creano checkpoint numerati senza sovrascriverli e verificano la coerenza di registro, indice e riferimenti. Solo libreria standard | — |
| `notebooks/` | storico | — | Cartella vuota, citata nel layout del README: non contiene esplorazioni | — |
| `docs/checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md` | attuale | — | Prima pipeline verticale eseguita e prima calibrazione misurata dell'ampiezza di trasferimento; corregge due letture dei dati mai scritte prima | — |
| `docs/PIPELINE.md` | attuale | — | Architettura della pipeline, moduli, comandi e scelte di progetto. Descrive codice eseguito, non previsto | — |
| `docs/ROADMAP.md` | attuale | — | Passi ordinati per valore informativo diviso costo, con ipotesi, criterio di successo e artefatto atteso per ciascuno | — |
| `docs/ESECUZIONE_REMOTA.md` | attuale | — | Piano locale/remoto con tempi misurati e profili di risorse. **Non contiene prezzi**: il preventivo va costruito al momento della proposta | — |
| `configs/sources.yaml` | attuale | — | Registry versionato delle sorgenti con livelli di verifica ed evidenza. Fonte autorevole sullo stato di una sorgente (D-013); `src/vcc2026/registry.py` ne verifica la coerenza | — |
| `reports/pipeline/` | attuale | — | Risultati leggeri e manifesti dei tre stadi eseguiti il 2026-09-12: QC delle firme, esperimento di trasferimento, calibrazione del nullo con lo scorer ufficiale. Gli artefatti pesanti restano in `artifact_root` | [R-010](#r-010--reportspipeline) |
| `reports/pipeline/transfer_experiment_e001_superseded.json` | superato | `reports/pipeline/transfer_experiment.json` | Stessa esecuzione, ma con un campo di riepilogo a `null` per un errore di chiave nella funzione di aggregazione. I numeri di trasferimento sono identici; conservato perché una riesecuzione non sovrascrive un'evidenza | [R-010](#r-010--reportspipeline) |
| `reports/scorer_2026-09-12/vcc2026_contract.json` | attuale | — | Riestrazione del contratto dallo stesso `cell-eval2` 0.16.0, con il `floor_note` corretto. Sostituisce funzionalmente `reports/scorer/vcc2026_contract.json`, che resta come evidenza storica | [R-002](#r-002--reportsscorervcc2026_contractjson) |
| `src/vcc2026/` (genes, signatures, pseudobulk, models, splits, evaluation, registry, manifest) | attuale | — | Moduli aggiunti il 2026-09-12, coperti da 42 test nuovi. I moduli preesistenti non sono stati toccati; `config.py` è stato solo esteso | — |
| `scripts/40_build_signatures.py`, `41_transfer_experiment.py`, `42_null_calibration.py` | attuale | — | I tre stadi della pipeline. Eseguiti il 2026-09-12; i loro manifesti sono in `reports/pipeline/` | — |
| `docs/SOTTOMISSIONE.md` | attuale | — | Contratto di sottomissione verificato il 2026-09-12 sulle fonti ufficiali e sulla CLI installata, comandi esatti per rigenerare, convalidare, inviare e leggere i punteggi, e la distinzione fra punteggi normalizzati e metriche locali. La sezione 4 è **compilata** dalla prima sottomissione del 2026-09-13 | — |
| `reports/trial_2026-09-12/` | attuale | — | Artefatti leggeri del primo trial locale: calibrazione annidata, confronto fuori campione, misure di risorse, convalide e log di `vcc prep`. Introdotti da [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md). Le previsioni pesanti restano in `artifact_root` | [R-011](#r-011--reportstrial_2026-09-12) |
| `reports/trial_2026-09-12/calibration_c001_peak_memory_unrecorded.json` | superato | `reports/trial_2026-09-12/calibration_c002.json` | Stessa esecuzione e numeri identici; il solo campo `peak_rss_bytes` è `null` perché il lettore di memoria di picco su Windows non era ancora corretto. Conservato perché una riesecuzione non sovrascrive un'evidenza | [R-011](#r-011--reportstrial_2026-09-12) |
| `configs/trials.yaml` | attuale | — | Definizione dei due trial: regola di previsione, dati leggibili, seed, e ciò che il trial **non** è. `src/vcc2026/trials.py` lo legge per freeze, generazione e packaging, così un run non può contraddire il trial che dichiara | — |
| `src/vcc2026/inference.py`, `resources.py`, `trials.py` | attuale | — | Moduli aggiunti il 2026-09-12: trasformazione da log2FC a conteggi con vincolo compositivo (D-015), misura di RAM/disco e memoria di picco, definizione dei trial. Coperti da 42 test in `tests/test_trial_inference.py` | — |
| `scripts/43_freeze_trial.py`, `44_calibrate_transfer.py`, `45_generate_prediction.py`, `46_validate_package.py`, `47_resource_report.py` | attuale | — | Gli stadi del trial: congelamento dello stato, calibrazione annidata, generazione, convalida e packaging, consolidamento delle risorse. Eseguiti il 2026-09-12; i risultati leggeri sono in `reports/trial_2026-09-12/` | — |
| `tests/test_trial_inference.py` | attuale | — | 42 test su prevenzione delle fughe di informazione nella selezione, conservazione dell'identità dei contesti, generazione dei conteggi e ampiezza degli offset CSR | — |
| `reports/trial_2026-09-13/` | attuale | — | Artefatti del packaging a memoria limitata di trial-01: report della corsa, manifesto, e `source_snapshot.tar.gz` — **il codice, non i suoi hash**: 66 file, 180 KB, verificato che ricostruisca i moduli byte per byte. Il `.vcc` (3,91 GiB) resta in `artifact_root`. Introdotti da [CP-0005](checkpoints/0005-packaging-streaming-trial01.md) | [R-012](#r-012--reportstrial_2026-09-13) |
| `reports/trial_2026-09-13/submit_PNn227rxP3bVByS37W41.json`, `status_PNn227rxP3bVByS37W41.json`, `submission_PNn227rxP3bVByS37W41.md` | attuale | — | La prima sottomissione valutata: output verbatim di `vcc submit` e `vcc status`, più la loro lettura ordinata. **Punteggio 0,045929, rango 446/920.** Non sovrascrivere: sono l'unica prova di che cosa il server ha risposto quel giorno | [R-012](#r-012--reportstrial_2026-09-13) |
| `reports/trial_2026-09-17/submission_texts.md` | attuale | — | I testi di nome e descrizione delle sottomissioni t02 e t03, scritti prima di mandarle. Sezione «Correzioni» in fondo: ogni numero corretto dopo la generazione è annotato lì, con la fonte | — |
| `reports/trial_2026-09-17/t02/` | attuale | — | Prove del file t02 prodotto su Colab il 2026-09-17 (job 011): `generation.json` (269/300 bersagli coperti, bin cis, diagnostica per contesto), `packaging.json` e manifesto (24 convalide PASS, X bit-identica all'ingresso), `prediction.vcc.sha256` e il log completo del job. Il `.vcc` (3,88 GiB) resta sul Drive, non nel repository | — |
| `reports/trial_2026-09-17/t03/` | attuale | — | Prove del file t03 (ampiezza di trasferimento 2,0, job 014): stessa forma del t02. **Generato e verificato ma mai sottomesso**, vedi [CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md) §6 | — |
| `reports/trial_2026-09-17/submit_49Gvtu504clN1mIu8T2V.json`, `reports/trial_2026-09-17/status_49Gvtu504clN1mIu8T2V.json`, `reports/trial_2026-09-17/submit_t02_raw.json` | attuale | — | La seconda sottomissione valutata (t02): output verbatim di `vcc submit` e `vcc status`, più la cattura grezza del comando. **Punteggio −0,092774, rango 764.** Contiene i valori **grezzi** di tutti e sei i membri, che sono ciò che ha reso risolvibili le ancore. Non sovrascrivere | — |
| `reports/anchors_2026-09-17/anchors.json` | attuale | — | Le ancore ufficiali di `vcc2026-val-1` risolte algebricamente da due sottomissioni valutate (stadio 82): base e replica di cinque membri su sei, con la ricostruzione degli scalati pubblicati come verifica. La `mse` resta indeterminata. Valide per questo pannello e questa `anchor_version` | — |
| `reports/prediction_t03_2026-09-17/prediction.json`, `scripts/84_predict_official.py` | attuale | — | Previsione **registrata prima** della sottomissione: dai grezzi del banco h002, dal punto di calibrazione t02 e dalle ancore ufficiali, media attesa +0,0338 per il t03. Calibrazione a un solo punto per membro, senza barra d'errore: è una previsione, non una misura. Non sovrascrivere, serve al confronto con il punteggio reale | — |
| `reports/trial_2026-09-17/submit_0TbVAwhVTj6UYpaU2v9d.json`, `reports/trial_2026-09-17/status_0TbVAwhVTj6UYpaU2v9d.json`, `reports/trial_2026-09-17/submit_t03_raw.json` | attuale | — | La terza sottomissione valutata (t03, ampiezza 2,0): **punteggio +0,019692, rango 576**. È il punto che ha verificato fuori campione le ancore di CP-0021 e la previsione registrata dello stadio 84. Non sovrascrivere | — |
| `reports/anchors_2026-09-17/three_points/anchors.json` | attuale | — | Le stesse ancore ririsolte con tre sottomissioni: il terzo punto non entra nel calcolo e i suoi scalati vengono riprodotti con scarto massimo 0,002. È la verifica fuori campione, non una seconda stima | — |
| `reports/prediction_calls_2026-09-17/t02_r4000/` | attuale | — | Stadio 83 sul file t02 già sottomesso: quanti geni dichiara significativi sui contesti ufficiali (mediana 53/17/1 in A/B/C, media 288/231/95, su 4.000 controlli dei 18.400 — quindi un **limite inferiore**), e il controllo sul gene bersaglio, che risulta abbassato solo del 5-9% invece che dell'85%. Nessun `k` e nessun `n_conf`: richiedono i dati perturbati nascosti | — |
| `reports/contexts_2026-09-17/`, `scripts/85_identify_contexts.py` | attuale | — | Che cosa sono i contesti ufficiali, dai marcatori di lignaggio nelle loro cellule di controllo. **Misurato:** A è un linfocita T (`CD3D` 943 CPM nel 100% delle cellule), B è cheratine+/E-caderina−/vimentina-alta, C è epiteliale coeso (`EPCAM` 312, `VIM` 2,0). Pluripotenza, marcatori eritroidi ed epatocitari **assenti in tutti e tre**: K562 e HepG2 non condividono il lignaggio con nessun bersaglio. I nomi di linea (Jurkat, HEK293) sono ipotesi, il lignaggio è misura | — |
| `reports/trial_2026-09-17/t04/` | attuale | — | Prove del file t04 (`--max-calls 150`, mediana di geni mossi esattamente 150 per contesto). **Generato e mai sottomesso**: [CP-0022](checkpoints/0022-previsione-verificata-t03.md) misura che va nella direzione contraria ai dati. Resta come controllo | — |
| `reports/call_budget_2026-09-17/c001/` | attuale | — | Stadio 80 sulle statistiche a singola cellula, contesti A/B/C, 20 bersagli, pool di riferimento da 1.500 cellule: quante chiamate producono le ampiezze 1,0 e 2,0. **Regime più piccolo di quello ufficiale** (18.400 controlli), quindi un limite inferiore | — |
| `reports/source_coverage_2026-09-17/c001/`, `reports/source_coverage_2026-09-17/c002/`, `scripts/86_source_panel_coverage.py` | attuale | — | Quanto del pannello del banco HepG2 copre ciascuna sorgente di trasferimento, misurato prima di spendere Colab. **Misurato:** dei 1.061 bersagli HepG2 con almeno 50 cellule, RPE1 ne copre 1.061 e K562 genome-wide 1.059; RPE1 misura 7.733 dei 9.624 geni HepG2, K562 7.425. Mediana di cellule per bersaglio 101 (RPE1) contro 184 (K562), cellule NTC 11.485 contro 75.328: la copertura non e' il confondente, la profondita' lo e'. `shared_targets.txt` e' il pannello condiviso (1.059) che i due bracci devono usare per essere confrontabili: `c002` (stessa misura piu' il controllo di selezione) misura che **senza** `--targets-file` i due banchi condividerebbero solo **205 bersagli su 300**, e con esso 300 su 300 | — |
| `configs/source_lineage_rule.yaml`, `scripts/87_compare_source_benches.py` | attuale | — | Regola **pre-registrata** (scritta il 2026-09-18 ~00:15, prima che i job 018 e 019 producessero qualsiasi cosa) per leggere il confronto RPE1 contro K562 sul banco HepG2, e lo stadio che la applica meccanicamente. Contiene il cancello di validita: `replicate`, `baseline` e `null_new` non leggono la sorgente e devono coincidere, altrimenti i due banchi non condividono una verita e il confronto e nullo. `owner_confirmed: false` alla stesura; dal 18 intorno alle 13:00, prima dei risultati, `owner_confirmed: true` con `verdict_scope` (una vittoria merita un approfondimento, non un'adozione). Soglia e bracci invariati | — |
| `reports/source_lineage_2026-09-18/` | attuale | — | Il confronto RPE1 contro K562 sul banco HepG2. `PRIMA_DEI_RISULTATI.md` è scritto **prima** che esistesse qualunque output: registra che i job 018 e 019 non hanno prodotto nulla (runtime perso il 17 intorno alle 22:10 UTC) e sono stati rimessi in coda come 020 e 021 con output `_r2`, e dichiara due letture secondarie che la regola non conteneva: la fedeltà a parità di chiamate (volume contro direzioni) e lo stato di TP53 come spiegazione alternativa al lignaggio. Non cambia la regola né la soglia. Il suo §4 registra la revisione del proprietario, sempre prima dei risultati, e la copertura dei bersagli ufficiali (RPE1 0/300). **Risultati** ([CP-0023](checkpoints/0023-rpe1-contro-k562-su-hepg2.md)): i due `bench.json` copiati da Drive; `c001/` è lo stadio 87 (verdetto `WINS_RPE1`, cancello passato); `c002/` è lo stadio 88 (vantaggio +0,056…+0,096 a parità di chiamate medie, pre-registrato; confronto appaiato esplorativo scelto dopo i risultati). **Controllo d'identità** ([CP-0024](checkpoints/0024-identita-del-bersaglio-su-hepg2.md)): `*_r3_bench.json` (job 022/023); `c003/` è lo stadio 89 (riproducibilità passata; K562 `MIXED`, RPE1 `SPECIFIC`, vantaggio di RPE1 `MAINLY_COMMON` alla coppia a ~100 chiamate); `c004/` è lo stadio 90, precisione per bersaglio, esplorativo | — |
| `reports/conditioned_2026-09-18/`, `configs/conditioned_rule.yaml`, `scripts/92_train_conditioned.py`, `scripts/93_pick_amplitudes.py`, `scripts/94_conditioned_verdict.py`, `src/vcc2026/conditioned.py`, `src/vcc2026/bench_score.py` | attuale | — | Primo predittore neurale condizionato su bersaglio e contesto (mandato del proprietario del 18 settembre). Rete in numpy (cancello di trasferimento per gene + termine bilineare bersaglio × gene; il contesto entra per gene come espressione basale nei controlli) contro un modello lineare con gli stessi input, il trasferimento semplice e la ricetta t03, con lo stesso generatore e gli stessi bersagli. Tre split: contesto nuovo (C), congiunto (J), bersagli nuovi (T). `panel/` fissa i bersagli prima del training; regola scritta prima di ogni training su dati reali, `owner_confirmed: false`. **Esito** ([CP-0026](checkpoints/0026-predittore-neurale-condizionato.md)): `DISCARD`, in `verdict/`. `benches/` contiene i quattro `bench.json` (validazione e test) e le scelte dello stadio 93; `effect_space/` le letture centrate dello stadio 95 (esplorative); `train*_manifest.json` i training; `PIANO_INVIO_t06.md` il piano di invio scritto prima dei risultati, con l'aggiunta che sostituisce il t06 con il t07. Job 028, 033, 034, 037 (ucciso per memoria), 038, 039 e 041 | — |
| `reports/common_component_2026-09-18/`, `configs/common_component_rule.yaml`, `scripts/91_common_component_verdict.py` | attuale | — | Tenere o scartare la componente comune RPE1 (`common_from_bulk`, termini `common_aX` e `permcommon_aX` negli stadi 73 e 75, `--a-common` nello stadio 76). Disegno scelto dal proprietario: peso scelto su un insieme di bersagli e verdetto su un altro, disgiunto, in due banchi (HepG2 con la ricetta t03; bersagli ufficiali in K562); si tiene solo se passano entrambi. `panel/` contiene i file dei bersagli, fissati prima dei job 024-027. Regola scritta prima dei job, `owner_confirmed: false`. **Esito** ([CP-0025](checkpoints/0025-componente-comune-scartata.md)): `DISCARD`, in `c001/verdict.json`, con i quattro `bench.json` copiati accanto | — |
| `reports/trial_2026-09-19/` | attuale | — | File generati la notte del 19 settembre. `t06/`: la rete condizionata (job 040), generata e impacchettata ma **non inviata**, perché il modello rilanciato dal job 039 non è quello giudicato dai banchi (`reports/conditioned_2026-09-18/PIANO_INVIO_t06.md`). `t07_job042/`: il log del primo tentativo di generare il t07, interrotto durante l'impacchettamento dalla perdita del runtime (circa 02:14 UTC); nessun file del t07 è arrivato su Drive. `t07/`: il t07 rigenerato dal job 043 e **inviato** il 19 alle 09:42:58 UTC (entry `BV1gqrIYuy2KMVZSGmN4`, punteggio −0,016004, rango 671), con i record di generazione e impacchettamento; accanto, l'output verbatim di `vcc submit` e `vcc status` e i testi della sottomissione ([CP-0027](checkpoints/0027-t07-punteggio-ufficiale.md)) | — |
| `reports/prediction_t07_2026-09-19/`, `scripts/95_centered_effect_space.py` | attuale | — | Previsione del punteggio ufficiale del t07 (stadio 84), registrata il 2026-09-19 alle 01:22 UTC prima dell'invio: +0,0101; ufficiale −0,0160 (`comparison.json`, [CP-0027](checkpoints/0027-t07-punteggio-ufficiale.md)). Lo stadio 95 misura la parte di una previsione specifica del bersaglio (correlazione centrata, accoppiamento, confronto con la media) | — |
| `configs/specificity_rule.yaml`, `scripts/88_matched_volume_reading.py`, `scripts/89_specificity_reading.py`, `scripts/90_per_target_precision.py` | attuale | — | 90: precisione dei segni `k/n_pred` per bersaglio dai `components_<braccio>.csv`, esplorativa. 88: la lettura di due banchi a parità di chiamate medie, più un confronto appaiato per bersaglio dichiarato come scelto dopo i risultati. 89 e la regola: il controllo d'identità del bersaglio (`shuffled_aX`) per i job 022 e 023. Regola scritta prima dei job; **versione 2** scritta dopo il loro avvio ma prima di ogni output, perché un test sintetico a risposta nota mostrava che la versione 1 chiamava `MIXED` una sorgente nulla. `owner_confirmed: false` | — |
| `scripts/82_solve_anchors.py`, `83_prediction_calls.py` | attuale | — | 82: risolve base e replica dal doppio output di `vcc status`. 83: conta quanti geni una previsione generata dichiara significativi contro le cellule di controllo ufficiali (`n_pred`) — non calcola `k` né `n_conf`, che richiedono i dati perturbati nascosti | — |
| `src/vcc2026/packaging.py` | attuale | — | Convalida e packaging `.vcc` senza materializzare la matrice. Le convalide sui metadati **sono** quelle ufficiali, importate e chiamate; quelle sulla matrice sono equivalenti a blocchi. Rifiuta esplicitamente i layout che non sa preservare | — |
| `scripts/48_package_prediction.py` | attuale | — | Lo stadio che convalida, impacchetta e verifica. Esce con codice diverso da zero se qualcosa fallisce, e non scrive nulla se la convalida non è pulita | — |
| `tests/test_packaging_parity.py` | attuale | — | 41 test di parità contro `vcc prep` 0.2.0 su fixture a forma ufficiale completa: stessa accettazione, stesso rifiuto, stesse codifiche HDF5. Circa 98 s | — |
| `notebooks/kaggle_package_trial01.ipynb` | attuale | — | Percorso remoto per la stessa implementazione su Kaggle CPU. **Non eseguito**: il run locale è riuscito. Resta pronto per il set finale D/E/F | — |
| `tests/test_pipeline_contracts.py` | attuale | — | 42 test sui contratti che fallirebbero in silenzio: maschere contro zeri, fuga di bersagli negli split, sovrascrittura di manifesti, livelli di verifica del registry | — |
| `docs/ORCHESTRATORE.md` | attuale | — | Architettura dell'orchestratore locale per le consultazioni multi-modello. Dichiara in testa che cosa e' stato eseguito e che cosa e' solo implementato: gli adattatori verso i servizi reali non sono mai stati usati | — |
| `src/orchestrator/` | attuale | — | Il codice dell'orchestratore: motore, contratto di risposta, stato persistente, adattatori, rapporto, CLI. Solo libreria standard, tranne PyYAML per le configurazioni YAML e Playwright per gli adattatori web | — |
| `configs/orchestrator/` | attuale | — | Configurazione operativa, profili dei servizi web, incarichi e risposte preparate a mano per le prove a secco. I profili di DeepSeek e Kimi sono `verified: true` dal 13 settembre, ciascuno citando l'invio reale che lo giustifica. **Solo DeepSeek dichiara un controllo di ricerca sul web** (`ricerca_intelligente`); su Kimi non ne è mai stato osservato uno | — |
| `scripts/orch.cmd` | attuale | — | Wrapper della console `orch`, come `py.cmd`: UTF-8 e `src/` sul PYTHONPATH. Usa `VCC2026_ORCH_PYTHON` se impostata, per tenere Playwright fuori dall'ambiente di analisi | — |
| `tests/test_orchestrator.py` | attuale | — | 95 test sui modi in cui l'orchestratore potrebbe sbagliare in silenzio: incarico modificato senza versione, materiale fuori perimetro, risposta che prova a cambiare le regole, doppio invio dopo un crash, accordo scambiato per verifica, servizio morto sostituito | — |
| `reports/orchestrator/` | attuale | — | Copie di esecuzioni dell'orchestratore tenute come evidenza. Le prove del 13 e del 14 settembre sono **a secco**. Puntatore alla campagna Jiang live del 15 settembre: `reports/orchestrator/jiang-audit-20260915.md` (run in `VCC2026_DATA_ROOT`, fermata `service_unavailable`) | — |
| `docs/RICERCA_SCIENTIFICA.md` | attuale | — | La modalità `scientific_research`: tre fasi, livelli di provenienza, deduplicazione delle fonti, regola delle piste, dossier. Dichiara in testa riga per riga che cosa è stato provato e che cosa no. Introdotta da [CP-0010](checkpoints/0010-modalita-ricerca-scientifica.md) | — |
| `src/orchestrator/research/` | attuale | — | Il codice della modalità di ricerca: contratto, prompt delle tre fasi, scelta deterministica delle piste, dossier e rapporto, motore. Non importa `oracle` né alcun client HTTP, e c'è un test per entrambe le cose | — |
| `tests/test_orchestrator_research.py` | attuale | — | 65 test sulle promozioni che non si annuncerebbero: una ricerca dichiarata che diventa osservata, un riferimento che diventa una fonte, una fonte solo elencata che diventa letta, un'opinione che diventa un risultato riferito dagli autori, due articoli che diventano uno | — |
| `reports/orchestrator/prova-a-secco-ricerca-2026-09-14/` | attuale | — | La campagna di ricerca di prova, per intero: dossier, piste, rapporto, eventi e cartelle dei passi. **I contenuti delle risposte sono inventati**, con DOI a prefisso `10.0000/finta-`. Dimostra il motore, non gli adattatori reali | — |
| `docs/oracle/` | attuale | — | Contratto del prototipo di oracolo numerico pairwise sulla loss. Indipendente dall'orchestratore; non valuta ipotesi biologiche | — |
| `reports/oracle/` | attuale | — | Prima esecuzione della CLI sull'esempio a tre casi. Fixture sintetici, non dati della gara. Introdotti da [CP-0007](checkpoints/0007-oracle-pairwise-loss.md) | — |
| `src/oracle/` | attuale | — | Verificatore `oracle.pairwise_loss` 0.2.1, sola libreria standard, frazioni esatte. Non importa `orchestrator` né `vcc2026`. Correzioni in [CP-0008](checkpoints/0008-oracle-fraction-regression.md) e [CP-0009](checkpoints/0009-oracle-json-number-csv-error.md) | — |
| `tests/test_oracle_pairwise_loss.py` | attuale | — | Test su fixture sintetici; i risultati attesi sono calcolati a mano, non generati dal verificatore | — |


## Dati

Nessun file di dati è stato spostato o copiato per compilare questo registro. I dati
pesanti stanno fuori dal repository, sotto `C:/Users/ferra/vcc2026-data`
(vedi `configs/config.yaml`). Dal 16 settembre due grezzi pesanti stanno anche sul
Google Drive del proprietario, secondo la sua dichiarazione
([CP-0018](checkpoints/0018-drive-storage-confermato.md)).

Tipi: `grezzo` (sorgente scaricata, da non modificare), `derivato` (prodotto da uno
script nostro), `campione` (piccolo estratto di verifica), `temporaneo` (cache o
dipendenza di runtime, ricreabile).

| Identificatore | Tipo | Stato | Provenienza | Riproducibile con | Nota |
|---|---|---|---|---|---|
| `C:/Users/ferra/vcc2026-data/raw/vcc_2026_controls.zip` e `raw/controls/` | grezzo | attuale | Bundle ufficiale della gara; `manifest.json` presente nella cartella. Checksum **non** ricalcolato da questo registro | Nuovo download dal sito ufficiale | Sorgente primaria: non modificare mai |
| `C:/Users/ferra/vcc2026-data/external/K562_gwps_raw_bulk_01.h5ad` | grezzo | attuale | Replogle 2022, scaricato con `scripts/10_fetch_external.py`. Checksum locale **sconosciuto** | `scripts/10_fetch_external.py` | Nonostante il nome `raw_bulk`, i valori per cella sono frazionari: non passarli come conteggi interi |
| `C:/Users/ferra/vcc2026-data/external/K562_essential_raw_bulk_01.h5ad` | grezzo | attuale | Come sopra. Checksum locale **sconosciuto** | `scripts/10_fetch_external.py` | 0/300 bersagli del pannello: utile come stress test |
| `C:/Users/ferra/vcc2026-data/external/rpe1_raw_bulk_01.h5ad` | grezzo | attuale | Come sopra. Checksum locale **sconosciuto** | `scripts/10_fetch_external.py` | 0/300 bersagli del pannello |
| `C:/Users/ferra/vcc2026-data/external/vcc2025/` | grezzo | attuale | Quattro CSV di metadati H1 2025. **Nessuna matrice RNA presente** | Da acquisire per la via ufficiale Arc | L'assenza dell'RNA è il motivo per cui il benchmark P0 non è partito |
| `C:/Users/ferra/vcc2026-data/interim/` | derivato | attuale | Prodotto dagli script 01/11/12/16 | Rilanciando quegli script | `shared_panel.csv` è di 13 byte: contiene solo l'intestazione, cioè un'intersezione vuota. È un risultato, non un errore |
| `C:/Users/ferra/vcc2026-data/predictions/smoke.h5ad` | derivato | storico | Prodotto da `scripts/02_smoke_test_submission.py` | `scripts/02_smoke_test_submission.py` | È una prova di formato del writer, non una previsione: non valutarlo come modello |
| `reports/data_audit/hipsci_metadata/*.tsv.gz` (21 MB nel repo) | grezzo | attuale | Figshare HIPSCI, **MD5 verificato** contro il valore dichiarato dalla sorgente in `scripts/14_fetch_hipsci_metadata.py` | `scripts/14_fetch_hipsci_metadata.py` | Esempio di dato ancora buono la cui strategia è cambiata: HIPSCI è scesa di priorità, i metadati restano validi |
| `reports/candidate_verification/annotations/` | grezzo | attuale | Scaricato con `scripts/22_fetch_candidate_annotations.py`; URL, byte e sha256 in `annotations/manifest.json` | `scripts/22_fetch_candidate_annotations.py` | Librerie di guide e metadati genici: piccoli e necessari ai join |
| `reports/candidate_verification/pilot/cd4_D1_Rest_64.h5ad` | campione | attuale | Provenienza completa: URL, seed, byte trasferiti e sha256 dell'output in `cd4_D1_Rest_64.manifest.json` | `scripts/25_ingest_cd4_pilot.py` con un `--out` nuovo | 64 cellule: prova che l'ingestione funziona, non abbastanza per scegliere un modello |
| `reports/candidate_verification/*.json` (sonde remote) | derivato | attuale | Sonde remote con budget di byte; manifest con sha256 | Script 20, 21, 23, 24, 26 | Fotografie di endpoint pubblici a una certa data: le sorgenti possono cambiare |
| `.runtime-deps/pyarrow` | temporaneo | attuale | Installato solo per la sonda Orion; ignorato da git | Reinstallazione | Ricreabile: candidato alla pulizia quando la sonda Orion non serve più |
| `C:/Users/ferra/vcc2026-data/artifacts/` (e001, e002, n001..n003) | derivato | attuale | Prodotto dagli stadi 40/41/42 il 2026-09-12; ogni run ha il suo manifesto con hash e ambiente | Rilanciando gli stadi con un `--run-id` nuovo | 519 MB di firme piu 3x112 MB di bundle a singola cellula. Fuori dal repository (D-001); i risultati leggeri sono copiati in `reports/pipeline/` |
| `C:/Users/ferra/vcc2026-data/artifacts/m001` | derivato | attuale | Pilot modulare 2026-09-14: split, pesi, `results.json` | `scripts/51_run_modular_pilot.py --run-id` nuovo | Fuori dal repository (D-001). Tabella, inventario, universo e specifica del bundle copiati in `reports/benchmark_2026-09-14/` |
| `C:/Users/ferra/vcc2026-data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad` | grezzo | attuale | Mirror scPerturb di GSE264667, 850.590.740 byte, **md5 verificato** contro Zenodo (`af2be47f…`); URL, data e licenza in `reports/hepg2_2026-09-14/acquisition.json` | Riscaricabile dallo stesso endpoint | 0,85 GB compressi contro 5,2 GB della copia GEO: la scelta del mirror è dettata da D-005 (≥10 GiB liberi). Non modificare in place |
| `C:/Users/ferra/vcc2026-data/artifacts/e003` | derivato | attuale | Firme HepG2 (2.346 bersagli), profilo basale NTC, QC e censimento. Controlli appaiati per batch | `scripts/53_build_hepg2_signatures.py --run-id` nuovo | Stessa definizione di log2FC delle firme e001, così un modello che legge le due sorgenti legge la stessa quantità |
| `C:/Users/ferra/vcc2026-data/artifacts/m002`, `m003`, `m004` | derivato | attuale | Benchmark a tre contesti: split, pesi, `results.json`. m003 è il solo fold con HepG2 fuori, con le predizioni salvate; m004 ripete m002 aggiungendo i confronti appaiati con/senza contesto e l etichetta di ampiezza corretta, con le stesse 108 righe numeriche | `scripts/51_run_modular_pilot.py --run-id` nuovo | Fuori dal repository (D-001). I file leggeri sono copiati in `reports/benchmark_3ctx_2026-09-14/` |
| `C:/Users/ferra/vcc2026-data/artifacts/m002-crashed-row-axis-2026-09-14` | derivato | storico | Primo tentativo del run a tre contesti, fermato dal controllo di coerenza fra righe ed etichette in `TrainArrays` | Non rieseguire: è la prova del guasto | Tenuto perché documenta che il controllo ha funzionato, non perché contenga risultati |
| `C:/Users/ferra/vcc2026-data/interim/hepg2_bundle/` | derivato | attuale | Bundle a singola cellula (reale e predetti) e output dello scorer per il confronto generatore×predittore | `scripts/57_generator_x_predictor.py` con un `--out` nuovo | Cellule reali di controllo condivise da tutti i bundle, come chiede il contratto |
| `C:/Users/ferra/vcc2026-data/artifacts/g001`, `g002` | derivato | attuale | Tabella GO slim congelata (140 termini, 2.693 simboli) e run del pilot dei descrittori | `scripts/58_build_go_slim_table.py` e `scripts/51_run_modular_pilot.py` con `--run-id` nuovo | Fuori dal repository (D-001). I file leggeri sono copiati in `reports/go_slim_2026-09-15/` |
| `C:/Users/ferra/vcc2026-data/artifacts/s001`, `s002`, `r001` | derivato | attuale | s001 SVD esatta, s002 randomizzata, r001 confronto di rango. Stessi 160 bersagli; s001/s002 stessi split | `scripts/51_run_modular_pilot.py` con `--run-id` nuovo | Fuori dal repository (D-001). I file leggeri sono in `reports/svd_2026-09-15/` e `reports/rank_2026-09-15/` |
| `C:/Users/ferra/vcc2026-data/artifacts/x001` | derivato | attuale | Run del gate di espressione 2026-09-16: split, pesi dei nove bracci originali, artefatti dei nove bracci gate, `results.json` | `scripts/51_run_modular_pilot.py --config configs/benchmark_expression_gate.yaml` con un `--run-id` nuovo | Fuori dal repository (D-001), 82 MB. Le sue 54 righe dei bracci originali coincidono con quelle di `m002`, differenza assoluta 0,0. I file leggeri sono in `reports/expression_gate_2026-09-16/` |
| `C:/Users/ferra/vcc2026-data/interim/encoder_inputs_2026-09-14/` | grezzo | attuale | HGNC, GOA GAF/GPI, GO slim, go-basic.obo, STRING info e physical.links; sha256 in `reports/encoder_inputs_2026-09-14/downloads.json` | `scripts/56_probe_target_descriptors.py` | Snapshot pubblico per i descrittori di modo B. Non modificare in place |
| `reports/jiang_2026-09-15/small_files/` | grezzo | attuale | Readme e liste pathway Jiang (file < 2 MB). Gli RDS non sono stati scaricati | `scripts/61_probe_jiang.py` | Non sono matrici di counts |
| `C:/Users/ferra/vcc2026-data/interim/remote_bundle_2026-09-15/` | derivato | attuale | Snapshot codice 536 KB + `gene_names.csv` + notebook. Nessuna matrice | `scripts/67_remote_ingest.py --prepare-bundle` | Da caricare su Colab/Kaggle; HepG2 e Jiang si scaricano da Zenodo là. Dal 16 settembre HepG2 è già su Drive (CP-0018): va collegato, non riscaricato |
| Google Drive del proprietario: `K562_gwps_raw_singlecell_01.h5ad`, `NadigOConner2024_hepg2.h5ad` | grezzo | da-verificare | Copie caricate dal proprietario, **dichiarate** il 2026-09-16 con le dimensioni mostrate da Drive (61,31 GB e 811,2 MB), coerenti in unità binarie con i 65.830.941.948 e 850.590.740 byte di `configs/remote_catalog.yaml`. Percorso su Drive non comunicato; md5 **non calcolato** su nessuna delle due copie | Nuovo caricamento dalle sorgenti figshare 35775507 e Zenodo 13350497 | Da collegare, non da scaricare. Un run Colab le vede solo in `<VCC2026_DATA_ROOT>/raw/replogle/` e `<VCC2026_DATA_ROOT>/raw/nadig_hepg2/` (predefinita: `/content/drive/MyDrive/vcc2026/data`). Diventano `attuale` quando un run ne verifica l'md5. [CP-0018](checkpoints/0018-drive-storage-confermato.md), [R-013](#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb) |

## Schede di revisione

### R-001 — `README.md`

- **Perché è segnalato:** è il primo file che chiunque legge, ed è fermo alle 21:51
  dell'11 settembre, cioè a prima dell'analisi del 12 settembre. Un agente che legge
  solo il README prende per correnti priorità e affermazioni già corrette.
- **Affermazioni contestate:**
  1. La sezione "Review and reorientation" chiude il racconto all'11 settembre e non
     cita `docs/candidate_adversarial_review_2026-09-12.md`, che ha riordinato le
     priorità di acquisizione verso CD4 e Orion.
  2. «`mse` cannot go below 0 […] so it is scale-invariant» e «Commit on direction,
     shrink magnitude»: il pavimento è sullo *score normalizzato*, non sull'errore, e
     l'invarianza di scala del PDS vale sul delta già trasformato, non su una
     compressione fatta nello spazio dei conteggi.
  3. «**B** an epithelial-mesenchymal hybrid carrying eye-field transcription factors»:
     l'identità oculare è un'ipotesi debole (PAX6 34, LHX2 38, MITF 27 CPM, contro
     CLU 7.857 e VIM 6.052), non un risultato.
  4. La tabella "Plan" dà la fase 1 come "next" senza dire che è bloccata dall'assenza
     di un bundle di valutazione reale e dall'RNA di H1 2025 non scaricato.
  5. Il layout elenca `notebooks/`, che è vuota.
  6. *Aggiunta il 2026-09-12 (CP-0004).* La tabella "Plan" dà la fase 0 come **done**
     con la formula «streaming submission writer verified against official `prep`».
     **Non esiste alcun log di `vcc prep` anteriore al 2026-09-12**, e l'unico
     artefatto candidato, `smoke.h5ad`, contiene 3 perturbazioni su 300. Misurato il
     2026-09-12: `vcc prep` con le opzioni predefinite **rifiuta** un file che non
     predice esattamente le 300 perturbazioni ufficiali per contesto. Resta possibile
     che sia stato eseguito con `--no-verify-targets`, nel qual caso avrebbe
     verificato asse genico, contesti, conteggi per perturbazione e conteggi grezzi
     ma **non** la lista delle perturbazioni. L'affermazione va letta come «il writer
     produce un h5ad strutturalmente valido», che è sostenuta da
     `scripts/02_smoke_test_submission.py`, non come «la CLI ufficiale ha validato una
     sottomissione», che non lo è.
- **Evidenza contraria:** `docs/candidate_adversarial_review_2026-09-12.md` §§2–3;
  `reports/candidate_verification/scorer_clamp_check.json`;
  `reports/context_identity/markers.csv`; elenco di
  `C:/Users/ferra/vcc2026-data/external/vcc2025/`; per la 6, il log
  `prep_dry_run.log` del pilot in `reports/trial_2026-09-12/`.
- **Cosa resta valido:** descrizione del compito, formato di sottomissione, tabella
  delle sei metriche, layout dei dati, setup, wrapper `.cmd`, autenticazione,
  scadenze. È la parte più consultata ed è corretta.
- **È ancora usato o citato:** sì, è l'ingresso predefinito del repository.
- **Disposizione proposta:** mantenere il file, aggiungere in testa il rimando a
  `docs/PROGETTO.md` e note di stato puntuali accanto alle affermazioni contestate
  (fatto il 2026-09-12). Non riscrivere le sezioni scientifiche finché una misura non
  le risolve.
- **Cosa chiuderebbe la revisione:** un benchmark locale che misuri la postura
  "direzione contro ampiezza" (chiude 2), e una verifica dell'identità di B con un
  riferimento esterno appaiato (chiude 3).

### R-002 — `reports/scorer/vcc2026_contract.json`

- **Perché è segnalato:** il campo `floor_note` afferma che
  `clamp_low=0.0 on expr_mse_unbiased_capped_norm makes that metric downside-free`.
  Lo script che lo genera, `scripts/17_extract_scorer_contract.py`, è già stato
  corretto (righe 63–69: «non è una garanzia di restringimento gratuito»), ma il JSON
  non è stato rigenerato e conserva la frase vecchia.
- **Affermazioni contestate:** una sola, il campo `floor_note`. Il pavimento a 0 vale
  sul punteggio normalizzato: chi restringe troppo la previsione non perde punti sotto
  zero, ma può perdere **tutti** i punti positivi della metrica.
- **Evidenza contraria:** `reports/candidate_verification/scorer_clamp_check.json`,
  che eseguendo il pacchetto installato mostra errore grezzo 1,0 → score 0,0 e
  errore 0,55 → score 0,50; `docs/candidate_adversarial_review_2026-09-12.md` §3.
- **Cosa resta valido:** tutto il resto del file, che è la fonte più affidabile che
  abbiamo sul comportamento dello scorer: `official_config` copiato dal pacchetto,
  elenco delle sei metriche punteggiate, direzione, ancora, clamp e aggregazione.
- **È ancora usato o citato:** il file è prodotto da `scripts/17_extract_scorer_contract.py`
  e non è letto da nessun altro script; è citato nei documenti di strategia.
- **Disposizione proposta:** ✅ **fatto il 2026-09-12.** Rigenerato con
  `.\scripts\py.cmd scripts/17_extract_scorer_contract.py --out reports/scorer_2026-09-12`,
  su una destinazione **nuova**: il file originale non è stato sovrascritto, perché
  documenta che cosa diceva l'estrattore prima della correzione. Un confronto campo per
  campo mostra che i due JSON sono identici **tranne** `floor_note`, quindi la
  sostituzione non cambia nessun altro fatto sullo scorer.
- **Cosa chiuderebbe la revisione:** è chiusa. La versione corrente del contratto è
  `reports/scorer_2026-09-12/vcc2026_contract.json`, prodotta dallo stesso
  `cell-eval2` 0.16.0 (D-008) e verificata identica salvo il campo corretto. Registrato
  in [CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §7.

### R-003 — `docs/data_strategy_2026-09-11.md`

- **Perché è segnalato:** è il primo documento di strategia. Il suo ordine di
  acquisizione (H1, poi KOLF2.1J, poi HIPSCI) è stato riordinato due volte, prima per
  lignaggio e poi per copertura misurata. Chi lo legge da solo acquisisce le sorgenti
  sbagliate.
- **Affermazioni contestate:**
  1. §3, l'ordine di priorità 1–4: tutte e tre le prime sorgenti sono contesti
     iPSC/ESC, che non corrispondono al lignaggio di nessuno dei tre contesti.
  2. §1, «Pseudobulk raw […] non usarli come input raw-count single-cell allo scorer»
     nella parte in cui li dichiara non ricostruibili come conteggi: la ricostruzione
     è stata poi misurata come possibile.
- **Evidenza contraria:** `docs/revisione_analisi_2026-09-11.md` §§2–3;
  `docs/candidate_adversarial_review_2026-09-12.md` §§1 e 5;
  `reports/context_identity/`.
- **Cosa resta valido:** molto. Il §4 (contratto di preprocessing: provenienza,
  riconciliazione dei geni, maschere di osservazione, QC, controlli appaiati, due
  riassunti, shrinkage) non è mai stato contestato ed è la guida operativa ancora in
  uso. Il §1 (audit dei controlli ufficiali, profondità, duplicati di simbolo) è stato
  verificato in modo indipendente e confermato. La revisione successiva dice
  esplicitamente che «il metodo dell'audit precedente è solido e va conservato».
- **È ancora usato o citato:** sì, da `README.md` e da
  `docs/revisione_analisi_2026-09-11.md`. Non spostarlo: i riferimenti si romperebbero.
- **Disposizione proposta:** lasciarlo dov'è con stato `superato` **come guida di
  acquisizione**, continuando a usarne il §4 come contratto di preprocessing. Nessuna
  riscrittura: la storia del riordino serve a capire perché le priorità sono cambiate.
- **Cosa chiuderebbe la revisione:** nulla da chiudere. È un documento storico il cui
  stato è corretto così; si aggiorna solo se il §4 venisse rimpiazzato da un contratto
  di preprocessing nuovo.

### R-004 — `docs/revisione_analisi_2026-09-11.md`

- **Perché è segnalato:** corregge bene il documento precedente, ma quattro delle sue
  affermazioni sono state a loro volta messe in discussione il giorno dopo. Una di
  queste è una **contraddizione aperta**: nessuno dei due documenti ha una misura che
  chiuda la questione.
- **Affermazioni contestate:**
  1. **Contraddizione aperta.** §2: «L'asse genico della gara è ordinato per Ensembl
     gene ID. Una sola inversione su 9.387 geni mappabili […] si ricostruisce l'ENSG
     esatto di tutti i 18.533 geni». La revisione avversariale sostiene l'opposto:
     `gene_names.csv` contiene simboli, e l'ordinamento non basta a dedurre gli ID.
     Le due affermazioni non sono del tutto incompatibili — l'ordine può essere
     coerente con un ordinamento per ENSG senza che da questo si deducano gli ID dei
     geni ambigui — ma la conclusione operativa («ogni join con dati esterni diventa
     esatto») **non è dimostrata**.
  2. §6, P1: «l'intorno di co-espressione nel contesto è una previsione a costo zero
     di quali geni si muovono». La co-espressione negli NTC non è uno stimatore
     causale del segno: può nascere da regolatori comuni, stato del ciclo cellulare o
     normalizzazione composizionale.
  3. §6, P0: H1 2025 come banco di prova immediato. Localmente ci sono solo quattro
     CSV di metadati: l'RNA va acquisito.
  4. §5, punti 1–2: «incollare i controlli […] non costa quasi nulla» e l'invarianza
     di scala del PDS. Vero sul delta già trasformato; non trasferibile a una
     compressione fatta nello spazio dei conteggi, e le altre cinque metriche
     dipendono dall'ampiezza.
  5. §2: «**Il pannello 2026 è: espresso ovunque, non essenziale.** Conseguenza
     diretta: le risposte sono piccole per costruzione». Due passaggi non
     dimostrati. La misura è 0/300 sovrapposizioni con i pannelli essential di K562 e
     RPE1: dice che quei pannelli non contengono i nostri bersagli, non che i bersagli
     siano non essenziali **nei contesti della gara**, dove l'essenzialità non è stata
     misurata. E un gene non essenziale può comunque produrre una risposta
     trascrizionale ampia: l'essenzialità riguarda la sopravvivenza della cellula, non
     l'intensità del cambiamento di espressione. L'audit precedente l'aveva scritto
     («L'assenza dal pannello essential non dimostra che un gene sia biologicamente non
     essenziale», `docs/data_strategy_2026-09-11.md` §1): la cautela è andata persa in
     questa revisione, ed è stata poi ripetuta come misura nella prima versione della
     mappa. Corretta in [CP-0002](checkpoints/0002-correzioni-dopo-revisione-umana.md).
- **Evidenza contraria:** `docs/candidate_adversarial_review_2026-09-12.md` §§2–4;
  elenco di `C:/Users/ferra/vcc2026-data/external/vcc2025/`;
  `reports/candidate_verification/scorer_clamp_check.json`. Per il punto 5, la cautela
  esplicita in `docs/data_strategy_2026-09-11.md` §1 e il fatto che nessuna misura di
  essenzialità nei contesti A, B, C esista in questo repository.
- **Cosa resta valido:** le parti più usate del documento. L'identificazione di
  lignaggio di A, B e C (§3); il pannello «espresso ovunque, non essenziale» (§2), che
  la revisione avversariale riprende e non contesta; la povertà di segnale in K562
  (§4: mediana 5 geni DE per riga); la tabella dei clamp (§5), verificata poi
  numericamente; e l'osservazione su `control_source: real`.
- **È ancora usato o citato:** sì, da `README.md`, che ne riassume le conclusioni.
- **Disposizione proposta:** mantenere, stato `da-verificare`, con questa scheda come
  chiave di lettura. Non promuoverlo a `superato`: la maggior parte del documento è la
  base su cui lavoriamo.
- **Cosa chiuderebbe la revisione:** per il punto 5, una misura di essenzialità nei tre
  contesti, oppure la rinuncia esplicita a quella conclusione; l'intensità attesa della
  risposta si stabilisce solo con dati perturbati, non deducendola dal disegno del
  pannello. Per il punto 1, allineare l'asse ufficiale a un
  riferimento Ensembl e **contare quanti dei 18.533 geni restano ambigui**, scrivendo
  la tabella di mapping su file. È un lavoro di poche ore e chiude una contraddizione
  che altrimenti resta a tempo indeterminato. Per il punto 2, un test su dati
  perturbati reali che confronti la direzione predetta dalla co-espressione con la
  direzione osservata. Per il 3, l'acquisizione dell'RNA di H1. Per il 4, il benchmark
  locale.

### R-005 — I due stub 404 di `candidate_verification`

- **Perché è segnalato:** `reports/candidate_verification/cd4_readme.txt` contiene
  quattordici byte, `404: Not Found`, e `cd4_repo_tree.txt` contiene il JSON di errore
  di GitHub. Sembrano evidenza, sono il corpo di due richieste fallite: la prima
  esecuzione ha chiesto il ramo `main`, mentre il repository dell'autore usa `master`.
- **Affermazioni contestate:** nessuna affermazione: sono file di contenuto nullo che
  possono essere scambiati per dati.
- **Evidenza contraria:** `reports/candidate_verification/manifest.json` registra
  onestamente `status: 404` per entrambe le richieste; la seconda esecuzione, con il
  ramo giusto, ha prodotto `expanded/cd4_readme.txt` (2.928 byte) e
  `expanded/cd4_repo_tree.txt` (88.510 byte), registrati con `status: 200` e sha256 in
  `expanded/manifest.json`.
- **Cosa resta valido:** il manifest della prima esecuzione resta utile: documenta che
  il ramo `main` non esiste, che è il motivo per cui `scripts/20_verify_candidate_accessions.py`
  oggi chiede `master`.
- **È ancora usato o citato:** i due `.txt` non sono letti da nessuno script; i nomi
  `cd4_readme` e `cd4_repo_tree` compaiono in `scripts/20_verify_candidate_accessions.py`
  come chiavi di richiesta.
- **Disposizione proposta:** conservare entrambe le acquisizioni e collegarle qui, che
  è ciò che questa scheda fa. **Non rieseguire la sonda sopra questi file**: la versione
  corretta esiste già in `expanded/`, e una riesecuzione con la destinazione predefinita
  sovrascriverebbe sia i due stub sia `reports/candidate_verification/manifest.json`,
  cioè l'unica prova che il ramo `main` non esiste. Una nuova esecuzione deve andare in
  una cartella propria, come ha fatto `scripts/27_verify_grok_leads.py` con
  `--out reports/grok_verification`.
- **Cosa chiuderebbe la revisione:** niente da chiudere. La coppia
  fallimento/successo è già completa e documentata; questa scheda resta come chiave di
  lettura dei due file. *(Una versione precedente di questa scheda proponeva la
  riesecuzione sovrascrivendo: correzione registrata in
  [CP-0002](checkpoints/0002-correzioni-dopo-revisione-umana.md).)*

### R-006 — `reports/candidate_pdf_extracted.txt`

- **Perché è segnalato:** sono 49 KB di prosa italiana sicura di sé, dentro
  `reports/`, che nessun file cita. Un agente che lo trova cercando nei report può
  scambiarlo per un'analisi del progetto. È invece un documento **esterno**, un
  insieme di affermazioni da verificare, e la verifica ne ha smentite parecchie.
- **Affermazioni contestate:** fra le altre, Pisces descritto come sorgente
  disponibile (la scheda pubblica dice "Coming Soon"); Nadig presentato come
  componente Jurkat/HepG2 di Replogle (è uno studio a sé); il DOI `20022944` indicato
  come raccolta processata scPerturb (identifica quattro manifest CSV di file di
  sequenziamento; il record processato è `20029387`); una correlazione residua
  attribuita al confronto sbagliato; una attribuzione «Datlinger in vivo» senza studio
  risolto.
- **Evidenza contraria:** `docs/candidate_adversarial_review_2026-09-12.md` §1 e
  sezione "Rejected", con le sonde eseguite salvate in
  `reports/candidate_verification/`.
- **Cosa resta valido:** ha indirizzato la ricerca verso sorgenti reali e utili, in
  particolare CD4 e Orion. Le sue stringhe di accessione esistono quasi tutte: è
  l'interpretazione di disponibilità e semantica a essere sbagliata.
- **È ancora usato o citato:** nessun file del repository lo cita.
- **Disposizione proposta:** conservarlo come evidenza di ciò che è stato verificato.
  Non spostarlo (nessun riferimento da aggiornare, ma nemmeno un guadagno di
  chiarezza che giustifichi lo spostamento); il presente registro è il posto in cui se
  ne dichiara la natura.
- **Cosa chiuderebbe la revisione:** nulla. Lo stato `storico` è quello definitivo per
  una fonte esterna già verificata.

### R-007 — `reports/transfer_ceiling/`

- **Perché è segnalato:** il nome della cartella dice "soffitto di trasferimento", cioè
  esattamente la conclusione che i numeri **non** dimostrano. I valori salvati sono
  correlazioni fra effetti stimati, e i più alti (0,13–0,16 mediana Pearson) sono
  confronti **della stessa linea** K562 essential contro K562 genome-wide, non fra
  linee diverse.
- **Affermazioni contestate:** che quei numeri misurino un limite superiore al
  trasferimento fra contesti. Il confronto fra linee diverse dà una mediana molto più
  bassa, 0,0905 grezza per K562 genome-wide verso RPE1, ma resta positiva e
  discrimina le coppie appaiate da quelle non appaiate: non basta a dichiarare K562
  inutile, che è la conclusione opposta e altrettanto non dimostrata.
- **Evidenza contraria:** `reports/transfer_ceiling/transfer_ceiling.json`, campi
  `similarity.raw.matched.pearson.median` per ciascun confronto (ricontrollati il
  2026-09-12); `docs/candidate_adversarial_review_2026-09-12.md` §3.
- **Cosa resta valido:** i numeri, la stratificazione per numerosità e per intensità
  d'effetto, e il confronto con il nullo esaustivo delle coppie non appaiate. È
  evidenza buona sotto un nome fuorviante.
- **È ancora usato o citato:** sì, da `scripts/18_cells_per_pert_replogle.py` e
  `scripts/19_power_curve_vcc_ntc.py`, che vi scrivono dentro. **Non rinominare la
  cartella** senza aggiornare quei due script.
- **Disposizione proposta:** tenere nome e file, e citare quei numeri sempre come
  "correlazione fra effetti stimati", mai come "soffitto". Il rinominamento non vale
  il rischio di rompere due script per una questione di etichetta.
- **Cosa chiuderebbe la revisione:** un ricalcolo con NTC verificati, spazio di output
  appaiato, replicazione per guida e le regole di esclusione dello scorer, che è
  quanto chiede la revisione avversariale.

### R-008 — `reports/grok_verification/`

- **Scheda chiusa lo stesso giorno in cui è stata aperta.** Si conserva perché mostra il
  meccanismo al lavoro, non perché il materiale sia ancora in dubbio.
- **Perché è segnalato:** alle 15:24 del 12 settembre la cartella è comparsa
  insieme a `scripts/27_verify_grok_leads.py`, dopo CP-0001, e nessun documento del
  repository la citava o spiegava a quale domanda rispondesse. Il controllo di copertura
  ricorsivo l'ha intercettata subito. Alle 15:32, mentre questa scheda veniva scritta, è
  arrivato `docs/revisione_grok_2026-09-12.md`, che spiega tutte le sonde: la cartella è
  tornata `attuale`. Restava scoperto un intervallo di otto minuti, che è esattamente
  quanto deve durare.
- **Affermazioni contestate:** nessuna. Questi file non affermano niente: sono risposte
  di endpoint pubblici. Il loro contenuto non è stato valutato in questa revisione, e le
  conclusioni che `docs/revisione_grok_2026-09-12.md` ne trae non sono state
  controllate qui.
- **Evidenza contraria:** non applicabile. Il suo `manifest.json` registra otto
  richieste, tutte con esito 200, verso GSE247601, GSE208240, i record Zenodo 14217682
  e 13350497, e gli studi E-MTAB-14567 ed E-MTAB-13324.
- **Cosa resta valido:** tutto, come istantanea datata. Lo script riusa la meccanica di
  `scripts/20_verify_candidate_accessions.py` con una destinazione distinta, che è il
  modo corretto di aggiungere sonde senza sovrascrivere le precedenti.
- **È ancora usato o citato:** no. Solo `scripts/27_verify_grok_leads.py` vi scrive
  dentro; nessun documento lo legge.
- **Disposizione proposta:** conservare, stato `attuale`. Il contesto che mancava ora
  esiste.
- **Cosa chiuderebbe la revisione:** è chiusa. Resta aperta una cosa diversa, che non
  riguarda questi file: l'inventario Grok di partenza non è conservato nel repository,
  a differenza del PDF in `reports/candidate_pdf_extracted.txt`, quindi le affermazioni
  che il documento corregge non sono più leggibili nella loro forma originale.

### R-009 — `docs/checkpoints/0001-ricostruzione-stato-2026-09-12.md`

- **Perché è segnalato:** tre sue affermazioni sono state corrette il giorno stesso da
  [CP-0002](checkpoints/0002-correzioni-dopo-revisione-umana.md). Il file **non è stato
  modificato** e non lo sarà: è una fotografia datata. Questa scheda e la colonna
  "Corretto da" dell'indice esistono perché chi lo legge sappia dove sta la correzione.
- **Affermazioni contestate:** §3, il pannello descritto come «non essenziale» sulla
  base dell'assenza da due pannelli *essential*; §4, «gli effetti sono piccoli per
  costruzione»; §5, l'esempio secondo cui sottostimare l'ampiezza «fa perdere poco».
  L'elenco con le correzioni è in CP-0002 §7.
- **Evidenza contraria:** `docs/data_strategy_2026-09-11.md` §1, che conteneva già la
  cautela sull'essenzialità; l'assenza in questo repository di qualunque misura di
  essenzialità o di ampiezza d'effetto nei contesti A, B e C;
  `reports/candidate_verification/scorer_clamp_check.json` per il terzo punto.
- **Cosa resta valido:** tutto il resto, che è la maggior parte: le coperture misurate,
  l'identità di lignaggio dei contesti, i clamp dello scorer, l'assenza dell'RNA di H1,
  i vincoli hardware, e la tabella §7 delle correzioni fra i tre documenti di strategia.
- **È ancora usato o citato:** sì, da `docs/PROGETTO.md`, da `CLAUDE.md` e da questo
  registro: è il secondo documento del percorso di lettura.
- **Disposizione proposta:** lasciarlo intatto. Nessuna riscrittura, nessuno
  spostamento: è il primo caso in cui questo sistema fa quello per cui è stato scritto,
  e vale più da leggere che da correggere.
- **Cosa chiuderebbe la revisione:** niente. Un checkpoint corretto resta
  `da-verificare` per sempre: è il modo in cui si dice a chi legge che la fotografia
  contiene qualcosa che poi si è rivelato sbagliato.

### R-010 — `reports/pipeline/`

- **Perché è segnalato:** contiene i primi risultati di modellazione del progetto, ed
  è quindi il primo materiale che si presta a essere citato fuori contesto. La scheda
  esiste per tenere le cautele attaccate ai numeri invece che in un documento a parte.
  Copre anche `transfer_experiment_e001_superseded.json`, marcato `superato`.
- **Affermazioni contestate:** che questi numeri dicano "il trasferimento da K562
  funziona", e che `null_calibration_A.json` sia un benchmark predittivo. Nessuna delle
  due segue. Quello che segue è: a piena ampiezza il trasferimento **peggiora** l'MSE
  del 16% rispetto al non prevedere nulla, e all'ampiezza calibrata lo migliora
  dell'1,0%. Le due frasi non sono la stessa frase. E il nullo ha effetto vero zero per
  costruzione: un modello che lo "battesse" indicherebbe una fuga di informazione.
- **Evidenza contraria:** `reports/pipeline/transfer_experiment.json`, campi
  `cv_mean.untuned_mse_vs_null` (1,162) e `cv_mean.tuned_mse_vs_null` (0,990) per la
  coppia K562 genome-wide → RPE1; `reports/pipeline/null_calibration_A.json`, campo
  `design.true_effect` e il rifiuto di aggregazione registrato in `aggregate_error`.
- **Cosa resta valido:** tutti i numeri, con il loro protocollo. Sono ricalcolabili con
  i comandi di [CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §2,
  la selezione degli iperparametri è su bersagli tenuti fuori e il bootstrap è sui
  bersagli. `transfer_experiment_e001_superseded.json` ha numeri di trasferimento
  identici alla versione corrente: differisce solo per un campo di riepilogo a `null`,
  causato da una chiave sbagliata nella funzione di aggregazione. È conservato perché
  una riesecuzione non sovrascrive un'evidenza.
- **È ancora usato o citato:** sì, da `docs/PROGETTO.md` §3, da D-006, D-012 e D-014, e
  da `configs/sources.yaml` (`signature_qc.json` è evidenza della riga `k562_gwps`).
- **Disposizione proposta:** tenere tutto. Citare sempre questi numeri come metriche
  proxy in spazio pseudobulk log2FC, mai come punteggi VCC, e citare l'alpha di 0,25
  come proprietà della coppia K562 → RPE1, non come costante del progetto.
- **Cosa chiuderebbe la revisione:** un bundle di valutazione a singola cellula (R-1
  della [roadmap](ROADMAP.md)). Con quello le sei metriche VCC si calcolano su effetti
  veri, le metriche proxy scendono al rango di diagnostiche di supporto, e l'ampiezza
  si ricalibra su ciò che assegna davvero i punti.

### R-011 — `reports/trial_2026-09-12/`

- **Perché è segnalato:** contiene i primi artefatti a forma di sottomissione del
  progetto — due previsioni complete per A/B/C e la loro convalida — ed è quindi il
  materiale che più facilmente verrebbe letto come "abbiamo partecipato". Non è così:
  nulla è stato caricato, nessuna quota è stata consumata, e non esiste alcun
  punteggio di leaderboard. La scheda esiste per tenere questa cautela attaccata ai
  file. Copre anche `calibration_c001_peak_memory_unrecorded.json`, marcato `superato`.
- **Affermazioni contestate:** che una convalida di formato superata dica qualcosa
  sulla qualità predittiva; che `trial-00-controls` sia "il baseline a punteggio zero"
  della gara; che l'α di 0,197 misurato su K562 → RPE1 valga per A, B o C; e che le
  metriche proxy pseudobulk si convertano in un punteggio VCC. Nessuna delle quattro
  segue.
- **Evidenza contraria:** `held_out_comparison.md` §3, che separa misura,
  interpretazione e ipotesi riga per riga; `q00prep_prep_dry_run.log` e
  `q01prep_prep_dry_run.log`, che registrano il fallimento della convalida ufficiale
  per esaurimento di memoria; `configs/trials.yaml` campo `not_this` di
  `trial-00-controls`; e il campo `uploaded: false` di ogni `validation.json`.
  `resources.json` copre i quattro run di generazione (due pilot e due completi); i due
  tentativi di packaging hanno i propri `q00prep_validation.json` e
  `q01prep_validation.json`.
- **Cosa resta valido:** tutte le misure, con il loro protocollo. La calibrazione è
  annidata e il bootstrap ricampiona solo previsioni fuori campione; la verifica del
  contratto è ricavata dal file scritto, non dal writer che l'ha prodotto; la
  provenienza dei contesti è verificata contro i profili basali, che è la cosa che
  `vcc prep` non può fare.
- **È ancora usato o citato:** sì, da `docs/PROGETTO.md` §3, da `docs/SOTTOMISSIONE.md`,
  da D-015, D-016 e D-017, e dall'aggiornamento 2026-09-12 di D-006 e D-012.
- **Disposizione proposta:** tenere tutto. Citare l'α di 0,197 come proprietà della
  coppia K562 → RPE1, mai come costante del progetto; citare la riduzione dell'1,01% di
  MSE come metrica proxy pseudobulk, mai come punteggio; e non descrivere i pacchetti
  come "validati dalla CLI ufficiale" finché `vcc prep` non è stato eseguito su di essi
  con esito positivo.
- **Cosa chiuderebbe la revisione:** un'esecuzione di `vcc prep` completata su una
  macchina con RAM sufficiente, il cui log entri qui accanto; e, per la parte
  predittiva, il bundle di valutazione a singola cellula di R-1 della
  [roadmap](ROADMAP.md).

### R-012 — `reports/trial_2026-09-13/`

- **Perché è segnalato:** documenta un `.vcc` valido, ed è il materiale che più
  facilmente verrebbe letto come "siamo pronti a vincere" o, peggio, come "il server
  ha accettato". Nessuna delle due cose. La scheda esiste per tenere attaccata ai
  file la distinzione fra tre affermazioni diverse: convalida di formato, parità con
  lo strumento ufficiale, accettazione del server.
- **Affermazioni contestate:** che un `.vcc` valido dica qualcosa sulla qualità
  predittiva; che la parità con `vcc prep` implichi l'accettazione da parte del
  servizio di scoring; che i test di parità coprano anche la densità; e che il
  picco di 0,52 GiB sia garantito su qualunque previsione.
- **Evidenza contraria:** `k01pack_packaging.json`, campi `uploaded: false` e `note`;
  [CP-0005](checkpoints/0005-packaging-streaming-trial01.md) §4, che elenca il
  confine della parità e dichiara che i fixture sono a densità sintetica.
- **Cosa resta valido:** tutte le misure. L'archivio è verificato con il validatore
  ufficiale del contenitore, e il suo payload è stato confrontato **con l'input**
  array per array: `X/data`, `X/indices` e `X/indptr` identici bit a bit, asse genico
  e etichette identici, con la sola trasformazione dell'indice di `obs` documentata e
  verificata positivamente.
- **È ancora usato o citato:** sì, da `docs/PROGETTO.md`, `docs/SOTTOMISSIONE.md`,
  `docs/ESECUZIONE_REMOTA.md`, e da D-018 e D-019.
- **Disposizione proposta:** tenere tutto. Non descrivere mai il `.vcc` come
  "accettato" finché una sottomissione non è stata valutata; citare il picco di
  0,52 GiB come misurato su questa previsione, non come proprietà generale.
- **Chiusa il 2026-09-13, per la parte sull'accettazione del server.** La
  sottomissione `PNn227rxP3bVByS37W41` è arrivata a `published` con
  `md5_verified: true` ed `error_info: null`: il servizio di scoring ha letto e
  valutato il `.vcc` prodotto da questo percorso
  ([CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) §3.1). Restano
  contestate le altre affermazioni della scheda: un `.vcc` valido continua a non dire
  nulla sulla qualità predittiva — misurata ora, e bassa: 0,046 — e i fixture di
  parità continuano a non esercitare la densità.
- **Cosa chiuderebbe la revisione:** per l'accettazione del server, è già chiusa (vedi
  sopra). Per il resto, niente che riguardi il packaging: la qualità predittiva si
  affronta con R-1 e R-3 della [roadmap](ROADMAP.md), non con questo materiale, e la
  densità dei fixture si chiuderebbe solo con un fixture a densità reale, che costerebbe
  minuti invece di secondi per ogni test.

### R-013 — Dimensione del file K562 a singola cellula: GiB contro GB

- **Perché è segnalato:** il 16 settembre il proprietario ha riferito le dimensioni
  delle copie su Google Drive. Confrontandole con il catalogo è emerso un errore di
  unità ripetuto in più materiali
  ([CP-0018](checkpoints/0018-drive-storage-confermato.md) §3.2–3.3). Lo stesso giorno
  è cambiato il punto di partenza del notebook remoto: i due file che la selezione
  automatica scaricherebbe per primi sono già su Drive.
- **Affermazioni contestate:**
  1. «65,8 GiB» per `K562_gwps_raw_singlecell_01.h5ad`. I 65.830.941.948 byte sono
     65,83 GB, cioè 61,31 GiB. L'etichetta compare in
     `reports/remote_2026-09-15/COME_APRIRE.md` (tre volte), nel markdown e nei
     messaggi di `notebooks/remote_ingest_hepg2.ipynb`, nelle docstring di
     `src/vcc2026/remote_ingest.py`, `src/vcc2026/remote_catalog.py` e
     `scripts/68_remote_catalog.py`, e in un commento di
     `tests/test_remote_catalog.py`. Compariva anche in
     `docs/PIANO_COMPRENSIONE_2026-09-16.md` §3, in
     `docs/PIANO_IMPLEMENTATIVO_2026-09-16.md` (I-5) e nella riga degli script 61–68 di
     questo registro: corretti il 16 settembre, con un rimando a questa scheda.
  2. «Il 61,3 GB del profilo non è la dimensione di questo file». È la stessa
     dimensione espressa in GiB, come il 9,9 e l'8,1 degli altri due file Replogle a
     singola cellula. L'affermazione compare in `configs/remote_catalog.yaml`
     (`advertised_bytes: 61300000000` e `advertised_note`, ripetuti in
     `reports/remote_catalog_2026-09-15/catalog_run.json`) e in
     `reports/remote_2026-09-15/COME_APRIRE.md`; compariva nella riga del catalogo di
     questo registro, ora corretta. `reports/source_cards_2026-09-15/` converte le tre
     cifre del profilo in byte decimali (`profile_declared_sc`).
  3. Non un errore, ma una circostanza nuova. `COME_APRIRE.md` e il notebook indicano
     `FETCH_BLOCKS = None` come scelta normale. Con i due file già su Drive nel posto
     atteso, quella scelta passa al blocco successivo e scarica `rpe1_raw_singlecell`;
     con i file altrove, riscarica i due file. Per collegare soltanto servono
     `FETCH_BLOCKS = []` o una `SELECT_BLOCKS` ristretta ai due blocchi.
- **Evidenza contraria:** i byte in `src/vcc2026/external.py` e
  `configs/remote_catalog.yaml` divisi per 1.073.741.824 danno 61,31, 9,93 e 8,10 GiB.
  Le dimensioni che Drive mostra per le due copie, 61,31 GB e 811,2 MB, sono una
  dichiarazione del proprietario. Per il punto 3: `recommend_fetch_ids` e `run_catalog`
  in `src/vcc2026/remote_catalog.py`, letti e non eseguiti.
- **Cosa resta valido:** tutto ciò che guida il codice. Byte, md5, URL e `relpath` del
  catalogo sono giusti, e la selezione lavora in byte, non in etichette. La parità
  HepG2, la prova di ripresa e il piano locale restano misure valide. L'ordine dei
  blocchi e la regola «un solo file grande alla volta» non cambiano.
- **È ancora usato o citato:** sì. Il notebook e `COME_APRIRE.md` sono le istruzioni per
  il prossimo run remoto (incarico I-6 del
  [workflow 1](PIANO_IMPLEMENTATIVO_2026-09-16.md)); il catalogo è letto da
  `scripts/68_remote_catalog.py` e dal notebook.
- **Disposizione proposta:** non riscrivere i report: `COME_APRIRE.md` si legge con
  questa scheda accanto. Correggere etichette e `advertised_bytes` nel codice e nel
  catalogo con un intervento a parte, insieme alla modalità «solo collegamento»
  proposta in CP-0018 §6.
- **Cosa chiuderebbe la revisione:** per i punti 1 e 2, la correzione di catalogo,
  notebook e docstring. Per il punto 3, un run remoto che colleghi le due copie senza
  scaricare nulla e ne verifichi l'md5, con il suo `catalog_run.json` conservato.

### R-014 — CP-0018: md5 e provenienza delle copie su Drive

- **Perché è segnalato:** il 17 settembre, con Drive per desktop montato, la cartella
  `MyDrive/vcc2026` conteneva accanto ai due file i sidecar `.fetch.json` scritti dal run
  Colab `catalog_2026-09-15T145842Z`
  ([CP-0020](checkpoints/0020-singola-cellula-cis-generatore.md) §3.1).
- **Affermazioni contestate:**
  1. Le copie sono una dichiarazione del proprietario, con md5 non calcolato
     (CP-0018 §3.1 e §4, e l'incertezza 20 di `docs/PROGETTO.md`). In realtà l'md5 è stato
     calcolato al download e coincide con il catalogo, per entrambi i file.
  2. Il percorso delle copie non è noto. In realtà sono nei percorsi che il catalogo si
     aspetta (`data/raw/replogle/` e `data/raw/nadig_hepg2/`).
- **Evidenza contraria:** `reports/drive_evidence_2026-09-17/` (sidecar, `catalog_run.json`
  del run, elenco dei file con i byte).
- **Cosa resta valido:** le dimensioni e la lettura in unità binarie (CP-0018 §3.2–3.3),
  la descrizione del codice del catalogo (§3.4–3.6), e il fatto che nessun run abbia
  letto il contenuto del K562: il QC di quel run è fallito per un errore di codice prima
  di aprirlo. Resta non misurato anche il tempo di lettura attraverso il mount.
- **È ancora usato o citato:** sì, da `docs/PROGETTO.md` e dai piani del 16 settembre.
- **Disposizione proposta:** CP-0018 resta com'è e si legge con questa scheda accanto.
  Nella mappa l'incertezza 20 si chiude per integrità e percorso, e resta aperta per i
  tempi di lettura.
- **Cosa chiuderebbe la revisione:** il primo run dello script 71 su Colab, il cui
  `report.json` ricalcola l'md5 sui byte letti e misura la velocità di lettura.

## Revisione periodica e pulizia

**Nessuna cancellazione fa parte di questo processo.** Serve a decidere cosa merita
uno stato diverso, non cosa eliminare.

Ogni volta che si scrive un checkpoint, ricontrollare tre cose sole:

1. Le righe `da-verificare` sono ancora tali? Una delle loro schede può essere chiusa
   con il lavoro appena fatto?
2. Il materiale nuovo prodotto va aggiunto al registro?
3. Qualche riga `attuale` è stata smentita da ciò che è appena stato misurato?

Candidati alla pulizia, da proporre a chi possiede il progetto e da eseguire solo con
il suo consenso esplicito:

| Candidato | Perché | Condizione per agire |
|---|---|---|
| `.runtime-deps/` | Dipendenza di runtime installata per la sola sonda Orion; ignorata da git e reinstallabile | Quando le sonde Orion non servono più |
| `C:/Users/ferra/vcc2026-data/predictions/smoke.h5ad` (43 MB) | Prova di formato del writer, già superata dal fatto che `vcc prep` ha validato — **quest'ultima giustificazione non è sostenuta da nessun artefatto**: non esiste un log di `vcc prep` prima del 2026-09-12, e misurato il 2026-09-12 `vcc prep` **rifiuta** un file con meno delle 300 perturbazioni ufficiali (`reports/trial_2026-09-12/`, log del pilot), quindi non può aver validato un file da 3 perturbazioni senza `--no-verify-targets`. Vedi [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §7. Il file resta un candidato alla pulizia per il motivo originale — è una prova di formato — non per quello smentito | Quando serve spazio su disco. Misurato il 2026-09-12: circa 26 GB liberi, non 28 |
| Sonde remote in `reports/candidate_verification/*.json` | Alcune sono grandi e sono fotografie datate di endpoint pubblici | Mai cancellare quelle citate nei documenti: sono l'unica prova di cosa si vedeva a quella data |

Controllo automatico della coerenza del registro:

```bash
python scripts/31_check_docs.py
```


