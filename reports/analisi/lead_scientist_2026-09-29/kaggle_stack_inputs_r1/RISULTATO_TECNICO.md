# Stack A: inferenza completata e recuperata

**Misurato, 29 settembre 2026.** Il kernel privato
`davidmaisterx/vcc-stack-pilot-r1`, versione 1, ha completato l'inferenza alle
20:26:05 UTC con stato `generated_no_scores`; alle 20:30 UTC la API riportava
`COMPLETE`. Sono stati conservati 36 report piccoli, 162.957 byte, in
`kaggle_lead_monitor/r2/stack/lead_stack_r1/` nella cartella di questa analisi.

I due H5AD sono stati recuperati in
`C:/Users/ferra/vcc2026-data/interim/lead_stack_kaggle_A_r1/`, insieme ai report.
Dimensioni e SHA256 coincidono con `prediction_hashes.json` prodotto dal runner;
il file locale è stato letto nuovamente dopo il download.

| File | Byte | SHA256 |
|---|---:|---|
| prediction_stack.h5ad | 45.573.691 | `4baa9e71184fcf365a13860843a5700fdcfed245f5e7d51a212b850d6c2d1255` |
| prediction_transfer.h5ad | 45.681.785 | `0210a9ffb131ee9f0412b89b70ea4e6d9aa0ea7c39d63b2276ab86e7dbd55828` |

`download_manifest.json` nella destinazione documenta entrambi i download.
Il runtime verifica i 16 membri del bundle espanso; dichiara correttamente
`archive_sha256_verified=false`. I due roundtrip H5AD con indici nullable
confermano conteggi, ordine genico ed etichette prima dell'inferenza.

**Riproducibilità delle diagnostiche, non equivalenza delle cellule.**
`diagnostic_comparison_r1/comparison.json` confronta tutti i 12 target con i JSON
Colab r2 conservati prima del run Kaggle. Tutti i campi delle 12 diagnostiche sono
semanticamente identici; anche i nove campi di provenienza (bundle, adapter,
checkpoint, lista geni, geni condivisi/modello, batch, RNG, versioni) coincidono.
Le vecchie cellule Colab non erano state salvate: questi riscontri non provano
identità dei loro array.

**Qualità ancora non letta.** Nessun punteggio è calcolato o letto in questa
attività. Il confronto AB deve essere congelato prima della lettura; i file
recuperati sono disponibili per lo scoring CPU coordinato dalla lead.
