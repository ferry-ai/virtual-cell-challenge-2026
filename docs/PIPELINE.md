# La pipeline — architettura e come si esegue

Aggiornato il 2026-09-15 nella sola §5, dopo
[CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md); il resto è del
2026-09-13. Introdotta da
[CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md), estesa con gli
stadi 43–47 da [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) e con lo
stadio 48 da [CP-0005](checkpoints/0005-packaging-streaming-trial01.md).

Questo documento descrive **codice che esiste e che è stato eseguito**. I numeri che
produce stanno in `reports/pipeline/`; i comandi qui sotto li rigenerano.

## 1. Il percorso verticale

```
configs/sources.yaml                      registry versionato delle fonti
        │
        ▼  40_build_signatures.py         selezione → ingestione → QC → firme
<artifact_root>/<run>/signatures/*.npz    firme con Δ, SE, maschera, n_cellule
        │
        ├──▶ 41_transfer_experiment.py    split → baseline → calibrazione → report
        │    reports/pipeline/transfer_experiment.json
        │
        ├──▶ 42_null_calibration.py       bundle a singola cellula → scorer ufficiale
        │    reports/pipeline/null_calibration_A.json
        │
        └──▶ 44_calibrate_transfer.py     CV annidata → (alpha, prior_sd) + stato
             <run>/calibration.json, <run>/fitted_state.json
                     │
configs/trials.yaml  │                    definizione dei due trial
        │            │
        ▼            ▼
   43_freeze_trial.py                     commit, patch, dipendenze, hash, seed
        │
        ▼  45_generate_prediction.py       basale A/B/C → log2FC → conteggi → h5ad
<artifact_root>/<run>/prediction.h5ad     360.000 × 18.533, scritta a blocchi
        │            <run>/generation_diagnostics.json
        │            <run>/provenance_<contesto>.npz  (solo trial-00)
        │
        ▼  46_validate_package.py          contratto dal file + provenienza + vcc prep
<artifact_root>/<run>/validation.json     <run>/prediction.vcc, prep_*.log
        │
        ▼  47_resource_report.py           consolida il costo misurato dei run
reports/trial_2026-09-12/resources.json

<artifact_root>/<run>/prediction.h5ad
        │
        ▼  48_package_prediction.py        convalida a blocchi → payload → zstd → tar
<artifact_root>/<run>/prediction.vcc      + verifica contro l'input, array per array
             <run>/packaging.json
```

Ogni stadio scrive un manifesto (`manifest_<stadio>.json`) con percorsi, dimensioni,
hash, seed, configurazione risolta e versioni dei pacchetti. I manifesti **non si
sovrascrivono**: `RunManifest.write` solleva `FileExistsError`, e una riesecuzione va in
un `--run-id` nuovo. Lo stesso vale per ogni output.

## 2. I moduli

