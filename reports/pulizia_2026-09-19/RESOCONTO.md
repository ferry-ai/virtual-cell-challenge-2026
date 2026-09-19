# Resoconto della pulizia del codice — 19 settembre 2026

**Dove:** branch `refactor/pulizia`, worktree `../vcc2026-refactor`. Nessun push, nessun
merge su `main`. Il branch parte da `4cdb618`, contiene i tre commit del 18 settembre e
il merge di `main` a `ec980b4` (lavoro della notte del 19), così la pulizia agisce
sull'albero corrente, script 95 compreso.

**Regole rispettate:** nessun test modificato, nessuno script numerato rinominato,
nessun flag cambiato, nessun docstring o commento di metodo cancellato. Non ho toccato
`scripts/82_*`, `84_*`, `94_*`, `src/vcc2026/bench_score.py` (t07 non ancora registrata),
né `docs/checkpoints/*`. `notebooks/colab_jobs/sync_to_drive.ps1` non è stato eseguito.

**Nessun refactor ha richiesto di cambiare un test.** Se fosse successo, mi sarei
fermato: non è successo.

Il lavoro del 18 settembre (import inutilizzati, tre copie di `_md5_file`) è raccontato
in `PULIZIA_2026-09-18.md` nella radice, e non è ripetuto qui.

---

## 1. Righe prima e dopo

File `.py` tracciati, contati con `git ls-files … | xargs wc -l` prima del primo commit
di oggi (`7391e69`) e dopo l'ultimo (`b7e83ed`).

| Cartella | File | Righe prima | Righe dopo | Δ | Byte prima | Byte dopo | Δ byte |
|---|---:|---:|---:|---:|---:|---:|---:|
| `src/` | 72 | 24.014 | 24.055 | **+41** | 1.040.904 | 1.040.960 | +56 |
| `scripts/` | 80 | 18.245 | 18.127 | **−118** | 838.783 | 831.852 | −6.931 |
| `tests/` | 18 | 8.956 | 8.956 | 0 | 430.251 | 430.251 | 0 |
| **totale** | **170** | **51.215** | **51.138** | **−77** | 2.309.938 | 2.303.063 | −6.875 |

`src/` cresce di 41 righe perché è lì che sono andate a vivere le funzioni condivise,
con la spiegazione che le copie non avevano; `scripts/` cala di 118.

**Va detto chiaro: −77 righe su 51.215 è lo 0,15%, e non è la riduzione sostanziale
chiesta.** Il §5 dice dove sono davvero le righe (circa 17.000, un terzo del codice) e
perché non le può togliere un agente: non è una questione di coraggio, è che il
controllo documentale del progetto lo vieta in modo verificabile.

---

## 2. Commit per commit

### `6040bec` — un solo lettore di righe h5ad, nella libreria (−33)

`read_rows` era scritta quattro volte. Tre (stadi 75, 92, 95) leggono una `X` densa a
blocchi e differiscono in dettagli: 75 non ordina il blocco, 92 sì, 95 riceve un dataset
già aperto invece di un percorso. Ora chiamano `sc_stream.read_rows`, che accetta
percorso o dataset e ordina ogni blocco. **L'ordinamento non cambia niente**: tutti e tre
i punti di chiamata costruiscono le righe con `np.flatnonzero` o `np.sort`
(`75:189`, `92:135`, `92:338`, `95:61`, `95:64`), quindi erano già crescenti.

Lo stadio 42 è il quarto ed è un altro animale: legge un file **sparso** CSR riga per
riga, cioè quello che `inference.read_csr_rows` già fa, con in più ordine e duplicati
conservati. Le sue righe vengono da `rng.choice(replace=False)` e le ordinava da sé,
quindi la chiamata passa `np.sort(pick)`.

Verificato sui file veri, non solo con la suite:

```
context_A.h5ad, righe estratte non ordinate come fa lo stadio 42
    1 righe: identiche=True  shape=(1, 18533) nnz=5381
   64 righe: identiche=True  shape=(64, 18533) nnz=388335
 4000 righe: identiche=True  shape=(4000, 18533) nnz=23994723
   (data, indices, indptr e dtype confrontati uno per uno)

NadigOConner2024_hepg2.h5ad, 145.473 righe, 1500 righe lette
 block= 4096: nuova==75 True | nuova==92 True | nuova(dataset)==95 True | path==dataset True
 block=  512: nuova==75 True | nuova==92 True | nuova(dataset)==95 True | path==dataset True
```

