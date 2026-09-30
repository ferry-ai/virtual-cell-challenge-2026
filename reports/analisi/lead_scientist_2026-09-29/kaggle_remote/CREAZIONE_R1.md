# Creazione remota r1: evidenza prima della disponibilità

29 settembre 2026. **Misurato:** la CLI ha caricato i quattro file dati autorizzati,
`code_snapshot.tar.gz` e `input_manifest.json`, ed è terminata con exit code 0 e risposta
«Your private Dataset is being created» per
`https://www.kaggle.com/datasets/davideferante/vcc-lead-generator-inputs-r1`.

Il consenso esplicito dell'utente al payload e alla destinazione privata è stato ottenuto
prima dell'upload. Un primo tentativo era stato bloccato dal revisore automatico; dopo
il consenso il blocco è stato risolto. Il primo comando effettivo ha incontrato un errore
locale della cache Windows del client con il percorso assoluto a slash. L'esecuzione
dallo staging con `--path .` ha caricato lo stesso payload senza modificare il client.

Log esterni: `interim/kaggle_lead_generator_r1/create_dataset_r1.log` registra il problema
del percorso; `create_dataset_r2.log` l'upload riuscito. Questi sono nomi dei tentativi,
non versioni scientifiche dello snapshot. Il dataset caricato contiene ancora il codice r1.

**Non ancora verificato:** le successive richieste status, elenco file e metadati
restituiscono 403 Forbidden. L'account autenticato coincide con quello atteso; la lista
dei propri dataset mostra ancora soltanto il dataset precedente. La risposta di creazione
non prova quindi che i nuovi file siano già utilizzabili. Nessun notebook è stato inviato
e nessun calcolo Kaggle è stato lanciato. Non si ripete la creazione per aggirare questo stato.

La correzione della serializzazione r2 e il futuro bundle dello sviluppo verranno aggiunti
in una versione successiva, preservando r1. Il runner da usare è in `kaggle_remote/r2/`.
