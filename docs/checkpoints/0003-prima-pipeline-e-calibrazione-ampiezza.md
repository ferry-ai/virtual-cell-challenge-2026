# CP-0003 — Prima pipeline verticale e calibrazione dell'ampiezza di trasferimento

- **Data:** 2026-09-12
- **Tipo:** osservazione
- **Redatto da:** agente (Claude Opus 5)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Due domande, entrambe rimaste aperte dopo CP-0002.

1. **D-006**: conviene comprimere l'ampiezza delle previsioni, e di quanto? Finora era
   una postura argomentata, mai misurata.
2. Si può costruire un percorso verticale eseguibile — registry, ingestione, QC,
   firme, baseline, valutazione, report — con i soli dati già su disco, senza
   attendere lo sblocco di D-003?

## 2. Cosa è stato fatto

Aggiunto un pacchetto sotto `src/vcc2026/` (`genes`, `signatures`, `pseudobulk`,
`models`, `splits`, `evaluation`, `registry`, `manifest`), un registry versionato
delle fonti (`configs/sources.yaml`), tre stadi di pipeline e 42 test nuovi.
Nessun file esistente è stato spostato o cancellato; `config.py` è stato solo esteso.

```powershell
.\scripts\py.cmd scripts/40_build_signatures.py --run-id e001
.\scripts\py.cmd scripts/41_transfer_experiment.py --run-id e002 `
    --signatures C:\Users\ferra\vcc2026-data\artifacts\e001\signatures --n-folds 5 --n-boot 500