| Modulo | Responsabilità | Contratto che protegge |
|---|---|---|
| `config.py` | `data_root`, `artifact_root`, `run_dir` | niente percorsi Windows nei componenti nuovi |
| `genes.py` | asse ufficiale 18.533, allineamento, maschere | **D-009**: un gene non misurato ha una maschera, non uno zero |
| `signatures.py` | `Signature` (Δ, SE, maschera, n_cellule), combinazione per guida | l'incertezza viaggia con la stima; la replica non può restringere l'intervallo sotto il disaccordo osservato |
| `pseudobulk.py` | lettura dei file Replogle, censimento dei bersagli | semantica di `X` come media per cellula; codifica categorica legacy; identità documentata dei controlli |
| `models.py` | nullo, trasferimento con shrinkage, pesato, ridge a basso rango | un bersaglio sconosciuto resta mascherato, non diventa uno zero sicuro |
| `splits.py` | bersagli / donatori / contesti tenuti fuori, bootstrap | tutte le guide di un bersaglio stanno dallo stesso lato; il bootstrap ricampiona bersagli, mai cellule |
| `evaluation.py` | metriche proxy su Δ; scorer `cell-eval2` | proxy e punteggio VCC non si confondono; il backend DE è registrato |
| `registry.py` | livelli di verifica, copertura in tre campi | una fonte non può essere abilitata sotto `sample_verified` |
| `manifest.py` | impronta di input, output, ambiente | un risultato senza manifesto non è riproducibile |
| `inference.py` | profilo basale a blocchi, log2FC → conteggi, maschere di supporto, provenienza dei contesti | **D-015**: il vincolo compositivo si assorbe sui geni supportati, così un gene senza evidenza realizza esattamente zero |
| `resources.py` | RAM, disco, memoria di picco, `require()` | un job che non finirebbe si rifiuta prima, invece di lasciare un file troncato |
| `trials.py` | definizione dei trial da `configs/trials.yaml` | freeze, generazione e packaging leggono lo stesso oggetto: un run non può contraddire il trial che dichiara |
| `submission.py` | scrittura a blocchi, larghezza degli offset CSR | gli offset di una sottomissione completa arrivano al 97% del tetto di int32: la larghezza si sceglie dal conteggio, non si assume |
| `packaging.py` | convalida e `.vcc` senza materializzare la matrice | **D-018**: le convalide sui metadati sono quelle ufficiali, importate; un layout che il packager non sa preservare viene rifiutato, non approssimato |

