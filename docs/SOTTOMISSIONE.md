Convalida e invio di una sottomissione
======================================

Aggiornato il 2026-09-13. Introdotto da
[CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md), esteso con il percorso
di packaging da [CP-0005](checkpoints/0005-packaging-streaming-trial01.md).

**Una sottomissione è stata inviata e valutata**, il 2026-09-13: entry
`PNn227rxP3bVByS37W41`, punteggio **0,045929**, rango **446 su 920 squadre**. Il
resoconto completo è nella sezione 4 e in
[`submission_PNn227rxP3bVByS37W41.md`](../reports/trial_2026-09-13/submission_PNn227rxP3bVByS37W41.md);
il checkpoint è [CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md).
Era `trial-01-transfer`; **`trial-00-controls` non è stato inviato** e non va inviato
(D-017).

> **`trial-01-transfer` è impacchettato; `trial-00-controls` no, e non deve esserlo.**
> Il `.vcc` di trial-01 è stato prodotto il 2026-09-13 con
> `scripts/48_package_prediction.py`, che convalida e scrive **senza caricare la
> matrice**: 0,519 GiB di picco contro i 33,5 che il modello della CLI attribuisce a
> `vcc prep`. Tutte e 24 le convalide attive, payload verificato bit a bit contro
> l'input. Evidenza:
> [`k01pack_packaging.json`](../reports/trial_2026-09-13/k01pack_packaging.json),
> [CP-0005](checkpoints/0005-packaging-streaming-trial01.md).
>
> `vcc prep` continua a non girare qui, ed è documentato in
> [`q01prep_prep_dry_run.log`](../reports/trial_2026-09-12/q01prep_prep_dry_run.log).
> Non serve più: le sue convalide sui metadati sono importate e chiamate dal nostro
> percorso, e la parità sui rifiuti è dimostrata da 41 test su fixture a forma
> ufficiale completa (D-019).
>
> **Il server ha accettato**, il 2026-09-13: la sottomissione è arrivata a `published`
> con `md5_verified: true` ed `error_info: null`. Il percorso di packaging in streaming
> è confermato end-to-end. Resta vero che un `.vcc` valido è un'affermazione sul
> **formato**: il punteggio, misurato, è 0,046.

## 1. Il contratto, verificato oggi

Ogni riga viene dalla pagina ufficiale *Evaluation* di virtualcellchallenge.org
(consultata il 2026-09-12), dalle FAQ ufficiali, o da `vcc prep --help` della CLI
installata (`vcc 0.2.0`). Le prime due sono la fonte; la CLI è ciò che il server usa
per rifiutare.

| Requisito | Valore | Dove è scritto |
|---|---|---|
| Un solo file per tutti e tre i contesti | non uno per contesto | Evaluation, FAQ "Do I submit one file per cell context?" |
| Colonna delle perturbazioni in `.obs` | `target_gene`, simboli (`ADNP`), non id di costrutto | Evaluation |
| Colonna del contesto in `.obs` | `context`, etichette identiche a quelle dei file di controllo | Evaluation |
| Perturbazioni | esattamente quelle di `pert_counts.csv`, per ogni contesto; una in più viene rifiutata | Evaluation |
| Cellule per perturbazione | esattamente 400, in ogni contesto | Evaluation |
| Geni in `.var` | esattamente 18.533, nell'ordine di `gene_names.csv` | Evaluation |
| `.X` | conteggi grezzi: non negativi, interi, finiti. Niente `normalize_total`, niente `log1p` | Evaluation, FAQ |
| Righe di controllo | **vietate**: nessuna riga `non-targeting`. I controlli scaricati sono soltanto input del modello | Evaluation |
| Valori memorizzati in `.X` | al massimo 4.750.000.000 in tutto, circa 13.200 per cellula a 360.000 cellule. Conta ciò che la matrice *memorizza*, quindi anche uno zero salvato esplicitamente | Evaluation, FAQ "rejected as too dense" |
| Conteggi per cellula | nessuna cellula oltre 1.000.000 sommando i geni | Evaluation |
| Forma attesa | 360.000 × 18.533 = 300 perturbazioni × 400 cellule × 3 contesti | Evaluation |
| Sottomissioni al giorno | **due** per squadra, il giorno cambia a mezzanotte UTC; contano solo quelle che arrivano al punteggio; una sola in volo alla volta | Rules, Evaluation |
| Codice e pesi | **non** vanno consegnati. Solo i finalisti devono fornire una descrizione di alto livello che verrà pubblicata (dataset usati, preprocessing, modelli, componenti non appresi, fasi di training; il compute è opzionale) | Rules §"Finalists, Winners, and Prizes"; FAQ "Am I required to submit my code?" |
| Dati esterni | ammessi, se se ne hanno i diritti; Arc non li richiede | FAQ "Can I use other data…" |
| Predizioni | devono essere generate **soltanto** da modelli di machine learning. Vietato inviare risultati sperimentali o di letteratura come parte della predizione (usarli per allenare è invece ammesso) | Rules §"Machine Learning Predictions Only" |

