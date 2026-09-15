# CP-0016 — Piano operativo: audit sorgenti e protocollo di valutazione congelato

- **Data:** 2026-09-15
- **Tipo:** cambio-di-strategia
- **Redatto da:** agente Grok (Grok 4.6)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il piano operativo del 15 settembre chiede di concentrare oggi audit, protocollo
e infrastruttura, con Jiang e Jurkat in testa. Che cosa si può stabilire
**senza** scaricare matrici da più gigabyte, e quale regola di valutazione va
congelata prima di nuovi punteggi?

## 2. Cosa è stato fatto

```bash
.\scripts\orch.cmd doctor
.\scripts\orch.cmd brief configs/orchestrator/briefs/vcc2026-jiang-audit.yaml
.\scripts\orch.cmd start --brief configs/orchestrator/briefs/vcc2026-jiang-audit.yaml --label jiang-audit-2026-09-15
.\scripts\py.cmd -m unittest tests.test_eval_protocol tests.test_remote_job
.\scripts\py.cmd scripts/61_probe_jiang.py --out reports/jiang_2026-09-15
.\scripts\py.cmd scripts/62_reconcile_nadig.py --out reports/nadig_reconcile_2026-09-15
.\scripts\py.cmd scripts/63_runtime_preflight.py --out reports/runtime_2026-09-15
.\scripts\py.cmd scripts/64_source_cards.py --out reports/source_cards_2026-09-15
.\scripts\py.cmd scripts/65_eval_protocol_pilot.py --out reports/eval_protocol_2026-09-15
.\scripts\py.cmd scripts/66_primeflow_feasibility.py --out reports/primeflow_2026-09-15
```

