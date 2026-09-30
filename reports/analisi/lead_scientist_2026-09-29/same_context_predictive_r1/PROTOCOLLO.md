# Verifica predittiva mascherata di uno screening mirato già locale

29 settembre 2026. **Proposta congelata prima di nuove stime di espressione o fit.**
L'inventario è misurato; il test qui descritto non è ancora eseguito. Nessuna
associazione fra identità biologiche e contesti ufficiali viene pubblicata.

## Correzione della domanda

La precedente soglia di correlazione tra metà campione >0,1 era un criterio
operativo di quel pilot. Non misurava il miglioramento di una previsione rispetto
al prior. Usarla come esclusione universale di questa sorgente introduce un bias
metodologico. La bassa riproducibilità resta un limite reale, particolarmente
importante con poche cellule, geni scelti a priori e molte guide per cellula.

Domanda primaria: **una correzione stimata da altre guide riduce l'errore su
cellule, canali e guide riservati, rispetto al medesimo prior esterno?** È una
verifica entro uno studio multi-perturbato, con bersagli già visti. Non dimostra
generalizzazione a nuova linea, effetto causale di una singola perturbazione,
prestazione su tutti i geni ufficiali o vantaggio nello scorer VCC.

## Inventario e recuperabilità

Fonte numerica: `r2/inventory_summary.json`; manifest completo con percorsi,
guide e provenienza conservato fuori dalla repository nella cartella privata
`interim/same_context_recheck_2026-09-29_r2`. I raw restano immutati.

| Quantità | Misura |
|---|---:|
| File raw nei manifest di acquisizione | 144 |
| Dimensione raw totale | 3.753.694.370 byte |
| Canali | 16 |
| Feature di guida, identiche nei 16 canali | 83.401 |
| Simboli unici nella tabella della libreria | 18.465 |
| Gruppi dopo il parser storico dei nomi guida, esclusi controlli | 18.599 |
| Bersagli ufficiali rappresentati nella libreria | 299/300 |
| Geni di risposta validi nella tabella | 374 |
| Risposte nell'asse ufficiale | 358/18.533 |
| Cellule del precedente QC, tutti i canali | 367.695 |
| Non stimolate / stimolate | 27.496 / 340.199 |
| Derivati H5AD ancora presenti nel pilot | 0 |
| Piccoli report, codice e manifest conservati | 30 |

Le due cardinalità dei bersagli non sono sinonimi: il raggruppamento dei nomi
guida include denominazioni non riconciliate alla tabella della libreria. Non
promuovere 18.599 a numero di geni validati. Gli alias richiedono una tabella
esplicita prima del fit. Le cellule non stimolate sono il 7,48% del precedente
QC; il vecchio riassunto 8,5% non concorda con la somma dei 16 report.

Fra i 300 bersagli: uno senza guida, cinque con 3 guide, 235 con 4, uno con 5,
tre con 6, sette con 7, 48 con 8. Questi sono identificativi nella libreria,
non guide efficaci né misure indipendenti osservate. Il vecchio QC aveva mediana
12–13 guide/cellula e circa 20/233 cellule per bersaglio nei due stati.

R1 contava erroneamente una nota della tabella come 375º gene. R2 richiede un
Entrez numerico nelle tabelle supplementari; un test verifica sia la rimozione
della nota sia la conservazione dei simboli letterali negli assi ufficiali.
358 geni compatibili e tutte le altre misure principali restano invariati.
I grandi SHA di acquisizione sono conservati, **non ricalcolati nell'inventario**;
sono verificati ora solo dimensioni e SHA dei file piccoli. Prima dell'ingestione
il preflight deve ricontrollare tutti gli SHA completi.

## Codice da riusare e cambiamenti necessari

Il pilot e il regressore congiunto sono ancora presenti nella cartella privata;
non serve recuperarli dal tag. Il manifest conserva i loro SHA. Riutilizzare
parsing dei nomi guida, QC UMI/hash, soglie guida e aggregazione sparse; conservare
la provenienza delle funzioni estratte e una verifica di equivalenza sintetica.
Non eseguire i moduli storici importandoli: contengono lavoro al livello principale.