Confermato anche dal bundle locale: `raw/controls/manifest.json` dichiara
`partition: val`, `panel_id: vcc2026-val-1`, `cells_per_pert: 400`, 46 `ntc_id` per
contesto e 18.400 cellule di controllo per contesto.

Verifiche di sola lettura sull'account, eseguite il 2026-09-12 con
`vcc whoami --json`: profilo `default`, endpoint di produzione, token dal keyring,
account attivo e verificato, `can_submit: true`, `blockers: []`, squadra presente.
**Nessun token è stato stampato, copiato o scritto in un file di questo repository.**

## 2. Le due domande da risolvere prima di inviare trial-00

`trial-00-controls` è un ricampionamento delle cellule di controllo reali etichettate
con le perturbazioni richieste. `vcc prep` lo accetta — non contiene righe
`non-targeting` e formalmente è in regola — ma due frasi delle regole ufficiali lo
riguardano direttamente:

1. «The control cells you downloaded are model inputs only — do not copy them into
   your prediction.» (pagina Evaluation)
2. «your predictions must be generated solely by one or more machine learning
   models you use.» (Rules)

Un ricampionamento non è una previsione di un modello. **Non inviare trial-00 senza
aver chiarito questo punto** con help@virtualcellchallenge.org, o senza la decisione
esplicita del proprietario del progetto. Il pacchetto esiste perché serve come
controllo operativo locale e come riferimento di dispersione: è reale, quindi la sua
variabilità fra cellule è giusta per costruzione. Questo non lo rende inviabile.

`trial-01-transfer` non ha questo problema: è la risposta prevista da un modello
calibrato, applicata al profilo basale del contesto.

## 3. Comandi esatti, per Windows

Percorsi di questa macchina; `<run>` è la cartella del run sotto
`C:\Users\ferra\vcc2026-data\artifacts\`.

### Rigenerare tutto da zero

`$RUN` è l'id del run nuovo, e **il passo 3 usa lo stato fittato del passo 2, non
quello di un run precedente.** Un comando che rigenera la calibrazione e poi punta a
`c002` produrrebbe una previsione che non corrisponde alla calibrazione appena
eseguita, e nulla se ne accorgerebbe: i due file hanno la stessa forma.

```powershell
$RUN  = "r001"                                   # scegline uno nuovo
$ART  = "C:\Users\ferra\vcc2026-data\artifacts"
$SIGS = "$ART\e001\signatures"

# 1. congela lo stato (commit, patch, snapshot del codice, hash degli input, seed)
.\scripts\py.cmd scripts/43_freeze_trial.py --run-id $RUN --trial trial-01-transfer

# 2. calibra ampiezza e shrinkage in validazione incrociata annidata
.\scripts\py.cmd scripts/44_calibrate_transfer.py --run-id $RUN `
    --signatures $SIGS --outer-folds 5 --inner-folds 4 --n-boot 1000

# 3. genera la previsione completa (300 x 400 x 3) CON LA CALIBRAZIONE DEL PASSO 2
.\scripts\py.cmd scripts/45_generate_prediction.py --run-id $RUN `
    --trial trial-01-transfer `
    --fitted-state "$ART\$RUN\fitted_state.json" `
    --signatures $SIGS

