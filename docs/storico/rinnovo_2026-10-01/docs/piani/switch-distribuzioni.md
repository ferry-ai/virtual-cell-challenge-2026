# R-SWITCH — soglie, intensità e cellule rispondenti

- **Stato:** aperto; esperimento subordinato a cellule e guide indipendenti.
- **Orientamento dopo t29 (1/10):** ipotesi ancora da provare, subordinata ai confronti
  di [R-LEAD](strategia-scientifica.md). Il collasso del gate identity di r3 è un problema
  di ottimizzazione; non prova l'esistenza o l'assenza di uno switch biologico. Questo
  filone non fornisce ancora un rimedio misurato allo score della rete.
- **Aggiornato:** orientamento riallineato il 1° ottobre; proposta originaria del 24/09.
  **Nota storica del 28/09 (D-046):** nessun lavoro registrato su questa
  scheda dopo il 24; le sorgenti a singola cellula acquisite nel frattempo sono in
  [reports/sorgenti/README.md](../../reports/sorgenti/README.md).
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
  nel progetto: [CP-0020](../../../../checkpoints/0020-singola-cellula-cis-generatore.md).
- Evitare circolarità: score su geni disgiunti o misura indipendente, congelato
  prima di verificare soglie sugli altri geni e nelle guide/repliche escluse.
- Distinguere effetto per cellula da percentuale di cellule rispondenti: confrontare
  spostamento uniforme e miscela a media comparabile. Controllare composizione,
  proliferazione, sopravvivenza e tempo se misurati.
- Una distribuzione bimodale non dimostra bistabilità o isteresi. Il trasporto
  fra distribuzioni non osserva la traiettoria delle singole cellule.

## Dipendenze e criterio di chiusura

Servono cellule, controlli, guide e supporto misurato; DE aggregate non bastano a
dimostrare H5. Applicare [GENERALIZZAZIONE](../../../../GENERALIZZAZIONE.md) se si sostiene
predizione su nuovi bersagli/contesti, e congelare soglie/metriche prima della prova.

Chiusura: report riproducibile che discrimini le forme di risposta, oppure documenti
che i dati non permettono di distinguerle. Se emerge un predittore, confrontarlo
con [R-MODELLI](trasferimento-modelli.md), poi valutarne le cellule nel banco VCC.
Non promuovere un generatore perché riproduce soltanto la media.

## Evidenze e passaggio di consegne

[Ricerca sugli switch e fonti primarie](../../../../../reports/analisi/ipotesi_trasferimento_2026-09-24/IPOTESI.md), §§3–6.
Le osservazioni di letteratura sono candidati da verificare qui, non risultati locali.
**Nessun dataset acquisito né esperimento eseguito con questa scheda.**

## Integrazione Codex del 25 settembre

Sottoattività documentale completata da Codex, task
`01a0d81b-3495-74d0-9537-eb5254b05002`, iniziata alle 21:32 UTC.
[Proposte e fonti](../../../../../reports/analisi/biologia_architetture_2026-09-25/PROPOSTE.md), §§3–5:
Jost GSE132080 come candidato con guide attenuate per distinguere dose, quota
di rispondenti e intensità; microglia e PerturbFate mantengono ruoli complementari.
Geni disgiunti riducono circolarità diretta, ma non garantiscono indipendenza
fra programmi correlati. Prossimo passo: audit file/guide/licenza e protocollo
con guide escluse, senza usare efficacia post-perturbazione come input di test.
Nessun download o modello adottato; il piano resta aperto.
