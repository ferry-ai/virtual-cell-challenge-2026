# Rapporto di ricerca — Collaudo - Perturb-seq CRISPRi pubblico in linea T matura o squamosa
- **Run:** `20260914T022455Z-ricerca-collaudo-v1-1485b2`
- **Incarico:** `ricerca-collaudo` versione 1 (sha256 `2c34027e7438ca71`)
- **Modalita':** `scientific_research`, 3 fasi
- **Esito:** **disaccordo irrisolto** — 3 contraddizioni restano aperte; il programma non ne chiude nessuna da solo
- **Avvio:** 2026-09-14T02:24:55Z · **Fine:** 2026-09-14T02:24:55Z
- **Dossier completo:** `dossier.json` · **risposte verbatim:** `steps/`
- **Rapporto generato:** 2026-09-14T02:24:55Z

> Questo rapporto raccoglie, non concilia. Le due sintesi restano separate e verbatim in appendice; nessuna sintesi consensuale e' stata prodotta e nessun terzo modello e' stato interrogato. Dove una ricerca risulta «dichiarata dal worker» vuol dire che il worker dice di averla eseguita e che noi non l'abbiamo vista eseguire: il canale non espone le query.

## 1. Domanda e perimetro

**Domanda:** Esiste un dataset Perturb-seq CRISPRi pubblico, con matrice RNA a singola cellula accessibile, in una linea T matura oppure epiteliale squamosa? Per ciascun candidato: quale linea cellulare, quante perturbazioni, se la matrice RNA e' davvero scaricabile o se l'archivio espone solo conteggi di guide.


**Perimetro:** Dataset Perturb-seq o CRISPRi a singola cellula depositati pubblicamente, in linee T mature (Jurkat, CD4 primarie, linee T trasformate) o epiteliali squamose. Conta solo cio' che ha una matrice RNA a singola cellula ottenibile: un archivio che espone i soli conteggi di guide non soddisfa il perimetro.

**Fuori perimetro:** Linee eritroidi (K562) e pluripotenti (H1, KOLF2.1J, HIPSCI), gia' inventariate altrove nel progetto. Screening CRISPR a lettura di sola fitness, senza RNA.

**Criteri di pertinenza** dichiarati prima di contattare i worker:

| id | criterio |
|---|---|
| P1 | La fonte nomina un'accessione di archivio pubblico (GEO, ArrayExpress, Zenodo, figshare) per un esperimento a singola cellula |
| P2 | La linea cellulare e' T matura o epiteliale squamosa, dichiarata esplicitamente |
| P3 | La fonte dice che cosa e' depositato: matrice RNA, conteggi di guide, o solo metadati |

**Prospettive assegnate:**

| worker | prospettiva |
|---|---|
| solver_a | Metodi e archivi. Come e' stato fatto l'esperimento, che cosa e' stato depositato, in quale formato, con quale copertura del pannello. Guarda le pagine di accessione e i file, non solo gli articoli.  |
| solver_b | Biologia e limiti. Se la linea e' davvero il contesto che dichiara, se l'efficienza di knockdown e' riportata, e quali limiti gli autori dichiarano sul trasferimento ad altri contesti.  |

## 2. Cosa e' stato cercato, e dove

Il canale puo' mostrare che l'interruttore di ricerca era acceso, non quali query siano state eseguite. Nessuna ricerca di questa campagna e' quindi 'osservata negli artefatti del canale': tutte quelle eseguite restano dichiarazioni dei worker.

**Capacita' di ricerca dei canali**, come risulta dalla configurazione e non da un'assunzione:

| servizio | stato | modalita' | dettaglio |
|---|---|---|---|
| scripted | available | ricerca_simulata | il profilo dichiara 'ricerca_simulata' come interruttore di ricerca sul web; l'adattatore lo imposta e ne rilegge lo stato prima del primo messaggio |

**Ricerche registrate: 13 in tutto, 5 dichiarate eseguite.**

