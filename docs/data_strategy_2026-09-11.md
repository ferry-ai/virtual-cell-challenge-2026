# Strategia dati VCC 2026 — audit dell'11 settembre 2026

La raccomandazione è acquisire altri dati perturbazionali, scegliendoli per copertura di bersagli, geni misurati e contesti, e costruire una validazione esterna prima di aumentare la complessità del modello. I controlli ufficiali descrivono lo stato iniziale; da soli non identificano la risposta causale al knockdown. La gara 2026 non fornisce training perturbazionale: è una previsione zero-shot su nuovi contesti. [Annuncio Arc](https://arcinstitute.org/news/virtual-cell-challenge-2026).

Questo documento distingue misure locali, disponibilità pubblica verificata e proposte sperimentali. Non è stato allenato un modello, né misurato un miglioramento di leaderboard. I file RNA esterni nuovi non sono stati scaricati; sono stati acquisiti cataloghi e circa 21 MB di metadati HIPSCI con verifica MD5.

## 1. Cosa abbiamo davvero

Audit eseguito sulle tre matrici ufficiali e sui tre pseudobulk Replogle locali. Output in `reports/data_audit/`.

| Dato | Evidenza | Conseguenza |
|---|---|---|
| Controlli A/B/C | 18.400 cellule ciascuno, 18.533 geni, conteggi interi non negativi; ordine geni verificato | Conservare gli originali e il loro asse genico |
| Profondità mediana | A 20.109, B 19.946, C 20.034 UMI | La generazione deve preservare una distribuzione realistica delle librerie |
| K562 genome-wide | 272/300 bersagli; 7.681/18.533 geni di output | Buona baseline di trasferimento, copertura incompleta |
| K562 essential / RPE1 | 0/300 bersagli del pannello, con matching esatto | Utili per apprendere effetti generali e stress test, non come risposta osservata diretta ai 300 bersagli |
| Pseudobulk “raw” | Valori prevalentemente frazionari; mediane di 166/116/71 cellule per riga | Non sono singole cellule né somme intere: non usarli come input raw-count single-cell allo scorer |
| Simboli duplicati | 2 in K562 GWPS, 2 in K562 essential, 1 in RPE1 | Necessaria una regola esplicita di mapping e aggregazione |

La copertura utile è diversa dalla copertura nominale. Calcolando per cellula CPM e poi la media, prima dell'esclusione del bersaglio:

| Contesto | Geni con media >5 CPM nei controlli | Presenti nel pseudobulk K562 GWPS | Presenti nell'unione dei tre pseudobulk |
|---|---:|---:|---:|
| A | 9.929 | 7.094 (71,45%) | 8.134 (81,92%) |
| B | 9.626 | 6.881 (71,48%) | 8.196 (85,14%) |
| C | 10.124 | 7.058 (69,72%) | 8.306 (82,04%) |

L'unione delle colonne non equivale a osservare quegli output per ciascuno dei 300 knockdown: mancano le corrispondenti righe in RPE1/essential. Neppure questi numeri rappresentano percentuali di score recuperabile. I geni poco abbondanti possono avere effetti discriminanti forti.

I 28 bersagli senza matching Replogle sono nel file `acquisition_targets.csv`; la verifica degli alias potrebbe modificarne il numero. Il parser preesistente ignorava etichette con trascritti ENST: è stato esteso e la copertura del pannello resta 272. Le righe non interpretate restano esplicitamente segnalate. L'assenza dal pannello essential non dimostra che un gene sia biologicamente non essenziale.

## 2. Correzioni che influenzano tutta la strategia

Lo zero ufficiale è la media delle risposte perturbate selezionate, non la media NTC. PDS esclude tutti i geni bersaglio del pannello; le altre metriche escludono il bersaglio della singola perturbazione. Il filtro DE usa la media dei CPM dei controlli; la specifica distingue normalizzazione pseudobulk e per-cellula. Lo scorer ammette numerosità predette variabili, mentre il writer locale usa 400: verificare separatamente i vincoli del CLI di submission. [Specifica ufficiale](https://github.com/ArcInstitute/cell-eval2/blob/main/docs/vcc2026_metrics/vcc2026-metrics-brief.md).

Conseguenza metodologica: non limitarsi a stimare una media di espressione. La dispersione e la quota di cellule che rispondono modificano i test DE. Ripetere 400 volte una media o aggiungere rumore arbitrario non ricostruisce la distribuzione biologica.

Bloccare versione, preset, backend DE e seed nel benchmark. Le metriche grezze di `compute_metrics` non costituiscono automaticamente lo score aggregato con ancore della gara; costruire bundle/ancore locali e distinguerli da quelli ufficiali. [Documentazione cell-eval2](https://github.com/ArcInstitute/cell-eval2/blob/main/README.md).

## 3. Quali dati acquisire, in quale ordine

### Priorità 1 — H1 hESC VCC 2025 completo

Il deposito ufficiale comprende training, validation e test 2025: circa 300.000 cellule, 300 bersagli. Accesso via `gs://arc-institute-virtual-cell-atlas/virtual-cell-challenge/2025/`. [Deposito Arc](https://github.com/ArcInstitute/arc-virtual-cell-atlas/tree/main/virtual-cell-challenge).

È il candidato iniziale per una validazione vicina al tipo di benchmark e per calibrare risposte deboli e forti. La sovrapposizione con i 300 bersagli 2026 va ancora misurata. Usare H1 come contesto completamente escluso nella prima valutazione, poi ruotarlo nel training. Non scegliere gli iperparametri sul suo test locale congelato.

L'accesso Arc passa oggi da Google Cloud Marketplace, con progetto sottoscritto e bucket Requester Pays; il repository indica fino a 2 TB/mese senza costo nelle condizioni descritte. I vecchi bucket non sono il percorso da usare. [Istruzioni aggiornate](https://github.com/ArcInstitute/arc-virtual-cell-atlas). Non è stato attivato alcun servizio cloud.

### Priorità 2 — KOLF2.1J, Nourreddine/Doctor/Mali

Atlante CRISPRi di 11.692 geni e oltre 2,5 milioni di cellule, pubblicato il 1 luglio 2026. [Articolo](https://www.nature.com/articles/s41587-026-03199-w). Il [deposito Figshare](https://doi.org/10.25452/figshare.plus.27261219) espone AnnData, licenza CC BY 4.0 e checksum; catalogo verificato via API e salvato localmente.

| File | Dimensione decimale verificata |
|---|---:|
| Pan_Genome_QC_Filtered | 189,39 GB |
| Strong_Perturbations | 46,72 GB |
| Chromatin_Modifiers_QC_Filtered | 4,64 GB |
| Metabolic_Enzymes_QC_Filtered | 6,98 GB |

Proposta: partire dai sottoinsiemi QC, verificare target/controlli/layer e qualità; elaborare il completo a blocchi su disco adeguato, ricavando riassunti per guida e batch. La copertura dei nostri bersagli non è ancora misurata. Evitare il solo subset “Strong”: selezionare in base alla risposta osservata sovrarappresenta effetti facili e forti. Verificare sovrapposizioni fra subset prima di unirli.

Il browser degli autori segnala restrizioni sui FASTQ con sequenze Y; l'AnnData è il percorso pubblico pratico. Non serve ripartire dalle sequenze per questo progetto. [Accesso degli autori](https://y-doctor.github.io/KOLF2.1J_Perturbation_Cell_Atlas/).

### Priorità 3 — HIPSCI, Feng e colleghi: utile, con limiti quantitativi

Sanger descrive un pannello genome-wide di 7.226 geni distribuito su 34 linee/26 donatori e uno screen mirato su 20 linee/10 donatori. Offre [tabelle LFC](https://doi.org/10.6084/m9.figshare.26819743) e [conteggi con metadati](https://doi.org/10.6084/m9.figshare.27989294). [Fonte primaria Sanger](https://www.sanger.ac.uk/tool/crispri-scrna-seq-hipsci/).

Abbiamo scaricato i tre metadati e contato solo assegnazioni singole gene–guida riconosciute, separando linea e batch:

- 197/300 bersagli hanno supporto nei metadati.
- Si aggiungono 10 bersagli assenti in Replogle: ABCD1, HEATR6, MAPK7, PARP3, PDK3, SLC44A1, SNN, TAF4, TBC1D19, ZC2HC1A. Copertura combinata potenziale: 282/300 (94%).
- Nei pannelli genome-wide, per i nostri bersagli, mediana di 1–2 cellule per coppia gene–linea e massimo 14, sommando batch. I dieci recuperati hanno 19–68 cellule ciascuno sommando le linee.
- Lo screen mirato copre 5 bersagli; mediana 86 cellule per gene–linea, massimo 144. Nessuna coppia raggiunge 400.

Sono risultati di metadati, non evidenza di knockdown efficace o di matrice RNA utilizzabile. Il numero di linee non garantisce una matrice completa target × contesto. Usare soprattutto effetti aggregati con incertezza; il pannello mirato può studiare variazione tra donatori su altri bersagli. Tenere insieme nello split le linee dello stesso donatore.

I conteggi RNA compressi sono circa 1,45/1,75/4,48 GB; il CSV decompresso può essere molto maggiore. Le LFC genome-wide per gene sono circa 0,795 GB, quelle mirate per gene 0,078 GB. Prima leggere schema e normalizzazione; evitare di equiparare LFC da modelli statistici diversi.

### Priorità 4 — espansione selettiva

Usare [scPerturb](https://github.com/sanderlab/scPerturb) e [PerturBase](https://pmc.ncbi.nlm.nih.gov/articles/PMC11701531/) come indici per trovare studi umani CRISPRi con controlli e metadati. Risalire al deposito originario, verificare la modalità e deduplicare studi e mirror. Considerare altri contesti quando migliorano copertura o validazione; non sommare indiscriminatamente CRISPRa, knockout, enhancer perturbation e knockdown.

Tahoe, atlanti osservazionali e dati farmacologici possono aiutare rappresentazioni basali o programmi cellulari, ma non forniscono automaticamente le etichette CRISPRi richieste. I dati simulati, come Perturb Sapiens, vanno identificati come tali: eventuale distillazione da valutare con un'ablazione dedicata. [Descrizione Arc di Stack/Perturb Sapiens](https://arcinstitute.org/news/foundation-model-stack).

## 4. Contratto di preprocessing proposto

1. **Provenienza:** dataset/accession/versione/checksum; specie, linea, donatore, batch, tempo, tecnologia, modalità, guida, bersaglio, controlli e layer di conteggi. Un file mancante o un metadato sconosciuto deve essere visibile, non sostituito con una supposizione.
2. **Geni:** riconciliare Ensembl/versioni e simboli con una tabella salvata. Aggregare conteggi solo quando la mappatura è univoca e biologicamente corretta; altrimenti marcare ambiguità. Un gene non misurato ha una maschera, non un valore biologico zero. Conservare tutti i 18.533 output, anche se l'encoder usa meno feature.
3. **QC:** mantenere raw immutabili e auditare cellule vuote, multiplet, assegnazione guida, profondità e outlier per batch. Non regredire via automaticamente ciclo cellulare o stress: possono essere conseguenze del knockdown. Separare QC tecnico da selezione per intensità della risposta.
4. **Controlli:** confrontare perturbazione e NTC dello stesso studio/batch/tempo quando disponibili. Non trattare tutte le righe `core_control` come NTC senza verificare le etichette. Suddividere i controlli ufficiali per guida per diagnosticare stabilità; le 46 guide non sono necessariamente 46 repliche biologiche.
5. **Due riassunti:** conservare somme/numero cellule per profili pseudobulk e media dei conteggi normalizzati per cellula per effetti DE. Non confondere log della media e media del log, né normalizzazione dopo aggregazione e prima di aggregazione. Salvare varianza, detection rate e conteggi per gruppo.
6. **Effetti:** stimare delta rispetto ai controlli abbinati, per guida/batch, con shrinkage più forte quando numerosità o concordanza sono basse. Non dividere ingenuamente la risposta per l'efficienza del knockdown: vicino a zero è instabile e la relazione può essere non lineare.
7. **Training:** bilanciare contesti e perturbazioni, non solo cellule. Usare maschere di osservazione nella loss. Normalizzatori appresi, selezione feature e riduzione dimensionale devono essere stimati nel fold di training; gli NTC del nuovo contesto sono input consentiti nell'emulazione zero-shot.

## 5. Esperimenti che proporrei

**Primo modello:** trasferire effetti regolarizzati verso lo stato basale del contesto destinatario. Confrontare delta additivo in spazio log-normalizzato e trasferimento moltiplicativo delle proporzioni; stimare pesi fra sorgenti sul benchmark esterno. L'espressione del bersaglio deve modulare la fiducia in modo continuo: bassa detection non prova assenza di funzione.

**Ipotesi di ricerca:** separare un effetto condiviso per bersaglio, la sua modulazione da programmi basali e un residuo dipendente dal contesto. Una decomposizione a basso rango rende questo modello apprendibile con dati limitati; serve un'ablazione contro il trasferimento diretto per dimostrarne il valore. Non assumere che linee vicine globalmente condividano ogni risposta: i pesi possono dipendere dal pathway perturbato.

**Distribuzione single-cell:** confrontare trasporto di cellule NTC, modello di conteggi con dispersione e miscela responder/non-responder. L'efficienza delle guide nelle sorgenti informa il training; quella nascosta dei contesti ufficiali non è disponibile. Non inventare pairing reale fra cellule controllo e perturbate: eventuali accoppiamenti sono costruzioni del modello.

**Validazione:** split esterno per studio/linea, e per donatore dove necessario; nessuna cellula perturbata del contesto held-out nel training. Dentro questo disegno distinguere bersagli già osservati altrove e bersagli esclusi globalmente. Riportare risultati per intensità d'effetto, copertura e numerosità, con bootstrap per perturbazione e unità sperimentale. Il pannello essential K562↔RPE1 è uno stress test, non una stima sufficiente della gara.

Non duplicare cellule per trasformare un gruppo di 20 in uno di 400: non aggiunge informazione. Se la numerosità limita il benchmark, dichiararlo e riportare curve rispetto al numero di cellule. Usare l'intero scorer quando i conteggi sono disponibili; sul solo pseudobulk limitarsi a diagnostiche della media, senza chiamarle score VCC completo.

## 6. Decisione operativa e criteri di avanzamento

1. Recuperare H1 2025 e auditare KOLF QC; misurare copertura prima di ingestione completa.
2. Costruire almeno un benchmark esterno con conteggi single-cell e controlli identificati; verificare baseline NTC, trasferimento e stima della risposta media.
3. Aggiungere HIPSCI come sorgente con pesi legati all'incertezza; testare se migliora davvero generalizzazione e bersagli mancanti.
4. Passare al modello condizionato sul contesto solo dopo che supera le baseline su fold congelati. Tenere una quota di ricerca per bersagli non osservati: il pannello finale può cambiare.
5. Scaricare l'atlante completo solo se l'analisi della copertura o un'ablazione giustificano il costo. La decisione deve dipendere dal guadagno marginale, non dalla dimensione del dataset.

Limiti aperti: mapping alias completo, coverage H1/KOLF, efficienza e allineamento RNA HIPSCI, identità del backend ufficiale attivo e vincoli CLI. L'audit ha verificato dati e accessi, non risolto questi aspetti né dimostrato competitività del modello.

Riproduzione: `scripts/py.cmd scripts/12_audit_data_strategy.py`; poi script `13` per il catalogo, `14` per i soli metadati e `15` per la copertura HIPSCI. I due script di rete richiedono accesso Internet. Input non modificati; report e metadati sono nel repository.
