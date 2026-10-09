# Pilot AMMI sul pannello: specifica r2 prima del fit

9 ottobre 2026. Integra le sette condizioni di VALIDAZIONE delle 02:44 in
`../validazione_indipendente_8a8ca58a_2026-10-08/MESSAGGI.md`.
Sostituisce la proposta r1 per i futuri fit, che non sono ancora stati avviati.
Implementazione del modello: `ammi_context.py`; integrazione e guardie aggiuntive:
`ammi_contract_v2.py`. Il trainer principale resta di DATI-TRANSFER.
Stato: specifica congelata; input numerici e ancore con esclusioni ancora da consegnare.
Questo documento non autorizza nuovi consumi cloud.

## Precedenti e segnale verificabile

S-001/S-002: correggere un'ancora congelata invece di sostituirla senza confronto.
S-006: decoder senza bias, riferimento ESM2 congelato sul training e guardia della
componente comune. S-007: codificare ogni NTC prima di mediare; la media degli stessi
input e il modello senza contesto sono confronti addestrati separatamente.
S-009/S-012: identica ancora T0, centratura, scala e maschere nel fit e nell'export;
nessun ricentraggio sui target delle query. S-013: massa uguale per lignaggio,
registrazione della massa realmente consumata e risultati per lignaggio.

**Segnale precoce e arresto:** parità al byte a residuo zero, gradienti verificati,
copertura e massa effettiva, disc95 con controllo positivo indipendente, ampiezza
e quota comune del residuo nelle guardie interne e nell'export. Un errore tecnico
blocca la corsa; una guardia fallita blocca l'export, senza correzioni post hoc.
Un esito negativo del pilot non chiude tutte le reti né gli embedding ESM2.

## Ancora e pannello: scelta (a)

Si addestra solo dove l'ancora T0 di produzione è definita, sul pannello congelato
del banco. Si preserva la sua centratura sul pannello: non si usa l'ancora T2
centrata su tutti i bersagli. Il pannello è fissato per fold, non ricostruito dal
mini-batch o dai target estratti nel pilot. La supervisione usa la stessa scala
ln fold change finale dello stadio 100, prima della scala dell'emissione.

Ogni ancora deve escludere le risposte del lignaggio esterno e di quello interno;
per le righe di training esclude anche il lignaggio della riga. Per validation
interna e test esterno non si riammette la linea interna a fine training: nessun
refit ulteriore. Le ancore panel T0 già esistenti nei dataset privati di VALIDAZIONE
sono riferimenti di produzione; si riusano solo se le esclusioni coincidono.
Le nuove ancore richiedono manifest delle esclusioni e pin di tutte le fonti.

Non si addestra sul residuo di una risposta già incorporata nella propria ancora.
Un test che cambia le risposte escluse deve lasciare identici ancore, selezione
e normalizzazione. Un'ancora con maschera falsa non diventa uno zero osservato.
Il pilot mantiene il supporto della propria ancora; ESM2 mancante dà residuo zero.
La parità a residuo nullo deve preservare l'intero file dell'ancora, byte per byte.

## Split, NTC e limiti di copertura

Primo fold C-K562, validation interna CD4T. Secondo fold C-iPSC, interna K562.
Tutte le esclusioni sono per lignaggio intero e alias riconciliati. Le linee già
esaminate sono sviluppo; H1 test resta chiusa. J necessita un protocollo e
ancore dedicate senza i target nascosti e loro componenti in tutte le fonti.

Si considerano tutti i contesti ammessi dalle viste congelate. Per contesto:
fino a 64 target del pannello con ESM2 e supervisione valida, hash con sale
`esm2-ammi-pilot-r1` e soli identificatori. Tutti i geni di risposta utilizzabili
restano nella loss mascherata. Zero target ammessi, NTC assenti o ancore mancanti
sono lacune nominate: nessuna eliminazione silenziosa, nessuna copertura completa.
Il pilot ristretto al pannello non sostituisce il percorso D-053 fuori pannello.