| fase | worker | query | dove | filtri | stato | provenienza | passo |
|---|---|---|---|---|---|---|---|
| 1 | solver_a | (Perturb-seq OR CRISPRi) AND (Jurkat OR "primary T cell") AND single-cell RNA-seq | GEO DataSets | Expression profiling by high throughput sequencing; 2019-2026 | eseguita | dichiarata dal worker | `steps/research_phase1-01-solver_a-70dbb24e/` |
| 1 | solver_a | CRISPRi single-cell squamous carcinoma keratinocyte perturbation atlas | Europe PMC | OPEN_ACCESS:y; 2020-2026 | eseguita | dichiarata dal worker | `steps/research_phase1-01-solver_a-70dbb24e/` |
| 1 | solver_a | "no detectable transcriptional effect" CRISPRi T cell negative results | Europe PMC | nessuno | non eseguita | proposta, non eseguita | `steps/research_phase1-01-solver_a-70dbb24e/` |
| 1 | solver_b | CRISPRi perturbation single cell "mature T" lineage transfer direction of effect | PubMed | 2021-2026; Journal Article | eseguita | dichiarata dal worker | `steps/research_phase1-01-solver_b-57c23818/` |
| 1 | solver_b | squamous epithelium CRISPRi atlas single-cell knockdown efficiency | PubMed | 2021-2026 | fallita | dichiarata dal worker | `steps/research_phase1-01-solver_b-57c23818/` |
| 2 | solver_a | Aaltonen 2024 primary T cell Perturb-seq "data availability" | Europe PMC | nessuno | non eseguita | proposta, non eseguita | `steps/research_phase2-02-solver_a-47d87ebf-a2/` |
| 2 | solver_b | Bergqvist Lorenzi squamous CRISPRi atlas preprint | bioRxiv | nessuno | non eseguita | proposta, non eseguita | `steps/research_phase2-02-solver_b-eb2299dd/` |
| 3 | solver_a | squamous CRISPRi single cell perturbation atlas 2025 | ArrayExpress | single cell; Homo sapiens | eseguita | dichiarata dal worker | `steps/research_phase3-03-solver_a-81dfd0f3/` |
| 3 | solver_a | Bergqvist squamous CRISPRi atlas | Zenodo | dataset | eseguita | dichiarata dal worker | `steps/research_phase3-03-solver_a-81dfd0f3/` |
| 3 | solver_a | Aaltonen 2024 primary T cell Perturb-seq supplementary table S4 | pagina dell'editore | nessuno | bloccata | dichiarata dal worker | `steps/research_phase3-03-solver_a-81dfd0f3/` |
| 3 | solver_b | Bergqvist Lorenzi squamous CRISPRi atlas | bioRxiv | nessuno | fallita | dichiarata dal worker | `steps/research_phase3-03-solver_b-a3764f9d/` |
| 3 | solver_b | squamous epithelial identity CRISPRi single cell | medRxiv | nessuno | fallita | dichiarata dal worker | `steps/research_phase3-03-solver_b-a3764f9d/` |
| 3 | solver_b | Lorenzi keratinocyte CRISPRi 2025 | bioRxiv | ricerca per autore | non eseguita | proposta, non eseguita | `steps/research_phase3-03-solver_b-a3764f9d/` |

**Fonti distinte: 4.** Deduplicate su DOI o URL normalizzato; due titoli simili senza identificatore comune restano due fonti. Il livello di consultazione e' quello **dichiarato** da ciascun worker.

| id | titolo | anno | DOI/URL | chiave | trovata da | livello dichiarato |
|---|---|---|---|---|---|---|
| F-b558b4be5b | Perturb-seq in primary human T cells reveals lineage-restricted regulators | 2024 | 10.0000/finta-2026-0001 | doi | solver_a, solver_b | solver_a: testo completo o sezione consultata; solver_b: abstract consultato |
| F-7a0575bb0e | A CRISPRi atlas of squamous epithelial identity | 2025 | 10.0000/finta-2026-0002 | doi | solver_b | solver_b: non accessibile |
| F-d9bd7e407c | Chromatin state predicts knockdown response across epithelial lineages | 2023 | https://example.invalid/chromatin-knockdown | url | solver_b | solver_b: trovata in un elenco di risultati |
| F-a54a3e23a8 | GSE999001: CRISPRi Perturb-seq in Jurkat T cells | 2024 | https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE999001 | url | solver_a | solver_a: abstract consultato |

Una fonte e' stata trovata da entrambi i worker e conta una volta sola: F-b558b4be5b.

## 3. Evidenze principali e contrarie

La colonna «natura» e' quella dichiarata da chi ha risposto. «Riferita dagli autori» vuol dire che il worker la attribuisce agli autori di una fonte: non l'abbiamo verificata leggendo il documento, e il parser non e' in grado di farlo.

