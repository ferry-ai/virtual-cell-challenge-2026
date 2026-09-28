# Audit di piani, dati e modello — 26 settembre 2026

Codex, task `01a0dda7-acf9-71a2-bb1a-6a35fb6f3164`. Analisi richiesta dal
proprietario mentre Claude lavora nel checkout. Nessuna modifica al modello,
nessun addestramento, download di dataset o invio. Le osservazioni sul codice
sono una fotografia: gli hash in [r1/measurements.json](r1/measurements.json)
identificano i file esaminati prima delle successive modifiche concorrenti.

## 1. Conclusione

**Non stiamo usando tutti i dataset trovati.** Il t20 usa tre sorgenti di effetti:
K562, CD4 e Orion HCT116. HEK293T entra nel nuovo banco e nel training dello
stadio 104 in sviluppo, ma non nella ricetta t20. Mixscale, DLD-1, RPE1,
HepG2 e gli altri dati hanno ruoli differenti o ancora incompleti.

La direzione utile è ampliare copertura e qualità, mantenendo il trasferimento
dello stesso bersaglio come riferimento. Due urgenze precedono la promozione di
un modello: riparare l'isolamento del banco (§4) e riconciliare le sorgenti
dimenticate/incompletamente utilizzate (§2). Integrare ogni dataset nella stessa
media non è un criterio di successo; assegnare a ciascuno un ruolo verificato sì.

## 2. Inventario riconciliato

Misure nuove, leggere: 195 file sotto la radice locale `external`, elenco in
[local_external_files.json](r1/local_external_files.json); 77 accessioni distinte
menzionate nei Markdown di docs/reports, con tutte le provenienze in
[accession_mentions.csv](r1/accession_mentions.csv). **Non sono 77 dataset
validati**: vi sono accessioni collegate, citazioni storiche errate, dati inadatti
e possibili duplicati. Il censimento non copre conversazioni esterne o contenuti
esistenti soltanto nei tag; i cataloghi storici conservati sono stati letti.
I record Figshare e le sorgenti senza accessione GEO sono riconciliati sotto.
Presenza di file e dimensione non certificano contenuto, completezza o qualità.

