# Quanto spazio avrebbe il gate sui contesti ufficiali

Conteggi sulle sole cellule di controllo di A, B e C, lette con `inference.read_basal_profile`. Non è una previsione e non è un punteggio. Prodotto da `scripts/70_context_presence_audit.py`.

| contesto | cellule | molecole totali | conteggi attesi per un gene a 1 CPM | geni a zero | geni < 1 CPM | geni < 5 CPM | bersagli < 5 CPM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 18,400.0 | 388,857,059 | 389 | 2398 | 7336 | 8610 | 1 |
| B | 18,400.0 | 367,814,894 | 368 | 2853 | 7470 | 8923 | 5 |
| C | 18,400.0 | 389,280,268 | 389 | 2317 | 6876 | 8409 | 6 |

Geni sotto 1 CPM in **tutti** i contesti: 5190; in almeno uno: 9148.

Geni spenti in un contesto e accesi (≥ 10 CPM) in un altro — è l'unica parte su cui un gate di contesto può agire diversamente da un filtro globale:

| sorgente → destinazione | geni |
| --- | ---: |
| B->A | 729 |
| C->A | 839 |
| A->B | 552 |
| C->B | 480 |
| A->C | 501 |
| B->C | 318 |
