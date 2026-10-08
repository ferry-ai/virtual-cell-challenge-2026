# Aggiornamento r3 — lettura a blocchi per la ridge

**Implementato e misurato su fixture, non su dati biologici.** Richiesta ricevuta
da DATI-TRANSFER dopo le prime derivazioni all-target. I file del componente denso
nel commit `10a2849` restano invariati. Quattro prove aggiuntive sono passate in
2,575 s (`streaming_tests_r1.txt`); nessun training reale, download o job cloud.
Ora verificata alla lettura dei risultati: 18:57 Europe/Rome, 8 ottobre 2026.

## File nuovi e contratto

- `chunk_store.py`: legge una volta i chunk NPZ del proprietario; scrive
  `effects.npy` float32 e `observed.npy` bool con mmap e ordine Fortran, più
  `axes.npz` e ricevuta con hash. Vietato collocare lo store nel repository.
- `embedding_ridge_streaming.py`: stessa loss pesata, alpha, standardizzazione
  delle feature, maschere e intercetta della ridge densa; lettura per colonne,
  64 geni per blocco come default, cache massima di due fattorizzazioni.
- `run_streaming_probe.py`: stessa interfaccia sperimentale del runner denso,
  `train.path` indica lo store e `train.sha256` il suo `manifest.json`.
- `test_streaming_ridge.py`: parità numerica, limiti di lettura e rifiuto di
  input incompatibili; ricevuta `streaming_tests_r1.txt`.

Manifest di staging, schema `external-ridge-chunks/1`, fornito e congelato dal
proprietario della banca:

| Campo | Contenuto |
|---|---|
| `modality` | `CRISPRi`, con la stessa modalità in ogni identity |
| `validation_review` | Riferimento reale alla review, non il segnaposto dei test |
| `quantity`, `normalization` | Unità e preprocessing nativi, uguali al manifest fit |
| `regime`, `release_sha256`, `split_manifest_sha256` | Regime C/J/production e hash reali della release e dello split applicati prima delle statistiche; uguali nel manifest fit |
| `effect_field` | `raw` oppure `shrunk`, scelto prima del confronto |
| `genes` | Asse ordinato comune, unico, verificato contro ogni chunk |
| `excluded_contexts`, `excluded_targets` | Liste canoniche complete; regola hash T/J applicata upstream prima delle statistiche |
| `expected_rows_by_context` | Conteggi per context_id, non per solo lignaggio |
| `chunks` | Lista ordinata descritta sotto |
| `max_chunk_rows` | Limite dichiarato prima del caricamento; default 128, nessun taglio automatico |

Ogni chunk dichiara `path`, `sha256`, `context_id`, `context_group`, `targets`
nell'ordine del file, `weights` positivi per riga e `identity` corrispondente al
JSON `meta` del NPZ. Il path può essere assoluto o relativo al manifest. Il reader
verifica esattamente geni, target, metadati, float32/bool e NaN fuori maschera.
`identity.line_group` deve coincidere con `context_group`; righe di contesti
diversi non vengono aggregate. Un context_id non può designare identità diverse.
Il reader non sceglie pesi né elimina target/contesti. Un errore lascia lo store
incompleto senza manifest di completamento; non riutilizzarlo come pronto.

Il runner rifiuta uno store di produzione dichiarato poi come C/J o un diverso
hash di release/split. La completezza e veridicità della dichiarazione upstream
restano da verificare tramite la ricevuta DATI-TRANSFER: questi campi non provano
da soli che gli split siano stati applicati correttamente.

```powershell
.\scripts\py.cmd reports/analisi/modelli_esterni_01a11c35_2026-10-08/chunk_store.py --manifest <chunk_manifest.json> --out <nuovo_store_fuori_repo>
.\scripts\py.cmd reports/analisi/modelli_esterni_01a11c35_2026-10-08/run_streaming_probe.py --manifest <fit_manifest.json> --out <nuovo_output_fuori_repo>
```

Il manifest fit conserva protocollo concordato, query senza verità, esclusioni,
revisione ESM2, alpha preregistrato e ricevuta di consumo. Accetta in più
`gene_block` (default 64) e `factor_cache` (default 2): cambiano il consumo di
risorse, non la regola scientifica. L'output resta nativo, non automaticamente
pronto per il generatore; serve ancora il bridge di quantità/normalizzazione.

