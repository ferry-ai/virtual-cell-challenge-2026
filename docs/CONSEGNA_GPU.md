# Consegna alla macchina con GPU del compagno di squadra

Data: 2026-09-15. Questo documento dice **che cosa trasferire, che cosa lanciare e
che cosa la GPU accelererà davvero**. La risposta breve alla terza domanda è
scomoda e sta nella sezione 1: sul codice di oggi, niente.

Misure in `reports/gpu_2026-09-15/gpu_readiness.json`, prodotte da
`scripts/59_gpu_readiness.py` su questa macchina a carico scarico.

## 1. La GPU non accelera il codice attuale, ed è misurato

| Passo numerico | Chi lo esegue | Può usare una GPU? |
|---|---|---|
| Base SVD mascherata | `numpy.linalg.svd` (LAPACK gesdd) | **no** |
| Ridge | `numpy.linalg.solve` | **no** |
| MLP avanti/indietro e Adam | matmul numpy **scritti a mano** in `models.py` | **no** |
| Trasferimento con shrinkage | numpy elementwise | **no** |
| Costruzione dei descrittori | ciclo Python + `concatenate` | **no** |
| Caricamento delle firme | decompressione npz | no, è I/O |
| Generazione dei conteggi | `numpy.random.Generator.poisson` | **no** |
| **Sei metriche VCC** | `cell-eval2`, backend DE | **sì**, `gpudge` se c'è CUDA |

Verificato, non dedotto: in tutto `src/` non esiste nessun `import torch`, `cupy`
o `jax` che tocchi un modello. L'unico `import torch` sta in
`src/vcc2026/evaluation.py` e serve a **chiedere se esiste CUDA**, per scegliere
il backend dello scorer. `torch` non è nemmeno fra le dipendenze del progetto.
Su questa macchina: `torch` non installato, `cupy` no, `jax` no, `gpudge` no,
`pdex` no, CUDA non disponibile. numpy gira su `scipy-openblas 0.3.34`, che è
BLAS multi-thread su CPU.

E anche se lo fosse: al formato del pilot il calcolo che una GPU potrebbe
prendersi è **1,3 s** (fit dei due decoder) su un run di **223 s**. Non c'è
niente da accelerare perché non c'è niente che pesi.

## 2. Il collo di bottiglia vero è algoritmico, non hardware

La SVD è l'unico passo che cresce male. Misurato su matrici di risposta **reali**
(firme HepG2, 9.023 geni misurati):

| Righe | SVD completa | SVD randomizzata rango 16 | Guadagno | Errore relativo sui valori singolari |
|---:|---:|---:|---:|---:|
| 320 | 0,858 s | 0,072 s | **11,9×** | 1,6 % |
| 1.280 | 6,191 s | 0,147 s | **42,2×** | 1,3 % |

E su rumore gaussiano, che è il caso peggiore per il metodo randomizzato, a 5.120
righe la completa costa **142 s** contro 0,55 s, cioè 260×, con il 10% di errore.

Il punto: `MaskedLowRank.fit` calcola **tutti** i valori singolari per tenerne
16. Passare a una SVD randomizzata di rango 16 vale fra 12× e 42× su CPU, con un
errore dell'1,5% sui dati veri. È più di quanto una GPU darebbe su queste forme,
costa una funzione, e non richiede hardware. **Va fatto prima di comprare o
occupare una GPU**, altrimenti si sposta su un acceleratore un calcolo che non
serviva fare.

Un secondo numero, che non riguarda la velocità ma l'ipotesi modulare: sulle
matrici reali il rango 16 cattura il **25–30%** della varianza. La «base di
programmi condivisi» a quel rango lascia fuori i due terzi.

## 3. Che cosa una GPU accelererebbe davvero, oggi

Una cosa sola: il **backend DE dello scorer**. `cell-eval2` sceglie
`gpudge` (CUDA) > `pdex` > `scanpy`. Qui ha risolto a `scanpy`, il più lento dei
tre, perché gli altri due non sono installati e CUDA non c'è. Questo tocca la
**valutazione**, non l'addestramento — ed è la metà lenta dell'esperimento
generatore × predittore: il run da 25 bersagli e 6 combinazioni ha passato la
maggior parte del tempo dentro il DE.

Quindi il lavoro che ha senso mandare sulla GPU del compagno è
**l'esperimento sulle sei metriche, ampliato**, non il benchmark pseudobulk.

## 4. Che cosa trasferire

Nessuno di questi file sta nel repository (D-001): vanno copiati a parte.

