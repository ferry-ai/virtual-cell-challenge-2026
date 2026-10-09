# Priorità alle reti — mandato del 9 ottobre

Registrato dal Lead il 9 ottobre 2026, dopo il messaggio del proprietario letto
alle 01:55 Europe/Rome. **Tipo: decisione operativa e ipotesi progettuale**;
non è un risultato scientifico. Sostituisce la priorità di consegna fast e il
mandato di invio autonomo di `MANDATO_REFIT_COMPLETO_r2.md`, che resta conservato.

Il proprietario dispone: «il modello fast va in secondo piano per ora,
concentriamoci sulle reti che volevamo già sviluppare (tra cui ESM2)».
DATI e MODELLI hanno ricevuto il cambiamento e lo hanno riconosciuto nei rispettivi
messaggi di avanzamento. Nessuna nuova scadenza viene promessa.

## Stato verificato e responsabilità

DATI ha registrato il fallimento operativo in
`reports/modelli/dati_transfer_2026-10-08_01a11c34/deadline_incident_r1.json`
e `STATO_r11.md`: T3 aveva generato le cellule, ma non aveva completato il
confezionamento; nessuna nuova entry o upload VCC. Non era disponibile il
ripiego nuovo richiesto. T36 era già stato valutato e non è una nuova consegna.
Il Lead assume la responsabilità di coordinamento della consegna mancata;
le cause tecniche e i tentativi restano nelle ricevute di DATI.

ESM2: `ESECUZIONE_FIT_r5.md` di MODELLI documenta cinque fit con avanzamento
effettivo alle 00:27; J-iPSC si è fermato prima del fit per un errore DNS.
La ricevuta `esm2-t-01a11c35-r3.retrieval_terminal_collection_r1.json`,
scritta alle 01:56:48, riporta COMPLETE per T e la presenza degli output.
Questa ricevuta non dimostra ancora correttezza numerica o beneficio predittivo.
MODELLI verifica ora gli output e lo stato fresco degli altri job.

## Proprietà del lavoro e ordine

1. **MODELLI-ESTERNI (`01a11c35`)**: concludere i fit ESM2 validi e verificarne
   le predizioni; recuperare J-iPSC su un runtime accessibile dopo il controllo
   degli slot e degli input, senza ripetere alla cieca il trasporto fallito.
   Conservare tutti i job validi in corso. Unico proprietario dei nuovi modelli,
   dei protocolli di fit, del codice e dei lanci associati.
2. **DATI-TRANSFER (`01a11c34`)**: input e consumo effettivo delle reti; risolvere
   accessi e lacune di ingestion, fornire controlli, maschere e campioni cellulari
   per contesto dalla banca canonica. Riconciliare il catalogo e indicare il ruolo
   di ogni fonte idonea. Non cambiare le viste congelate dei fit in corso.
   Non avviare nuove generazioni, confezionamenti o invii fast. Conservare T3,
   ricevute e output recuperabili; eventuali processi già avviati si verificano
   prima di intervenire. Nessun reinvio di t36.
3. **VALIDAZIONE (`8a8ca58a`)** mantiene confronti indipendenti, leakage,
   conclusioni e documenti condivisi. Questa nota è il passaggio di consegne
   per aggiornare priorità e incidente; non afferma che sia già stata letta.
   Gli output ESM2 vanno letti prima come correttezza tecnica, poi nei regimi
   C/T/J con le regole già congelate. T da solo non dimostra contesti nuovi.

## Prossimo esperimento neurale

Decisione di indirizzo: dopo aver protetto la conclusione di ESM2, sviluppare
**un solo ramo contestuale** che riusi i descrittori ESM2 e l'infrastruttura
CellNet v5, con una correzione a basso rango bersaglio × contesto ricavato
dai controlli, sopra un'ancora congelata. È il primo blocco già proposto nel
catalogo `reports/analisi/pezzi_adottabili_2026-10-05/CATALOGO.md` (AMMI).
Non è implementato né validato da questa nota; MODELLI deve congelarne la
specifica e verificarne la fattibilità prima del fit.

ESM2 attuale è congelato più ridge sugli effetti aggregati: non legge lo stato
cellulare e non effettua fine-tuning della rete ESM2. Serve come confronto
separato. Il ramo nuovo deve dimostrare l'utilità del contesto, non soltanto
un aumento del numero di parametri. La supervisione cellulare e quella
aggregata hanno ruoli espliciti e conteggi distinti.

**Precedenti:** S-001/S-002/S-006 richiedono discriminazione del bersaglio e
controllo della risposta comune; S-007 vieta di presentare come nuova prova
lo stesso correttore basato soltanto sul basale medio; S-009 richiede la stessa
ancora e la stessa trasformazione in fit, banco ed esportazione. Il prodotto
bersaglio × contesto non garantisce da solo una correzione specifica.

La correzione parte da zero e non ha un termine esportato prodotto dal solo
contesto. Verificare parità con l'ancora a correzione nulla e apprendimento
con gradienti non nulli. Controllare bersagli permutati, ampiezza e quota comune
anche all'esportazione. Confrontare con transfer, ESM2 ridge e ablation del
contesto sugli stessi split; la promozione richiede i sei membri e guardie PDS
per contesto, con soglie congelate prima della lettura.

**PIE** resta il confronto esterno già selezionato, con adattatore disponibile
e inferenza reale ancora non eseguita nelle ricevute lette. Qualificarne asset,
esposizioni e ponte di scala in parallelo alla preparazione, senza far dipendere
il ramo ESM2 dai circa 45,64 GB del suo piano. GEARS e ulteriori architetture
restano successive: non aprire una nuova ricerca di catalogo al posto del fit.

## Risorse e tappe verificabili

CPU per la ridge corrente; GPU di `davidmaisterx` per training effettivamente
CUDA, previa misura di risorse, accessi e quota. Le circa due ore GPU residue
di `davideferrante11` sono una dichiarazione del proprietario da riverificare,
non un budget per prove indiscriminate. Nessun acquisto o nuovo push implicito.

Le prossime consegne sono: ricevute finali e predizioni ESM2; valutazione
indipendente C/J; protocollo e prova tecnica del ramo contestuale, poi training
con conteggi di uso effettivo per contesto. Il percorso principale mantiene
D-053: nessun contesto idoneo escluso per comodità, nessun corpus chiamato
completo sulla sola presenza dei file. Una prova ridotta resta un pilot.

Prima del prossimo ciclo di produzione, provare l'intera catena su una fixture
e sul filesystem del runtime, inclusi confezionamento e recupero degli output.
I controlli operativi devono prevenire i guasti osservati; non sostituiscono
la valutazione scientifica e non introducono una nuova scadenza nominale.