### `af36846` — una sola porta sui file bulk Replogle (+2)

Le stesse otto righe aprivano `*_raw_bulk_01.h5ad` in sette posti (stadi 75, 76, 77, 80,
86, 92, 95) più `predictor_sc.common_from_bulk`. La regola che trasforma l'etichetta
`gene_transcript` in `(is_ntc, simbolo)` era scritta **otto volte**.

`predictor_sc` ora esporta `bulk_symbols(labels)` e `read_bulk(path)`, che restituisce
`(means, cells, sym, ntc, names)` nell'ordine che `effects_from_bulk` vuole. Chiamano
`read_bulk` gli stadi 75, 92, 95 e `common_from_bulk`; chiamano solo `bulk_symbols` gli
stadi 76, 80, 86 e 77, che leggono un sottoinsieme di righe o non leggono `X`.

**Questo commit è +2 righe nette**, ed è il prezzo dichiarato: otto copie di una regola
diventano una, e la funzione condivisa porta la nota «medie e non somme» (CP-0003 §3.1)
che nessuna delle copie aveva. Il guadagno non è in righe, è che la regola ora si può
sbagliare in un posto solo.

Verificato su `K562_essential_raw_bulk_01.h5ad` e `rpe1_raw_bulk_01.h5ad`: `means`,
`cells`, `sym`, `ntc`, `names` identici al blocco in linea, e `effects_from_bulk` su 40
bersagli dà uno `shrunk` identico. Una sola avvertenza, registrata perché è il tipo di
cosa che si scambia per un errore: `cells` risulta uguale solo con `equal_nan=True`,
perché contiene 12 NaN; i due array sono **identici byte per byte** (`tobytes()`).

### `ba8ed5d` — `load_effects` accanto al banco che la usa (−22)

Venti righe identiche byte per byte negli stadi 73 e 75 (verificato con `diff` delle due
copie contro quella spostata: «IDENTICA» in entrambi i casi). Ora sta in
`vcc2026.bench`, da cui i due stadi già importavano `log`.

### `b7e83ed` — quattro definizioni che nessuno raggiunge (−24)

Ciascuna controllata con `grep` su tutto il repository — test, notebook, configurazioni,
`docs/` e `reports/` compresi: nessun chiamante e nessuna citazione in un report o in un
documento.

| Definizione | Righe | Perché è morta |
|---|---:|---|
| `benchmark/models.py prediction_on_axis` | 10 | il suo unico riferimento era un import mai usato in `run.py`, tolto il 18 settembre |
| `research/campaign.py is_research_brief` | 2 | la stessa domanda la fa in linea `brief.mode == "scientific_research"` in cinque punti; questa leggeva `brief.raw` |
| `research/campaign.py campaign_id` | 2 | un identificatore che nessuno costruisce |
| `sc_stream.py write_json` | 2 | un involucro di `json.dumps` senza chiamanti |

Con loro se ne vanno gli import che servivano solo a loro: `Prediction` in `models.py`,
`short_id` in `campaign.py`, `json` in `sc_stream.py`.

---

## 3. Duplicazioni che ho lasciato stare, e perché

Questa sezione è un risultato, non una scusa: **le copie rimaste sono andate alla
deriva**, e unificarle cambierebbe il comportamento in un caso limite. Una copia che si
comporta diversamente dall'originale è più pericolosa di due copie identiche, perché
nessuno se lo aspetta.

| Duplicazione | Dove | La differenza che impedisce di unirle |
|---|---|---|
| `_fmt` | `scripts/69:38` e `benchmark/evaluate.py:275` | la versione della libreria stampa «—» per un valore non finito, quella dello stadio 69 stamperebbe `inf`. Lo stadio 69 ha prodotto `reports/expression_gate_2026-09-16/` |
| `_table` | `orchestrator/report.py:39` e `research/dossier.py:439` | una fa `str(cell)`, l'altra no: su una cella non stringa una funziona e l'altra solleva |
| `bh` | `scripts/19:37` e `de_tools.py:196` | `np.clip(q, 0, 1)` contro `np.minimum(adj, 1.0)`: stesso risultato per p in [0,1], non per un input negativo |
| scrittura di `gene_mask.npz` | `remote_catalog.py:519` e `remote_ingest.py:230` | politica di sovrascrittura opposta: `if not exists` contro `raise FileExistsError` |
| blocco attorno a `delta_from_pseudobulk` | `scripts/53:243` e `pseudobulk.py:245` | contorni diversi (accumulatori per bersaglio contro lettura a blocchi) e il risultato sono **firme**, cioè numeri pubblicati |
| cicli di training dei quattro decoder | dentro `benchmark/models.py` (righe 187/400, 274/337, 298/381, 554/672) | unificarli cambia l'ordine delle operazioni in virgola mobile: i numeri di CP-0011, CP-0013, CP-0015 e CP-0017 non sarebbero più riproducibili bit a bit |
| costruzione di `FactorizationResult` | `factorization.py:186` e `:225` | 4 campi su 10 diversi: un aiutante condiviso risparmierebbe 8 righe e aggiungerebbe una funzione |

