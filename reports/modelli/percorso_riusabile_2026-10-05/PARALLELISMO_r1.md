# Parallelismo, 5 ottobre 2026

Mandato: usare Kaggle CPU sui tre account e quattro Colab CPU, senza duplicare ingestion.
Assegnazioni congelate in `parallel_archives_r1/assignments.json`; manifest originali e
accessi in `archive_metadata_r1/`, versioni e identificatori risolti in `archive_followup_r2/state.json`.

## Avvio del proprietario su Colab

Due account, due sessioni CPU per account, entro quanto consentito dal servizio.
Caricare `parallel_archives_r1/colab_slot_1.ipynb` e `colab_slot_2.ipynb` sul primo;
`colab_slot_3.ipynb` e `colab_slot_4.ipynb` sul secondo. Eseguire entrambe le celle.
Ogni account deve avere accesso alla cartella Drive `vcc2026`, con scorciatoia in MyDrive.
Non avviare i vecchi dispatcher: le nuove sessioni hanno lavori distinti.

Pacchetti già copiati e hash riletti in
`G:/Il mio Drive/vcc2026/runs/parallel_archives_2026-10-05_r1/`.
1: SCP KO (melanoma, Calu-3, THP-1); 2: SCP cellule T/Jurkat;
3: SCP K562/HEK293; 4: Tian/Norman (iPSC, neuroni e K562).
Sono derivati di archivi esistenti, non nuovi download delle sorgenti.

Output persistenti:
`Drive/vcc2026/data/processed/percorso_riusabile_2026-10-05/colab_<dataset>_r1/`,
con `bank/<unit>/complete.json`, `samples/<unit>/complete.json` e chiusura globale.
Log a flusso in `runs/parallel_archives_2026-10-05_r1/logs/slot_N.log`.
Non condividere token o cartelle di segreti con teammate; condividere solo i dati necessari.
Il pacchetto è verificato per hash nel Colab; CPU/RAM/disco misurati prima del calcolo.
La partenza effettiva e gli output di questi Colab sono ancora da verificare.

## Kaggle

Sette nuovi job CPU accettati e RUNNING: HepG2, Jurkat Nadig, H1 train/val,
RPE1, K562 GWPS sul primo account; K562 essential e A549 su davidmaisterx.
Kaggle ha derivato gli slug dai titoli: **usare gli identificatori effettivi di
`archive_followup_r2/resolved_launches.jsonl`**, non quelli richiesti dal primo ledger.
Il generatore è corretto per i prossimi job; nessun rilancio dei sette attivi.

Prima dei lanci: 0 job sul primo account, 2 su davidmaisterx, 2 sul terzo.
Il terzo account non legge nessuno dei dodici vecchi archivi provati (accesso 403):
non è corretto assegnargli quei consumatori o replicare matrici per riempire uno slot.
Continua i suoi campioni HEK293T già autorizzati. HIPSCI mirato resta da assegnare
appena si libera uno slot con accesso; non considerarlo escluso.

`archive_jobs_progress_r1.json` verifica avanzamento e risorse. I nuovi output Kaggle
non sono ancora chiusure persistenti certificate: recuperare piccoli manifest alla
fine e verificare versione salvata, conteggi e hash, senza scaricare matrici.

## Riuso e limiti

Nuova copia congelata del produttore già testato: supporta shard con più donatori/condizioni,
verifica asse nominale e SHA dei grezzi, preserva tutti gli strati e le maschere per BIO.
Fixture H5AD → banca → campioni con due donatori, parità dei counts e tamper: passata.
Livelli annidati 32/64/128, un solo CSR per cellula conservata; nessun nuovo sampling duplicato.

La banca da grezzi non risolve da sola QC o ammissibilità: Tian 2019 richiede ancora
la decisione sui droplet, UNASSIGNED non sono etichette di fit e i compound richiedono
componenti canoniche. Applicare D-053 nel trainer prima di usare questi derivati.
Non si dichiara training completo né miglioramento. Nessun GPU, invio, pubblicazione o push Git.

Southard resta parziale e conservato; i vecchi battiti del 3 ottobre non provano un
runtime vivo. Un eventuale ripristino deve riusare shard/ricevute (`--reuse`), non
avviare da zero né sovrascrivere l'output precedente.
