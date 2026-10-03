# Miscele di transfer e spostamento della rete: lettura prespecificata

3 ottobre 2026, dopo le 15:48 CEST (ora letta con `date`). La regola è quella di [MISCELE.md](../../MISCELE.md),
committata alle 14:20 prima di calcolare qualunque miscela. Lo script è `lane_b_blend.py` (commit `ff4c877`), con
gli stessi bersagli, cellule vere, verità, replica, baseline e semi della corsia B. Le tabelle sono in
`scaled_local_<linea>.csv`, gli argomenti in `run_<linea>.json`. Misurato.

Media locale dei sei membri; differenze dal transfer:

| Linea | `transfer_cells` | `blend_50` − transfer | `blend_75` − transfer | `blend_25` − transfer |
|---|---:|---:|---:|---:|
| HepG2 | 0,247 | +0,009 | −0,006 | −0,019 |
| RPE1 | 0,223 | −0,099 | −0,023 | −0,158 |
| H1 | 0,279 | −0,077 | −0,028 | −0,139 |

**Lettura fissata prima:** `blend_50` supera il transfer in **1 linea su 3**, con differenza media −0,056. Quindi
**non promettente**. Le due sensibilità sono sotto il transfer in tutte e tre le linee.

**Controllo di coerenza (misurato):** in ogni linea `transfer_cells` e `cells_shift` danno le stesse medie della
corsia B (H1 0,279 e 0,024; RPE1 0,223 e 0,034; HepG2 0,247 e 0,212). Il banco è dunque lo stesso.

**Interpretazione:** mescolare lo spostamento della rete r3 nel transfer diluisce il transfer, salvo un +0,009 su
HepG2. Su RPE1 e H1 la miscela al 50% perde soprattutto PDS (da 0,87 a 0,39 su RPE1, da 0,79 a 0,69 su H1). Lo
spostamento della rete r3 non porta un segnale complementare utile ai sei membri. Il controllo è descrittivo e non
adotta niente. Non decide la rete ancorata, che è un'ipotesi diversa: lì la rete parte dal transfer e impara solo
la correzione sulle cellule. Ne riduce però l'attesa a priori, e il suo protocollo lo scrive al congelamento.
