# Piano operativo scientifico e ingegneristico — 15 settembre 2026

**Responsabile:** Codex, direzione scientifica e pianificazione.
**Stato:** piano approvato dall'utente, con esecuzione compressa al 15 settembre.
L'utente avvia e supervisiona agenti contemporanei; solo il training può estendersi
oltre oggi. La [regia parallela](REGIA_PARALLELA_2026-09-15.md) assegna otto filoni,
consegne e dipendenze. Nessun nuovo training o incarico esterno è attestato da questa
modifica del piano. Le scansioni settimanali sotto restano come sequenza originaria,
superata per calendario e limiti di parallelismo dalla regia parallela.

## 1. Diagnosi e obiettivo

Il prossimo traguardo è un candidato migliore di trial-01, sostenuto da confronti
fuori campione e da una submission accettata. Non abbiamo ancora evidenza per
chiamarlo competitivo. Il punteggio storico del 13 settembre è **0,0459294**;
il rango 446 è quello di quella rilevazione, non una posizione attuale verificata.
Fonte: `reports/trial_2026-09-13/status_PNn227rxP3bVByS37W41.json`.

| Evidenza letta | Interpretazione operativa | Limite |
|---|---|---|
| Benchmark a tre contesti: su HepG2, seed 2026, MSE/nullo 0,9521 per ShrunkTransfer e 1,0825 per modular_frozen | Mantenere il trasferimento come riferimento da battere; il modulare attuale non giustifica uno scaling | Proxy pseudobulk, non sei metriche normalizzate; calibrazione interna diversa tra bracci |
| L'universo comune è 6.477/18.533 geni | Riportare copertura e prestazioni separatamente | Il successo su questa intersezione non prova copertura dell'output di gara |
| Esperimento HepG2: 25 bersagli, 40 cellule per bersaglio, sei metriche grezze | Esiste già un banco di prova su perturbazioni vere; ampliarlo e aggiungere ancore locali | Un contesto, campione piccolo, asse della sorgente, nessun punteggio di leaderboard |
| GO slim e rango aumentato non hanno passato i rispettivi confronti | Non riaprire queste griglie senza una nuova ipotesi verificabile | Non è una confutazione di ogni descrittore biologico o modello a basso rango |
| I modelli attuali sono NumPy; la GPU riguarda eventualmente il backend DE | Separare migrazione dei dati, valutazione accelerata e futuro training GPU | Trasferire il notebook non converte il modello in codice CUDA |

Fonti: `reports/benchmark_3ctx_2026-09-14/comparison_table.md`,
`reports/benchmark_3ctx_2026-09-14/summary.json`,
`reports/hepg2_2026-09-14/generator_x_predictor.json`,
`reports/go_slim_2026-09-15/summary.json`,
`reports/rank_2026-09-15/rank_summary.json`,
`reports/gpu_2026-09-15/gpu_readiness.json`.

**Giudizio sul modello:** separare basale, risposta e generazione resta una buona
organizzazione degli esperimenti. L'ipotesi che la specifica base condivisa e il
descrittore di contesto migliorino la generalizzazione non è confermata. Prima di
abbandonare l'intera famiglia, controllare calibrazione, scala dei descrittori e
differenza fra validazione entro linea e trasferimento fra linee. Un audit può
motivare una nuova prova; non annulla i risultati negativi già misurati.

## 2. Dati: distinguere raccomandazione ufficiale e utilità misurata

