# t36 — transfer t28, banca estesa parziale

**Misurato:** ricevuto da VCC il 6 ottobre alle00:56 Europe/Rome. Entry
`JLcMRGExhXKk77XVds7x`, 4.163.225.600 byte, MD5 remoto verificato;
[ricevuta](submit_t36_public_receipt.json), [SHA locale](t36_local_product.json).
[Primo stato ufficiale completo](status_JLcMRGExhXKk77XVds7x_0105.json): launching,
senza punteggio. Nessun secondo invio o download.

Modello e ricetta in [record t36](../prediction_t36_2026-10-06/README.md),
[ricetta](t36_recipe_extbank.json), [manifest finale](t36_generation_manifest.json)
e [packaging](t36_packaging.json). 360.000 cellule sono l'output generato, non
le cellule sperimentali della banca. Release parziale, nessun miglioramento presunto.

Il proprietario ha corretto **t31 → t36 prima dell'upload**: testi e copie t31 si
conservano come bozza mai inviata. `submission_texts_t36.md` è il testo effettivo;
il percorso locale `t31_frozen_bank_2026-10-06` è solo l'origine del trasferimento
parziale riusato, non un altro modello o invio.

`submit_t36_raw.json` conserva integralmente l'output CLI locale. Contiene il
percorso remoto con identità personale ed è escluso da Git; la ricevuta pubblicabile
registra il suo SHA256 senza quel campo. I successivi stati ufficiali vanno salvati
in file nuovi, senza sovrascrivere questo stato né inventare membri mancanti.