Il lettore storico carica tutte le triple MTX in pandas e forma matrici intere.
Il regressore forma anche DᵀD. Il nuovo adattamento usa lettura a blocchi,
matrici per canale e operatore Dᵀ(Dv), senza costruire la matrice normale.
Il centering e le covariate del modello vengono stimati soltanto dal training.
Le cellule con guida non-targeting possono contenere altre guide: non sono
controlli puri e non vanno trattate automaticamente come tali.

## Separazioni fissate prima del fit

Seed unico 20260929. Ordinamento mediante SHA256 del tipo di oggetto, del seed
e dell'identificativo; nessuna scelta sulla forza della risposta.

1. Ordinare i 16 canali e assegnare i primi 8 al training, 4 alla calibrazione,
   4 al test. Conservare i due stati separati. I canali non sono automaticamente
   repliche biologiche: condividono libreria e studio.
2. Tutti i 300 bersagli ufficiali appartengono al gruppo finale di test.
   Calibrazione: primi 512 bersagli non ufficiali, con almeno 4 guide e prior
   esterno misurato, secondo lo stesso ordinamento. Dichiarare se ne esistono meno.
3. Per ogni bersaglio di calibrazione/test, riservare le prime 2 guide; se il
   bersaglio ha esattamente 3 guide, riservarne 1 e conservarne 2 per il fit.
   Meno di 3 guide: correzione non stimabile, prior conservato.
4. Escludere dal training **ogni cellula con qualsiasi guida riservata**, anche
   se la guida appartiene a un altro bersaglio. Non riutilizzare la stessa RNA
   come training per un bersaglio e test per un altro.
5. La calibrazione usa solo i propri canali e guide; il test solo i propri.
   Escludere le cellule contenenti guide riservate all'altro gruppo e, per il
   bersaglio valutato, qualunque sua guida di fit. Se più guide riservate della
   stessa partizione coesistono, assegnare la cellula a una sola guida focale
   tramite hash del suo identificativo: nessuna duplicazione nella metrica primaria.
6. Fissare due metà dei 358 geni di risposta tramite hash. La scelta di ampiezza
   e regolarizzazione usa solo la prima metà nei bersagli di calibrazione; la
   primaria usa la seconda. Escludere sempre il gene bersaglio e il cis entro
   5 kb quando le coordinate locali sono disponibili; dichiarare la maschera.
   La metà usata per calibrare resta una diagnostica separata.

Non si propone uno split disgiunto di tutte le 83.401 guide: a MOI 13 quasi
tutte le cellule mescolerebbero i fold. Il numero effettivo di esclusioni viene
misurato nella fase di ingestione prima di decidere il fit, senza leggere outcome.
Il pilot precedente ha già usato l'intero studio: non chiamare questo test
completamente vergine o esterno; è una nuova verifica predittiva preregistrata
su un dataset scelto dopo diagnostiche precedenti.

## Baseline, modello e lettura

Il prior è una sorgente esterna già locale, sull'universo completo, con maschera
dei geni misurati. Il manifest del fit deve fissare file, SHA, unità e conversione
alla scala log1p(CP10K) del pilot: non è lecito interpretare una differenza di
logCPM come differenza logCP10K senza conversione. La preparazione resta fermata
al parser finché questo contratto numerico non è verificato e registrato.

Modello: regressione additiva regolarizzata delle risposte alle presenze dei
bersagli, con intercetta, covariate di qualità/carico e stato separato, prior
esterno come centro. Stime soltanto sui canali/cellule di training. Intercetta
e centering non possono assorbire medie delle cellule di test. Le guide
riservate non entrano nel nuisance. Le altre guide osservate in training possono
descrivere il background; registrare combinazioni mai viste e collinearità.

