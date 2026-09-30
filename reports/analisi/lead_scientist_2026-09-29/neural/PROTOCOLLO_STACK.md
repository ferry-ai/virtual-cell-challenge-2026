# Stack: pilot prospettico con prompt cellulari

29 settembre 2026. **Proposta implementata, non eseguita con il modello.** Questo
pilot è separato dal banco fattoriale dei generatori e dalla source-attention.
Non legge risultati di scoring per scegliere bersagli, opzioni o ampiezze.

## Domanda e regime

Stack-Large-Aligned, 217 milioni di parametri, può trasferire una risposta K562
usando come contesto i controlli HepG2 meglio della previsione congelata K562?
È il regime C, stessi target e nuova destinazione. **Non si dichiara HepG2 mai vista
nel pretraining pubblico**: il training Stack/scBaseCount non è stato escluso o
ricostruito su queste famiglie. Non è un test J.

La scelta usa i 48 bersagli development già congelati nel manifest del banco
generatore r3. Fra quelli con almeno 64 cellule K562 nel file originale, si prendono
i primi 12 ordinati per SHA256 della stringa `Stack:20260929:<target>`. Le cellule
sono aggregate per gene su tutte le guide. Se mancano 12 target il programma si
ferma; nessun ripiego sulle conferme o scelta in base agli effetti. La lista concreta
è salvata da `plan` prima dell'estrazione e dello scoring.

I derivati K562 `x002` non bastano: fra i 48 development contengono soltanto CTU2
(295 cellule) e NOMO1 (593). Il file originale è ancora presente in
`G:/Il mio Drive/vcc2026/data/raw/replogle/K562_gwps_raw_singlecell_01.h5ad`,
65.830.941.948 byte. Il reader usa soltanto una colonna categoriale per scegliere
righe e poi legge le righe dense selezionate. Non copia o attraversa tutti i 65 GB.

## Input e modello fissi

- K562: fino a 128 cellule reali per target, senza rimpiazzo; 512 NTC reali.
- HepG2: 2.000 NTC reali senza rimpiazzo, o tutte se fra 512 e 1.999; 512 fra questi
  alimentano Stack. Nessuna cellula perturbata HepG2 entra nel bundle o nel modello.
- Effetti transfer già congelati, log naturale e mask `observed` esplicita. Non si
  deduce la mask da `lfc != 0`. I valori zero osservati rimangono osservati.
- Codice Arc commit `cacc2e4b09435c3e536d46237d10b50f222dd144`; checkpoint
  `arcinstitute/Stack-Large-Aligned` revision `b09f085dac03d170b078a5c72f550ae93686e544`.
  I checksum dei due file consentiti sono in `STACK_ALLOWLIST.json` e nel codice.
- `ICL_FinetunedModel`, valutazione, nessun fine-tuning: cinque passi `mdm`,
  prompt ratio 0,25, context ratio 0,4, minimo 0,2, mask rate 1; seed 20260929.
  Queste opzioni riprendono l'[API pubblica](https://github.com/ArcInstitute/stack/blob/cacc2e4b09435c3e536d46237d10b50f222dd144/src/stack/models/core/inference.py).
- Input raw counts. Si usa l'intersezione dei geni misurati in K562, HepG2 e nella
  lista Stack. Sul resto della lista Stack entrambi gli input sono zero. Il modello
  mantiene tutta la sua architettura; si conserva solo l'effetto sull'intersezione.
  Supporto, frazione della lista modello e massa fuori supporto sono espliciti.
  Come stage 73 e banco HepG2, si conserva la prima colonna per simbolo duplicato,
  mantenendo l'ordine originale e contando le colonne escluse. I metadati K562
  originali hanno 8.248 colonne e 8.246 simboli unici; la regola è fissata prima
  dell'estrazione, non decisa sui risultati.

Batch iniziale 1, worker 0. Il batch può essere ridotto/aumentato per memoria senza
cambiare i prompt, l'asse, il numero di cellule per set o i parametri biologici.
Non si promette identità bit-per-bit fra batch diversi: le operazioni GPU e i
campioni possono cambiare. Ogni run registra batch e runtime; cambiare dopo aver
visto gli score crea un esperimento nuovo.

## Controllo sintetico e produzione delle 400 cellule

