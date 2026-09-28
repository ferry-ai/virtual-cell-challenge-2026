# Modulo cis CRISPRi: la repressione dei geni vicini, aggiunta al trasferimento

26 settembre 2026, notte. **Proxy contro sorgenti pubbliche tenute fuori, non punteggi VCC.**
Tre passaggi: `cis_bench.py` (r1), `cis_bench2.py` (r2), `cis_generator_check.py` (r3).

## La biologia e la domanda

Il dCas9-KRAB legato al TSS del bersaglio reprime anche i geni con il TSS a poche kb,
soprattutto i promotori bidirezionali, in qualunque contesto. Il 17 settembre la curva era stata
misurata sul K562 genome-wide (mediana circa −0,5 log2 entro 1 kb, circa 0 oltre 20 kb) e il
segno si conservava in HepG2 nel 97,5% delle coppie forti
([CP-0020](../../docs/checkpoints/0020-singola-cellula-cis-generatore.md) §3.5). Nessun invio
l'aveva modellata: gli effetti trasferiti la contengono solo dove una sorgente ha misurato la
coppia, mediata, centrata e moltiplicata per l'ampiezza della parte trasferita. **Domanda:** un
modulo esplicito, che non vede i bersagli del pannello, aggiunge qualcosa al trasferimento?

## Metodo

Banco "una famiglia fuori" (K562, CD4, HCT116, HEK293T), caricatore e media dello stadio 100,
forme t16 (grezzi × 0,788) e t19 (ristretti × 1,576), un solo insieme di bersagli per sorgente
tenuta fuori, bootstrap appaiato sui bersagli. Prior: effetto medio o mediano per fascia di
distanza dal TSS, stimato sulle coppie del K562 genome-wide di `reports/cis_2026-09-17/` **dopo
aver tolto i 300 bersagli del pannello** (6.115 coppie, bersagli fuori pannello). Controllo:
gli stessi valori messi sui vicini di un altro bersaglio.

## Risultati

**r1: i dati trasferiti contengono già gran parte del segnale cis.** Sulle coppie entro 2 kb
(53–60 per sorgente tenuta fuori) il valore trasferito correla 0,58–0,70 con la verità e ha il
segno giusto nel 79–88% dei casi (`r1/cis_pairs_2kb.csv`). Sostituire il valore trasferito con
il prior perde o non guadagna PDS proxy (−0,009…+0,001); aggiungerlo guadagna (+0,002…+0,006,
ogni intervallo sopra zero); il controllo mescolato sta a zero (−0,0005…+0,0005). Il solo prior, senza
trasferimento, dà PDS proxy 0,55–0,60 contro 0,5 del caso.

**r2: la forma di produzione e la dose.** Con `CisModel.from_pairs` (mediana per fascia,
già usato dagli stadi 75 e 76) aggiunto k volte entro 5 kb:

| Forma | k = 1 | k = 2 | k = 4 | k = 2, bersagli con un vicino |
|---|---|---|---|---|
| t16 | +0,0014…+0,0036 | +0,0029…+0,0065 | +0,0053…+0,0119 | +0,011…+0,025 |
| t19 | +0,0011…+0,0030 | +0,0024…+0,0061 | +0,0037…+0,0113 | +0,009…+0,024 |

Ogni intervallo al 95% sopra zero; controllo mescolato −0,0007…+0,0002; rapporto d'errore
quadratico invariato entro +0,001 a k = 2. Rimettere il valore misurato senza ampiezza
(`cis_meas`) guadagna sulla forma t16 e perde sulla t19: il PDS proxy premia un segnale cis più
forte, non più fedele. Entro 2 kb e entro 5 kb danno lo stesso risultato.

**r3: attraverso il modello del generatore** (profilo di trial-01, spostamento compositivo,
rumore di 400 cellule; contesti A, B e C; semi 1–3), k = 2 entro 5 kb:

| Sorgente fuori | PDS forma t16 | PDS forma t19 | primo gene giusto, t19 |
|---|---|---|---|
| K562 | +0,0049 | +0,0028 | +0,001 |
| CD4 | +0,0055 | +0,0048 | +0,026 |
| HCT116 | +0,0025 | +0,0014 | +0,003 |
| HEK293T | +0,0020 | +0,0012 | +0,001 |

Ogni intervallo del PDS sopra zero. "Primo gene giusto" è la quota di bersagli il cui gene più
mosso fra i significativi della verità ha il segno giusto: il primo passo del membro reach.
Precisione dei segni e numero di geni rilevabili invariati.

## Che cosa se ne ricava

- **Misurato:** il modulo aggiunge un guadagno piccolo e coerente su tutte le sorgenti tenute
  fuori, concentrato sui 67–75 bersagli con un vicino entro 5 kb.
- **Interpretazione:** sui bersagli di oggi il guadagno è piccolo perché le sorgenti hanno già
  misurato quasi tutte le coppie; il modulo vale soprattutto per i bersagli che nessuna sorgente
  ha misurato, perché richiede solo le coordinate del gene. Il set finale ne avrà.
- **Scelta per il t20:** k = 2 entro 5 kb. Nel K562 la mediana per fascia è 0,4–0,6 volte la
  media, quindi due volte la mediana è vicina all'effetto medio misurato. La dose 4 guadagna di più sul proxy ma supera l'effetto
  tipico misurato: sarebbe taratura della metrica, non biologia.

## Che cosa non si è fatto

Nessuna orientazione dei promotori nel modello di produzione: in K562 le coppie divergenti e le
altre hanno effetti simili entro 1 kb (`r1/prior_k562_non_panel.csv`). Nessuna dipendenza
dall'espressione del vicino nel contesto. Il reach vero dipende da tutta la testa della
classifica, non solo dal primo gene.
