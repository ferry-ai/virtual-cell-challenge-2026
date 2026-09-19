# Archivio del codice — 2026-09-19

Il codice tolto dal branch non e' perduto: sta in un tag, e questo file dice che cosa c'e'
dentro. **Nessun report, documento, checkpoint o dato e' stato cancellato**, e i checkpoint
continuano a citare per nome gli script archiviati, come devono, perche' sono immutabili.

| | |
|---|---|
| Tag | `archivio/pre-pulizia-2026-09-19` |
| Punta a | `ec980b4`, la punta di `main` il 19 settembre 2026 (*Record the conditioned neural predictor (discarded) and the night of 19 Sept*) |
| Dove sta | solo in locale: il tag **non e' stato inviato** a nessun remoto |
| Perche' | la semplificazione del 19 settembre sul branch `refactor/pulizia` |
| Quando | questo elenco e' scritto per intero in un commit solo; le rimozioni vere arrivano nei commit che seguono, uno per sottosistema |

## Come si recupera

```bash
git show archivio/pre-pulizia-2026-09-19:src/orchestrator/engine.py             # a schermo
git show archivio/pre-pulizia-2026-09-19:src/orchestrator/engine.py > engine.py # su disco
git checkout archivio/pre-pulizia-2026-09-19 -- src/orchestrator                # un'intera cartella
git log -1 archivio/pre-pulizia-2026-09-19                                      # che cosa conserva il tag
```

La colonna «Recupero» delle tabelle e' sempre lo stesso schema, `git show archivio/pre-pulizia-2026-09-19:<percorso>`.

## Che cosa non e' stato toccato

- `reports/` e `docs/`: nessun file rimosso, nessun checkpoint modificato;
- `configs/`, `notebooks/`, `.agents/`, `.claude/`: restano interi, anche dove configurano
  codice archiviato (per esempio `configs/ciclo_giornaliero/` e `configs/orchestrator/`);
- i dati fuori dal repository, sotto `C:/Users/ferra/vcc2026-data`, e le copie su Drive.

## Come lo usa il controllo documentale

`scripts/31_check_docs.py` verifica che ogni percorso citato fra backtick nel registro,
nella mappa e nei checkpoint esista sul disco. Un checkpoint non si puo' correggere e
continua a nominare il codice archiviato: il controllo legge quindi **questo file** e
considera valido un percorso elencato qui. Un percorso che sparisce senza comparire in
queste tabelle resta un errore, ed e' esattamente la differenza fra archiviare e perdere.

## Le tabelle

Ogni riga: il percorso come lo citano registro e checkpoint, quante righe aveva, a che
cosa serviva (una frase, condensata dal docstring del file stesso) e il comando che lo
riporta indietro.

### Orchestratore — 27 file, 11.881 righe

Consultazione multi-modello: incarichi, adattatori verso i servizi web, motore, dossier. L'ultima campagna vera e' l'audit Jiang del 15 settembre, fermata `service_unavailable`. Non partecipa alla catena che produce una sottomissione.

