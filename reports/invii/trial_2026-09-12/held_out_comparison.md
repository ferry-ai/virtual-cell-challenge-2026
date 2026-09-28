Confronto fuori campione — trial-01-transfer
============================================

Eseguito il 2026-09-12, run `c002`. Evidenza:
[`calibration_c002.json`](calibration_c002.json),
[`fitted_state_c002.json`](fitted_state_c002.json),
[`manifest_44_calibrate_transfer.json`](manifest_44_calibrate_transfer.json).
Comando:

```powershell
.\scripts\py.cmd scripts/44_calibrate_transfer.py --run-id c002 `
    --signatures C:\Users\ferra\vcc2026-data\artifacts\e001\signatures `
    --outer-folds 5 --inner-folds 4 --n-boot 1000
```

> **Queste sono metriche proxy, non punteggi VCC.** Tutto quanto segue vive nello
> spazio pseudobulk log2FC di K562 e RPE1. La gara valuta conteggi a singola cellula
> contro le cellule di controllo **reali** dei contesti A/B/C, dove nessuna
> perturbazione è osservabile. Nessun numero di questa pagina si converte in un
> punteggio di leaderboard, e non esiste una conversione misurata fra i due.

## 1. Il disegno

Esperimento di sviluppo **esterno**: sorgente `k562_gwps` (Replogle 2022 K562
genome-wide, pseudobulk), destinazione `rpe1_essential` (RPE1, linea diversa). La
sorgente è la stessa che verrà poi usata per A/B/C, ed è questo che rende
l'esperimento informativo sul *metodo*: 2.350 bersagli condivisi, 6.714 geni
condivisi (intersezione fra i 7.681 osservati dalla sorgente e gli 8.260 della
destinazione).

**Protocollo annidato.** Il ciclo esterno serve solo a riportare, quello interno solo
a scegliere. Per ogni fold esterno: `prior_sd` è scelto per errore in validazione
incrociata *dentro* i bersagli di training, `alpha` è poi rifittato in forma chiusa su
tutti quei bersagli, e la coppia è applicata alla cieca ai bersagli tenuti fuori. Ogni
bersaglio riceve quindi esattamente una previsione fatta con parametri scelti senza di
lui, e il bootstrap ricampiona quell'insieme fuori campione — non tutti i bersagli con
i parametri già scelti, che è ciò che faceva lo stadio 41.

**Controlli di fuga, misurati non assunti.**

- Le guide di un bersaglio sono collassate *prima* dello split, quindi il bersaglio è
  l'unità di divisione. In questa coppia la mediana è di 1 guida per bersaglio, quindi
  la protezione morde poco qui: conta per sorgenti con più guide per bersaglio.
- La maschera genica condivisa non porta informazione sui bersagli tenuti fuori: la
  copertura per bersaglio è **costante** dentro ciascuna sorgente (verificato, campo
  `coverage_constant_both_sides: true`), quindi la maschera è una proprietà dei due
  dataset. Se non lo fosse, lo script si fermerebbe.
- Nessuna risposta di riferimento tenuta fuori entra nella scelta dei parametri, e non
  esiste una base di risposte da fittare in questo modello.

## 2. I numeri

### Parametri scelti, per fold esterno

| Fold | α scelto | `prior_sd` | MSE/nullo tenuto fuori | Pearson mediana |
|---|---:|---:|---:|---:|
| 0 | 0,1947 | 4 | 0,98929 | 0,0864 |
| 1 | 0,2006 | 4 | 0,99135 | 0,0933 |
| 2 | 0,1971 | 4 | 0,98947 | 0,0966 |
| 3 | 0,1970 | 4 | 0,98959 | 0,0999 |
| 4 | 0,1975 | 4 | 0,98981 | 0,0970 |

α varia fra 0,1947 e 0,2006 su cinque fold indipendenti: la scelta è stabile.
`prior_sd` esce 4 in tutti e cinque.

### Confronto fuori campione

| Modello | MSE / MSE del nullo | Note |
|---|---:|---|
| **selezionato** (α ≈ 0,197, `prior_sd` = 4) | **0,98991** | IC95 bootstrap [0,98866, 0,99114] |
| risposta prevista zero (il nullo) | 1,00000 | per definizione |
| trasferimento a piena ampiezza (α = 1, senza shrinkage) | 1,16228 | **peggiore del nullo del 16,2%** |

| Statistica fuori campione | Valore | IC95 (bootstrap su bersagli) |
|---|---:|---|
| Pearson mediana per bersaglio | 0,0931 | [0,0879, 0,0992] |
| frazione di bersagli con Pearson > 0 | 0,933 | — |
| Spearman mediana | 0,0798 | — |
| cosine mediana | 0,0905 | — |
| accordo di segno sui geni \|Δ\|≥0,5 | 0,5558 | — |
| geni "forti" mediani per bersaglio | 1.375 | — |

Bootstrap su 1.000 ricampionamenti dei 2.350 bersagli fuori campione. L'unità è il
bersaglio, mai la cellula.

### Costo

