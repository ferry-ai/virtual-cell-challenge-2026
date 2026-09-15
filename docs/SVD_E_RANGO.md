# SVD randomizzata e rango della base di risposta

Data: 2026-09-15. Distingue **implementato**, **eseguito**, **misurato** e
**ancora ipotizzato**. Non adotta la SVD randomizzata come default e non
alza il rango della base.

Punto di ingresso dei numeri: `reports/svd_2026-09-15/` per la sostituzione,
`reports/rank_2026-09-15/` per il rango. I run completi stanno in
`C:/Users/ferra/vcc2026-data/artifacts/` (D-001): `s001` esatta, `s002`
randomizzata, `r001` confronto di rango. Configurazioni:
`configs/benchmark_svd_exact.yaml`, `configs/benchmark_svd_randomized.yaml`,
`configs/benchmark_rank.yaml`. Codice: `src/vcc2026/benchmark/factorization.py`.

Continua [CP-0014](checkpoints/0014-go-slim-e-gpu.md) §3.4, che aveva misurato
tempi e valori singolari e aveva scritto D-029. Questo documento misura le
**predizioni**.

## 1. Implementato

- Un solo punto di fattorizzazione, `factorize(matrix, rank, spec)`, con due
  metodi: `exact` (`numpy.linalg.svd` economy, poi i primi *k*) e
  `randomized` (Halko, Martinsson & Tropp 2011, Alg. 4.4, iterazioni QR).
  Seed, oversampling e iterazioni sono argomenti, non default nascosti.
  Nessuna dipendenza nuova.
- La funzione **non centra**. La centratura resta nei caller
  (`MaskedLowRank`, `ModularFrozen._fit_basis`, `svd_codes`), visibile.
- Configurazione `factorization:` nei yaml. Senza il blocco, il comportamento
  è l'esatta di prima. I yaml storici non sono stati toccati.
- Bootstrap della metrica primaria: ogni replica ricampiona gli stessi
  bersagli e ricalcola `sum sse / sum sst`. È un oggetto distinto dalla media
  dei rapporti per bersaglio. Segni opposti fra le due aggregazioni non sono
  una contraddizione.
- Ranghi incompatibili con `min(n, p) − 1` escono dalla griglia, non vengono
  tagliati in silenzio allo stesso *k*.

Generatore, scorer e colonne dei descrittori non sono stati ridisegnati.

## 2. Eseguito

```bash
.\scripts\py.cmd scripts/60_compare_factorization.py --out reports/svd_2026-09-15
.\scripts\py.cmd scripts/51_run_modular_pilot.py --run-id s001 --config configs/benchmark_svd_exact.yaml --signatures <e001>/signatures <e003>/signatures
.\scripts\py.cmd scripts/51_run_modular_pilot.py --run-id s002 --config configs/benchmark_svd_randomized.yaml --signatures <e001>/signatures <e003>/signatures
.\scripts\py.cmd scripts/51_run_modular_pilot.py --run-id r001 --config configs/benchmark_rank.yaml --signatures <e001>/signatures <e003>/signatures
```

s001 e s002 condividono subsample seed 2026, split seed 2026 e 2027, 160
bersagli, tre fold, due protocolli, quattro bracci (lowrank e frozen, con e
senza contesto). r001 usa la SVD esatta e la griglia {16, 32, 64, 128}, un
solo split seed, dopo che s002 non ha superato la regola di A.

## 3. Misurato

Ogni numero ha un file. Dettaglio e tabelle: [CP-0015](checkpoints/0015-svd-randomizzata-e-rango.md) §3.

In breve:

- Sulla matrice 320 × 6.477, rango 16: randomizzata 9,74× più veloce,
  errore relativo sui valori singolari 1,05%, differenza fra le due
  ricostruzioni di rango 16 **18,5%**, angolo principale massimo 39°.
- Verdetto prefissato sulle predizioni: **not_compatible** (4 fold su 48
  fuori banda, tutti frozen con contesto, segni misti).
- Risparmio reale del run: 331 s → 207 s di orologio; 178 s → 53 s di
  training. Picco RSS invariato (~456 MiB).
- Rango: il lowrank sceglie 64 sul seen e perde tre decimi di MSE/nullo sul
  test, in tutti e tre i fold, contro la griglia {8, 16} di s001. Il frozen
  "sceglie" 128 su una griglia interna piatta.

## 4. Ancora ipotizzato

- Se `n_iter` > 2 avvicini i sottospazi abbastanza da rientrare nella banda
  sul frozen. Non misurato.
- Se 2.315 bersagli invece di 160 cambiano la selezione di rango. Non
  eseguito: il disaccordo inner/outer è già grande.
- Se una GPU accelererebbe *questa* SVD randomizzata. Non misurato, e D-029
  vieta il porting finché la sostituzione non è adottata.

## 5. Configurazione candidata

Non una nuova architettura. Per i run successivi di questo banco:

- `factorization.method: exact` (default). `randomized` resta un flag.
- `rank_grid: [8, 16]` come m002. Non 32/64/128.
- GO slim spento (D-028).
- Intervalli della primaria: `diff_paired_pooled`, non la sola media dei
  rapporti.
