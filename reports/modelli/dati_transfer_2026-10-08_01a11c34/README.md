# DATI-TRANSFER — sessione 01a11c34, 8 ottobre 2026

Mandato del proprietario: banca canonica → training → predizione, copertura D-053 e
release immutabili. Questa cartella contiene codice ed evidenze della sessione;
la sede operativa condivisa resta R-LEAD, di competenza di VALIDAZIONE.

**Stato corrente:** [STATO_r7.md](STATO_r7.md), verificato alle 23:13 dell'8 ottobre.
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
