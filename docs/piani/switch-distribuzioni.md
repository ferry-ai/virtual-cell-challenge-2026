# R-SWITCH — soglie, intensità e cellule rispondenti

- **Stato:** aperto; promettente, esperimento in attesa di cellule e guide indipendenti.
- **Aggiornato:** 24 settembre 2026.
- **Assegnazione:** da verificare con gli agenti già attivi; nessuna presa in carico registrata qui.
- **Ipotesi:** H4 soglie e H5 quota di rispondenti; collegamento con H2 stato e H9 tempo.

## Prossima azione

Con [R-DATI](dati-affidabilita.md), verificare se Mixscale e microglia GSE335887
permettono di stimare l'intensità e misurare la risposta **su informazioni disgiunte**.
Scrivere un protocollo che confronti gradualità, saturazione e soglia su altre
guide/repliche, indicando cosa si può identificare con i dati disponibili.

## Esperimenti e alternative

- Distinguere switch topologici da co-espressione, regolatori perturbati e risposta
  a soglia. Le tre categorie non sono intercambiabili; un gene non è uno switch universale.
- Confrontare descrittori SWIM con hub appaiati per grado/espressione, TF e pathway.
  La semplice co-espressione non dimostra causalità e ha già dato un risultato debole
  nel progetto: [CP-0020](../checkpoints/0020-singola-cellula-cis-generatore.md).
- Evitare circolarità: score su geni disgiunti o misura indipendente, congelato
  prima di verificare soglie sugli altri geni e nelle guide/repliche escluse.
- Distinguere effetto per cellula da percentuale di cellule rispondenti: confrontare
  spostamento uniforme e miscela a media comparabile. Controllare composizione,
  proliferazione, sopravvivenza e tempo se misurati.
- Una distribuzione bimodale non dimostra bistabilità o isteresi. Il trasporto
  fra distribuzioni non osserva la traiettoria delle singole cellule.

## Dipendenze e criterio di chiusura

Servono cellule, controlli, guide e supporto misurato; DE aggregate non bastano a
dimostrare H5. Applicare [GENERALIZZAZIONE](../GENERALIZZAZIONE.md) se si sostiene
predizione su nuovi bersagli/contesti, e congelare soglie/metriche prima della prova.

Chiusura: report riproducibile che discrimini le forme di risposta, oppure documenti
che i dati non permettono di distinguerle. Se emerge un predittore, confrontarlo
con [R-MODELLI](trasferimento-modelli.md), poi valutarne le cellule nel banco VCC.
Non promuovere un generatore perché riproduce soltanto la media.

## Evidenze e passaggio di consegne

[Ricerca sugli switch e fonti primarie](../../reports/ipotesi_trasferimento_2026-09-24/IPOTESI.md), §§3–6.
Le osservazioni di letteratura sono candidati da verificare qui, non risultati locali.
**Nessun dataset acquisito né esperimento eseguito con questa scheda.**
