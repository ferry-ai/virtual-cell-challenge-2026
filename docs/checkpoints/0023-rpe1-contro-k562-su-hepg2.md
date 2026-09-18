# CP-0023 — RPE1 trasferisce su HepG2 meglio di K562, anche a parita' di chiamate; non copre alcun bersaglio ufficiale

- **Data:** 2026-09-18
- **Tipo:** esperimento
- **Redatto da:** agente
- **Revisione umana:** no (il proprietario ha rivisto regola e addendum **prima** dei risultati, non questa scheda)
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Se il lignaggio della sorgente conta, RPE1 (epiteliale) deve trasferire su HepG2 meglio di
K562 (eritroide). Lo fa, sul banco dello stadio 75, a parità di bersagli, seme e codice?

## 2. Cosa è stato fatto

1. I job 018 e 019, messi in coda il 17 alle 23:57, sono partiti alle 22:09 UTC e **non
   hanno prodotto nulla**: l'ultimo battito del dispatcher è delle 22:09:37 UTC, dodici ore e
   mezza prima della verifica del 18 mattina, e la cartella di output non esisteva. Il
   dispatcher salta ogni job con un marcatore `.started` (cella 2 di
   `notebooks/colab_sc_training.ipynb`), quindi sono stati rimessi in coda come **020** e
   **021**, con output `s_k562_gwps_r2` e `s_rpe1_r2`. Il proprietario ha riavviato il
   notebook; il dispatcher è ripartito alle 10:56 UTC.
2. Stadio 75 con `--k562-bulk` su `K562_gwps_raw_bulk_01.h5ad` e su `rpe1_raw_bulk_01.h5ad`
   (md5 verificati dal job), `--targets-file` sul pannello condiviso di 1.059 simboli
   (`reports/source_coverage_2026-09-17/c002/shared_targets.txt`), `--n-targets 300`,
   `--min-cells 50`, `--seed 2026`, bracci `null_new transfer_a0.5 transfer_a1.0
   transfer_a2.0 rawtransfer_a0.5 transfer_a2.0+cismeas_a1.0+cis_a1.0`. Il codice su Drive
   era identico byte per byte a quello locale per tutti i file usati.
3. Lettura con la regola pre-registrata `configs/source_lineage_rule.yaml` (versione 1,
   scritta il 18 alle 00:11, prima di ogni output; confermata dal proprietario intorno alle
   13:00, sempre prima dei risultati, con il campo `verdict_scope`) e con l'addendum
   `reports/source_lineage_2026-09-18/PRIMA_DEI_RISULTATI.md`.
4. Stadio 87 → `reports/source_lineage_2026-09-18/c001/compare.json`; stadio 88
   (`scripts/88_matched_volume_reading.py`, scritto dopo i risultati per applicare la lettura
   secondaria dichiarata prima) → `reports/source_lineage_2026-09-18/c002/matched_volume.json`.
   I due `bench.json` sono copiati in `reports/source_lineage_2026-09-18/` (md5 `b5d340d2…`
   K562, `b9ae1f89…` RPE1, identici alle copie su Drive).

## 3. Cosa si è osservato

**Misurato — il cancello di validità passa.** `replicate`, `baseline` e `null_new` coincidono
esattamente nei due banchi, e i 300 bersagli sono gli stessi (`c001/compare.json`).

**Misurato — fedeltà grezza e volume, per braccio** (`c001/compare.csv`):

| braccio | chiamate/bersaglio K562 | RPE1 | fedeltà grezza K562 | RPE1 |
|---|---|---|---|---|
| `transfer_a0.5` | 12,0 | 100,0 | 0,0796 | 0,3121 |
| `transfer_a1.0` | 91,6 | 540,5 | 0,2440 | 0,5870 |
| `transfer_a2.0` | 410,5 | 1.557,4 | 0,4464 | 0,6341 |
| `rawtransfer_a0.5` | 29,4 | 169,9 | 0,1294 | 0,4312 |
| `transfer_a2.0+cismeas_a1.0+cis_a1.0` | 408,9 | 1.554,5 | 0,4487 | 0,6346 |
| replica / baseline / `null_new` | 430,2 / 8,5 / 0,1 | idem | 0,6986 / 0,1187 / 0,0242 | idem |