| id | worker | fase | natura | affermazione | a sostegno | contrarie | localizzatore | limiti |
|---|---|---|---|---|---|---|---|---|
| C-4be086cdc7 | solver_a | f1 | riferita dagli autori | L'accessione GSE999001 elenca, oltre ai conteggi di guide, una matrice di espressione a singola cellula in formato mtx. | F-a54a3e23a8 | — | pagina di accessione, sezione Supplementary file | e' cio' che l'archivio dichiara; non ho scaricato il file e non so se sia completo |
| C-dfc8afd05b | solver_a | f1 | riferita dagli autori | Gli autori riportano che il segno della risposta si conserva fra linee T diverse per i geni a effetto forte. | F-b558b4be5b | — | Fig. 3b e testo a p. 7 | vale sui 112 bersagli con almeno 200 cellule; sugli altri gli autori non si pronunciano |
| C-1c706db2fa | solver_a | f1 | interpretazione del worker | Se la matrice RNA e' depositata, il collo di bottiglia del progetto si sposta dalla disponibilita' del dato alla sua estrazione mirata. | F-a54a3e23a8 | — | — | e' una conseguenza operativa, non un risultato degli autori |
| C-f8bba36f15 | solver_b | f1 | riferita dagli autori | Gli autori riportano che la direzione della risposta NON si conserva fra lignaggi diversi, nemmeno per i bersagli a effetto forte. | — | F-b558b4be5b | abstract, ultime due frasi | l'ho letto nell'abstract; il dato che lo sostiene sta in una figura supplementare che non ho potuto aprire |
| C-0a77cddf88 | solver_b | f1 | riferita dagli autori | Lo stato della cromatina nel contesto bersaglio determina il segno della risposta al knockdown, ed e' per questo che il trasferimento fallisce. | F-d9bd7e407c | — | — | — |
| C-2c63ba79fb | solver_b | f1 | interpretazione del worker | Registrare F2 come non accessibile, invece di descriverlo dal titolo, lascia aperta la domanda sul contesto squamoso. | F-7a0575bb0e | — | — | non dice nulla sul contenuto di F2, che resta ignoto |
| C-9061290f0b | solver_a | f2 | interpretazione del worker | L'affermazione del collega sullo stato della cromatina e' attribuita agli autori di una fonte che lui registra come solo trovata in un elenco: nessuno l'ha letta. | — | — | — | dice che l'attribuzione non e' sostenuta, non che l'affermazione sia falsa |
| C-8ed86621a5 | solver_b | f2 | ipotesi nuova | Lo stato della cromatina nel contesto bersaglio potrebbe determinare il segno della risposta al knockdown. | — | — | — | nella fase 1 l'avevo attribuita agli autori di una fonte che non ho aperto; era sbagliato, ed e' un'ipotesi mia |
| C-8cf50c85b9 | solver_b | f2 | interpretazione del worker | Una lettura dell'abstract non e' equivalente a una lettura della figura che l'abstract riassume. | F1 | — | — | — |
| C-e7e4fe9413 | solver_a | f3 | riferita dagli autori | La didascalia della Fig. 3b dichiara che la figura usa i 112 bersagli con almeno 200 cellule, non tutti i bersagli dello studio. | F-b558b4be5b | — | didascalia della Fig. 3b | non dice su quale popolazione sia costruita la frase dell'abstract, che e' l'altra meta' della domanda |
| C-6cfd47838f | solver_a | f3 | interpretazione del worker | Se l'abstract generalizza su tutti i bersagli e la figura ne mostra 112 selezionati, i due passaggi possono essere entrambi corretti e la contraddizione fra me e il collega sarebbe apparente. | F-b558b4be5b | — | — | e' la spiegazione alternativa che avevo proposto, e resta non verificata: serve la tabella S4, che non e' accessibile |
| C-4d8d417b2a | solver_a | f3 | interpretazione del worker | Le due query su ArrayExpress e Zenodo non hanno restituito nessun deposito per il lavoro squamoso. | — | — | — | e' un'assenza in due archivi con due stringhe, non un'assenza nella letteratura |

### Attribuzioni da guardare

Queste affermazioni sono dichiarate come risultati riferiti dagli autori e hanno una forma che spesso accompagna un'attribuzione sbagliata. **Non e' un verdetto**: il programma non ha letto le fonti e non sa dire se un'affermazione sia falsa. E' un elenco di punti dove guardare.

| id | worker | affermazione | perche' segnalata | passo |
|---|---|---|---|---|
| C-f8bba36f15 | solver_b | Gli autori riportano che la direzione della risposta NON si conserva fra lignaggi diversi, nemmeno per i bersagli a effetto forte. | attribuito agli autori senza indicare una fonte | `steps/research_phase1-01-solver_b-57c23818/` |
| C-0a77cddf88 | solver_b | Lo stato della cromatina nel contesto bersaglio determina il segno della risposta al knockdown, ed e' per questo che il trasferimento fallisce. | attribuito agli autori di F-d9bd7e407c, che pero' risulta «found»: nessuno ha letto il testo a cui l'affermazione viene attribuita; attribuito agli autori senza localizzatore nel documento | `steps/research_phase1-01-solver_b-57c23818/` |

