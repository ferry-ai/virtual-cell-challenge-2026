# DATI-TRANSFER — sessione 01a11c34, 8 ottobre 2026

Mandato del proprietario: banca canonica → training → predizione, copertura D-053 e
release immutabili. Questa cartella contiene codice ed evidenze della sessione;
la sede operativa condivisa resta R-LEAD, di competenza di VALIDAZIONE.

**Nuovo t39 T3+ESM2 pronto localmente:**
[consegna esatta per consenso del Lead](t39_t3_ready_for_specific_consent_r1.json).
T3 preservato al bit su 4.467.808 coppie, ESM2 aggiunto solo su 380.820 vuoti;
19.812.145 byte, hash `577a5a56a57df6a2ba07beead6217a7274ad639e85e8be780d942c1c7152094b`.
Pacchetto CPU privato distinto già costruito con upload fittizio; mancano nuova
preregistrazione e consenso esatto. Nessun trasferimento, lancio o entry VCC.
La versione T0 sotto rimane sospesa e non è stata inviata.

**T39 T0+ESM2 sospeso prima di qualsiasi upload/lancio:**
[stato esatto e blocco auto-review](t39_hold_candidate_review_r1.json).
Lead sta verificando una base T38/T3; la precedente domanda di consenso non
riattiva il candidato T0. [Verifica numerica PASS](t39_effect_verified_r1.json)
e [pacchetto locale con upload fittizio](t39/r1/draft_prepared.json) restano
riusabili come preparazione. Nessuna entry VCC creata e nessun calcolo cloud.

**Destinazione produzione aggiornata il 10 ottobre: MX**, su richiesta MODELLI.
[Variante emettitore MX](EMETTITORE_ACCESSI_PRODUZIONE_MX_r1.md): 209 payload,
10.100.920.946 byte, job esatto e consenso specifico obbligatori; otto test locali
superati, nessun accesso emesso. Supera la proposta operativa df11 qui sotto.

**Produzione AMMI:** [consegna input e accessi](CONSEGNA_PRODUZIONE_AMMI_r1.md),
[inventario per hash e account](production_input_handoff_r1.json).
Su df11 il trasferimento privato richiesto è 5,387 GB; su MX 10,101 GB.
30 parti NTC, controlli A/B/C e ancore pronti; consenso pilot non esteso
alla produzione. Nessuna nuova estrazione o duplicazione dei lanci MODELLI.
[Emettitore pronto con blocco sul consenso](EMETTITORE_ACCESSI_PRODUZIONE_r1.md):
135 payload, sei verifiche locali superate, nessun locator emesso.

**NTC completate il 9 ottobre alle 21:48:** [raccolta e verifica](df11_ntc_watch_result_r1.json),
[manifest finale](ntc_ready_manifest_r2.json),
[catalogo riusabile 30/30](ntc_reuse_catalog_r2.json): 47 contesti,
1.329.117 candidati prima del merge globale. Nessuna parte mancante.
Metadata e codice verificati; gli hash numerici restano da verificare nel
consumer. MODELLI-ESTERNI ha acquisito gli accessi autorizzati e mantiene
l'esclusiva del packaging e lancio dei due fit cells. Nessuna nuova estrazione.

**Audit riuso NTC precedente al completamento:** [diagnosi e correzione minima](AUDIT_RIUSO_NTC_r1.md),
[catalogo verificato 18 bundle / 12 parti attive](ntc_reuse_catalog_r1.json).
I 1.739 shard delle 12 parti erano già collegati ai campioni persistenti:
il divario è selezione/normalizzazione/adattatore, non assenza dei dati.
Recupero depth da soli metadata verificato su fixture; nessuna sostituzione
del protocollo corrente e nessun rilancio. MODELLI gestisce la transizione
automatica dopo le sentinelle DATI.