Per ogni bersaglio focale confrontare lo stesso background congelato con (a)
il suo prior, (b) prior + alpha × correzione stimata. Alpha in {0, 0,1, 0,25,
0,5, 1}; regolarizzazione in {1, 10, 100}, selezionati soltanto su calibrazione
e prima metà dei geni, con parità risolta verso alpha minore e penalità maggiore.
Includere nullo, nuisance senza effetto focale e prior senza correzione.

**Primaria:** differenza di errore quadratico medio sulle risposte osservate
delle cellule riservate, maschera identica e background identico nei confronti;
media prima per guida, poi per bersaglio, poi per stato con peso uguale.
Riportare anche rischio completo e residuale, con le stesse trasformazioni:
un nuisance che assorbe l'effetto non deve creare un vantaggio apparente.
Non ristimare ridge o pseudoeffetti sulle cellule finali per fabbricare la truth.
La differenza va riportata in unità assolute e relativa al rischio del prior.

I 300 bersagli restano nel prospetto: numero di guide/cellule per split, presenza
del prior, maschera, esclusioni, supporto misurato e risultato eventualmente
mancante. Assenza di osservazioni non è un effetto nullo. Fuori dai 358 geni non
esiste una misura di questo studio. Nessuna espansione automatica all'intero asse.

**Null:** 20 permutazioni fissate dal seed, entro canale, stato, numero guide
(bin 0–5/6–10/11–15/16+) e quintile di library size definito nel training.
Permutare le associazioni guida→bersaglio fra profili compatibili, conservando
matrice di co-presenza e covariate; dichiarare i gruppi con meno di 2 unità.
Non fare shuffle globale delle cellule. Se non è possibile conservare le
caratteristiche di esposizione, il null è una sensibilità imperfetta, dichiarata.

Intervalli da 2.000 bootstrap per bersaglio con guide annidate, non per cellula;
sensibilità leave-one-test-channel-out e supporto stratificato. Studio unico e
co-guide rendono gli intervalli condizionati al disegno, non replicazione biologica.
Segnale promettente: guadagno primario >0, limite inferiore 95% >0, superiore
al 95º percentile dei null, e nessuno stato con peggioramento dimostrato.
Questo autorizza una verifica più vicina al prodotto, **non una promozione VCC**.
Una produzione richiede una decisione successiva e una prova su cellule/metriche
compatibili, senza cambiare questa soglia dopo i risultati.

## Piano di memoria e lavoro locale

Misurato dagli header: il canale maggiore ha 53.890.492 triple di espressione.
I soli tre array int32/int32/float32 richiedono 646.685.904 byte, prima di pandas,
CSR e copie. Il percorso storico intero non è adatto al budget corrente.

Adattamento fattibile: chunk da 100.000 triple; primo passaggio per totali UMI,
QC e guide, secondo per sole cellule mantenute e 374 risposte. Un vettore
float64 su 6.794.880 barcode usa 54.359.040 byte; un indice int32 circa 27 MB.
Una matrice finale densa float32 per tutte le vecchie cellule e 374 geni sarebbe
550.071.720 byte su disco, da conservare per canale/memmap, non tutta in RAM.
Guide sparse e metadati aggiungono decine di MB, da misurare e registrare.
La regressione può lavorare su blocchi di 16 geni e scansioni dei canali.

Budget operativo proposto: RSS 700 MiB, almeno 2 GiB liberi prima dell'ingestione,
output incrementali per canale; nessuna copia dei 3,75 GB raw. Prima del fit
misurare il consumo reale del primo canale, conteggi e equivalenza del QC storico.
Se una guardia fallisce, preservare il parziale e registrare il limite; non
allargare silenziosamente memoria o materiale trasferito.

Un job remoto eventuale richiede allowlist concreta dei soli file pubblici
consumati, codice congelato e licenza primaria verificata. La disponibilità GEO
non viene qui trasformata in una licenza: `metadata_license_revalidated=false`.
Non è stato caricato alcun file di questa sorgente. Le autorizzazioni di sessione
già valide non vanno chieste nuovamente; prima si prepara il contratto effettivo.