La [presentazione ufficiale 2026](https://arcinstitute.org/news/virtual-cell-challenge-2026)
conferma il compito zero-shot e rimanda all'Atlas; cita il dataset completo 2025 e
raccomanda la lettura di PRiMeFlow. Il testo della sezione dati del profilo utente
è stato **ricevuto dall'utente il 15 settembre**: Replogle 2022, Nadig 2025,
Jiang 2025, Srivatsan 2020 e McFaline-Figueroa 2024, oltre all'Atlas.
Il testo incollato non contiene gli URL dei pulsanti: i link sotto sono stati
ricercati separatamente. Le dimensioni del profilo sono dichiarazioni del sito,
non misure effettuate sui file durante questa sessione.

### Priorità aggiornata dopo la risposta dell'utente

1. **Jiang: audit prioritario per diversità di contesto.** Il repository degli
   autori [Mixscale](https://github.com/satijalab/Mixscale) collega i dati a
   [Zenodo 14518762](https://zenodo.org/records/14518762). Il record espone circa
   20,5 GB: cinque oggetti Seurat/RDS da 2,6–5,6 GB, più risultati DE e materiali.
   Si può pianificare un blocco per volta. Il blocco TGFB da 2,6 GB è candidato
   tecnico iniziale per dimensione, non per forza dell'effetto. Conteggi, metadati,
   numero di cellule utilizzabili e RAM per deserializzare RDS restano da misurare.
2. **Nadig/Jurkat: quarto contesto del benchmark già avviato.** Nel profilo:
   HepG2 5,2 GB e Jurkat 8,7 GB. L'audit locale usa invece un HepG2 da 850.590.740
   byte, 145.473 × 9.624: non assumere equivalenza o perdita di informazione dalla
   sola dimensione. Confrontare asse, barcode, guide, filtri e matrice. Il precedente
   probe Jurkat misura zero target del pannello attuale: utile come contesto di
   training/validazione su target condivisi, non come copertura diretta dei 300.
3. **Replogle:** preservare le baseline locali e verificare cosa aggiungono i
   single-cell consigliati (61,3/9,9/8,1 GB dal profilo) rispetto ai pseudobulk;
   priorità a conteggi reali per validazione e copertura, non al download completo.
4. **Srivatsan/sci-Plex:** farmacologico (188 composti secondo il profilo), utile
   eventualmente al pretraining e alla variazione di contesto. Non aggiunge
   direttamente etichette di knockdown; nessuna ingestione nella prima settimana.
5. **McFaline-Figueroa/sci-Plex-GxE:** la [pagina del laboratorio](https://cole-trapnell-lab.github.io/papers/mcfaline-sci-plex-gxe/)
   conferma perturbazioni genetiche e chimiche combinate. Prima di unire: verificare
   meccanismo genetico, controlli vehicle, dose/tempo e bracci separabili. Priorità
   successiva a Jiang/Jurkat; non trattare l'effetto combinato come CRISPRi semplice.

**Jiang richiede uno split specifico.** Il record GEO GSE281048, consultabile negli
estratti indicizzati ma bloccato da controllo browser all'apertura diretta, descrive
sei linee e stimoli IFNB/IFNG/TGFB/TNFA/INS. Tenere fuori tutte le condizioni di una
linea insieme, appaiare NTC per linea/stimolo/batch e usare solo stimoli realmente
confrontabili. Sei linee × cinque stimoli non sono trenta linee indipendenti.
Nel trasferimento verso la gara, lo stimolo è una covariata e una possibile fonte
di mancata trasferibilità. La copertura del pannello non è ancora calcolata.

Fonti locali per Nadig: `reports/hepg2_2026-09-14/nadig_hepg2_audit.json`,
`reports/candidate_verification/coverage_summary.json`.
L'incarico `configs/orchestrator/briefs/vcc2026-jiang-audit.yaml` incorpora queste
domande e allega il pannello, evitando la lacuna della campagna precedente.

| Sorgente | Ruolo proposto | Primo controllo necessario |
|---|---|---|
| K562, RPE1, HepG2 già acquisiti | Riferimento riproducibile e sviluppo | Deduplicare esperimenti, fissare split e versioni |
| H1 / VCC2025 completo | Ulteriore contesto perturbato; controllo della generalizzazione | Manifesto file e byte, RNA effettivo, NTC, guide, asse genico; localmente la documentazione riporta solo metadati |
| CD4 / GWCD4i | Priorità condizionata per copertura e diversità | Riconciliare GSE314342, Zenodo e mirror: non contare lo stesso esperimento come nuova sorgente; verificare donor/stato/guide e celle utilizzabili |
| Tahoe-100M nell'Atlas | Eventuale pretraining o descrittore di contesto | È farmacologico: nessuna equivalenza automatica farmaco → knockdown |
| scBaseCount nell'Atlas | Eventuale rappresentazione dello stato basale | Dati osservazionali non costituiscono etichette CRISPRi |
| Altri dataset consigliati nel profilo | Coda da completare | Stesso audit; priorità alla diversità perturbativa e ai target condivisi |

La tabella qui sopra conserva i ruoli delle altre sorgenti; l'ordine operativo è
quello della priorità aggiornata. CD4 resta una pista di copertura, da riaprire dopo
l'audit dei dataset esplicitamente consigliati, senza duplicare lo studio già censito.

La natura dei componenti Atlas è descritta dalla
[fonte Arc](https://arcinstitute.org/tools/virtualcellatlas) e le modalità di accesso dal
[repository ufficiale](https://github.com/ArcInstitute/arc-virtual-cell-atlas/).

**Scheda obbligatoria per sorgente:** identificatore dello studio e versione, URL
primario, licenza/accesso, CRISPRi/KO/CRISPRa/farmaco, linea/donatore/stato/batch,
numero di bersagli, corrispondenza simboli/ENSG, RNA grezzo o normalizzato,
campo NTC e guide, cellule per bersaglio, geni misurati, byte remoti e temporanei,
checksum, sovrapposizione con pannello attuale e con training. Dato mancante resta
mancante. Non filtrare sul numero di geni DE o sull'ampiezza dell'effetto.

La copertura dei 300 geni attuali serve al pilot; non deve escludere a priori fonti
utili ai nuovi target del set finale. Conservare anche un campione di target extra.
Per acquisire: file identificato e accessibile, NTC abbinabili, budget misurato,
piccolo estratto validato. Per adottare nel modello: ablation con e senza la fonte
sugli stessi split. La prima condizione non implica la seconda.

## 3. Locale, Kaggle e Colab

**Proposta:** elaborare i file pesanti direttamente nella macchina remota dalla
sorgente, salvare blocchi e firme ridotte, riportare in locale manifesti e risultati.
Evitare il percorso download sul portatile → upload sul cloud.

**Risorse dichiarate dall'utente:** account Kaggle e Colab disponibili; GPU del
compagno non disponibile fino al 16 settembre; training con checkpoint accettato.
Hardware e quote non ancora misurati. Il piano dimensiona una sessione disponibile
alla volta e salva risultati portabili, senza presumere la somma delle quote.

| Ambiente | Lavoro iniziale | Condizione di avvio |
|---|---|---|
| Locale | Orchestrazione, metadati, review, test, pilot pseudobulk, packaging streaming | RAM e disco liberi rimisurati prima del job |
| Kaggle | Primo candidato per notebook riproducibile di ingestione/scoring | Account, rete, quota disco, persistenza e acceleratore verificati nel runtime |
| Colab | Alternativa per pilot interattivo e debugging | Stesse verifiche; export dei risultati e ripresa dopo interruzione |
| GPU del compagno | Scoring DE, poi eventuale training implementato per GPU | Hardware, dipendenze e backend effettivo verificati |

Non assumere una quota standard di GPU, RAM o spazio. La
[FAQ Colab](https://research.google.com/colaboratory/faq.html) dichiara risorse
variabili e runtime temporanei. La [pagina Kaggle](https://www.kaggle.com/docs/notebooks)
non ha restituito testo leggibile in questa verifica: quote dell'account non accertate.

**Contratto del primo notebook remoto, da implementare:**

1. Registrare Python, dipendenze, commit più snapshot delle modifiche locali,
   CPU/RAM/disco/GPU, backend scorer, rete e spazio persistente disponibile.
2. Risolvere tutti i percorsi da `VCC2026_DATA_ROOT`; nessun percorso Windows nel job.
3. Leggere il manifesto della sorgente e stimare picco disco: input contemporanei +
   decompressione + derivati + checkpoint + export, con margine del 25% proposto.
4. Scaricare un solo blocco, con checksum e file parziale; imporre un tetto di byte.
   HDF5 su HTTP non è automaticamente streaming efficiente: misurare il traffico.
5. Estrarre a blocchi RNA/NTC e firme; conservare maschere dei geni non misurati.
6. Salvare dopo ogni blocco con identità degli input, seed e stato; simulare una
   interruzione e verificare che la ripresa non duplichi righe o ricalcoli tutto.
   Per training iterativo salvare anche pesi, stato ottimizzatore e scheduler,
   stato dei generatori casuali, epoca/step, cursore del sampler, precisione e
   configurazione. Per la pipeline NumPy corrente il checkpoint è prima di tutto
   per fase/fold; non dichiarare una ripresa a metà fit finché non è implementata.
7. Esportare artefatti e checksum, rileggerli dalla destinazione persistente.
   Un file rimasto sul disco effimero non è una consegna.

Primo job proposto: campione HepG2 già noto per verificare parità locale/remoto,
poi un blocco della sorgente prioritaria. CPU inizialmente; GPU solo dopo aver
verificato il backend DE. Nessun porting PyTorch prima di evidenza di costo e utilità.

## 4. Protocollo che decide la direzione

Due compiti distinti: **nuovo contesto, target già perturbato altrove** e **nuovo
contesto, target mai perturbato nel training**. Nel secondo si escludono tutte le
risposte del target da ogni sorgente di fit e calibrazione. NTC del contesto query
ammessi, risposte perturbate vietate. Guide dello stesso target sempre raggruppate;
donatori e batch preservati e controllati. Deduplicazione prima degli split.

- Fissare split esterni e lista delle prove prima di eseguirle. I fold del 14–15
  settembre sono ormai dati di sviluppo: un nuovo seed non li rende una conferma
  indipendente. Riservare target nuovi e, appena possibile, un contesto ulteriore.
- Calibrazione e selezione di rango, descrittori, sorgenti e generatore nei soli
  dati di training/validazione interna; stesso budget e criterio fra bracci.
  Non riusare 0,1974 come costante universale.
- Confrontare nullo diagnostico, risposta media stimata dal training,
  ShrunkTransfer e un solo candidato semplice. La baseline media ufficiale usa
  ground truth del contesto ed è un'ancora locale, non un predittore utilizzabile.
- Primo esperimento: due predittori × due generatori, con stessi target e seed
  di campionamento appaiati; nullo per verificare DE spurio e distorsione del basale.
- Riportare tutte le sei metriche, gate vuoti e denominatori, per contesto e
  protocollo. Non mediare sei valori grezzi con scale diverse.
- Costruire ancore **locali** baseline/replicato con cellule disgiunte e controlli
  propri, secondo la specifica ufficiale. Nessun tuning del candidato sulle ancore
  del test. Se il denominatore è instabile, riportare metriche grezze e incertezza;
  non produrre un totale apparentemente confrontabile con la leaderboard.
- Bootstrap appaiato per target, separato per contesto; i seed non sono repliche
  biologiche e tre linee non sostengono un'affermazione generale su tutti i tessuti.

Riferimento: [specifica delle metriche](https://github.com/ArcInstitute/cell-eval2/blob/main/docs/vcc2026_metrics/vcc2026-metrics-brief.md).
Versione locale e server vanno registrate; la pagina web consultata non prova la
parità con la versione installata.

**Regola proposta di promozione:** su dati di conferma non usati per scegliere,
IC95 della differenza appaiata del totale locale normalizzato candidato − baseline
interamente positivo; controlli di nullità e formato validi. Per ogni contesto e
metrica stabilire prima una tolleranza da ripetibilità su sviluppo; eventuali danni
oltre tolleranza impediscono la promozione. Se mancano ancore stabili o conferma
indipendente, dichiarare il candidato esplorativo e motivare separatamente una
submission diagnostica. Nessun punteggio obiettivo inventato.

## 5. Sequenza originaria: tutte le attività anticipate a oggi

**Aggiornamento dell'utente:** le date della tabella seguente non sono più scadenze
operative. Tutte le attività sono assegnate oggi secondo
[REGIA_PARALLELA_2026-09-15.md](REGIA_PARALLELA_2026-09-15.md); si conservano le
dipendenze dei risultati, non l'attesa fra giorni. Revocato il limite di due filoni.

| Giorno | Responsabile | Attività | Consegna e condizione di chiusura |
|---|---|---|---|
| 15 settembre | Lead scientist | Audit dello stato, fonti ufficiali, priorità e incarichi | Piano ed elenco del profilo acquisito; accesso Kaggle/Colab dichiarato, quote da misurare |
| 16 settembre | Researcher DeepSeek; revisore Kimi; verifica locale del lead | Audit Jiang e Jurkat, controlli, stimoli e duplicati | Tabella sorgenti con prove; massimo due acquisizioni candidate; nessuna copertura dichiarata senza file |
| 17 settembre | Implementatore dati | Preflight e notebook remoto sul campione HepG2 | Parità di input/output, misura RAM/disco/byte, ripresa ed export verificati |
| 18 settembre | Implementatore dati + lead | Pilot di una sorgente prioritaria | Manifesto, NTC abbinati, QC, maschere, conteggi; decisione acquisire/scartare/approfondire |
| 19 settembre | Researcher valutazione + implementatore | Ancore locali e disegno predittore × generatore | Confronti sulle sei metriche e nullo; nessun tuning sui dati di conferma |
| 20 settembre | Implementatore modello; revisore Kimi | Ablation della nuova sorgente e singolo candidato calibrato | Tabella appaiata con/senza dati e con/senza contesto; costo e copertura |
| 21 settembre | Lead scientist | Review delle evidenze e scelta del prossimo trial | Candidato congelato e submission diagnostica se giustificata; altrimenti causa del fallimento e un solo esperimento successivo |

Se il runtime non è pronto, il 16–18 settembre si lavora sui metadati Jiang/Jurkat e sul
pilot locale HepG2, senza dichiarare completata la migrazione. La scalabilità non
deve bloccare la verifica metodologica già possibile.

**Ritmo per ogni giornata attiva:** 15 minuti di triage su nuovi artefatti; un
esperimento principale con domanda e regola d'arresto; review di fine giornata con
misure, decisione, blocco e prossimo passo. Massimo due filoni aperti: dati e
valutazione/modello. Ricerca aggiuntiva solo se cambia una decisione eseguibile.

## 6. Uso dei worker

Gli incarichi pronti sono `configs/orchestrator/briefs/vcc2026-jiang-audit.yaml`,
`configs/orchestrator/briefs/vcc2026-primeflow-audit.yaml`
e `configs/orchestrator/briefs/vcc2026-validation-review.yaml`. Ordine: Jiang,
protocollo, poi PRiMeFlow solo se resta utile alla decisione. Sono incarichi
delimitati, **non esecuzioni completate**. Il primo cerca fonti; il secondo critica
il protocollo e può lavorare senza browsing. Non contengono credenziali o dati cellulari.

DeepSeek: ricerca mirata con URL e livello di lettura. Kimi: verifica del materiale
ricevuto, controesempi e criteri di test; ricerca indipendente solo quando il canale
la supporta. Implementatore: codice e artefatti, con test; lead: verifica fonti,
esegue/controlla misure, accetta modifiche e decide priorità. Il consenso fra worker
non è una prova e nessun worker web vede automaticamente file locali.

Per gli incarichi sui dataset allegare prima pannello e inventario deduplicato,
entro il perimetro dell'incarico. La campagna precedente non li aveva: il dossier
`reports/ricerca_dataset_20260915.md` lo dichiara. Le query di DeepSeek sono
**dichiarate**, non osservate dall'orchestratore; Kimi segnala assenza di browsing.
Non ripetere una campagna generica con gli stessi input incompleti.

I brief già preparati hanno un budget di tre fasi di ricerca o due round di review;
un seguito soltanto se c'è una nuova fonte, una contraddizione verificabile o una
prova da implementare. Questo limita il costo di revisione anche quando i worker
sono gratuiti. Questi sono limiti del singolo run, non un limite al numero di
incarichi attivabili oggi: l'utente ha autorizzato tutti i filoni possibili in
parallelo. Nessuna promessa di disponibilità continua dei servizi.

**Verifica operativa della sessione:** il caricatore degli incarichi è disponibile.
Il comando `orch brief` ha letto i primi due incarichi, ma ha fallito nell'aprire
il database di stato esterno (`sqlite3.OperationalError: unable to open database file`).
Non è prova di guasto dei servizi DeepSeek/Kimi. Validazione successiva tramite i
caricatori senza aprire il database; avvio live non effettuato.

## 7. Milestone fino alla chiusura

**Aggiornamento:** audit, preparazione, implementazione e verifiche fattibili sono
anticipati a oggi, incluse le opzioni State/PRiMeFlow e tutte le sorgenti elencate.
Le finestre precedentemente proposte sotto non giustificano rinvii; restano validi
il rilascio esterno dei dati finali e i lavori dipendenti da training non conclusi.

- **22–28 settembre:** conferma su dati nuovi, primo candidato migliorato;
  completare almeno una ablation di sorgente e una di generatore.
- **29 settembre–12 ottobre:** allargare contesti/target e un solo confronto
  esterno (State o PRiMeFlow) se audit di input, pesi, costo e split lo rende fattibile.
- **13–21 ottobre:** congelare selezione del metodo; prova completa di inferenza,
  packaging, ripresa, disco e consegna. Tenere una baseline riproducibile di riserva.
- **22 ottobre:** acquisire D/E/F e nuovo pannello; verificare contratto, mapping e
  supporto senza pretendere di avere le risposte perturbate.
- **23 ottobre–2 novembre:** inferenza e verifiche, consegna finale con margine.
- **3–5 novembre:** buffer per errori di infrastruttura/formato. Scadenza ufficiale:
  5 novembre 2026, 23:59 UTC (6 novembre, 00:59 in Italia).

## 8. Disallineamenti da tenere visibili

La mappa contiene righe iniziali che parlano ancora di banco reale bloccato,
mentre documenta sotto l'esperimento HepG2. La guida GPU suggerisce una sostituzione
SVD che CP-0015 non ha accettato. Il riepilogo JSON a tre contesti conserva inoltre
testo di verdetto riferito a due contesti; contiene 2.315 target disponibili, contro
2.319 citati nella mappa. Usare tabella e split della singola esecuzione; non
riconciliare numeri diversi senza controllare filtri e sorgenti. Sono problemi di
tracciamento da correggere, non ragioni per inventare una nuova misura.

## 9. Verifica della consegna

Eseguiti il 15 settembre: controllo documentale superato (15 checkpoint), tre
incarichi validati tramite `load_brief` e, dove applicabile, `load_research_brief`;
suite `unittest discover -s tests`: 429 test, esito OK, uno saltato, 183,153 s.
Il pannello allegato è una copia del CSV ufficiale locale. Questi controlli
verificano struttura e regressioni, non fattibilità del runtime remoto o qualità
scientifica futura. Notebook remoto, training e consultazioni live restano da eseguire.
