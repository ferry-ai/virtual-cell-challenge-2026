# Benchmark a tre contesti: K562, RPE1, HepG2

Data: 2026-09-14. Questo documento distingue **acquisito**, **implementato**,
**eseguito**, **misurato** e **ancora ipotizzato**. Non adotta un'architettura,
non dichiara un vincitore e non produce un punteggio di gara.

Continua [BENCHMARK_MODULARE.md](BENCHMARK_MODULARE.md), che misurava la stessa
cosa con due contesti. La differenza che conta è una sola: con due contesti
perturbati, tenerne fuori uno lasciava **un** contesto di training, il
descrittore di contesto era una colonna costante e un confronto con/senza
contesto non poteva identificare niente. Era la condizione di riapertura scritta
in D-025. Adesso i contesti sono tre.

Punto di ingresso dei numeri: `reports/hepg2_2026-09-14/` per l'acquisizione e
l'audit, `reports/benchmark_3ctx_2026-09-14/` per il confronto. I run completi
stanno in `C:/Users/ferra/vcc2026-data/artifacts/` (D-001): `e003` per le firme
HepG2, `m002` per il benchmark a tre contesti, `m003` per il solo fold con HepG2
fuori e le predizioni salvate.

## 1. Acquisito

- **Che cosa:** `NadigOConner2024_hepg2.h5ad`, mirror scPerturb del deposito GEO
  GSE264667 (Nadig, O'Conner et al., CRISPRi Perturb-seq in HepG2).
- **Da dove:** `https://zenodo.org/api/records/13350497/files/NadigOConner2024_hepg2.h5ad/content`,
  record Zenodo 13350497, DOI `10.5281/zenodo.13350497`, licenza dichiarata sul
  record **CC BY 4.0**. L'endpoint era già negli artefatti raccolti il 12
  settembre (`reports/grok_verification/scperturb_zenodo.txt`) ed è stato
  ricontrollato in diretta prima di scaricare: la voce del file corrispondeva
  byte per byte a quella in cache.
- **Verificato:** 850.590.740 byte ricevuti contro 850.590.740 dichiarati;
  md5 `af2be47f7477cf32fa6e4bec1c6a4868`, **uguale** a quello pubblicato.
  Richiesta di intervallo accettata (HTTP 206), quindi lo scaricamento era
  riprendibile. Evidenza: `reports/hepg2_2026-09-14/acquisition.json`.
- **Perché il mirror e non GEO:** la copia GEO dello stesso esperimento è un h5ad
  non compresso da 5,2 GB. Con 14 GiB liberi sul disco, prenderla avrebbe
  lasciato 8,8 GiB e violato D-005 (≥10 GiB liberi). Il mirror è lo stesso
  esperimento compresso a 0,85 GB. **Un mirror è una copia, non un secondo
  esperimento:** non va mai sommato all'originale né contato come replica.
- **Dove:** `C:/Users/ferra/vcc2026-data/raw/nadig_hepg2/`, fuori da OneDrive
  (D-001). Nessun file preesistente è stato sovrascritto. Nessun altro dataset
  completo è stato scaricato e nessun servizio a pagamento è stato usato.

## 2. Verificato nel contenuto

Fonte: `reports/hepg2_2026-09-14/nadig_hepg2_audit.json`, prodotto da
`scripts/52_audit_hepg2.py`, che legge `obs` e `var` per intero e campiona `X` a
blocchi. La matrice densa (5,6 GB) non viene mai materializzata.

Il report tiene separati **dichiarato**, **verificato** e **incerto**, perché in
questo repository il collasso fra i tre è il modo di sbagliare documentato.

| Voce | Valore | Come lo sappiamo |
|---|---|---|
| Forma | 145.473 cellule × 9.624 geni | attributo di `X` |
| Formato | denso float32, gzip, chunk 569×76 | attributi HDF5 |
| Altre matrici | nessuna: né `layers`, né `raw`, né `obsm` | chiavi del file |
| Conteggi | 3.072 cellule campionate: non negativi, **interi**, nessuna cellula a libreria zero, libreria mediana 15.778 | lettura dei valori |
| Coerenza | `obs.ncounts` ha mediana 15.487 sull'intero file | colonna dichiarata |
| Geni | 9.624 simboli, **nessun duplicato**, 9.023 sull'asse ufficiale da 18.533 | `var.gene_name` |
| Controlli | `obs.perturbation == 'control'`, 4.976 cellule | livelli osservati |
| Bersagli | 2.393 livelli perturbanti, mediana 45 cellule; 2.346 con ≥10, 1.818 con ≥30, 1.061 con ≥50 | conteggio dei livelli |
| Batch | 56, **tutti** con cellule NTC (min 5, mediana 92) | tabella incrociata |
| Pannello VCC | **0 / 300** | join con `pert_counts.csv` |

Due cose che l'audit **non** stabilisce, e che restano scritte come incerte: la
verifica di interezza è su un campione, non su tutte le 145.473 cellule; e il
nome del file non è una prova — «raw» è una dichiarazione, l'aritmetica è il
controllo.

Una differenza attesa e trovata: la sonda del 12 settembre sul file GEO aveva
registrato `obs.gene == 'non-targeting'` per i controlli; questo mirror
armonizzato li chiama `obs.perturbation == 'control'`. Forma, numero di cellule e
numero di NTC coincidono. Il mirror rinomina, non rimisura.

**0/300 sul pannello è il limite che governa tutto il resto:** questo esperimento
verifica il trasferimento *fra contesti*, non la copertura dei 300 bersagli VCC.
Nessuna riga di questo documento va letta come una misura sul pannello.

## 3. Implementato

- `scripts/53_build_hepg2_signatures.py` — firme HepG2 dalle singole cellule con
  **la stessa definizione** delle sorgenti pseudobulk esistenti:
  `log2((CPM_bersaglio + c) / (CPM_controllo + c))` sull'asse ufficiale, errore
  standard di Poisson, stesso pseudoconteggio. Niente di nuovo è stato inventato
  per questa sorgente, così una firma HepG2 e una K562 significano la stessa cosa
  quando un modello le legge accanto.
- **Controlli appaiati per batch.** Ogni bersaglio è confrontato con gli NTC dei
  batch da cui vengono le sue cellule, mescolati nella proporzione in cui quelle
  cellule compaiono, con una libreria di controllo efficace
  `1 / Σ_b w(t,b)² / L_b` — l'equivalente in varianza della miscela. Mettere
  insieme tutti gli NTC avrebbe confrontato un bersaglio presente in due batch
  con la media di cinquantasei, e un effetto di batch sarebbe arrivato
  etichettato come effetto di perturbazione.
- `scripts/55_control_profile.py` — profilo basale NTC di una sorgente a singola
  cellula, letto sulle sole righe NTC. Stessa quantità di
  `extract_control_profile`, lettore diverso.
- `scripts/54_context_target_table.py` — censimento contesto × bersaglio, con
  *osservato* e *sufficientemente supportato* come colonne separate.
- `src/vcc2026/benchmark/` esteso, **in modo retrocompatibile** (i 24 test di
  m001 restano verdi):
  - `fit_descriptor_bank(train_contexts=…)` accetta più contesti di training; i
    geni ad alta espressione sono scelti sulla **media** dei contesti di
    training, così nessuno dei due decide da solo che cosa il descrittore guarda.
  - `DescriptorBank.transform_rows` — una riga per (bersaglio, contesto). È ciò
    che rende il blocco di contesto una variabile invece di una colonna costante.
  - `_rows_of` sostituisce l'indice per bersaglio dove le righe sono per
    (bersaglio, contesto): `{t: i}` avrebbe tenuto in silenzio una riga su due.
  - `select_multi_source_transfer` con `context_equal_weights` — peso uguale per
    **contesto biologico**, diviso fra i dataset di quel contesto. Pesare per
    dataset darebbe a K562 due voti dove RPE1 e HepG2 ne hanno uno.
  - `evaluation.save_full_predictions` ora è letto davvero: era una chiave di
    configurazione che nessun codice leggeva.
- `configs/benchmark_3ctx.yaml` — il protocollo. Metrica primaria fissata prima
  del confronto (`pooled_mse_vs_null` in spazio log2FC pseudobulk), margine di
  non inferiorità `null`, alpha 0,1974 vietato, universo per intersezione,
  riempimento a zero rifiutato.
- `tests/test_modular_benchmark.py` — sei test nuovi: che il secondo contesto
  faccia davvero variare il descrittore, che ogni riga porti il proprio contesto,
  che tutte le righe di un bersaglio sopravvivano allo split, che una linea
  cellulare non prenda due voti, che il trasferimento multi-sorgente rifiuti
  l'alpha del trial, e che la configurazione tenga i due dataset K562 dalla stessa
  parte.

Autoencoder, esperti, bagging e boosting **non** sono in questo esperimento.

## 4. Eseguito

```bash
.\scripts\py.cmd scripts/52_audit_hepg2.py --h5ad <raw>/nadig_hepg2/NadigOConner2024_hepg2.h5ad --out reports/hepg2_2026-09-14
.\scripts\py.cmd scripts/53_build_hepg2_signatures.py --run-id e003
.\scripts\py.cmd scripts/55_control_profile.py --source-id nadig_hepg2
.\scripts\py.cmd scripts/54_context_target_table.py --out reports/hepg2_2026-09-14
.\scripts\py.cmd scripts/51_run_modular_pilot.py --run-id m002 --config configs/benchmark_3ctx.yaml --signatures <e001>/signatures <e003>/signatures
.\scripts\py.cmd -m unittest tests.test_modular_benchmark
python scripts/31_check_docs.py
```

Nessuna sottomissione, nessun download oltre HepG2, nessun servizio a pagamento.

## 5. Misurato

Ogni numero di questa sezione ha un file. Se il file non c'è, la riga non è una
misura.

### 5.1 Che cosa è entrato

Fonte: `reports/hepg2_2026-09-14/context_target_summary.json` e
`C:/Users/ferra/vcc2026-data/artifacts/e003/signature_qc_nadig_hepg2.json`.

| Contesto | Sorgenti | Bersagli osservati | ≥30 cellule | ≥50 cellule | Cellule/bersaglio (mediana) | Geni misurati |
|---|---|---:|---:|---:|---:|---:|
| K562 | `k562_gwps`, `k562_essential` | 2.665 | 2.613 | 2.528 | 147 | 7.681 / 7.940 |
| RPE1 | `rpe1_essential` | 2.354 | 2.016 | 1.611 | 73 | 8.260 |
| HepG2 | `nadig_hepg2` | 2.346 | 1.818 | 1.061 | 46 | 9.023 |

Bersagli condivisi: HepG2∩K562 2.346, HepG2∩RPE1 2.319, K562∩RPE1 2.354,
**tutti e tre 2.319**. Pannello VCC: **0/300 in HepG2**, 272/300 in `k562_gwps`,
0/300 nelle altre due — invariato rispetto a m001.

Le firme HepG2 sono sulla stessa scala delle altre, che è il controllo minimo
perché un modello possa leggerle accanto: mediana di |log2FC| sui geni osservati
0,229 contro 0,143 di `k562_gwps` e 0,245 di `rpe1_essential`; quota di geni con
|log2FC| oltre 1 pari a 4,9% contro 1,2% e 7,4% (campione di 400 firme per
sorgente).

### 5.2 Il benchmark a tre contesti

Fonte: `reports/benchmark_3ctx_2026-09-14/` (run `m002`). 108 righe = 3 fold × 2
protocolli × 2 seed × 9 bracci. 160 bersagli estratti a caso su 2.315 condivisi,
seed 2026, **non** filtrati per efficacia.

Universo genico: **6.477 / 18.533 geni** (34,9%) in ogni fold — l'intersezione
dei tre pannelli misurati. Erano 6.714 con due contesti: il terzo contesto costa
237 geni di asse comune, ed è un costo reale del disegno, non un dettaglio.

`pooled_mse_vs_null`, più basso è meglio, protocollo *contesto nuovo, bersaglio
già visto*, seed 2026 / 2027:

| Braccio | K562+RPE1 → **HepG2** | K562+HepG2 → **RPE1** | RPE1+HepG2 → **K562** |
|---|---:|---:|---:|
| shrunk_transfer | **0,952 / 0,949** | 0,971 / 0,968 | **0,999 / 1,000** |
| lowrank_linear | 1,487 / 1,487 | 0,874 / 0,874 | 1,164 / 1,164 |
| lowrank_linear_noctx | 1,333 / 1,333 | 0,896 / 0,896 | 1,279 / 1,279 |
| compact_mlp | 10,008 / 7,054 | 7,862 / 14,673 | 10,634 / 4,922 |
| compact_mlp_noctx | 1,387 / 1,472 | 0,925 / 0,934 | 1,383 / 1,410 |
| modular_frozen | 1,083 / 1,102 | **0,887 / 0,878** | 1,124 / 1,085 |
| modular_frozen_noctx | 1,211 / 1,193 | 0,879 / 0,873 | 1,200 / 1,288 |
| modular_joint | 2,365 / 3,031 | 0,993 / 1,553 | 1,070 / 1,388 |

Nel protocollo *bersaglio mai visto* ShrunkTransfer vale esattamente 1,0000 in
tutti i fold: senza quel bersaglio fra le risposte di training non ha nulla da
trasferire e predice il nullo. È copertura zero, non bravura.

**Differenze appaiate per bersaglio contro ShrunkTransfer** (bootstrap 200, seed
2026; positivo = il braccio appreso è peggio):

| Fold | modular_frozen | IC95 esclude 0 | lowrank_linear | IC95 esclude 0 |
|---|---:|---|---:|---|
| K562+RPE1 → HepG2 | +0,441 | sì | +0,696 | sì |
| K562+HepG2 → RPE1 | +0,082 | sì | +0,011 | **no** |
| RPE1+HepG2 → K562 | +0,295 | sì | +0,200 | sì |

**Le due aggregazioni della stessa corsa non concordano**, e va detto invece di
scegliere quella che conviene: sul fold con RPE1 fuori la MSE aggregata dà
modular_frozen migliore di ShrunkTransfer (0,887 contro 0,971), mentre la
differenza appaiata per bersaglio — l'unica che porta un intervallo — lo dà
peggiore (+0,082, IC senza zero). La prima è un rapporto di somme dominato dai
bersagli a varianza alta, la seconda una media su bersagli. Nessuna delle due
autorizza ad adottare la modularità.

Il segnale favorevole alla base congelata misurato in m001 (K562 → RPE1,
differenza appaiata **negativa**, IC senza zero su entrambi i seed) **non si
ripresenta** in nessuno dei tre fold a tre contesti: qui la differenza appaiata è
positiva ovunque. Il fold più vicino a quello di m001 è K562+HepG2 → RPE1, che ha
lo stesso contesto di test e un training più grande; anche lì il segno è
cambiato.

### 5.3 Il descrittore di contesto

In m001 `lowrank_linear` e `lowrank_linear_noctx` davano MSE **identica a quattro
decimali**: il descrittore era una colonna costante e non poteva fare differenza.
Adesso i vettori di contesto distinti in training sono **2** in tutti e sei gli
split (`n_unique_context_vectors_in_training` nei file di split), e le due
varianti divergono. Differenza *con − senza* sulla MSE aggregata, su 12 split:

| Braccio | Media | Minimo | Massimo | Lettura |
|---|---:|---:|---:|---|
| compact_mlp | **+9,73** | +2,10 | +22,32 | sempre peggio con il contesto |
| modular_joint | +0,33 | −0,25 | +1,80 | prevalentemente peggio |
| lowrank_linear | +0,02 | −0,13 | +0,24 | segno alterno |
| modular_frozen | −0,05 | −0,20 | +0,03 | leggermente meglio, 8 split su 12 |

Il risultato leggibile: **il descrittore di contesto non aiuta in modo
sistematico**, e sulla MLP unica è distruttivo — trentasette colonne di
statistiche NTC che il modello adatta al training e poi estrapola a un contesto
mai visto. La lettura prudente è che con due contesti di training il descrittore
assume due valori: il modello può distinguerli, non può imparare come la risposta
dipenda dal contesto in generale. Biologia e provenienza sperimentale restano
confuse, perché ogni contesto viene da un esperimento solo.

**Con gli intervalli, però, la frase va resa più precisa.** Il run `m004` ripete
lo stesso protocollo aggiungendo il confronto appaiato di ogni braccio contro il
proprio gemello senza contesto — 48 confronti, uno per braccio × fold ×
protocollo × seed. Le sue 108 righe numeriche coincidono con quelle di `m002`
(differenza assoluta zero su `pooled_mse_vs_null`, `pearson_median`,
`coverage_targets` e conteggio dei parametri), quindi è lo stesso esperimento con
una misura in più. Fonte:
`reports/benchmark_3ctx_2026-09-14/summary_m004_con_confronti_contesto.json`.

[CP-0013](checkpoints/0013-hepg2-terzo-contesto.md) è stato scritto prima che
`m004` finisse e riporta le stime puntuali della tabella qui sopra; gli intervalli
stanno in questo documento. Un checkpoint non si riscrive, e questo non lo corregge:
le due misure sono quantità diverse — differenza fra MSE aggregate da una parte,
differenza appaiata per bersaglio con bootstrap dall'altra.

**45 confronti su 48 hanno l'IC95 che esclude lo zero.** Il descrittore non è
inerte: fa una differenza misurabile quasi sempre. Il punto è il *segno*, che
dipende dal fold:

| Braccio | K562+HepG2 → RPE1 | K562+RPE1 → HepG2 | RPE1+HepG2 → K562 |
|---|---:|---:|---:|
| compact_mlp | +46,2 (peggiora) | +13,7 (peggiora) | +13,5 (peggiora) |
| modular_joint | +1,09 (peggiora) | +1,82 (peggiora) | −0,12 (misto) |
| lowrank_linear | **−0,024 (aiuta)** | +0,354 (peggiora) | **−0,178 (aiuta)** |
| modular_frozen | +0,047 (misto) | +0,032 (misto) | **−0,119 (aiuta)** |

(media della differenza *con − senza* sui quattro confronti di ogni cella;
negativo = il contesto aiuta.)

Il low-rank è il caso più netto: il contesto aiuta quando il fold tiene fuori
RPE1 o K562, e peggiora quando tiene fuori HepG2, con intervalli che escludono lo
zero in tutti e dodici i confronti. Un effetto reale il cui segno cambia con il
contesto tenuto fuori non è un descrittore che «funziona»: è un descrittore che
adatta il training e poi estrapola, e il costo dell'estrapolazione dipende da
quanto il contesto nuovo somiglia a quelli visti. Questo è coerente con il fatto
che HepG2 è il contesto più lontano dai due su cui la pipeline era stata
costruita.

### 5.3-bis Due etichette che il codice produceva sbagliate

Nate qui, trovate qui, corrette qui, con un test ciascuna. Nessuna toccava un
numero; entrambe toccavano ciò che il numero dichiarava di essere.

- `calibration_label` dei bracci appresi diceva `internal_same_line_limited` anche
  quando la coppia interna era fra **due contesti biologici diversi**. La stringa
  era fissata dentro `fit_amplitude`, vera finché l'unica coppia disponibile era
  K562 genome-wide contro K562 essential. In `m004` l'etichetta è
  `cross_context_within_training` su tutti e nove i bracci, che è ciò che il fold
  fa davvero. **La tabella di `m002` porta l'etichetta vecchia**: i suoi alpha non
  ne erano toccati, la descrizione sì.
- `perturbed_contexts_local` dell'inventario contava le sole sorgenti
  *pseudobulk*. Con HepG2 su disco, abilitato e usato dal benchmark, l'inventario
  continuava a rispondere `['K562', 'RPE1']`. Adesso conta le sorgenti perturbate
  su disco di qualunque formato, escludendo per `cell_state` i controlli
  ufficiali non perturbati, e risponde `['HepG2', 'K562', 'RPE1']`. Le copie di
  `inventory.json` nel report restano quelle che i run hanno davvero usato.

### 5.4 Costi misurati

Fonte: colonne `train_seconds`, `infer_seconds`, `peak_rss_bytes`,
`artifact_bytes` di `comparison_table.csv`, e `machine` in `summary.json`.

Macchina: 8,38 GB di RAM totali, **290 MB disponibili** allo snapshot, 8 CPU,
nessuna GPU (VRAM non misurata perché non esiste un device CUDA). Disco: 12,7 GB
liberi dopo l'acquisizione.

- Preprocessing: 1,6 s, picco RSS 142 MB.
- Somma dei tempi di training su tutti i fold: 611 s per 108 righe. Picco RSS
  **509,5 MiB**, identico per ogni braccio: lo domina il caricamento delle firme,
  non il modello.
- Artefatti: da 3,7 KiB (ShrunkTransfer, due scalari) a 1,2 MiB (MLP unica).
- Parametri: 2 per ShrunkTransfer, 531 addestrabili per il low-rank, 624 per la
  base congelata, 163.365 per la MLP unica.

La memoria è il vincolo vero, e si è visto: la prima costruzione delle firme
HepG2 è stata letta mentre ancora scriveva l'npz e il file è sembrato corrotto.
Il run è poi terminato bene e il file è integro (2.346 × 18.533, tutti finiti);
l'episodio resta scritto qui perché con 290 MB liberi il margine è quello.

### 5.5 Riproducibilità

Il run `m003` ripete un solo fold (K562+RPE1 → HepG2, seed 2026) con lo stesso
protocollo e le predizioni salvate. Le 18 righe condivise con `m002` hanno
`pooled_mse_vs_null` **identica, differenza assoluta zero**. La corsa è
deterministica, quindi le sezioni precedente e successiva misurano lo stesso
oggetto.

### 5.6 Generatore × predittore, sulle sei metriche VCC

Fonte: `reports/hepg2_2026-09-14/generator_x_predictor.json`. È l'esperimento che
`BENCHMARK_MODULARE.md` §6 indicava come quello che ridurrebbe più incertezza, e
che m001 non poteva eseguire perché mancavano cellule perturbate reali.

Disegno: 25 bersagli del fold con HepG2 fuori (fra quelli con almeno 40 cellule,
poi sottoinsieme casuale con seed; **mai** filtrati per efficacia), 40 cellule per
bersaglio, 400 cellule NTC **reali e identiche in ogni bundle**, come chiede il
contratto (`control_source: real`). Asse genico: i 9.624 geni della sorgente,
condivisi da predizione e verità. Scorer `cell-eval2 0.16.0`, backend DE `scanpy`
(né gpudge né pdex disponibili). Copertura media della predizione sui geni del
bundle: 93,8%.

Metriche **grezze**, senza ancore: per un dataset esterno non esistono baseline e
replicato pubblicati, quindi nessuna normalizzazione e **nessun punteggio di
leaderboard**. Questi numeri confrontano le sei corse fra loro e nient'altro.

| Predittore | Generatore | PDS ↑ | fidelity ↑ | reach ↑ | Jaccard ↑ | NMAE ↓ | MSE norm. ↓ |
|---|---|---:|---:|---:|---:|---:|---:|
| shrunk_transfer | attuale (Poisson da profilo medio) | **0,738** | 0,244 | 0,239 | 0,008 | 0,983 | **0,994** |
| shrunk_transfer | ancorato agli NTC | 0,582 | 0,008 | 0,194 | **0,127** | 0,983 | 1,023 |
| modular_frozen | attuale | 0,498 | **0,439** | **0,243** | 0,023 | 0,879 | 1,175 |
| modular_frozen | ancorato agli NTC | 0,518 | 0,373 | 0,188 | 0,014 | **0,873** | 1,143 |
| nullo (nessun cambiamento) | attuale | 0,425 | 0,243 | 0,107 | 0,003 | 1,036 | 1,154 |
| nullo | ancorato agli NTC | 0,492 | 0,000 | 0,095 | 0,120 | 1,035 | 1,136 |

Che cosa dicono, con prudenza:

1. **I due fattori muovono metriche diverse, e a volte in direzioni opposte.** Il
   predittore domina la PDS: ShrunkTransfer col generatore attuale sta a 0,738
   contro 0,425 del nullo. Il generatore domina il Jaccard sui geni
   significativi: passare al generatore ancorato lo porta da 0,008 a 0,127 per
   ShrunkTransfer e da 0,003 a 0,120 **per il modello che non predice niente**.
2. **Una metrica che premia il realismo del generatore può essere alzata da un
   modello che non predice nulla.** È il risultato più utile della tabella, e il
   motivo per cui «migliorare il generatore» e «migliorare il predittore» non si
   sommano: il nullo col generatore ancorato batte sul Jaccard ogni predittore
   col generatore attuale.
3. Il generatore ancorato azzera la *direction fidelity* (0,008 e 0,000): un gene
   a zero nella cellula di controllo estratta resta a zero, e la direzione non
   può essere espressa. È il suo difetto, dichiarato prima di misurarlo.
4. Nessuna combinazione è migliore su tutte e sei. Non c'è un vincitore e non
   viene dichiarato.

Limite di numerosità da tenere presente leggendo la colonna NMAE: il gate del DE
lato-verità ha escluso 3 perturbazioni per gate vuoto e 9 per meno di 10 geni
ammessi, quindi quella colonna è calcolata su **13 bersagli su 25**. L'esclusione
è una proprietà del riferimento reale, identica per tutti i bracci. Lo scorer
segnala anche che 24 etichette su 25 si risolvono a un gene misurato: `NOMO3` no,
e viene valutata senza esclusione del gene bersaglio.

## 6. Ancora ipotizzato

Niente di quanto segue è misurato qui, e nessuna di queste frasi va citata come
risultato.

- Che una decomposizione modulare convenga sulla rete unica **in generale**. Con
  tre contesti il segnale favorevole di m001 non si ripresenta; questo non prova
  il contrario, prova che non regge fuori dal fold in cui era stato visto.
- Che il descrittore di contesto trasferisca ad A/B/C. Qui varia fra due valori e
  non aiuta in modo sistematico; A/B/C sono tre contesti ulteriori, senza
  etichette perturbative.
- Che ciò che il modello legge dal descrittore sia biologia. Ogni contesto viene
  da un esperimento solo: biologia, laboratorio, chimica delle guide e batch
  restano confusi, e nessun disegno a tre contesti può separarli.
- Che questi proxy in log2FC si traducano nelle sei metriche VCC. Il §5.6
  suggerisce che non si traducano in modo semplice, perché generatore e
  predittore muovono metriche diverse.
- Che il generatore ancorato agli NTC sia «migliore». Alza il Jaccard e azzera la
  fidelity: è un compromesso diverso, non un miglioramento.
- Che 0/300 di copertura del pannello si possa aggirare. Non si può: HepG2 misura
  il trasferimento fra contesti e niente di ciò che riguarda i 300 bersagli.

## 7. Che cosa questo esperimento non è

- Non è un punteggio VCC e non è una sottomissione. Nessuna ancora ufficiale è
  stata inventata per un dataset esterno.
- Non è una scelta di modello sul test esterno: `verdict_eligible` è no su ogni
  riga, e nessun braccio è stato selezionato guardando il fold di test.
- Non è una dimostrazione che ShrunkTransfer «vinca». È il braccio che regge
  meglio i tre fold in spazio proxy, con due parametri; sul bersaglio mai visto
  non predice nulla, e quella è una copertura zero, non una qualità.
- Non è una verifica della copertura del pannello dei 300 bersagli.
- Non è una misura della dipendenza dal contesto in generale: due contesti in
  training rendono il confronto con/senza descrittore *identificabile*, non
  *conclusivo*.

## 8. L'esperimento successivo che ridurrebbe di più l'incertezza

Uno, e non è più il bundle a singola cellula, che ora esiste: **un quarto
contesto perturbato**, di lignaggio diverso da K562, RPE1 e HepG2, con bersagli
condivisi. Tre contesti permettono di vedere che il descrittore non aiuta in modo
sistematico; non permettono di distinguere «il descrittore non porta
informazione» da «due valori non bastano a stimarne l'uso». Con quattro contesti
il confronto con/senza contesto ha tre fold in cui il training ne vede tre, ed è
la prima configurazione in cui quella distinzione diventa misurabile.

Il secondo per valore, e molto più economico: **ripetere il §5.6 con più bersagli
e più cellule**. Venticinque bersagli e quaranta cellule sono ciò che entra nella
memoria disponibile; il gate del DE ne ha già tolti dodici dalla colonna NMAE. Le
differenze fra generatori sono grandi, ma la numerosità è piccola, e la tabella
non porta intervalli.

## 9. Le cinque risposte

**1. Quali dati abbiamo davvero aggiunto?** Un terzo contesto biologico
perturbato: 145.473 cellule HepG2, 2.393 bersagli, 4.976 controlli, md5
verificato contro il pubblicatore. Diventano 2.346 firme utilizzabili (≥10
cellule) con controlli appaiati per batch, di cui 2.319 condivise con K562 e
RPE1. In più — ed è la cosa che m001 non aveva — **cellule perturbate reali con
NTC reali**, che è ciò che serve per calcolare le sei metriche della gara su
qualcosa che non abbiamo generato noi. Copertura del pannello VCC: **0/300**.

**2. Quali blocchi del modello possiamo ora addestrare o verificare meglio?**
Verificare, più che addestrare. Il descrittore di contesto è diventato
*misurabile*: prima era una colonna costante, adesso assume due valori in
training e le varianti con e senza divergono. La calibrazione dell'ampiezza ha
una coppia interna **fra contesti diversi** invece che fra due dataset della
stessa linea cellulare. Il generatore è diventato confrontabile su cellule vere
invece che per ipotesi. Ciò che **non** possiamo addestrare meglio è la
dipendenza dal contesto in generale: due valori non la insegnano.

**3. Il descrittore del contesto aiuta?** No, non in modo sistematico. Media
della differenza *con − senza* su 12 split: +9,73 sulla MLP unica (sempre
peggio, fino a +22), +0,33 sull'affinamento congiunto, +0,02 sul low-rank (segno
alterno), −0,05 sulla base congelata (meglio in 8 split su 12, di poco). E va
detto che il descrittore varia davvero fra i contesti di training — non è un
identificativo di dataset: è costruito dalle statistiche NTC e i due vettori sono
distinti in tutti e sei gli split.

