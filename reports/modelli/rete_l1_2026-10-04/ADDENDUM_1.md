# Addendum 1: la rete passa la regola, ma H1 dice di non mandarla così

4 ottobre 2026, sera. Scritto **dopo** il banco della rete registrata e **prima** del banco della variante qui
descritta. Il commit che aggiunge questo file ne fissa l'ora.

## Che cosa ha detto il banco (misurato)

Uscita: `vcc2026-data/processed/rete_l1_2026-10-04/bench/result.json`, codice del commit 059e76a. Un primo lancio,
fermato prima di qualsiasi uscita perché rileggeva gli array a ogni bersaglio, è in `bench_launch1_stopped.log`.

| Piega | `copia1` | `copia2` | `rete` | Segni giusti `copia1` → `rete` |
|---|---|---|---|---|
| H1 | 0,999 | 1,098 | **1,495** | 0,59 → 0,52 |
| KOLF | 1,001 | 1,021 | 0,826 | 0,50 → 0,62 |
| RPE1 | 0,971 | 0,984 | 0,967 | 0,61 → 0,56 |
| HepG2 | 0,962 | 0,994 | 0,876 | 0,62 → 0,61 |
| Jurkat | 0,930 | 0,978 | 0,814 | 0,70 → 0,64 |
| HipSci | 0,988 | 1,069 | 0,713 | 0,66 → 0,70 |
| Tian | 1,012 | 1,034 | 0,936 | 0,53 → 0,27 |

- **Regola registrata:** passa. Macro **0,947 [0,933; 0,961]**, `rete` meglio di `copia2` in 6 pieghe su 7.
- **Ma H1 va a 1,495.** Ed è la piega più simile al pannello: bersagli tipici, non essenziali, verità pulite e geni DE
  con |y| piccolo (mediana 0,26 contro circa 0,5 nelle altre linee).
  - Lì la rete perde il segno (0,52) e mette magnitudini più grandi della verità (mediana 0,34).
  - Interpretazione: il segno della rete viene dai priori dei geni, cioè dalla risposta generica degli schermi su geni
    essenziali, che sul pannello non vale. Fra le diagnosi del 4/10 è la terza (contesto e regime) e la quarta (banco
    che sovrastima).
- **Decisione:** questa rete non si genera e non si invia, anche se la regola formale passa.

## Variante registrata ora: `rete_anti`

- **Segno:** è quello del transfer, cioè il log2FC K562, e la rete non lo può cambiare. L'uscita è
  `sign(k) · softplus(f(ingressi senza segno))`, e con `k = 0` l'uscita è 0.
- **Ingressi:**
  - `|k|`, il rapporto segnale/rumore senza segno;
  - i priori del gene moltiplicati per `sign(k)` (dicono se il gene va di solito nella stessa direzione);
  - la forza del bersaglio;
  - le due espressioni;
  - il flag misurato.
- **Che cosa impara la rete:** solo la magnitudine L1-ottima dato il segno. Con un segno giusto con probabilità
  `q > 0,5`, la magnitudine ottima è un quantile basso di |y| che sale con `q`.
- **Banco:** stesso codice, dati, pieghe e arresto. Si confronta con `zero` e `copia1`.
- **Regola, più severa della registrata:**
  - macro `rete_anti` ≤ 0,99 con IC superiore < 1;
  - `rete_anti` < 1,0 **anche in H1**;
  - `rete_anti` ≤ `copia1` in almeno 5 pieghe su 7.

  Se non passa, niente invio stanotte.
- **Generazione, se passa:**
  - il segno degli obiettivi è quello dell'effetto t34 che si genera (osservato e diverso da 0), così che i membri di
    direzione restino quelli del t34;
  - la magnitudine viene dalla rete;
  - i geni senza effetto t34 (bersagli non coperti, geni non espressi) restano fuori dallo spostamento.
- **Previsione e regola dell'invio:** quelle di `prediction_t35_2026-10-04/prediction.json`, invariate.