# 4a. verifica locale del contratto e della provenienza, senza toccare la CLI.
#     Rilegge il file a blocchi: gira ovunque, picco sotto 1 GiB.
#     Esce con codice != 0 se un controllo fallisce, e in quel caso non impacchetta.
.\scripts\py.cmd scripts/46_validate_package.py --run-id $RUN --skip-prep

# 5. impacchetta in .vcc senza caricare la matrice (questo è il percorso che funziona
#    su questa macchina; vedi la sezione 7)
.\scripts\py.cmd scripts/48_package_prediction.py --run-id $RUN `
    --prediction "$ART\$RUN\prediction.h5ad"
```

Per **riusare** una calibrazione esistente invece di rifarla, si salta il passo 2 e si
punta esplicitamente al run che l'ha prodotta — per esempio
`--fitted-state "$ART\c002\fitted_state.json"`. Lo stadio 45 rifiuta di girare se lo
sha256 delle firme non corrisponde a quello su cui i parametri sono stati scelti,
quindi un accoppiamento sbagliato fra calibrazione e firme si ferma da solo; un
accoppiamento sbagliato fra calibrazione e *previsione* no, ed è per questo che il
comando qui sopra non nomina un run diverso da `$RUN`.

Per il controllo: `--trial trial-00-controls` ai passi 1 e 3, senza `--fitted-state`.
Per un pilota: `--n-perts 6` al passo 3. Un pilota **non** si invia, e `vcc prep` lo
rifiuta da sé perché mancano 294 perturbazioni su 300.

Il passo 4a scrive `validation_<AAAAMMGGTHHMMSSZ>.json` e i log con lo stesso
suffisso: un secondo tentativo sullo stesso run **non** sovrascrive l'evidenza del
primo. Con `--attempt <etichetta>` si sceglie il suffisso.

### Convalidare a mano, senza lo script

```powershell
.\scripts\vcc.cmd prep C:\Users\ferra\vcc2026-data\artifacts\<run>\prediction.h5ad `
    -g C:\Users\ferra\vcc2026-data\raw\controls\gene_names.csv `
    --perts C:\Users\ferra\vcc2026-data\raw\controls\pert_counts.csv `
    --dry-run --json
```

```powershell
.\scripts\vcc.cmd prep C:\Users\ferra\vcc2026-data\artifacts\<run>\prediction.h5ad `
    -g C:\Users\ferra\vcc2026-data\raw\controls\gene_names.csv `
    --perts C:\Users\ferra\vcc2026-data\raw\controls\pert_counts.csv `
    -o C:\Users\ferra\vcc2026-data\artifacts\<run>\prediction.vcc
```

I limiti di convalida non si aggirano. `--no-verify-targets`,
`--no-check-cell-counts`, `--expected-gene-dim -1`, `--max-nnz -1` esistono per casi
diagnostici: usarli per far passare un file che il server rifiuterebbe sposta
l'errore dal proprio terminale alla quota giornaliera.

### Inviare — **non ancora autorizzato, e non ancora possibile**

I comandi seguenti consumano quota. Vanno eseguiti solo dopo l'autorizzazione
esplicita del proprietario del progetto.

Il primo punta a un file che **esiste**: 3,91 GiB, sha256 `681b0aac…a1a2a6`. Il
secondo punta a un file che **non è stato creato**, e non va creato finché la sezione
2 non è risolta.

```powershell
.\scripts\vcc.cmd submit C:\Users\ferra\vcc2026-data\artifacts\k01pack\prediction.vcc `
    -m "trial-01-transfer shrunk k562 a=0.197 sd=4" `
    -d "ShrunkTransfer da K562 genome-wide; alpha e prior_sd scelti in CV annidata su bersagli tenuti fuori nell'esperimento K562->RPE1. Nessun dato perturbato dei contesti ufficiali." `
    --json --wait
