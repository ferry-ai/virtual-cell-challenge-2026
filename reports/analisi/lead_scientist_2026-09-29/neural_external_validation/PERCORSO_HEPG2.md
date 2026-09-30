# Banco cellulare della rete su un contesto esterno

29 settembre 2026. **Proposta**, condizionata al gate completo dei cinque fold.
Nessun training, scoring cellulare o lettura dei risultati della conferma del
generatore è stato eseguito per questo documento.

## Copertura realmente disponibile

**Misurato da soli metadati** in `metadata_r2.json`, riproducibile con
`audit_overlap.py`: il file HepG2 ha 145.473 cellule, 2.393 bersagli perturbati,
4.976 controlli e 9.624 geni unici. **Zero dei 300 bersagli della gara** è perturbato
qui. 254 sono presenti come geni di risposta: è una proprietà diversa.
L'intersezione dei geni di risposta è 9.023 con l'asse ufficiale e 8.768 con i
13.248 geni modellati r2. Non significa che tutti questi geni superino gene_keep
o siano utilizzabili per qualsiasi target.

Ci sono 961 bersagli sull'asse ufficiale con almeno 50 cellule, tutti registrati
nel pool r2. Mediana 74 cellule (quartili 59 e 98, minimo 50, massimo 1213). Gli outcome
HepG2 non sono nel pool; manca anche il suo basale. La copertura diretta varia:
959/961 in K562 genome-wide, 643/670/670 nei tre stati CD4, 758 in HCT116 e 802 in
HEK293T. RPE1 li comprende tutti; questi profili sono input leciti in C, ma
richiedono di dichiarare che il bersaglio è già visto in una diversa linea.

**Secondo limite concreto:** la cache t25 r9 contiene solo i bersagli della gara
(K562 272, CD4mix 293, HCT116 268, HEK293T 281), quindi **nessuna riga** dei target
HepG2. L'adattatore t25 attuale non può validare qui i suoi file salvati aggiungendo
semplicemente un nome di contesto. Una prova pubblica riguarda un'estensione della
stessa ricetta a bersagli diversi; non valida direttamente quei 300 effetti.

## Percorso minimo corretto

1. Congelare la selezione del modello e le due pipeline prima di leggere outcome
   di questi nuovi target. Campionare 96 target dai **683 eleggibili fuori
   dall'intero vecchio banco di 300**, così da evitare sia sviluppo, conferma e
   Stack pilot di oggi sia l'adattamento a quelle perturbazioni. La selezione usa
   solo nomi, conteggi di cellule e copertura delle sorgenti, con seed fissato e
   manifest prima di qualsiasi score. Non scegliere in base a n_conf o al delta
   già visto del generatore. Questo è ancora un nuovo campione nello stesso studio
   HepG2, non una replica indipendente dello studio.
2. Stimare il basale da soli controlli HepG2, come somma dei conteggi divisa per
   massa totale (non media dei CPM per cellula). Allinearlo ai 18.533 geni del pool,
   mantenendo NaN dove il file non misura. Aggiungere **solo una riga basale in
   memoria**: nessuna nuova riga di contesto/outcome, nessun riaddestramento,
   centro o prior ricalcolato. Usare identici closure, log1p/8 e ranghi di
   SourceView. Il suo riferimento cieco, gene_keep e standardizzazione dei prior
   restano quelli delle sorgenti visibili. `batch` già accetta un indice basale
   esterno e famiglia−1; basta un wrapper di inferenza, non cambiare il training.
3. Estendere la ricetta t25 ai 96 target dalle **tabelle sorgente float32** degli
   universi stage98, mantenendo gamma 1, reliability 100, quattro sorgenti e ampiezza 1,576.
   Conservare come centri i vettori r9 calcolati sul pannello originale; non
   ricentrarli sul nuovo campione. La miscela CD4 deve mantenere i suoi tre stati
   e il centro condiviso cd4_mix. I metadati r9 CD4/Orion hanno `min_expected=1`,
   coerente col suffisso me1; ciò non prova da solo identità numerica. Prima della
   prova, ricostruire righe del pannello già in r9 e verificare valori, n_cells e
   maschere. Se non coincidono, ricostruire dalle stesse sorgenti e parametri;
   non usare in silenzio i memmap r2 float16 come se fossero la cache r9.
4. Applicare i modificatori della rete con il medesimo operatore relativo già
   testato: `base + 0,5×1,576×(m1−m0)`, solo sulle coppie osservate fuori own/cis5kb.
   I fattori di fallback restano unitari. La baseline include lo stesso trattamento
   cis della ricetta (scala 2 dopo ampiezza). Rete neutra deve riprodurre la baseline
   estesa bit per bit; la prova di parità deve includere righe realmente ricostruite,
   anche se non usa i loro outcome HepG2. Non eguagliare la norma a posteriori.
5. Generare e confrontare le due pipeline con identico generatore congelato,
   400 cellule/target e tre semi appaiati. Non mescolare questa differenza con
   nuove scelte di ampiezza/dispersione. Per isolare la direzione, il generatore
   semplice stage45 Poisson può essere fissato a priori; l'eventuale generatore
   scelto oggi richiederebbe entrambi i bracci sulla medesima configurazione,
   dichiarando la dipendenza dalla selezione separata. Usare scorer vero, truth
   completa e controlli fissati; tutte sei metriche grezze. Una primaria e le sue
   soglie devono essere preregistrate prima del job, non importate dal PDS neurale.

L'asse cellulare può restare quello HepG2 intero: 9.624 geni. Il trasferimento usa
le misure sorgente realmente disponibili sui 9.023 geni ufficiali; i 601 geni fuori
asse mantengono il basale. Missing di una fonte e previsione nulla restano distinti.
La normalizzazione composizionale e il clipping devono essere quelli stage45.

## Fattibilità e alternative dichiarate

Non occorre incorporare gli 850 MB HepG2 nel dataset neurale da 8,7 GB. Il file resta
separato; prima dell'inferenza si leggono solo controlli, in blocchi. Basale full-axis
float64: circa 145 KiB. Un blocco 256×9624 float32: circa 9,4 MiB. I 96×400 conteggi
generati sono circa 1,38 GiB se densi float32 prima dei temporanei; usare una pipeline
che conserva un solo braccio e legge le righe di verità richieste. Il costo del
SourceView resta quello dell'inferenza r2 e va sul runner.

La via più corta, previsione net contro transfer nello spazio r2 e successiva
generazione, è fattibile ma è **un altro candidato**: non convalida l'adattatore
ancorato a t25. Se mancano tempo o sorgenti per la ricostruzione controllata,
registrare questo limite, senza tradurre i cinque fold in un guadagno t25.
La produzione ABC può essere preparata, ma il gate dei cinque fold autorizza una
prova del candidato completo, non una promozione automatica alla submission.

Il presente documento descrive il percorso e i controlli necessari; il wrapper
basale esterno e l'estensione delle tabelle non sono stati implementati.