**4. La base congelata resta promettente nei diversi fold?** No. In CP-0011 la
differenza appaiata contro ShrunkTransfer era negativa con IC senza zero su
entrambi i seed. Con tre contesti è **positiva in tutti e tre i fold** (+0,441,
+0,082, +0,295; IC95 senza zero ovunque). Sul fold che tiene fuori RPE1 la MSE
aggregata la dà ancora migliore: le due aggregazioni si contraddicono, e quando
si contraddicono non c'è niente da adottare.

**5. Che cosa manca prima di scegliere un modello per la gara?** Quattro cose,
in ordine di quanto tolgono incertezza:

1. **Un quarto contesto perturbato**, di lignaggio diverso. È l'unica via per
   distinguere «il descrittore non porta informazione» da «due valori non
   bastano», e per separare un minimo la biologia dalla provenienza sperimentale.
2. **Una misura sui 300 bersagli del pannello.** Tutto questo lavoro sta a 0/300
   in HepG2 e 272/300 nel solo K562 genome-wide: nessuna riga qui dice che cosa
   succederà sui bersagli della gara.
3. **Un margine di non inferiorità**, fissato dalla ripetibilità della baseline
   misurata a parte. Senza, «non inferiore» resta una frase, e il confronto può
   solo dire *inconcludente*.
4. **Ancore per le sei metriche**, o l'accettazione esplicita che su dati esterni
   si riportano solo numeri grezzi. Oggi la seconda: è la scelta corretta e limita
   ciò che la tabella §5.6 può concludere.

Fino ad allora il modello da battere resta ShrunkTransfer, che ha due parametri,
regge i tre fold meglio degli altri bracci in spazio proxy, e sul bersaglio mai
visto non predice nulla — che è un limite, non una virtù.