Dopo i quattro commit di oggi, una scansione che ignora nomi e costanti non trova più
**nessuna** funzione clonata di almeno sei righe fra file diversi, a parte i due casi
minuscoli `local_source_targets`/`local_targets` (8 e 6 righe, stadi 52 e 53) e
`repair_prompt` (8 e 9 righe, due protocolli diversi).

---

## 4. Codice morto che non ho rimosso

Uguale agli altri per «nessuno lo chiama», diverso per una ragione:

- `splits.held_out_context` (3 righe) e `splits.held_out_groups` (21) — il docstring del
  modulo dichiara le **tre domande di generalizzazione** come disegno della valutazione,
  e chiama `held_out_context` «l'analogo più vicino al compito della gara». Toglierle
  cancellerebbe una decisione documentata, non del codice morto.
- `descriptors.high_expr_indices` (7 righe) — involucro esportato che porta la nota su
  dove si può prendere la classifica dei geni abbondanti («mai dal contesto di test»).
  La funzione gemella che fa il lavoro, `high_expr_indices_from_values`, è usata e il suo
  docstring dice «stessa selezione», cioè si appoggia a questa.

Decide il proprietario: 31 righe in tutto.

---

## 5. Proposte che richiedono il proprietario

### 5.1 Il vincolo che rende impossibile cancellare, e la leva che resta

Prima delle proposte, il fatto che le governa tutte. `scripts/31_check_docs.py` verifica
che ogni percorso citato fra backtick nel registro **e in ogni checkpoint** esista sul
disco. I checkpoint sono immutabili per contratto (CLAUDE.md, `docs/REGISTRO.md`).
Risultato, verificato leggendo i file:

- `docs/checkpoints/0019-catena-cicli-guardiano.md` cita `scripts/32_daily_cycle.py`,
  `scripts/ciclo.cmd`, `tests/test_daily_cycle.py` e sei file di
  `configs/ciclo_giornaliero/`;
- `docs/checkpoints/0007…`, `0008…`, `0009…` citano `src/oracle/`,
  `src/oracle/fixtures/pairwise_loss/`, `tests/test_oracle_pairwise_loss.py`;
- altri checkpoint citano `src/orchestrator/`, `src/orchestrator/briefs.py`,
  `src/orchestrator/cli.py`, `src/orchestrator/research/`.

**Cancellare uno qualunque di questi file fa fallire il controllo documentale**, e la
correzione — modificare il checkpoint — è vietata. Quindi la scelta non è «cancellare o
no»: è fra (a) lasciare i file e cambiare lo **stato nel registro**, dichiarando che non
si usano più; (b) accettare che il controllo fallisca; (c) cambiare
`scripts/31_check_docs.py` perché tolleri un percorso archiviato. La (a) non toglie una
riga di codice ma dice la verità a chi legge; la (c) è l'unica che apre la strada alla
cancellazione, ed è una decisione sul contratto del progetto, non una pulizia.

### 5.2 I tre gruppi, misurati

