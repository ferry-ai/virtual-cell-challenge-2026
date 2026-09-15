# Primo confronto modulare contro rete unica

Data: 2026-09-14. Questo documento distingue **implementato**, **eseguito**,
**misurato** e **ancora ipotizzato**. Non adotta un'architettura e non dichiara
un vantaggio scientifico.

Punto di ingresso dei numeri: `reports/benchmark_2026-09-14/`. Il run completo
sta in `C:/Users/ferra/vcc2026-data/artifacts/m001` (D-001). Configurazione:
`configs/benchmark.yaml`. Codice: `src/vcc2026/benchmark/`.

## 1. Implementato

Codice e configurazioni nel repository, coperti da test. Non è la prova che il
pilot sia andato a buon fine — quella sta nella sezione 3.

- Inventario machine-readable delle sorgenti (`src/vcc2026/benchmark/inventory.py`,
  `scripts/50_inventory_data.py`): contesto, dataset, bersagli, guide, donatore/batch
  se presenti, cellule, controlli, geni misurati, tipo di matrice, percorso.
  Distingue pseudobulk (media per cellula), conteggi a singola cellula, metadati
  soli, campioni e candidati non acquisiti.
- Universo genico = **intersezione dei geni effettivamente misurati**. La SVD e la
  loss vedono solo quell'universo. Il riempimento a zero è rifiutato
  (`assert_no_zero_fill`). Copertura persa dichiarata.
- Interfacce uniformi: descrittori con provenienza, predizione di delta con maschera,
  fit / inferenza / salvataggio / caricamento, split, valutazione proxy, risorse.
- Cinque bracci, più le varianti senza descrittore di contesto per i modelli
  condizionati:
  - A. ShrunkTransfer, ampiezza senza leakage del contesto di test
  - B. lineare a basso rango (ridge su base SVD mascherata)
  - C. MLP unica compatta sul vettore dei delta
  - D. base condivisa congelata + piccolo MLP sui coefficienti
  - E. come D con breve affinamento congiunto
- Due protocolli tenuti separati: contesto nuovo e bersaglio già visto altrove;
  contesto nuovo e bersaglio escluso da tutte le risposte di training. Le guide
  dello stesso bersaglio restano insieme.
- Alpha 0,1974 (trial K562→RPE1) è **vietato** nei fold che tengono fuori K562 o
  RPE1. Senza coppia interna al training si usa una costante prefissata
  (`predetermined_alpha: 1.0`), etichettata come euristica, non come calibrazione
  cross-context. Con coppia interna (K562 genome-wide → K562 essential) l'ampiezza
  è minimi quadrati sulla coppia, dichiarata *same-line limited*.
- I NTC del contesto da predire sono ammessi per il condizionamento, dichiarati, e
  dati a tutti i bracci. Le risposte perturbate di quel contesto non entrano in
  fit né in selezione.
- Metrica primaria fissata prima del confronto: `pooled_mse_vs_null` in spazio
  log2FC pseudobulk. Margine di non inferiorità: `null`. Le sei metriche VCC non
  si calcolano in questo run.
- Specifica del bundle a singola cellula mancante, senza scaricare atlanti
  (`missing_generator_bundle.json`).

Autoencoder, esperti, bagging e boosting **non** sono in questo esperimento.

## 2. Eseguito

Comandi, con destinazioni distinte, senza sottomissioni e senza servizi a pagamento.

```bash
.\scripts\py.cmd scripts/50_inventory_data.py --out reports/benchmark_2026-09-14
.\scripts\py.cmd scripts/51_run_modular_pilot.py --run-id m001
.\scripts\py.cmd -m unittest tests.test_modular_benchmark
python scripts/31_check_docs.py
```

Il runner scrive split, modelli, tabella e manifesti sotto
`C:/Users/ferra/vcc2026-data/artifacts/m001`. I file leggeri (inventario, tabella,
riepilogo, specifica del bundle) sono copiati in `reports/benchmark_2026-09-14/`.

## 3. Misurato

Ogni numero di questa sezione ha un file. Se il file non c'è, la riga non è una
misura.

### 3.1 Inventario (eseguito)

Fonte: `reports/benchmark_2026-09-14/inventory.json`.

| Voce | Valore |
|---|---|
| Contesti perturbati locali | K562, RPE1 |
| Bersagli condivisi k562_gwps ∩ rpe1_essential | 2390 |
| Geni sull'asse ufficiale condivisi fra gli stessi due | 6714 / 18533 |
| Pannello 2026 in k562_gwps | 272 / 300 |
| Pannello 2026 in rpe1_essential e k562_essential | 0 / 300 |
| Conteggi perturbati a singola cellula in locale | nessuno |
| Esperimento generator × predittore sulle sei metriche | bloccato |

