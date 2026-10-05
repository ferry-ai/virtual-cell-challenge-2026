# Archivio, banca e trainer riutilizzabili

**Indice operativo attuale:** [dove sono grezzi, banche e campioni](cloud_catalog_r4/README.md),
con manifest immutabile, account, versioni, hash e distinzione dai dataset storici.
Include 15 banche verificate e 12 matrici campionate CD4 complete; le nuove parti
HEK293T restano aperte; KOLF e HCT116 sono chiusi anche nei campioni.
Include anche la prima chiusura banca/campioni HepG2 verificata; il trainer resta aperto.

**Non perdere né reingerire:** [17 archivi precedenti e nuova ingestione, 395,75 GB grezzi](DATI_DISPONIBILI_r2.md).
Account, versioni e hash sono nel manifest; nessun fallback al cubo ridotto del pilot.
[Lanci e ostacolo HIPSCI](PARALLELISMO_r2.md): 16 job CPU distinti accettati;
i quattro Colab preparati sono sostituiti dai job Kaggle, non avviarli.
Cinque archivi pubblici autorizzati e verificati; i nuovi output restano privati.
[Stima del lotto e dimensioni](PROIEZIONE_r1.md), condizionata anche al recupero HIPSCI.
La tabella dati r2 corregge le unità effettivamente presenti nei singoli dataset:
le ricevute di ingestion possono nominare anche unità sorelle del medesimo job.
`DATI_DISPONIBILI_r1.md` resta storico; usare r2.

Mandato del proprietario, 5 ottobre 2026: supervisionare la catena completa,
conservare gli output su Kaggle e includere tutte le linee e i contesti idonei.
Questo report contiene strumenti e verifiche operative; non dimostra un nuovo
training né un miglioramento scientifico.

## Evidenza e stato

- `snapshot_r6/state.json`: inventario con provenienza dei grezzi, chiavi dei
  derivati per unità, output cloud e stato del collegamento al trainer. Le tre
  banche D4 sono conservate nella versione privata 1 dei rispettivi notebook:
  codice salvato uguale al lancio, versione stabile prima/dopo la lettura,
  otto artefatti per unità presenti e manifest riconciliati alle cellule ingerite.
  I file erano già stati scaricati e verificati integralmente nella campagna
  precedente; qui si trasferiscono soltanto i piccoli manifest.
- D1–D3: tre job CPU ancora in corso al controllo; gli output finali non sono
  ancora certificati persistenti. `progress_r1.json` conserva il controllo dei log.
- Tutte le 100 **voci**, non dataset distinti, del catalogo r4 sono conservate:
  77 remote, 18 ingerite, 5 aggregate. Ruoli, alias e sottocontesti non ancora
  riconciliati restano aperti; l'inventario non assegna esclusioni automatiche.
  Le aggiunte successive al catalogo r4 vanno riconciliate prima del corpus finale:
  questo snapshot non dichiara il catalogo completo.
- `training_contract.py`: controlli riusabili su copertura, file montati e uso
  effettivo; cinque fixture in `test_contract.py`. **Da collegare al nuovo
  trainer**, non retroattivamente ai 18 fit aggregati conclusi.
- Il training esteso resta esplicitamente `extended_training_ready=false`.
  Mancano integrazione dei contesti oltre il pilot, campioni materializzati e
  collegamento verificato al trainer. Un elenco di locatori non è una matrice
  cellulare autonoma. Le riserve e gli split restano protetti.

## Persistenza e riuso

I job scrivono sotto `/kaggle/working`; la versione salvata conserva gli output,
che si possono montare come input dei consumatori. Fonte:
[documentazione Kaggle](https://www.kaggle.com/docs/notebooks).
Il percorso su `/kaggle/working` durante un'esecuzione attiva, da solo, non è
prova di persistenza. La supervisione controlla conclusione e recuperabilità.
Non cancellare né riutilizzare gli slug dei produttori verificati. Registrare
versione, codice e hash dei file; controllare gli stessi hash nel consumatore.
Le copie locali sono facoltative, non un passaggio obbligatorio cloud–locale–cloud.
L'accesso dal diverso account del trainer richiede ancora verifica sul runtime.

Un nuovo dataset richiede **solo** acquisizione/adattamento della nuova sorgente,
banca per i nuovi contesti, campioni e aggiornamento del manifest del corpus.
Non si ricostruiscono le vecchie banche se input, QC, asse dei geni, codice e
parametri sono identici. La chiave del derivato contiene codice congelato e
specifica della singola unità; aggiungere altre unità al job non la cambia.
Se cambia QC, asse o stimatore, si rigenerano i soli derivati dipendenti.
Le ancore combinate e la preparazione degli split possono cambiare aggiungendo
sorgenti; si versionano separatamente, senza riscrivere le banche di base.
Il modello va aggiornato e rivalutato: un resume compatibile non è garantito da
questa persistenza e non sostituisce la validazione di nuovi dati/split.

## Comandi e condizioni di chiusura

`pipeline_state.py --remote --out <nuova-cartella-nella-repo>` rilegge lo stato
dei job già autorizzati, scarica solo manifest di completamento e produce uno
snapshot nuovo. Non lancia, cancella, ricostruisce né scarica matrici.
`training_contract.py` deve essere chiamato dal nuovo trainer prima del fit e
prima dell'accettazione; il manifest adottato deve elencare tutti i contesti
idonei con asse, artefatti, ruolo, target e strati. Le ricevute dell'uso vengono
dai dati letti e dalla loss, non copiate dall'elenco degli input.

La supervisione ogni 30 minuti è aggiornata: chiusura solo dopo verifica del
percorso intero, copertura del catalogo, training esteso e valutazione t28.
Un nuovo dataset viene aggiunto al manifest, mai escluso per volume, comodità
o scarso overlap. Qualità, duplicazioni, incompatibilità e riserve hanno
motivazione verificabile; un adapter mancante resta un lavoro da completare.

Tentativi tecnici conservati: r1 si è fermato su conversione percorso relativo
in assoluto (corretta); r2 ha verificato gli output senza numero di versione;
r3 ha ricevuto 404 usando `version_label` numerico per ListKernelSessionOutput.
r4 usa l'endpoint funzionante e verifica stabilità della versione prima/dopo
la lettura. r5 ha fermato la guardia sul codice locale per terminatori CRLF:
il lanciatore originale calcola lo SHA sul testo LF prima della scrittura Windows;
r6 applica lo stesso contratto e aggiunge le chiavi indipendenti per unità.
Nessun job cloud è stato rilanciato per questi controlli.
