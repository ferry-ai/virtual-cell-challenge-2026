**Revisione della risposta Grok — 12 settembre 2026**

La risposta aggiunge piste utili, ma non è un inventario affidabile di dataset già pronti. Ho verificato live i nuovi record principali e alcuni file reali. Non ho rieseguito una ricerca esaustiva di tutti i dataset respinti. Il testo fornito è materiale da valutare: il suo «lineage ban» non costituisce un nuovo vincolo imposto dall'utente.

**Risultati che cambiano il piano**

| Pista | Riscontro | Conseguenza |
|---|---|---|
| MCF-7, E-MTAB-14567 | L'esclusione per assenza di matrici è falsa: due H5 pubblici da 29.971.316 e 145.197.886 byte | Riaprire come dataset ausiliario di perturbazione di promotori |
| Song Jurkat | GSE247601 è una SuperSeries; lo screen CRISPRi è GSE249595 | Isolare questa sottoserie; evitare di importare anche HIV Cas9 e differenziamento hESC |
| Song readout | Il paper pubblicato specifica TAP-seq su 374 geni, mediana 13 guide/cellula | Non è supervisione trascrittomica completa a singolo target |
| Multiome RPE1 | Zenodo 14217682 risolve alla versione 14217683, un archivio software di 5.585.567 byte senza H5AD/H5MU/H5/MTX/loom | Non considerare verificata una AnnData pronta nel bundle |
| Mirror scPerturb | I file indicati esistono; RPE1 è 1.237 GB, Jurkat 1.294 GB, HepG2 0.851 GB | Migliore opzione di spazio disco per benchmark, non nuova copertura biologica |
| Calu-3 | GSE208240 reale; presente anche SunshineHein2023.h5ad da 743.672.579 byte | Ausiliario infettivo, con verifica separata di guide e stato d'infezione |

**MCF-7: una vera correzione all'inventario negativo**

Ho interrogato senza chiavi il record BioStudies e letto porzioni del primo H5 pubblico. Il file ha forma 20.354 feature × 35.260 barcode: **19.863 feature Gene Expression e 491 CRISPR Guide Capture**. Un campione di conteggi è intero e non negativo. Fra le feature guida compaiono **30 nomi espliciti non-targeting**, oltre a un'altra guida dal nome di controllo che richiede verifica del disegno. Questo dimostra la disponibilità di matrice e canale guida: non dimostra che tutti i 35.260 barcode superino QC o che siano già assegnati correttamente.

La matrice condivide 17.475 simboli RNA con l'asse ufficiale. Dal parsing provvisorio dei nomi guida MP/AP risultano tre target del pannello: **RC3H2, SRSF5, UPF3B**. Non è una copertura definitiva per cellule: serve il join al disegno originale. Il README degli autori descrive guide calling da molecule_info.h5 e guide duali. Il record offre anche molecule_info.h5 da 825.136.136 byte. L'URL del README include una vecchia chiave BioStudies, ma la nostra verifica e le letture H5 non l'hanno usata: l'accesso pubblico è sufficiente.