```

```powershell
.\scripts\vcc.cmd submit C:\Users\ferra\vcc2026-data\artifacts\q00full\prediction.vcc `
    -m "trial-00-controls resampling NTC per contesto" `
    -d "Ricampionamento delle cellule di controllo reali entro contesto, etichettate con le perturbazioni richieste. Nessun modello. Vedi docs/SOTTOMISSIONE.md sezione 2 prima di inviare." `
    --json --wait
```

Una sola sottomissione in volo per squadra: una seconda durante la prima restituisce
HTTP 409. Non è un errore da ritentare, è la regola.

### Leggere stato e punteggi

```powershell
.\scripts\vcc.cmd status <entry-id> --json
```

```powershell
.\scripts\vcc.cmd status <entry-id> --wait --poll-interval 30 --json
```

Il JSON va salvato così com'è, senza riscriverlo:

```powershell
.\scripts\vcc.cmd status <entry-id> --json | `
    Out-File -Encoding utf8 C:\Users\ferra\vcc2026-data\artifacts\<run>\status_<entry-id>.json
```

`--wait` esce con codice diverso da zero se il punteggio fallisce. Un fallimento è un
fallimento: si registra con l'id e il testo dell'errore, non si archivia come
problema noto del backend.

## 4. Trovare la voce nel portale, e cosa registrare

`vcc submit` stampa l'**entry id**: è l'unico identificatore che collega il file
locale alla riga del portale, e va scritto nel manifesto del run appena arriva. Con
`--json` sta nel campo dell'oggetto restituito; senza, nel testo. La voce si ritrova
poi su virtualcellchallenge.org → *Leaderboard* cercando il **model name** passato con
`-m`, che è ciò che compare in classifica assieme al nome della squadra
(`Mandolino` al 2026-09-13; il nome della squadra può cambiare, l'entry id no) — motivo per cui il nome del modello deve identificare il trial,
non essere generico.

Da registrare, in un file nuovo per ogni sottomissione (mai sovrascrivendone uno):

| Campo | Da dove |
|---|---|
| entry id | output di `vcc submit` |
| model name e description | quelli passati a `-m` e `-d` |
| file inviato, byte, sha256 | `validation.json` del run |
| run id e commit | `freeze.json` del run |
| timestamp dell'invio (UTC) | orologio locale al momento dell'invio |
| punteggio complessivo | `vcc status --json` |
| sei punteggi per metrica | `vcc status --json`: le intestazioni di leaderboard sono `pds`, `mse`, `nmae`, `fid`, `reach`, `jac` |
| partizione | `val` per questa fase; `raw/controls/manifest.json` campo `partition` |
| pannello | `vcc2026-val-1`, da `raw/controls/manifest.json` campo `panel_id` |
| insieme di ancore | campo `anchor_version` di `vcc status`. Per la partizione `val` al 2026-09-13: `vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4`. I valori numerici di `b` e `r` restano non esposti, ma la classifica pubblica mostra grezzo e scalato per ogni riga, il che li rende in linea di principio ricavabili ([CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) §3.5) |
| posizione in classifica | pagina Leaderboard, con l'ora della lettura |
| timestamp della lettura | orologio locale |

I nomi dei campi di `vcc status --json`, osservati il 2026-09-13 su una risposta reale:
`entry_id`, `status`, `model_name`, `description`, `is_final`, `submission_date`,
`error_info`, `rank`, `score_avg`, `is_terminal`, `partition`, `panel_id`,
`anchor_version`; le sei **grezze** `pds_cosine`, `expr_mse_unbiased_capped_norm`,
`de_wilcoxon_lfc_nmae`, `de_wilcoxon_direction_fidelity_yield_raw`,
`de_wilcoxon_direction_reach_raw`, `de_wilcoxon_sig_jaccard`; le sei **scalate**
`score_pds`, `score_mse`, `score_nmae`, `score_fid`, `score_reach`, `score_jac`. I campi
`de_score`, `pert_score` e `mae_score` sono tornati `null`.

Si continua a salvare il JSON grezzo, verbatim, e a leggere i campi da lì.

### Compilato: la sottomissione del 2026-09-13

| Campo | Valore |
|---|---|
| entry id | `PNn227rxP3bVByS37W41` |
| model name | `trial-01-transfer k01pack a=0.197 sd=4` |
| file, byte, sha256 | `k01pack/prediction.vcc`, 4.203.520.000, `681b0aac…a1a2a6` |
| run e commit | `k01pack`; codice in `reports/trial_2026-09-13/source_snapshot.tar.gz` |
| inviata (UTC) | 2026-09-13T01:12:02Z |
| **complessivo** | **0,045929** |
| `pds` / `mse` / `nmae` | 0,413315 / 0,000000 / 0,026833 |
| `fid` / `reach` / `jac` | −0,182476 / 0,021322 / −0,003417 |
| partizione / pannello | `val` / `vcc2026-val-1` |
| ancore | `vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4` |
| rango | **446 su 920 squadre** |
| letto (UTC) | 2026-09-13T01:44:48Z |

## 5. Punteggi ufficiali contro metriche locali

Non sono la stessa cosa e non vanno messi nella stessa tabella.

**Il punteggio ufficiale** è riscalato: per ogni metrica e ogni contesto, 0 è la media
del contesto e 1 è «buono come un replicato reale», calcolato come media di cinque
metà disgiunte dei dati veri. Il punteggio complessivo è la media non pesata delle sei
metriche sui tre contesti. 1 non è il massimo e non è una percentuale: cinque delle sei
metriche non hanno tetto, quattro non hanno pavimento, e solo `mse` è limitata a 0–1.
Un punteggio negativo vuol dire «peggio della media del contesto», non «errore».

**Le nostre metriche locali** sono di due tipi, entrambi diversi da quello sopra:

- Le metriche *proxy* in spazio pseudobulk log2FC di
  `44_calibrate_transfer` — MSE rispetto al nullo, Pearson per bersaglio, accordo di
  segno. Sono su K562 e RPE1, non sui contesti ufficiali, e non passano dallo scorer.
- Le metriche *grezze* dello scorer vero in `42_null_calibration`, che girano
  `cell-eval2` ma su un riferimento il cui effetto è zero per costruzione e senza le
  ancore `b` e `r`, quindi `score_bundle` marca `normalized: false`.

**Nessuna delle due si converte nell'altra, e nessuna delle due predice il punteggio
della gara.** Il benchmark esterno (K562→RPE1) è un esperimento diverso su linee
cellulari diverse: dire che una riduzione dell'1,0% dell'MSE pseudobulk «vale» un
certo punteggio VCC sarebbe inventare una conversione che non abbiamo misurato.
Validazione e test finale, fra loro, non sono nemmeno confrontabili: linee diverse,
pannelli diversi, e `pds` è un rango dentro il proprio pannello.

## 6. Prima di inviare, la lista

1. `.\scripts\py.cmd scripts/46_validate_package.py --run-id <run> --skip-prep` è
   passato, **con codice di uscita 0**: tutti i controlli di contratto e la provenienza
   dei contesti. **Fatto** per entrambi i trial il 2026-09-12: 18 controlli su 18.
2. `.\scripts\py.cmd scripts/48_package_prediction.py` è passato, **con codice di
   uscita 0**: 24 convalide su 24, validatore ufficiale del contenitore superato,
   payload confrontato con l'input. **Fatto per `trial-01-transfer`** il 2026-09-13.
3. `prediction.vcc` esiste, con sha256 e dimensione in `packaging.json`. **Fatto per
   `trial-01-transfer`**: 4.203.520.000 byte, sha256 `681b0aac…a1a2a6`, da un input
   `1b7e15f4…c091e2` verificato invariato *dopo* il packaging. Per
   `trial-00-controls`: **non fatto di proposito**, vedi la sezione 2 e D-017.
4. La verifica di provenienza dice che ogni contesto è più vicino al proprio basale.
   `vcc prep` non se ne accorgerebbe: un contesto scambiato somiglia a un modello
   debole, non a un errore.
5. Il model name identifica il trial e il run.
6. La quota del giorno non è esaurita e non c'è un'altra sottomissione in volo.
7. Per trial-00: la sezione 2 di questa pagina è stata risolta.

## 7. Il packaging a memoria limitata

`vcc prep` è l'autorità sul formato, e questo percorso non la sostituisce: le sue
convalide sui metadati sono **importate e chiamate**, non riscritte. Ciò che sostituisce
è la riga che lo rende inutilizzabile qui — `adata = read_h5ad(input_path)`, prima di
qualunque convalida.

```powershell
.\scripts\py.cmd scripts/48_package_prediction.py `
    --run-id NUOVO `
    --prediction C:\Users\ferra\vcc2026-data\artifacts\<run>\prediction.h5ad `
    --expect-sha256 <sha256 atteso>
```

