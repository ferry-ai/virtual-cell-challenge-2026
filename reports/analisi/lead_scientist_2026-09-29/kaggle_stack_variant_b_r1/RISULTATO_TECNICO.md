# Stack B: inferenza completata e baseline invariata

**Misurato il 29 settembre 2026.** Il kernel privato
`davidmaisterx/vcc-stack-variant-b-r1`, versione 1, termina con stato
`generated_no_scores` alle 20:58:29 UTC. La API riporta `COMPLETE` alla lettura
delle 21:01 UTC. L'avvio segue l'autorizzazione esplicita dell'utente per gli invii
necessari, dopo la domanda concreta sulla variante B; nessun nuovo dato è stato
caricato. Il solo dataset è quello pubblico di 32 MB già conservato privatamente.

`push_raw_r1.txt`, `status_after_push_r1.txt`, `pull_after_push_r1/` e
`pull_verification_r1.json` conservano avvio, codice e metadata. Le celle eseguibili
scaricate coincidono esattamente con il notebook approvato
`9e5f87d176f24953cd543b492dbdc924fbe4ea630187c40c64dff7717596b579`.

Recuperati 38 report piccoli, 171.351 byte, in
`kaggle_lead_monitor/r8/stack_b/lead_stack_variant_b_r1/` della cartella di analisi.
I due H5AD, con hash produttore e rilettura locale verificati, sono in
`C:/Users/ferra/vcc2026-data/interim/lead_stack_kaggle_B_r1/`:

| File | Byte | SHA256 |
|---|---:|---|
| prediction_stack.h5ad | 45.829.851 | `7dc7cf11c36ad97ff13f20be9e5dc4c70085fa024c8b0f8d87cf0eeb8ae3c790` |
| prediction_transfer.h5ad | 45.681.785 | `0210a9ffb131ee9f0412b89b70ea4e6d9aa0ea7c39d63b2276ab86e7dbd55828` |

**Misurato:** il file transfer di A e B è byte-identico. Sono stati anche
confrontati shape 4.800×9.624, obs, var, indptr, indices e data CSR con letture
limitate a un milione di elementi: tutti esatti. Evidenza in
`transfer_cells_comparison_r1.json`, codice `verify_stack_ab_baseline.py`.
Questa verifica riguarda la baseline e non implica qualità o identità fra le
predizioni Stack A e B, che sono volutamente varianti diverse.

Nessuno score è stato letto o calcolato da questa attività. Gli output sono
consegnati alla lead per il confronto AB congelato e lo scoring CPU.
