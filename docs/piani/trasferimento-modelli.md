# R-MODELLI — programmi, stato cellulare e bersagli nuovi

- **Stato:** aperto; promettente, training in attesa dei dati e del protocollo.
- **Aggiornato:** 24 settembre 2026.
- **Assegnazione:** da verificare con gli agenti già attivi; nessuna presa in carico registrata qui.
- **Ipotesi:** H1 programmi, H2 stato, H3 ruolo con segno, H6 pesi delle sorgenti, H10 prior aggiuntivi.

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

[GENERALIZZAZIONE](../GENERALIZZAZIONE.md) resta il vincolo: nei regimi T/J togliere
le risposte dei bersagli di test da ogni sorgente e derivato, inclusa la base dei
programmi. Il trasferimento dello stesso bersaglio è un confronto solo dove è lecito.
Un programma poco espresso nei controlli non è automaticamente impossibile da indurre.
Calibrare ampiezza e generatore separatamente dalla direzione degli effetti.

Prima di recuperare implementazioni leggere [CP-0026](../checkpoints/0026-predittore-neurale-condizionato.md)
e [ARCHIVIO](../ARCHIVIO.md): usare il codice utile con i suoi test, rispettando D-040.
Questo piano non riattiva il vecchio predittore scartato né supera il risultato di t07.

## Criterio di chiusura

Esito del protocollo congelato con confronti sullo stesso supporto, copertura,
incertezza e uso del contesto. Un guadagno solo nella componente comune non prova
specificità; un proxy non è un punteggio VCC. Promozione o scarto con evidenza e
checkpoint; risultati negativi restano utili e chiudono il relativo esperimento.

## Evidenze e alternative

[Pattern misurati](../../reports/pattern_mixscale_2026-09-24/RISULTATI.md);
[ipotesi e alternative](../../reports/ipotesi_trasferimento_2026-09-24/IPOTESI.md), §§2–5/7/8.
Se le etichette non reggono, tornare a R-DATI; se emerge una quota di rispondenti,
aprire il confronto di distribuzioni in [R-SWITCH](switch-distribuzioni.md).
Reti causali dinamiche restano candidate quando tempo e interventi le rendono valutabili.

**Passaggio di consegne:** nessun training o protocollo congelato prodotto con questa scheda.
