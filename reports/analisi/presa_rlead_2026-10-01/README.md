# Presa in carico di R-LEAD sulla macchina del teammate

1 ottobre 2026, dalle 16:54 CEST (ora del primo preflight). Claude Code (Opus 5.5) per Alfredo,
sessione `42343bb9-c8d1-4b93-a9cc-2008dd008900`, su incarico del prompt di consegna
([CONSEGNA_TEAMMATE](../../../docs/CONSEGNA_TEAMMATE.md)). Branch `codex/teammate-rlead` da `1f086cb`.
Il codice corretto sta in [cellnet_rlead_2026-10-01](../../modelli/cellnet_rlead_2026-10-01/README.md).

**In breve.**
- *Misurato:* l'ambiente di progetto funziona su questa macchina. Ci sono Python 3.12, lo scorer
  `cell-eval2` 0.16.0 con l'API usata dal banco e la GPU.
- *Misurato:* tre analisi dell'audit e i controesempi riprodotti danno valori identici a quelli
  originali.
- *Implementato:* le correzioni del passo A, provate su dati sintetici.
- *Misurato:* su questa macchina non c'è ancora nessun dato reale. Nessun training, confronto o
  score è stato eseguito.

## 1. Ambiente

| Voce | Misura | Fonte |
|---|---|---|
| Sistema | Windows 11 Home 10.0.26200, i9-13980HX (24 core, 32 thread), 15,7 GB di RAM, circa 6 GB liberi alla misura | `ambiente_r1/validate_runtime_py312.json` |
| Disco | C: 998 GB, 87 GB liberi dopo l'installazione | idem |
| GPU | RTX 4080 Laptop, 12 GB; CUDA 12.6 da torch 2.14.1+cu126, prodotto di matrici su GPU riuscito | verifica in sessione |
| Radice dati | `VCC2026_DATA_ROOT=C:\Users\39346\vcc2026-data`, fuori dal clone; `paths().data_root` la risolve; `py.cmd` e `vcc.cmd` usano il suo venv | `ambiente_r1/preflight_py312_progetto.json` |
| Python | 3.12.10 (winget, utente) invece del 3.12.3 del lock; pacchetti installati da `requirements.lock.txt` con le versioni esatte | idem |
| Scorer | `cell_eval2.config` importato dal venv; `de_tools.scorer_config()` dà `EvalConfig(metrics='vcc2026', …)`; API private e aggregazione presenti | idem, `validate_runtime` |
| H5AD | Round trip CSR: conteggi interi, identità, maschera dei geni misurati, zero distinto da non misurato, lettura a righe | `validate_runtime` |
| Pacchetti assenti | decoupler, harmonypy, pertpy, pyarrow, requests, scvi-tools: non sono nel lock e nessun passo eseguito qui li usa | idem |

La prima prova era su un venv provvisorio con Python 3.13 (`ambiente_r1/*py313*`). Lì mancavano
`cell_eval2`, `sklearn`, `polars` e `httpx`, e un test di streaming falliva per una differenza di
2,6 × 10⁻⁸ fra somme. Nel venv di progetto non si ripete. Nessun pacchetto è stato riparato a mano.

**Suite di progetto** (`py.cmd -m unittest discover -s tests`, Python 3.12): 287 test.
- **244 passano.**
- **42 sono saltati:** chiedono il bundle dei controlli ufficiali.
- **1 fallimento iniziale:** il controllo documentale, per le cartelle nuove non ancora registrate.
  Dopo le righe nel registro `31_check_docs.py` passa.

Due test di `test_live_tree` leggono l'elenco dei file tracciati da Git. Falliscono finché le
cartelle nuove non sono committate; dopo il commit passano. È lo stesso caso già annotato
nell'audit (`lead_audit_2026-10-01/VERIFICHE.md`).

**Test accanto ai report** (la suite generale non li include):