**T38 pubblicato:** 0,14892212354470022, differenza +0,0016727636292174775
contro t36: entro la soglia preregistrata ±0,005, **non conclusivo**.
[Verifica indipendente](t38_published_verified_r1.json) della nuova ricevuta
del 9 ottobre alle 21:28 circa: sei scalati pubblicati, media esatta, stessi
pannello/partizione/ancore del t36; coincide con il
[confronto già registrato da VALIDAZIONE](../../invii/prediction_t38_2026-10-09/comparison.json)
e [CP-0074](../../../docs/checkpoints/0074-t38-crispri-piu-ko-punteggio-ufficiale.md).
Nuovo massimo osservato, nessuna promozione stabile o attribuzione al KO.
NTC df11/r5 resta RUNNING, senza progresso applicativo osservabile:
[snapshot](df11_progress_snapshot_r4.json). Raccolta terminale al watcher DATI;
issuance successiva a MODELLI-ESTERNI, che ha confermato la presa in carico.

**T38 consegnato il 9 ottobre:** [verifica delle ricevute](t38_delivery_verified_r1.json).
Upload completato alle 20:04:41 Europe/Rome, 3.993.702.400 byte e MD5 remoto
uguale al locale. Alle 20:06 il server conferma l'avvio della valutazione,
entry `LJmnhqqh1WTrx1JcoRlr`, stato `launching`, nessun punteggio ancora disponibile:
[ricevuta server](../../invii/trial_2026-10-09/status_LJmnhqqh1WTrx1JcoRlr_after_launch.json).
Archivio SHA256 `5198c78f1a5c804253377bfecd4f72f5e54c049a18aa6672768034c326284bc1`,
360.000 cellule e 18.533 geni; validatore ufficiale e confronto del payload
superati. Recuperate le cellule esistenti, senza nuovo fit o generazione.
Nessuna promozione scientifica o chiusura D-053. I 12 input NTC df11/r5
restano in elaborazione; il loro watcher è distinto e continua.

**Fotografia della ripresa T38:** [consenso umano originale](t38_resume_authorization_r1.json),
[presa in carico e piano](t38_resume_taken_r1.json). Unica entry VCC
`LJmnhqqh1WTrx1JcoRlr`, upload non ancora confermato. Il tentativo CPU privato
[r3](cloud_delivery/r3/prepared.json) riprende la stessa entry dopo un errore
di verifica del download in r2. [Misure del runtime e log r2](cloud_delivery/r2/failure_snapshot_r1.json):
30,4 GiB RAM, 1.070 GiB temporanei e 19,5 GiB output liberi; guasto distinto
dalla precedente riserva disco. Il nuovo downloader usa intervalli esatti,
verificati anche con quattro test offline; l'hash atteso resta invariato.
Nessun nuovo fit o generazione, NTC/AMMI non interrotti. La ricevuta del watcher
in `cloud_delivery/r3/watcher_result_r1.json`, quando presente, riporta il seguito.

**Stato corrente:** [STATO_r16.md](STATO_r16.md), 9 ottobre, 19:23 Europe/Rome.
df11/r5 RUNNING con codice remoto verificato; progresso e parti finite non
osservabili tramite API/log live. Nessuna ETA complessiva verificabile.

**Accessi già pronti:** [STATO_r15.md](STATO_r15.md), 9 ottobre, 18:44 Europe/Rome.
Accessi AMMI autorizzati: 105 file, 97 contenuti distinti con header HTTP verificati,
21 mount ammissibili; locator privati fuori Git. Restano 12 parti NTC df11/r5.
[Ricevuta](ammi_private_access_issued_r1.json), [verifica HTTP](ammi_locator_headers_r1.json).

**Fotografia precedente:** [STATO_r14.md](STATO_r14.md), 9 ottobre, 18:10 Europe/Rome.
18 parti MX complete (35 contesti, 460.940 candidati), controlli ufficiali A/B/C
e ancore produzione verificati. Restano 12 parti df11/r5 in esecuzione e
l'accesso privato fra account. Nessun fold AMMI è ancora pronto al training.
[Consegna precedente](HANDOFF_RETI_r2.md).
Un [osservatore locale una tantum](df11_ntc_watch_started_r1.json) raccoglie
le ricevute df11 alla conclusione: `df11_ntc_watch_result_r1.json` e
`ntc_ready_manifest_r2.json`, quando presenti, sono le prove successive.
Non rilancia job, non trasferisce dati e non dichiara pronto il training.
[Diagnosi del recupero](STATO_r13.md), [consegna precedente](HANDOFF_RETI_r1.md),
[pin ancore](ammi_anchors_verified_r1.json),
[30 parti e 47 contesti attesi](ammi_ntc_runtime_contract_r1.json),
[T3 recuperabile senza nuovo invio](t3_preserved_handoff_r1.json).
I sei fit ESM2 hanno ricevute di consumo indipendente PASS. Routing della guardia
AMMI e accesso privato ai nuovi output restano da completare. Fast resta fermo.

