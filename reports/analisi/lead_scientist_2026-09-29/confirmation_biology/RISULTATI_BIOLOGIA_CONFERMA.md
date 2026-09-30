# Diagnostica biologica della conferma: beneficio eterogeneo, trasferibilità limitata

29 settembre 2026. **Analisi POST HOC, descrittiva.** Si legge soltanto la conferma
completa di ampiezza 1,5 / dispersione 1 contro il riferimento 1 / 0: 96 bersagli
HepG2, tre semi. Non si selezionano altri candidati, bersagli o criteri. Tutti i
numeri sono locali e non sono punteggi VCC. La decisione preregistrata resta quella
di `../RISULTATI_GENERATORE_CONFERMA.md`.

**Misurato:** il beneficio si concentra nelle risposte con molti geni DE, ma non
deriva soltanto da più chiamate. La fedeltà migliora per circa il 62% attraverso
la precisione direzionale e per il 38% attraverso la copertura del budget DE.
Esistono fallimenti ripetuti anche per perturbazioni con risposte ampie. Le
annotazioni non identificano un programma funzionale che giustifichi una regola
di amplificazione diversa. Il campione è molto diverso dal pannello di gara per
alcune categorie funzionali.

## Evidenza e unità di analisi

I risultati riproducibili sono `r1/analysis.json`, `r1/per_target.csv`,
`r1/annotations_by_target.csv`, `r1/annotation_evidence.csv` e
`supplement_r1/supplement.json`. I relativi script sono `analyze_biology.py` e
`supplement_biology.py`. Ogni risultato registra data UTC, hash del codice e
degli input principali; i report originali sono identificati dal
`../generator_confirmation_r3/COPY_MANIFEST.json` e già verificati da
`../confirmation_analysis/results_r1/analysis.json`.

L'esito per bersaglio è il suo **contributo additivo alla proiezione congelata**:
media dei tre semi, cinque variazioni grezze con le pendenze delle ancore, divisione
per sei e denominatore eleggibile proprio di ciascun membro. I 96 contributi
sommano a **+0,02891771**. Per le correlazioni si moltiplica ogni contributo per 96,
senza cambiare i ranghi. Non è un punteggio ufficiale per bersaglio.

La proiezione lascia fuori il peggioramento MSE, pari a **+0,381556** grezzo.
I contributi positivi di FID e REACH compensano peggioramenti di NMAE e Jaccard;
il PDS medio è quasi invariato. Questa diagnostica non trasforma tale compromesso
in un miglioramento generale della qualità biologica.

La forza osservata della risposta è `expr_distance_unbiased` del comparatore:
distanza quadratica media fra medie perturbate e controllo, nello spazio
`bulk_lognorm5e4`, escluso il gene bersaglio, con correzione del rumore da
campionamento. **Sei stime su 96 sono negative**, cosa ammessa dalla correzione:
non si interpretano come intensità negative, né se ne prende la radice.
`source_expected_energy_all_genes` è invece una somma di quadrati dell'effetto
atteso del generatore, include il gene bersaglio e ha un altro denominatore.
Si confrontano ranghi; non si deriva un rapporto di ampiezza fra le due grandezze.

## Che cosa predice il beneficio osservato

| Caratteristica | Spearman con il contributo | Lettura descrittiva |
|---|---:|---|
| Budget DE reale `n_conf` | +0,396 | Le risposte più estese beneficiano mediamente di più |
| Forza osservata della risposta | +0,339 | Associazione positiva, non monotona nei quartili |
| Numero di cellule reali | +0,077 | Nessuna associazione evidente in questo campione |
| Energia attesa dalla sorgente | +0,008 | Non discrimina i bersagli che guadagnano |
| Precisione direzionale iniziale | +0,112 | Associazione debole |

Per `n_conf` e forza osservata i valori q BH esplorativi, su dieci correlazioni,
sono rispettivamente 0,000319 e 0,001825. **Non sono conferme di ipotesi biologiche**:
le analisi sono successive al risultato, condividono controlli e alcuni membri,
come PDS, dipendono dagli altri bersagli del pannello.

`n_conf` e forza osservata hanno fra loro **rho = 0,953**. Non è possibile attribuire
con sicurezza il beneficio all'una separatamente dall'altra: la correlazione
parziale della forza cambia segno quando si controllano `n_conf` e cellule, ma
questa regressione è fortemente collineare e non sostiene un'inversione biologica.
Anche l'associazione fra gain e FID iniziale, negativa, contiene l'accoppiamento
aritmetico del riferimento sottratto nel gain.

