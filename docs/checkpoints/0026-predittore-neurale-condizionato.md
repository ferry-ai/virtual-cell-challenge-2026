# CP-0026 — Primo predittore neurale condizionato su bersaglio e contesto: scartato; il modello lineare con gli stessi input lo pareggia o lo batte

- **Data:** 2026-09-19
- **Periodo:** training e validazione il 18 settembre, test e verdetto il 19
- **Tipo:** esperimento
- **Redatto da:** agente
- **Revisione umana:** no. Il mandato è del proprietario (18 settembre); la regola non è stata rivista.
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il mandato del proprietario chiede una piccola rete che riceva:
- descrittori del bersaglio disponibili anche per geni mai perturbati;
- una rappresentazione del contesto presa dai soli controlli.

La rete deve predire l'effetto della coppia bersaglio-contesto meglio del trasferimento
semplice, di un modello lineare con gli stessi input e della ricetta t03, fuori campione, e
deve usare davvero il contesto.

## 2. Cosa è stato fatto

- **Modelli** (`src/vcc2026/conditioned.py`).
  - Rete in numpy: un cancello per gene sulla risposta K562 del bersaglio, più un termine
    bilineare bersaglio × gene.
  - Il contesto entra **per gene**, come log CPM di ogni gene nei controlli del contesto e
    di K562. È la differenza voluta rispetto alla `compact_mlp` di
    [CP-0013](0013-hepg2-terzo-contesto.md), dove un vettore di contesto adattato su due
    contesti la rendeva molto peggiore.
  - Descrittori del bersaglio: la sua risposta K562 (solo nel modo A), la risposta media dei
    suoi partner fisici STRING (punteggio ≥ 400), il suo log CPM nei controlli.
  - Modello lineare con gli stessi input: un cancello lineare più una ridge multi-output.
    Ha **più** parametri della rete (471.619 contro 231.857 o 120.385).
- **Dati.** Etichette dai bulk di K562 genome-wide (9.866 bersagli) e di RPE1 (2.393), in ln
  fold change con contrazione EB, su 6.835 geni misurati in K562, RPE1 e HepG2.
- **Tre split**, fissati prima del training in `configs/conditioned_rule.yaml`:
  - C: contesto nuovo, HepG2;
  - J: congiunto, bersagli tolti da ogni etichetta;
  - T: bersagli nuovi, i bersagli ufficiali in K562.
  - Controlli di leakage registrati: tutti a zero.
- **Stesso budget per le due famiglie:** 8 configurazioni ciascuna, scelte sulla MSE di
  validazione. Per C e J la validazione è su un contesto già visto: non ne esiste un secondo
  nuovo. Training di 2 ore su Colab (job 028).
- **Banchi con lo stesso generatore e gli stessi bersagli**, stadi 73 e 75 con `--effects`.
  - Validazione: 300 bersagli HepG2 e 111 bersagli ufficiali in K562. Le ampiezze le sceglie
    lo stadio 93.
  - Test: 299 bersagli HepG2 disgiunti e 113 bersagli ufficiali disgiunti.
  - Punteggio in unità ufficiali, con le ancore di `reports/anchors_2026-09-17/`, calibrato
    sul t03 per HepG2. Bootstrap appaiato sui bersagli.
- **Verdetto:** stadio 94.
- **Letture nello spazio degli effetti**, esplorative: stadio 95, correlazione dopo aver tolto
  la risposta media, accoppiamento predizione-bersaglio, confronto con la media.
- **Il runtime Colab si è perso tre volte** (16:53 UTC, 20:21 UTC con il PC chiuso, più un
  job ucciso per memoria). Ogni ripresa ha usato un numero e un'uscita nuovi.

## 3. Cosa si è osservato

**Misurato — il verdetto è `DISCARD`**
(`reports/conditioned_2026-09-18/verdict/verdict.json`).

| condizione | differenza | IC 95% | esito |
|---|---|---|---|
| rete C meglio della ricetta t03 (HepG2 test) | −0,002 | [−0,028, +0,024] | no |
| rete C meglio del lineare C | +0,004 | [−0,010, +0,020] | no |
| rete C usa il contesto (contro il contesto RPE1) | −0,001 | [−0,016, +0,015] | no |
| split J: rete non peggiore del lineare | +0,065 | [+0,037, +0,093] | sì |
| split T: rete non peggiore del lineare | −0,128 | [−0,187, −0,066] | no |

**Misurato — banco HepG2 di test** (299 bersagli, punteggio ufficiale previsto, il t03 vale
+0,0204 per costruzione della calibrazione):