### Accordi dichiarati

| worker | fase | testo |
|---|---|---|
| solver_a | 2 | Esiste almeno un candidato in linea T matura che dichiara una matrice a singola cellula |
| solver_a | 2 | Il contesto squamoso resta scoperto: nessuno dei due ha trovato un deposito accessibile |
| solver_b | 2 | Esiste un candidato in linea T matura con una matrice dichiarata |
| solver_b | 2 | Il contesto squamoso e' scoperto |
| solver_b | 2 | La mia attribuzione sulla cromatina non era sostenuta: su questo gli do ragione |

### Contributi complementari

| worker | fase | testo |
|---|---|---|
| solver_a | 2 | Io ho guardato le pagine di accessione, lui i limiti dichiarati dagli autori: le due cose non si sovrappongono e servono entrambe |
| solver_a | 2 | Lui ha trovato il candidato squamoso a paywall, che io non avevo intercettato |
| solver_b | 2 | Lui sa che cosa e' depositato, io so che cosa gli autori dichiarano di non poter estendere |

### Assunzioni senza sostegno segnalate

| worker | fase | testo |
|---|---|---|
| solver_a | 2 | Che lo stato della cromatina spieghi il segno della risposta: appoggiato a una fonte mai aperta |
| solver_a | 2 | Che il file di matrice dichiarato dall'accessione sia effettivamente scaricabile: nessuno dei due ha provato |
| solver_b | 2 | La mia ipotesi sulla cromatina, che nella fase 1 avevo presentato come risultato di un paper |

## 4. Ipotesi, e come sono cambiate

Gli stati sono **dichiarazioni dei worker**, non verifiche. Nessuno stato in questa tabella e' stato prodotto da un controllo del programma.

| id | enunciato | origine | stati dichiarati |
|---|---|---|---|
| H1 | Esiste almeno un Perturb-seq CRISPRi pubblico in linea T matura con matrice RNA scaricabile.  | operatore | solver_a f1: supported_declared; solver_b f1: undecided; solver_a f2: undecided; solver_b f2: undecided; solver_a f3: undecided; solver_b f3: undecided |
| H2 | Dove la matrice RNA manca dall'archivio, e' comunque ricostruibile da un supplemento o da un repository secondario del gruppo che l'ha prodotta.  | operatore | solver_a f1: open; solver_a f3: undecided |
| H3 | La direzione della risposta dipende dallo stato della cromatina nel contesto bersaglio piu' che dall'identita' del gene spento. | solver_b fase 1 | solver_b f1: open; solver_a f2: open; solver_b f2: open; solver_b f3: open |

**Spiegazioni alternative messe sul tavolo:**

| ipotesi | worker | alternativa |
|---|---|---|
| H1 | solver_a | L'accessione elenca il file ma il deposito e' sotto accesso controllato |
| H1 | solver_b | Il deposito esiste ma e' su accesso controllato |
| H1 | solver_a | il file e' elencato ma servito solo su richiesta |
| H1 | solver_b | accesso controllato |
| H1 | solver_a | accesso controllato |
| H1 | solver_a | il file e' elencato ma non servito |
| H2 | solver_a | I supplementi contengono solo pseudobulk aggregato |
| H3 | solver_b | La direzione dipende dalla co-espressione basale, che e' correlata alla cromatina ma non la stessa cosa |
| H3 | solver_a | dipende dalla co-espressione basale |
| H3 | solver_b | dipende dalla co-espressione basale |

## 5. Contraddizioni e lacune

**Il programma non chiude nessuna contraddizione.** Non e' in grado di leggere la fonte che ne deciderebbe una, e una contraddizione archiviata senza evidenza e' peggio di una contraddizione aperta. Restano tutte qui, con i passi da cui vengono.

| id | tipo | sollevata da | fase | fonte | testo | passi |
|---|---|---|---|---|---|---|
| X-b4f2afc006 | dichiarata | solver_a | 2 | — | Sulla stessa fonte (lo studio 2024 sulle cellule T primarie) io riporto che il segno si conserva fra lignaggi per i bersagli a effetto forte, lui riporta che non si conserva. Io cito la Fig. 3b del testo completo, lui le ultime frasi dell'abstract. | `steps/research_phase2-02-solver_a-47d87ebf-a2/` |
| X-d7845cf845 | dichiarata | solver_b | 2 | — | Sullo studio 2024 delle cellule T primarie: lui legge conservazione del segno fra lignaggi in Fig. 3b, io leggo il contrario nell'abstract. Resta aperta: non ho il testo completo per decidere. | `steps/research_phase2-02-solver_b-eb2299dd/` |
| X-f68e837166 | derivata dalla struttura (stessa fonte, direzioni opposte) | solver_a, solver_b | 3 | F-b558b4be5b | solver_a usa F-b558b4be5b a sostegno di [C-dfc8afd05b] «Gli autori riportano che il segno della risposta si conserva fra linee T diverse per i geni a effetto forte.»; [C-e7e4fe9413] «La didascalia della Fig. 3b dichiara che la figura usa i 112 bersagli con almeno 200 cellule, non tutti i bersagli de [... 711 caratteri non mostrati ...] | `steps/research_phase1-01-solver_b-57c23818/`, `steps/research_phase1-01-solver_a-70dbb24e/`, `steps/research_phase3-03-solver_a-81dfd0f3/` |

