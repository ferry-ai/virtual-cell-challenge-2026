# Controllo descrittivo: transfer mescolato allo spostamento della rete, sui sei membri

Scritto il 3/10 dopo le 14:19 CEST (ora letta con `date`), **prima di calcolare qualunque miscela**. Viene dalla
decisione del proprietario del §11 del [protocollo](PROTOCOLLO.md): prima di preregistrare una rete cellulare ancorata
al transfer, verificare gratis se mescolare transfer e spostamento della rete aiuta. L'indizio è HepG2 nella corsia B:
spostamento della rete passato per il generatore a 0,212 contro 0,247 del transfer, peggiore in PDS ma migliore in NMAE,
FID e JAC.

- **Linee e bersagli:** H1, HepG2 e RPE1, con gli stessi bersagli, le stesse cellule vere, la stessa verità, replica e
  baseline della corsia B (`lane_b.py`, semi uguali).
- **Bracci:** `transfer_cells` (riferimento), `cells_shift` (spostamento previsto dal braccio `cells` r3) e le miscele
  `blend_w = w · transfer + (1 − w) · rete`, sui geni dove il transfer ha supporto (dove la rete non ha valore resta il
  transfer). Tutti passano per il generatore trial-01.
- **Primaria:** `blend_50` (w = 0,5). Sensibilità: `blend_75` e `blend_25`.
- **Lettura, fissata ora:** «promettente» se la media locale dei sei membri di `blend_50` supera quella di
  `transfer_cells` in almeno 2 linee su 3 e la differenza media è positiva. È **descrittivo**: non adotta niente. Al più
  motiva un protocollo preregistrato della rete ancorata al transfer. Le linee sono di sviluppo, già lette.