DATI fornisce NTC individuali, fino a 64 per strato biologico/tecnico identificato,
provenienza, assi, maschere e denominatore nativo per cellula. `cells` legge
log1p(counts * 10000 / depth_native) e mask; `mean` media esattamente questi
input già trasformati e le loro mask, poi applica lo stesso encoder. Non usa
log1p dei conteggi medi. Nessuna rinormalizzazione sui soli geni allineati.
I controlli del test sono input ammessi; le risposte perturbate escluse non entrano
in fit, selezione, riferimento ESM2, statistiche o scelta dei parametri.

La supervisione resta aggregata; gli NTC sono letti cellula per cellula.
Non è ancora supervisione sulle cellule perturbate individuali, né D-053 completa.

## Bracci, pesi e addestramento

Architettura invariata: ancora + decoder[(proiezione lineare senza bias di
ESM2 - mu_train) * stato NTC]. ESM2 congelato; rango 16, hidden 64, decoder
inizializzato a zero, altri fattori non nulli. Nessuna nuova testa cis o ampiezza.

Per fold: `cells` e `none` riaddestrati ai semi **17, 29, 43**; `mean` a seme 17,
descrittivo. Stessi esempi, ordine per seme, ancore e inizializzazione dei moduli
condivisi. Il controllo `swapped` usa ciascun checkpoint `cells` già addestrato,
senza nuovo fit: cambia solo i controlli con quelli di un altro lignaggio del
training, mediante hash degli identificatori fissato prima dei risultati.
Si esportano anche le previsioni scambiate e la mappa sorgente/destinazione.
La mancata variazione dimostra mancato uso funzionale del contesto.

Massa di training uguale per lignaggio; al suo interno uguale per contesto;
nel contesto uguale per riga. Ogni riga pesa la media degli errori sui propri
geni validi. I pesi globali sono calcolati dopo tutte le esclusioni e congelati:
mai rinormalizzati per massa osservata nel batch. `mu_train` usa gli stessi
pesi globali sui target delle righe ammesse. Alias non creano due lignaggi.
Ricevute per epoca e finestra: righe previste/viste, massa attesa/consumata per
lignaggio e contesto, supporto genico, NTC viste e contributo numerico alla loss.

AdamW lr 0,0003, weight_decay 0,0001; due epoche complete, batch 32, penalità
L2 del residuo 0,01 sullo stesso supporto. Mini-batch uniformi senza rimpiazzo;
obiettivo del batch = N/B volte la somma dei contributi pesati globalmente,
con B effettivo anche nell'ultimo batch. Nessuna selezione di epoca o tuning
sulla validation interna o esterna. GPU reale su davidmaisterx, modello e
tensori su CUDA attestati; il locale resta limitato a fixture piccole.

## Guardie e lettura indipendente

Per contesto, su geni con almeno due target osservati: quota comune del residuo
<= 0,5; RMS residuo/ancora <= 0,5 sul supporto dichiarato. Supporto insufficiente
o valori non finiti bloccano il verdetto. Ancora nulla consente solo residuo nullo.
Si riportano anche quota comune dell'ancora e della previsione intera, senza
introdurre una nuova soglia. Nessun clipping o centratura per superare le guardie.

La validation interna serve alle guardie, con disc95 e controllo positivo del
banco: non si implementa una metrica omonima ma diversa. Consegna per ogni
fold/braccio/seme nel formato stage100: byte, SHA256, provenienza e ricevuta di
consumo; ancora originale e prova di parità nulla. Il banco riporta ogni lignaggio
accanto alla macro e variabilità fra semi distinta dal bootstrap fra bersagli.
Una differenza a un seme non permette di dire che il contesto aiuta.

La regola di promozione di VALIDAZIONE resta invariata: sei membri e almeno due
fold. Il pilot non promuove da solo, non apre una submission e non cambia t36.

## Ridge già conclusa: regola di integrazione distinta

Prima della lettura dei nuovi output C, si accetta esplicitamente la regola
descritta da VALIDAZIONE alle 11:25: **T0 dove il transfer predice; ESM2 come
ripiego dove il transfer non predice**, con supporto e scala verificati dal banco.
Nessuna media pesata o residuo della ridge scelto dopo i numeri. La formulazione
generica dell'accordo v1 non autorizza una sostituzione diversa per questa lettura.
AMMI resta invece l'esperimento additivo sopra T0 definito in questo documento.