Il quarto dei bersagli con più DE, **24 bersagli con 1.599–5.193 geni**, contribuisce
**+0,014808**, il **51,2%** del guadagno netto; 23/24 hanno contributo positivo.
I quartili della forza osservata contribuiscono invece +0,004309, +0,002237,
+0,013268 e +0,009103: il quarto non supera il terzo. Non emerge una legge semplice
«amplificare sempre di più gli effetti più forti».

L'energia della sorgente correla con la forza osservata (**rho = 0,590**) e con
`n_conf` (**rho = 0,534**), pur non correlando con il vantaggio del candidato.
**Interpretazione:** una sorgente può segnalare l'intensità generale della risposta
senza indicare quale perturbazione sia aiutata da questa trasformazione di
ampiezza e dispersione. Non basta ordinare i bersagli per energia della sorgente
per ricavare una regola di scala adattiva.

## Precisione, copertura e REACH sono quantità diverse

Dal comparatore, FID grezza è `k / max(n_pred, n_conf)`, dove `k` conta gli accordi
direzionali delle chiamate previste. Con `P = k/n_pred` e
`C = n_pred/max(n_pred,n_conf)`, vale `FID = P*C`. Qui tutti i budget previsti sono
positivi. La scomposizione simmetrica esatta è:

`deltaFID = deltaP*(C1+C0)/2 + deltaC*(P1+P0)/2`.

La formula è stata ricostruita da conteggi indipendenti su **288 coppie** e
confrontata con tutti i sei CSV originali del comparatore: errore massimo
**1,12e-16**, residuo della scomposizione inferiore a **8,4e-17**.

| Quantità macro sui 96 bersagli | Misura |
|---|---:|
| FID riferimento | 0,472977 |
| FID candidato | 0,523541 |
| Aumento FID | +0,050564 |
| Componente precisione direzionale | +0,031442, ossia 62,18% |
| Componente copertura del budget | +0,019122, ossia 37,82% |

Tutta la componente copertura viene dai **44 bersagli con `n_conf >= 500`**.
In questo strato la precisione media passa da **0,553608 a 0,595476** e la copertura
troncata da **0,769068 a 0,838121**. Questi bersagli producono +0,021105 della
proiezione, **72,98%** del guadagno netto. Sotto 500 il numero di chiamate supera
già il budget reale in tutte le coppie; il miglioramento FID è quindi interamente
di precisione, non di copertura.

Questa è una **decomposizione contabile del cambiamento FID**, non una separazione
causale fra ampiezza e dispersione, né una decomposizione della proiezione intera.
La precisione direzionale non è la percentuale di chiamate che risultano anche
significative nella verità. La copertura del budget non è il richiamo dell'insieme
dei DE veri. **Il richiamo DE classico non è ricostruibile esattamente dai soli
report piccoli qui usati**; non lo si sostituisce con `k/n_conf`.

REACH usa la profondità massima del ranking dei geni adjudicabili e significativi
nel riferimento che mantiene una purezza direzionale almeno 0,9, divisa per
`n_conf`; non è il richiamo DE classico. È assente quando `n_conf=0`. Per piccoli
budget può cambiare molto in seguito a pochissimi accordi: nei bersagli con
`n_conf=1`, un cambiamento di una unità in uno dei tre semi muove la media di 1/3.
Questo limita la lettura biologica di alcune code negative.

## Annotazioni funzionali, con provenienza

Si usano esclusivamente gli snapshot HGNC, GOA umano e GO basic già presenti in
`C:/Users/ferra/vcc2026-data/interim/encoder_inputs_2026-09-14/`. I tre SHA256
coincidono con i manifest storici del progetto. L'ontologia e il GAF indicano la
release GO **2026-07-26**, GAF generato il 28 luglio. La versione non è stata scelta
in funzione di questi risultati.

