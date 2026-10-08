# Consegna tecnica r1 — in attesa della prova reale

**Verdetto attuale: approfondire.** Due componenti implementati e verificati su
fixture; nessuna inferenza PIE reale, nessun regressore fittato su dati biologici,
nessun beneficio comparativo dichiarato. Non adottare in produzione per il solo
fatto che il codice funziona. Questo stato sarà integrato da una nuova nota dopo
le autorizzazioni/dipendenze, senza sovrascrivere i risultati.

## A DATI-TRANSFER

File posseduti in questa cartella:

- `pie_adapter.py`: reader parquet PIE v1, join per dataset/contesto/target e gene,
  maschere separate, conversione log2→ln subordinata a bridge verificato,
  fallback della baseline conservato. Esporta NPZ e manifest con SHA256.
- `embedding_ridge.py`: regressore originale con pesi e maschere, generico fittato,
  rifiuto delle righe escluse; feature centrate/scalate solo nel training.
- `run_embedding_probe.py`: runner di fit/predizione nativa, nessuno scorer e
  nessuna verità di query. Verifica hash e ricevuta di consumo per contesto.
- `acquire_assets.py`: acquisizione selettiva con lock, verifica byte/hash,
  riuso verificato e parziali conservati. Richiede autorizzazione esplicita;
  non viene lanciato dal solo fatto che questo documento esiste.
- `audit_public.py`, `public_audit_r1.json`: inventario metadata riproducibile.
- `test_pie_adapter.py`, `interface_tests_r2.txt`: 13 prove CPU passate.

### Confine PIE

Input: parquet originale, baseline NPZ, contratto JSON. Baseline:
`effects[R,G]` float32/64, `mask[R,G]` bool, `genes[G]`, `dataset[R]`,
`context[R]`, `perturbation[R]` stringhe; R sono query esplicite ordinate.
Il contratto identifica release, protocollo, pesi, codice, asset, input con hash;
espone regime, inventario delle etichette già viste e review VALIDAZIONE.

Output: `effects.npz`, stessi assi, `effects`, `mask`, `external_mask`, e le tre
teste native separate. Fuori supporto esterno resta esattamente il valore della
baseline. Zero esterno valido sostituisce il valore; assenza non equivale a zero.
Non moltiplica per `p_de`. Non usa `delta_p_pred` come LFC. Nessuna calibrazione.

Il consumer dello stadio 100 usa file per contesto con `targets`, `genes`, `lfc`,
`observed`. DATI-TRANSFER può mappare rispettivamente perturbation/genes/effects/mask
in un wrapper isolato dopo il bridge; le celle non osservate vanno serializzate
come zero **con maschera falsa**, secondo il contratto produttivo. Vietata una
nuova applicazione di ampiezza, gamma o cis su questi effetti già finali. Gli
input del generatore e i suoi parametri restano responsabilità del proprietario.

```powershell
.\scripts\py.cmd reports/analisi/modelli_esterni_01a11c35_2026-10-08/pie_adapter.py --predictions <native.parquet> --baseline <baseline.npz> --contract <contract.json> --out <nuova_cartella>
```

`test_pie_adapter.fixture()` mostra un contratto **sintetico** completo per i test;
non copiarne i flag di review o gli hash come prova su dati reali.

### Confine ESM2

Runner:

```powershell
.\scripts\py.cmd reports/analisi/modelli_esterni_01a11c35_2026-10-08/run_embedding_probe.py --manifest <fold.json> --out <nuova_cartella>
```

Train NPZ fornito dal proprietario: `targets[R]`, `context_groups[R]`, `genes[G]`,
`effects[R,G]`, `observed[R,G]`, `weights[R]`. Riga unica per contesto canonico e
target; pooling degli strati e modalità restano upstream. Il manifest contiene
SHA training, hash metadata/matrice ESM2, quantità/normalizzazione, alpha fissato,
queries senza verità, liste escluse e conteggi attesi per contesto.

L'output `native_predictions.npz` conserva scala nativa e maschere, oltre a
`generic` e `generic_observed`; `ridge.npz` rende riproducibili i pesi. La ricevuta
registra righe/contesti/target, osservazioni e pesi realmente consumati, feature
mancanti, codice e hash. Questo non certifica da solo la copertura dell'intero
catalogo D-053: occorre la riconciliazione upstream. Missing descriptor in training
blocca il fit, anziché eliminare silenziosamente righe o contesti. Missing query
produce maschera falsa, per un fallback deciso nel confronto.

La ridge è una baseline target-only: non dimostra uso del contesto e non sostituisce
il training cellulare principale. ESM2 è congelato, nessuna API di embedding
chiamata e nessun fine-tuning. La regolarizzazione si sceglie soltanto sullo
sviluppo concordato, non provando ripetutamente sulla conferma.

## A VALIDAZIONE

Richieste prima del confronto:

1. Ratificare `PROTOCOLLO_r1.md` o scrivere un emendamento prima dei risultati:
   release/vista C/J, gruppi canonici, target/componenti, controlli ammessi,
   criteri di successo, bootstrap e guardia PDS.
2. Audit di tutte le esposizioni PIE: training, validation/checkpoint selection,
   memoria, annotazioni/DepMap e calibrazione. Cambiare split non disimpara pesi.
   `xdataset` include VCC25: non ammetterlo a H1 test per inferenza dal nome.
3. Definire/verificare il bridge di normalizzazione; `ln(2)` non basta.
4. Confrontare stesso supporto e pannello con fallback; sei membri e C/J separati,
   errore comune/specifico, correlazione degli errori, generic e target permutati.
5. Aggiornare README categoria e REGISTRO per questa cartella; checkpoint/STRADE
   solo quando si legge un esito scientifico. Non ho modificato documenti condivisi
   perché il mandato assegna quell'aggiornamento a VALIDAZIONE.

Nessuna predizione biologica congelata è ancora disponibile. I test non vengono
consegnati come predizioni scientifiche. Il pacchetto pronto per il freeze è
attualmente un componente sperimentale, non un candidato valutato.

## Dipendenze e permessi

- Comunicazioni DATI-TRANSFER/VALIDAZIONE autorizzate dal proprietario, dopo il
  primo rifiuto auto-review; scambio con DATI-TRANSFER riuscito.
- Drive autorizzato dal proprietario per lo spazio; lettura directory verificata.
- Richiesta esplicita pendente: acquisizione PIE 45,64 GB / ESM2 98,54 MB e prove
  cloud coordinate. Nessun acquisto, invio o push incluso.
- VALIDAZIONE non compare nelle prime due liste chat; chiesto nome/ID al proprietario.
- Ricevuta release T1 `277ae3441b78c9a1ebf79149cff914fb494d8fff09529b367e9f42cb6a76ffd8`:
  è produzione, non una nuova autorizzazione a usare risposte holdout.

Le condizioni di PIE e la licenza non esplicita dell'asset repository sono riportate
in `CANDIDATI.md`; l'ammissibilità dell'uso in gara non è stata risolta.
