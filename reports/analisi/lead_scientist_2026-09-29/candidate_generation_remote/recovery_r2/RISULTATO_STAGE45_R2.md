# t28: cellule recuperate e riproducibilità verificata

Misurato il 29 settembre 2026. La ricevuta di Colab delle 20:41:15 UTC attesta
la copia completa verificata per SHA256 su Drive prima dell'avvio dello stadio 48.
Il file contiene 360.000 cellule, 18.533 geni e 2.085.425.466 valori memorizzati;
pesa 4.213.225.652 byte. La provenienza dei tre contesti passa i controlli dello
stadio 45. Picco RSS dichiarato: 0,63 GiB.

SHA256 del file h5ad:
`123ce93f4d8d21c107215c96f726a6b7121545c1329948f431234eabce80f40e`.
Coincide con quello registrato nel diagnostico del primo runtime poi perso:
la rigenerazione della stessa ricetta è identica byte per byte.

Le quattro ricevute originali sono conservate in `stage45_receipt/`.
Il file completo resta fuori dal repository, in
`MyDrive/vcc2026/runs/lead_candidate_t28_2026-09-29_r2/stage45_checkpoint/`.
Questa verifica riguarda le cellule: non dimostra ancora il completamento del
contenitore `.vcc`, un miglioramento VCC o l'autorizzazione a inviarlo.
