# Esito terminale della diagnostica CPU

**Misurato:** il preflight si è fermato alle 19:47:28 UTC del 29 settembre 2026:
`Completed seed0 kernel output is not uniquely mounted: k562`.
Il runner non ha avviato la diagnostica, né training; il gate di seed 0 resta
negativo. Il limite previsto in `LIMITE_SORGENTE.md` è ora confermato dall'esito,
senza inferire la causa interna del rifiuto della dipendenza da parte di Kaggle.

Evidenza primaria recuperata con hash:
`../kaggle_neural_monitor/r4/cluster0/download_manifest.json` e
`../kaggle_neural_monitor/r4/cluster0/neural_cluster0_r1/completion.json`.
Sono due piccoli report, 8.399 byte, più il log statico. Nessun tentativo ulteriore
è stato avviato. La replica seed 1 risultava ancora RUNNING alle 19:50 UTC.