| | Valore |
|---|---|
| tempo totale | 27,6 s |
| picco di memoria (working set) | 1,79 GiB |
| RAM disponibile misurata prima del run | 1,58 GiB |

Il picco supera la RAM *disponibile* misurata e il run è comunque riuscito: su Windows
la memoria libera riportata esclude la cache di file, che viene sfrattata. Il margine
però non c'è, ed è il motivo per cui questo stadio carica una sorgente alla volta.

## 3. Che cosa dicono, e che cosa no

**Misura.** A piena ampiezza il trasferimento è peggiore del non prevedere nulla: MSE
1,162 volte quella del nullo. All'ampiezza scelta fuori campione l'MSE scende a 0,990,
cioè **una riduzione dell'errore quadratico dell'1,01%** rispetto a non prevedere
nulla. L'intervallo di confidenza [0,98866, 0,99114] non contiene 1, quindi il
guadagno è distinguibile da zero. È anche minuscolo.

**Misura.** α non è 0,25. Lo stadio 41 aveva riportato 0,25 perché quello era il punto
di griglia più vicino; la selezione continua dà 0,197. La differenza è praticamente
irrilevante — sul fold 0, α = 0,25 dà 0,98964 contro 0,98929 del valore selezionato —
ma il numero da trasportare è quello misurato, non quello della griglia. Questo
conferma la regola di D-012 e corregge il *valore* che circolava.

**Misura.** Lo shrinkage per gene è quasi inattivo. Nella tabella di selezione interna
`prior_sd` = 4 batte «nessuno shrinkage» (`prior_sd` = 10⁶) di 0,00003 in MSE
cross-validata: una parità. Con SE mediana 0,175 e `prior_sd` = 4 il peso per gene è
16/(16+0,03) ≈ 0,998, cioè non tocca nulla. **Il lavoro lo fa tutto l'ampiezza
globale.** La compressione utile non è "per gene secondo la precisione", è "tutta la
risposta, di un fattore cinque".

**Interpretazione.** Un fattore di attenuazione intorno a 0,2 su una sorgente la cui
stima mediana è più piccola del proprio errore standard (|Δ|/SE mediano 0,795,
`reports/pipeline/signature_qc.json`) si legge come correzione per errore di misura
più distanza di lignaggio. Non lo dimostra.

**Ipotesi, non misura.** Che α ≈ 0,197 e `prior_sd` = 4 valgano per A, B e C. Sono
stati stimati su K562 e RPE1. Nei contesti ufficiali nessuna perturbazione è
osservabile, quindi questa scelta **non è verificabile localmente** e resta
un'assunzione dichiarata. Ciò che trasferisce è il protocollo.

**Ipotesi, non misura.** Che una riduzione dell'1,01% di MSE pseudobulk corrisponda a
un qualunque punteggio VCC. Le sei metriche ufficiali sono riscalate contro la media
del contesto e un replicato reale, quattro dipendono da chiamate DE su conteggi a
singola cellula, e nessuna di esse è stata calcolata su effetti veri in questo
progetto.

**Un fallimento a battere il nullo sarebbe stato un risultato valido.** Qui il nullo è
battuto, ma dell'1%: la lettura corretta non è «il trasferimento funziona», è «il
trasferimento, compresso, non fa danno e aggiunge quasi niente». Il trial resta utile
come test operativo del percorso di sottomissione, e va etichettato così.

## 4. Confronto con CP-0003

| | CP-0003 (stadio 41) | Qui (stadio 44) |
|---|---:|---:|
| α riportato | 0,25 (griglia) | 0,1974 (continuo) |
| α oracolo | 0,216 | — (la selezione *è* il minimizzatore) |
| MSE/nullo tenuto fuori | 0,990 | 0,98991 |
| MSE/nullo a α = 1 | 1,162 | 1,16228 |
| Pearson mediana | 0,0947 | 0,0931 |
| IC95 Pearson | [0,0891, 0,0997] su **tutti** i bersagli | [0,0879, 0,0992] su bersagli **fuori campione** |
| Protocollo | un solo livello di fold | annidato: interno seleziona, esterno riporta |
| Tempo | 288 s | 27,6 s |

I numeri coincidono nella sostanza. Le due differenze che contano sono metodologiche:
l'intervallo qui è calcolato su previsioni fuori campione invece che su tutti i
bersagli con i parametri già scelti, e il valore di α è il minimizzatore invece del
punto di griglia. Il calo di tempo da 288 s a 27,6 s viene dall'aver precalcolato tre
prodotti scalari per bersaglio invece di ricostruire la matrice di previsione a ogni
fold; non cambia nessun risultato.

## 5. Stato salvato

`fitted_state_c002.json` contiene tutto ciò che serve a ricostruire il modello:
`alpha`, `prior_sd`, `collapse_guides`, l'id della sorgente, e sha256 più dimensione
del file di firme su cui i parametri sono stati scelti. Lo stadio 45 rifiuta di girare
se lo sha256 delle firme non corrisponde, perché parametri scelti su un insieme di
firme e applicati a un altro sarebbero silenziosamente sbagliati.