| Percorso | Righe | A che cosa serviva | Recupero |
|---|---:|---|---|
| `scripts/orch.cmd` | 14 | Console `orch`: UTF-8 e `src/` sul PYTHONPATH, come py.cmd | `git show archivio/pre-pulizia-2026-09-19:scripts/orch.cmd` |
| `src/orchestrator/__init__.py` | 19 | Pacchetto dell'orchestratore locale per consultare piu' modelli su una domanda | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/__init__.py` |
| `src/orchestrator/adapters/__init__.py` | 61 | Costruzione degli adattatori: un servizio, un canale, scelto solo dalla configurazione | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/adapters/__init__.py` |
| `src/orchestrator/adapters/base.py` | 107 | Interfaccia dell'adattatore e tassonomia degli errori a cui il motore reagisce | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/adapters/base.py` |
| `src/orchestrator/adapters/gemini_cli.py` | 117 | Gemini attraverso la sua CLI ufficiale | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/adapters/gemini_cli.py` |
| `src/orchestrator/adapters/manual.py` | 68 | Adattatore con l'umano nel canale: il prompt si consegna, la risposta si incolla | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/adapters/manual.py` |
| `src/orchestrator/adapters/scripted.py` | 87 | Adattatore offline che legge le risposte da file, per le prove a secco | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/adapters/scripted.py` |
| `src/orchestrator/adapters/web.py` | 902 | Chat web guidate nel browser dell'operatore con Playwright | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/adapters/web.py` |
| `src/orchestrator/briefs.py` | 277 | L'incarico: l'unica cosa che l'operatore consegna al sistema, e il suo versionamento | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/briefs.py` |
| `src/orchestrator/checks.py` | 187 | Controlli di accettazione: l'unica cosa che puo' far diventare verde un criterio | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/checks.py` |
| `src/orchestrator/cli.py` | 853 | La console dell'operatore: nessuna campagna parte se non la digita una persona | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/cli.py` |
| `src/orchestrator/convergence.py` | 382 | Quando continuare, quando fermarsi, e di che tipo di arresto si tratta | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/convergence.py` |
| `src/orchestrator/engine.py` | 1143 | Il ciclo: codice deterministico che decide chi viene interrogato su che cosa, e quando si smette | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/engine.py` |
| `src/orchestrator/protocol.py` | 665 | Che cosa si chiede a un modello e che cosa si e' disposti a rileggere | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/protocol.py` |
| `src/orchestrator/report.py` | 342 | Il rapporto finale: risultato, evidenza, controlli davvero eseguiti, disaccordi, limiti | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/report.py` |
| `src/orchestrator/research/__init__.py` | 30 | Modalita' ricerca scientifica: tre fasi, registrazione strutturata, dossier deterministico | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/research/__init__.py` |
| `src/orchestrator/research/campaign.py` | 301 | La meta' di ricerca di un incarico: perimetro, pertinenza, ipotesi, budget, politica di ricerca | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/research/campaign.py` |
| `src/orchestrator/research/contract.py` | 664 | Che cosa puo' dire una risposta di ricerca e che cosa si e' disposti a scrivere come fatto | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/research/contract.py` |
| `src/orchestrator/research/dossier.py` | 784 | Il dossier comune, montato dal codice, e il rapporto che legge una persona | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/research/dossier.py` |
| `src/orchestrator/research/engine.py` | 528 | Il ciclo di ricerca a tre fasi, dal primo prompt al dossier | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/research/engine.py` |
| `src/orchestrator/research/leads.py` | 221 | Scelta deterministica delle piste che la fase 3 paga | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/research/leads.py` |
| `src/orchestrator/research/prompts.py` | 341 | Le tre domande di una campagna di ricerca e il contratto sotto cui le pone | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/research/prompts.py` |
| `src/orchestrator/settings.py` | 211 | Configurazione dell'orchestratore: servizi, ruoli, percorsi, limiti, guardie | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/settings.py` |
| `src/orchestrator/store.py` | 484 | Stato persistente: indice SQLite, registro eventi in sola aggiunta, file su disco | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/store.py` |
| `src/orchestrator/util.py` | 132 | Aiutanti deterministici: id, hash, orologi, file scritti una volta sola, differenze di testo | `git show archivio/pre-pulizia-2026-09-19:src/orchestrator/util.py` |
| `tests/test_orchestrator.py` | 2015 | 95 test sui modi in cui l'orchestratore potrebbe sbagliare in silenzio | `git show archivio/pre-pulizia-2026-09-19:tests/test_orchestrator.py` |
| `tests/test_orchestrator_research.py` | 946 | 65 test sulle promozioni che la modalita' ricerca non annuncerebbe | `git show archivio/pre-pulizia-2026-09-19:tests/test_orchestrator_research.py` |

### Oracolo — 28 file, 1.831 righe

Prototipo di verificatore numerico pairwise sulla loss, indipendente da tutto il resto: non importa `orchestrator` ne' `vcc2026`. Usato su fixture sintetici in CP-0007, CP-0008 e CP-0009.

| Percorso | Righe | A che cosa serviva | Recupero |
|---|---:|---|---|
| `src/oracle/__init__.py` | 11 | Pacchetto dell'oracolo numerico deterministico | `git show archivio/pre-pulizia-2026-09-19:src/oracle/__init__.py` |
| `src/oracle/__main__.py` | 5 | Punto di ingresso `python -m oracle` | `git show archivio/pre-pulizia-2026-09-19:src/oracle/__main__.py` |
| `src/oracle/cli.py` | 78 | CLI dell'oracolo pairwise sulla loss | `git show archivio/pre-pulizia-2026-09-19:src/oracle/cli.py` |
| `src/oracle/pairwise_loss.py` | 1013 | Verificatore pairwise sulla loss: ricalcola dal CSV in frazioni esatte e confronta con l'affermazione | `git show archivio/pre-pulizia-2026-09-19:src/oracle/pairwise_loss.py` |
| `src/oracle/README.md` | 18 | Che cos'e' l'oracolo e che cosa non e' (non valuta ipotesi biologiche) | `git show archivio/pre-pulizia-2026-09-19:src/oracle/README.md` |
| `tests/test_oracle_pairwise_loss.py` | 591 | Test su fixture sintetici, con i risultati attesi calcolati a mano | `git show archivio/pre-pulizia-2026-09-19:tests/test_oracle_pairwise_loss.py` |
| `src/oracle/fixtures/pairwise_loss/` (22 file) | 115 | Fixture sintetici dell'oracolo: CSV e affermazioni con l'esito atteso calcolato a mano | `git checkout archivio/pre-pulizia-2026-09-19 -- src/oracle/fixtures` |

### Catena di cicli — 3 file, 2.649 righe

La macchina dei cicli piano-revisione-implementazione-controllo. Implementata e provata solo con agenti simulati: **nessun ciclo e' mai girato dal vivo**, e il proprietario ha deciso di non usarla. I suoi testi e schemi (`configs/ciclo_giornaliero/`, `.agents/skills/`) restano dove sono.

| Percorso | Righe | A che cosa serviva | Recupero |
|---|---:|---|---|
| `scripts/32_daily_cycle.py` | 1851 | La catena di cicli: guardiano, coda, dialogo, collaudo, fase di Grok, campagne con tetto | `git show archivio/pre-pulizia-2026-09-19:scripts/32_daily_cycle.py` |
| `scripts/ciclo.cmd` | 18 | Wrapper per l'Utilita' di pianificazione che avvia la catena | `git show archivio/pre-pulizia-2026-09-19:scripts/ciclo.cmd` |
| `tests/test_daily_cycle.py` | 780 | 42 test della catena con agenti simulati in un repository git temporaneo | `git show archivio/pre-pulizia-2026-09-19:tests/test_daily_cycle.py` |

### Benchmark modulare (pseudobulk) — 37 file, 13.219 righe

Il confronto fra architetture in spazio pseudobulk: firme, split, universo genico, quattro decoder, gate di espressione, SVD. Ha prodotto CP-0011, CP-0013, CP-0014, CP-0015 e CP-0017, tutti esiti negativi o inconcludenti per l'adozione. La pipeline attuale lavora a singola cellula e non lo usa.

| Percorso | Righe | A che cosa serviva | Recupero |
|---|---:|---|---|
| `scripts/50_inventory_data.py` | 69 | Inventario leggibile dalla macchina dei dati davvero presenti su disco | `git show archivio/pre-pulizia-2026-09-19:scripts/50_inventory_data.py` |
| `scripts/51_run_modular_pilot.py` | 88 | Esegue il pilot modulare contro monolitico sulle firme pseudobulk locali | `git show archivio/pre-pulizia-2026-09-19:scripts/51_run_modular_pilot.py` |
| `scripts/52_audit_hepg2.py` | 465 | Audit di un oggetto a singola cellula appena acquisito, prima che qualcuno lo usi | `git show archivio/pre-pulizia-2026-09-19:scripts/52_audit_hepg2.py` |
| `scripts/53_build_hepg2_signatures.py` | 347 | Costruisce le firme HepG2 dalle cellule, sullo stesso asse e con controlli appaiati per batch | `git show archivio/pre-pulizia-2026-09-19:scripts/53_build_hepg2_signatures.py` |
| `scripts/54_context_target_table.py` | 193 | Censimento contesto x bersaglio su tutte le firme presenti | `git show archivio/pre-pulizia-2026-09-19:scripts/54_context_target_table.py` |
| `scripts/55_control_profile.py` | 124 | Profilo basale NTC di una sorgente a singola cellula, salvato per il benchmark | `git show archivio/pre-pulizia-2026-09-19:scripts/55_control_profile.py` |
| `scripts/56_probe_target_descriptors.py` | 769 | Sonda le sorgenti di descrittori di bersaglio per il modo B (gene mai perturbato) | `git show archivio/pre-pulizia-2026-09-19:scripts/56_probe_target_descriptors.py` |
| `scripts/57_generator_x_predictor.py` | 368 | Generatore per predittore su cellule HepG2 reali, con le sei metriche VCC | `git show archivio/pre-pulizia-2026-09-19:scripts/57_generator_x_predictor.py` |
| `scripts/58_build_go_slim_table.py` | 303 | Congela la tabella simbolo -> 140 bit GO slim con gli sha256 delle fonti | `git show archivio/pre-pulizia-2026-09-19:scripts/58_build_go_slim_table.py` |
| `scripts/59_gpu_readiness.py` | 320 | Audit misurato: una GPU renderebbe piu' veloce questo codice? | `git show archivio/pre-pulizia-2026-09-19:scripts/59_gpu_readiness.py` |
| `scripts/60_compare_factorization.py` | 556 | SVD troncata esatta contro randomizzata sulle matrici che il benchmark usa davvero | `git show archivio/pre-pulizia-2026-09-19:scripts/60_compare_factorization.py` |
| `scripts/65_eval_protocol_pilot.py` | 163 | Verifica del protocollo di valutazione congelato su split esistenti e cellule HepG2 | `git show archivio/pre-pulizia-2026-09-19:scripts/65_eval_protocol_pilot.py` |
| `scripts/69_expression_gate_decision.py` | 275 | Applica la regola di decisione scritta prima al run del gate di espressione, e nient'altro | `git show archivio/pre-pulizia-2026-09-19:scripts/69_expression_gate_decision.py` |
| `scripts/70_context_presence_audit.py` | 219 | Quanto spazio avrebbe un gate di espressione sui contesti ufficiali A/B/C | `git show archivio/pre-pulizia-2026-09-19:scripts/70_context_presence_audit.py` |
| `src/vcc2026/benchmark/__init__.py` | 26 | Protocollo comune per confrontare trasferimento, lineare, MLP e modulare | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/benchmark/__init__.py` |
| `src/vcc2026/benchmark/descriptors.py` | 532 | Descrittori di contesto e bersaglio con la provenienza registrata | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/benchmark/descriptors.py` |
| `src/vcc2026/benchmark/evaluate.py` | 341 | Valutazione proxy, differenze appaiate per bersaglio, conto delle risorse | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/benchmark/evaluate.py` |
| `src/vcc2026/benchmark/factorization.py` | 236 | SVD troncata di una matrice di risposta gia' centrata; unico punto di SVD del benchmark | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/benchmark/factorization.py` |
| `src/vcc2026/benchmark/gate.py` | 698 | I bracci del gate di espressione, con i due controlli obbligatori | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/benchmark/gate.py` |
| `src/vcc2026/benchmark/generator_spec.py` | 157 | Specifica del bundle a singola cellula mancante per generatore x predittore | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/benchmark/generator_spec.py` |
| `src/vcc2026/benchmark/inventory.py` | 404 | Inventario leggibile dalla macchina di cio' che sta su disco | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/benchmark/inventory.py` |
| `src/vcc2026/benchmark/models.py` | 760 | I predittori confrontati: ShrunkTransfer, low-rank mascherato, MLP compatto, modulare | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/benchmark/models.py` |
| `src/vcc2026/benchmark/protocol.py` | 256 | Interfacce uniformi: descrittori, split, fit/predict/save, niente fughe di informazione | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/benchmark/protocol.py` |
| `src/vcc2026/benchmark/run.py` | 1256 | Esecutore del pilot modulare sulle firme pseudobulk locali | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/benchmark/run.py` |
| `src/vcc2026/benchmark/universe.py` | 118 | Universo genico davvero misurato in tutte le sorgenti confrontate | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/benchmark/universe.py` |
| `src/vcc2026/eval_protocol.py` | 411 | Protocollo di valutazione congelato: fughe, ancore locali, promozione | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/eval_protocol.py` |
| `src/vcc2026/models.py` | 283 | Baseline di trasferimento che prevedono la risposta di un bersaglio mai visto | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/models.py` |
| `src/vcc2026/presence.py` | 208 | Presenza per gene nei controlli di un contesto, e il peso graduale che ne deriva | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/presence.py` |
| `src/vcc2026/pseudobulk.py` | 287 | Legge gli h5ad pseudobulk stile Replogle come firme sull'asse ufficiale | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/pseudobulk.py` |
| `src/vcc2026/registry.py` | 250 | Registry delle sorgenti: che cos'e' ogni dataset e fin dove e' stato verificato | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/registry.py` |
| `src/vcc2026/signatures.py` | 373 | Firme di risposta a una perturbazione, con incertezza e numerosita' | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/signatures.py` |
| `src/vcc2026/splits.py` | 156 | Split che rispondono separatamente alle tre domande di generalizzazione | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/splits.py` |
| `tests/test_eval_protocol.py` | 162 | Contratti del protocollo congelato: fughe, ancore, promozione | `git show archivio/pre-pulizia-2026-09-19:tests/test_eval_protocol.py` |
| `tests/test_expression_gate.py` | 677 | 53 test sui modi in cui il gate di espressione potrebbe sbagliare in silenzio | `git show archivio/pre-pulizia-2026-09-19:tests/test_expression_gate.py` |
| `tests/test_factorization.py` | 256 | Contratto della fattorizzazione: esatta contro randomizzata, centratura, bootstrap | `git show archivio/pre-pulizia-2026-09-19:tests/test_factorization.py` |
| `tests/test_modular_benchmark.py` | 690 | Contratti del pilot modulare: maschere, fughe, salvataggio, identita' delle predizioni | `git show archivio/pre-pulizia-2026-09-19:tests/test_modular_benchmark.py` |
| `tests/test_pipeline_contracts.py` | 423 | 42 test sui contratti che fallirebbero in silenzio | `git show archivio/pre-pulizia-2026-09-19:tests/test_pipeline_contracts.py` |

### Ingestione remota — 18 file, 4.137 righe

Catalogo, fetch riprendibile e schede sorgente per portare i grezzi pesanti su un runtime remoto. Superato dal fatto che i due file pesanti stanno gia' su Drive e i job Colab li collegano (CP-0018, CP-0020).

| Percorso | Righe | A che cosa serviva | Recupero |
|---|---:|---|---|
| `scripts/61_probe_jiang.py` | 338 | Sonda su Jiang/Mixscale dai record pubblici, senza scaricare l'oggetto Seurat | `git show archivio/pre-pulizia-2026-09-19:scripts/61_probe_jiang.py` |
| `scripts/62_reconcile_nadig.py` | 249 | Riconcilia HepG2 GEO contro il mirror scPerturb e Jurkat, senza nuovi download | `git show archivio/pre-pulizia-2026-09-19:scripts/62_reconcile_nadig.py` |
| `scripts/63_runtime_preflight.py` | 139 | Misura questa macchina e scrive gli ingressi del contratto per il job remoto | `git show archivio/pre-pulizia-2026-09-19:scripts/63_runtime_preflight.py` |
| `scripts/64_source_cards.py` | 405 | Schede sorgente per Replogle SC, H1, CD4, Srivatsan, McFaline, Tahoe, scBaseCount | `git show archivio/pre-pulizia-2026-09-19:scripts/64_source_cards.py` |
| `scripts/66_primeflow_feasibility.py` | 191 | Fattibilita' di PRiMeFlow dal testo dell'articolo; non e' un'esecuzione del modello | `git show archivio/pre-pulizia-2026-09-19:scripts/66_primeflow_feasibility.py` |
| `scripts/67_remote_ingest.py` | 59 | Esegue il contratto di ingestione remota, o prepara il bundle da caricare | `git show archivio/pre-pulizia-2026-09-19:scripts/67_remote_ingest.py` |
| `scripts/68_remote_catalog.py` | 76 | Pianifica o esegue il catalogo remoto multi-sorgente; non addestra | `git show archivio/pre-pulizia-2026-09-19:scripts/68_remote_catalog.py` |
| `src/vcc2026/external.py` | 198 | Registry e scaricatore dei dataset pubblici di perturbazione | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/external.py` |
| `src/vcc2026/remote_catalog.py` | 759 | Ingestione remota multi-sorgente: un catalogo, checkpoint indipendenti, un blocco per volta | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/remote_catalog.py` |
| `src/vcc2026/remote_ingest.py` | 446 | Primo job remoto: parita' HepG2, prova di ripresa, poi il blocco Jiang con cancello | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/remote_ingest.py` |
| `src/vcc2026/remote_job.py` | 330 | Primitive riprendibili: un blocco, checksum, ripresa dopo interruzione | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/remote_job.py` |
| `src/vcc2026/remote_ranges.py` | 85 | Accesso HTTP a intervalli con budget di byte, per ispezionare file pubblici | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/remote_ranges.py` |
| `src/vcc2026/runtime.py` | 202 | Inventario del runtime per i job locali e remoti | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/runtime.py` |
| `src/vcc2026/source_card.py` | 165 | Scheda obbligatoria per sorgente: i campi mancanti restano mancanti | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/source_card.py` |
| `tests/test_remote_catalog.py` | 252 | Contratti del catalogo: byte misurati, nessun 61,3 GB silenzioso, cancello sul disco | `git show archivio/pre-pulizia-2026-09-19:tests/test_remote_catalog.py` |
| `tests/test_remote_ingest.py` | 63 | Contratto dell'ingestione: regole sui percorsi, cancello del disco, niente percorsi Windows | `git show archivio/pre-pulizia-2026-09-19:tests/test_remote_ingest.py` |
| `tests/test_remote_job.py` | 143 | Fetch riprendibile ed export: un'interruzione non deve duplicare ne' ricominciare | `git show archivio/pre-pulizia-2026-09-19:tests/test_remote_job.py` |
| `tests/test_remote_ranges.py` | 37 | Test del lettore HTTP a intervalli con budget di byte | `git show archivio/pre-pulizia-2026-09-19:tests/test_remote_ranges.py` |

