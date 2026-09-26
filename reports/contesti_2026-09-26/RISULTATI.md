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

## Seconda prova (r2): lo stato di p53 al posto della somiglianza intera

Script `p53_weighting.py`, uscita `r2/`. Motivo: nella letteratura portata da grok
(`../trasferimento_appreso_2026-09-26/agenti/conservazione_risposte_grok.md`), Nadig et al. 2025
trovano trasferimento alto fra linee con lo stesso stato di p53 e lo stesso modo di crescita
(interpretazione degli autori, non prova controllata). Il gruppo di p53 di ogni contesto è letto dai
controlli (percentile medio di 25 bersagli canonici di p53): basso K562 (0,45) e HEK293T (0,61), alto
CD4 (0,75) e HCT116 (0,71). Per ogni sorgente tenuta fuori, le sorgenti dello stesso gruppo pesano 2,
4, oppure da sole; forma t20.

| Sorgente fuori | stesso gruppo | ×2 | ×4 | solo stesso gruppo |
|---|---|---|---|---|
| K562 | HEK293T | +0,001 | −0,006 | −0,049 |
| CD4 | HCT116 | +0,001 | −0,005 | −0,038 |
| HCT116 | CD4 | −0,016 | −0,031 | −0,057 |
| HEK293T | K562 | +0,016 | +0,026 | +0,068 |

(PDS proxy meno pesi uguali; intervalli in `r2/summary.csv`: per HCT116 tutti sotto zero e per
HEK293T tutti sopra zero, a ogni dose; "solo stesso gruppo" è negativo anche per K562 e CD4.)

- **Misurato:** lo stato di p53 letto dai controlli non predice quale sorgente trasferisce meglio.
- **Interpretazione:** lo schema che si vede è un altro: CD4, cellule primarie, predice male entrambe
  le linee Orion, e K562 le predice meglio. La distinzione fra cellule primarie e linee, o il saggio,
  sembra pesare più dello stato di p53. Con quattro sorgenti è un'osservazione, non una regola.
