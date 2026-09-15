# Documento in esame — prospetto interno di un progetto, datato 2026-09-14.
# Estratto preparato per questo incarico: sono stati rimossi i collegamenti a percorsi
# interni e l identificativo della sottomissione. Nessun altra parola e stata cambiata.

# Prospetto del prossimo modello

Data: 2026-09-14. Stato: **proposta di ricerca**, non architettura validata o adottata.
Obiettivo concordato: valutare una decomposizione in sottoproblemi addestrabili e
definire come verificarne il vantaggio rispetto a un modello unico.

## 1. Punto di partenza verificato

Il trial inviato era **ShrunkTransfer**, non una rete neurale. Il codice in
models.py trasferisce la firma di ciascun bersaglio
misurata in K562, con shrinkage per gene e ampiezza globale:

`delta_pred = alpha * prior_sd² / (prior_sd² + SE²) * delta_K562`.

La configurazione in trials.yaml usa alpha calibrato
su K562 → RPE1, poi applicato invariato ad A/B/C. Il basale del contesto entra nella
conversione in conteggi in inference.py, ma la regola
che predice il delta non impara una dipendenza dal contesto. Dove manca supporto
si usa un fallback nullo, registrando la maschera: assenza di dati non significa
assenza biologica di effetto.

Il JSON del server
registra alpha 0,1974, prior_sd 4 e questi risultati:

| Metrica scalata | Valore | Lettura prudente |
|---|---:|---|
| Complessivo | 0,045929 | Modesto guadagno sulla baseline ufficiale |
| PDS | 0,413315 | Segnale discriminativo tra perturbazioni |
| MSE | 0 | Pavimento del punteggio; non errore nullo |
| NMAE | 0,026833 | Piccolo guadagno |
| FID | −0,182476 | Peggiore della baseline ufficiale |
| Reach | 0,021322 | Piccolo guadagno |
| Jaccard | −0,003417 | Poco sotto la baseline ufficiale |

**Interpretazione:** preservare la specificità del bersaglio è utile; trasferire la
stessa risposta fra contesti lascia molto irrisolto. Questi aggregati non identificano
la causa della FID negativa, né dimostrano che tutta la direzione biologica sia errata.
La baseline ufficiale è la risposta media del contesto, non il ricampionamento NTC.
Le formulazioni più forti nel CP-0006 su nullo, causalità dell'ampiezza e invarianza
della PDS non vengono assunte qui: l'invarianza sul delta trasformato non equivale
all'invarianza dopo generazione e normalizzazione dei conteggi.

Il percorso di consegna funziona. Il generatore da profilo medio ha invece un rischio
distinto, documentato nel codice: alterare sparsità e variabilità anche con delta zero.
**Ipotesi da testare:** parte dell'errore di scoring deriva da questa conversione.
Esperimento diagnostico: tenere fissi i delta e cambiare solo il generatore; poi
tenere fisso il generatore e cambiare solo il predittore.

## 2. Evidenze esterne e implicazioni

Ricognizione mirata, non revisione sistematica. Consultazione il 14 settembre 2026.
I risultati pubblicati nei loro benchmark non dimostrano prestazioni su VCC 2026.

