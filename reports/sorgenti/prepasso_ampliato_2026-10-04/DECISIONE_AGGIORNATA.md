# Pre-passo del corpus ampliato: la decisione del 4/10 corretta da una misura (4/10, 07:35)

[DECISIONE.md](DECISIONE.md) fissava il livello 64 «prima di ogni misura del suo effetto». La misura è arrivata ed è
contraria. Questa pagina la registra e corregge la scelta; DECISIONE.md resta com'era.

## La misura

Studio dei campioni annidati per fold, H1 esclusa, sole cellule di classe training (`rcell-v4-nested-fold-h1-r1`,
`--classes train --dispersion`). Regola di sufficienza congelata prima dei numeri in
[CAMPIONI_ANNIDATI.md](../../modelli/rete_ancorata_v4_2026-10-03/CAMPIONI_ANNIDATI.md) §4, applicata con
`nested_rule.py` ([decisione](../../modelli/rete_ancorata_v4_2026-10-03/esito/nested_fold_h1_r1/decision.md)).

| Unità | Livello raccomandato | r specifico mediano a 64 (p10) |
|---|---|---|
| A549 | 256 (sufficiente) | 0,675 (0,491) |
| HepG2 | 128 (sufficiente) | 0,910 (0,720) |
| K562 essenziali | 256 (sufficiente) | 0,701 (0,552) |
| K562 GWPS | 512 (non giudicabile) | 0,595 (0,465) |
| RPE1 | 256 (sufficiente) | 0,695 (0,544) |
| Jurkat, KOLF, neuroni | 512 (non giudicabile o senza perdita) | — |

Ai livelli raccomandati restano 3.222.119 cellule su 3.609.008 (89 %); a 64 ne resterebbero 1.410.206, con perdita di
segnale specifico in ogni unità giudicabile.

## La correzione

- **Il livello 64 non è adottato** per il corpus di training: la regola congelata lo giudica insufficiente.
- Livelli per unità: quelli raccomandati dalla regola, fold per fold. Per le sorgenti nuove senza studio (Orion,
  KOLF pan-genome, CD4), che sono genome-wide come K562 GWPS (circa 150–200 cellule per bersaglio), vale per analogia
  il livello 512, cioè quasi tutte le cellule, finché uno studio sulle loro cellule di training non dice altro.
- Conseguenza: il campionamento riduce le cellule solo del 10–15 % circa. Il pre-passo su tutto il corpus
  (circa 18–19 milioni di cellule) non entra nelle 12 ore di un kernel con 2 processi. La strada diventa quella
  scartata nella prima versione: **pre-passo per sorgente con unione degli stati**, cioè una parte indipendente dal
  fold (QC, impronte, serbatoi dei controlli, somme per chiave e bersaglio) per kernel e sorgente, e una parte per fold
  (classi, somme di training, gruppi di valutazione) che li unisce. È codice nuovo su un passo validato: va scritto con
  i test di parità contro il pre-passo attuale sul corpus pilot (stesso stato, a meno dell'ordine).
- `build_sampled_shards.py` resta utile per livelli alti e per pilot dichiarati. Il kernel di HCT116 a livello 64
  (`vcc-sampled-hct116-l64-r3`) serve ora come prova tecnica del costruttore, non come corpus.
