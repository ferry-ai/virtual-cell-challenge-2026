# Revisione delle guardie prima di qualsiasi esecuzione successiva

**Implementato e verificato offline, 29 settembre 2026.** La revisione indipendente
ha trovato due controlli mancanti in `plan_r1`: cinque run coerenti fra loro potevano
avere iperparametri diversi dal comando previsto; gli hash dei piccoli input del
nuovo runtime venivano registrati senza confronto con quelli dei fold seed 0.

Il nuovo builder `build_neural_postgate_r2.py` e il runtime
`neural_postgate_runner_r2.py` lasciano intatti codice e archivio r1. Il gate verifica
per ciascuno dei cinque fold l'intero insieme di opzioni di training, compresi
`selection_seed`, passi, batch, campionamenti di geni e target, pazienza e learning
rate. Sono esclusi dal confronto soltanto percorsi, device, holdout e seed; questi
ultimi due devono comunque identificare un fold originale seed 0 valido. Opzioni
mancanti o aggiunte sono rifiutate. Il comando remoto è derivato dalla medesima
tabella verificata, senza cambiare i default di predizione o modalità preparazione.

Il gate conserva `options` e `data_files` del primo fold dopo il confronto fra tutti
e cinque. Prima di qualsiasi training, il runtime ricontrolla insieme dei file,
dimensione di ciascuno e ogni SHA256 registrato. Per file sotto 30 MB un hash assente
è un errore. Gli array grandi mantengono il limite già dichiarato dal run originale:
identità tramite versione del dataset, manifest e dimensioni, senza un nuovo hash
integrale quando il seed 0 non lo aveva registrato.

`plan_r2/runtime_payload.tar.gz` contiene 38 file, SHA256
`7a9094de87ee33c912a211c1474ab716ee3037c7de6d32c43452e8c3bd7fbf89`.
Trentasette file sono byte identici a `plan_r1`; cambia soltanto il runtime delle
guardie, ora con suffisso r2. Nessun training, architecture, protocollo, adapter o
lettore è cambiato. Non è stato creato alcun notebook, non è stato eseguito push e
non è stata richiesta una GPU.

**Misurato:** `test_neural_postgate_r2.py` passa: 30 configurazioni di opzioni
alterate/mancanti/aggiunte sono rifiutate; 5 casi di identità dati errata sono
rifiutati, incluso contenuto diverso a parità di byte; 3 gate con identità mancante
o cambiata sono rifiutati. Il comando corrisponde ai valori CLI nel launcher r1
originale; tutti i Python del payload compilano. Sono test software su piccoli
input temporanei e non risultati scientifici del modello.

Il comando successivo, dopo il gate completo e la revisione della lead, userà
`build_neural_postgate_r2.py --frozen-plan .../plan_r2 --seed0-runs <cinque fold>`
con un nuovo `--out`. Anche un gate positivo non avvia autonomamente seed 1 o
produzione: l'avvio rimane in attesa della decisione esplicita della lead.