| Fonte primaria e accesso | Evidenza utilizzata | Implicazione proposta |
|---|---|---|
| [GEARS](https://www.nature.com/articles/s41587-023-01905-6), estratti indicizzati; [repository ufficiale](https://github.com/snap-stanford/GEARS) individuato | Usa conoscenza fra geni per predire anche perturbazioni non viste; la connettività del grafo può limitarlo | Confrontare descrittori biologici del bersaglio con semplici identità; non equiparare bersaglio nuovo a contesto nuovo |
| [CPA](https://pmc.ncbi.nlm.nih.gov/articles/PMC10258562/), estratti indicizzati; apertura bloccata da controllo browser | Separa rappresentazioni di stato basale, perturbazione e covariate | La composizione latente è un precedente; non prova che la separazione sia identificabile nei nostri dati |
| [Benchmark lineare](https://www.nature.com/articles/s41592-025-02772-6.pdf), estratto indicizzato; testo completo non recuperato | Riporta che i metodi deep confrontati non superano semplici baseline lineari nei compiti studiati | Baseline lineare obbligatoria; nessuna conclusione universale contro le reti |
| [State, repository ufficiale](https://github.com/ArcInstitute/state), README letto | Distingue embedding e transizione; fornisce esempi e split che escludono interi tipi cellulari | Candidato di confronto già disponibile, da verificare per dati, pesi e compatibilità prima dell'uso |
| [Replogle et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC9380471/), pagina completa accessibile, lettura mirata | Perturb-seq su scala genomica collega perturbazioni a fenotipi trascrizionali | Fonte sperimentale per cercare struttura condivisa delle risposte; non assumere moduli indipendenti o invarianti fra lignaggi |

**Vincolo biologico e statistico:** controlli abbondanti descrivono lo stato cellulare,
ma non identificano da soli la risposta causale al knockdown. Servono perturbazioni
in più contesti, possibilmente con bersagli condivisi, per apprendere come la risposta
dipenda dal contesto. Milioni di cellule in un solo contesto non sostituiscono questa
diversità. Efficienza del knockdown, donatore, batch e stato vanno conservati come
metadati; quando non sono separabili, l'incertezza resta esplicita.

## 3. Architettura candidata: base condivisa e piccoli moduli

**Proposta:** predire una risposta rispetto al basale attraverso programmi condivisi
e un piccolo adattamento dipendente dal contesto. Nessuna suddivisione rigida dei geni.

| Blocco | Input → output | Addestramento e verifica |
|---|---|---|
| Encoder del contesto | Insieme di NTC → descrittore `z_c` | Prima statistiche/PCA; autoencoder solo come confronto. Verificare utilità sulla risposta fuori contesto, oltre alla ricostruzione |
| Encoder del bersaglio | Descrittori disponibili del gene → `e_t` | Annotazioni/embedding con provenienza; gestire geni mai perturbati e descrittori mancanti. Confronto con identità e descrittori semplici |
| Base dei programmi | Firme perturbative di training → matrice `B` | Fattorizzazione di risposte firmate con maschere, poi eventuale decoder non lineare; scegliere rango nei fold interni |
| Predittore dei programmi | `z_c, e_t` → coefficienti `a` | Ridge o piccola MLP condivisa; opzionali pochi esperti con pesi continui condizionati al contesto |
| Calibrazione | Risposta e supporto → ampiezza e incertezza | Su predizioni fuori fold; limitare flessibilità quando i contesti sono pochi |
| Generatore | NTC del contesto + risposta → distribuzione di conteggi | Calibrazione su controlli e perturbazioni esterne; test separati di media, varianza, geni rilevati e DE spurio |

Ricomposizione iniziale: `delta(c,t) = B * a(z_c,e_t)`.
Estensione da guadagnare sperimentalmente:
`delta(c,t) = B * a_shared(z_c,e_t) + B * sum_k w_k(z_c,e_t) * a_k(z_c,e_t)`.
I pesi degli esperti sono non negativi e normalizzati; i coefficienti dei programmi
possono essere positivi o negativi. Il ramo condiviso permette comunicazione globale.
I programmi possono sovrapporsi sugli stessi geni. Sono fattori predittivi, non
automaticamente pathway causali identificati.

Si parte addestrando e congelando rappresentazioni e base, poi il predittore piccolo,
poi la calibrazione. Un breve affinamento congiunto è un confronto successivo: blocchi
ottimi isolatamente possono comporsi male. Tutti i blocchi appresi dalle risposte sono
rifatti dentro il training fold. Le etichette A/B/C non sostituiscono i descrittori:
il modello deve funzionare su contesti nuovi.

**Perché potrebbe convenire:** riutilizzo della base, meno parametri da aggiornare,
esperimenti locali più economici, errori attribuibili a componenti. **Perché potrebbe
fallire:** programmi troncati, interazioni perse, errori propagati fra blocchi, gating
inaffidabile fuori distribuzione, troppe poche condizioni per specializzare esperti.
Un residuo più grande non è una soluzione gratuita: può annullare il risparmio.

## 4. Autoencoder, bagging e boosting: ruoli diversi

Un autoencoder comprime e ricostruisce: non impara una perturbazione dai soli NTC.
Una PCA costituisce il confronto minimo. Misurare anche la ricostruzione delle
risposte deboli e la qualità predittiva; spiegare varianza basale non basta.

Il bagging combina stime dello stesso problema. Se sperimentato, ricampionare
bersagli e unità biologiche appropriate, non solo cellule pseudoreplicate. Potrebbe
ridurre varianza, ma non corregge automaticamente un errore condiviso di trasferimento.

Il boosting corregge residui in sequenza. È un'opzione per i coefficienti dei
programmi; residui rumorosi possono produrre overfitting. Confrontarlo con ridge e
MLP senza trasformarlo in requisito architetturale.

Un ensemble fra sorgenti richiede pesi stimati fuori fold e diversità degli errori.
Cinque reti simili non costituiscono cinque fonti biologiche indipendenti. Gli esperti
specializzati, l'ensemble e la decomposizione funzionale rispondono a domande diverse.

## 5. Dati necessari e ordine di acquisizione

Stato locale da registry e roadmap, fotografie
del 12–13 settembre; disponibilità e dimensioni remote da ricontrollare prima del download.

| Dati | Uso | Limite e azione |
|---|---|---|
| K562/RPE1 pseudobulk locali | Baseline, base di risposta, primo confronto lineare | Copertura incompleta; maschere nelle loss e nella fattorizzazione. Il LowRankRidge esistente riempie i mancanti a zero prima della SVD: non riusarlo indiscriminatamente fra pannelli differenti |
| NTC A/B/C locali | Descrittori e controllo generatore | Nessuna etichetta perturbativa; non validano la risposta causale |
| HepG2 o RPE1 a singola cellula candidati | Scorer e confronto fra generatori | R-1 propone circa 0,85/1,24 GB compressi; non acquisiti in questo lavoro. Nessuna copertura dei 300 target secondo l'audit: banco metodologico, non benchmark del pannello |
| CD4 candidato | Segnale di lignaggio e copertura bersagli | Audit locale: 293 osservati, 239 con almeno 30 cellule. Separare donatore/condizione; chiarire guide escluse e costo estrazione prima di scalare |
| Altri contesti perturbati e descrittori biologici | Apprendere trasferimento e target nuovi | Selezionare per sovrapposizione sperimentale, metadati, licenza e misurabilità; i candidati non sono dati già utilizzabili |

La prima raccolta deve costruire una matrice **contesto × bersaglio × numero di
cellule/repliche**, con disponibilità dei controlli e geni misurati. Da questa si
decide quanti moduli sono identificabili. Il prospetto non richiede scaricare atlanti
interi né addestrare oggi una rete grande.

## 6. Esperimento che decide se divide et impera conviene

Confronti incrementali, stessi dati e generatore:

1. Trasferimento attuale e baseline lineare a basso rango, con maschere corrette.
2. MLP unica compatta con gli stessi descrittori in input.
3. Base condivisa + predittore dei programmi.
4. Come 3, aggiungendo pochi esperti; confronto anche con gruppi casuali, se si
   introducono gruppi biologici, per misurare il valore della conoscenza biologica.
5. Solo dopo: autoencoder al posto della PCA, bagging o boosting, un cambiamento alla volta.

Un confronto con State è utile se dati e risorse lo consentono. Separare il confronto
architetturale a dati uguali da quello con pesi preaddestrati che hanno visto altri dati.

Tenere fuori interi contesti; separare target già osservati altrove da target mai
osservati nel training. Il secondo test deve escludere quel target da tutte le
risposte di training. Guide dello stesso target restano insieme; controllare
duplicati fra dataset, donatori, selezione dei geni, fitting degli encoder e tuning.
L'uso dei soli NTC del contesto di test per condizionamento va dichiarato e replicato
in tutti i modelli: è coerente con l'input disponibile nel compito.

Misurare tutte le sei metriche con lo stesso backend e le stesse ancore. Se le ancore
ufficiali non sono disponibili per i dati esterni, riportare grezzi e normalizzazione
locale esplicitamente distinta dal punteggio di leaderboard. Registrare i target
esclusi dai gate e copertura; non selezionare solo risposte forti per vantare qualità.
Bootstrap per bersaglio entro contesto, risultati per contesto e variabilità fra seed;
pochi contesti non consentono intervalli credibili su ogni futuro lignaggio.

Confrontare sia a budget di tempo uguale sia, dove possibile, a numero di parametri
simile. Registrare picco RAM/VRAM, tempo di preprocessing, training di **tutti** i
blocchi, tuning, inferenza e spazio degli artefatti. Moduli sequenziali riducono
potenzialmente il picco, ma non garantiscono minore costo totale.

**Criterio proposto prima dei run:** adottare modularità se migliora il punteggio
locale a budget uguale con differenza positiva supportata dal bootstrap, oppure se
resta entro un margine di non inferiorità prefissato dimezzando tempo o memoria.
Il margine va fissato dopo aver misurato la ripetibilità della baseline e prima del
confronto finale. Se manca stabilità, il risultato è inconcludente, non una vittoria.

Esempio di dimensionamento, non misura: una base float32 18.533 × 64 occupa 4.744.448
byte, circa 4,52 MiB. Ciò rende la base piccola, ma non stima il picco di training,
che include batch, gradienti, ottimizzatore e caricamento dati. Fare un pilot misurato
prima di promettere compatibilità con la macchina disponibile.

## 7. Proposta operativa e confine del risultato

Il primo candidato è **PCA/statistiche del basale + descrittori del bersaglio + base
di risposta condivisa + ridge/piccola MLP + calibrazione + generatore separato**.
Gli esperti sono un'estensione da confrontare, non un assunto. Il benchmark a singola
cellula resta lo strumento che permette di scegliere, dentro questo obiettivo di
progettazione.

Completato qui: ricostruzione del trial da codice e JSON, ricognizione di precedenti,
specifica dei blocchi, fabbisogno dati e protocollo di confronto. Non eseguiti:
download di nuove matrici, training dei candidati, misura del vantaggio modulare,
recupero delle precedenti chat. La superiorità sulla rete unica resta una domanda
sperimentale aperta. Questo documento non cambia da solo le decisioni attive.