| Cosa | Da dove | Byte | Serve per |
|---|---|---:|---|
| Firme pseudobulk | `<data_root>/artifacts/e001/signatures/` | 518 MiB | benchmark |
| Firme HepG2 | `<data_root>/artifacts/e003/signatures/` | 182 MiB | benchmark |
| Profilo basale HepG2 | `<data_root>/artifacts/e003/signatures/nadig_hepg2.control_profile.npz` | incluso sopra | benchmark |
| Tabella GO slim | `<data_root>/artifacts/g001/go_slim_table.npz` | 32.489 | solo per rifare il pilot scartato |
| HepG2 a singola cellula | `<data_root>/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad` | 850.590.740 | **solo** per le sei metriche |
| Controlli ufficiali | `<data_root>/raw/controls/` | 632 MiB | solo per una sottomissione |

Il repository si clona; `configs/` e `scripts/` viaggiano con lui.
`VCC2026_DATA_ROOT` punta alla cartella dati sulla macchina di destinazione.

**Verificare dopo il trasferimento**, non prima: `NadigOConner2024_hepg2.h5ad`
deve avere md5 `af2be47f7477cf32fa6e4bec1c6a4868`. È l'unico file la cui
integrità abbiamo verificato contro il pubblicatore, e un trasferimento lungo è
esattamente il momento in cui si corrompe.

## 5. Dipendenze

`requirements.txt` non cambia: è ciò che serve per far girare tutto, GPU o no.
Per la GPU si aggiunge `requirements-gpu.txt`, che **non** contiene `torch` per i
modelli — contiene ciò che rende più veloce lo scorer.

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
python -m pip install -r requirements-gpu.txt      # solo sulla macchina con CUDA
```

Dopo l'installazione, la verifica che conta (non fidarsi del fatto che la scheda
esista):

```bash
python scripts/59_gpu_readiness.py --out reports/gpu_<macchina>_<data>
```

Va letto `de_backend_resolved` nel JSON: se dice ancora `scanpy`, la GPU non sta
entrando nello scorer e il resto è inutile.

## 6. I comandi

Tutti riproducibili, tutti con un `--run-id` nuovo, nessuno sovrascrive niente.

**Benchmark a tre contesti** (CPU; la GPU non lo tocca):

```bash
python scripts/51_run_modular_pilot.py --run-id m005 --config configs/benchmark_3ctx.yaml --signatures <data_root>/artifacts/e001/signatures <data_root>/artifacts/e003/signatures
```

**Pilot dei descrittori GO slim** (CPU; 223 s e 345 MiB di picco qui):

```bash
python scripts/51_run_modular_pilot.py --run-id g003 --config configs/benchmark_go_slim.yaml --signatures <data_root>/artifacts/e001/signatures <data_root>/artifacts/e003/signatures
```

**Generatore × predittore sulle sei metriche** — questo sì usa la GPU, tramite lo
scorer. Prima servono le predizioni salvate:

```bash
python scripts/51_run_modular_pilot.py --run-id m006 --config configs/benchmark_3ctx_hepg2_predictions.yaml --signatures <data_root>/artifacts/e001/signatures <data_root>/artifacts/e003/signatures
```

```bash
python scripts/57_generator_x_predictor.py --predictions <data_root>/artifacts/m006/models/new_context_seen_target_k562_rpe1_to_hepg2_seed2026 --arms shrunk_transfer modular_frozen --n-targets 100 --cells-per-target 100 --ntc-cells 1000 --out reports/generator_<macchina>_<data>
```

I numeri di quest'ultimo comando sono quattro volte quelli girati qui (25
bersagli, 40 cellule, 400 NTC), ed è l'unico ampliamento che questo documento
propone: la tabella §5.6 di `BENCHMARK_TRE_CONTESTI.md` ha differenze grandi e
numerosità piccola, e il gate del DE le aveva già ridotte a 13 bersagli su 25
sulla colonna NMAE.

## 7. Che cosa non fare ancora

- **Nessuna migrazione su Kaggle o Colab.** Non è stata avviata e non va avviata:
  `notebooks/kaggle_package_trial01.ipynb` resta documentato e non eseguito.
- **Nessun porting a torch dei quattro modelli** prima di aver sostituito la SVD
  completa con quella randomizzata e rimisurato. Sono ~350 righe e il test di
  round-trip salvataggio/caricamento deve continuare a passare bit per bit,
  altrimenti i confronti con m001–m004 si rompono.
- **Nessun acquisto di capacità** per un lavoro non ancora deciso: vale ancora
  ciò che dice `ESECUZIONE_REMOTA.md` §4.
