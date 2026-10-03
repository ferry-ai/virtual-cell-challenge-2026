# Corsia B di H1, generazione

Le cellule della rete r3 vengono dal kernel `rcell-gen-h1-r3`, lanciato dopo la correzione del generatore. Usa quindi
`pi` = 1 per i modelli senza miscela: il valore è registrato blocco per blocco nei `cells_<braccio>.json` della radice
dati. Per H1 non c'è una generazione scartata, a differenza di HepG2 e RPE1 (`r3` scartata, `r3b` buona).

I bersagli sono 70: sono quelli di H1 con almeno 50 cellule e supporto, scelti con la regola di `choose_targets.py`
([targets.json](targets.json)). Le cellule vere sono al più 64 per bersaglio, con 2.048 controlli
([real_cells.json](real_cells.json)).
