# H6 su Mixscale: la somiglianza basale non predice il trasferimento, e pesarla peggiora

26 settembre 2026, notte. Filone F6 della scheda [R-V2](../../docs/piani/modello-v2.md).
**Proxy nello spazio degli effetti su un altro saggio (knockout CRISPR, pannelli di vie), non
punteggi VCC.** Script `h6_mixscale.py`, uscita `r1/`.

## Domanda

Oggi ogni sorgente pesa uguale in ogni contesto, e il set finale porta tre linee nuove.
L'ipotesi H6 ([IPOTESI](../ipotesi_trasferimento_2026-09-24/IPOTESI.md)) dice che gli effetti
passano meglio fra linee con stato basale simile, quindi le sorgenti andrebbero pesate per
somiglianza. Mixscale ha gli stessi bersagli (circa 218) in sei linee (A549, BXPC3, HAP1, HT29,
K562, MCF7) e cinque stimoli: è il posto giusto per provarla.

## Metodo

- Trasferimento fra due linee: PDS proxy (coseno, rango del bersaglio vero fra quelli dello
  stimolo) predicendo i log2FC della linea c con quelli della linea s, medio sui cinque stimoli,
  poi simmetrizzato. Geni e bersagli esclusi come nell'analisi del 24 settembre.
- Somiglianza basale: Spearman fra i profili DepMap 24Q4 delle due linee, sui 14.461 geni
  espressi (log1p TPM > 1 in almeno una linea) e sui 2.000 più variabili fra le sei.
- Test di Mantel: Spearman fra le 15 somiglianze e i 15 trasferimenti, permutazione esatta
  delle sei etichette (720).
- Pesatura: per ogni linea tenuta fuori, media delle altre cinque con pesi ∝ exp(β · z), z la
  somiglianza standardizzata; β = 0 sono pesi uguali.

## Risultati (r1)

- **Misurato:** la somiglianza basale non predice il trasferimento. Mantel +0,08 (p 0,43) sui
  geni espressi, −0,02 (p 0,53) sui 2.000 più variabili.
- **Misurato:** pesare per somiglianza peggiora quattro linee su sei.

| Linea tenuta fuori | pesi uguali (β 0) | β 1 | β 4 |
|---|---|---|---|
| A549 | 0,592 | 0,576 | 0,562 |
| BXPC3 | 0,569 | 0,566 | 0,577 |
| HAP1 | 0,576 | 0,564 | 0,568 |
| HT29 | 0,626 | 0,614 | 0,577 |
| K562 | 0,573 | 0,558 | 0,569 |
| MCF7 | 0,576 | 0,584 | 0,575 |

- **Misurato:** il trasferimento fra coppie è asimmetrico (`r1/transfer_pds.csv`, 0,526–0,629):
  per esempio HT29 è predetta bene da A549 e HAP1 (0,629 e 0,628).

## Che cosa se ne ricava

- **Interpretazione:** con sei linee, mediare tutte le sorgenti riduce il rumore più di quanto
  la somiglianza dell'espressione basale aiuti a scegliere quali pesare. Coerente con quanto
  visto sulle nostre sorgenti: aggiungere sorgenti aiuta, sceglierle per somiglianza no.
- **H6 contraddetta in questa forma** (somiglianza del profilo basale intero). Non escluse:
  somiglianze su programmi specifici, o per bersaglio (per esempio l'espressione del bersaglio e
  della sua via nelle due linee).
- **Proposta per D/E/F:** pesi uguali fra le sorgenti; lo sforzo va sulla copertura dei bersagli
  e sulla riduzione del rumore.

## Limiti

Knockout e non CRISPRi, pannelli di vie e non trascrittoma intero, sei linee soltanto, cinque
stimoli trattati come repliche della stessa coppia.