**Fotografia precedente:** [STATO_r11.md](STATO_r11.md), 01:49 del 9 ottobre:
nessun nuovo upload completato. Il ripiego sul refit parziale non è stato
preparato per tempo: [incidente e responsabilità](deadline_incident_r1.json).
T36 era già valutato e non è stato reinviato. T3 ha tutte le cellule generate,
ma il confezionamento è fallito; Kaggle sta ancora esportando il recupero.
La scelta di recupero è stata rimessa al proprietario dopo le sue correzioni.
Il [protocollo T3](CONSEGNA_T3_PROTOCOLLO_r1.md) e la previsione registrata
prima del fit restano invariati. Il consenso Dixit/Shifrut è ricevuto e registrato.
La fotografia precedente è [STATO_r8.md](STATO_r8.md), alle 23:55 dell'8 ottobre.
Nuovo mandato: refit su tutte le fonti utilizzabili. Generazione T1 preparata ma
mai lanciata, ora superata e bloccata dal launcher. Accessi C/J-iPSC corretti
e consegnati al proprietario ESM2; locator privati fuori Git.
T2 è COMPLETE e gli effetti sono consegnati: nessun consenso al fit ancora pendente.
Produzione/T ESM2 sono RUNNING; ricevute finali del consumo ancora da verificare.
Le sei viste congelate sono invariate. I paragrafi iniziali e gli stati r1–r6
qui sotto sono fotografie dei rispettivi momenti, non nuovi blocchi operativi.

## Perimetro e stato iniziale

- File posseduti: soltanto questa cartella e i suoi nuovi output.
- Nessun job o download avviato. Nessun runtime occupato.
- Ingresso: `banca_canonica_2026-10-07/percorso.py` e i manifest congelati del 7/10.
- t36 resta riserva storica; nessuna robustezza ulteriore attribuita.
- Lettura corrente: release r1 a 17 fonti, non valutata; campioni cellulari non
  consumati dal fit. Queste sono prove datate da riconciliare, non verifiche cloud odierne.
- Freeze richiesto: 23:00 dell'8/10; consegna entro 02:00 del 9/10, Europe/Rome.

## Indice

