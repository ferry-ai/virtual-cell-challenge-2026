# Banco del t35: lo spostamento dei conteggi letto con lo scorer vero, prima di decidere l'invio

4 ottobre 2026, notte. Claude Code per Alfredo, che ha chiesto in chat di «gradarlo sul nostro per capire se lanciarlo
in futuro». **Registrato prima di ogni numero di questo banco.** Le soglie non si spostano dopo i risultati.

## Perché

- Il t35 (`reports/invii/prediction_t35_2026-10-04/`, pacchetto pronto e non inviato) è il t34 più lo spostamento dei
  conteggi verso gli obiettivi della `rete_anti` (`reports/modelli/rete_l1_2026-10-04/`).
- Il banco della rete misura l'nMAE su porte approssimate, senza celle. Il controllo dello spostamento ha visto che
  cambia circa un terzo delle chiamate DE ([VERIFICA_SLIDE.md](../../modelli/rete_l1_2026-10-04/VERIFICA_SLIDE.md)).
- Serve il numero che conta: **la media dei sei membri**, con lo scorer vero, sulle cellule vere di linee tenute
  fuori.

## Come

- **Banco:** quello della strada C ([banco_tipo.py](../../trasferimento/strada_c_banco_2026-10-03/banco_tipo.py),
  importato senza modifiche).
  - Gira su Kaggle sugli stessi dataset rlab.
  - Per ogni linea L fra H1, KOLF, HepG2 e Jurkat: verità = metà A delle cellule di L, replica = metà B, controlli
    NTC di L, `cell_eval2` 0.16.0, scala locale (u − b)/(r − b).
- **Pannello:** i bersagli di L con almeno 40 cellule, coperti da K562 e con magnitudine esportata; al massimo 150,
  seme 2026.
- **Bracci,** tutti dal `ControlModel` kde di L con lo stesso flusso casuale:
  - `null`: nessun effetto;
  - `k562_a2`: l'effetto K562 ×2 con la regola d'ampiezza registrata della strada C. È l'analogo del t34 (t31 e t34
    sono K562 ×2);
  - `k562_a2_slide`: **le stesse cellule** di `k562_a2`, poi lo spostamento del t35 (`genera_l1.slide`, tetto ±2%
    di profondità, due passate).
    - **Obiettivo:** `sign(effetto del braccio) · |m|`, dove |m| è la magnitudine della `rete_anti` addestrata
      **senza la linea L** e senza il suo gruppo interno, come nella sua piega di banco (`obiettivi_linee.py`).
    - **Geni attivi:** CPM medio per cellula dei controlli ≥ 5, effetto ≠ 0, gene bersaglio escluso.

## Regola

- **Linea leggibile:** la replica batte la baseline in almeno 4 membri su 6 (cancello della strada C).
- **Confronto:** per ogni linea leggibile, `k562_a2_slide − k562_a2` sulla media dei sei membri scalati, con bootstrap
  appaiato sui bersagli (`banco_tipo.compare`).
- **Il t35 si invia in futuro solo se:**
  - la macro sulle linee leggibili è ≥ **+0,005**;
  - H1 è ≥ 0;
  - le linee leggibili sono almeno 3.

  Altrimenti il pacchetto resta non inviato e lo spostamento non entra nella ricetta in questa forma.
- **Si riportano anche,** senza che decidano: i sei membri grezzi dei due bracci (soprattutto nMAE, Jaccard, reach,
  fedeltà), `k562_a2 − null` e la quota d'obiettivo raggiunta.

## Previsione (registrata ora, soggettiva)

| Grandezza | Previsione |
|---|---|
| nMAE grezzo | `k562_a2_slide` sotto `k562_a2` su 3 linee su 4 |
| PDS e MSE | uguali fra i due bracci (bulk identico) |
| Macro `slide − t34` | da −0,02 a +0,02, centro 0; fiducia 0,3 che la regola passi |
| H1 | da −0,03 a +0,01 |

## Limiti

- Analogo del t34, non il t34: niente rete contrastiva sugli effetti, e gli effetti K562 sono quelli stimati sui
  frammenti con le formule della strada C, non le chiavi.
- Un seme. Pannelli di linee pubbliche, non A, B, C.
