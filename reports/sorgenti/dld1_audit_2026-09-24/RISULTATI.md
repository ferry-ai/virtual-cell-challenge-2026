# Nuovi contesti: DLD-1, Mixscale e Jurkat

24 settembre 2026. **Misure esplorative e proposte**, senza adozione di sorgenti,
addestramento di reti, modifica delle ricette o invii VCC.

## 1. DLD-1: primo confronto completato

Evidenza: [misure](r1/measurements.json), [risultati per bersaglio](r1/per_target.csv),
[protocollo scritto prima dei risultati](PROTOCOLLO.md), [script](audit.py).
I quattro file già presenti nella cartella dati coincidono con dimensioni e SHA256
del manifest locale. Non è una verifica indipendente del loro download originario.

| Quantità | Misura |
|---|---:|
| Colonne della matrice Low1 | 6.451 |
| Geni di risposta nella matrice | 2.827 |
| Geni sull'asse ufficiale | 2.587 / 18.533 (14,0%) |
| Bersagli del pannello con almeno una colonna | 67 / 300 |
| Bersagli con colonna P1 e presenti in K562 r5 | 61 |
| Geni finiti comuni, esclusi i 300 bersagli | 2.259 |
| Pearson mediana DLD-1/K562 sullo stesso bersaglio | 0,01838 |
| Mediana del controllo a bersagli diversi, aggregato per bersaglio | 0,00102 |
| Accordo mediano sui 100 effetti K562 più grandi | 52% |
| Controllo a bersagli diversi sugli stessi 100 geni | 50% |

La sottrazione della risposta media di ogni sorgente porta Pearson a 0,01984:
non emerge un cambiamento ampio. I 61 bersagli sono eterogenei: il decile inferiore
di Pearson grezza è −0,0271, quello superiore 0,1003. Nessun intervallo di confidenza
o test di significatività è stato calcolato.

**Interpretazione:** c'è una specificità descrittiva modesta rispetto al bersaglio
sbagliato. Non è una prova di miglioramento ufficiale e non misura il tetto del
trasferimento. Soprattutto, la matrice DE è molto più ristretta del trascrittoma:
la facilità di lettura non significa compatibilità completa con la pipeline.

**Limiti:** il confronto usa solo Low1 e le colonne P1 esatte, senza aggregare
promotori o stimare l'indipendenza fra guide. Le etichette contengono anche P2,
P1P2, identificativi ENST e annotazioni W/D. L'ispezione completa per prefisso
esatto conferma comunque 67 bersagli, in
[dld1_complete_labels.json](source_inventory_r2/dld1_complete_labels.json).
Il campo `panel_targets_any_suffix` di r1 si riferisce soltanto ai suffissi
riconosciuti dal parser; la verifica completa è quella successiva.

