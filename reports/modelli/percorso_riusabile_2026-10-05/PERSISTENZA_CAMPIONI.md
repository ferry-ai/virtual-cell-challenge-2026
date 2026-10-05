# Primo campione persistente e lettura congiunta sul cloud

Heartbeat 5 ottobre, dalle 02:20 CEST. Stato tecnico; nessun nuovo fit o
risultato scientifico. Evidenze: `progress_r3.json`, `snapshot_r9/state.json`,
`snapshot_samples_r1/state.json`, `consumer_d1_rest_r1/launch.json`.

**Misurato:** D1 Rest ha concluso la materializzazione. Kaggle conserva la
versione privata 1 di `davideferrante11/vcc-samples-cd4-d1-rest-r1`:
8.100.133.840 byte, 1.093.082 cellule uniche nel livello 128, 660.906 nel 64,
414.048 nel 32. Sono selezioni annidate, non tre copie delle matrici.
Verificati codice salvato, stabilità della versione, presenza dei file,
manifest SHA256, collegamento alla banca, identità di righe/maschere e conteggi.
Gli hash delle matrici montate restano da verificare nel consumatore.
È stato scaricato solo il manifest; gli 8,10 GB restano su Kaggle.

**Implementato ed eseguito:** `sample_state.py` recupera solo manifest dei job
conclusi e isola le credenziali in processi separati. Rifiuta output mancanti,
codice/versione cambiati, conteggi o provenienza non riconciliati. Per i prossimi
controlli usare un nuovo `--out snapshot_samples_rN` e il più recente snapshot
delle banche con `--state`. Non confonde persistenza con uso nel training.

**Lancio accettato:** `davideferrante11/vcc-reader-d1-rest-r1`, CPU privata,
monta direttamente campioni e banca esistenti. `consumer_probe.py` attraversa
i due lettori, verifica gli hash consumati, conteggi e maschere, abbinamento dei
controlli e copertura delle righe. È esclusivamente una verifica di integrità:
non crea ancore, fit, split scientifici o statistiche di selezione di modelli.
Tutti i batch sono registrati esplicitamente con contributo alla loss nullo.
Alla chiusura verificare `consumer_complete.json`: l'accettazione del lancio
non prova ancora che i lettori funzionino sui dati reali.

`consumer_d1_rest_r1/live_r1.json` conferma l'esecuzione reale alle 02:36:
quattro CPU, 32,64 GB disponibili all'avvio, lettura delle popolazioni superata
e primi 63.380 campioni attraversati. La verifica completa resta in corso.

Gli ultimi log confermano avanzamento degli altri sette job originali.
Le due banche stimolate elaboravano D3; `snapshot_r9` mantiene sei unità
di banca con output finale persistente verificato. Non duplicare questi job.
I quattro test pertinenti dei lettori sono passati; nessuna suite generale.

**Prossimi passi:** recuperare le nuove chiusure con i supervisori, avviare i
campioni stimolati quando banche e slot sono pronti, verificare il consumatore.
Poi collegare asse nominale, trasformazioni lecite e ricevute di uso effettivo
al trainer. Rimangono aperti catalogo completo oltre CD4/pilot, integrazione
del training esteso e valutazione t28 dei 18 fit preliminari. Nessuna chiusura
D-053, promozione di rete, pubblicazione o push Git.
