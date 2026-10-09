# Correzione ESM2 × stato dei controlli — proposta r1

9 ottobre 2026. Ipotesi e specifica scritte prima di leggere risultati biologici.
Implementazione isolata: `ammi_context.py`; sei fixture CPU in `ammi_tests_r1.txt`.
**Stato: proposta da concordare con VALIDAZIONE; input cellulari e ancore non
ancora congelati. Nessun fit biologico né lancio GPU autorizzato da questo file.**

## Domanda e scelta

Lo stato dei singoli controlli permette una correzione specifica del bersaglio
che superi l'ancora congelata senza perderne la discriminazione? Si riprende
il primo blocco AMMI del catalogo 5/10 e il mandato reti del Lead 9/10.
ESM2 resta congelato: si addestrano proiezione del bersaglio, encoder dei
controlli e decoder a basso rango. La ridge in corso è un confronto distinto,
target-only; non è fine-tuning ESM2 e non legge controlli cellulari.

PIE resta il concorrente congelato già selezionato: adattatore disponibile,
ma pesi/memoria non acquisiti, piano minimo 45,64 GB, esposizioni e ponte di
scala da qualificare. Non blocca questo ramo e non è stato scartato da uno score.
Non vengono aperti altri cataloghi o rilanciato CellNet invariato.

## Precedenti e differenza verificabile

- S-001/S-002: preservare l'ancora e confrontare la discriminazione dei target.
- S-006: decoder senza bias, nessun percorso additivo dal solo contesto;
  centrare i descrittori ESM2 su una popolazione di training congelata.
- S-007: `cells` codifica separatamente ogni controllo prima di mediare gli
  embedding; `mean` applica lo stesso encoder alla media degli input. Il test
  a medie uguali verifica che il primo veda eterogeneità. Il semplice basale
  medio è un'ablation, non il nuovo candidato.
- S-009: ancora, scala, maschere, centraggio e correzione identici nel fit,
  banco e export. Guardia su ampiezza e componente comune anche al pannello
  esportato, senza cambiare riferimento o centrare sulle query a posteriori.

**Segnale precoce e arresto:** parità a residuo zero, gradienti dopo il primo
update, disc95 con controllo positivo, ampiezza e quota comune per contesto.
Errore tecnico arresta immediatamente; guardie fallite bloccano export e scala
piena, senza ritoccare le soglie dopo aver letto i risultati.

## Modello e quantità

`prediction = frozen_anchor + W_out[(W_target (ESM2 - mu_train)) * context]`.
`context` è la media di un encoder nonlineare delle cellule NTC; le maschere
di misurazione entrano nell'encoder. Rango 16, hidden 64. W_out parte a zero;
W_target e l'encoder hanno inizializzazione non nulla. Il gradiente al decoder
deve essere non nullo al primo passo, agli altri rami dopo il primo update.
Non si inizializzano contemporaneamente a zero tutti i fattori del prodotto.

`mu_train` è la media ESM2 pesata dei soli target ammessi e con feature presenti,
calcolata dopo esclusioni e congelata nel checkpoint. La proiezione target è
lineare e senza bias: su **questa popolazione di riferimento** la correzione
media è zero a contesto fisso. Questo non garantisce media zero su un pannello
diverso: lì intervengono misure e guardie, non una nuova centratura.
Le query singole o in batch devono produrre lo stesso risultato.

Scala della testa: quella dell'ancora e della verità aggregate, ln fold change
con la medesima normalizzazione/pseudoconteggio del contratto. Nessuna nuova
amplificazione, correzione cis o trasformazione del generatore. L'encoder dei
controlli può leggere log1p CP10k: questo **non** rende la sua uscita una logFC;
la supervisione e l'ancora fissano separatamente la quantità prevista.

ESM2 mancante: residuo zero e fallback esplicito all'ancora, non vettore zero
spacciato per feature. TMEM104 resta riportato. Risposta non misurata: loss
mascherata, mai zero osservato. Controlli assenti: errore o fallback dichiarato
prima del fit; nessuna eliminazione silenziosa del contesto.

## Dati, split e copertura

DATI fornisce manifest e pin per context_id: controlli NTC verificati, conteggi
ammessi, assi, maschere, denominatore di libreria nativo e provenienza. Non si
normalizza sul solo sottoinsieme di geni allineato. Controlli di test ammessi
come input; risposte perturbate della linea esclusa vietate al fit e alla
scelta di feature, normalizzazione, ampiezza, early stopping o architettura.

