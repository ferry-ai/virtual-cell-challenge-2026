# CP-0015 — SVD randomizzata misurata; il rango oltre 16 non trasferisce

- **Data:** 2026-09-15
- **Tipo:** esperimento
- **Redatto da:** agente Grok (Grok 4.6)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Due, in quest'ordine, e tenute distinte.

**A.** Sostituire la SVD completa con una randomizzata di rango *k* riduce il
costo della fattorizzazione senza spostare `pooled_mse_vs_null` fuori da una
banda prefissata, sugli stessi dati e gli stessi split?

**B.** Il rango 16 della base di risposta limita la qualità predittiva, oppure
un rango scelto in validazione interna fra 16, 32, 64 e 128 predice meglio un
contesto tenuto fuori?

## 2. Cosa è stato fatto

```bash
.\scripts\py.cmd -m unittest tests.test_factorization tests.test_modular_benchmark
.\scripts\py.cmd scripts/60_compare_factorization.py --out reports/svd_2026-09-15
.\scripts\py.cmd scripts/51_run_modular_pilot.py --run-id s001 --config configs/benchmark_svd_exact.yaml --signatures <e001>/signatures <e003>/signatures
.\scripts\py.cmd scripts/51_run_modular_pilot.py --run-id s002 --config configs/benchmark_svd_randomized.yaml --signatures <e001>/signatures <e003>/signatures
.\scripts\py.cmd scripts/51_run_modular_pilot.py --run-id r001 --config configs/benchmark_rank.yaml --signatures <e001>/signatures <e003>/signatures
python scripts/31_check_docs.py
```

Regola di sostituzione **scritta nei due yaml prima dei run**: la randomizzata
è compatibile come drop-in se, su ogni fold, l'intervallo bootstrap appaiato
al 95% di (randomizzata − esatta) su `pooled_mse_vs_null` sta interamente in
(−0,01, 0,01). Non è una non-inferiorità sull'architettura. I vettori
singolari non sono il criterio.

Il confronto di rango usa la SVD **esatta**, perché A non ha superato quella
regola. GO slim spento. Descrittori, loss, griglia di ridge, budget MLP e
generatore come in m002. Tre fold biologici, entrambi i protocolli, con e
senza contesto. Rango scelto solo sulla validazione interna.

Niente download, niente GPU, niente sottomissioni.

## 3. Cosa si è osservato

### 3.1 Fattorizzazione isolata, matrice reale

Fonte: `reports/svd_2026-09-15/factorization_comparison.json`.
Una matrice di training del fold K562+RPE1 → HepG2, protocollo seen, 160
bersagli: **320 × 6.477**, universo 6.477/18.533.

| Rango | Tempo esatta (s) | Tempo randomizzata (s) | Guadagno | Errore rel. valori singolari | ‖A_k^rand − A_k^ex‖ / ‖A_k^ex‖ | Angolo can. max | Varianza esatta |
|---|---|---|---|---|---|---|---|
| 16 | 1,310 | 0,135 | 9,74× | 1,05% | 0,185 | 39,4° | 0,499 |
| 32 | 1,763 | 0,261 | 6,75× | 1,08% | 0,193 | 41,2° | 0,614 |
| 64 | 1,446 | 0,476 | 3,04× | 1,45% | 0,201 | 64,1° | 0,745 |
| 128 | 1,391 | 1,277 | 1,09× | 1,48% | 0,198 | 87,1° | 0,869 |

SVD completa (tutti i 319 componenti): 1,46 s best / 1,74 s mediana.
Picco RSS del worker esatto a k=16: 159,4 MiB; randomizzato: 114,0 MiB.
Tre seed della randomizzata a k=16: errore di ricostruzione 0,709–0,710, ma
le ricostruzioni fra seed differiscono del 23–25% in Frobenius.

### 3.2 Predizioni fuori campione, s001 contro s002

Fonte: `reports/svd_2026-09-15/prediction_comparison.json`.
48 righe, stessi 160 bersagli, stessi split. Banda prefissata 0,01.