`validation_review` registra lo stato della valutazione comparativa e può essere
pendente: non introduce un'approvazione di VALIDAZIONE per ogni fit di sviluppo.
L'ammissione tecnica si basa sui controlli effettivi di hash, assi, metadati,
modalità, regime/release/split, copertura ed esclusioni. Il protocollo deve essere
concordato prima dei risultati; un fit con valutazione pendente resta `not_scored`.
I permessi del proprietario per download e cloud restano separati. Questa
distinzione è stata concordata con DATI-TRANSFER prima di qualsiasi fit biologico.

## Cosa è stato verificato

Parità con il codice denso su fixture pesate con feature costante, geni totalmente
o parzialmente mancanti, sistemi sia con più righe che feature sia viceversa;
predizioni e coefficienti concordano entro rtol 1e-11/atol 1e-12. Un reader di test
solleva errore se il fit tenta di convertire l'intera matrice o leggere più colonne
del blocco: il test passa. Alterare valori mascherati non cambia i coefficienti.
Roundtrip chunk→mmap→runner verificato; hash errati, assi invertiti, identity diversa,
righe duplicate, copertura divergente e modalità CRISPRko sono rifiutati.

Questa è equivalenza numerica su esempi piccoli. Non misura RAM di picco o velocità
sul corpus reale e non dimostra beneficio biologico. SciPy disponibile nel runtime
locale verificato: 1.18.1; il runtime cloud dovrà avere dipendenze esplicite.

## Risorse e limiti residui

Lo store richiede circa **5 × R × G byte** su disco, oltre a NPZ originali, assi,
header e output. La matrice completa delle risposte non viene copiata in float64;
gli array temporanei delle risposte sono limitati a R × gene_block. Restano in
RAM feature e loro temporanei O(R × D), coefficienti O(D × G), cache di sistemi
lineari e predizioni. La cache di fattorizzazioni è limitata, ma il numero di
maschere distinte può aumentare sensibilmente il costo del fit. Non è un benchmark
di throughput e non garantisce che l'intero corpus entri nel runtime scelto.

Se G è minore o uguale al blocco scelto, il singolo blocco coincide naturalmente
con la matrice completa: la ricevuta lo dichiara e registra il massimo numero di
colonne materializzate. Non aumentare `gene_block` fino a G sul corpus grande.

Non ridurre contesti per farlo entrare: prima misurare R, G, D, disco, RAM libera
e picco reale nel runtime autorizzato. Drive può ospitare l'archivio; per mmap
intensivo è preferibile lo staging sul disco del runtime, valutato nel preflight.
Feature ESM2 mancanti in training continuano a bloccare il fit: il proprietario
deve dichiarare una policy, non si eliminano righe in silenzio.

DATI-TRANSFER ha comunicato autorizzazioni per le proprie derivazioni. Ha anche
precisato che esse non autorizzano training o acquisizioni di questa sessione.
La richiesta al proprietario per ESM2/PIE e prove cloud resta pendente; nessuna
autorizzazione è stata dedotta dai messaggi di un'altra chat.

**Verdetto scientifico invariato: approfondire.** Questa modifica rende il probe
più adatto a ricevere la banca reale senza cambiare il protocollo preregistrato.

## Consegna del pilot e controlli finali

Letto solo il manifest `training_view_production_pilot_r1.json` di DATI-TRANSFER:
8.819 righe × 18.533 geni, 4 contesti CRISPRi, 73 chunk. Dal prodotto delle forme:
817.212.635 byte per effetti+maschera mmap, circa 90,3 MB per una matrice feature
float64 R×1280 e 189,8 MB per i coefficienti 1280×G. Sono conti delle dimensioni,
non RAM di picco misurata: temporanei e librerie richiedono altro spazio.
Il manifest ha mount non risolti e review comparativa pendente; produzione parziale,
non banco C/J e non corpus D-053 completo. DATI-TRANSFER preparerà una nuova
revisione con i riferimenti regime/release/split richiesti, senza alterare r1.

`combined_tests_r2.txt`: tutte le 17 prove passate in 5,111 s. Le successive prove
`streaming_tests_r2.txt` e `streaming_tests_r3.txt` documentano gli stati intermedi;
la revisione finale `streaming_tests_r4.txt` verifica anche che una valutazione
comparativa pendente non venga confusa con un divieto di fit tecnico.

Suite generale obbligatoria rieseguita: `repo_tests_r2.txt`, 290 test in 575,346 s,
tre errori per `cell_eval2.config` mancante; nessun errore degli indici/cartelle.
`docs_check_r4.txt`: otto segnalazioni relative a file concorrenti DATI-TRANSFER
non ancora registrati. Non sono state corrette modificando i file condivisi.
Non si dichiara la suite globale verde e non si installano dipendenze comuni
durante il lavoro degli altri proprietari.