Per ciascuna dimensione di prompt si genera un controllo sintetico usando lo stesso
numero di NTC K562, gli stessi 512 NTC HepG2 e lo stesso seed del prompt perturbato.
Il [tutorial Stack](https://github.com/ArcInstitute/stack/blob/cacc2e4b09435c3e536d46237d10b50f222dd144/notebooks/tutorial-predict.ipynb)
motiva la correzione con un controllo sintetico ma non specifica nel notebook una
formula finale: **la formula seguente è nostra, preregistrata, non attribuita ad Arc**.

Sull'asse condiviso S, si sommano i conteggi generati e si normalizzano ciascuna
popolazione alla massa 1. Si calcola
`d_g = clip(log((p_pert,g + 1e-6)/(p_ctrl,g + 1e-6)), ±6 log(2))`.
È una regolarizzazione di 1 CPM, fissa, senza fitting sul vero perturbato HepG2.

La baseline completa q0 viene prodotta dagli effetti transfer con `predicted_profile`.
Nel candidato, su S si usa il basale HepG2 inclinato da `exp(d)` e normalizzato alla
stessa massa q0(S); fuori S si mantiene q0 **esattamente**. Questo è un candidato
ibrido Stack/transfer, non una previsione Stack pura su tutti i geni. Con prompt e
controllo identici l'effetto Stack si annulla su S; fuori S resta il transfer.

Entrambi i bracci (`transfer`, `stack`) passano allo stesso Poisson con distribuzione
empirica delle library size HepG2. Si emettono 400 cellule nuove per target, flussi
casuali fissati per target, massimo 12.000 valori nonzero e 1.000.000 conteggi per
cellula. Nessuna cellula sorgente viene copiata nell'output; nessun totale di gruppo
o media realizzata viene bloccato o riparato. I cap si applicano alla singola cellula.
Il decoder Stack aiuta a stimare l'effetto; il suo rumore non è un nuovo braccio del
generatore. I valori intermedi del modello non sono venduti come cellule VCC.

## Lettura e limiti

L'inferenza scrive due H5AD di conteggi e diagnostica. Non esegue scoring né carica
truth. Il confronto successivo usa tutti e soli i 12 target e gli stessi controlli,
lo stesso scorer e la stessa proiezione sui cinque membri già dichiarata nel banco
generatore; riportare separatamente MSE e tutti i membri. I 12 sono un pilot
esplorativo: non costituiscono conferma indipendente o autorizzazione automatica
all'invio. Il criterio per proseguire è proiezione media positiva rispetto al
transfer e PDS medio non inferiore, senza scegliere target favorevoli dopo gli score.
Qualunque candidato da portare oltre richiede una conferma prospettica distinta.

Prima dello scoring verificare: NTC-only destinazione, 12 × 400 cellule, conteggi
integrali e cap, assi identici, profilo invariato fuori S, e drift sintetico nullo.
I test locali con modello fittizio verificano il contratto; non provano che i pesi
Stack girino o generalizzino. Nessun download di checkpoint o inferenza è incluso
nella preparazione. Uso in gara e condizioni di licenza restano una verifica
distinta; non viene inventato un divieto a partire dalla sola dicitura NC.

## Memoria e avvio revisionabile

Per B batch, C cellule/set e G geni: un input float32 occupa `4 B C G` byte;
le due uscite del decoder `8 B C G`; un latente `4 B C H D`.
A titolo di dimensionamento, B=1, C=512, G=15.012 dà 30,7 MB per input e 61,5 MB
per le due uscite. Non è una stima del picco totale. Pesi 217M float32 ~868 MB,
checkpoint 2,61 GB; caricamento iniziale CPU, poi trasferimento modello sul device.
Attention, buffer, copie e allocator si aggiungono. Le dimensioni effettive lette
dal modello e le versioni installate vengono salvate prima della prima generazione.

Ordine: `stack_pilot.py plan`, poi `prepare` con originale K562 e HepG2, infine
`infer` sul solo bundle e due file modello approvati. `STACK_ALLOWLIST.json`
definisce gli input ammessi; `requirements_stack.txt` è una specifica di ambiente
proposta, non un runtime già installato o certificato. `pip freeze` va salvato nel
job remoto insieme al manifest. L'output deve sempre essere nuovo.