La mappatura usa simboli HGNC approvati, alias univoci e accessioni UniProt
univoche. Tutti i 96 bersagli sono risolti e hanno almeno un'annotazione GO positiva;
cinque richiedono un alias: CENPJ→CPAP, EPRS→EPRS1, HARS→HARS1, RARS→RARS1,
VARS→VARS1. Si escludono le annotazioni `NOT`; si propagano soltanto relazioni
`is_a` e `part_of`, come consentito dalla semantica GO. Le righe di evidenza
conservano GO ID, nome del termine, qualificatore, codice di evidenza, riferimento,
data, ente assegnante e accessione. Le regole sono documentate dalle fonti
primarie [relazioni GO](https://geneontology.org/docs/ontology-relations/),
[annotazioni GO](https://www.geneontology.org/docs/go-annotations/) e
[formato GAF](https://www.geneontology.org/docs/go-annotation-file-gaf-format-2.2/).

I cinque insiemi sono fissati nel codice: ribosoma/biogenesi (GO:0005840,
GO:0042254), spliceosoma/splicing RNA (GO:0005681, GO:0008380), mitocondrio
(GO:0005739), ciclo cellulare (GO:0007049), trasporto vescicolare/intracellulare
(GO:0016192, GO:0006886). Sono categorie larghe, **sovrapposte**, e descrivono
associazioni annotate dei bersagli; non dimostrano l'attivazione del programma
nelle cellule HepG2 perturbate.

| Categoria | Bersagli | Positivi | Media dei contributi ×96 | Solo evidenza sperimentale |
|---|---:|---:|---:|---:|
| Ribosoma / biogenesi | 15 | 12 | +0,02936 | 10 bersagli |
| Spliceosoma / splicing | 7 | 6 | +0,05851 | 6 bersagli |
| Mitocondrio | 10 | 9 | +0,04023 | 8 bersagli |
| Ciclo cellulare | 15 | 13 | +0,03019 | 8 bersagli |
| Trasporto vescicolare / intracellulare | 7 | 6 | +0,03518 | 3 bersagli |

La media complessiva è +0,02892. Lo splicing appare sopra la media, ma ha soltanto
sette membri e non costituisce un risultato confermato. Regressioni esplorative
con errori HC3 e aggiustamento per `n_conf`, cellule e forza osservata non separano
nessuna categoria dopo BH sui cinque confronti (**tutti q >= 0,666**). I controlli
sono collineari e i gruppi piccoli: è assenza di evidenza di una differenza, non
equivalenza. Limitando le annotazioni ai codici sperimentali le medie restano
positive, ma i numeri scendono a 3–10; i dettagli e tutti i membri sono salvati.
Non si sommano i contributi di queste categorie, perché alcuni bersagli ricorrono
in più insiemi.

## Bias di campionamento e limiti di trasferibilità

Il confronto con gli altri **178 bersagli eleggibili** del banco non mostra uno
sbilanciamento evidente per questi cinque insiemi: tutti i q Fisher/BH sono 0,860.
Questo è compatibile con l'estrazione casuale dal banco e non dimostra equilibrio
per caratteristiche biologiche non analizzate.

Il confronto con i **300 bersagli challenge**, distinti dai bersagli HepG2, è diverso:

| Categoria | Conferma HepG2 | Challenge | Fisher/BH esplorativo |
|---|---:|---:|---:|
| Ribosoma / biogenesi | 15/96, 15,63% | 2/300, 0,67% | q = 1,06e-7 |
| Ciclo cellulare | 15/96, 15,63% | 8/300, 2,67% | q = 4,97e-5 |
| Spliceosoma / splicing | 7/96, 7,29% | 10/300, 3,33% | q = 0,238 |
| Mitocondrio | 10/96, 10,42% | 34/300, 11,33% | q = 1 |
| Trasporto | 7/96, 7,29% | 25/300, 8,33% | q = 1 |

Le differenze di ribosoma e ciclo cellulare restano visibili restringendo alle
annotazioni sperimentali: rispettivamente 10/96 contro 2/300 e 8/96 contro 7/300.
**Misurato:** il banco sovrarappresenta queste categorie rispetto al pannello.
**Non dimostrato:** che questa differenza annulli il beneficio del generatore o
permetta di predirne il valore ufficiale. Non si classifica come «non essenziale»
un bersaglio per assenza da un insieme, e assenza di annotazione non significa
assenza di funzione.

Il campione ha inoltre 50–430 cellule reali per bersaglio contro 400 previste.
La quasi assenza di correlazione lineare nei ranghi con il numero di cellule non
dimostra che potenza, profondità o qualità della verità siano irrilevanti.
I controlli sono comuni, la linea è una sola, i bersagli e la ricetta di sorgenti
non sono quelli della submission. Nessuna ripesatura biologica del risultato è
giustificata da questi cinque insiemi.

## Fallimenti importanti

73/96 bersagli hanno contributo medio positivo e 60 sono positivi in tutti i tre
semi. **Undici sono negativi in tutti e tre:** ADAM10, CFDP1, DHX37, NFRKB, OLFML3,
ORC5, PTPN1, RPS15, RRP7A, TAF10 e TAF3. I nomi identificano righe dei risultati;
non vengono usati per inferire funzioni.

| Bersaglio | `n_conf` | Cellule | Contributo ×1000 | Cambiamento principale |
|---|---:|---:|---:|---|
| BCAR1 | 1 | 346 | −0,571 | REACH −1/3 e PDS −0,0491; FID migliora; non negativo in tutti i semi |
| RPS15 | 2356 | 57 | −0,513 | FID −0,0828, NMAE +0,0721; REACH migliora |
| TAF3 | 311 | 68 | −0,482 | FID −0,0557, NMAE +0,0363 e Jaccard −0,0197 |
| OLFML3 | 4 | 76 | −0,472 | REACH −0,1667; quantità sensibile a poche chiamate |
| TAF10 | 916 | 50 | −0,345 | FID −0,0414, Jaccard −0,0203 |
| ADAM10 | 678 | 161 | −0,298 | NMAE +0,0658 e FID −0,0262 |
| RRP7A | 1404 | 68 | −0,159 | NMAE +0,0238 e Jaccard −0,0220, nonostante FID migliori |

NMAE più alto è peggiore. RPS15, annotato al ribosoma anche con evidenza
sperimentale, è un controesempio concreto a una protezione basata sul programma:
ha risposta osservata forte e molti DE, ma peggiora in tutti i semi. RRP7A fornisce
un altro fallimento nello stesso insieme, con un compromesso fra membri diverso.
I casi a basso `n_conf` richiedono cautela metrica; quelli con centinaia o migliaia
di DE impediscono di attribuire tutte le perdite alla bassa potenza.

## Implicazione modellistica, da provare separatamente

**Interpretazione:** il generatore attuale migliora soprattutto il rapporto fra
chiamate corrette e budget, mentre l'intensità dell'effetto e alcuni insiemi DE
restano calibrati male. L'aumento congiunto di ampiezza e dispersione non equivale
a correggere la direzione biologica di ogni perturbazione.

**Proposta falsificabile futura:** apprendere, su contesti di sviluppo separati,
una calibrazione con due uscite: intensità e affidabilità della risposta trasferita.
Usare soltanto informazioni disponibili prima dell'outcome di destinazione
(concordanza fra sorgenti, incertezza degli effetti sorgente, profilo basale del
contesto). Confrontare scala globale, scala da energia sola e calibrazione appresa
a generatore fissato, su contesti e bersagli lasciati fuori, misurando separatamente
FID precisione/copertura, NMAE, MSE e Jaccard. L'energia da sola è un controllo
necessario perché qui non predice il gain. I programmi GO servono a diagnosticare
il trasferimento, non sono giustificati come regola di scala da questi risultati.

Non usare `n_conf` o forza osservata HepG2 come ingressi del modello, non cambiare
scala su RPS15 o altri casi visti qui e non selezionare una nuova ricetta sui 96
bersagli. Questa analisi consuma la loro funzione diagnostica; non crea un altro
insieme di conferma indipendente.

## Riproduzione e verifiche

Da repository, con nuove directory di output:

```powershell
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/confirmation_biology/analyze_biology.py --data-root C:/Users/ferra/vcc2026-data --out NUOVA_DIRECTORY
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/confirmation_biology/supplement_biology.py --out ALTRA_NUOVA_DIRECTORY
.\scripts\py.cmd -m unittest discover -s reports/analisi/lead_scientist_2026-09-29/confirmation_biology -p test_biology.py -v
```

Il supplemento usa intenzionalmente le tabelle congelate `r1/` per documentare
questa esatta lettura. Nessun caricamento di matrici cellulari, predizioni complete
o nuovo scorer è necessario. I test piccoli verificano propagazione GO senza
`regulates` o termini obsoleti, esclusione `NOT` e organismi diversi, alias e
provenienza sperimentale, attraversamento del limite di copertura, budget reale
nullo, additività e simmetria della decomposizione. L'esito dei test è registrato
separatamente in `VERIFICA.txt`.