Non si è convertita l'ampiezza: restano da verificare sul codice degli autori unità,
SE e semantica dei promotori. Il metodo pubblicato usa limma-voom con covariate,
quindi non va equiparato automaticamente al nostro rapporto fra pseudobulk.
[Fonte primaria](https://www.biorxiv.org/content/10.64898/2026.07.10.737863v1.full).

## 2. Mixscale: acquisizione e prova fra sei linee completate

Scaricato solo l'archivio DE, **324.112.587 byte**, nella cartella dati esterna;
MD5 uguale al checksum Zenodo `f077cba680a1affc599f5153d99b0e45`.
Non servono gli oggetti Seurat per questa prova.
[Deposito degli autori](https://zenodo.org/records/14518762).

Lettura locale: **271 file, 218 bersagli distinti**, cinque stimoli e sei linee
(A549, BXPC3, HAP1, HT29, K562, MCF7). Le colonne distinguono log2FC, coefficienti
beta e p-value: lo script usa soltanto i log2FC. Nove bersagli coincidono con il
pannello: ELK1, FOXO4, IFNAR2, IFNGR2, MED15, MTF1, SMARCA5, STAT6, ZNF22.
Sono conteggi dell'archivio, non della libreria originale dello studio.

Evidenza: [misure e inventario](mixscale_r1/measurements.json),
[risultati per bersaglio e linea](mixscale_r1/per_target_context.csv),
[mediane per linea e stimolo](mixscale_r1/by_context_stimulus.csv),
[protocollo](MIXSCALE_PROTOCOLLO.md), [script](analyze_mixscale.py).

Per ogni stimolo si tiene fuori una linea e si media l'effetto dello stesso
bersaglio nelle altre cinque. Il controllo ignora il bersaglio e usa gli altri
bersagli delle sole linee sorgenti. Sono **1.626 confronti**, con mediana di
3.729 geni utilizzabili; i mancanti non valgono zero.

| Mediana sui confronti | Stesso bersaglio | Controllo che ignora il bersaglio |
|---|---:|---:|
| Pearson | 0,02714 | 0,01551 |
| Coseno | 0,14535 | 0,10548 |
| Accordo del segno sui 100 geni scelti dalla previsione specifica | 61% | 58% |

Queste sono mediane separate, non differenze appaiate e non osservazioni indipendenti.
Lo stesso bersaglio può ricorrere in stimoli diversi. Le stime DE degli autori
potrebbero condividere selezioni o parametri fra linee: la prova è descrittiva,
non una validazione indipendente dell'intera procedura di addestramento.
Il vantaggio di specificità è limitato; il coseno più alto della correlazione
mostra quanto sia necessario controllare la componente comune.

L'inventario preliminare r2 aveva letto i file separati da spazi come una colonna:
le sue anteprime sono conservate, ma per schema e misure vale `mixscale_r1/`.
Il primo inventario si era interrotto per permessi della sandbox sulla cartella
dati; il secondo è stato eseguito con accesso autorizzato. Non era un blocco biologico.

## 3. Jurkat: riferimento corretto e limite confermato

La serie specifica è **GSE249595**, inclusa nella SuperSeries GSE247601.
L'esperimento distingue cellule stimolate e non stimolate; il disegno legge
374 geni tramite pannello mirato, pur perturbando 18.595 bersagli.
Fonti: [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE249595),
[articolo](https://www.nature.com/articles/s41556-025-01626-9).

**Proposta:** prima acquisire l'elenco delle caratteristiche e misurarne
l'intersezione con l'asse ufficiale; poi ricostruire assegnazioni e controlli per
canale e stato. Le cellule con più perturbazioni non possono essere trattate
come osservazioni isolate dello stesso bersaglio senza un modello appropriato.
Nessuna matrice Jurkat acquisita o misura di trasferimento Jurkat eseguita qui.

## 4. Come conservare e usare contesti anche lontani

**Proposta**, coerente con la richiesta del proprietario: conservare l'intero
archivio Mixscale, non soltanto i nove bersagli attuali. Non eliminare un contesto
perché diverso da A/B/C. Separare le sue possibili funzioni: effetti trasferibili,
addestramento su bersagli diversi, test fuori contesto, controlli tecnici.

Una futura tabella comune deve registrare sorgente/versione, linea, donatore,
stimolo, chimica, bersaglio, promotore, replicato, gene di risposta, stimatore,
unità, errore standard quando disponibile e maschera dei dati mancanti.
I beta Mixscale non sono i log2FC; i p-value non sono SE intercambiabili.

Per verificare l'ipotesi «15 contesti meglio di 2»:

1. Definire prima test e gruppi: tenere fuori intere linee, poi interi studi;
   aggiungere una prova con bersagli nuovi. Tenere insieme repliche e aliquote.
2. Confrontare sottoinsiemi annidati di contesti con la stessa copertura di
   bersagli e geni e budget comparabile. Ripetere la scelta delle sorgenti:
   un risultato favorevole con una sola coppia non basta.
3. Misurare sia sul supporto comune sia sulla copertura completa. La maschera
   non deve premiare chi misura meno geni.
4. Confrontare media non pesata, media che ignora il bersaglio e modello semplice
   prima della rete. Pesi, selezioni e normalizzazioni si stimano solo nel training.
5. Riportare risultati per linea, stimolo e studio, con incertezza per gruppi.
   Cinque stimoli della stessa linea non contano come cinque linee indipendenti.

## 5. Prossimi passi concreti ancora aperti

- **DLD-1:** chiarire suffissi, base del log e filtro dei 2.827 geni; confrontare
  Low1/Low2 solo dopo aver verificato la loro indipendenza; valutare accesso a
  conteggi più ampi prima di costruire un adattatore di produzione.
- **Mixscale:** verificare se stima DE e selezione dei geni usano congiuntamente
  tutte le linee; costruire split per studio/linea e una curva del numero di
  contesti. Il primo confronto è già eseguibile in locale, senza R o Colab.
- **Jurkat:** audit del pannello e degli stati, poi confronto sul solo supporto
  misurato. I 374 geni non diventano zeri sul resto dell'asse.
- **Nuovi dati:** cercare per linea, saggio e accessioni nei supplementi e nei
  depositi degli autori; tenere un catalogo anche dei risultati negativi.
  La ricerca incollata non dimostra che dati squamosi/cervicali pubblici non esistano.
- **Identità A/B/C e licenze Orion/Pisces:** non verificate in questa sessione;
  non promuovere le ipotesi incollate a fatti.

Il passo verso una rete resta un esperimento da progettare, non una conseguenza
automatica del numero di dataset raccolti.
