# Regola del t13 (generatore con dispersione per gene), scritta prima dei piloti — 23 settembre 2026

Scritta intorno alle 03:25 locali del 23 settembre, prima di qualunque pilota con
`--gene-dispersion`. Il t11 era in impacchettamento e senza punteggio. Autore: agente (Claude).
Ablazione autorizzata (`reports/trial_2026-09-22/autorizzazioni.md`).

## Perché

Lo stadio 83 sul file del t11 (`reports/prediction_calls_2026-09-23/t11/calls.json`) misura:
il generatore di trial-01 chiama 543–764 geni per bersaglio, l'83–85% «in su». Nei contesti
di validazione la mediana di geni significativi del riferimento è stimata a 30–50 (docstring
dello scorer). La fedeltà di questa famiglia (0,458–0,461 su trial-01, t08, t10) è quindi la
precisione di chiamate in gran parte spurie. Il t13 toglie l'artefatto e lascia le chiamate
agli effetti trasferiti.

## Regola

1. **Generatore:** quello di trial-01 (stadio 45, `trial-ext-profile`, seme 20260912) con
   `--gene-dispersion`, cioè Gamma-Poisson per gene adattata agli zeri dei controlli di
   ciascun contesto. Nient'altro cambia nel generatore.
2. **Controllo nullo, prima di tutto:** pilota con `--effects-scale 0`, 20 bersagli per
   contesto, conteggio con lo stadio 83 (9.200 controlli di riferimento). **Se la mediana di
   n_pred supera 10 in un contesto, il t13 non si costruisce**: la dispersione per gene non
   basta a togliere l'artefatto.
3. **Effetti:** quelli del migliore fra t08 e t11 per punteggio ufficiale. A parità entro
   0,005 vale il t08, che ha meno sorgenti.
4. **Ampiezza:** fattore di scala A in {1, 2,5, 5, 10} sugli effetti del file, già
   moltiplicati per 0,197. Si sceglie il **più piccolo** A che dà n_pred mediano ≥ 60 in tutti
   e tre i contesti, nello stesso pilota. Se nessuno ci arriva, A = 10.
5. Stesso seme, stessi 20 bersagli per ogni A, perché i conteggi si confrontino.

## Che cosa mi aspetto (previsione, non misura)

- Fedeltà grezza sopra 0,5 se i segni trasferiti sulle prime chiamate sono giusti più della
  metà delle volte (55% sui geni confidenti fra K562 e CD4, CP-0028).
- MSE sotto 1,15: senza artefatto la MSE a effetto nullo dovrebbe scendere verso 1.
- PDS: incerta. Un'ampiezza più grande alza il segnale rispetto al rumore, e la dispersione
  alza il rumore del pseudobulk.

La banda numerica si registra in `reports/prediction_t13_*` prima dell'invio.
