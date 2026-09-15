# CP-0013 — HepG2 acquisito: benchmark a tre contesti e generatore contro predittore

- **Data:** 2026-09-14
- **Tipo:** esperimento
- **Redatto da:** agente Claude (Opus 5)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

[CP-0011](0011-primo-benchmark-modulare.md) ha confrontato trasferimento, ridge a
basso rango, MLP unica e base congelata con **due** contesti perturbati, e D-025
ha registrato il limite: tenendone fuori uno resta un solo contesto di training,
il descrittore di contesto è una colonna costante, e un confronto con/senza
contesto non identifica niente. D-025 dice anche a quale condizione riaprire:
*un terzo contesto perturbato locale con bersagli condivisi*, oppure *un bundle a
singola cellula* che permetta di misurare le sei metriche VCC.

Due domande, quindi. Il terzo contesto cambia le conclusioni di CP-0011? E, sulle
cellule reali, quanto del punteggio dipende dal generatore e quanto dal
predittore?

## 2. Cosa è stato fatto

```bash
.\scripts\py.cmd scripts/52_audit_hepg2.py --h5ad <raw>/nadig_hepg2/NadigOConner2024_hepg2.h5ad --out reports/hepg2_2026-09-14
.\scripts\py.cmd scripts/53_build_hepg2_signatures.py --run-id e003
.\scripts\py.cmd scripts/55_control_profile.py --source-id nadig_hepg2
.\scripts\py.cmd scripts/54_context_target_table.py --out reports/hepg2_2026-09-14
.\scripts\py.cmd scripts/51_run_modular_pilot.py --run-id m002 --config configs/benchmark_3ctx.yaml --signatures <e001>/signatures <e003>/signatures
.\scripts\py.cmd scripts/51_run_modular_pilot.py --run-id m003 --config configs/benchmark_3ctx_hepg2_predictions.yaml --signatures <e001>/signatures <e003>/signatures
.\scripts\py.cmd scripts/57_generator_x_predictor.py --predictions <m003>/models/new_context_seen_target_k562_rpe1_to_hepg2_seed2026 --arms shrunk_transfer modular_frozen --n-targets 25 --cells-per-target 40 --ntc-cells 400 --out reports/hepg2_2026-09-14
.\scripts\py.cmd -m unittest tests.test_modular_benchmark
python scripts/31_check_docs.py
```

Dati acquisiti: `NadigOConner2024_hepg2.h5ad`, mirror scPerturb di GSE264667,
scaricato da Zenodo (record 13350497) con `curl -L -C -`. Il documento completo,
con il protocollo e tutte le tabelle, è
[BENCHMARK_TRE_CONTESTI.md](../BENCHMARK_TRE_CONTESTI.md).

## 3. Cosa si è osservato

**Acquisizione** — `reports/hepg2_2026-09-14/acquisition.json`: 850.590.740 byte
ricevuti contro altrettanti dichiarati, md5 `af2be47f7477cf32fa6e4bec1c6a4868`
uguale a quello pubblicato, licenza del record CC BY 4.0, richiesta di intervallo
accettata (HTTP 206). Il mirror è stato scelto sulla copia GEO da 5,2 GB perché
quest'ultima avrebbe lasciato 8,8 GiB liberi, sotto il minimo di D-005.

**Contenuto** — `reports/hepg2_2026-09-14/nadig_hepg2_audit.json`: 145.473 × 9.624,
denso float32 gzip; nessun `layers`, nessun `raw`. Su 3.072 cellule campionate i
valori sono non negativi e interi, nessuna cellula ha libreria zero, la libreria
mediana è 15.778 contro 15.487 della colonna dichiarata `obs.ncounts`. 9.624
simboli senza duplicati, 9.023 sull'asse ufficiale. Controlli
`obs.perturbation == 'control'`, 4.976 cellule. 2.393 livelli perturbanti,
mediana 45 cellule, 2.346 con almeno 10. 56 batch, **tutti** con cellule NTC.
**Pannello VCC: 0/300.**

