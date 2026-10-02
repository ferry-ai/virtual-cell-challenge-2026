# Prepass R-LEAD r1: le correzioni del passo A sul corpus reale

2 ottobre 2026, Claude Code per Alfredo, sessione `42343bb9-c8d1-4b93-a9cc-2008dd008900`.

**Il run.**
- **Kernel:** `alfredo2003bit/rlead-prepass-r1`, privato, solo CPU, senza internet. È durato dalle 17:34 alle 18:22 CEST, 2.693 s in tutto.
- **Codice:** quello di [cellnet_rlead](../cellnet_rlead_2026-10-01/README.md) al commit `3062380`. Il kernel ha ricontrollato i suoi SHA256 prima di partire.
- **Dati:** gli stessi 6 dataset `davidmaisterx/rlab-*` del prepass r3.
- **Asse:** `gene_names.csv` dal portale VCC, scaricato con il login del teammate. Il suo SHA256 è `25bfa667…`, uguale ad `AXIS_SHA`.
- **Argomenti:** quelli di r3 (`--holdout-context HepG2 --same-experiment h1_vcc2025=… --workers 4`), più le correzioni del passo A:
  - `--split-rule stable --split-salt rlead-2026-10-01`;
  - `--pool-min-per-library 64`;
  - `--eval-selection stratified`.

**Nessun training, nessun confronto di modelli.** Il file di stato `prepass.pkl` resta nell'output del kernel su
Kaggle: 1.375.714.890 byte, SHA256 `8dfa413c…`. Qui ci sono solo i file piccoli.

## Esito, misurato

**Verifica degli input.** I 183 shard e i 3 file di codice coincidono con i loro manifest (`verify.json`, `bad` vuoto). Le
cellule lette sono 2.609.698, come in r3.

**QC identico a r3.** `prepass/qc.json` è uguale, valore per valore, a quello di
`cellnet_tecnico_2026-10-01/esito/prepass_r3/prepass/qc.json`. Stessi dati, stesso asse e stessa lettura delle
etichette: le differenze qui sotto vengono solo dalle correzioni.

| Misura | r3 | r1 (corretto) |
|---|---|---|
| Cellule ammesse al training | 1.066.336 | 1.056.046 |
| Simboli nascosti (classe J nel contesto tenuto fuori) | 749 | 718, di cui 79 in comune con r3 |
| Simboli addestrabili | 7.490 | 7.490 |
| Cellule C / T / J nel contesto tenuto fuori (prima del QC) | 126.561 / 135.557 / 13.936 | 126.950 / 144.816 / 13.547 |
| Gruppi di valutazione | 1.008 (i più numerosi) | 1.021 (selezione stratificata per classe e chiave) |
| File di stato | 896.146.697 byte | 1.375.714.890 byte |

**Split stabili.** La regola cambia, quindi il sorteggio è nuovo: solo 79 simboli nascosti su 718 coincidono con r3.
È atteso: da qui in poi la decisione per simbolo non cambia più quando il corpus cresce. Il manifest del sorteggio
è in `splits.json`, alla voce `split`.

**Classi dopo il QC.** Con le etichette, 6.772 simboli hanno cellule di training. Dopo l'ammissione ne restano 2.384:
quasi tutti gli altri vengono dagli schermi genome-wide di HipSci, che restano fuori dal training per mancanza di
controlli, come già in r3. Nel contesto tenuto fuori 2 cellule passano da C a J (l'esempio registrato è CDCA8). Prima della correzione sarebbero state valutate come C senza cellule di training per quel bersaglio.

**Controlli per libreria** (`prepass/controls.json`, 81 chiavi):

| Chiave | Controlli ammessi | Librerie | Con 64 controlli propri nel pool | Cellule perturbate coperte dalla propria libreria |
|---|---|---|---|---|
| H1 (VCC 2025) | 38.176 | 48 | 48 | 100% |
| HepG2 | 4.976 | 56 | 52 | 97,6% |
| Jurkat | 12.011 | 55 | 53 | 99,0% |
| HipSci targeted, 19 linee | da 86 a 668 per linea | da 54 a 72 per linea | 0 | 0% |
| HipSci genome-wide, 58 chiavi | 0 | — | — | fuori dal training |

- **HepG2:** i numeri coincidono con la misura locale sul file grezzo (`reports/analisi/hepg2_locale_2026-10-02`:
  52 librerie, 97,6%, pool di 3.426). Le librerie `obs/batch` del file pubblico sono quindi le librerie degli
  shard.
- **HipSci targeted:** ogni libreria ha al massimo 23 controlli, quasi sempre meno di 10. Nessuna arriva a 64 né prima né dopo il
  limite del pool, quindi la correzione non cambia nulla: le cellule usano il pool comune della loro linea, e
  `controls.json` lo dichiara. *Interpretazione:* se il condizionamento per libreria conta, per HipSci serve una
  soglia più bassa o un raggruppamento delle librerie. È una scelta da registrare prima di un confronto, non qui.

**Costo.** Il pool più grande (HepG2 3.426, Jurkat 3.490, H1 3.072 righe, contro 2.048) porta il file di stato da
0,90 a 1,38 GB e la durata da 2.385 a 2.693 s. La memoria del training va misurata al primo run su GPU.

## Che cosa non dice

Non dice se le correzioni migliorano la previsione: per saperlo serve un training con una regola di lettura
registrata prima.

## File

| Percorso | Contenuto |
|---|---|
| `esito/run.py`, `esito/kernel-metadata.json` | il kernel inviato |
| `esito/verify.json`, `esito/env.json`, `esito/kernel_done.json` | verifica degli input, ambiente Kaggle, chiusura |
| `esito/prepass/` | `qc.json`, `splits.json`, `controls.json`, `prepass_done.json` |
| `esito/prepass.log`, `esito/rlead-prepass-r1.log` | log del prepass e del kernel |
