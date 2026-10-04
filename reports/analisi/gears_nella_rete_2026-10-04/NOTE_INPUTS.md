# Materiale già presente: verifica dopo il primo studio

**Misurato localmente:** [audit_local_inputs_r1.json](audit_local_inputs_r1.json), prodotto da
[audit_local_inputs.py](audit_local_inputs.py), conferma lo SHA della matrice usata dalla rete:
`7313ba892ba8aaaa8c967be15ac5fe1f17578811ecfa5e55c58fb914a1c81c80`.
Sono 18.533 geni × 284 descrittori. I blocchi comprendono GO, STRING, HGNC, coordinate,
espressione basale DepMap e indicatori di disponibilità. Non partiamo senza informazione biologica.

Gli indicatori dichiarano GO presente per 17.591 geni e STRING per 9.989. Sono conteggi
sull'asse del bundle, non misure di connettività, affidabilità delle relazioni o copertura
del futuro training. Il file di configurazione H1 D-056 registra lo stesso SHA e 284 dimensioni.

**Lacuna rilevata:** tutti e cinque i percorsi storici controllati (GOA, OBO, STRING links,
STRING info, HGNC) non sono più presenti dove li cita il manifest. Il primo controllo è
stato corretto per leggere il campo `sources` e poi per registrare esplicitamente le assenze:
la ricevuta positiva della matrice non è una ricevuta positiva delle sorgenti.
Sono state trovate `external/annotation/string_physical_links.gz` e
`external/annotation/string_protein_info.gz`; non se ne è verificata in questa sessione
l'equivalenza con i file storici. Il grande file DepMap non è stato riletto o ricalcolato.

Conseguenza operativa: prima del grafo reale localizzare gli artefatti originali oppure
definire una nuova acquisizione versionata. I vettori GO compressi non consentono di
ricostruire automaticamente il grafo Jaccard delle annotazioni originali: un grafo kNN
sui descrittori sarebbe un candidato diverso, da nominare e confrontare come tale.
La nuova proposta deve misurare il valore della propagazione rispetto agli stessi
descrittori già disponibili, senza attribuirlo semplicemente all'aggiunta di GO/STRING.

Le figure estese 3 e 4 del [paper originale, copia degli autori](https://ai.stanford.edu/~jure/pubs/gears-natbio23.pdf)
sono ulteriori riferimenti per il disegno: confrontano la rimozione dei componenti e
mettono in relazione la qualità con la connettività verso geni supervisionati.
Non sono una verifica del nostro innesto: riportare i risultati per grado/copertura e
includere nodi isolati, invece di valutare soltanto i bersagli meglio annotati.
