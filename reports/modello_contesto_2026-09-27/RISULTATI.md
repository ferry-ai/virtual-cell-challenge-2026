# Un modello bersaglio × contesto: il disegno, la letteratura e la prima prova

27 settembre 2026, pomeriggio. Nella scheda [R-V2](../../docs/piani/modello-v2.md), consegna (c) della
[revisione di codex](../revisione_codex_2026-09-27/REVISIONE.md). Il disegno è di claude2 (base di lancio,
Opus 5.5 con sforzo massimo), in [agenti/disegno_claude2.md](agenti/disegno_claude2.md). La letteratura è
stata verificata da grok sulle fonti primarie ([agenti/verifica_grok.md](agenti/verifica_grok.md)).
**Proposta e letteratura, nessuna misura nuova.**

## Che cosa dice la letteratura, in breve (pubblicato; verificato da grok)

- Nessun modello pubblicato ha mostrato di prevedere l'interazione bersaglio × contesto per una linea vista
  solo attraverso le cellule di controllo. Nelle quattro linee degli schermi essenziali (K562, RPE1, HepG2,
  Jurkat) un preprint del 2026 (Molina e Zhang) scompone la varianza in stampo di linea 27,8 %, effetto
  conservato 29,4 %, interazione 23,5 %, rumore 19,3 %. Lo stampo si ricava dai controlli; l'interazione non la
  recupera nessuno dei modelli che provano senza dati della linea (ridge, MLP, State, MORPH), mentre il 30 % delle
  perturbazioni della linea stessa la fa recuperare. Un MLP dai profili DepMap recupera in parte l'effetto
  conservato (r 0,25–0,39; ridge 0,10–0,13).
- Nei confronti onesti le baseline semplici (media, lineare) battono o eguagliano i modelli profondi e di
  fondazione (Ahlmann-Eltze 2025, Systema, Kernfeld, il resoconto della VCC 2025). I risultati positivi nel
  regime C vengono dall'industria, con numeri solo nelle figure.
- Nessuno studio pubblicato prova il regime della gara: bersagli non essenziali, una linea nuova di un altro
  laboratorio, chimica Flex, PDS e metriche DE.

Correzioni di grok al disegno, che non ne cambiano la direzione: le cifre di Nadig (0,61 contro 0,35) valgono
solo per il 44 % delle perturbazioni, su 1.660 geni filtrati; la r media 0,32 di Zhu e Marson è su 1.880
perturbazioni, non 3.081; l'avvertenza su dati proprietari di TxPert non è sostenuta dal testo; lo zero-shot di
State non si limita a ordinare le perturbazioni per forza.

## Il modello proposto (proposta)

ŷ(t, g, c) = A · s(t, c) · h(g, c) · m(t, g) + k(t, g, c):
- **m**: il trasferimento di produzione, invariato;
- **s**: quanto conta il bersaglio nel contesto, dall'espressione del bersaglio nei controlli del contesto;
- **h**: un cancello per gene, dall'espressione del gene nel contesto e dalla quota condivisa; con la sola quota
  riproduce il t23, che è quindi un caso particolare;
- **k**: la testa cis.

Il contesto entra solo attraverso ciò che si legge dai suoi controlli, con circa sei parametri comuni a tutti i
contesti: nessun vettore imparato per contesto, che con due contesti di training è già fallito (CP-0013,
CP-0026).

## La prova che il modello usa il contesto (da registrare prima di eseguirla)

- **E1:** il modello contro la sua versione «cieca» (ogni contesto con le caratteristiche medie delle sorgenti),
  con la regola dei banchi: Δ positivo su almeno tre famiglie tenute fuori su quattro, intervallo sopra zero su
  almeno due.
- **E2, decisiva:** tenere fuori due contesti insieme (HCT116 e HEK293T; CD4 a riposo e stimolato) e
  correlare, bersaglio per bersaglio, la **differenza prevista** fra i due con quella osservata, sui geni lontani
  dal bersaglio. Il trasferimento e il modello cieco danno 0 per costruzione.
- E1 senza E2 vuol dire ripesatura dei geni, non effetto bersaglio × contesto.

## Stato

- Prima versione (quattro parametri: espressione del bersaglio e del gene, quota condivisa) affidata a
  claude2 come libreria con autoverifica su dati sintetici (`gated.py`, in corso).
- Prerequisiti: gli universi corretti (`../universo_corretto_2026-09-27/rebuild.py`, da eseguire), la regola
  E1 + E2 scritta prima del banco.