**Lacune dichiarate:**

| id | worker | fase | cosa manca | ricerca che la colmerebbe |
|---|---|---|---|---|
| G-b3f657233c | solver_a | 1 | Non so se il file di matrice dichiarato da GSE999001 sia effettivamente servito senza autenticazione. | Una richiesta della sola intestazione HTTP sull'URL del file, senza scaricarlo |
| G-d47ff31742 | solver_a | 1 | Non ho cercato nulla nel contesto squamoso oltre alla seconda query. | Ripetere la seconda query su ArrayExpress e su Zenodo, dove finiscono i depositi che non passano da GEO |
| G-e4355d764a | solver_b | 1 | Il contenuto di F2, l'unico candidato squamoso che ho trovato, resta ignoto. | Cercare un preprint dello stesso gruppo su bioRxiv, dove la versione aperta di solito esiste |
| G-be25eb386b | solver_b | 1 | Non ho verificato se F3 dica davvero quello che il titolo suggerisce. | Aprire F3 e leggerne almeno l'abstract |
| G-53687ace7d | solver_a | 2 | Nessuno dei due ha guardato ArrayExpress o Zenodo per il contesto squamoso. | La seconda query della fase 1, ripetuta su quei due archivi |
| G-388e2c7242 | solver_b | 2 | Nessuno di noi due ha letto il supplemento dello studio 2024, dove starebbe il dato che decide la contraddizione. | Scaricare il supplemento dalla pagina dell'editore, se e' aperto |
| G-18557f6773 | solver_a | 3 | La tabella supplementare S4 dello studio 2024, che direbbe se la contraddizione e' apparente. | Chiedere il supplemento agli autori, oppure cercare una copia depositata dal gruppo su un repository istituzionale |
| G-aa41130a4f | solver_a | 3 | Non ho mai provato a chiedere l'intestazione HTTP del file di matrice: la domanda che ha aperto la campagna resta senza risposta. | Una richiesta HEAD sull'URL del file dell'accessione |
| G-f1c8732c25 | solver_b | 3 | I server di preprint non sono stati interrogati: i due tentativi sono falliti per un errore del servizio, non per assenza di risultati. | Ripetere le stesse due query quando il servizio risponde, piu' la ricerca per autore che non ho tentato |

**Dichiarazioni di saturazione.** Un worker sostiene di aver esaurito la letteratura utile. E' una sua affermazione motivata: il programma puo' contare i duplicati e l'assenza di riferimenti nuovi, non dedurne che la letteratura sia esaurita. «Non abbiamo trovato evidenze nelle ricerche registrate» non diventa «non esistono evidenze».

| worker | fase | dichiarazione |
|---|---|---|
| solver_b | 3 | Dopo tre fasi ritengo che la letteratura aperta pertinente a questo perimetro sia sottile e che le query rimaste darebbero soprattutto duplicati. E' una mia valutazione: due dei tre archivi che volevo interrogare non hanno risposto, e non so cosa ci sia dietro i paywall che non ho aperto. |

## 6. Ricerche proposte e non eseguite

Queste sono le query che restano da fare. Sono il punto di partenza piu' economico di una campagna successiva.