Un gene assente da `var` è **non misurato**, non invariato. Lo dice lo stesso
JSON, campo `unmeasured_vs_unchanged`.

Due soli contesti perturbati: un test che ne esclude uno lascia **un** contesto
di training. L'inventario lo registra come limite, non come dettaglio.

### 3.2 Pilot predittivo

Fonte: `reports/benchmark_2026-09-14/summary.json` e `comparison_table.md`,
prodotti da `C:/Users/ferra/vcc2026-data/artifacts/m001/results.json` (72 righe,
223 s, picco RSS 505.606.144 byte). 160 bersagli casuali su 2350 condivisi
nelle firme e001.

- Spazio: log2FC pseudobulk. **Non è un punteggio VCC.**
- Universo: 6700/18.533 geni (con k562_essential) o 6714/18.533 (senza).
- Metrica primaria: `pooled_mse_vs_null` (più basso è meglio), fissata prima.
- Non inferiorità: non dichiarata (margine `null`).
- Vincitore: non dichiarato. `verdict_eligible` è no su ogni riga.

K562 → RPE1, bersaglio già visto, MSE/nullo:

| modello | 2026 | 2027 |
|---|---:|---:|
| shrunk_transfer | 0,9942 | 0,9955 |
| lowrank_linear | 0,9906 | 0,9906 |
| compact_mlp | 0,9974 | 0,9883 |
| modular_frozen | 0,9763 | 0,9737 |
| modular_joint | 0,9797 | 0,9939 |

Differenza appaiata modular_frozen − ShrunkTransfer: IC95 senza zero su entrambi
i seed (medie −0,013 e −0,011). La MLP unica a seed 2026 è *peggio* di
ShrunkTransfer (IC senza zero). Low-rank con/senza contesto: identici a quattro
decimali. `context_dependence_identifiable: false`.

RPE1 → K562, alpha prefissato 1,0: ShrunkTransfer 4,30 volte il nullo; tutti i
bracci sopra 1. Bersaglio mai visto, K562 → RPE1: ShrunkTransfer copertura 0;
gli altri circa 0,98. Nella direzione inversa gli appresi stanno a 1,63–2,51.

Esito del confronto architetturale: **inconcludente** per l'adozione. I numeri
esistono; non autorizzano a scegliere un modello né a dichiarare un vantaggio
sulla gara.

### 3.3 Generator × predittore

Non eseguito. Manca un bundle di conteggi perturbati reali con NTC appaiati.
La specifica del mancante è in
`reports/benchmark_2026-09-14/missing_generator_bundle.json`: campi, coperture
dichiarate, dimensioni stimate, modo di acquisizione. Nessun atlante è stato
scaricato.

## 4. Ancora ipotizzato

- Che una decomposizione modulare convenga sulla rete unica **in generale**.
- Che un descrittore di contesto appreso da NTC trasferisca ad A/B/C.
- Che l'α interno K562→K562 essential sia informativo per RPE1.
- Che un miglioramento del generatore dica qualcosa sul predittore o sulla
  modularità. Non lo dice: sono fattori distinti.
- Che questi proxy log2FC si traducano nelle sei metriche VCC.

Il prospetto `docs/PROSPETTO_MODELLO_2026-09-14.md` resta una proposta. Il
rapporto dei worker del 14 settembre è materiale valutato, non un insieme di
istruzioni: le obiezioni su leakage di alpha, NTC, asimmetria congelato/congiunto
e gate del generatore sono state tradotte in vincoli di codice, non in un
verdetto.

## 5. Cosa questo esperimento non è

- Non è un test di apprendimento generale della dipendenza dal contesto.
- Non è un punteggio VCC e non è una sottomissione.
- Non è una scelta di modello sul test esterno.
- Non è una dimostrazione che ShrunkTransfer, la MLP o la modularità "vincano".

## 6. Esperimento successivo che ridurrebbe di più l'incertezza

Uno solo: **un bundle a singola cellula di conteggi perturbati reali più NTC
appaiati**, dello stesso batch, letto a blocchi, sulle sei metriche VCC, con lo
stesso predittore tenuto fisso e il solo generatore variato — e, simmetricamente,
lo stesso generatore con predittori diversi. Senza quello, ogni conclusione sul
predittore resta in spazio proxy, e ogni conclusione sul generatore resta
un'ipotesi. I candidati più piccoli sono nella specifica del bundle mancante
(HepG2 Nadig ~0,85 GB compressi, oppure RPE1 single-cell ~1,24 GB), entrambi a
copertura 0/300 del pannello: banco metodologico, non benchmark dei 300 bersagli.
