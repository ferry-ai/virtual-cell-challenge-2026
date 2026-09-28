# Tahoe: estrazione dei controlli DMSO — 28 settembre 2026

## Evidenza pubblica

**measured — lettura della documentazione, non dei dati.** La
[dataset card](https://huggingface.co/datasets/tahoebio/Tahoe-100M/raw/main/README.md)
dichiara CC0, 50 linee, 95.624.334 righe, 337.644.770.670 byte compressi e
1.693.653.078.843 byte logici. Ogni riga rappresenta una cellula:

| Campo | Contratto documentato |
|---|---|
| `genes` | lista int64 di token, non indici contigui |
| `expressions` | lista float32 di conteggi grezzi, allineata ai token |
| primo elemento | marcatore, escluso dai conteggi |
| `drug` | controllo esatto `DMSO_TF` |
| `cell_line_id`, `plate` | Cellosaurus e piastra; mantenere entrambe |
| `sample`, `BARCODE_SUB_LIB_ID` | chiavi di campione e cellula |
| altri campi stringa | `moa-fine`, `canonical_smiles`, `pubchem_cid` |

La stessa fonte descrive i metadati: geni (`token_id`, `gene_symbol`,
`ensembl_id`); campioni (`sample`, `plate`, `drug`, concentrazione e medie QC);
farmaci (target, MOA, struttura); linee (nome, Cellosaurus, DepMap, tessuto,
mutazioni). Non documenta un conteggio di cellule per campione né una mappa
campione → shard. Le piastre sono indicate come 1–14.

**measured.** Il [tutorial ufficiale](https://huggingface.co/datasets/tahoebio/Tahoe-100M/raw/main/tutorials/loading_data.ipynb)
elimina il primo elemento **solo se `expressions[0] < 0`**; ordina il vocabolario
dei token e associa i conteggi alle colonne corrispondenti. Lo script segue
questa condizione, preservando un eventuale primo gene reale, e rifiuta token
sconosciuti invece di scartarli silenziosamente. La formulazione assoluta
della card e quella condizionale del tutorial non sono identiche: verificarle
sui dati reali resta necessario. Il tutorial usa ancora il vecchio nome
`vevotx`; lo script usa `tahoebio`.

**measured.** Il [listing data](https://huggingface.co/datasets/tahoebio/Tahoe-100M/tree/main/data)
mostra 338 GB e nomi `train-00000-of-03388.parquet`, `train-00001-of-03388.parquet`,
ecc.; prima shard 71,2 MB. **inferred:** 3.388 shard dal suffisso; la pagina
mostra solo le prime 50, quindi non è un censimento completo.

**measured.** Il [listing metadata](https://huggingface.co/datasets/tahoebio/Tahoe-100M/tree/main/metadata)
mostra `sample_metadata.parquet` 65,6 kB, `gene_metadata.parquet` 1,33 MB,
`cell_line_metadata.parquet` 19 kB, `drug_metadata.parquet` 40,5 kB,
`obs_metadata.parquet` **2,29 GB**, vocabolari JSON/JSONL e una cartella di DE
pseudobulk. Non confondere quest'ultima con somme grezze dei controlli.
Il [listing radice](https://huggingface.co/datasets/tahoebio/Tahoe-100M/tree/main)
riporta 429 GB complessivi e commit breve `2dc5790`; non è la dimensione dei soli
conteggi. Il codice non scarica `obs_metadata`, vocabolari o risultati DE.

## Limiti della verifica e stima prima dell'estrazione

**measured.** Python 3.14.4 non può aprire socket nel sandbox: il tentativo
`urllib.request.urlopen('https://huggingface.co/api/datasets/tahoebio/Tahoe-100M')`
ha restituito `WinError 10013`. Il web tool ha letto le pagine sopra, ma ha
restituito `Internal Error` per:

- [API del repository](https://huggingface.co/api/datasets/tahoebio/Tahoe-100M), anche con `?blobs=true`;
- [albero API](https://huggingface.co/api/datasets/tahoebio/Tahoe-100M/tree/main?recursive=true&limit=1000);
- [API metadata](https://huggingface.co/api/datasets/tahoebio/Tahoe-100M/tree/main/metadata);
- [preview campioni](https://datasets-server.huggingface.co/first-rows?dataset=tahoebio%2FTahoe-100M&config=sample_metadata&split=train).

**unverified:** schema fisico, numero/dimensione dei row group, statistiche
min/max, ordine delle cellule, numero effettivo di campioni/cellule DMSO,
copertura delle linee nei controlli, supporto HTTP Range del CDN. Nessuna shard
è stata scaricata; neppure i footer reali sono stati letti. Il runtime fissa
il commit completo via API, senza affidarsi al commit breve della pagina o
all'allineamento temporale delle cache web.

**inferred — limiti, non una stima puntuale misurata:** dalle informazioni
accessibili, controlli fra 0 e 95.624.334 cellule; lettura dei conteggi fra 0 e
circa **337,645 GB** più preflight. Non c'è una base verificata per promettere
«pochi GB» o un numero di controlli. Il campione finale è al massimo 3.000 per
linea (150.000 se le linee effettive sono 50). Il numero di campioni non è un
numero di cellule; assumere popolazioni uguali per pozzetto sarebbe arbitrario.

Il **preflight eseguibile prima dei conteggi** risolve questa incertezza:

1. Censisce l'API paginata, fissa la revisione, legge quattro piccoli metadati.
   Conserva schema e righe DMSO dei campioni in `metadata_audit.json`.
2. Per ogni shard legge trailer da 8 byte + footer Thrift; salva il footer.
3. Esclude row group con intervallo `drug` incompatibile con `DMSO_TF`.
   Se min=max=DMSO e null count noto, ricava il numero senza leggere le etichette.
   Negli altri casi legge **solo `drug`**, non geni/conteggi, e conta esattamente.
4. `plan.json` riporta `n_vehicle`, row group/shard selezionati,
   `extraction_column_bytes` (somma delle dimensioni compresse delle cinque
   colonne necessarie), byte effettivi e tempo del preflight.

**inferred:** costo preflight = footer + chunk `drug` non esclusi. Se i controlli
sono sparsi in tutti i row group, anche pochissimi controlli possono richiedere
quasi tutti i 338 GB dei conteggi: Parquet non permette di scaricare singole
righe arbitrarie di un chunk compresso. Non viene applicato alcun rapporto
«percentuale DMSO × dimensione totale». Il default `--max-read-gb 20` interrompe
prima dei conteggi quando il piano supera 20 GB decimali; questa soglia riguarda
il traffico previsto, non i 20 GB di disco Kaggle. Non esiste fallback che
scarichi automaticamente tutte le shard.

## Esecuzione Kaggle e ripresa

Caricare questo script nel notebook; internet attivo, nessun token necessario:

```bash
pip install numpy pyarrow
python extract_dmso.py --selftest
python extract_dmso.py --out /kaggle/working/tahoe_dmso --plan-only
python extract_dmso.py --out /kaggle/working/tahoe_dmso --cells-per-line 3000 --max-read-gb 20
```

**inferred:** se il piano supera la soglia, Claude1 deve valutare il costo e
scegliere un limite esplicito compatibile con il job. Il piano non garantisce
il completamento entro 12 ore: latenza di molte richieste Range e distribuzione
dei row group non sono misurate. Una risposta HTTP che ignora Range causa un
errore prima di leggere il corpo; niente download completo involontario.

**measured — implementazione:** estrae solo i row group positivi, filtra ancora
`drug`, elabora batch di 256 righe e somma tutti i conteggi validi in uint64.
I geni duplicati nella stessa cellula vengono coalesciuti; geni non presenti
nella cellula restano zero sull'intero asse `gene_metadata`. Il campionamento
bottom-k per linea usa priorità hash pseudocasuali con seme e posizione stabile
shard/row-group/riga; è uniforme sotto l'assunzione di hash uniforme, senza
bilanciamento forzato per piastra. I campi di origine restano disponibili.

SQLite conserva somme e campione globale in una transazione per shard. Dopo
interruzione, la shard incompleta si rilegge, quelle concluse si saltano. Anche
il piano riparte dalle shard concluse. Mantenere **l'intera cartella** fra sessioni
Kaggle; il disco effimero di una nuova sessione non contiene i checkpoint.
Una sola istanza alla volta. Cambiare seme, limite di campionamento o revisione
richiede una nuova destinazione. Gli NPZ finali sono scritti atomicamente e il
manifest completo viene scritto per ultimo.

| Output | Contenuto |
|---|---|
| `pseudobulk.npz` | `sums[group,gene]`, `n_cells`, `library`, `cell_line`, `plate`, `token_id`, `gene_symbol`, `ensembl_id` |
| `cells.npz` | CSR `data`, `indices`, `indptr`, `shape`, `format`; `cell_line`, `plate`, `cell_id` e stesso asse geni |
| `manifest.json` | commit, fonti, shard/byte/tempi, cellule totali e campionate per linea, stato completo |
| `state.sqlite` | checkpoint transazionale; necessario alla ripresa |
| `plan.json`, `inventory.json`, `metadata/`, `metadata_audit.json` | piano riprendibile, provenienza e metadati |

`cell_id` è una posizione sorgente, non `BARCODE_SUB_LIB_ID`. Si può aprire il CSR
con `scipy.sparse.load_npz`, oppure costruirlo dai tre array senza SciPy durante
l'estrazione. Nessun array pickle. Il manifest distingue byte delle shard
concluse dai byte di questa invocazione: API/metadati piccoli, tentativi falliti
e shard interrotte non fanno parte del totale cumulativo. Il tempo cumulativo
copre pianificazione/estrazione concluse, non export o tentativi falliti.

**unverified:** picco RAM/disco con i dati reali. Per N cellule campionate e z geni
nonzero medi, i soli array CSR occupano circa `12*N*z + 8*(N+1)` byte (conteggi
uint64, indici int32). Per 150.000 cellule e z=3.000 **ipotetico**, sono 5,4 GB;
SQLite, journal, NPZ temporanei e overhead aggiungono spazio. Nessuna garanzia
dei 20 GB di output o 30 GB RAM senza misurare z. Non viene conservato il dataset
di espressione completo.

## Verifiche locali e integrazione

**measured.** Il Python di progetto dispone di numpy 2.5.3, pyarrow 25.0.1,
pandas 3.0.5; il Python globale non dispone di numpy. Comando:

```powershell
.\scripts\py.cmd reports/tahoe_dmso_2026-09-28/extract_dmso.py --selftest
```

Output:

```text
SELFTEST PASS: 2 shards, 5 vehicle cells, 3 line/plate groups, 4 sampled cells; CLS, duplicate tokens, absent statistics, mixed groups, rollback/resume and deterministic sampling verified
```

Il test usa le dieci colonne documentate, tipi Arrow reali, due shard, gruppi
misti/esclusi e statistiche assenti. Verifica somme esatte, librerie, limite del
campione, rollback di una shard interrotta e identità del campione dopo ripresa.
Un trasporto locale che implementa Range verifica che PyArrow con footer fornito
legga solo il chunk `drug` previsto, senza prefetch del resto del file. Una
risposta HTTP 200 simulata verifica il rifiuto prima della lettura del corpo
quando Range viene ignorato. Non prova il comportamento del CDN reale.

**measured.** `python scripts/31_check_docs.py` segnala la mancata registrazione
dei nuovi file. Il vincolo del task «new files only, in the new folder» prevale:
non sono stati modificati `docs/REGISTRO.md`, `reports/CLAUDE.md` o schede di piano.
Claude1 deve aggiungere la voce di cartella al registro e all'indice reports
quando integra. Nessun job Kaggle avviato, nessun modello addestrato e nessuna
prova di miglioramento del context encoder.

**measured.** `.\scripts\py.cmd -m unittest discover -s tests`: 203 test in
364,965 secondi, 201 superati, un fallimento e un errore. Il fallimento è
`test_this_repository_is_consistent` (registro mancante; al momento del suo
controllo esisteva solo il nuovo script). L'errore è
`test_components_reproduce_the_scored_fidelity`: dipendenza
`cell_eval2.config` non disponibile. Nessuna modifica a quelle dipendenze o ai
test di progetto. Il successivo controllo documentale vede entrambi i file
nuovi non registrati; `git diff --check` non segnala errori nei file tracciati.