| Insieme | Python 3.12 di progetto | Python 3.13 provvisorio |
|---|---|---|
| Rete originale (`risposta_biologica_2026-09-30`: cell_data, prepass, pi_floor, read_csr) | 53 OK | 53 OK |
| Corpus (`corpus_cellulare_2026-09-30`) | non ripetuto | 10 OK |
| Versione corretta: 51 test originali e 15 nuovi | 66 OK | 66 OK |

I log sono in `ambiente_r1/test_cellnet_*_py312.log`, `ambiente_r1/suite_py312.log` (prima dell'indice Git: 2 fallimenti di `test_live_tree`) e `ambiente_r1/suite_py312_dopo_commit_indice.log` (287 test, OK, 42 saltati).

## 2. Input e accessi, per passo

Inventario con `inventory.py --no-drive` sulla radice nuova (`inventario_r1/`): **tutti i percorsi
locali di `sources.yaml` mancano**. Le frasi di classificazione stampate dallo script vengono dai
livelli dichiarati in `sources.yaml`, non dai file trovati.

| Passo | Input necessari | Leggibili qui | Accesso | Blocca |
|---|---|---|---|---|
| A, correzioni | codice, fixture sintetiche, output r2/r3 versionati | sì | Git | nulla |
| A, misure reali | conteggi HepG2 (850.590.740 byte, SHA256 nel manifest dell'audit); shard del corpus | no | Zenodo 13350497 (pubblico); Kaggle `davidmaisterx/rlab-*` (13 dataset del lancio r3, privati) | misura dei controlli e degli split sul corpus reale |
| B, banco a più contesti | shard per contesto e studio, manifest dei prepass r5/r7, descrittori | solo i manifest | Kaggle privato | il banco congelato su dati reali |
| C, modello ibrido | come B; GPU | GPU sì, dati no | Kaggle privato; quota cloud da autorizzare se serve | confronti su dati reali |
| D, dati ponte | CD4, HIPSCI, Orion, VIPerturb | no | download da autorizzare (licenze diverse, Orion CC BY-NC-SA) | ablation dei dati |
| E, generatore e sei membri | controlli ufficiali A/B/C, asse dei 18.533 geni, scorer | scorer sì, controlli no | portale della gara (login del proprietario o del teammate) | i 42 test saltati e ogni banco a sei membri |
| F, produzione | tutto il precedente; `vcc-cli` | `vcc-cli` 0.2.0 sì | come E | prova a forma piena |

H1 test non è stato aperto né cercato. Pesi e `model.pt` di r2/r3 non sono nel clone, come
dichiarano i loro manifest.

## 3. Prove dell'audit riprodotte

Stessi script, codice al commit `1f086cb`, cartelle nuove; confronto valore per valore.

| Prova | Valori confrontati | Esito |
|---|---|---|
| `reproduce_findings.py` → `counterexamples_r1/` | 9 | identici: gradiente nullo dell'embedding unknown, gradiente della base dalle perturbate, G2 chiamato C dopo l'esclusione della sua fonte |
| `replay_sampler.py` → `sampler_r1/` | 46 | identici: K562 genome-wide al 32,61% invece del 16,67%; rapporto 256 del controesempio di fusione |
| `analyze_outputs.py` → `outputs_r1/` | 2.625 più il CSV per target | identici salvo l'ora di scrittura |
| `analyze_r3.py` → `r3_followup_r1/` | 1.189 | identici |
| `analyze_hepg2.py`, `analyze_design.py` | — | non eseguibili: manca il file grezzo HepG2 |

Il codice della rete al commit di base non è più quello di r2. `cellnet.py` e `train_cellnet.py`
hanno l'opzione `--pi-floor` (`39f451d`). `cell_data.py` è identico byte per byte. I controesempi
dipendono dal comportamento a `pi_floor = 0`, che è il default.

## 4. Matrice di applicabilità

| Problema | Nel codice di base | Riprodotto qui | Conseguenza | Correzione | Prova |
|---|---|---|---|---|---|
| 1. Split che cambiano con il corpus | `cell_data.splits`: `random.sample` sulla lista ordinata | sì, su etichette sintetiche (`Splits`, lato legacy) | r3 − r2 non attribuibile ai dati; i nuovi training non comparabili | decisione per hash e manifest congelato | `Splits`, 3 test |
| 1b. Classi prima del QC | `prepass`, classi da etichette prima dell'ammissione | sì, controesempio identico | C gonfiato con bersagli J | riclassificazione dopo l'ammissione | `ClassesAfterQC` |
| 2. Bilanciamento della loss | `loss = -(ll*w).sum()/w.sum()` | sì, replay r2 identico e replay sintetico | pesi effettivi diversi dal dichiarato | normalizzatore globale; S conta solo gli studi attivi | `LossWeights`, 3 test |
| 2b. Studi senza cellule | `study_weights` conta gli studi vuoti in S | sì, nel codice (nuovo) | con il normalizzatore per batch si annulla; con quello globale ridurrebbe la scala | S sugli studi attivi | idem |
| 3. Controlli | serbatoio per shard fuso in ordine; propria libreria solo con almeno 64 righe | sì su fixture (perdita delle librerie col serbatoio vecchio); HepG2 **non verificabile qui** | condizionamento fra librerie; peso delle cellule dipendente dall'ordine | bottom-k per libreria, minimo per libreria, report di copertura e fallback | `ControlPool`, 3 test |
| 4. Miscela sotto il clamp | `log(pi.clamp_min(1e-6))` | sì: derivata −1,71828 × 10⁻⁸ dal logit contro una positiva col clamp | il cancello non si riapre | `gate_logs` dal logit; compatibile con `--pi-floor` | `Mixture`, 2 test |
| 5. Baseline | unknown mai addestrato; base con gradiente dalle perturbate | sì, controesempi identici | confronto debole | braccio `generic` addestrato; ablation della base **non fatta** (passo C) | `GenericArm`, 2 test |
| 6. Valutazione | 400 gruppi più grandi; coseno top-200 senza esclusione del cis | sì su fixture (una chiave sola rappresentata) | contesti assenti; cis mescolato al trans | selezione stratificata con tabella; **manca** la versione trans e i sei membri | `EvaluationGroups` |

**Su `--pi-floor`** (lettura del codice, non un confronto): con il pavimento `pi ≥ floor` il clamp a
10⁻⁶ non è mai attivo, quindi il difetto del gradiente non si presenta. Il pavimento però impone una
quota minima di risposta anche ai veri non rispondenti. La miscela dal logit non ha questo
vincolo. Quale dei due prevenga meglio il collasso è un confronto del passo C da registrare prima.

## 5. Che cosa resta bloccato e la richiesta minima

1. **Dati reali, per le misure del passo A e per il passo B:** accesso Kaggle ai 13 dataset
   `davidmaisterx/rlab-*` del lancio r3. Il teammate dice di averlo; su questa macchina manca la
   chiave API, che la mette lui. Prima di scaricare servono i byte per dataset e un'autorizzazione
   in chat: il disco libero è 87 GB.
2. **Controlli ufficiali A/B/C**, per i 42 test saltati e per ogni banco a sei membri: dal portale
   della gara, con login fatto dal teammate.
3. **Job attivi di R-LAB e t29:** da confermare con il proprietario prima di creare altri job.

Il lavoro indipendente da questi blocchi continua: protocollo del banco, versione trans della
diagnostica, bilineare e ablation della base su fixture.

## 6. File di questa cartella

| Percorso | Contenuto |
|---|---|
| `ambiente_r1/` | preflight (Python 3.13 provvisorio e 3.12 di progetto), `validate_runtime`, log della prima suite |
| `inventario_r1/` | `inventory.py --no-drive` sulla radice nuova |
| `counterexamples_r1/`, `sampler_r1/`, `outputs_r1/`, `r3_followup_r1/` | riproduzioni dell'audit, ciascuna con il suo manifest |
| `*.log` | uscita degli script di riproduzione |