.\scripts\py.cmd scripts/42_null_calibration.py --run-id n003 --context A --n-pseudo 6
.\scripts\py.cmd -m unittest discover -s tests
```

Dati usati: solo materiale già locale — i tre pseudobulk Replogle e i controlli
ufficiali. Nessun download, nessun servizio a pagamento, nessun atlante.
Tempi misurati su questa macchina: stadio 1 254 s, stadio 2 288 s, stadio 3 392 s.
Risultati leggeri in `reports/pipeline/`; artefatti pesanti in
`C:/Users/ferra/vcc2026-data/artifacts/`.

## 3. Cosa si è osservato

### 3.1 Due difetti di lettura dei dati, entrambi silenziosi

**Il file `*_raw_bulk_01.h5ad` non contiene somme di conteggi ma medie per cellula.**
Le righe sommano a circa 12.000, la scala di una singola cellula, e
`X * num_cells_filtered` torna intera (deviazione massima 1,6·10⁻³, oltre il 99,9%
dei valori interi). Evidenza: `configs/sources.yaml`, campo `count_schema` di
`k562_gwps`, riprodotto in `src/vcc2026/pseudobulk.py`. L'audit precedente aveva
notato che i valori non erano interi
(`reports/candidate_verification/coverage_summary.json`,
`sample_fraction_noninteger` 0,9963) senza identificarne il divisore. Conseguenza
pratica: chi legge X come conteggi sottostima la precisione di un fattore pari al
numero di cellule — mediana 166 nel file genome-wide — e ogni errore standard di
Poisson che ne deriva è circa 13 volte troppo grande.

**Le colonne `var` di quei file usano la codifica categorica legacy di anndata**
(codici interi accanto a `var/__categories/<nome>`). Leggere i codici come valori
produce le stringhe "0", "1", … e **zero** corrispondenze con l'asse ufficiale. Il
difetto è stato visto perché il report di ingestione conta le esclusioni:
`n_axis_genes_observed: 0` con `n_source_genes_off_axis: 8246`. Dopo la correzione:
7.681 geni osservati per `k562_gwps`, che coincide con `genes_hit: 7681` misurato
indipendentemente dall'audit precedente.

### 3.2 Le firme sono dominate dal rumore nella loro stessa sorgente

`reports/pipeline/signature_qc.json`:

| Fonte | firme | bersagli | pannello | mediana \|Δ\|/SE | mediana geni \|z\|>2 | cellule mediane |
|---|---:|---:|---:|---:|---:|---:|
| k562_gwps | 2.816 | 2.659 | 272 | 0,795 | 851 | 166 |
| k562_essential | 2.167 | 2.048 | 0 | 0,835 | 813 | 117 |
| rpe1_essential | 2.509 | 2.354 | 0 | 0,945 | 71 | 71 |

Il rapporto mediano fra effetto ed errore standard è **sotto 1 in tutte e tre le
fonti**. L'SE qui è il solo pavimento di campionamento di Poisson: ignora la
variabilità biologica fra cellule e fra guide, quindi **sottostima** l'incertezza
vera, e i conteggi di `|z|>2` vanno letti come limiti superiori ottimistici (con
7.681 geni, il solo caso ne produrrebbe circa 350).

### 3.3 Gli effetti nel pseudobulk non sono piccoli

Misurato sulle firme collassate per guida, sui geni osservati:

| Fonte | \|log2FC\| ≥ 0,25 | ≥ 0,5 | ≥ 1,0 | ≥ 2,0 |
|---|---:|---:|---:|---:|
| rpe1_essential | 47,7% | 23,3% | 6,8% | 1,3% |
| k562_gwps | 27,5% | 8,1% | 1,2% | 0,13% |

Mediana di 1.848 geni oltre 0,5 log2FC per bersaglio in RPE1, 337 in K562.

### 3.4 Trasferire a piena ampiezza è peggio che non prevedere nulla

`reports/pipeline/transfer_experiment.json`. Protocollo: bersagli interi divisi in
5 fold; la griglia di shrinkage è cercata **solo** sui bersagli di training; i
numeri sono sui bersagli tenuti fuori; il bootstrap ricampiona bersagli.

| | K562 gw → RPE1 | K562 ess → RPE1 | K562 ess → K562 gw (stessa linea) |
|---|---:|---:|---:|
| bersagli condivisi | 2.350 | 2.017 | 2.042 |
| geni condivisi | 6.714 | 6.841 | 7.639 |
| α scelto (tutti i fold) | 0,25 | 0,25 | 0,50 |
| α oracolo | 0,216 | 0,265 | 0,472 |
| Pearson mediana (held-out) | 0,0947 | 0,0792 | 0,1693 |
| bootstrap IC95 | [0,0891, 0,0997] | [0,0734, 0,0839] | [0,1589, 0,1816] |
| **MSE/MSE-nullo, α=1** | **1,162** | **1,151** | **1,535** |
| MSE/MSE-nullo, α scelto | 0,990 | 0,984 | 0,922 |
| accordo di segno, \|Δ\|≥0,5 | 0,5555 | 0,5550 | 0,6496 |
| frazione con Pearson > 0 | 0,932 | 0,921 | 0,960 |

Tre fatti in questa tabella:

- **A piena ampiezza il trasferimento è peggio del nulla in MSE**, del 16% fuori
  linea e del 54% perfino dentro la stessa linea.
- **L'α scelto in validazione incrociata coincide con l'oracolo** (0,25 contro
  0,216; 0,50 contro 0,472). Il protocollo di selezione trova la risposta giusta:
  l'ampiezza è misurabile, non da indovinare.
- **L'α ottimo non è zero.** A 0,25 il trasferimento cross-lineage riduce l'errore
  quadratico dell'1,0% rispetto al non prevedere nulla; nella stessa linea del 7,8%.

Il riferimento di stessa linea inquadra il resto: la correlazione cross-lineage è
circa il **56%** di quella fra due esperimenti nella stessa linea cellulare, e
quest'ultima è essa stessa bassa (0,169).

### 3.5 Lo scorer vero gira, e il nullo è davvero nullo

`reports/pipeline/null_calibration_A.json`. Sei pseudo-perturbazioni costruite da
gruppi **disgiunti** di guide NTC del contesto A (300 cellule ciascuna contro 3.000
di controllo), effetto vero zero per costruzione; previsione generata attraverso lo
stesso `SubmissionWriter` e `sample_counts` di una sottomissione reale; punteggio con
`cell-eval2` 0.16.0.

| metrica | mediana | finite |
|---|---:|---:|
| `pds_cosine` | 0,500 | 6/6 |
| `de_wilcoxon_sig_jaccard` | 0,000 | 6/6 |
| `de_wilcoxon_direction_fidelity_yield_raw` | 0,369 | 6/6 |
| `de_wilcoxon_direction_reach_raw` | 1,000 | **1/6** |
| `expr_distance_unbiased` | 2,7·10⁻⁶ | 6/6 |

- `pds_cosine` vale esattamente 0,5: la discriminazione al caso, ancora utile.
- **`de_lfc_nmae` ha escluso 5 perturbazioni su 6 per "empty gate"** e la sesta per
  meno di 10 geni superstiti. Su dati reali NTC-contro-NTC, a questa profondità, il
  macchinario DE dello scorer **non produce quasi falsi positivi**.
- L'aggregazione di `expr_mse_unbiased_capped_norm` è stata **rifiutata**: la somma di
  `expr_distance_unbiased` sulle sei perturbazioni è −1,16·10⁻⁵, non positiva. È lo
  scorer che certifica l'assenza di effetto nel riferimento.

### 3.6 Due vincoli di contratto non documentati prima

- **Ogni etichetta di perturbazione deve risolversi a un gene dell'indice delle
  feature.** Con nomi inventati (`NTCGROUP0`) `cell-eval2` solleva un errore anziché
  non escludere nulla — la sua diagnostica lo chiama "the worst failure mode
  available to these metrics".
- **Il backend DE non è fissato dalla versione del pacchetto.** Qui si è risolto a
  `scanpy` (pdex assente, nessuna CUDA) e il pacchetto stesso avverte che "DE numbers
  differ between engines". Quattro delle sei metriche dipendono da questa scelta.
  Ora è registrata in `scorer_fingerprint()` accanto a ogni numero.

### 3.7 Hardware, rimisurato

7,81 GiB di RAM totali (0,76 GiB liberi durante le misure), 31,11 GB di disco libero,
8 thread su Intel i7-10510U. Il primo tentativo di costruire tutte le 9.866 firme di
K562 ha esaurito la memoria: una firma densa sull'asse ufficiale costa
18.533 × 4 byte per array, e servono due array più una maschera.

## 4. Interpretazione e incertezza

**Misura.** Tutti i numeri della sezione 3 sono ricalcolabili con i comandi della
sezione 2.

**Interpretazione.** L'α ottimo intorno a 0,22–0,27 fuori linea e 0,47 dentro la
stessa linea si legge naturalmente come un fattore di attenuazione: l'errore di misura
nella sorgente riduce la pendenza ottimale, e la distanza di lignaggio la riduce
ancora. Che l'α di stessa linea sia già solo 0,47 dice che gran parte della
compressione necessaria serve a compensare **il rumore**, non la biologia.

**Ipotesi, non misura.** Che questi α si applichino ai contesti A, B e C. Sono stati
stimati su K562 e RPE1; nessuna perturbazione dei contesti ufficiali è osservabile.
Il valore trasferibile è il *metodo* — calibrare α su bersagli tenuti fuori — non il
numero.

**Limite importante.** Tutto in §3.4 è in spazio pseudobulk log2FC. Non è un punteggio
VCC e non lo diventa: lo scorer vuole conteggi a singola cellula contro controlli
reali. La riduzione dell'1,0% di MSE cross-lineage, su 2.350 bersagli × 6.714 geni, è
quasi certamente significativa e praticamente minuscola; non va raccontata come "il
trasferimento funziona".

**Il nullo non è un benchmark.** §3.5 misura un pavimento di falsi positivi su dati
il cui effetto vero è zero. Un modello che "battesse il nullo" lì indicherebbe una
fuga di informazione, non una scoperta.

**Contraddizione parzialmente chiusa.** §3.3 misura effetti tutt'altro che piccoli in
RPE1 e K562. Non contraddice direttamente la catena corretta da CP-0002 (che
riguardava i contesti A/B/C, dove l'ampiezza resta ignota), ma toglie plausibilità
all'idea che gli effetti di un knockdown siano piccoli per costruzione.

## 5. Spiegazione semplice

Immagina di dover indovinare di quanto cambia la temperatura in una città B, sapendo
solo quanto è cambiata in una città A. Se le due città si somigliano poco, la cosa
sensata non è riportare pari pari il numero di A: è riportarne una frazione. Se A dice
"+10 gradi" e la relazione è debole, dire "+2,5" sbaglia meno che dire "+10".

Qui abbiamo misurato quella frazione invece di sceglierla: circa **un quarto** fra
linee cellulari diverse, **metà** fra due esperimenti nella stessa linea. E abbiamo
misurato la cosa che più conta: **copiare il numero intero è peggio che dire "non
cambia niente"**. Non di poco — del 16%.

Perché anche nella stessa linea serve dimezzare? Perché il numero di partenza è già
sporco. Con 166 cellule per riga, l'effetto medio misurato è più piccolo del suo
stesso margine d'errore. Si sta copiando in buona parte rumore, e il rumore va
attenuato.

## 6. Conseguenze

- `docs/DECISIONI.md`: **D-006 passa da `da-verificare` ad `attiva`**, riformulata sui
  numeri di §3.4. Nuove decisioni D-012 (calibrazione dell'ampiezza su bersagli tenuti
  fuori), D-013 (registry versionato come unica fonte sullo stato delle sorgenti),
  D-014 (backend DE registrato accanto a ogni metrica).
- **D-007 confermata**: K562 non è inutile, ma il suo contributo marginale misurato è
  dell'1,0% di MSE, e va confrontato con quello di CD4 prima di pesarlo.
- `docs/PROGETTO.md`: lo stato passa da "nessun modello allenato" a "baseline di
  trasferimento calibrate e valutate fuori campione, benchmark predittivo VCC ancora
  pendente"; aggiunte le due incertezze nuove (§3.6).
- `docs/REGISTRO.md`: nuove voci per `configs/sources.yaml`, `reports/pipeline/`,
  `reports/scorer_2026-09-12/` e i moduli aggiunti.
- Il collo di bottiglia **non** è cambiato: senza cellule perturbate reali non esiste
  un punteggio VCC. Ma non è più l'unico lavoro possibile.

## 7. Cosa corregge

Non corregge nessun checkpoint precedente. Aggiunge misure dove CP-0001 e CP-0002
dichiaravano incertezza, e corregge due letture dei dati mai messe per iscritto prima
(§3.1): la semantica di `X` nei file `raw_bulk` e la codifica categorica legacy.

Conferma esplicitamente, senza modificarle: le coperture misurate, i clamp dello
scorer, l'assenza dell'RNA di H1, i vincoli hardware, la distinzione fra pseudobulk e
valutazione a singola cellula, e il fatto che **nessuna sottomissione sia stata
inviata e nessun punteggio di leaderboard esista**.

Una precisazione su `reports/scorer/vcc2026_contract.json`: il suo campo `floor_note`
contiene ancora la formulazione "makes that metric downside-free", già corretta nel
codice di `scripts/17_extract_scorer_contract.py`. Il JSON resta come evidenza storica;
la versione corrente è in `reports/scorer_2026-09-12/vcc2026_contract.json`.

## 8. Domanda di comprensione

Un collega osserva che a α = 0,25 il trasferimento K562→RPE1 riduce l'MSE solo dell'1%
rispetto al non prevedere nulla, e propone di abbandonare K562. Che cosa gli mostri
prima di decidere, e quale numero di questo checkpoint rende la sua proposta
prematura?
