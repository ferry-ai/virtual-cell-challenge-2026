# ESM2: asset acquisiti, copertura completa e policy del primo fit

**Stato: preparazione del fit; nessun fit biologico o risultato predittivo.**
Aggiornamento dell'8 ottobre 2026 dopo l'audit delle 22:05 Europe/Rome.
I report precedenti conservano lo stato e le autorizzazioni del proprio momento.

## Mandato e confini

Il via umano al primo fit e all'acquisizione è stato verificato nella chat lead
`01a11c05-970e-7af2-a07e-3860bd74acbd`, messaggio umano
`01a11d0c-c3b1-7bf0-81a4-fecea099454c`: «Ok puoi avviare i task.
Cerchiamo di portare a termine un modello finito il prima possibile, ma con qualità.»
DATI-TRANSFER conserva banca, viste, pesi e risoluzione degli input; questa sessione
conserva adattatore e fit ESM2. Nessun invio VCC, push Git o acquisto implicito.

## Misurato: acquisizione e copertura

Gli asset ESM2, 98.539.820 byte totali, sono acquisiti in
`C:/Users/ferra/vcc2026-data/external_models/01a11c35/PIE_sources/cb1aaa4e7655605bdc70a9bd77bbd62016b8c7d7/esm2/`.
Hash della matrice e dei metadata in `feature_coverage_r1.json`; verifica completa
di forma, tipo e finitezza di tutti i valori. Nessuna risposta RNA letta.

| Vista | Righe dichiarate | Contesti | Target | Target con ESM2 | Righe senza ESM2 | Peso senza ESM2 |
|---|---:|---:|---:|---:|---:|---:|
| production r1 | 203.975 | 47 | 18.562 | 18.348 | 786 | 0,276744% |
| T r1 | 163.143 | 47 | 14.786 | 14.626 | 650 | 0,271594% |

Sono inventari verificati sui metadata congelati, non ricevute di consumo del fit.
Il JSON elenca ogni simbolo mancante e ogni contesto con conteggi e pesi.
Match esatto: nessun alias inventato. Non equivale a completamento D-053.

## Decisioni congelate prima del fit e dei suoi numeri

- Policy `training_weighted_mean_plus_missing_indicator_v1`: media dei vettori
  ESM2 osservati, pesata con la somma dei pesi delle sole righe training ammesse
  per target. Imputazione dei vettori mancanti con quella media; aggiunta di una
  coordinata missing, 1 per imputati e 0 per osservati. La standardizzazione
  successiva usa sempre le righe training e i loro pesi originali.
- Tutte le righe e i contesti ammessi partecipano alla loss: nessuna esclusione
  per feature mancante. Nessuna risposta biologica o feature delle query entra
  nella stima della media di imputazione.
- Le query senza ESM2 restano **non supportate dal ramo specifico**: effetto NaN,
  maschera falsa; il generico stimato sul training è esportato separatamente.
  Nell'integrazione si usa il ripiego della baseline previsto da K3. Il vettore
  imputato non viene descritto come feature osservata.
- Alpha 1.0, nessuna ricerca di iperparametri. Modello target-only: lo stesso
  target riceve lo stesso effetto in contesti diversi a parità di modello.
- T richiede target non visti e context_id visto; C lignaggio escluso e target
  visto; J lignaggio e target esclusi. Gli split e l'esclusione delle componenti
  prima delle statistiche restano responsabilità della derivazione di DATI.
  La guardia del runner non sana contaminazione upstream.

## Interfaccia e prove

Nuovi file `feature_policy.py`, `chunk_store_v2.py`, `run_sufficient_probe_v2.py`.
Il builder v2 supporta `mask_storage=finite_verified`: verifica per ogni chunk
originale che valori finiti e maschera coincidano (osservati finiti, mancanti NaN),
poi deriva la maschera per blocchi dal mmap degli effetti. Nessuna maschera piena
in RAM o file bool duplicato. Lo store di produzione richiede così circa 15,12 GB
di valori invece di 18,90 GB valori+maschera; risparmio calcolato di 3,78 GB,
oltre agli header/assi. Il confronto con maschera esplicita fa parte della fixture;
un chunk con maschera incoerente è rifiutato. La ricevuta registra la verifica.
Le versioni precedenti restano immutate. Il builder v2 ammette esplicitamente T;
non etichetta T come J. Il manifest del fit richiede `missing_feature_policy`
uguale all'identificatore sopra. Il modello salva anche `imputation_mean` e
`feature_policy`; le predizioni salvano `esm2_observed`. La ricevuta conserva
nomi/count/pesi dei mancanti e uso effettivo di righe/contesti/target.

`test_feature_policy.py`: media pesata indipendente da query e placeholder
mancanti; rifiuto degli incroci errati C/T/J; percorso completo chunk → store →
fit T → predizioni, con riga senza ESM2 inclusa e parità con soluzione densa;
query senza ESM2 mascherata e gene senza risposte non supportato. Solo fixture.

## Consegna a VALIDAZIONE

Accetto gli emendamenti del contratto indipendente v2, conservando le regole
di v1 non emendate e K3 come sostituzione sul supporto esterno + ripiego baseline.
Questa nota fissa l'alternativa ESM2 prima dei suoi risultati; non dichiara già
concordato un nuovo braccio di miscela o una promozione.

La prima esportazione del runner è in effetti nativi: nessun gain, cis o fattore
di emissione applicato. Per il confronto autonomo si propone gain 1 e nessuna
testa cis aggiunta; per K3 lo stesso esterno sostituisce la baseline sul supporto,
senza sommare altre correzioni. Questa scelta richiede la revisione della scala
da VALIDAZIONE prima dell'ammissione allo stadio 100. Nessuna scala sarà scelta
sulle risposte del fold. Le predizioni restano `not_scored` e la compatibilità
con l'emissione `not_established` fino alla verifica indipendente.

## Runtime e dipendenze aperte

Colab non è stato verificato attivo; il log dispatcher letto terminava il 3/10.
Concordata la verifica di Kaggle CPU df11. DATI prepara il resolver dei mount e
dei chunk privati. La revisione automatica aveva bloccato il trasferimento di
URL temporanei df→df11; DATI ha poi comunicato il consenso umano specifico,
registrato nella propria `runtime_access_authorization_r1.json`. Il trasferimento
non è stato eseguito da questa sessione. Nessun URL o credenziale in questa cartella.
Il preflight effettivo, lo smoke reale e il fit completo restano da eseguire.

## Precedenti

S-001/S-002/S-006: il generico separato e le guardie di specificità distinguono
un apprendimento della risposta comune dall'informazione sul target. S-003/S-009:
nessuna miscela o scala scelta a posteriori e nessuna doppia correzione. S-008:
ESM2 è una feature congelata con regressore semplice, non il rilancio di Arc Stack.
Il nuovo indicatore missing documenta una necessità di copertura prima del fit.

**Segnale precoce e arresto:** input/hash/assi o uso delle righe non corrispondenti
fermano il job; assenza di ESM2 su tutte le righe ammesse ferma l'imputazione.
La validazione scientifica applica le guardie e le soglie del contratto v2,
senza usare il solo superamento dei test tecnici come prova di beneficio.
