# DATI-TRANSFER — sessione 01a11c34, 8 ottobre 2026

Mandato del proprietario: banca canonica → training → predizione, copertura D-053 e
release immutabili. Questa cartella contiene codice ed evidenze della sessione;
la sede operativa condivisa resta R-LEAD, di competenza di VALIDAZIONE.

## Perimetro e stato iniziale

- File posseduti: soltanto questa cartella e i suoi nuovi output.
- Nessun job o download avviato. Nessun runtime occupato.
- Ingresso: `banca_canonica_2026-10-07/percorso.py` e i manifest congelati del 7/10.
- t36 resta riserva storica; nessuna robustezza ulteriore attribuita.
- Lettura corrente: release r1 a 17 fonti, non valutata; campioni cellulari non
  consumati dal fit. Queste sono prove datate da riconciliare, non verifiche cloud odierne.
- Freeze richiesto: 23:00 dell'8/10; consegna entro 02:00 del 9/10, Europe/Rome.

## Indice

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
