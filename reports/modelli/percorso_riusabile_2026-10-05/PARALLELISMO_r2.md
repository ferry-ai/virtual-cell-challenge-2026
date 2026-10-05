# Parallelismo osservato e ostacoli, 5 ottobre 2026

Misurato: 16 job CPU distinti accettati dai tre account Kaggle; non significa
16 sessioni contemporanee. Sette dei primi dodici COMPLETE nell'ultimo snapshot,
cinque RUNNING. Lanci: `archive_launches_r2.jsonl` e
`remaining_archives_r1/launches.jsonl`; stati: `archive_jobs_progress_r2.json`
e `remaining_archives_progress_r1.json`. La prima chiusura HepG2 conserva codice,
versione, ricevute e presenza degli artefatti in `archive_completion_hepg2_r1`.
Nessun training esteso ancora avviato né consumo certificato dal trainer.

I quattro nuovi consumatori KOLF piccoli/forte e HIPSCI genome-wide hanno accesso
verificato agli input. Entrambi KOLF avanzano; HIPSCI gwnonfit è RUNNING.
HIPSCI gwfit è ERROR: `hipsci_failure_r1/vcc-derivatives-hipsci-gwfit-r1.log`
registra `OSError: insufficient output capacity` nel controllo banca
`N * G * 21 + 2 GiB`. La sessione aveva circa 20,94 GB di disco libero.
Non è un fallimento dei grezzi, né ragione per escludere questi dati.
Occorre una partizione dei derivati che conservi gruppi BIO/target, ancore,
conteggi e campionamento globale, con ricevuta di unione verificata, oppure
un runtime autorizzato con spazio sufficiente. Non rilanciare lo stesso job
né togliere il controllo di capienza. Stima 1–3 ore del lotto subordinata a
questa correzione; non è una ETA del corpus completo o del training.

I quattro Colab preparati in PARALLELISMO_r1 non sono mai partiti: sostituiti
da Kaggle, non avviarli. I cinque archivi resi pubblici con autorizzazione
puntuale sono verificati in `public_archives_r2/publication.jsonl`.
I nuovi output sono privati: l'accesso del trainer va verificato senza rifare
calcolo, ingestion o upload dei grezzi. Indice corrente: cloud_catalog_r4;
tabella dati corrente: DATI_DISPONIBILI_r2 (unità riconciliate ai file pubblicati).