Viste C/J congelate e distinzione context_id/lignaggio restano quelle correnti.
J esclude tutti i target nascosti e componenti in ogni studio. H1 test chiusa.
I controlli di una linea non diventano esempi di risposta perturbata.
Le linee già esaminate rimangono sviluppo, non nuova conferma indipendente.

Primo pilot: C-K562, tutti i suoi contesti di training ammessi e tutti i geni
di risposta; fino a 64 target per context_id scelti solo per hash con sale
`esm2-ammi-pilot-r1`, senza leggere la verità. Ogni contesto con meno target
li mantiene tutti. Campioni NTC annidati da 64 cellule per strato disponibile;
le regole di strato/replica devono essere nel manifest DATI prima del lancio.
Nessuna selezione dei contesti per comodità. Ogni contesto privo di NTC è una
lacuna aperta che blocca la dichiarazione di copertura del pilot.

La loss iniziale è MSE mascherata sugli **effetti aggregati**: i controlli sono
letti cellula per cellula come input, ma le cellule perturbate non sono ancora
supervisione individuale. Non dichiarare chiuso il mandato cellulare D-053.
Registrare righe/target/contesti previsti e usati, NTC viste, pesi e contributi
alla loss per finestra ed epoca. Scale piena e supervisione delle cellule
perturbate richiedono consegne distinte, non un cambio silenzioso del pilot.

Per ogni esempio di training l'ancora va ricostruita dalle sorgenti consentite
escludendo il suo lignaggio di risposta; per validation interna si applicano
anche le esclusioni interne. Non usare come label residua una propria risposta
già incorporata nell'ancora. DATI deve fornire o qualificare questa vista:
è una dipendenza reale, non risolta dall'esistenza dell'ancora di produzione.

## Contrasto, arresto e passaggio alla scala piena

Tre bracci riaddestrati a seed 17: cells, mean, none. Stessi dati, ordine di
batch e ancore; none usa vettore contestuale unitario, senza leggere lo stato.
Riferimenti: ancora congelata e ridge ESM2 del medesimo fold. Nessuna miscela
o scelta di ampiezza su test. Proposta iniziale: AdamW lr 0,0003, decay 0,0001,
due epoche complete, batch 32, penalità L2 del residuo 0,01. VALIDAZIONE deve
accettare la specifica e lo split interno prima del fit biologico.

Arresto tecnico immediato per errore di asse/hash/scala/copertura, NaN sul
supporto o perdita della parità iniziale. Guardie per contesto, in validation
interna e export: RMS residuo/ancora <=0,5 e quota comune <=0,5; assenza di
supporto sufficiente blocca il verdetto. Nessun clipping o riscalamento per
far passare la guardia. Un'ancora nulla non ammette un residuo arbitrario.

Livello A con contratto indipendente v2: disc95, supporto e controllo positivo,
target permutati, confronto appaiato contro ancora e ablation none. Il pilot
può giustificare solo il confronto successivo, non una promozione. Per espandere:
nessun errore tecnico, guardie superate, direzione favorevole della componente
specifica contro ancora e none con incertezza riportata; se indistinguibile,
non si dichiara beneficio del contesto. J e secondo lignaggio restano necessari.
La promozione mantiene la regola indipendente a sei membri già concordata,
più semi e almeno due fold, con PDS e denominatori visibili. Non si cambia
l'emissione per aiutare il candidato. Nessun invio fast fa parte del protocollo.

## Esecuzione e stato concreto

`ammi_context.py` è un modulo isolato, non ancora collegato al trainer v5.
Riusa lo schema di codifica cellulare e le invarianti di v5; loader bilanciato,
split e ricevute devono essere adattati soltanto dopo il contratto DATI.
`test_ammi_context.py`: parità nulla, gradienti, centraggio pesato, indipendenza
dal batch, eterogeneità a media uguale, permutazione NTC, maschere, fallback,
reload ed export che rifiuta componente comune o ampiezza eccessiva.

CPU locale solo fixture. Il fit deve usare CUDA realmente su davidmaisterx,
con preflight RAM/VRAM/disco/input e controllo modello/tensori su device. Quota
misurata separatamente in `accelerator_quota_r2.json`; nessuna prenotazione GPU
o assunzione che la quota garantisca hardware disponibile. Lancio subordinato
anche alla copertura del consenso sul pacchetto concreto e alla review indipendente.