| Gruppo | Righe | Chi lo importa (grep) | Righe del registro | Ultima esecuzione documentata |
|---|---:|---|---|---|
| **Catena dei cicli**: `scripts/32_daily_cycle.py` (1.851), `tests/test_daily_cycle.py` (780), `scripts/ciclo.cmd`, `configs/ciclo_giornaliero/` (8 file), `.agents/skills/` e `.claude/skills/` (6 file) | **3.502** | nessun modulo lo importa: è una CLI. `tests/test_daily_cycle.py` lo carica con `importlib`/`subprocess`. Lo nominano `AGENTS.md`, le tre `SKILL.md`, `docs/CICLO_GIORNALIERO.md`, CP-0019, `reports/catena_2026-09-16/verifiche.txt` | righe 76, 77, 78, 79 del registro | **nessun ciclo dal vivo** (registro riga 78 e CP-0019: «provata con agenti simulati») |
| **Orchestratore**: `src/orchestrator/` (8.914) + `tests/test_orchestrator.py` e `test_orchestrator_research.py` (2.961) | **11.875** | fuori dal proprio albero lo importano **solo i suoi due file di test**; `scripts/orch.cmd` lo avvia come console | righe 217, 220, 223, 224 | campagna Jiang del 15 settembre, fermata `service_unavailable` (riga 110 del registro); le prove del 13-14 settembre sono a secco |
| **Oracle**: `src/oracle/` (1.107) + `tests/test_oracle_pairwise_loss.py` (591) | **1.698** | fuori dal proprio albero lo importa **solo il suo file di test**; non importa `orchestrator` né `vcc2026`, e c'è un test che lo verifica | righe 228, 229 | CP-0007/0008/0009, 12–13 settembre, su fixture sintetici |

**17.075 righe**, il 33% dei file `.py` tracciati. Nessuno dei tre partecipa alla catena
che produce una sottomissione: la si può rifare per intero con gli stadi 71-95 e il
notebook Colab.

Quello che chiedo di decidere, per ciascun gruppo: **stato `storico` nel registro con una
riga che dice «non si usa più»**, oppure una modifica dichiarata del controllo
documentale che permetta di spostarli in un `archivio/`. La prima non libera righe ma
smette di far credere a un agente nuovo che quel codice sia in gioco; la seconda libera
il 33% del repository.

### 5.3 Rimaste dal 18 settembre, ancora aperte

- Il file spurio `, remote ingestion and scientific plans"` nella radice del checkout
  principale (16.465 byte, la schermata d'aiuto di `less`): è la decisione **O4** del
  piano del 16 settembre, la sua prima metà è stata fatta (commit `4272b3b`), questa no.
  Al 19 settembre il file è ancora lì.
- `.runtime-deps/` (misurato: **89 MB**, `pyarrow` 88 MB), citato solo da
  `scripts/23_probe_orion.py:5`. Il registro lo elenca già fra i candidati alla pulizia,
  con la condizione «quando le sonde Orion non servono più».
- `PULIZIA_2026-09-18.md` sta nella radice perché ieri il registro era fuori dai file
  modificabili. Oggi non lo è: se vuoi, può spostarsi in `reports/pulizia_2026-09-18/`
  con la sua riga.

### 5.4 Un'ultima possibilità, che costa una esecuzione

`scripts/64_source_cards.py` (405 righe) ripete otto blocchi di
`Field(None, "missing")` quasi identici (righe 103/257/328, 288-291/323-326), e
`src/vcc2026/source_card.py` ha già `empty_card()`. Si risparmiano 40-60 righe, ma la
verifica seria non è la suite: è rieseguire lo stadio con un `--out` nuovo e confrontare
il JSON con `reports/source_cards_2026-09-15/`. Non l'ho fatto perché non era fra le
priorità di oggi; è pronto da fare.

---

## 6. Come rifare le verifiche

```bash
# lo stato del branch
git -C ../vcc2026-refactor log --oneline 4cdb618..HEAD
git -C ../vcc2026-refactor diff --numstat 7391e69..HEAD -- '*.py'

# i due controlli, prima di ogni commit (eseguiti quattro volte oggi)
python scripts/31_check_docs.py
.\scripts\py.cmd -m unittest discover -s tests        # 581 test, 1 saltato

# le righe per cartella
for d in src scripts tests; do git ls-files "$d/*.py" "$d/**/*.py" | sort -u | xargs wc -l | tail -1; done

# che i file bloccati non siano stati toccati
git diff --name-only 7391e69..HEAD | grep -E 'scripts/(82|84|94)_|bench_score|docs/checkpoints'   # vuoto
```

Le prove di equivalenza dei §2 sono state prodotte con script usa e getta nella cartella
temporanea della sessione, che caricano la versione **vecchia** della funzione copiata
dal commit precedente e la confrontano con quella nuova sui file veri. Non sono
versionati: chi li rifà li riscrive in dieci righe, e il punto è che la suite da sola non
tocca questi lettori.