**Misurato — il verdetto della regola è `WINS_RPE1`:** RPE1 è avanti su tutti e tre i bracci
primari, di +0,2325, +0,3430 e +0,1877; il più grande supera la soglia di 0,03.

**Misurato — a parità di ampiezza, RPE1 chiama da 4 a 8 volte di più** (tabella sopra). È il
confondente dichiarato prima dei risultati in `PRIMA_DEI_RISULTATI.md` §1.

**Misurato — lettura a parità di chiamate medie, pre-registrata** (`c002/matched_volume.json`):
nell'intervallo comune di 100,0–410,5 chiamate per bersaglio, interpolando in `log(sig/t)`,
il vantaggio di RPE1 vale **+0,056 a 100 chiamate e +0,096 a 410**, contro +0,19…+0,34 alla
stessa ampiezza.

**Misurato — lettura esplorativa, scelta dopo i risultati** (stesso file): confronto
appaiato per bersaglio fra le coppie di bracci con volume vicino, bootstrap su 10.000
ricampionamenti dei bersagli.

| coppia | chiamate/bersaglio | bersagli | differenza media | intervallo 95% | bersagli con RPE1 sopra |
|---|---|---|---|---|---|
| RPE1 `a0.5` contro K562 `a1.0` | 100 contro 92 | 256 | +0,076 | +0,036…+0,116 | 50% (pari 13%) |
| RPE1 `a1.0` contro K562 `a2.0` | 540 contro 410 | 265 | +0,133 | +0,091…+0,174 | 64% |

La seconda coppia non è pareggiata: RPE1 chiama il 32% in più.

**Misurato — gli altri membri, alla stessa ampiezza** (`c001/compare.csv`): `reach` più alto
con RPE1 su tutti i bracci (0,40/0,55/0,61 contro 0,21/0,31/0,36); `pds_cosine` quasi uguale
ad ampiezza 1,0 (0,7154 contro 0,7160) e migliore con K562 a 2,0 (0,7517 contro 0,7365);
`mse` migliore con RPE1 a 0,5 (0,80 contro 0,96) ma molto peggiore a 1,0 (1,20 contro 0,99) e
a 2,0 (3,69 contro 1,41); `sig_jaccard` simile, migliore con K562 a 2,0.

**Misurato — la copertura dei bersagli della gara.** Dei 300 bersagli di `vcc2026-val-1`
RPE1 ne ha perturbati **0**, K562 genome-wide 272, K562 essential 0
(`scripts/11_check_target_coverage.py`, 11 settembre, ricontato il 18 con la lettura dei
simboli dello stadio 75; `PRIMA_DEI_RISULTATI.md` §4).

**Misurato — la profondità.** Cellule NTC 75.328 in K562 contro 11.485 in RPE1; mediana di
cellule per riga-bersaglio 168 contro 70 (conteggio da `obs/num_cells_filtered`,
`PRIMA_DEI_RISULTATI.md` §1).

## 4. Interpretazione e incertezza

**Interpretazione.** Sul banco HepG2 le firme RPE1 producono più geni significativi e una
fedeltà grezza più alta di quelle K562. Una parte del vantaggio viene dal volume: correggendo
**approssimativamente** per il numero medio di chiamate, si attenua da +0,19…+0,34 a
+0,06…+0,10, ma resta sopra la soglia della regola. La correzione pareggia la media delle
chiamate e non la loro distribuzione fra bersagli, quindi non isola la causa. Nel confronto
appaiato a volume vicino RPE1 è sopra solo sul 50% dei bersagli: il vantaggio medio è portato
da una parte di essi.

**Non è una conferma del lignaggio.** RPE1 differisce da K562 per lignaggio, ma anche per
stato di TP53 (dato di letteratura, non misurato qui), cariotipo, crescita aderente, spazio
dei geni (7.733 contro 7.425 geni HepG2 misurati) e profondità, che anzi favorisce K562. Il
banco non separa queste spiegazioni.

