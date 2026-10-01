# Ricerca su bersagli e contesti nuovi

**Decisione operativa D-044, 24 settembre 2026**, su richiesta del proprietario.
Un dataset può essere utile anche se non contiene nessuno dei 300 geni perturbati
del pannello attuale. La ricerca mira anche a prevedere perturbazioni mai viste
durante l'addestramento in contesti nuovi. La baseline di produzione trasferisce
effetti già osservati dello stesso bersaglio: resta un confronto utile.

## 1. Tre distinzioni obbligatorie

- **Bersaglio perturbato:** il gene su cui si interviene. L'overlap col pannello
  misura l'utilità immediata per la baseline, non tutta l'utilità per apprendere.
- **Gene di risposta:** una delle variabili che prevediamo. Una risposta non
  misurata resta mascherata, non nulla (D-009). Uno scarso overlap dei bersagli
  non è equivalente a una scarsa copertura delle risposte.
- **Nuovo per la gara oppure nuovo per il modello:** il pannello finale cambia,
  ma alcuni suoi bersagli potrebbero essere già nei dati pubblici. Entrambi i
  casi devono avere una valutazione dedicata.

Zero overlap dei bersagli fra due sorgenti non le rende automaticamente inutili.
Rende però più difficile separare l'effetto del bersaglio da quello di linea,
stimolo e studio. Servono descrittori trasferibili e prove coerenti con ciò che
è identificabile; una rete non risolve da sola la mancanza di collegamenti.
Ammettere una sorgente senza bersagli in comune non vuol dire poterne concatenare
assi di risposta o saggi incompatibili senza riconciliarli prima.

## 2. Come scegliere e conservare le sorgenti

**Regola:** nessuna soglia minima di overlap col pannello per ammettere una sorgente
alla ricerca. Non restringere permanentemente un archivio ai bersagli attuali.
Conservare file originali, provenienza e metadati fuori dalla repo; produrre viste
ristrette per singoli esperimenti quando servono, con manifest e destinazioni nuove.
Questo non autorizza download indiscriminati: prima verificare file, dimensioni,
licenza e utilità prevista, secondo le regole operative già esistenti.

Ogni scheda sorgente deve separare:

| Dimensione | Che cosa registrare |
|---|---|
| Bersagli | Universo completo, tipo di perturbazione, promotori/guide, identificativi; overlap attuale come statistica descrittiva |
| Risposte | Geni misurati, unità, selezione dei geni, maschera, disponibilità di cellule/conteggi oppure sole stime DE |
| Contesti | Linea, donatore, stimolo, tempo, stato, studio, chimica e replicati; non sommarli come linee indipendenti |
| Qualità | Controlli, numerosità, riproducibilità, incertezza, assegnazione delle perturbazioni, possibili dipendenze fra stime |
| Uso | Addestramento, confronto fra contesti, test esterno, descrittori basali oppure baseline dello stesso bersaglio |
| Accesso | Versione, URL, checksum, licenza verificata o da verificare, costo di acquisizione e memoria |

**Priorità iniziale:** verificare la qualità delle etichette e la possibilità di
costruire test indipendenti; ampliare diversità di bersagli e contesti; usare la
copertura del pannello soltanto per l'eventuale impiego immediato nella baseline.
Contesti lontani e pannelli mirati restano candidati con ruoli espliciti.

**Acquisire e catalogare.** Un download lo autorizza il proprietario in chat, con file,
dimensione e licenza detti prima ([CLAUDE.md](../CLAUDE.md)). I dati vanno nella radice
dati, mai nella repo (D-001), con una riga nella tabella «Dati» del
[registro](REGISTRO.md) che dice provenienza e come riprodurli. **Ogni dataset trovato
entra nel catalogo della repo, anche se lontano dai contesti di gara o scartato**, con
ruolo possibile e stato di verifica, nel report della ricerca che l'ha trovato, indicizzato
in `reports/sorgenti/README.md`: lo ha chiesto il proprietario il 25/09, perché un candidato
scartato a voce si perde (finora la regola stava solo nella memoria di un agente).

## 3. Valutazione che deve precedere la scelta di un modello

| Regime | Bersaglio nel training | Contesto nel training | Domanda |
|---|---|---|---|
| C | visto | nuovo | Trasferisce lo stesso intervento? |
| T | nuovo | visto | Predice un intervento mai osservato? |
| J, generalizzazione congiunta | nuovo | nuovo | Generalizza entrambe le componenti? |

Il regime J è il criterio principale per dichiarare generalizzazione congiunta.
**Precisazione D-050, 1 ottobre:** per la produzione competitiva valutare separatamente C e J,
in base al supporto disponibile; un miglioramento C può essere adottato per C con una regola
preregistrata che preservi il ramo J, senza pretendere che dimostri entrambe le capacità.
Riportare anche T e un test su uno studio distinto quando disponibile, per distinguere
biologia e differenze tecniche. Nessuna reinterpretazione dei protocolli esistenti.

**Separazioni richieste:**

1. Per T/J, togliere le etichette perturbazionali dei bersagli di test da **tutte**
   le sorgenti del training, incluse repliche, guide, alias riconciliati e derivati.
   Una media di vicini o un embedding ricavato da quelle risposte è anch'esso leakage.
2. Per C/J, escludere dal training le risposte perturbate dell'intero gruppo di
   contesto scelto. Per dichiarare una linea nuova, tenere fuori quella linea in
   tutti gli stimoli e studi, non solo una sua condizione.
3. I controlli non perturbati del contesto di test possono essere input, come in
   gara. Dichiararlo; non usarne le risposte perturbate per selezionare geni,
   normalizzazioni, rappresentazioni o parametri.