Il database dell'orchestratore, che il piano segnalava come `unable to open
database file`, in questa sessione si è aperto
(`C:/Users/ferra/vcc2026-data/orchestrator/orchestrator.sqlite3`,
`orch doctor` verde su DeepSeek e Kimi). La campagna Jiang è **avviata**, non
conclusa: run `20260915T115742Z-vcc2026-jiang-audit-v1-a81104`.

Nessun RDS Jiang e nessun Jurkat sono stati scaricati. Nessun training nuovo.

## 3. Cosa si è osservato

**Jiang (misura).** Il record Zenodo 14518762, v2.1, licenza `cc-by-4.0`, espone
12 file. I cinque Seurat Perturb-seq sommano **20.141.612.637** byte. Il blocco
più piccolo è `Seurat_object_TGFB_Perturb_seq.rds`, **2.642.041.433** byte,
md5 `8e9b4d39a95ec5881a30be6a2df541d1`. HEAD HTTP 200 su ciascun RDS, con
`Content-Length` coincidente. Cinque file sotto 2 MB scaricati (readme, tre
liste di pathway, protocollo Parse). La copertura del pannello 300 è **missing**:
nessun elenco di target è stato letto.
Fonte: `reports/jiang_2026-09-15/jiang_probe.json`.

**Disco locale (misura).** 7,81 GiB RAM totali, **11,3 GiB** liberi su
`C:/Users/ferra/vcc2026-data`, 0,53 GiB RAM disponibili al momento della
misura. Scaricare il solo TGFB lascerebbe circa 8,8 GiB, sotto il pavimento
da 10 GiB di D-005. HepG2 già locale (0,85 GB) lo rispetta.
Fonte: `reports/runtime_2026-09-15/runtime_inventory.json`.

**HepG2 GEO vs mirror (misura).** Stessa forma 145.473 × 9.624. NTC GEO
`obs.gene == 'non-targeting'` = 4.976; mirror `obs.perturbation == 'control'`
= 4.976. md5 del mirror già verificato in acquisizione. Non sono due esperimenti.
Fonte: `reports/nadig_reconcile_2026-09-15/nadig_reconciliation.json`.

**Jurkat (misura, file non aperto oggi).** GEO 262.956 × 8.882, 12.013 NTC,
0/300 bersagli del pannello, 8.284 geni in comune con l'asse. Mirror scPerturb
1.293.665.804 byte, md5 `d8b05d00bfbd686d37ffdd4293bc6c8c`. Schema GEO allineato
a HepG2 GEO. Fonte: come sopra, più
`reports/candidate_verification/jurkat_probe.json` e
`reports/candidate_verification/coverage_summary.json`.

**Altre sorgenti (derivato da evidenza già locale o citata).** Srivatsan e
Tahoe: farmaco, **exclude**. scBaseCount: osservazionale, **exclude**.
McFaline-Figueroa: combinato genetico+chimico, **defer**. Replogle single-cell
e H1: **defer**. CD4: **defer** (copertura alta, 1,7 TB).
Fonte: `reports/source_cards_2026-09-15/decisions.md`.

**Protocollo (misura).** Dodici split del run a tre contesti: **0 fallimenti**
di leakage algebrico (unseen ∩ train vuoto; seen con train=test). Tutti e
dodici sono **sviluppo** (seed 2026 e 2027). Il seed di conferma 4242 non è
stato aperto. Fonte: `reports/eval_protocol_2026-09-15/split_audit.json`.

**PRiMeFlow (citato, non eseguito).** Il risultato VCC 2025 H1 del preprint
usa finetuning con perturbazioni del contesto query. Pretrained-only è più
debole su quel compito (PDS 0,712 vs 0,817). Codice e pesi **missing**.
Fonte: `reports/primeflow_2026-09-15/primeflow_feasibility.json`.

**Ancore HepG2.** Un passaggio di codice su una finestra contigua di 2.000
cellule ha trovato un solo bersaglio con abbastanza cellule. Non è un campione
casuale dello studio e **non è un risultato da usare**. I test unitari delle
ancore restano su dati sintetici.

## 4. Interpretazione e incertezza

Jiang aggiunge linee e stimoli, non trenta contesti indipendenti. K562 in Jiang
è un esperimento nuovo su una linea già locale. Lo stimolo è una covariata e
una possibile fonte di mancata trasferibilità verso la gara, che non stimola.

Jurkat è il quarto contesto perturbato più economico da aggiungere, con
copertura pannello zero: serve al trasferimento fra linee, non alla
supervisione dei 300.

Questa macchina non è il posto in cui deserializzare un RDS da 2,6 GB
(RAM 7,81 GiB, disco sotto soglia). Il notebook remoto è la sede del primo
blocco.

PRiMeFlow non è un confronto giustificato su VCC 2026 finché il protocollo
non esclude ogni perturbazione del contesto query e non esistono pesi con
costo misurato.

## 5. Spiegazione semplice

Abbiamo tre linee perturbate in casa. Per imparare a predire una **quarta**
linea mai vista, Jiang offre sei linee sotto stimolo e Jurkat una linea T.
Nessuno dei due file grandi sta su questo portatile senza violare la regola
dei 10 GiB liberi. Prima di scaricarli altrove, abbiamo congelato come si
giudica un modello: i test di settembre sono compiti in classe, il compito
in palestra ha un seed ancora chiuso.

## 6. Conseguenze

- **D-004** (ordine CD4 → Orion) è **superata** per l'ordine operativo:
  la sostituisce **D-031** (Jiang audit, poi Jurkat, CD4 rinviato). L'argomento
  di copertura di CD4 resta vero e non è cancellato.
- **D-032:** protocollo di valutazione congelato in
  `configs/eval_protocol.yaml`. Seed 4242 riservato. I fold del 14–15 settembre
  sono sviluppo.
- Jiang e Jurkat restano `enabled: false` finché un runtime remoto non misura
  RAM/disco e non produce NTC abbinati.
- PRiMeFlow e State: nessun porting oggi.
- Prossimo lavoro pesante: notebook remoto, dopo che quel runtime ha scritto
  il proprio inventario. In locale: attendere il dossier Jiang dell'orchestratore
  e non aprire il seed 4242.

## 7. Cosa corregge

- `docs/PROGETTO.md` §2 diceva ancora «banco di prova predittivo bloccato:
  manca un dataset perturbato reale» mentre HepG2 è locale dal 14 settembre
  ([CP-0013](0013-hepg2-terzo-contesto.md)). Corretto nella mappa: il banco
  metodologico a singola cellula esiste; manca il pannello 300 e mancano le
  ancore ufficiali.
- Il numero **2.319** bersagli condivisi nella mappa non coincide con
  `reports/benchmark_3ctx_2026-09-14/summary.json` (**2.315**). Si cita il
  JSON della singola esecuzione.
- D-004 sull'ordine di acquisizione: l'ordine operativo non è più CD4-primo.

## 8. Domanda di comprensione

Perché scaricare il blocco TGFB di Jiang su questa macchina violerebbe una
decisione già attiva, anche se 2,6 GB «sembrano» stare in 11 GiB liberi?
