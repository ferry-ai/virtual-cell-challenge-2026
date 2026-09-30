# Stack: avvio privato verificato

**Misurato il 29 settembre 2026, circa 20:21 UTC.** Dopo il rifiuto preventivo
documentato in `BLOCCO_AVVIO.md`, l'utente ha risposto esplicitamente «Sì, invia e
avvia Stack» alla domanda su notebook/codice, kernel privato e GPU gratuita.
Il nuovo tentativo ha creato la versione 1 del kernel
`davidmaisterx/vcc-stack-pilot-r1`; la prima lettura è `RUNNING`.

La destinazione privata usa soltanto `davidmaisterx/vcc-stack-prompts-r1`, già
verificato READY. Kaggle ne ha estratto automaticamente l'archivio: il runtime
`fresh_r2` verifica il manifest e i 15 contenuti, la lista esatta di 16 file e la
copia locale prima di installare dipendenze o scaricare pesi. Distingue questa
verifica da un hash dell'archivio originale, non disponibile nel mount.

`push_raw_r1.txt` e `status_after_push_r1.txt` sono le risposte del servizio.
`pull_after_push_r1/` conserva notebook e metadata remoti; la verifica eseguita
da `verify_stack_pull_r1.py` è in `pull_verification_r1.json`: tutte le celle
eseguibili coincidono esattamente con il notebook approvato, la sintassi è valida,
il kernel è privato con GPU e Internet e il solo dataset previsto. Il notebook
intero viene riserializzato da Kaggle e non è dichiarato byte-identico.

Non è ancora una misura di qualità. Le 12 diagnostiche della precedente
inferenza Colab sono conservate in `reference_diagnostics_r2/`; il confronto con
quelle Kaggle sarà una misura distinta. Le sole diagnostiche non dimostrano
identità delle cellule generate.