**Firme** — `<artifacts>/e003/signature_qc_nadig_hepg2.json`: 2.346 firme, 9.023
geni osservati, controlli appaiati per batch. Mediana di |log2FC| 0,229 contro
0,143 di `k562_gwps` e 0,245 di `rpe1_essential`: la stessa scala.

**Censimento** — `reports/hepg2_2026-09-14/context_target_summary.json`: bersagli
condivisi dai tre contesti **2.319**.

**Benchmark a tre contesti** — `reports/benchmark_3ctx_2026-09-14/`, run m002,
108 righe, 160 bersagli su 2.315 condivisi, universo **6.477/18.533 geni**
(erano 6.714 con due contesti).

- `pooled_mse_vs_null`, bersaglio già visto, seed 2026: ShrunkTransfer 0,952
  (HepG2 fuori), 0,971 (RPE1 fuori), 0,999 (K562 fuori). modular_frozen 1,083 /
  0,887 / 1,124.
- Differenze appaiate per bersaglio contro ShrunkTransfer, bootstrap 200:
  modular_frozen **+0,441 / +0,082 / +0,295**, IC95 senza zero in tutti e tre i
  fold. In CP-0011 la stessa differenza era **negativa** con IC senza zero.
- Sul fold con RPE1 fuori le due aggregazioni si contraddicono: la MSE aggregata
  dà modular_frozen migliore (0,887 contro 0,971), la differenza appaiata lo dà
  peggiore (+0,082).
- Vettori di contesto distinti in training: **2** in tutti e sei gli split. In
  CP-0011 erano 1, e low-rank con/senza contesto davano MSE identica a quattro
  decimali.
- Differenza *con − senza* contesto sulla MSE aggregata, media su 12 split:
  compact_mlp **+9,73** (sempre peggio), modular_joint +0,33, lowrank_linear
  +0,02 (segno alterno), modular_frozen −0,05 (meglio in 8 split su 12).
- Costi: 611 s di training in totale, picco RSS 509,5 MiB, macchina con 8,38 GB
  di RAM e 290 MB disponibili allo snapshot.
- Riproducibilità: m003 ripete un fold e le 18 righe condivise con m002 hanno
  `pooled_mse_vs_null` con differenza assoluta **zero**.

**Generatore × predittore** — `reports/hepg2_2026-09-14/generator_x_predictor.json`,
25 bersagli, 40 cellule ciascuno, 400 NTC reali condivisi, `cell-eval2 0.16.0`,
backend DE `scanpy`, metriche **grezze senza ancore**:

| Predittore | Generatore | PDS | fidelity | Jaccard |
|---|---|---:|---:|---:|
| shrunk_transfer | attuale | 0,738 | 0,244 | 0,008 |
| shrunk_transfer | ancorato agli NTC | 0,582 | 0,008 | 0,127 |
| nullo | attuale | 0,425 | 0,243 | 0,003 |
| nullo | ancorato agli NTC | 0,492 | 0,000 | 0,120 |

## 4. Interpretazione e incertezza

**Misurato:** tutti i numeri della sezione 3.

**Interpretazione.** Il segnale favorevole alla base congelata di CP-0011 non
sopravvive al terzo contesto: la differenza appaiata cambia segno in tutti e tre
i fold, compreso quello che tiene fuori lo stesso contesto di allora. Questo non
dimostra che la modularità sia inutile; dimostra che quel segnale non reggeva
fuori dal singolo fold in cui era stato visto, ed è il motivo per cui CP-0011 non
aveva dichiarato un vincitore.

**Interpretazione.** Il descrittore di contesto adesso *può* fare differenza e
non la fa in modo sistematico. Sulla MLP unica è distruttivo: trentasette colonne
di statistiche NTC adattate a due contesti ed estrapolate a un terzo.

**Interpretazione, ed è il risultato più utile.** Sulle cellule reali il
generatore e il predittore muovono metriche diverse e talvolta in direzioni
opposte. Il Jaccard sui geni significativi sale da 0,003 a 0,120 cambiando solo
il generatore, **su un modello che non predice nulla**: una metrica che premia il
realismo del generatore può essere alzata senza alcuna capacità predittiva. Di
conseguenza «migliorare il generatore» e «migliorare il predittore» non si
sommano, e un guadagno complessivo non dice quale dei due l'ha prodotto.

