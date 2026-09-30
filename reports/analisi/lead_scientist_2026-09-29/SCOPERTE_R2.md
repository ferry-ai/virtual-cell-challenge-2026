# Scoperte della sessione — aggiornamento successivo a R1

29 settembre 2026, prima del risultato ufficiale t28. Integra [R1](SCOPERTE_R1.md), che resta una fotografia storica. Le prove complete sono nei report collegati.

| Scoperta | Evidenza e portata | Conseguenza pratica |
|---|---|---|
| Il calcolo del banco t28 è riproducibile; il suo delta non è un guadagno VCC | [Audit score](SCORE_CREDIBILITA.md): nove CSV, eleggibilità, aggregazioni e bootstrap ricostruiti | Leggere lo score ufficiale dai sei membri pubblicati; mantenere le soglie registrate |
| 95 dei 96 target della conferma erano già stati valutati nel progetto | [Overlap storico](SCORE_BIAS_DATI_PRECISAZIONE.md), confronto delle liste e dei manifest; non prova quali valori fossero stati consultati | Chiamarla conferma interna alla selezione odierna; istituire un registro globale delle riserve prima della prossima selezione |
| Le ancore aggregate non ricostruiscono esattamente gli score | [Audit score](SCORE_CREDIBILITA.md): errore +0,000730 su t03 e +0,000826 su t25 | Correggere la guida; non usare la conversione come score ufficiale né sottrarre questo errore come correzione universale |
| Più contesti nel manifest non equivale a training su tutte le linee disponibili | Produzione t28: quattro sorgenti. Rete: cinque fold su dodici contesti aggregati, due semi; nessun fit finale comune di produzione | Tracciare separatamente file disponibili, unità biologiche, pool eleggibili e campioni effettivamente utilizzati; integrare le linee già presenti ma escluse |
| Il prescreen PDS non esaurisce la valutazione di una rete | [Audit neurale](neural/NN_PRESCREEN_AUDIT.md); fallimento del criterio attuale confermato, non prova contro ogni rete o ogni metrica | Un eventuale nuovo candidato richiede un esperimento distinto sulle sei metriche e una riserva realmente nuova |
| t28 è recuperato senza differenze rispetto al primo generato | [Ricevuta SHA integrale](../../invii/trial_2026-09-29/t28_in_place_validation_r1/validation.json), più validazione e payload stage48 | Invio diretto del contenitore verificato; conservare ricevute CLI e stato ufficiale. Nessuna correzione neurale aggiunta |

**Decisione:** t28 resta un esperimento ufficiale ragionevole, con limiti espliciti. Né il delta locale né una previsione soggettiva dimostrano che sia competitivo. Il piano operativo successivo sta nella scheda [modello competitivo](../../../docs/piani/modello-competitivo.md); questa tabella conserva le scoperte, non assegna nuovi job.