| fase | worker | query | dove | filtri | stato | nota |
|---|---|---|---|---|---|---|
| 1 | solver_a | "no detectable transcriptional effect" CRISPRi T cell negative results | Europe PMC | nessuno | non eseguita | la lascio proposta: cercare i risultati negativi e' il modo piu' rapido di scoprire se l'assenza e' reale o di pubblicazione |
| 1 | solver_b | squamous epithelium CRISPRi atlas single-cell knockdown efficiency | PubMed | 2021-2026 | fallita | la seconda pagina di risultati non si e' caricata; ho fermato la query invece di riprovare a ripetizione |
| 2 | solver_a | Aaltonen 2024 primary T cell Perturb-seq "data availability" | Europe PMC | nessuno | non eseguita | e' la query della prima pista; la eseguo nella fase 3 |
| 2 | solver_b | Bergqvist Lorenzi squamous CRISPRi atlas preprint | bioRxiv | nessuno | non eseguita | e' la query della mia pista; la eseguo nella fase 3 |
| 3 | solver_a | Aaltonen 2024 primary T cell Perturb-seq supplementary table S4 | pagina dell'editore | nessuno | bloccata | il file supplementare richiede un abbonamento; mi sono fermato |
| 3 | solver_b | Bergqvist Lorenzi squamous CRISPRi atlas | bioRxiv | nessuno | fallita | errore di servizio della pagina di ricerca, due tentativi |
| 3 | solver_b | squamous epithelial identity CRISPRi single cell | medRxiv | nessuno | fallita | stesso errore |
| 3 | solver_b | Lorenzi keratinocyte CRISPRi 2025 | bioRxiv | ricerca per autore | non eseguita | non tentata dopo i due errori: la propongo per una campagna successiva |

## 7. Prossimo approfondimento suggerito

**Regola di selezione delle piste**, applicata dal programma: Una proposta prioritaria per worker -- la prima ben formata nell'ordine in cui l'ha scritta -- ordinate per nome del ruolo, deduplicate sull'ipotesi, troncate a 2. Nessun ripescaggio: se i due propongono la stessa pista, la pista e' una sola, e il fatto che coincidano e' un'informazione, non un posto vuoto da riempire.

Piste considerate: 5; selezionate: 2 (tetto 2).

| id | proposta da | ipotesi | spiegazione alternativa | ricerca che le distingue | cambio di strategia |
|---|---|---|---|---|---|
| L-231e74d438 | solver_a | La figura 3b e l'abstract dello stesso studio dicono cose opposte sulla conservazione del segno fra lignaggi. | non si contraddicono affatto: parlano di due sottoinsiemi diversi di bersagli, e l'abstract generalizza su tutti mentre la figura mostra solo quelli con almeno 200 cellule | aprire il testo completo e confrontare la popolazione di bersagli della figura con quella dichiarata nell'abstract; se le numerosita' differiscono, la contraddizione e' apparente | smettere di cercare fonti nuove e leggere per intero quella che abbiamo, compresi i supplementi |
| L-5097e3a754 | solver_b | Il candidato squamoso a paywall ha un preprint aperto con i dati depositati altrove. | non esiste nessun preprint, e il lavoro e' nato direttamente sulla rivista con i dati sotto accesso controllato: in quel caso l'assenza che vediamo e' reale e non e' un problema di dove abbiamo cercato | cercare gli stessi autori su bioRxiv e medRxiv per titolo e per nome; se il preprint esiste, leggerne la sezione sui dati; se non esiste dopo aver cercato per entrambi gli autori, l'alternativa e' quella giusta | cambiare fonte: dai motori bibliografici ai server di preprint, e cercare per autore invece che per argomento |

**Piste scartate, con il motivo:**

| id | worker | ipotesi | motivo |
|---|---|---|---|
| L-56a85d931c | solver_a | Il contesto squamoso ha un deposito pubblico che non passa da GEO. | pista incompleta: mancano spiegazione alternativa |
| L-56a85d931c | solver_a | Il contesto squamoso ha un deposito pubblico che non passa da GEO. | non e' la proposta prioritaria di questo worker |
| L-1a4c90a143 | solver_a | L'efficienza di knockdown e' il vero fattore limitante del trasferimento. | non e' la proposta prioritaria di questo worker |
| L-704cd2b3d9 | solver_b | L'efficienza di knockdown non e' riportata perche' gli studi non la misurano. | non e' la proposta prioritaria di questo worker |

**Domande aperte alla fine della fase 3:**

| worker | domanda |
|---|---|
| solver_a | Se il file di matrice dell'accessione sia davvero servito senza autenticazione: e' rimasta senza risposta per tre fasi |
| solver_a | Se il lavoro squamoso abbia un deposito da qualche parte che non ho interrogato |
| solver_b | Se il lavoro squamoso abbia un preprint: la domanda e' esattamente dov'era all'inizio della fase |

Le ricerche della sezione 6 e le lacune della sezione 5 sono, insieme a queste domande, il materiale di una campagna successiva. Il sistema non ne avvia nessuna: non esiste un percorso di codice che crei un nuovo incarico.

## 8. Perche' si e' fermata, e quanto e' costata

**Esito:** disaccordo irrisolto — 3 contraddizioni restano aperte; il programma non ne chiude nessuna da solo

**Consumo di interazioni.** Il conteggio include riparazioni di formato e tentativi di canale, non solo le risposte principali.

