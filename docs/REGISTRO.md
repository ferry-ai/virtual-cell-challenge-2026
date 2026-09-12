# Registro del ciclo di vita di documenti e dati

A che serve: dire, per ogni materiale del progetto, **se ci si può ancora contare**.
Un documento non diventa falso tutto insieme: di solito resta valido in gran parte e
sbaglia in due punti. Qui si segna lo stato del documento e, quando serve, si apre una
scheda che elenca le singole affermazioni in discussione.

Aggiornato il 2026-09-12 (compilazione iniziale, vedi
[CP-0001](checkpoints/0001-ricostruzione-stato-2026-09-12.md)).

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
| `tests/test_pipeline_contracts.py` | attuale | — | 42 test sui contratti che fallirebbero in silenzio: maschere contro zeri, fuga di bersagli negli split, sovrascrittura di manifesti, livelli di verifica del registry | — |

## Dati

Nessun file di dati è stato spostato o copiato per compilare questo registro. I dati
pesanti stanno fuori dal repository, sotto `C:/Users/ferra/vcc2026-data`
(vedi `configs/config.yaml`).

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
- **Evidenza contraria:** `docs/candidate_adversarial_review_2026-09-12.md` §§2–3;
  `reports/candidate_verification/scorer_clamp_check.json`;
  `reports/context_identity/markers.csv`; elenco di
  `C:/Users/ferra/vcc2026-data/external/vcc2025/`.
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
| `C:/Users/ferra/vcc2026-data/predictions/smoke.h5ad` (43 MB) | Prova di formato del writer, già superata dal fatto che `vcc prep` ha validato | Quando serve spazio su disco, di cui restano circa 28 GB |
| Sonde remote in `reports/candidate_verification/*.json` | Alcune sono grandi e sono fotografie datate di endpoint pubblici | Mai cancellare quelle citate nei documenti: sono l'unica prova di cosa si vedeva a quella data |

Controllo automatico della coerenza del registro:

```bash
python scripts/31_check_docs.py
```
