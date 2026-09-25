# CP-0038 — Il t17 in classifica: +0,109, pari al t15; HEK293T a pesi uguali non è attribuibile

- **Data:** 2026-09-25
- **Tipo:** esperimento
- **Redatto da:** agente (Claude Opus 5.5)
- **Revisione umana:** no. Invio autorizzato dal proprietario in chat il 24 settembre
  (`reports/trial_2026-09-22/autorizzazioni.md`).
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Aggiungere Orion HEK293T come quarta sorgente, a pesi uguali, sulla ricetta del t15 alza il
punteggio?

## 2. Cosa è stato fatto

- **Ricetta** `configs/recipes/t17.json`: il t15 più `orion_hek293t` a peso 1, cache r5 (che
  riproduce r4 per le altre tre sorgenti), ampiezza 0,4285 scelta perché il q99 mediano di
  |ln fc| coincida con quello del t15 (0,229).
- **Previsione e regola** registrate il 24 settembre prima della generazione
  (`reports/prediction_t17_2026-09-24/prediction.json`): banda +0,095…+0,125; t17 − t15 fra
  −0,01 e +0,015; ±0,005 come soglie di lettura.
- **Invio** dalla catena dopo il t16, alle 00:43 UTC del 25; pubblicato alle 01:16 UTC
  (`reports/trial_2026-09-24/submit_t17_started.txt`, `submit_t17_raw.json`,
  `status_4su3dF6Up12QhdCfnNgE.json`).

## 3. Cosa si è osservato

**Misurato — il punteggio.** **+0,108774**, rango 448: t17 − t15 = +0,0012.

**Misurato — i grezzi pubblicati** (`reports/prediction_t17_2026-09-24/comparison.json`):

| membro | t15 | t17 | t17 − t15 |
|---|---|---|---|
| `pds_cosine` | 0,7743 | 0,7700 | −0,0043 |
| `de_wilcoxon_lfc_nmae` | 0,9503 | 0,9485 | −0,0018 (meglio) |
| fedeltà direzionale | 0,4769 | 0,4752 | −0,0016 |
| `reach` | 0,1389 | 0,1570 | +0,0181 |
| Jaccard | 0,0325 | 0,0324 | −0,0001 |
| `mse` | 1,5794 | 1,5022 | −0,0773 (scalato 0 in entrambi) |

Punteggio, differenza e i due membri previsti (`pds_cosine` 0,76–0,79, fedeltà 0,47–0,49)
stanno dentro gli intervalli registrati.

## 4. Interpretazione e incertezza

**Esito della regola scritta prima:** |t17 − t15| < 0,005, quindi «non conclusivo; non
attribuire».

**Interpretazione, non misura:** la quarta sorgente sposta i membri in versi opposti,
`reach` su e `pds_cosine` giù, e il saldo è nullo. Il confronto non isola l'informazione di
HEK293T: cambiano insieme la miscela e l'ampiezza per bersaglio (R-016 nel registro: il q99
mediano coincide, ma 22 bersagli su 300 cambiano q99 di oltre il 20%).

**Incertezza:** un solo invio, all'ampiezza del t15; all'ampiezza del t16 il confronto
potrebbe andare diversamente.

## 5. Spiegazione semplice

Abbiamo aggiunto un quarto esperimento pubblico alla media. Il voto è rimasto quello di
prima: il nuovo esperimento aiuta un po' in una misura e peggiora un po' in un'altra.

## 6. Conseguenze

- **HEK293T non entra nella ricetta di riferimento**, che resta a tre sorgenti (t16).
- Riprovarlo ha senso solo sulla ricetta del t16 e con un fattore alla volta; non ha priorità
  sugli invii che proseguono la curva dell'ampiezza ([CP-0037](0037-t16-ampiezza-quadrupla.md)).
- R-016 resta aperta: la domanda sull'informazione di HEK293T non è chiusa.

## 7. Cosa corregge

Nessuna conclusione precedente.

## 8. Domanda di comprensione

Perché una sorgente che migliora `reach` di +0,018 può lasciare invariato il punteggio?