4. Usare validation separata dal test, con gruppi coerenti con il regime. Pesi,
   ampiezze, selezione dei geni e arresto del training si decidono lì. Se i gruppi
   non bastano, dichiarare il risultato esplorativo, senza chiamarlo test finale.
5. Registrare provenienza dei descrittori: annotazioni e sequenze esterne possono
   descrivere bersagli nuovi, ma un modello preaddestrato su perturbazioni di test
   non sostiene la stessa dichiarazione di generalizzazione rigorosa.
6. Congelare un manifest esplicito di target e contesti: aggiungere una sorgente non deve
   riassegnare gli split esistenti. Dopo QC, deduplicazione ed esclusioni, verificare C/T/J
   contro le etichette effettivamente ammesse. Un seme fisso su un universo variabile non
   basta ([audit del 1/10](../reports/analisi/lead_audit_2026-10-01/REVISIONE.md)).

Confrontare i modelli sullo stesso supporto misurato; affiancare una misura di
copertura. L'intersezione dei geni valida un confronto, non impone di buttare via
tutti gli altri geni in addestramento: possono contribuire con perdite mascherate.

## 4. Scelte sui modelli e criterio di successo

**Scelta:** iniziare da descrittori del bersaglio disponibili anche per un gene
mai perturbato e da descrittori del contesto ottenuti dai suoi controlli.
Il primo modello appreso sarà un confronto semplice, regolarizzato, prima di
aumentare la capacità. La specifica dei descrittori segue l'audit dei dati;
non è stata selezionata o addestrata una nuova architettura con questa decisione.

Confronti necessari: effetto nullo, risposta media che ignora il bersaglio, modello
semplice con gli stessi input, ablazione che ignora il contesto. Il trasferimento
dello stesso bersaglio si valuta dove l'informazione esiste (C o regime misto),
senza dargli accesso illecito alle risposte nascoste in J.

Per l'ipotesi «più contesti aiuta», confrontare sottoinsiemi annidati di sorgenti
sullo stesso test congelato, ripetendo la scelta delle sorgenti. Riportare sia
un confronto a budget e copertura comparabili sia quello con tutti i dati utili.
Non confondere numero di cellule, numero di linee e numero di studi.

Prima del prossimo training fissare metrica primaria, aggregazione per gruppi,
incertezza e soglia di promozione in un protocollo immutabile. Per dichiarare J, richiedere
vantaggio su J rispetto ai confronti semplici e verificare uso del contesto. Per adottare
un candidato competitivo seguire la regola sul supporto C/J (D-050), con baseline generica
realmente addestrata, affidabilità della verità e composizione dei gruppi esplicite.
Con DE aggregate si misura lo spazio degli effetti; le metriche VCC complete
richiedono un banco con cellule e controlli. Non chiamare un proxy punteggio VCC.

## 5. Priorità concrete dopo CP-0035

Priorità del 24/09, lasciate come motivazione dei requisiti: quelle correnti stanno in
[PIANI.md](PIANI.md), che dal 29/09 mette prima R-COMP. L'ordine aggiornabile dei lavori
e le prese in carico stanno lì: R-DATI, R-MODELLI e R-SWITCH. I punti sotto motivano i requisiti iniziali; le nuove
ipotesi su programmi, switch e distribuzioni sono collegate dalle schede senza
modificare le regole di valutazione di questo documento.

1. **Mixscale:** conservare tutti i 218 bersagli dell'archivio, non solo i nove
   attuali. È il primo candidato per progettare separazioni fra sei linee. Prima
   verificare se le stime DE e la selezione dei geni condividono informazione fra
   linee: la prova descrittiva di CP-0035 non risolve questo punto e non è un test J.
   Nell'archivio DE scaricato non ci sono profili basali separati: acquisirli o
   estrarli dagli oggetti degli autori prima di addestrare descrittori di contesto.
   Dall'inventario di CP-0035, 181 bersagli compaiono in un solo stimolo, 26 in due,
   sei in tre e cinque in quattro. **Scelta:** assegnare i fold per identità del
   bersaglio attraverso tutti gli stimoli; uno split casuale dei 271 file non basta.
   La prevalenza di bersagli specifici di uno stimolo richiede inoltre risultati
   stratificati e limita quanto possiamo separare effetto di gene e stimolazione.
2. **DLD-1:** usare l'universo completo dei bersagli per valutare il contributo
   come ulteriore contesto; chiarire suffissi, unità e selezione dei 2.827 geni di
   risposta. I 67 bersagli in comune non sono un criterio di ammissione o rifiuto.
3. **K562/CD4/Orion e nuovi dati:** inventariare gli universi completi disponibili,
   distinguendoli dalle cache filtrate di produzione. Ampliare le cache di ricerca
   solo in una destinazione nuova, dopo aver stimato costi e copertura.
4. **Jurkat e contesti lontani:** restano candidati anche con supporto di risposta
   parziale. Valutarne il ruolo e la qualità, senza richiedere somiglianza ad A/B/C.
5. **Prima di riprendere codice:** consultare CP-0026 e l'archivio. La rete precedente
   è stata scartata per il suo esperimento, non ogni rete possibile; quel fallimento
   va usato come confronto e avvertimento sulla riproducibilità. Ripristinare codice
   utile dal tag con i suoi test, secondo D-040, senza riscriverlo da zero.

Riferimenti interni: [CP-0035](checkpoints/0035-dld1-mixscale-audit.md),
[report dei dati](../reports/sorgenti/dld1_audit_2026-09-24/RISULTATI.md),
[CP-0026](checkpoints/0026-predittore-neurale-condizionato.md),
[ARCHIVIO.md](ARCHIVIO.md). Comandi e risorse restano in [PROCEDURE.md](PROCEDURE.md), le
autorizzazioni in [CLAUDE.md](../CLAUDE.md).
