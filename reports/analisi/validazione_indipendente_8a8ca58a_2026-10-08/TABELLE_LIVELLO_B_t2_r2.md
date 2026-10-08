## Controlli tecnici del livello B

| Fold | Banco concluso | Bersagli | Controllo: PDS di T0 − T0 a righe scambiate (1 seme) | Banco utilizzabile |
|---|---|---:|---:|---|
| C-K562 | sì | 272 | +0.5733 | sì |
| C-iPSC | sì | 55 | +0.4386 | sì |

Nel fold C-K562 il controllo a righe scambiate è quello della corsa `reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/livello_b_k562_r1/failure`, sugli stessi dati: questo kernel ha eseguito la sola corsa principale.

Nel fold C-iPSC il controllo a righe scambiate è quello della corsa `reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/livello_b_ipsc_r1/completion`, sugli stessi dati: questo kernel ha eseguito la sola corsa principale.

## K2t0 — T2 − T0, sei membri (scala locale), 400 cellule per bersaglio, 5 semi

| Fold | Sei membri | Senza JAC | PDS | MSE | NMAE | FID | REACH | JAC |
|---|---|---|---|---|---|---|---|---|
| C-K562 | -0.0087 ± 0.0045 **ris.** | -0.0101 ± 0.0053 **ris.** | -0.0202 ± 0.0243 | +0.0000 ± 0.0000 | -0.0292 ± 0.0259 **ris.** | +0.0022 ± 0.0056 | -0.0031 ± 0.0328 | -0.0016 ± 0.0013 **ris.** |
| C-iPSC | +0.0023 ± 0.0125 | +0.0022 ± 0.0148 | +0.0184 ± 0.0798 | +0.0000 ± 0.0000 | -0.0014 ± 0.0065 | -0.0014 ± 0.0058 | -0.0048 ± 0.0392 | +0.0030 ± 0.0013 **ris.** |
| **macro, 2 fold** | -0.0032 ± 0.0074 | -0.0040 ± 0.0087 | -0.0009 ± 0.0298 | | | | | |

**Esito del §8 per K2t0 (T2:T0):** VALIDO E SFAVOREVOLE — regressione risolta della media o del PDS su: C-K562.

## K2 — T2 − T1, sei membri (scala locale), 400 cellule per bersaglio, 5 semi

| Fold | Sei membri | Senza JAC | PDS | MSE | NMAE | FID | REACH | JAC |
|---|---|---|---|---|---|---|---|---|
| C-K562 | -0.0079 ± 0.0041 **ris.** | -0.0090 ± 0.0048 **ris.** | -0.0202 ± 0.0272 | +0.0000 ± 0.0000 | -0.0220 ± 0.0249 | +0.0020 ± 0.0049 | -0.0050 ± 0.0337 | -0.0022 ± 0.0012 **ris.** |
| C-iPSC | +0.0022 ± 0.0129 | +0.0022 ± 0.0151 | +0.0222 ± 0.0792 | +0.0000 ± 0.0000 | -0.0026 ± 0.0067 | -0.0015 ± 0.0068 | -0.0071 ± 0.0410 | +0.0020 ± 0.0021 **ris.** |
| **macro, 2 fold** | -0.0029 ± 0.0078 | -0.0034 ± 0.0091 | +0.0010 ± 0.0295 | | | | | |

**Esito del §8 per K2 (T2:T1):** VALIDO E SFAVOREVOLE — regressione risolta della media o del PDS su: C-K562.

## K1 — T1 − T0, sei membri (scala locale), 400 cellule per bersaglio, 5 semi

| Fold | Sei membri | Senza JAC | PDS | MSE | NMAE | FID | REACH | JAC |
|---|---|---|---|---|---|---|---|---|
| C-K562 | -0.0008 ± 0.0023 | -0.0010 ± 0.0028 | -0.0000 ± 0.0031 | +0.0000 ± 0.0000 | -0.0072 ± 0.0060 **ris.** | +0.0002 ± 0.0011 | +0.0019 ± 0.0097 | +0.0006 ± 0.0003 **ris.** |
| C-iPSC | +0.0001 ± 0.0031 | -0.0000 ± 0.0036 | -0.0038 ± 0.0173 | +0.0000 ± 0.0000 | +0.0012 ± 0.0014 | +0.0001 ± 0.0021 | +0.0023 ± 0.0073 | +0.0010 ± 0.0015 |
| **macro, 2 fold** | -0.0003 ± 0.0014 | -0.0005 ± 0.0016 | -0.0019 ± 0.0089 | | | | | |

**Esito del §8 per K1 (T1:T0):** INCONCLUDENTE — macro dei sei membri non risolta.

## Solo i bersagli con voti nuovi (corsa «cambiati»)

| Fold | Bersagli | Coppia | Sei membri | Senza JAC | PDS | NMAE | FID | REACH |
|---|---:|---|---|---|---|---|---|---|