### Pipeline trial-01 (pseudobulk) — 9 file, 2.916 righe

Gli stadi che hanno prodotto trial-01, la prima sottomissione valutata (0,045929). La generazione attuale passa dallo stadio 76 a singola cellula; restano tenuti il 46 e il 48, che convalidano e impacchettano.

| Percorso | Righe | A che cosa serviva | Recupero |
|---|---:|---|---|
| `scripts/40_build_signatures.py` | 248 | Stadio 1: registry -> selezione -> ingestione -> QC -> firme | `git show archivio/pre-pulizia-2026-09-19:scripts/40_build_signatures.py` |
| `scripts/41_transfer_experiment.py` | 337 | Stadio 2: misura quanto si trasferisce una risposta e calibra l'ampiezza | `git show archivio/pre-pulizia-2026-09-19:scripts/41_transfer_experiment.py` |
| `scripts/42_null_calibration.py` | 233 | Stadio 3: esegue lo scorer vero su un bundle in cui la verita' e' nota | `git show archivio/pre-pulizia-2026-09-19:scripts/42_null_calibration.py` |
| `scripts/43_freeze_trial.py` | 215 | Congela un trial: lo stato esatto da cui il run e' partito | `git show archivio/pre-pulizia-2026-09-19:scripts/43_freeze_trial.py` |
| `scripts/44_calibrate_transfer.py` | 570 | Stadio 4: calibra ShrunkTransfer con validazione incrociata annidata | `git show archivio/pre-pulizia-2026-09-19:scripts/44_calibrate_transfer.py` |
| `scripts/45_generate_prediction.py` | 504 | Stadio 5: genera una previsione a forma di sottomissione per i contesti ufficiali | `git show archivio/pre-pulizia-2026-09-19:scripts/45_generate_prediction.py` |
| `scripts/47_resource_report.py` | 213 | Stadio 7: consolida in una tabella il costo misurato di un insieme di run | `git show archivio/pre-pulizia-2026-09-19:scripts/47_resource_report.py` |
| `src/vcc2026/trials.py` | 49 | Definizione dei trial, letta da `configs/trials.yaml` | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/trials.py` |
| `tests/test_trial_inference.py` | 547 | 42 test della pipeline di trial: fughe, identita' dei contesti, generazione dei conteggi | `git show archivio/pre-pulizia-2026-09-19:tests/test_trial_inference.py` |

### Sonde e audit delle sorgenti — 22 file, 2.775 righe

Le sonde datate su endpoint pubblici e gli audit dei dati locali di settembre. I loro **report restano** in `reports/`: qui se ne va solo il codice che li ha prodotti.

| Percorso | Righe | A che cosa serviva | Recupero |
|---|---:|---|---|
| `scripts/01_inspect_controls.py` | 125 | Ispeziona il bundle di controlli scaricato e riporta che aspetto hanno i dati | `git show archivio/pre-pulizia-2026-09-19:scripts/01_inspect_controls.py` |
| `scripts/02_smoke_test_submission.py` | 110 | Prova di andata e ritorno del writer di sottomissione su poche perturbazioni | `git show archivio/pre-pulizia-2026-09-19:scripts/02_smoke_test_submission.py` |
| `scripts/10_fetch_external.py` | 50 | Scarica i dataset pubblici di perturbazione in data_root/external | `git show archivio/pre-pulizia-2026-09-19:scripts/10_fetch_external.py` |
| `scripts/11_check_target_coverage.py` | 153 | Quanto del pannello ufficiale copre davvero il dato Replogle | `git show archivio/pre-pulizia-2026-09-19:scripts/11_check_target_coverage.py` |
| `scripts/12_audit_data_strategy.py` | 118 | Audit in sola lettura degli ingressi locali | `git show archivio/pre-pulizia-2026-09-19:scripts/12_audit_data_strategy.py` |
| `scripts/13_catalog_public_data.py` | 32 | Scarica solo i metadati pubblici di Figshare, mai le matrici | `git show archivio/pre-pulizia-2026-09-19:scripts/13_catalog_public_data.py` |
| `scripts/14_fetch_hipsci_metadata.py` | 35 | Scarica le tre tabelle di metadati HIPSCI (circa 21 MB) | `git show archivio/pre-pulizia-2026-09-19:scripts/14_fetch_hipsci_metadata.py` |
| `scripts/15_audit_hipsci_coverage.py` | 49 | Misura il supporto di bersagli e contesti dai soli metadati HIPSCI | `git show archivio/pre-pulizia-2026-09-19:scripts/15_audit_hipsci_coverage.py` |
| `scripts/16_probe_context_identity.py` | 146 | Identifica che tipi cellulari sono davvero i contesti anonimi A/B/C | `git show archivio/pre-pulizia-2026-09-19:scripts/16_probe_context_identity.py` |
| `scripts/17_extract_scorer_contract.py` | 94 | Estrae il contratto di punteggio dal cell-eval2 installato, non dalla prosa | `git show archivio/pre-pulizia-2026-09-19:scripts/17_extract_scorer_contract.py` |
| `scripts/18_cells_per_pert_replogle.py` | 357 | Cellule per perturbazione nei file Replogle, con confondenti e pavimento di rumore | `git show archivio/pre-pulizia-2026-09-19:scripts/18_cells_per_pert_replogle.py` |
| `scripts/18_check_external_compat.py` | 736 | Pone le stesse domande a ogni dataset esterno candidato, una volta e a basso costo | `git show archivio/pre-pulizia-2026-09-19:scripts/18_check_external_compat.py` |
| `scripts/19_power_curve_vcc_ntc.py` | 273 | Curva di potenza NTC contro NTC sui controlli ufficiali | `git show archivio/pre-pulizia-2026-09-19:scripts/19_power_curve_vcc_ntc.py` |
| `scripts/20_verify_candidate_accessions.py` | 89 | Fotografa i metadati pubblici dei candidati, con tetto di 4 MiB per URL | `git show archivio/pre-pulizia-2026-09-19:scripts/20_verify_candidate_accessions.py` |
| `scripts/21_probe_remote_h5ad.py` | 89 | Ispeziona byte HDF5 remoti veri con un budget, senza scaricare tutto | `git show archivio/pre-pulizia-2026-09-19:scripts/21_probe_remote_h5ad.py` |
| `scripts/22_fetch_candidate_annotations.py` | 36 | Scarica annotazioni pubbliche piccole ed esplicite, non atlanti interi | `git show archivio/pre-pulizia-2026-09-19:scripts/22_fetch_candidate_annotations.py` |
| `scripts/23_probe_orion.py` | 51 | Proiezione di colonne Parquet con budget; nessun download dell'atlante | `git show archivio/pre-pulizia-2026-09-19:scripts/23_probe_orion.py` |
| `scripts/24_scorer_clamp_check.py` | 22 | Verifica i pavimenti del punteggio con ancore sintetiche | `git show archivio/pre-pulizia-2026-09-19:scripts/24_scorer_clamp_check.py` |
| `scripts/25_ingest_cd4_pilot.py` | 108 | Estrae un pilot CD4 stratificato con un tetto rigido di byte HTTP | `git show archivio/pre-pulizia-2026-09-19:scripts/25_ingest_cd4_pilot.py` |
| `scripts/26_candidate_coverage.py` | 33 | Copertura per bersaglio, distinguendo la libreria di guide dalle cellule osservate | `git show archivio/pre-pulizia-2026-09-19:scripts/26_candidate_coverage.py` |
| `scripts/27_verify_grok_leads.py` | 25 | Verifica con budget dei metadati delle piste nuove dell'inventario di Grok | `git show archivio/pre-pulizia-2026-09-19:scripts/27_verify_grok_leads.py` |
| `scripts/28_probe_grok_files.py` | 44 | Ispeziona i file pubblici piccoli e campioni di conteggi per le piste di Grok | `git show archivio/pre-pulizia-2026-09-19:scripts/28_probe_grok_files.py` |

### Funzioni tolte da file tenuti — 3 definizioni, 183 righe

Non sono file interi: sono funzioni rimaste senza chiamanti quando il loro unico
chiamante e' finito nell'archivio. Stesso tag, stesso comando, ma il percorso da cui
ripescarle e' quello del file che le conteneva.

| Funzione | Righe | Dove stava | Perche' non serve piu' | Recupero |
|---|---:|---|---|---|
| `align_to_axis` e `AlignedMatrix` | 115 | `src/vcc2026/genes.py` | Mettevano una matrice sorgente sull'asse ufficiale con la maschera degli osservati: le chiamavano `pseudobulk.py` e gli stadi 40 e 53, tutti archiviati | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/genes.py` |
| `predicted_profile` | 60 | `src/vcc2026/inference.py` | Componeva il profilo previsto per lo stadio 45, archiviato con la pipeline di trial-01 | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/inference.py` |
| `reset_caches` | 8 | `src/vcc2026/config.py` | Svuotava le cache dei percorsi per i test che cambiavano l'ambiente; nessun test tenuto lo fa | `git show archivio/pre-pulizia-2026-09-19:src/vcc2026/config.py` |

**Totale archiviato: 39.408 righe in 144 file.**