| braccio | punteggio | `pds_cosine` | fedeltà | `reach` | Jaccard |
|---|---|---|---|---|---|
| ricetta t03 | +0,020 | 0,753 | 0,529 | 0,419 | 0,124 |
| trasferimento semplice ×4 | −0,005 | 0,748 | 0,580 | 0,447 | 0,085 |
| lineare C ×2 | +0,010 | 0,566 | 0,620 | 0,498 | 0,067 |
| rete C ×2 | +0,015 | 0,576 | 0,607 | 0,522 | 0,110 |
| rete J ×4 | −0,214 | 0,538 | 0,213 | 0,226 | 0,106 |
| vicini STRING ×4 | −0,155 | 0,599 | 0,324 | 0,204 | 0,071 |

**Misurato — banco K562, bersagli ufficiali** (113): lineare +0,030, vicini STRING +0,031,
rete −0,093, risposta media −0,108, nessun effetto −0,144, oracolo +0,397.

**Misurato — spazio degli effetti** (`reports/conditioned_2026-09-18/effect_space/`),
correlazione dopo aver tolto la risposta media:

| split | rete | rete con contesto RPE1 | lineare | vicini |
|---|---|---|---|---|
| C | +0,369 | +0,366 | +0,359 | +0,174 |
| J | +0,187 | +0,190 | +0,267 | +0,169 |
| T | +0,022 | +0,020 | +0,030 | +0,035 |

Su HepG2 nello split C i modelli appresi riconoscono il proprio bersaglio fra 300 nel 5-6% dei
casi (il caso vale 0,3%). Sui bersagli ufficiali in K562 lo fanno al livello del caso.

**Misurato — l'addestramento della rete non si riproduce.** Rilanciando lo split C con gli
stessi semi (job 039), la selezione ha scelto un'altra configurazione e le predizioni
cambiano fino a 1,2. Il lineare si riproduce a 1e-7
(`reports/conditioned_2026-09-18/PIANO_INVIO_t06.md`).

## 4. Interpretazione e incertezza

**Interpretazione.**
- **I modelli appresi funzionano, la rete no.** Lineare e rete trasferiscono su un contesto
  nuovo un segnale davvero specifico del bersaglio (0,36-0,37 di correlazione dopo aver tolto
  la risposta comune), ben oltre la firma grezza. Nel punteggio però questo si traduce in un
  pareggio con la ricetta t03: guadagnano fedeltà e `reach`, perdono `pds_cosine` e Jaccard.
  Questi modelli spingono verso la risposta comune, e la discriminazione fra bersagli ne
  soffre.
- **La rete non aggiunge nulla al lineare**, e non usa il contesto: sostituire i controlli
  HepG2 con quelli RPE1 non cambia nulla in nessuno dei tre split.

**Incertezza.**
- La validazione degli iperparametri avviene su un contesto già visto.
- Un solo contesto nuovo (HepG2), di geni essenziali, che non è A, B o C.
- Il bootstrap copre solo l'estrazione dei bersagli.
- Il contesto per gene ha avuto due contesti di training da cui imparare: che non serva qui
  non dimostra che non servirebbe con più contesti.

**Ipotesi, non misurata.** Che una rete aggiunga qualcosa solo con molti più contesti
perturbati di training, o con descrittori del contesto più ricchi della sola espressione
basale.

## 5. Spiegazione semplice

Abbiamo costruito un modello che impara come la risposta di un gene spento cambia da una
cellula all'altra. Ha imparato qualcosa di vero, ma un modello lineare con le stesse
informazioni impara altrettanto. La parte che doveva «capire la cellula» non viene usata:
dargli la cellula sbagliata non cambia le sue previsioni.

## 6. Conseguenze

- La rete condizionata è **scartata** come direzione, secondo la regola scritta prima.
- Il modello lineare condizionato è l'unico predittore appreso che si riproduce, e pareggia la
  ricetta t03 sul banco. È diventato il candidato t07 (vedi `PIANO_INVIO_t06.md`, aggiunta
  delle 02:40).
- Da correggere: lo stadio 92 deve salvare i pesi del modello scelto. Un file da sottomettere
  va generato da quei pesi, non da un nuovo addestramento.
- Il mandato del proprietario vieta di trasformare questo esito in una promessa o in un'altra
  catena di diagnosi: non se ne propone una qui.

## 7. Cosa corregge

- Non corregge checkpoint precedenti.
- Conferma nella direzione [CP-0013](0013-hepg2-terzo-contesto.md): con due contesti di
  training, il contesto non migliora la previsione. Questa volta è misurato anche per un
  ingresso per gene, non solo per un vettore di contesto.
- Precisa un messaggio in chat del 18 settembre, dove la rete era indicata come «circa 100k
  parametri»: le configurazioni scelte ne hanno 231.857 (split C e T) e 120.385 (split J).

## 8. Domanda di comprensione

Perché un modello che correla meglio della firma grezza con la risposta vera di ciascun
bersaglio può comunque perdere `pds_cosine`, cioè la capacità di distinguere i bersagli fra
loro?
