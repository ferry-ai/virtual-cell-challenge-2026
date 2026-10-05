# Candidato concluso; trasferimento e invio in corso

6 ottobre, 00:20 Europe/Rome. Job generazione versione1 COMPLETE, codice salvato
verificato contro il codice del lancio: upload_execution_r2/producer_verified.json.
Stage100/45/48 conclusi; [manifest finale](generation_successors_r1/completion_r1/generation_manifest.json).
File prediction.vcc:4.163.225.600byte,
SHA256 `ea41ddf1ba352911e81442f0e07af999450088a8d5e1738fc66656e1595d4af7`.

[Packaging](generation_successors_r1/completion_r1/packaging.json): tutti i controlli
di formato PASS;360.000cellule,18.533geni,A/B/C120.000ciascuno,300target ciascuno,
400cellule/target,zero controlli,conteggi finiti/interi/nonnegativi e asse ufficiale.
[Record congelato prima dello stage100](generation_successors_r1/records_r1/prediction_record.json)
conserva ricetta, origini/hash delle fonti e controlli montati. Non è una valutazione
predittiva e non dimostra miglioramento. Release estesa parziale come r15.

Trasferimento e invio autorizzati in un processo Windows indipendente, Hidden,
con prevenzione sospensione: PID18600, [lancio](generation_successors_r1/upload_execution_r2/launch.json),
[stato corrente](generation_successors_r1/upload_execution_r2/state.json).
Script download_submit_frozen_r2.py recupera SOLO il file finale in
`C:/Users/ferra/vcc2026-data/submissions/t31_frozen_bank_2026-10-06/`, verifica byte
e SHA, poi esegue un unico vcc submit con i normali controlli di quota.
Testi e output grezzi in reports/invii/trial_2026-10-06. Non rilanciare lo script:
seguire stato/PID, e leggere l'entry creata prima di qualunque resume.

Primo processo r1 terminato prima del trasferimento per cartella genitore locale
inesistente; r2 corregge solo mkdir(parents=True). Nessun ricalcolo, download doppio
o entry VCC creata dal primo tentativo. Log del primo conservato.
Recupero log Kaggle inizialmente fallito per codifica locale; PYTHONUTF8=1 ha
risolto il solo downloader. Manifest immutati riusati, modello non rilanciato.

Il file non è ancora dichiarato inviato: monitorare upload_execution_r2/state.json
e submit_t31_raw.json. Valutazione ufficiale e copertura completa restano aperte.
