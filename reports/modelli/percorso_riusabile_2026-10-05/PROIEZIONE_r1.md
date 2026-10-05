# Stima del lotto corrente, 5 ottobre 2026

**Misurato:** `archive_jobs_progress_r2.json`, 12 job accettati, sette COMPLETE e
cinque RUNNING; HepG2 ha già chiusura banca/campioni verificata. Aggiunti quattro
consumatori di archivi KOLF/HIPSCI appena si liberano slot, non nuova ingestion.

Il K562 GWPS sta alla prima metà del primo dei due blocchi: 27/50 shard, 1.547s
di banca. A549 25/31, 1.778s; i nuovi Tian/HIPSCI sono appena partiti.
Salvataggio delle statistiche e materializzazione dei campioni sono passi successivi.

**Stima operativa, non scadenza:** altri **1–3 ore** per le banche/campioni di questo
lotto, se gli avvii e l'I/O continuano regolari. Non è una promessa sull'intero
catalogo: mancano ancora adapter/QC/ruoli per sorgenti ulteriori e l'integrazione
del trainer. Il training esteso non è avviato e non ha ancora una ETA verificata.

**Dati:** 395,75 GB di grezzi perturbazionali già archiviati, non da riscaricare.
Nuovo ramo: 27,00 GB di banche; CD4/KOLF/HCT116 hanno 132,49 GB di campioni chiusi.
Con HEK293T e i derivati degli archivi precedenti, proiezione prudente **200–250 GB
di banca e campioni** complessivi per le fonti attuali, circa **600–650 GB** sommando
grezzi e questi derivati. Sono stime di artefatti distinti; non includono tutte le
versioni/copiedati, gli altri pacchetti storici, né nuove sorgenti del catalogo.

Non sono GB caricati contemporaneamente in RAM o tutti usati da ogni fold:
QC, ruoli, deduplicazione e D-053 determinano l'uso effettivo nel training.
