# t36 — candidato completo, download ripreso e invio autorizzato

6 ottobre 2026, 00:34 Europe/Rome. Nome **t36** corretto dal proprietario prima
dell'invio; t31 era una bozza locale mai inviata. L'utente ha confermato il file
esatto da 4,16 GB e la destinazione Virtual Cell Challenge dopo il rifiuto
auto-review, poi corretto soltanto l'etichetta. Nessun'altra conferma richiesta.

Rifit/generazione conclusi: [manifest](generation_successors_r1/completion_r1/generation_manifest.json)
e [packaging PASS](generation_successors_r1/completion_r1/packaging.json).
`prediction.vcc`: 4.163.225.600 byte,
SHA256 `ea41ddf1ba352911e81442f0e07af999450088a8d5e1738fc66656e1595d4af7`.
360.000 cellule sono l'output (3 contesti × 300 target × 400), distinto dai milioni
di cellule sperimentali nell'archivio. Release parziale, non tutti i 395,75 GB.

**Misurato:** r2 è terminato prima dell'upload. Il downloader Kaggle usa
`response.content`, ha perso il corpo incompleto in memoria e lasciato un file
locale di zero byte: [errore](generation_successors_r1/upload_execution_r2/state.json).
La nuova procedura usa HTTP Range a blocchi di 64 MiB e stream di 1 MiB, verifica
Content-Range e conserva byte parziali; SHA completo obbligatorio prima dell'invio.
Nessuna rigenerazione del modello. R3 fermato prima dell'upload per correggere t36,
375.390.208 byte riusati; r4 download-only preparato, mai avviato.

**Processo corrente:** PID7228, Hidden, prevenzione sospensione,
[lancio](generation_successors_r1/upload_execution_r5_t36/launch.json),
[stato](generation_successors_r1/upload_execution_r5_t36/state.json).
`download_submit_t36_r5.py` recupera lo stesso candidato e invia una sola volta
con i normali controlli di quota. Non avviare un secondo processo. Il percorso
locale conserva `t31_frozen_bank_2026-10-06` per riusare i byte: non è il nome VCC.
Output CLI previsto `reports/invii/trial_2026-10-06/submit_t36_raw.json`; leggere
l'entry prima di qualsiasi resume, mai creare una seconda entry alla cieca.

[Record t36](../../invii/prediction_t36_2026-10-06/prediction.json): record runtime
congelato prima dello stage100, copia locale successiva alla generazione. Nessuna
banda numerica preregistrata, nessun miglioramento presunto. Questo aggiornamento
sostituisce lo stato operativo r16; le prove e i tentativi precedenti si conservano.
Invio non ancora dichiarato riuscito; copertura completa e valutazione restano aperte.