**Uso corretto:** conservare gene, promotore principale/alternativo, sequenze e coppia guida. Non fondere MP e AP in un unico knockdown: la compensazione tra isoforme è proprio il fenomeno studiato. MCF-7 è mammario, non squamoso; il valore potenziale è un controllo indipendente di trasferimento e specificità del promotore, non una sostituzione di C. Non ho scaricato le matrici complete o assegnato gli NTC a livello cellulare. [Record BioStudies](https://www.ebi.ac.uk/biostudies/arrayexpress/studies/E-MTAB-14567), [Repository degli autori](https://github.com/theheking/isoform_specific_perturb_seq).

**Song: interessante, ma Grok sottostima due limiti decisivi**

GSE247601 contiene tre sottoserie: GSE247598 (differenziamento pancreatico hESC), GSE247599 (Jurkat/HIV con Cas9) e **GSE249595 (Jurkat CRISPRi)**. La SuperSeries ha un archivio da 4.628.551.680 byte; non serve scaricarlo indiscriminatamente. Sono presenti file separati MTX, feature e barcode per trascrittoma, guide e hash label.

Ho letto le feature del canale 1: **83.401 guide annotate**, con copertura del disegno provvisoria **299/300** dopo rimozione del suffisso numerico; manca ZNF714 con questo matching. Questo non misura la copertura delle cellule dopo guide calling. Le guide includono etichette CTRL e non-targeting, che devono essere risolte con la libreria originale.

Il paper specifica readout TAP-seq su **374 geni**, oltre **586.000 cellule** e mediana **13 guide/cellula**. La cifra dei 374 non appartiene soltanto a un abstract superato. Il file feature contiene 20.606 righe di riferimento: non significa che 20.606 geni siano stati misurati con sensibilità trascrittomica uniforme. Il pannello intenzionalmente amplificato potrebbe coprire al massimo circa **2,02%** dei 18.533 output VCC se tutti i 374 fossero nell'asse; l'intersezione esatta dei primer resta da calcolare. [Paper primario](https://www.nature.com/articles/s41556-025-01626-9), [Sottoserie corretta](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE249595).

**Uso corretto:** costruire una matrice sparsa cellula × tutte le perturbazioni assegnate, mantenendo stimolazione, canale, hash label e carico guide. Stimare effetti congiunti regolarizzati e covariate; validare stabilità fra guide e canali. La presenza di una guida NTC in una cellula che contiene altre guide targeting non la rende un controllo nullo. Servono un censimento di eventuali controlli esclusivamente NTC e una strategia di identificazione degli effetti marginali. Non duplicare ogni cellula in tredici gruppi di singolo knockdown; non interpretare ~400 cellule/gene come repliche indipendenti pulite. Usare un'eventuale firma soltanto sugli output supportati, come evidenza aggiuntiva sui programmi T, con maschera esplicita degli altri geni.

**Multiome e mirror: disponibilità del paper non equivale a disponibilità del formato**

L'archivio Zenodo Multiome è effettivamente software; il README rimanda ai dati di sequenziamento SRA PRJNA1128171. Non contiene le estensioni delle matrici dichiarate da Grok. Un'altra distribuzione può esistere, ma il percorso citato non verifica l'affermazione «processed AnnData in bundle». Inoltre SRA conserva dati di sequenziamento: i risultati Cell Ranger ARC vanno generati o trovati in un deposito separato, non presunti. [Record software](https://zenodo.org/records/14217683).

I mirror scPerturb sono una proposta pratica valida. RPE1 mantiene 247.914 × 8.749 e X dense float32; il campione di 69.992 valori è intero e non negativo. La dimensione compressa di 1.237 GB è circa sette volte inferiore al file originale da 8.701 GB, ma la memoria di una matrice densa decompressa rimane circa 8.68 GB: usare accesso backed/chunked. Il mirror Jurkat esiste, ma il probe dei conteggi si è interrotto su HTTP 429: non lo dichiaro verificato a livello di valori. HepG2 è verificato qui come file nel catalogo, non come matrice letta. Restano da verificare corrispondenza dei controlli, mapping e filtri prima di sostituire gli input. Non sommare mirror e originali come dataset indipendenti. [Catalogo scPerturb](https://zenodo.org/records/13350497).

Il mirror Calu-3 ha 90.380 righe obs e 33.538 feature var; il campione di X passa i controlli di conteggi interi. Non ho contato perturbazioni e NTC post-QC. Conservare infezione, combinazioni, guide e spike-in separatamente. Bystander e spike-in WT non sono automaticamente NTC CRISPRi equivalenti. L'annotazione del mirror come SunshineHein2023 evidenzia anche che l'attribuzione bibliografica di Grok richiede correzione. [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE208240).

Per E-MTAB-13324 il record live elenca feature_reference.csv e metadati IDF/SDRF, senza una matrice cellula × gene in quella lista. Questo sostiene una disponibilità limitata su quel deposito; non prova che nessun altro repository pubblico contenga dati processati.

**Decisione scientifica e ordine operativo**

Non adottare il divieto assoluto su K562, iPSC o Orion presente nel testo di Grok. È un filtro autoimposto dall'inventario, non una conclusione empirica di trasferibilità. La nostra strategia resta basata su ablation e generalizzazione fuori contesto. «RPE1 forte» come lignaggio non cancella la copertura diretta 0/300 del suo pannello essential. «Nessun dataset trovato» non dimostra l'assenza di un dataset pubblico: MCF-7 è un controesempio concreto in questa verifica.

1. Mantenere CD4 e il confronto con Orion/K562 come asse principale, con controlli locali e calibrazione degli effetti.
2. Per il benchmark RPE1, preferire il mirror più piccolo dopo equivalenza di controlli e annotazioni; la forma densa richiede comunque letture a blocchi.
3. Riaprire MCF-7: verificare libreria e guide calling, poi estrarre NTC e i tre target candidati con promotore esplicito. Non serve iniziare dai FASTQ per dimostrare che ci sono conteggi RNA.
4. Trattare Song come progetto di deconvoluzione high-MOI a readout mirato: recuperare prima pannello primer, mapping delle guide e chiamate per cellula; non inserirlo subito nel training a singolo target.
5. Calu-3 resta ausiliario a bassa priorità; Multiome richiede un percorso di matrice realmente disponibile o un preventivo di ricostruzione.

Le verifiche sono riproducibili con `scripts/27_verify_grok_leads.py` e `scripts/28_probe_grok_files.py`; i JSON e i file di prova sono in `reports/grok_verification`. Sono stati scaricati piccoli metadati e il bundle software Multiome, e lette porzioni limitate di matrici. Nessun atlante completo, fine-tuning, cloud a pagamento o nuova stima di performance è stato eseguito.