Tre fasi, riportate separatamente perché stabiliscono cose diverse:

1. **convalida** — 24 controlli, a blocchi di righe. Un esito pulito è un'affermazione
   sul **formato** e su nient'altro.
2. **packaging** — payload → zstd livello 3 → tar con `meta.json` per primo, metadati
   dei membri normalizzati (uid/gid 0, nomi vuoti, mtime 0), come fa `_write_vcc`.
3. **verifica** — validatore ufficiale del contenitore, poi il payload estratto in
   streaming e confrontato **con l'input**, array per array.

Opzioni che contano:

| Opzione | A che serve |
|---|---|
| `--expect-sha256` | rifiuta di partire se l'input non è il file atteso |
| `--workdir` | dove finiscono i transitori (payload e payload compresso, circa 4 GiB ciascuno). Su un host con poco output persistente e molto scratch — Kaggle — si punta allo scratch e il `.vcc` resta nella cartella del run |
| `--values-per-block` | valori memorizzati per blocco. Governa il picco di memoria, che non dipende dalla dimensione della matrice |
| `--validate-only` | convalida senza scrivere |

Misurato su `trial-01-transfer` il 2026-09-13
([`k01pack_packaging.json`](../reports/trial_2026-09-13/k01pack_packaging.json)):

| | Valore |
|---|---|
| picco di memoria | **0,519 GiB** (modello per `vcc prep`: 33,49 GiB) |
| picco di disco transitorio | 7,88 GiB |
| convalida / packaging / verifica / totale | 156 s / 756 s / 216 s / 1.005 s |
| archivio | 4.203.520.000 byte, sha256 `681b0aac…a1a2a6` |