| voce | valore |
|---|---|
| posti previsti (fasi x worker) | 6 |
| posti con una risposta utilizzabile | 6 |
| risposte principali | 6 |
| riparazioni di formato | 1 |
| tentativi di canale ripetuti | 0 |
| risposte non leggibili | 1 |
| passi abbandonati | 0 |
| errori di canale | 0 |
| **interazioni totali** | **7** |
| tetto di risposte principali | 6 |
| tetto di interazioni totali | 12 |
| tetto di tempo (minuti) | 20 |

**Richieste dei worker all'operatore.** Sono state registrate e non hanno cambiato nulla: budget, instradamento e permessi si leggono solo dalla configurazione.

| worker | fase | richiesta |
|---|---|---|
| solver_a | 2 | Servono almeno altri due round: con tre fasi non si fa in tempo a leggere il testo completo e a interrogare gli altri archivi. Alzare max_rounds a 6 e le risposte principali a 10. |

**Campi scartati nelle risposte** (non previsti dal contratto, quindi senza effetto):

| worker | fase | campi |
|---|---|---|
| solver_a | 2 | budget, max_rounds |

**Segnalazioni del lettore di risposte:**

| worker | fase | segnalazione |
|---|---|---|
| solver_a | 2 | pista incompleta, non selezionabile: mancano spiegazione alternativa |
| solver_b | 2 | supported_by: il riferimento 'F1' non corrisponde a nessuna fonte elencata nella stessa risposta |
| solver_b | 3 | dichiara una saturazione della letteratura: resta una sua affermazione motivata, non una misura |

## Appendice A — le sintesi, verbatim

Conservate separate. Il dossier non le fonde, e nessun modello e' stato chiamato a farlo: sarebbe una campagna a parte, con un budget suo.

### solver_a — fase 1 — `steps/research_phase1-01-solver_a-70dbb24e/`

*Un candidato in linea T matura con matrice RNA dichiarata scaricabile, un secondo candidato squamoso con solo conteggi di guide.*

Ho cercato su GEO e su Europe PMC, con filtri su singola cellula e CRISPRi. Due candidati emergono nel perimetro. Il primo (accessione finta GSE999001, linea Jurkat) dichiara nella pagina di accessione file di matrice a singola cellula, oltre ai conteggi di guide: e' il candidato che soddisfa P1, P2 e P3. Il secondo, nel contesto squamoso, ha la pagina di accessione con i soli conteggi di guide, quindi non soddisfa P3 per come e' scritto il perimetro. Non ho verificato scaricando i file: ho letto la pagina di accessione e la sezione Data Availability dell'articolo collegato. Una terza query, sui risultati negativi, non l'ho eseguita per mancanza di tempo nella fase.

### solver_b — fase 1 — `steps/research_phase1-01-solver_b-57c23818/`

*La linea T matura piu' citata ha un fenotipo discutibile, e l'unico atlante squamoso che ho trovato non e' accessibile.*

Ho cercato su PubMed con filtri sul tipo cellulare e ho aperto tre lavori. Il piu' rilevante e' lo studio sulle cellule T primarie, di cui ho potuto leggere solo l'abstract: la rivista mi ha servito la pagina, non il PDF. Nell'abstract gli autori sono espliciti nel dire che il trasferimento fra lignaggi NON conserva la direzione della risposta, che e' l'opposto di quello che mi aspettavo di trovare. Un secondo lavoro, un atlante CRISPRi su epitelio squamoso, e' dietro paywall: l'ho registrato come non accessibile invece di riportarne il contenuto dal titolo. Un terzo lavoro l'ho visto solo nell'elenco dei risultati.

### solver_a — fase 2 — `steps/research_phase2-02-solver_a-47d87ebf-a2/`

*Un accordo sui candidati, una contraddizione sul contenuto dello stesso paper, e due piste.*

Concordiamo sull'esistenza di un candidato in linea T matura e sul fatto che il contesto squamoso resti scoperto. Non concordiamo su che cosa dica lo studio sulle cellule T primarie: io ho letto il testo completo e la figura 3b, il collega ha letto l'abstract, e le due letture dicono il contrario l'una dell'altra sulla conservazione del segno fra lignaggi. Questa non e' una divergenza di interpretazione risolvibile discutendo: o la figura e l'abstract dicono cose diverse, oppure uno di noi due ha letto male. Finche' non e' guardata, resta aperta. Segnalo anche che la sua affermazione sullo stato della cromatina si appoggia a una fonte che lui stesso registra come vista solo in un elenco di risultati, quindi non e' un risultato riferito dagli autori di niente.

### solver_b — fase 2 — `steps/research_phase2-02-solver_b-eb2299dd/`

