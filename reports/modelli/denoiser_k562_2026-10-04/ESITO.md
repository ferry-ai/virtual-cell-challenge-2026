# Denoiser degli effetti K562: esito secondo la regola registrata

4 ottobre 2026, corse fra 02:17 e 02:20, ora del PC. Protocollo e codice nel commit 0bf6c2c, prima di ogni corsa.
I `result.json` sono in [esito/](esito/). **Sono coseni di un banco locale, non punteggi VCC.**

## 1. Esito

| Regola | Esito |
|---|---|
| Cancello tecnico | **passa:** 553 bersagli di test nella piega R; nessun NaN |
| **Passa** | **no.** Nella piega R `pca − k562` = **−0,004 [−0,008; −0,001]**; la discriminazione scende da 0,861 a 0,805 (−0,056, oltre il limite di −0,01) |
| Fase 2 (t32) | **nessuna** |

## 2. Numeri

| Piega (bersagli) | k scelto | coseno `k562` | coseno `pca` | coseno `mean_only` | discriminazione `k562` | discriminazione `pca` |
|---|---|---|---|---|---|---|
| R, RPE1 (553) | 1.024 | **0,106** | 0,101 | 0,027 | **0,861** | 0,805 |
| T, Tian 2021 (32) | 1.024 | **0,014** | 0,004 | 0,013 | **0,690** | 0,575 |
| H, HipSci (85) | 1.024 | **0,068** | 0,046 | 0,014 | **0,876** | 0,810 |

**In validazione il coseno sale in modo monotono con k e resta sotto la copia anche a k = 1.024.** Per esempio nella
piega R: da 0,019 (k = 8) a 0,040 (k = 1.024), contro 0,054 della copia.

## 3. Lettura

- **Misurato:** togliere a K562 le direzioni oltre le prime k peggiora sempre la previsione in un'altra linea, e
  peggiora molto la capacità di distinguere i bersagli.
- **Interpretazione:** ciò che di K562 si porta su un'altra linea non è nei programmi comuni a bassa dimensione, ma
  nei dettagli propri di ciascun bersaglio. Non è rumore da togliere.
- **Misurato:** la risposta comune da sola (`mean_only`) vale quasi zero di coseno, con discriminazione 0,5 per
  costruzione.
- **Previsioni registrate:**

  | Previsione | Atteso | Esito |
  |---|---|---|
  | `pca − k562` | da −0,005 a +0,04 | −0,004: dentro, al bordo basso |
  | k scelto | da 32 a 256 | 1.024: fuori |
  | `mean_only − k562` | da −0,08 a +0,02 | −0,078: dentro |
  | Discriminazione | da −0,03 a +0,02 | −0,056: fuori, sotto |
  | Passa | fiducia 0,4 | no |