### Che cosa cambia nel payload, e che cosa no

`X/data`, `X/indices` e `X/indptr` sono **identici bit a bit** all'input, dtype
compresi. L'asse genico e le etichette per cellula sono identici. L'unica
trasformazione è l'**indice di `obs`**, sostituito con `'0'..'n-1'` — ed è quella che
applica anche `vcc prep`, il cui `new_obs` usa `index=np.arange(n_cells).astype(str)`.
Il nome originale della cellula non entra in un `.vcc` per nessuna delle due strade.
`payload_transformations()` restituisce l'elenco completo come dati.

### Che cosa viene rifiutato invece di approssimato

Matrice densa, CSC, dtype diverso da float32, geni fuori ordine, percorso
log-normalizzato, colonna di tipo cellulare. Ognuno con il motivo e con `vcc prep`
indicato come lo strumento che li gestisce, su una macchina abbastanza grande.

### Se servisse una macchina remota

`notebooks/kaggle_package_trial01.ipynb` esegue la stessa implementazione su Kaggle CPU.
Non è stato eseguito — il run locale è riuscito — e resta per il set finale D/E/F. Il
trasferimento dell'input è a carico del proprietario, in un **dataset Kaggle privato**;
il notebook riverifica lo sha256 dopo il trasferimento e rigira i test di parità su
quella macchina prima di produrre qualcosa.
