# DATI-TRANSFER — sessione 01a11c34, 8 ottobre 2026

Mandato del proprietario: banca canonica → training → predizione, copertura D-053 e
release immutabili. Questa cartella contiene codice ed evidenze della sessione;
la sede operativa condivisa resta R-LEAD, di competenza di VALIDAZIONE.

**Stato corrente:** [HANDOFF_RETI_r2.md](HANDOFF_RETI_r2.md), recupero NTC del 9 ottobre.
Sei parti disponibili in r6a (tre D4 riusate e tre nuove), controlli ufficiali
A/B/C completi; r6b/r6c e df11/r5 ancora in corso. Ancore produzione separate
in r2; 17 ancore dei fold e due parità T0 già verificate.
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