I moduli preesistenti `external.py`, `sampling.py` e `remote_ranges.py` non sono stati
toccati; `config.py` è stato solo esteso; `signatures.py` ha acquisito un filtro per
bersagli in `read_npz`, retrocompatibile. `submission.py` è stato **corretto** il
12 settembre: scriveva gli offset CSR in int32 e una sottomissione completa arriva al
97% di quel tetto ([CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.6).
Gli script da 01 a 31 continuano a funzionare come prima.

## 3. Eseguire

Prerequisiti: il bundle dei controlli spacchettato in `data_root/raw/controls/` e i tre
pseudobulk Replogle in `data_root/external/`.

```powershell
# Stadio 1 — firme (circa 4 min qui, 3 sorgenti, 2.694 bersagli selezionati)
.\scripts\py.cmd scripts/40_build_signatures.py --run-id e001

# Stadio 2 — trasferimento e calibrazione dell'ampiezza (circa 5 min)
.\scripts\py.cmd scripts/41_transfer_experiment.py --run-id e002 `
    --signatures <artifact_root>\e001\signatures --n-folds 5 --n-boot 500

# Stadio 3 — scorer ufficiale su un bundle nullo (circa 6 min)
.\scripts\py.cmd scripts/42_null_calibration.py --run-id n003 --context A --n-pseudo 6

# Stadio 4 — calibrazione annidata, sostituisce lo stadio 2 per questo scopo (28 s)
.\scripts\py.cmd scripts/44_calibrate_transfer.py --run-id c002 `
    --signatures <artifact_root>\e001\signatures --outer-folds 5 --inner-folds 4

# Stadi 43, 45, 46, 47, 48 — un trial completo, dal freeze al .vcc. I comandi
# esatti, con i percorsi di questa macchina, stanno in docs/SOTTOMISSIONE.md
# sezioni 3 e 7.

# Parità del packaging con vcc prep (46 test su fixture a forma ufficiale, 98 s)
.\scripts\py.cmd -m unittest tests.test_packaging_parity

# Contratti
.\scripts\py.cmd -m unittest discover -s tests
python scripts/31_check_docs.py
```

`--signatures` esiste perché le firme sono costose e immutabili: un esperimento nuovo
le riusa invece di ricostruirle. È anche il motivo per cui una macchina remota può
calcolare le firme una volta e rispedire una sola cartella.

## 4. Scelte che vale la pena conoscere prima di modificare il codice

**Perché la selezione dei bersagli viene prima dell'ingestione.** Una firma è densa
sull'asse ufficiale, quindi la memoria cresce linearmente col numero di bersagli:
tutte le 9.866 righe di K562 sarebbero circa 2,93 GB fra Δ e SE in float64 (3,11 GB
con la maschera), su una macchina da
7,8 GB. `select_targets` usa un censimento che legge solo `obs` (0,13 s) per decidere
che cosa materializzare. Il default `panel+shared` tiene il pannello più ogni bersaglio
misurato da almeno due fonti — cioè esattamente l'insieme su cui il trasferimento si
può *misurare* anziché assumere.

**Perché l'ampiezza si sceglie sull'MSE e non sulla correlazione.** La correlazione è
invariante di scala: è indifferente ad α e non può sceglierne uno. Nella griglia, per
ogni `prior_sd` l'MSE aggregato è una quadratica in α, quindi tre prodotti scalari
valutano l'intera griglia in forma chiusa — il che ha anche eliminato il collo di
bottiglia che rendeva lo stadio 2 impraticabile.

**Perché il nullo usa nomi di geni veri.** `cell-eval2` 0.16.0 pretende che ogni
etichetta di perturbazione si risolva a un gene dell'indice delle feature: con nomi
inventati solleva un errore, perché non escludere nulla «would otherwise return a
plausible wrong number». Le pseudo-perturbazioni sono quindi etichettate con simboli
del pannello, il che esercita anche l'esclusione per pannello della configurazione
ufficiale.

**Perché lo split è sulle guide NTC e non sulle cellule.** Cellule che condividono una
guida condividono il suo batch di cattura e ogni artefatto specifico di quella guida:
uno split a livello di cellula sottostimerebbe il pavimento di falsi positivi.

## 5. Che cosa la pipeline non fa

- **Non produce un punteggio VCC su effetti veri.** Lo stadio 3 gira lo scorer vero, ma
  su un riferimento il cui effetto è zero per costruzione. Serve a misurare il
  pavimento di falsi positivi e a verificare il percorso di sottomissione, non a
  dimostrare capacità predittiva.
- **Non normalizza i punteggi sulla scala della gara.** La formula è
  `(u − b) / (r − b)` con `b` baseline pubblicata e `r` ancora di replicato: non
  abbiamo né `b` né `r`, quindi `score_bundle` restituisce metriche grezze e marca
  `normalized: false`.
- **Non ingerisce ancora CD4 né Orion.** Sono nel registry a `pilot_ingested` e
  `sample_verified`, `enabled: false`. Lo stadio 1 legge solo fonti `usable` con un
  percorso locale.
- **Non allena un modello generativo di conteggi.** Deliberatamente: prima una stima
  di risposta calibrata e onestamente validata. Il generatore di conteggi è un
  campionatore Poisson dal profilo previsto, e il suo artefatto è misurato, non
  assunto: 2,1–6,3% di geni rilevati in più dei controlli reali anche a effetto previsto
  zero ([CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.8).
- **Impacchetta**, dallo stadio 48, senza materializzare la matrice: 0,519 GiB di
  picco contro i 33,49 che il modello della CLI attribuisce a `vcc prep`
  ([CP-0005](checkpoints/0005-packaging-streaming-trial01.md)). Le convalide non sono
  indebolite — quelle sui metadati sono le funzioni ufficiali, chiamate direttamente —
  e i layout che non sa preservare li rifiuta invece di approssimarli (D-018).
- **Non invia niente, e non è lo stadio che ha inviato.** Nessuno stadio parla con la
  rete della gara: la sottomissione del 2026-09-13 è passata da `vcc submit`, a mano,
  con i comandi di `docs/SOTTOMISSIONE.md` §3. Che il server accetti l'archivio non è
  più una riserva — l'entry `PNn227rxP3bVByS37W41` è arrivata a `published` e ha un
  punteggio ([CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md)) — ma
  resta un'affermazione sul **formato**: la pipeline non produce da sé un punteggio
  VCC su effetti veri, che è il primo punto di questo elenco.