| Sorgente | Uso verificato o evidenza disponibile | Lacuna / prossimo impiego proposto |
|---|---|---|
| Replogle K562 genome-wide | t20; cache di produzione 272 bersagli; universo di ricerca 9.866 nel manifest | Usare l'universo per training e split realmente nuovi; non confondere cache universo con training già esteso a tutti i bersagli |
| K562 essential e RPE1 | Due h5ad pseudobulk locali; vecchi banchi/calibrazione | Recuperare come studi/contesti di valutazione; 0 overlap col pannello attuale non li rende inutili per J |
| CD4 / GSE314342 | Estratto locale; cache mix 293 bersagli, Rest 293, 8h/48h 292; t20 | Universo ancora limitato al pannello; incertezza tra donatori e covarianza fra condizioni da modellare |
| Orion HCT116 / HEK293T | Entrambi estratti locali; cache 268 / 281 bersagli; HCT116 nel t20, entrambi nel banco appreso | Universi completi mancanti nelle cache ispezionate; studio comune, non due repliche indipendenti |
| Nadig HepG2 e Jurkat | HepG2 nei banchi storici; nuovo banco F2 preparato; scheda Jurkat storica | HepG2 può essere test esterno solo se congelato e non usato per tuning; non confondere Jurkat Nadig con Song |
| Mixscale / GSE281048 / Zenodo 14518762 | ZIP DE locale; 218 bersagli, sei linee, cinque stimoli; analisi di pattern/H6 | Controlli della stessa condizione e guide ancora da estrarre; DepMap è un surrogato basale, non lo stesso campione |
| DLD-1 / GSE337988 | Low1/Low2 LFC, SE Low1 e metadati locali; audit | Supporto parziale delle risposte; identificare promotori e log; prova mascherata, non zeri fuori pannello |
| Song Jurkat / GSE249595, serie GSE247601 | File transcriptome, guide e hash di 16 canali presenti localmente | Il readout mirato e la MOI richiedono audit; lunghezza dell'elenco feature non dimostra trascrittoma misurato per intero |
| HIPSCI / Figshare 26819743 e 27989294 | Catalogo API dell'11 settembre e tre tabelle metadati nel repo; 197/300 supportati nei metadati | Non presente come matrice RNA/LFC sotto `external`; rimettere nel piano dati per generalizzazione fra donatori |
| KOLF2.1J / Figshare 27261219 | Catalogo già dell'11 settembre; ripreso nelle ricerche recenti | Distinto da HIPSCI; nessuna cache locale individuata; evitare di scegliere soltanto perturbazioni forti per test rappresentativi |
| H1 gara 2025 | Solo quattro CSV locali | RNA non trovato nel percorso locale; candidato esterno, non sorgente pronta |
| H1 / GSE295214 | Scheda candidata distinta dal dataset gara 2025 | Verificare matrice e metadati prima di identificare i due H1 come stessa sorgente |
| VIPerturb-seq / Zenodo 18460279; demo K562 Flex 10x | Candidati, non nelle cache locali | Priorità per verificare il trasferimento tra saggi; mantenere identità di esperimento separate finché deduplicate |
| DepMap 24Q4 | Model, espressione e copy number locali; H6 usa espressione | Descrittori e controlli di confondimento, non etichette di knockdown |
| STRING e GENCODE | File locali; prior cis/rete e nuovo trasferimento appreso | STRING non fornisce automaticamente verso e segno regolatorio; cache derivate entro fold |
| THP-1 GSE221321; Papalexi GSE153056 | Candidati in due ricerche di date diverse | Non deduplicare per sola linea; separare KO/CRISPRi e multimodale |
| A549 GSE345058 e GSE337804 | Candidati distinti | Confronti KO/i, con modalità esplicita; non trasferire KO come se fosse lo stesso intervento |
| Southard CRISPRa, Hs27/RPE1 | Quattro record Zenodo nelle schede del 25 | Programmi TF e differenze tra contesti; non invertire automaticamente il segno per ottenere CRISPRi |
| Jost GSE132080; microglia GSE335887; PerturbFate GSE291147 | Candidati R-SWITCH, non cache di produzione | Dose, quota rispondente e tempo: valore meccanicistico anche con pochi bersagli |
| Organoidi GSE280506 e PRJNA1219803; Ker-CT Squiers | Schede candidate | Studi distinti; matrici/accesso da verificare, separare trattamento ed effettore |
| Pisces | Disponibilità incompleta nella scheda storica | Non contare come acquisito; stato attuale del rilascio non riverificato in questo audit |
| Neuroni GSE289235, glia GSE284197, HSPC GSE274113, GSE343369 | Candidati di contesti lontani | Conservare per ruoli di ricerca; la correzione della scheda neuroni riduce il pannello a 45 geni |
| GSE275483, GSE327057, GSE320250; cervello murino Flex; GSE344535 | Specie o bersagli diversi nelle schede | Confronti tecnici/ortologia esplicita; non etichette umane intercambiabili |
| Altre accessioni e schermo 16 linee del preprint 2026.08.24.746802 | Inventario delle menzioni e schede del 24–25 | Coda da verificare, con stato non adottato; non scomparire perché manca un file oggi |
| sci-Plex3, McFaline GxE, Tahoe, scBaseCount; MCF10A GSE108699, GSE190604 | Candidati storici differiti/esclusi dal trasferimento diretto | Conservare ruolo farmacologico, osservazionale o misto; rivedere esclusioni di ricerca basate solo sul lignaggio/modalità |
| PRiMeFlow | Fattibilità di un metodo nel report storico | Non è un dataset addizionale; non conteggiarlo come sorgente |