- [HANDOFF_RETI_r1.md](HANDOFF_RETI_r1.md), [STATO_r12.md](STATO_r12.md): input neurali, verifiche e ostacoli correnti.
- [ammi_anchors_verified_r1.json](ammi_anchors_verified_r1.json): 17 ancore numeriche, due parità T0 e pin recuperati.
- [ammi_ntc_runtime_contract_r1.json](ammi_ntc_runtime_contract_r1.json): parti obbligatorie e contesti previsti; non è un completamento.
- [ammi_inner_truth_C-K562_r1.json](ammi_inner_truth_C-K562_r1.json), [ammi_inner_truth_C-iPSC_r1.json](ammi_inner_truth_C-iPSC_r1.json): sorgenti e routing da revisionare.
- [t3_preserved_handoff_r1.json](t3_preserved_handoff_r1.json): effetti, maschera e inventario delle cellule T3 conservate.
- [STATO_r11.md](STATO_r11.md), [deadline_incident_r1.json](deadline_incident_r1.json): mancata predisposizione del ripiego e correzione esplicita su t36.
- [STATO_r10.md](STATO_r10.md), [cloud_delivery/r1/plan.json](cloud_delivery/r1/plan.json): recupero LZF e corsia di upload diretto privato, senza trasferire la chiave VCC.
- [STATO_r9.md](STATO_r9.md), [candidate_t3_r1.json](candidate_t3_r1.json), [coverage_t3_r1.json](coverage_t3_r1.json): fit T3 verificato e ruoli delle 45 unità della banca.
- `generation_recovery/r1/`: recupero della sola generazione con effetti congelati; `generation_recovery/r2/` è una copia difensiva mai lanciata.
- `collect_t38_generation.py`, `t38_submission.py`, [t38_delivery_tests_r1.txt](t38_delivery_tests_r1.txt): guardie per ricevute, hash, forma completa e invio unico.
- [generation_incident_r1.json](generation_incident_r1.json): errore CLI misurato, correzione e guardia con parser reale.
- [CONSEGNA_T3_PROTOCOLLO_r1.md](CONSEGNA_T3_PROTOCOLLO_r1.md), [protocol.json](extended_transfer/r1/protocol.json): ramo T3 CRISPRi+KO congelato, 7 unità/12 contesti/5 voti KO, tutti i 34 bersagli disponibili.
- [private_locator_metadata_J_r1.json](private_locator_metadata_J_r1.json): audit metadata dei 987 locator J, senza richieste di rete o prova di accessibilità.
- [STATO_r8.md](STATO_r8.md): mandato corretto su tutte le fonti, nessun lancio T1, accessi privati iPSC consegnati.
- [cross_account_access_plan_r1.json](cross_account_access_plan_r1.json), [multi_account_authorization_r3.json](multi_account_authorization_r3.json): trasferimenti aggiuntivi autorizzati, guardie per destinatario e vista.
- [TRANSFER_RAPIDO_PROTOCOLLO_r1.md](TRANSFER_RAPIDO_PROTOCOLLO_r1.md): verifica di riuso; la corsia di generazione T1 è superata dal nuovo mandato r8.
- [STATO_r7.md](STATO_r7.md): verifica live, T2 completato e aggiornamento pronto per VALIDAZIONE; ricevute finali ESM2 pendenti.
- [HANDOFF_CJ_r1.md](HANDOFF_CJ_r1.md): quattro viste C/J K562/iPSC congelate e verificate, accessi runtime filtrati, supporto query esplicito; nessun fit C/J avviato.
- [STATO_r6.md](STATO_r6.md): job ESM2 privati corretti in esecuzione, verifica indipendente delle ricevute pronta; consumo ancora da attestare.
- [STATO_r5.md](STATO_r5.md): T2 verificato, accessi privati autorizzati preparati, consumo del primo fit ancora da attestare.
- [CONSEGNA_T2_r1.md](CONSEGNA_T2_r1.md): T2 eseguito, parità T1 e array finali verificati.
- [candidate_t2_r1.json](candidate_t2_r1.json): identità e contratto degli effetti di produzione T2.
- [MANDATO_RIPRESA_r1.md](MANDATO_RIPRESA_r1.md): nuovo via umano verificato e consenso specifico al trasferimento privato.
- `runtime_view_resolver.py`, `runtime_access_*`: risoluzione per hash dei mount e cache autenticata autorizzata; riferimenti sensibili fuori Git.
- `verify_external_consumption.py`: confronto indipendente delle ricevute del fit esterno con tutta la vista congelata; prove sintetiche in `external_consumption_tests_r1.txt`, senza attestare un consumo reale prima delle ricevute.
- [STATO_r4.md](STATO_r4.md): fotografia storica precedente al consenso e al completamento T2; stato corrente in r7.
- [HANDOFF_T2_MEDIE_r2.md](HANDOFF_T2_MEDIE_r2.md): consegna completa delle 16 medie di produzione e T/J.
- [coverage_ledger_r2.json](coverage_ledger_r2.json): collegamento fra catalogo, banca, derivazioni e ruoli effettivi, con lacune esplicite.
- [training_release_T_r1.json](training_release_T_r1.json): contratto del trainer con esclusioni target.
- [STATO_r3.md](STATO_r3.md): 41 unità di produzione verificate, ricomposizioni, T2 e limiti correnti.
- [training_release_production_r1.json](training_release_production_r1.json): contratto di training CRISPRi a 47 contesti, con manifest numerico fuori dal repository.
- [campaign_snapshot_r2.json](campaign_snapshot_r2.json): ricevute per unità, senza sommare produzione e fold come cellule nuove.
- `common_cd4/`, `k562_bulk_common_r1.json`, `common_stream.py`: medie fuori pannello e prove del loro ordine di calcolo.
- `final_t2/`, `prepare_final_t2.py`, `final_t2_driver.py`: preparazione del fit privato, con parità T1 obbligatoria.
- [HANDOFF_T2_MEDIE_r1.md](HANDOFF_T2_MEDIE_r1.md): contratto delle 16 medie di produzione consegnate al banco.
- [STATO_r2.md](STATO_r2.md): aggiornamento della campagna, release, runtime e limiti.
- [CONSEGNA_T1_r1.md](CONSEGNA_T1_r1.md): T1 verificata e consegna al banco.
- [candidate_t1_r1.json](candidate_t1_r1.json): identità degli effetti T1.
- [campaign_snapshot_r1.json](campaign_snapshot_r1.json): fotografia del consumo verificato.
- [training_view_production_pilot_r1.json](training_view_production_pilot_r1.json): primo contratto dei chunk CRISPRi.
- `alltargets/`: pacchetti immutabili, lanci, ricevute e verifiche per unità e split.
- `dispatch/`: preflight e ondate della campagna autorizzata.
- `private_share_xu_r1/`: evidenza della condivisione privata autorizzata.
- `fold_bank.py`, `alltarget_runtime.py`: selezione prima delle statistiche e derivazione a blocchi.
- `joint_rows.py`, `joint_runtime.py`: pooling biologico esplicito prima dello shrinkage.
- `cloud_campaign.py`, `dispatch_waves.py`: esecuzione con limiti e raccolta verificata.
- `training_view.py`: contratto per il consumer; non attesta il fit.
- `test_fold_bank.py`, `test_joint_rows.py`: invarianti scientifici su fixture piccole.

