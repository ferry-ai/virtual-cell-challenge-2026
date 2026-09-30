# Controllo del generatore — protocollo del 29 settembre

Esplorazione tecnica sui soli controlli A/B/C, prima del calcolo. Non misura precisione
dei segni perturbati né un punteggio ufficiale. Il generatore di produzione non cambia.

- Profilo atteso: tutti i controlli, letti a flusso.
- Riferimento DE: 1.500 controlli per contesto, scelti con seme 20260929; il gruppo
  `real` usa altri controlli. Questa riduzione è necessaria per la memoria durante
  l'impacchettamento concorrente. I conteggi DE sono confrontabili fra bracci in questa
  prova; non direttamente con quelli storici su 9.200 controlli.
- Tre repliche indipendenti da 400 cellule. Effetto nullo. Media pooled di produzione.
- Bracci: reali, Poisson, Gamma-Poisson con dispersione per gene moltiplicata per
  0,25, 0,5 e 1. Controllo aggiuntivo: dispersione piena con media CPM per cellula
  come profilo, per separare la forma della distribuzione dalla media.
- Wilcoxon e BH di `fast_scorer_de`, soglia p aggiustato <0,05, geni con media CPM
  nei controlli di riferimento >5. Si riportano n_pred, quota positiva e deriva del
  profilo aggregato. Nel nullo si tratta di chiamate spurie; non di n_conf della
  verità perturbata, che resta ignota.

Regola di lettura: la diminuzione di n_pred documenta la correzione dell'artefatto.
Non decide quale braccio migliori la gara. Nessuna soglia di n_pred chiude un
candidato: per la selezione occorre lo scorer a sei membri sui bersagli tenuti
fuori. Il braccio con media per-cell può diminuire un bias DE e introdurre una
deriva MSE: si legge insieme all'energia della differenza di profilo.

Il fit di dispersione è stimato sugli zeri con 1.000 library size campionate,
per contenere la memoria. I valori sono diagnostici, non una nuova ricetta.