| Esito sulla banda | N |
|---|---|
| Intervallo interamente dentro (−0,01, 0,01) | 27 |
| Intervallo più largo della banda | 8 |
| Intervallo interamente fuori da 0 oltre la banda | 4 |
| Altri (bordo) | 9 |
| **Verdetto prefissato** | **not_compatible** |

Le quattro violazioni sono tutte `modular_frozen__with_ctx`. Tre sul
protocollo seen (randomizzata *meglio* di ~0,03), una sull'unseen verso K562
(randomizzata *peggio* di 0,037). Il segno non è stabile.

Somma dei tempi di training: **177,82 s** esatta, **53,22 s** randomizzata,
risparmio **124,6 s** (3,34× sul solo fit). Orologio dei due run: **331 s**
contro **207 s** (124 s, il 37% del run esatto). Picco RSS dei manifesti:
456,0 MiB e 457,1 MiB — la SVD non è il collo di bottiglia di memoria.

Sulle stesse 48 coppie, pooled e media dei rapporti per bersaglio hanno
**segno opposto in 13 casi**. Non è una contraddizione: sono due aggregazioni.

### 3.3 Confronto di rango, r001

Fonte: `reports/rank_2026-09-15/rank_summary.json` e
`C:/Users/ferra/vcc2026-data/artifacts/r001/results.json`.
24 righe, seed 2026, griglia {16, 32, 64, 128}, SVD esatta. Orologio 207 s,
somma train 118 s, picco RSS 456,6 MiB.

Ranghi scelti in validazione interna:

| Braccio | 16 | 32 | 64 | 128 |
|---|---|---|---|---|
| lowrank con contesto | 3 (tutti unseen) | 0 | 3 (tutti seen) | 0 |
| lowrank senza contesto | 3 (tutti unseen) | 0 | 3 (tutti seen) | 0 |
| frozen con contesto | 2 | 1 | 0 | 3 |
| frozen senza contesto | 2 | 2 | 0 | 2 |

La griglia interna del frozen è **piatta** (differenze di val_mse ~10⁻⁴).
Quella del lowrank no: a rango 128 con ridge 1 la val_mse raddoppia.

Confronto appaiato r001 contro s001 (griglia {8, 16}) sugli **stessi** split
seed 2026. Positivo = r001 peggio. Sul protocollo seen, il lowrank che ha
scelto 64 contro l'8 di s001:

| Test | Δ pooled (r001 − s001) | IC95 | esclude 0 |
|---|---|---|---|
| → HepG2, con contesto | +0,260 | [0,162, 0,346] | sì |
| → HepG2, senza | +0,347 | [0,240, 0,437] | sì |
| → RPE1, con | +0,137 | [0,101, 0,184] | sì |
| → RPE1, senza | +0,143 | [0,106, 0,193] | sì |
| → K562, con | +0,213 | [0,173, 0,271] | sì |
| → K562, senza | +0,276 | [0,224, 0,348] | sì |

Il frozen a 128 contro 16, stesso fold verso HepG2: −0,032 [−0,038, −0,024]
(r001 meglio, piccolo). Verso RPE1: +0,0005, IC che contiene zero. Verso K562
a rango 32: −0,016. Sull'unseen il lowrank sceglie 16 e sta vicino a s001.

### 3.4 Contesto, seen contro unseen (r001)

Fonte: `paired_differences` in
`C:/Users/ferra/vcc2026-data/artifacts/r001/results.json`, aggregazione
`diff_paired_pooled` (con − senza; negativo = il contesto aiuta).

Sul seen: il contesto aiuta il frozen verso HepG2 (−0,103) e K562 (−0,183);
aiuta il lowrank verso RPE1 (−0,029) e K562 (−0,178); **peggiora** il lowrank
verso HepG2 (+0,067). Sull'unseen: il contesto **peggiora** verso HepG2 sul
lowrank (+0,163) e sul frozen (+0,027); aiuta verso K562. Due fold hanno
segno opposto fra pooled e media dei rapporti.

## 4. Interpretazione e incertezza

**Misurato:** tutto il §3.