Fonti: [catalogo originale](../data_audit/public_catalog.json),
[copertura HIPSCI](../data_audit/hipsci_coverage.json),
[schede del 15](../source_cards_2026-09-15/decisions.md),
[schede del 24](../schede_sorgenti_2026-09-24/SCHEDE.md),
[ricerca del 25](../ricerca_sorgenti_2026-09-25/RISULTATI.md),
[universo K562](../universo_2026-09-26/r1/manifest.json).

**Correzione documentale verificata:** la scheda 17 del 24 settembre sospetta
che HIPSCI sia KOLF. Il [Sanger](https://www.sanger.ac.uk/tool/crispri-scrna-seq-hipsci/)
descrive lo studio su 34 linee/26 donatori e un braccio mirato su 20 linee/10
donatori, con accessioni proprie. Il catalogo locale aveva già distinto quei
record da KOLF. I numeri complessivi non significano che ogni bersaglio sia
misurato in tutte le linee. Questo è un candidato particolarmente pertinente
all'incertezza fra donatori, non un miglioramento predittivo già dimostrato.

**Selezione sull'esito:** la proposta del 25 di privilegiare KOLF Strong
Perturbations può servire come pilot, ma non come test rappresentativo dei
bersagli futuri. Anche il [record VIPerturb-seq](https://zenodo.org/records/18460279)
distingue un oggetto filtrato per fingerprint e tre blocchi genome-wide.
Registrare il filtro e mantenere la popolazione di riferimento: il file minore
non è necessariamente un campione neutrale del file maggiore.

## 3. Piani vecchi e attuali: che cosa mantenere

| Fase | Cosa ha insegnato | Implicazione attuale |
|---|---|---|
| Calibrazione pseudobulk di settembre 11–15 | α≈0,197 ottimizza una coppia e una MSE proxy | Non è una costante biologica o l'ottimo dello score; i t15/t16 lo hanno mostrato |
| Modello condizionato/t07 | Quel modello e quel descrittore di contesto non hanno prodotto l'invio migliore | Non prova che contesto, reti o nuovi bersagli siano impossibili |
| Trasferimento multisorgente | CD4 ha un contributo ufficiale attribuito; HCT116 migliora insieme al cambio pesi; HEK293T non conclusivo | Conservare baseline e ablazioni sullo stesso supporto |
| t16 → t20 | +0,0020487 ufficiale, entro banda non conclusiva; cambiano restrizione, ampiezza e cis | Il migliore numerico non prova il contributo isolato del cis |
| R-DATI/R-MODELLI/R-SWITCH | Buone domande, prerequisiti in parte ancora aperti | Collegare esperimenti ai dati che distinguono le ipotesi, non ripetere soltanto banchi sul pannello |
| R-V2 | Universo K562, cis/rete e banco reale sono passi concreti | F1 CD4/Orion, F3 C/T/J e F8 prova generale restano necessari |
| Nuovo stadio 104 | Modula l'ampiezza gene per gene usando un modello appreso | È adattamento di un trasferimento già disponibile, non prova di previsione di bersagli completamente ignoti |

Ricetta t20: stessi pesi e ampiezza nei tre contesti. L'emissione usa controlli
diversi, ma non c'è una funzione appresa del contesto nel trasferimento t20.
Lo stadio 104 introduce descrittori basali: è una differenza tecnica reale,
il cui valore deve ancora essere confermato dal banco indipendente.

## 4. Revisione tecnica del banco appreso

**Esito: richiede correzioni prima di dichiarare generalizzazione rigorosa.**
La revisione r1 aveva identificato leakage. r2/r3 correggono esclusione dei
partner del pannello, SE della miscela CD4 sotto indipendenza e coorte della
precisione; resta un problema nella costruzione delle quantità aggregate.

### 4.1 Medie prima degli split

In `lct_bench3.py` tutti i task sono costruiti prima del ciclo per famiglia/fold.
`lct_bench2.build` sceglie le sorgenti escludendo solo la famiglia della propria
etichetta. `mix(..., gamma=1)` e `tab.common()` centrano sui bersagli dell'intera
tabella. Il modello poi esclude le righe del fold k, ma non ricalcola tali medie.

Esempio: per test K562, il task di training CD4 può usare la tabella K562; la sua
media comprende anche le risposte K562 dei bersagli di test. La loro influenza
rimane nelle feature delle righe di training ammesse. Inoltre `yc = y -
nanmean(y)` è calcolato prima di separare i fold. Anche quel centro conserva
risposte dei bersagli esclusi nelle altre sorgenti.

**Misurato con controesempio sintetico usando il vero `mix`:** spostare soltanto
una riga test da 2 a 12 cambia la feature della riga training da −0,5 a −5,5;
con centro calcolato solo sul training rimane 0. [Script](audit.py) e risultati
in r1. Non è una stima del bias sullo score reale, né dimostra che il vantaggio
del nuovo braccio sparirebbe.

### 4.2 Quale generalizzazione sta misurando

Le feature di test usano le risposte dello **stesso bersaglio** nelle sorgenti
disponibili: legittimo per trasferimento C o completamento di coppie, non J.
Lo split dei bersagli del regressore non rende il bersaglio biologicamente mai
osservato. Per C/J rigoroso, inoltre, l'esclusione della famiglia deve valere
anche per input dei task di training e prior derivati. L'universo/cis K562
contiene risposte di altri bersagli della linea K562: quando K562 è test, la
linea non è completamente nuova secondo D-044.

**Proposta di correzione:** ricostruire task e trasformazioni dentro ciascun fold
esterno, escludendo tutta la famiglia esterna da etichette, sorgenti e prior;
per T/J escludere anche i bersagli test da tutte le risposte e dai derivati.
Stimare centri e selezioni sui soli gruppi di training. Aggiungere una prova di
invarianza: alterare gli esiti vietati non deve cambiare training o predizioni.
Conservare anche il regime misto, chiamandolo con il suo nome.

### 4.3 Limiti della selezione e dell'emissione

- `HistGradientBoostingRegressor` usa validazione casuale di coppie
  bersaglio–gene per early stopping. Non è il test esterno, ma non equivale a
  validation per bersaglio/studio: raggrupparla per il regime dichiarato.
- I molti bracci/proxy sono scelti dopo ripetute osservazioni delle stesse
  famiglie. Il bootstrap sui bersagli è condizionato ai modelli; non comprende
  incertezza tra studi, training e selezione di iperparametri.
- Il reweighting moltiplica per una quantità non negativa: conserva i segni
  degli effetti non azzerati. Può scegliere meglio quali geni chiamare, ma non
  corregge direttamente un segno trasferito sbagliato.
- Uguagliare la mediana dei geni rilevabili non uguaglia energia, coda delle
  ampiezze, chiamate per bersaglio o le sei metriche. r3 K562 a esponente 0,25
  passa da 1,0823 a 1,1336 nel rapporto MSE proxy mentre migliora il PDS.
- `mse_ratio_best_scale` usa la verità valutata per scegliere la scala:
  diagnostica oracolare, non prestazione di calibrazione fuori campione.
- r4 applica un modello del generatore, non genera/valuta le cellule con tutti
  i membri ufficiali. A esponente 0,25 riporta ΔPDS proxy circa +0,0076…+0,0102,
  con intervalli positivi nei quattro task: segnale esplorativo da conservare,
  non conferma indipendente dopo r3 e non score ufficiale.

La preparazione locale del banco HepG2 non dimostra che il job sia finito.
Non è stato verificato uno stato remoto vivo in questo audit.

## 5. Lettura biologica dei pattern

Le misure di riferimento restano quelle di [CP-0040](../../docs/checkpoints/0040-biologia-contesti-donatori.md)
e del [report riproducibile](../biologia_architetture_2026-09-25/RISULTATI.md),
senza nuovo fitting in questa sessione.

1. **Stato × intervento, non semplice somiglianza globale.** STAT2 si trasferisce
   sotto IFNB (Pearson 0,53–0,71) molto meno sotto IFNG (circa −0,04…0,05), su
   supporto appaiato. È compatibile con programmi dipendenti dallo stimolo;
   non prova soglie, e riduzione dell'RNA non misura attività proteica.
2. **Il segno della relazione conta.** USP18 ha risposta anticorrelata a STAT2
   sotto IFNB (mediana −0,484), mentre altri componenti hanno segno concorde.
   Una media indiscriminata dei partner STRING può cancellare struttura utile.
   Rete con segno/ruolo è un'ipotesi da provare contro vicini non orientati.
3. **Affidabilità nella sorgente ≠ trasferibilità.** CD4 halfA/halfB, gruppi di
   donatori diversi: Pearson mediana 0,0844; tra coppie con |z|≥2 in entrambi,
   34,93% di segni opposti. Numerosità, batch, guide e donatore sono alternative
   confondenti. Serve varianza gerarchica e validazione a donatore escluso;
   le tre condizioni non diventano tre sorgenti indipendenti.
4. **Effetti circoscritti.** Il divario TNF di MCF7 è concentrato in FADD/TRAF3/TRAF2.
   Non giustifica scartare l'intera linea. Verificare guide, efficacia, selezione
   dei sopravvissuti e composizione prima di chiamarlo inversione causale.
5. **Dose e composizione non si ricavano da una media.** Jost/microglia/PerturbFate
   hanno ruoli diversi per dose, quota rispondente e tempo. L'efficacia misurata
   dopo la perturbazione non è un input disponibile nei controlli della gara.
6. **Fallimenti delimitati.** Proiezione lineare e pesi di somiglianza basale
   negativi non respingono programmi con segno, interazioni bersaglio-specifiche
   o contesto in generale. DepMap basale non misura lo stato stimolato Mixscale.

### Correzione Mixscale

Il report H6 del 26 e la sua riga del registro chiamano Mixscale knockout e
oppongono pannelli di vie a trascrittoma intero. Il
[record GEO GSE281048](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE281048)
specifica **CRISPRi dCas9-KRAB-MeCP2**. Il pannello mirato è quello degli
interventi; non va confuso con il supporto dei geni di risposta. La correzione
non cambia i numeri H6, cambia l'interpretazione e il trasferimento dei limiti.

## 6. Ordine operativo proposto per Claude

1. Sistemare isolamento e trasformazioni del banco; congelare un vero test
   esterno e distinguere C/T/J dal completamento di coppie.
2. Valutare con scorer reale effetti e generatore insieme; per nuovi bracci
   riportare tutti i membri, supporto e ampiezza per bersaglio.
3. Completare gli universi CD4/Orion già prioritari; in parallelo pianificare
   VIPerturb-seq e HIPSCI con manifest, costo e test specifico. KOLF resta
   utile, con popolazione non selezionata per risposta forte.
4. Trasformare i dati già acquisiti ma parzialmente sfruttati (Jurkat, DLD-1,
   Mixscale; vecchi RPE1/HepG2) in test con maschere e ruoli espliciti.
5. Affidabilità per donatore/guida/studio e calibrazione della magnitudine
   precedono un aumento della capacità del modello. Una buona predizione dei
   geni che rispondono in media non sostituisce la specificità del bersaglio.
6. Prova generale per 300 bersagli nuovi: distinguere osservati pubblicamente
   da mai osservati; misurare copertura, latenza e fallback dell'intera pipeline.

Queste sono proposte, non nuove assegnazioni né adozioni. L'audit è ripetibile
con `scripts/py.cmd -B reports/audit_piani_dati_2026-09-26/audit.py --out` seguito
da una directory nuova. Nessuna ragione per rilanciare ricerche identiche finché
le sorgenti già trovate non hanno stato, uso e blocco verificabili.
