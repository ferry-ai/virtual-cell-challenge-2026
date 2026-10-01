# R-MODELLI — programmi, stato cellulare e bersagli nuovi

- **Stato:** **chiuso** il 30 settembre 2026, su scelta del proprietario in chat; esito e condizione
  di riapertura nella sezione «Chiusura» qui sotto. Il testo che segue è com'era.
- **Aggiornato:** 30 settembre 2026, chiusura (Claude, sessione `a1ec75f0`,
  [pulizia della struttura](../../../../../reports/analisi/pulizia_struttura_2026-09-30/README.md), §3).
  Prima: 24 settembre 2026. **Nota del 28/09 (D-046):** la scheda non è stata aggiornata;
  i confronti che proponeva sono stati eseguiti nella scheda [R-V2](modello-v2.md) (programmi, H6,
  modello a cancelli, rete, encoder), tutti con esito negativo finora:
  [reports/trasferimento/README.md](../../../../../reports/trasferimento/README.md) e
  [reports/modelli/README.md](../../reports/modelli/README.md).
- **Integrazione:** 25 settembre 2026, ricerca esplorativa CP-0040.
- **Assegnazione:** da verificare con gli agenti già attivi; nessuna presa in carico registrata qui.
- **Ipotesi:** H1 programmi, H2 stato, H3 ruolo con segno, H6 pesi delle sorgenti, H10 prior aggiuntivi.

## Chiusura (30 settembre 2026)

Nessuno ha preso in carico il training di questa scheda; la sola sottoattività, documentale, è di
Codex del 25/09 (sotto). I suoi confronti sono stati
eseguiti altrove, soprattutto in [R-V2](modello-v2.md) e in [R-COMP](modello-competitivo.md), e
nessuno ha superato la sua regola. L'esito per confronto, dalle fonti citate:

| Confronto (§ «Confronti in ordine») | Esito | Fonte |
|---|---|---|
| 1. Nullo, risposta comune, lineare | la risposta comune pesa l'1–14 % e non si trasferisce fra linee; il motore C/T/J con le basi di confronto è lo stadio 105 | [risposta comune](../../../../../reports/trasferimento/risposta_comune_2026-09-26), filone F3 di R-V2 |
| 2. Programmi (H1) | proiettare l'effetto trasferito su programmi perde PDS a ogni rango | [programmi](../../../../../reports/trasferimento/programmi_2026-09-26) |
| 3. Stato dai controlli, con il contesto scambiato (H2) | modello a cancelli: E1 non passa, e dove batte il cieco non batte lo scambio; rete su molti contesti r1: perde contro il trasferimento su K562, HCT116 e HEK293T e passa solo J; encoder dei basali, seme 0: nessuna condizione passa; misura decisiva per la rete relazionale inconclusiva; rete che pesa le sorgenti sotto soglia in due semi | [modello a cancelli](../../../../../reports/modelli/modello_contesto_2026-09-27), [lettura di r1](../../../../../reports/modelli/rete_r1_lettura_2026-09-28), [encoder](../../../../../reports/modelli/encoder_contesto_2026-09-28), [CP-0043](../../../../checkpoints/0043-misura-decisiva-relazioni.md), [CP-0048](../../../../checkpoints/0048-rete-sorgenti-primo-seme.md), [CP-0049](../../../../checkpoints/0049-rete-sorgenti-replica.md) |
| 4. Ruoli con segno, complessi e reti (H3); pesi per programma | **non eseguito**. I pesi per somiglianza basale (H6) sono caduti; i descrittori dei bersagli nuovi, filone F5 di R-V2, aspettano il via ai download | [contesti](../../../../../reports/trasferimento/contesti_2026-09-26), R-V2 F5 |
| 5. Modelli preaddestrati | Stack A e B non superano il trasferimento | [CP-0051](../../../../checkpoints/0051-stack-ab-negativi.md) |

Sono esiti di banchi e proxy, non punteggi VCC, e ciascuno vale per il suo protocollo: non
dimostrano che nessun modello appreso possa funzionare. Il lavoro sui modelli prosegue in
R-COMP, priorità dal 29/09, e in R-V2.

**Si riapre se** R-COMP o R-V2 riaprono i descrittori dei bersagli nuovi e i ruoli con segno (H2–H3,
confronto 4), per esempio dopo il via ai download del filone F5. Si riapre anche se un nuovo
protocollo C/T/J chiede i confronti di questa scheda. Chi la riapre scrive qui stato, data e
assegnazione.

