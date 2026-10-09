# T39 — upload verificato e finalizzazione accettata

**Misurato il 10 ottobre 2026, fuso Europe/Rome.** Il candidato T3+ESM2
è stato consegnato alla stessa entry `C49E3QzIDZk0LGmXPCPP`, senza nuovi
fit, rilanci o altre entry. Il consenso specifico è conservato in
[t39_t3_private_egress_authorized_r1.json](t39_t3_private_egress_authorized_r1.json).

- Upload verificato: 01:29:11 (23:29:11 UTC del 9 ottobre).
- Finalizzazione: 01:29:35, risposta VCC `Job launched successfully`.
- Stato server riletto alle 01:33:20: `scoring`; nessun punteggio letto.
- Pacchetto: `prediction_t39_T3_E2.vcc`, 3.995.084.800 byte.
- SHA256: `46e9a150a4d3f89dd2a7db688061ba2ad5aa5d50a890117c09302f3f72322cb6`.
- MD5 locale e remoto identici; 360.000 cellule, 18.533 geni,
  300 bersagli per contesto, 400 cellule per bersaglio, contesti A/B/C.
- Validatore ufficiale superato e array della matrice identici al file generato.

## Evidenze

[Ricevuta server](t39_t3/r2/server_receipt_obtained.json),
[risposta di avvio VCC](../../invii/trial_2026-10-10/t39_t3_launch_response.json),
[stato successivo](../../invii/trial_2026-10-10/status_C49E3QzIDZk0LGmXPCPP_delivery_check_r2.json),
[ricevuta upload](../../invii/trial_2026-10-10/t39_t3_cloud_upload_receipt.json) e
[verifica dei manifest](t39_t3/r2/completion_r1/verification.json).

Il job privato `davideferrante11/dt-t39-t3-e2-upload-01a11c34-r1`, versione 1,
è concluso; il raccoglitore ha riverificato identità del codice, effetti,
preregistrazione, forma, seed, scala applicata una volta, validatore e hash.
Sono stati recuperati soltanto otto piccoli JSON, non la matrice o il pacchetto.

Il watcher ha terminato con `SERVER_RECEIPT_OBTAINED`. Le ricevute esecutive
sono in `reports/invii/trial_2026-10-10/`. La lettura scientifica del punteggio
resta a Lead/VALIDAZIONE secondo la preregistrazione: questo esito operativo
non dimostra un beneficio del candidato e non chiude D-053.

## Controlli del repository

La [suite locale](t39_delivery_tests_r1.txt) ha eseguito 290 test: tre errori
per il modulo locale assente `cell_eval2.config`. Non sono errori del job
cloud o della validazione del pacchetto. Non è stata ripetuta la suite.
Il [primo controllo documentale](t39_delivery_docs_check_r1.txt) ha segnalato
due nuovi log durante le scritture concorrenti; le loro cartelle risultano
già coperte dalle righe del registro. Questi controlli non hanno bloccato
la finalizzazione, eseguita dal watcher indipendente.
Il [controllo documentale conclusivo](t39_delivery_docs_check_r2.txt) è passato:
74 checkpoint, registro, decisioni, 16 percorsi e collegamenti coerenti.