**Ipotesi, non misurate:** che RPE1 chiami di più perché le sue risposte al knockdown sono
più ampie (per esempio un programma p53 comune), oppure perché la media dei suoi controlli,
stimata su sei volte meno cellule, aggiunge a tutti i bersagli lo stesso errore. La `mse`
molto peggiore ad ampiezze alte è coerente con effetti RPE1 più grandi di quelli di HepG2.

**Incertezza.** L'intervallo bootstrap copre soltanto quali bersagli sono stati estratti, non
la casualità del generatore né la divisione metà A / metà B: c'è un solo seme. La soglia di
0,03 è una regola pratica. Le tre ampiezze leggono gli stessi dati e non sono tre repliche.
HepG2 non è A, B o C, e i bersagli del banco sono geni essenziali con molte risposte
confidenti (mediana 130, decili 2 e 1.660: `real_n_conf` nei due `bench.json`), un regime che
non è quello dei contesti ufficiali.

## 5. Spiegazione semplice

Due studenti devono indovinare in che direzione si muovono i geni. Il primo risponde a
poche domande, il secondo a molte, e il voto premia anche il numero di risposte date. Il
secondo prende un voto molto più alto. Confrontandoli a parità di domande risposte, il
secondo resta avanti, ma di molto meno.

Il secondo studente, però, ha studiato su un programma che non contiene nessuna delle 300
domande dell'esame vero. Se il suo vantaggio sta nel metodo che vale per ogni domanda, lo si
può usare; se sta nel conoscere le singole domande, per l'esame non serve.

## 6. Conseguenze

- **Nessuna strategia adottata.** Per il `verdict_scope` della regola, una vittoria merita un
  approfondimento, non l'adozione di una sorgente. Nessuna sottomissione deriva da qui.
- **RPE1 non può fornire la firma di nessun bersaglio ufficiale.** Il suo vantaggio sarebbe
  utilizzabile solo attraverso ciò che non dipende dall'identità del bersaglio, o attraverso
  una correzione applicata alle firme K562. Per questo la domanda successiva, posta dal
  proprietario per il caso di vittoria di RPE1, è se il vantaggio sia **specifico del
  bersaglio o comune**.
- **Passo successivo, in corso quando questa scheda è stata scritta:** i job 022 e 023
  ripetono i due banchi con un braccio di controllo `shuffled_aX` (a ogni bersaglio l'effetto
  di un altro bersaglio della stessa sorgente), letto dalla regola
  `configs/specificity_rule.yaml` con lo stadio 89. La regola è stata corretta alla
  versione 2 **dopo** l'avvio dei job e **prima** di ogni output, perché un test sintetico
  a risposta nota aveva mostrato che la versione 1 dichiarava `MIXED` una sorgente nulla; la
  correzione è scritta nel file.
- **Strumenti nuovi**, implementati e provati: `k`, `n_pred` e `n_conf` per bersaglio in
  `src/vcc2026/bench.py` (`components_<braccio>.csv`, ricostruiti con la funzione interna
  dello scorer e verificati contro la fedeltà che lo scorer riporta); il termine `shuffled`
  nello stadio 75; gli stadi 88 e 89.

## 7. Cosa corregge

- Non corregge checkpoint precedenti.
- Precisa la premessa del proprietario di questa mattina, «se RPE1 vince, la strategia una
  sorgente per lignaggio è confermata da una misura»: la vittoria c'è, ma non separa il
  lignaggio da TP53, profondità e volume, e la sorgente vincente non copre il pannello
  ufficiale. La strategia resta un'ipotesi.
- I percorsi `inputs` di `configs/source_lineage_rule.yaml` (`s_k562_gwps`, `s_rpe1`) non
  esistono: i banchi letti sono `s_k562_gwps_r2` e `s_rpe1_r2`, come scritto
  nell'addendum.

## 8. Domanda di comprensione

Se il braccio a bersagli rimescolati di RPE1 raggiungesse la stessa fedeltà del suo braccio
di trasferimento, che cosa si potrebbe usare di RPE1 per una sottomissione, e che cosa no?