- [PROTOCOLLO.md](PROTOCOLLO.md): contrasti tecnici e precedenti, prima dei fit.
- [HANDOFF.md](HANDOFF.md): richieste precise e aggiornamenti per gli altri responsabili.
- `percorso.py`: ingresso della nuova versione; produce output nuovi, senza riscrivere r1.

Stati distinti: codice implementato, release verificata, fit eseguito, beneficio
misurato e copertura completa. Nessuno implica automaticamente il successivo.

## Riproduzione e consumo

Eseguire dalla radice del repository tramite `scripts/py.cmd`, usando
`reports/modelli/dati_transfer_2026-10-08_01a11c34/percorso.py` come ingresso.
`--help` elenca i comandi; scegliere sempre un nuovo nome di output.

| Comando | Risultato e limite |
|---|---|
| `audit <output.json>` | Verifica identità e popolazioni dei metadati della banca; non legge cellule raw. |
| `coverage <output.json>` | Collega ogni record del catalogo alle unità, ricevute e ruoli effettivi; mantiene separate le decisioni storiche non riverificate. |
| `freeze <release.json>` | Congela l'ammissione T1 rispetto al parent fissato per hash. |
| `package <release.json> <revision>` | Prepara il fit T1; non lo avvia. |
| `training-release production <revision>` | Costruisce il contratto CRISPRi da tutte le ricevute della campagna di produzione. |
| `training-release T <revision>` | Richiede tutte le ricevute con esclusioni; non riusa quelle di produzione. |
| `collect-common production <revision>` / `collect-common T <revision>` | Recupera i piccoli output dei job già autorizzati e congela solo un insieme completo di 16 fonti. Il recupero richiede l'autorizzazione già acquisita in chat. |

`verify_training_contract.py <release.json> <nuova_verifica.json>` controlla
hash locali, assi, unicità target/contesto, esclusioni e masse dei pesi senza
aprire le matrici remote. `training_contract_production_check_r1.json` ne conserva
il primo esito sulla release di produzione. Il consumer deve risolvere ogni
`UNRESOLVED_MOUNT` con i byte e gli hash del manifest, verificare i chunk e
applicare le esclusioni C/J prima delle statistiche apprese. Nessun fit è
attestato da questa verifica dei soli metadati.

I lanci restano nel controller `dispatch_waves.py`, con piano esplicito,
preflight e consenso cloud registrato: i comandi di release non lo avviano.
I sei `effect_release.json` CD4 oltre 1 MB sono conservati qui come unica
ricevuta completa degli esiti e delle esclusioni; gli array e il manifest
numerico del trainer sono fuori dal repository.
