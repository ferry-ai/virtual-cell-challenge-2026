# Correzione meccanica del lettore, dopo il push della versione 1

29 settembre 2026, registrazione dopo la verifica delle 18:01:41 UTC. Il notebook
privato `davidmaisterx/vcc-lead-neural-sources-r1` è già in esecuzione. Non viene
riavviato o sostituito per questa correzione.

**Difetto riprodotto su fixture sintetica:** `pandas.read_csv` interpreta la stringa
`null` come mancante. La colonna che identifica il braccio nullo perde quindi il suo
nome; il lettore congelato cerca poi `null` e non può completare il riepilogo. Lo
stesso comportamento può alterare un nome letterale di bersaglio `NA`.

L'unica modifica al lettore è `keep_default_na=False` nella lettura di
`per_target.csv`. Non cambia training, checkpoint, split, metriche, bootstrap,
aggregazione, confronti o soglie. Il difetto riguarda la deserializzazione dei nomi.
La correzione è stata motivata dai test, senza leggere risultati reali della rete.

La copia byte per byte del lettore inviato è conservata in
`neural_reader/r1/read_neural_sources.py`.

- SHA256 prima: `95f0f37610778d26b09806cfed5614d054c8f6fa181a6844480f5277f47c8f22`.
- SHA256 dopo: `21b936b387ec734e0aaeb4b85f982f127a465a84fb3a77dc89917190881a8243`.

Il launcher remoto tenta i cinque fold prima del riepilogo. Un errore del solo
lettore finale non invalida un training completato né autorizza a saltare un fold.
Gli output scaricati sono controllati con `verify_neural_runs.py` e poi letti con
`read_neural_verified.py`, che registra entrambi gli hash e questo emendamento.
La verifica pretende copertura completa, versioni e opzioni coerenti, assenza di
righe di test nel training e tutti i bersagli congelati per ogni braccio.
