# Runner Kaggle dopo la correzione della serializzazione

Notebook preparato, non inviato e non eseguito. Mantiene il nome remoto approvato
`davideferante/vcc-lead-generator-r1`, ma richiede lo snapshot corretto r2, SHA256
`634f228e1c358a1f1d4474d59a0dcac2f3a501921d68795ca9acd4b371db1033`.
Il notebook locale r1 rimane conservato come evidenza, senza essere stato eseguito.

La correzione r2, applicata dalla sessione principale, serializza l'asse dei geni come
Unicode invece di oggetti Python, così il caricamento NPZ non richiede pickle. Non cambia
split, predittore, generatore o regole di selezione. L'esecuzione Colab r1 si era interrotta
prima dello scoring. Sorgente e manifest corretti sono in
`C:/Users/ferra/vcc2026-data/interim/lead_generator_code_r2/`.

Per preparare la versione successiva degli input, dopo lo sviluppo concluso, usare
`prepare_kaggle_confirmation.py` con lo staging iniziale in `--dataset-v1`, la cartella
del codice r2 in `--snapshot-root`, il run Colab scaricato in `--development-root` e
una nuova cartella `--out`. Il builder verifica ogni fingerprint dello sviluppo rispetto
allo snapshot e ai dati; collega i dati originali, aggiunge il codice r2 e il bundle di
sviluppo. Non effettua upload né avvia il notebook.
