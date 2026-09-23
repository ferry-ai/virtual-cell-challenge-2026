# Controllo nullo del generatore con dispersione per gene — esito e applicazione della regola

Eseguito il 23 settembre, 03:17–03:36 locali, secondo `PRIMA_DEI_RISULTATI.md`:
- pilota dello stadio 45 con `--gene-dispersion --effects-scale 0`, 20 bersagli per contesto,
  400 cellule;
- conteggio con lo stadio 83, 9.200 controlli di riferimento.

Output in `null/calls.json`.

**Misurato:**

| contesto | n_pred mediano (min–max) | quota «in su» | geni con φ > 0 | φ mediano |
|---|---|---|---|---|
| A | 5 (1–7) | 0,61 | 13.454 | 0,165 |
| B | 15 (9–24) | 0,59 | 12.962 | 0,135 |
| C | 31 (21–40) | 0,82 | 12.187 | 0,083 |

Per confronto, il generatore di trial-01 senza dispersione chiama 543 / 582 / 764 geni per
bersaglio sul file del t11 (`reports/prediction_calls_2026-09-23/t11/calls.json`). Quello però
è misurato con gli effetti del t11, non a effetto nullo.

**Applicazione della regola:** la mediana supera 10 in B e in C. **Il t13 non si costruisce.**
La dispersione per gene riduce l'artefatto di uno o due ordini di grandezza ma non lo toglie.
In C resta una trentina di chiamate spurie, per l'82% «in su», cioè lo stesso ordine della
mediana stimata di n_conf.

**Interpretazione (ipotesi):** resta ciò che una dispersione per gene non può rendere, cioè
l'eterogeneità di stato fra cellule che muove molti geni insieme, e il legame fra profondità e
composizione. `ControlModel` modella gli stati e a effetto nullo chiamava 0 geni
([CP-0020](../../docs/checkpoints/0020-singola-cellula-cis-generatore.md) §3.3). Il generatore
pulito da usare per la leva della fedeltà resta quindi `ControlModel`, su Colab.