### Sottoattività documentale del 25 settembre

Codex, task `01a0d81b-3495-74d0-9537-eb5254b05002`, presa in carico il
25 settembre 2026 alle 21:32 UTC: consolidamento della ricerca svolta in chat,
autorizzato dal proprietario. Ambito: nuova cartella
`reports/analisi/biologia_architetture_2026-09-25/`, output nuovo `r1`, checkpoint,
registrazione e rimandi nelle tre schede di ricerca. Non prende in carico il
training né modifica le assegnazioni degli audit dati altrui.

## Prossima azione

Usare l'audit [R-DATI](dati-affidabilita.md) per scrivere un **protocollo C/T/J**:
gruppi esclusi, metrica primaria, aggregazione, incertezza e soglia di promozione
fissati prima del training. Progettare i confronti anche mentre l'audit procede;
non addestrare con split o dipendenze delle etichette ancora ambigui.

## Confronti in ordine

1. Effetto nullo, risposta comune e modello lineare regolarizzato sugli stessi input.
2. Base di programmi imparata solo sul training e predizione dei coefficienti
   da descrittori del bersaglio disponibili anche per geni mai perturbati.
3. Interazioni con lo stato dai controlli: confronto senza contesto e con
   contesto scambiato. Verificare che il contesto venga effettivamente usato.
4. Ruoli con segno, complessi e reti contro vicini non orientati; split aggiuntivo
   per famiglia genica. Pesi delle sorgenti per programma contro pesi uguali.
5. Solo se il confronto lo giustifica: embedding di sequenza/modelli fondazionali
   come input congelati, reti tipo GEARS/CellOracle e maggiore capacità.
   Audit del pretraining e input compatibili con il finale; nessuna promessa di vantaggio.

## Dipendenze e protezioni dell'esperimento

[GENERALIZZAZIONE](../../../../GENERALIZZAZIONE.md) resta il vincolo: nei regimi T/J togliere
le risposte dei bersagli di test da ogni sorgente e derivato, inclusa la base dei
programmi. Il trasferimento dello stesso bersaglio è un confronto solo dove è lecito.
Un programma poco espresso nei controlli non è automaticamente impossibile da indurre.
Calibrare ampiezza e generatore separatamente dalla direzione degli effetti.

Prima di recuperare implementazioni leggere [CP-0026](../../../../checkpoints/0026-predittore-neurale-condizionato.md)
e [ARCHIVIO](../../../../ARCHIVIO.md): usare il codice utile con i suoi test, rispettando D-040.
Questo piano non riattiva il vecchio predittore scartato né supera il risultato di t07.

## Criterio di chiusura

Esito del protocollo congelato con confronti sullo stesso supporto, copertura,
incertezza e uso del contesto. Un guadagno solo nella componente comune non prova
specificità; un proxy non è un punteggio VCC. Promozione o scarto con evidenza e
checkpoint; risultati negativi restano utili e chiudono il relativo esperimento.

## Evidenze e alternative

[Pattern misurati](../../../../../reports/sorgenti/pattern_mixscale_2026-09-24/RISULTATI.md);
[ipotesi e alternative](../../../../../reports/analisi/ipotesi_trasferimento_2026-09-24/IPOTESI.md), §§2–5/7/8.
Se le etichette non reggono, tornare a R-DATI; se emerge una quota di rispondenti,
aprire il confronto di distribuzioni in [R-SWITCH](switch-distribuzioni.md).
Reti causali dinamiche restano candidate quando tempo e interventi le rendono valutabili.

**Passaggio di consegne:** nessun training o protocollo congelato prodotto con questa scheda.

## Consegna documentale del 25 settembre

Sottoattività Codex sopra **completata**: [risultati riproducibili](../../../../../reports/analisi/biologia_architetture_2026-09-25/RISULTATI.md)
e [architetture e prove](../../../../../reports/analisi/biologia_architetture_2026-09-25/PROPOSTE.md),
registrati in [CP-0040](../../../../checkpoints/0040-biologia-contesti-donatori.md).
Prossimo passo proposto: protocollo per programmi con segno e contrasti fra
contesti, includendo grafo multirelazione e incertezza gerarchica. Non confondere
scambio del contesto con prova positiva di apprendimento; il pannello poco
incrociato richiede split e controlli specifici. Formulazione, non training.