*Il collega ha letto il testo completo e io l'abstract: la contraddizione resta, e non la chiudo a mio favore.*

Il collega ha letto una figura che io non ho potuto aprire, e riporta il contrario di quello che ho letto io nell'abstract. Non ho modo di decidere chi ha ragione senza il testo completo, quindi la lascio aperta: preferisco un disaccordo registrato a una concordanza costruita cedendo a chi ha letto di piu'. Accetto invece la sua obiezione sulla mia affermazione sulla cromatina: l'ho attribuita agli autori di un lavoro che ho solo visto in un elenco di risultati, e questo non e' un risultato riferito dagli autori. La declasso a ipotesi mia. Sul resto siamo complementari: lui ha guardato che cosa e' depositato, io se la linea sia il contesto che dichiara.

### solver_a — fase 3 — `steps/research_phase3-03-solver_a-81dfd0f3/`

*La ricerca sugli altri archivi non ha prodotto nulla; il supplemento che deciderebbe la contraddizione non e' accessibile.*

Sulla pista del deposito squamoso fuori da GEO: ho interrogato ArrayExpress e Zenodo con i termini della fase 1 e non ho trovato nessuna accessione riconducibile a quel lavoro. Questo NON vuol dire che non esista: vuol dire che le due query che ho registrato non l'hanno restituita, e che ho guardato due archivi su molti. Sulla pista della contraddizione: ho ritrovato lo studio del 2024 e ho riletto la Fig. 3b, che continua a dirmi quello che avevo riportato. Il pezzo che deciderebbe -- la tabella supplementare con la popolazione di bersagli usata nella figura e quella usata per la frase dell'abstract -- sta in un file supplementare che l'editore serve solo agli abbonati. Non l'ho aggirato. Quindi la spiegazione alternativa che avevo proposto io stesso, che i due passaggi parlino di sottoinsiemi diversi, resta plausibile e non verificata, e la contraddizione con il collega resta aperta.

### solver_b — fase 3 — `steps/research_phase3-03-solver_b-a3764f9d/`

*Nessuna evidenza nuova in questa fase: la ricerca sui preprint non e' andata a buon fine.*

Questa fase non ha prodotto evidenze nuove, e lo scrivo invece di ripetere la fase precedente con parole diverse. La pista che mi era stata assegnata chiedeva di cercare gli autori del lavoro squamoso sui server di preprint: ho tentato la ricerca per titolo e per autore, e la pagina di ricerca ha risposto con un errore di servizio in entrambi i tentativi. Non ho ripetuto oltre. Nessuna fonte nuova, nessuna affermazione nuova. Sulla contraddizione con il collega: lui ha letto che la figura usa 112 bersagli selezionati, il che rende plausibile che l'abstract e la figura parlino di popolazioni diverse. E' plausibile, non verificato, e la tabella che lo direbbe e' chiusa anche a lui. Non la considero risolta. Aggiungo una valutazione mia, e la presento per quello che e': dopo tre fasi ho l'impressione che la letteratura aperta su questo perimetro sia sottile, e che le poche query rimaste darebbero soprattutto duplicati. E' un'impressione motivata dal fatto che le ultime ricerche hanno restituito zero o gia' noto; non ho modo di sapere che cosa ci sia dietro i paywall che non ho aperto ne' negli archivi che non ho interrogato.

## Appendice B — tracciabilita'
| fase | worker | servizio | stato | durata | errore | cartella |
|---|---|---|---|---|---|---|
| 1 | solver_a | scripted | answered | 0.0s | — | `research_phase1-01-solver_a-70dbb24e` |
| 1 | solver_b | scripted | answered | 0.0s | — | `research_phase1-01-solver_b-57c23818` |
| 2 | solver_a | scripted | unparsed | 0.0s | no_result_block | `research_phase2-02-solver_a-7a2f33e4` |
| 2 | solver_a | scripted | answered | 0.0s | — | `research_phase2-02-solver_a-47d87ebf-a2` |
| 2 | solver_b | scripted | answered | 0.0s | — | `research_phase2-02-solver_b-eb2299dd` |
| 3 | solver_a | scripted | answered | 0.0s | — | `research_phase3-03-solver_a-81dfd0f3` |
| 3 | solver_b | scripted | answered | 0.0s | — | `research_phase3-03-solver_b-a3764f9d` |

Tutti i percorsi sono relativi a `C:\Users\ferra\AppData\Local\Temp\orch-ricerca-finale\runs\20260914T022455Z-ricerca-collaudo-v1-1485b2`. Il dossier completo, con ogni campo letto da ogni risposta, e' in `dossier.json`.
