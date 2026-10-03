# Corsia B: la regola registrata sulle tre linee (r3)

3 ottobre 2026, dopo le 14:57 CEST (ora letta con `date`). `decide_lane_b.py` applica il §6 del
[protocollo](../../PROTOCOLLO.md) alle tabelle a sei membri delle tre linee: «gli stessi confronti sul punteggio locale
a sei membri, con la stessa soglia». I bracci sono quelli del §5: le cellule generate da ogni braccio della rete e il
transfer passato per il generatore. Misurato in [decision_lane_b.json](decision_lane_b.json).

| Confronto (media locale dei sei membri) | H1 | HepG2 | RPE1 | Esito |
|---|---:|---:|---:|---|
| Q1: cellule `cells` − cellule `mean` | +0,116 | +0,324 | −0,002 | passa (2 su 3, media +0,146) |
| Q2: cellule `cells` − transfer | −0,358 | −0,635 | −0,466 | non passa (0 su 3) |
| Q3: cellule `cells` − cellule `generic` | −0,015 | +0,525 | +0,096 | media +0,202: la rete usa il bersaglio |

La clausola di espansione della corsia B (cellule della rete sopra il transfer in almeno 2 linee su 3) **non scatta**.
L'esito è coerente con il verdetto della corsia A e con la decisione del proprietario (§11): niente espansione, si passa
alla rete ancorata al transfer.

**Membro per membro (misurato):**
- Q1 passa soprattutto per NMAE, con H1 +0,78 e HepG2 +1,85. Il PDS dà +0,04 in media, REACH −0,03. Le cellule del
  braccio `mean` sono soprattutto più lontane in NMAE.
- Nella media locale le cellule dei tre bracci della rete restano sotto la baseline, da −0,91 a −0,07. Il transfer sta
  sopra, fra 0,22 e 0,28.
- Lo spostamento della rete passato per il generatore è descrittivo, fuori dalla regola. Supera le cellule della rete in
  tutte e tre le linee, ma resta sotto il transfer in tutte e tre: −0,26 su H1, −0,04 su HepG2, −0,19 su RPE1.
- In scala locale MSE vale 0 per ogni braccio, quindi la media si muove di fatto su cinque membri.

**Una differenza di definizione (misurata nel codice, effetto non misurato):** il `transfer_cells` della corsia B
(`lane_b.py`) usa i gruppi interi del cubo, compresa la tabella VIPerturb di K562. Quello della corsia A
(`bench_effects.py`) la esclude, perché le sue cellule non sono nel corpus della rete. Che la differenza non cambi Q2 è
un'interpretazione: gli scarti sono fra 0,36 e 0,64, mentre fra `transfer_cells` e `transfer_all`, che aggiunge
sorgenti intere, le medie locali differiscono di 0,007 su H1, 0,035 su HepG2 e 0,007 su RPE1. La rete ancorata usa la
definizione della corsia A e riporta entrambe.