**Perché potrebbe non significare questo.** Tre contesti restano pochi e ciascuno
viene da un esperimento solo: biologia, laboratorio e batch sono confusi, quindi
«il descrittore non aiuta» potrebbe voler dire «due valori non bastano a stimarne
l'uso». La tabella delle sei metriche ha 25 bersagli, 13 dei quali per la colonna
NMAE dopo il gate del DE, e non porta intervalli. L'universo genico è il 34,9%
dell'asse ufficiale: quello che accade sugli altri due terzi non è misurato.
Infine 0/300 di copertura del pannello: niente qui riguarda i bersagli della gara.

**Ipotesi non verificata.** Che un quarto contesto renda distinguibile «il
descrittore non porta informazione» da «due valori non bastano».

## 5. Spiegazione semplice

Volevamo sapere se conviene un modello fatto di pezzi invece che un unico blocco.
Per giudicarlo servono contesti diversi in cui provare: prima ne avevamo due, e
tenendone fuori uno per la prova ne restava uno solo per imparare — come voler
capire se una ricetta si adatta al forno di casa avendo provato un forno solo.
Adesso i forni sono tre. Il risultato è che il vantaggio visto la volta scorsa
non si ripresenta, e che la parte del modello che «guarda il contesto» non aiuta
in modo affidabile.

La seconda misura è più sottile. Il punteggio della gara si calcola su cellule, e
noi le cellule le inventiamo a partire da una previsione. Abbiamo separato i due
lavori — prevedere l'effetto, e trasformarlo in cellule — e li abbiamo variati
uno alla volta. Una delle sei metriche è salita di quindici volte cambiando solo
il modo di fabbricare le cellule, per un modello che prevedeva *nessun effetto*.
Quella metrica, da sola, non misura se abbiamo capito la biologia.

## 6. Conseguenze

- D-025 va riaperta: la sua condizione di riapertura («un terzo contesto
  perturbato locale con bersagli condivisi») è soddisfatta. Vedi **D-026**.
- Il registry ha una sorgente in più utilizzabile: `nadig_hepg2` passa a
  `pilot_ingested`, `enabled: true`, `ingestion_status: local`.
- L'esperimento indicato come il più informativo in `BENCHMARK_MODULARE.md` §6 è
  stato eseguito. Il successivo più informativo non è più un bundle a singola
  cellula ma **un quarto contesto perturbato**.
- Nessuna architettura è adottata e nessuna sottomissione è stata preparata.

## 7. Cosa corregge

- **Corregge CP-0011 §3.2 su un punto e solo quello:** la differenza appaiata
  favorevole a `modular_frozen` contro ShrunkTransfer (media −0,013 e −0,011, IC
  senza zero) era misurata su un fold con un solo contesto di training. Con tre
  contesti la stessa differenza è positiva in tutti e tre i fold. Il resto di
  CP-0011 — l'esito inconcludente, il rifiuto di dichiarare un vincitore, i costi
  misurati — resta valido e viene confermato.
- **Corregge un'etichetta prodotta dal codice, non da un documento:** in m002 i
  bracci appresi riportano `calibration_label: internal_same_line_limited` anche
  dove la coppia interna è fra due contesti biologici diversi. La stringa era
  fissa in `fit_amplitude`. È stata resa un parametro del chiamante, con un test;
  il valore di alpha non ne era toccato, solo l'etichetta.
- **Corregge una frase generata in `summary.json`:** il campo `winner_reason`
  affermava che tenere fuori un contesto ne lascia uno solo in training. Era vero
  del progetto a due contesti e falso dal momento in cui il terzo è arrivato.
  Adesso è derivato dalla configurazione.
- Non corregge nient'altro. In particolare non tocca CP-0012 né il lavoro sui
  descrittori di modo B, svolto in parallelo.

## 8. Domanda di comprensione

Il generatore ancorato agli NTC porta il Jaccard da 0,003 a 0,120 sul modello
nullo. Perché questo **non** è una ragione per adottarlo, e quale numero della
stessa tabella lo mostra?