**Interpretazione (A).** L'1% di errore sui valori singolari non basta. Le
due basi di rango 16 ricostruiscono A con errori simili (~0,71) ma *fra loro*
differiscono del 18%, e un angolo principale arriva a 39°. Sulle predizioni,
la regola scritta prima dei run non è soddisfatta: quattro fold del frozen
con contesto escono dalla banda, e in direzioni opposte. La randomizzata
resta disponibile, non diventa il default. Il risparmio vero, su questo
formato, è 124 s di orologio su un run da 331 s, non 9,7×, perché la SVD non
è tutto il run. Il picco RSS non si muove.

**Interpretazione (B).** Il rango che spiega più varianza in training (128:
87%) non è il rango che predice un contesto nuovo. Il lowrank *sceglie* 64
sul seen e ci perde tre decimi di MSE/nullo sul test, in tutti e tre i fold.
Il frozen "sceglie" 128 su una griglia piatta: non è una selezione, è rumore.
La griglia candidata resta {8, 16}. Non si adotta un rango da un fold.

**Perché potrebbe non significare questo.** Pilot da 160 bersagli su 2.315.
Un effetto piccolo di rango 32 sul frozen potrebbe stare sotto la risoluzione;
la griglia interna già dice che 16 e 128 non si distinguono lì. La banda 0,01
è stretta rispetto alla variabilità del frozen e larga rispetto a un lowrank
stabile: è la regola che ci siamo dati, non una proprietà dei dati. n_iter=2
è il valore dichiarato; più iterazioni potrebbero avvicinare i sottospazi, e
quella è un'altra misura.

## 5. Spiegazione semplice

Immagina di riassumere una tabella enorme con 16 direzioni principali. Farlo
in modo approssimato è più veloce — qui circa dieci volte sulla sola
fattorizzazione. Ma «i numeri in diagonale coincidono all'1%» non dice se
stai guardando lo stesso riassunto: due riassunti possono avere le stesse
lunghezze e puntare altrove. L'abbiamo controllato sulle previsioni, con una
soglia scritta prima. Su alcuni confronti il riassunto veloce spostava il
punteggio oltre quella soglia, e non sempre dalla stessa parte. Quindi non lo
sostituiamo in silenzio.

Sulle 16 contro 32, 64, 128: in allenamento, 64 e 128 catturano più
movimento. Fuori, sul contesto che il modello non ha visto, il lineare a 64
fa *peggio* di quello a 8, in tutti e tre i tipi cellulari. Avere più
manopole in palestra non è saperle usare in gara.

## 6. Conseguenze

- **D-029 resta attiva**, e non è soddisfatta la sua condizione di riapertura
  sulla GPU: la randomizzata esiste, è misurata, **non** è adottata come
  drop-in. Nessun porting.
- **D-030**: la griglia di rango resta {8, 16}. 32/64/128 non diventano il
  default.
- `factorization.method` è configurabile (`exact` predefinito).
- L'intervallo di `pooled_mse_vs_null` è un bootstrap appaiato del rapporto
  delle somme, tenuto distinto dalla media dei rapporti per bersaglio.
- Non si allarga il pilot ai 2.315 bersagli: il disaccordo inner/outer sul
  lowrank è già grande e ripetuto su tre fold. Ampliare servirebbe se il
  confronto fosse incerto.

## 7. Cosa corregge

- **Non corregge CP-0014** sul GO slim né sul fatto che il codice non usi una
  GPU. Corregge l'uso che si poteva fare del suo §3.4: l'1,3–1,6% di errore
  sui valori singolari **non** era una misura sulle predizioni, e su questa
  matrice l'1,05% convive con un 18% di differenza fra le due ricostruzioni
  di rango 16. Il 25–30% di varianza al rango 16 era su matrici HepG2 9.023
  geni; qui, 320 × 6.477, il rango 16 cattura il **50%**. Sono due matrici.
- Non adotta un'architettura. Non tocca D-028.

## 8. Domanda di comprensione

Se i valori singolari di una SVD randomizzata coincidono all'1% con quelli
esatti, perché questo checkpoint rifiuta comunque di dichiararla
equivalente — e che cosa, nella tabella del lowrank a rango 64, mostra che
«più varianza spiegata» non è «meglio in test»?
