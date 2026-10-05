# Prima release estesa: 24 pacchetti CPU pronti per il push del parent

Misura: `launch_packages.py` ha scritto il dispatch alle 2026-10-05T16:57:17Z. Orologio letto subito dopo: 2026-10-05T16:57:22Z. Questo worker non ha eseguito `kaggle kernels push`, non ha scritto `launches.jsonl` e non ha identificativi di kernel. `worker_pushed` è false. `fit_admitted` è false. Il confronto 400×5 non è partito (`comparison_protocol.json`, `observed_result` null).

## Azione del parent

Preflight fresco, poi i push nell'ordine di `ready_dispatch.json`, con tetto di 5 kernel attivi per account. Il preflight di questo worker non è stato rieseguito: l'ultimo dato del parent è GWPS ancora aperto e il reader Norman/iPSC già COMPLETE.

```text
.\scripts\py.cmd reports/modelli/percorso_riusabile_2026-10-05/agenti/grok_transfer_esteso_r4/preflight_slots.py reports/modelli/percorso_riusabile_2026-10-05/agenti/grok_transfer_esteso_r4/preflight.json 20
```

Il file `preflight.json` non esiste: lo crea quel comando. Primi push, se il preflight lascia i posti:

1. `davideferrante11` — `packages/vcc-effects-orion-hct116-r4`, poi `vcc-effects-orion-hek293t-r4`, `vcc-effects-d1-rest-r4`, `vcc-effects-rpe1-r4`, `vcc-effects-jurkat-nadig-r4`. Se GWPS occupa ancora uno slot, il quinto resta in coda.
2. `davidmaisterx` — `packages/vcc-effects-k562-essential-r4`, poi i tre `vcc-effects-d4-*-r4`. Configurazione `.kaggle`.

Esempio, account del proprietario, primo della coda:

```text
Remove-Item Env:KAGGLE_USERNAME,Env:KAGGLE_KEY,Env:KAGGLE_API_TOKEN,Env:KAGGLE_CONFIG_DIR -ErrorAction SilentlyContinue; $env:KAGGLE_CONFIG_DIR = Join-Path $HOME '.kaggle-davideferrante11'; $py = & .\scripts\py.cmd -c "import sys; print(sys.executable)"; $kaggle = Join-Path (Split-Path $py) 'kaggle.exe'; & $kaggle kernels push -p 'C:\Users\ferra\OneDrive\Desktop\vcc2026\reports\modelli\percorso_riusabile_2026-10-05\agenti\grok_transfer_esteso_r4\packages\vcc-effects-orion-hct116-r4'
```

Ogni pacchetto ha il comando completo nel dispatch. Non rilanciare `davideferrante11/vcc-derivatives-rlab-k562-gwps-r3`, `davidmaisterx/vcc-reuse-runtime-norman-ipsc-r1` (reader COMPLETE, ricevuta `b779ab8a5518674114c4c780a757666b412a2777a539b72b7b90af2a6d1e43fa`) né `davideferante/vcc-derivatives-hipsci-targeted19-r1`.

## Cosa esegue il kernel

Fase 1, 24 kernel CPU privati, GPU/TPU/internet spenti. Ogni kernel monta la banca chiusa e `gene_names.csv` dell'account proprietario, ricalcola gli hash di asse, `count_sum`, `rows.csv` e `mask` prima della stima, applica gli split C/J (72) e i target nascosti prima delle statistiche, e salva `statistics/*.npz`, `source_model.json`, `fit_receipt.json` e `checkpoint.json`. Il rifit lineare non ha loss né optimizer: la ricevuta lo dichiara. Ripresa: se il checkpoint e gli hash coincidono, il job non ricalcola.

Ricetta congelata nel pacchetto: effetti shrunk, ampiezza 1.576, gamma 1, reliability 100, peso 1 per fonte, `min_expected` 1, pseudocount 0.5 costante, phi 0.2, emissione t28 (400 cellule, 5 semi, seed 20260912, effects_scale 1.5, dispersione genica 1). Testa cis: distanza 5000, scala 2. Il path della ricetta `reports/cis_2026-09-17/k562_neighbour_pairs.csv` è assente; il file presente è `reports/trasferimento/cis_2026-09-17/k562_neighbour_pairs.csv`, sha256 `d874c305f12e932d2d43eff629ea7d44c8536b7a198868c8fac10007d01dcf8f`, 248599 byte. Punteggio ufficiale t28 0.14484520500645978 trascritto da TRANSFER_IDENTICO: è il riferimento del sito, non la baseline locale.

Asse locale ricalcolato dal builder: sha256 `25bfa66715e186bebabce7ac788bbcea47e2bf59ca70be1f8f3a06f2f0e47201`, 18533 geni. Gli hash di `count_sum` e `mask` nel dispatch sono quelli dell'indice r10; il kernel li verifica sul file montato. Storage r10 `7134c13c741e04b1bb90b15f42afd2a50e653454aca17e49005edcad6f2e7fdf`. Il flag `training_ready` dell'indice resta false: è lo stato dello storage, non il blocco di questi 24 job.

Il pool dei controlli ora include ogni donatore con controlli non-targeting, anche se quel donatore non ha il bersaglio. Prova su fixture, stesso input denso della funzione originale `effects_from_pseudobulk`: gli shrunk coincidono; il pool ridotto ai soli donatori col bersaglio no. Sette test del file `test_r3_refit.py` passati in 7.1 s. Sono fixture, non l'esecuzione sulla banca.

## Prima release e catalogo D-053

Questa è la prima release estesa delle banche CRISPRi chiuse e montabili, con lo stesso transfer t25/t28. Non è il catalogo D-053. `inventory.json` elenca i 100 record di `catalogo_r4`, ciascuno con ruolo e evidenza del classificatore, più Orion assente dal catalogo.

Nel lancio (24): CD4 dodici unità come sotto-contesti di `cd4_mix`; Orion HCT116 e HEK293T; `k562_essential` come fonte distinta, che lascia il GWPS al job del parent; Jurkat; RPE1; H1 train e val come un solo voto `h1`; HepG2 come validazione, fuori solo dallo split che tiene HepG2; quattro KOLF distinti, con ancora non verificata e comunque stimati.

Fuori dal lancio, con motivo (19 unità r10 più due assenze): Norman senza mappa dei composti; Tian2019 con QC aperto; Tian2021 con etichetta `control` non mappata; HIPSCI genome-wide con controlli scarsi e unassigned che non è un controllo; HIPSCI targeted19 con controlli non risolti e asse assente sull'account `davideferante`; A549 KO; dieci banche SCP/modalità non partizionata; GWPS aperto; GSE249595 senza guide. Nessuna di queste mappe è stata inventata.

Fase 2, `release_fit.py`, mescola i frammenti con peso 1 e scrive effetti, manifest ed esposizione. `push_now` è false finché gli output della fase 1 non esistono (`release_phase2/PREREQUISITE.json`). Il mix di prova sulle fixture scrive i tre file e tiene HepG2 solo fuori dallo split HepG2. Il mix sulla banca parte dopo i kernel.
