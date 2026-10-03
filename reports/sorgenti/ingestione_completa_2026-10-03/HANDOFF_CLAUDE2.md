# Passaggio di consegne a claude2: regia dell'ingestione completa

Scritto il 3/10/2026 verso le 16:25 CEST dalla sessione Claude Code «R-LEAD implementazione vcc2026» (`22d21f`), che
ha consumato l'80% della finestra di 5 ore. Il proprietario apre claude2 dall'app desktop, con l'altro account, nella
cartella `C:\Users\ferra\OneDrive\Desktop\vcc2026`. **Priorità esclusiva: l'ingestione completa** (mandato del
proprietario del 3/10: tutti i dataset per intero, in fretta, anche in parallelo su più code Colab).

## Da leggere prima di agire

1. `CLAUDE.md` alla radice: regole, autorizzazioni e la checkout condivisa.
2. `docs/PROCEDURE.md` §3 e `docs/ERRORI.md`, da «Prima del prossimo job» a «Registro immutabile»: preflight e job
   Colab.
3. `docs/AGENTI.md` §3. **Commit sempre con percorsi espliciti** (`git commit -- <percorsi>`): l'indice è condiviso
   con altre sessioni.
4. [README dell'ingestione](README.md): sorgenti, vincoli e file. La scheda
   [R-LAB](../../../docs/piani/piano-giorno-2026-09-30.md) ha lo stato riprendibile.
5. [GEO_METADATI.md](GEO_METADATI.md): DLD-1, microglia, PerturbFate.

## Stato alle 16:25

**Colab**, account del proprietario. I dispatcher li avvia lui dal browser; il battito sta in
`G:/Il mio Drive/vcc2026/runs/jobs/dispatcher*.log`, ogni 10 minuti, in ore UTC. I log dei singoli job arrivano su
Drive solo alla fine.

| Coda | Notebook | Job in corso o in attesa |
|---|---|---|
| `queue` | `notebooks/colab_sc_training.ipynb` | 134 verifica dell'archivio A (ripresa r2); 138 Orion HCT116 shard, parte 1/2 |
| `queue2` | `notebooks/colab_dispatcher_queue2.ipynb` | 132 Southard r3 (137 è fallito, vedi sotto) |
| `queue3` | `notebooks/colab_dispatcher_queue3.ipynb` (anche su Drive in `vcc2026/notebooks/`) | 139, Orion HEK293T, parte 0 di 4 |
| `queue4` | `notebooks/colab_dispatcher_queue4.ipynb` (idem) | 141, Orion HEK293T, parte 2 di 4 |

**Memoria (misurato alle 16:23):** il job 137, HCT116 parte 0/2, è stato ucciso con rc=137 al nono file, mentre
girava accanto a Southard; il runtime era a 7 GiB su 12. Ogni file Orion ha circa 31.000 cellule e 170 milioni di
valori. **Regola: un solo job di shard Orion per runtime, mai accanto a Southard o a un altro job pesante.** Per
questo 140 e 142 sono stati spostati in `runs/queue3/ritirati/` e `runs/queue4/ritirati/` prima di partire.

**Parti Orion ancora da mettere in coda,** una per runtime quando il job Orion di quel runtime finisce, con
`orion/build_orion_job.py --kind shards`, numeri nuovi da 143 e lo stesso setup e snapshot. La riga di comando è in
`orion/jobs/*_manifest.json` e nei launcher.
- HCT116 parte 0/2: rifatta con un nome nuovo, per esempio `j16_orion_full_shards_hct116_p0of2_r2`. Gli shard del
  primo tentativo restano dove sono e si possono passare a `--reuse`.
- HEK293T parti 1/4 e 3/4.

Si può ridurre il picco di memoria in `orion_job.py:read_selected`: con la selezione completa si costruisce la CSR
direttamente dagli offset di arrow, in int32 e float32, senza le liste per riga. Va fatto con un test, prima di
lanciare due job per runtime.

Le code 3 e 4 partono quando il proprietario apre i due notebook. Un job con `.started` e senza battito per ore è
perso: si rimette in coda con **numero e output nuovi**, mai sopra il vecchio.

**Output su Drive** (`G:/Il mio Drive/vcc2026/`):
- Orion: `data/processed/ingestione_completa_2026-10-03/<job>/`; la parità dei metadati è passata su entrambe le
  linee (3.409.169 e 4.534.299 cellule);
- Southard: `data/processed/corpus_cellulare_2026-09-30/j09_southard_r3/`;
- verifiche: `runs/archivio_verify_2026-10-03_r2/out_*_r2/` (la B è finita alle 16:06, con codice 0).

**Agenti e compagni:**
- **Codex** è il supervisore. Lavora in `adattatori_codex/`: `h5csc` compatto a intervalli di cellule (KOLF) e
  `h5rows` con filtro di idoneità (CD4). La consegna è in corso; i file sono suoi, non toccarli.
- **Grok** non riesce a fare ricerche GEO senza shell: non riassegnargliele.
- Il run claude2 dell'hub `20261003-155531-vcc-rds-conversion` si è fermato per un limite di spesa e non ha scritto
  niente.

## Aggiornamento delle 16:38: niente secondo Colab, si usa Kaggle CPU (decisione del proprietario)

- **Code 3 e 4:** non si aprono. I job 139–142 sono in `runs/queue3/ritirati/` e `runs/queue4/ritirati/`.
- **Kaggle CPU misurato** (`kaggle_cpu/esito_nettest_r1/nettest.json`): 4 CPU, 31 GB di RAM, 20 GB di output per
  kernel; Hugging Face, S3, Zenodo e GEO raggiungibili, 44 MB/s su un file Orion.
- **Kernel Orion:** `kaggle_cpu/build_orion_kaggle.py`, dataset del codice `davideferrante11/vcc-ingest-code-r1`,
  stesso snapshot `4df47fab…` dei job Colab. Le parti sono 8 per HEK293T e, per HCT116, la 0/4 e la 2/4, cioè i file
  del job 137 fallito; la 1/2 la fa il job Colab 138.
- **Difetto da correggere prima di rispingere:** alle 16:37 tre kernel sono andati in `ERROR` per
  `FileNotFoundError: .../vcc-ingest-code-r1/code_snapshot.tar.gz`. Kaggle scompatta da solo gli archivi caricati in
  un dataset, e probabilmente falliranno anche i due ancora `RUNNING`. Correzione: nel `run.py` del kernel cercare
  la cartella già estratta sotto il mount (per esempio `reports/` dentro `DS`) invece di aprire il tar, oppure
  caricare lo snapshot con un nome non d'archivio (`code_snapshot.bin`). Poi slug nuovi `-r2`.
- **Concorrenza:** con 2 training GPU e 2 kernel CPU attivi non è stato visto nessun rifiuto per limite di sessioni;
  gli errori erano tutti il FileNotFoundError.

## Aggiornamento delle 17:16: claude2 ha preso la regia (sessione `c7c07a`)

Stato verificato sui log e su Kaggle, ore lette con `date`.

- **Colab:** 133 e 134 (verifiche dell'archivio) finiti con codice 0 alle 16:06 e alle 16:47. Girano 132 (Southard,
  `queue2`) e 138 (Orion HCT116 parte 1/2, `queue`: 27 shard su 55 alle 17:16).
- **Kernel Orion r1:** tutti e cinque in `ERROR` per lo stesso `FileNotFoundError`
  ([log](kaggle_cpu/esito_orion_r1/vcc-orion-hek293t-p0of8-r1.log)). Kaggle ha scompattato il tar in
  `code_snapshot/`.
- **Kernel Orion r2:** [build_orion_kaggle_r2.py](kaggle_cpu/build_orion_kaggle_r2.py) legge la cartella scompattata
  dopo aver confrontato ogni file con i membri del tar (sha256). Stesso dataset del codice, nessun caricamento nuovo.
  In esecuzione dalle 17:05–17:07: HCT116 0/4 e 2/4, HEK293T 0/8, 1/8, 2/8. Sul primo: controllo del codice
  passato, parità dei metadati in 130 s, 3.409.169 cellule selezionate come nel campione Colab, 40–75 s per shard.
- **Limite misurato:** Kaggle accetta 5 sessioni CPU insieme. Le parti HEK293T 3/8–7/8 sono state rifiutate alle
  17:12; le loro cartelle di stage esistono e si rispingono con `--repush` quando una sessione si libera. Ogni spinta
  è in [lancio_orion_r2.jsonl](kaggle_cpu/lancio_orion_r2.jsonl). La CLI esce con 0 anche su un rifiuto: decide la
  frase «successfully pushed».
- **I file parquet del campione** hanno sha256 diverso fra Kaggle e Colab (versioni diverse di pyarrow), con lo stesso
  numero di cellule. Il confronto vero è fra le ricevute degli shard: gli 8 shard del job 137 su Drive coprono file
  che i kernel HCT116 0/4 e 2/4 rifanno.
- **Dimensionamento e proposta su CD4:** [DIMENSIONAMENTO.md](DIMENSIONAMENTO.md). Il proprietario ha chiesto se il
  terabyte entra nel training: no, il limite è il tempo di GPU. La proposta è CD4 a tranche; **aspetta il suo sì**,
  quindi i job CD4 completi non si costruiscono prima.
- **Codex** ha consegnato `adattatori_codex/complete_adapters.py` con 20 test passati (`test_r2.txt`, 16:15). I file
  sono ancora non tracciati e restano suoi.

## Aggiornamento delle 18:00 (sessione `c7c07a`)

- **Difetto trovato nel codice Orion ereditato:** `orion_job.py` mette `whole_line` fra i controlli di un'unità, e
  per una parte vale sempre falso. Ogni job `--part` finisce quindi con «PARITY FAILED», `parity_failed.json` e
  codice 1, anche quando ogni file della parte è fatto e le cellule sono quelle del campione. Vale per i cinque kernel
  r2 (stato `ERROR`) e varrà per il job Colab 138. **Gli shard e le ricevute sono validi**: Kaggle conserva l'output
  di un kernel fallito (provato scaricando `kaggle_done.json` e `parity_failed.json` di `vcc-orion-hct116-p0of4-r2`).
  Il primo kernel ha scritto 28 shard, 9,53 GB.
- **Regola per una parte, scritta prima di vedere una parte finita** (`build_orion_kaggle_r2.py --part-rule`, kernel
  con suffisso `-r3`): ogni altro controllo booleano dell'unità è vero, e cellule e shard sono le cellule selezionate
  e i file del campione che cadono nella parte, ricontati dalla tabella del campione. Se passa, il kernel scrive
  `part_complete.json` ed esce con 0. Il codice di ingestione e lo snapshot non cambiano.
- **In esecuzione:** HEK293T 3/8, 4/8, 5/8 (dalle 17:43) e 6/8 (17:51) come r3; KOLF parte 0/2 (17:47). Da spingere
  quando si libera una sessione: KOLF 1/2 con `--readahead 8`, HEK293T 7/8, poi HCT116 1/4 e 3/4, così tutta la linea
  sta anche su Kaggle (la metà del job 138 resta su Drive come seconda copia).
- **Da fare a parti finite:** un kernel che monta tutte le parti di una linea, applica la stessa regola alle parti r2,
  controlla che l'unione sia la lista congelata (109 e 223 file; 3.409.169 e 4.534.299 cellule) e ricalcola lo sha256
  di ogni shard. È la verifica indipendente e la chiusura della linea.
- **KOLF pan-genome:** [kolf/](kolf/) con l'adattatore di Codex in copia identica, parti contigue, controllo
  preliminare e 4 test; dataset del codice `vcc-ingest-code-kolf-r2` (parte 0/2) e `-r3` (con la lettura anticipata).
  Sul file vero il controllo preliminare è passato: 17.971 geni sull'asse ufficiale. **La lettura è lenta:** 5,8 MB/s
  un blocco alla volta, cioè circa 4,5 ore per i 94,5 GB dello strato dei conteggi. Per questo esiste
  [lettura/prefetch.py](lettura/prefetch.py) (blocchi richiesti in parallelo, 5 test, stessi byte del lettore
  originale sul file vero anche dopo il rinnovo dell'URL firmato): la parte 1/2 la usa, e serve per CD4, dove un file
  da 143 GB non starebbe nelle 12 ore di un kernel.
- **Strategia dati inoltrata dal proprietario alle 17:46:** [STRATEGIA_DATI_TRAINING.md](STRATEGIA_DATI_TRAINING.md).
  L'acquisizione resta completa, CD4 compreso; il campionamento (livelli 32, 64, 128 annidati) riguarda le copie
  preparate per i training. Prima consegna chiesta: inventario dopo QC, campioni con dimensioni reali, manifest degli
  split, verifica del bilanciamento, protocollo del primo confronto.
- **Codice ancora da scrivere:** il job CD4 (`h5rows_cd4` di Codex più `ShardSink` e lettura anticipata, un file per
  kernel) e il job dell'inventario per combinazione.

## Aggiornamento delle 18:35 (sessione `c7c07a`)

- **Un kernel finito in `ERROR` non si può montare:** alla spinta della verifica parziale Kaggle ha risposto «not
  valid kernel sources» per le due parti r2 di HCT116. Il loro output si scarica ma non entra in un altro kernel.
  Le cinque parti r2 (HCT116 0/4 e 2/4, HEK293T 0/8, 1/8, 2/8) si rifanno quindi come r3, che esce con 0.
- **La regola della parte funziona sui dati veri:** HEK293T 3/8 r3 ha 563.632 cellule, quante ne seleziona il campione
  nei suoi 28 file, 7,81 GB; stato `COMPLETE`. Finite anche 4/8, 5/8 e 6/8. La parte Colab 138 (HCT116 1/2) è finita
  con codice 1 per il solo `whole_line`: 54 shard, 1.697.191 cellule, 19,37 GB, ogni altro controllo vero.
- **Lettura anticipata misurata su Kaggle:** KOLF parte 1/2 legge a 92 MB/s (11,04 GB in 120 s), contro 5,8 MB/s
  della parte 0/2 lanciata prima. La 0/2 è stata rilanciata come `vcc-kolf-pan-p0of2-r2`; il kernel lento
  `vcc-kolf-pan-p0of2-r1` occupa una sessione finché non finisce o il proprietario lo ferma dalla pagina di Kaggle.
- **CD4, prova sul file vero** (`vcc-cd4-d1-rest-smoke-r1`, 79 s): 40.000 righe di `D1_Rest`, 22.751 idonee (1.018
  controlli), escluse 10.287 senza guida, 6.903 con più guide, 41 di bassa qualità, 18 con bersaglio non valido;
  884 bersagli senza simbolo sull'asse del file (il simbolo pubblicato resta in `cd4_perturbed_gene_name`);
  184 MB, 2,35 byte per valore. Proiezione per tutto CD4: circa 170 GB in 24 parti da 7–9 GB.
- **Coda:** [fill_sessions.py](kaggle_cpu/fill_sessions.py) spinge i prossimi kernel nelle sessioni libere, una
  chiamata per volta fatta dalla sessione. In coda 6 parti Orion r3 e le 24 parti CD4.

## Aggiornamento delle 19:55: in pausa su richiesta del proprietario (sessione `c7c07a`)

Alle 19:51 il proprietario ha scritto in chat: «Aspetta, sto delineando un nuovo piano con codex». Da quel momento la
sessione **non spinge altri kernel**; i processi che la richiamavano a sessione libera sono stati fermati. I kernel
già partiti finiscono da soli. Per riprendere la coda com'era: `kaggle_cpu/fill_sessions.py`, una chiamata per volta.

- **Chiuso:** KOLF pan-genome. Il kernel `vcc-kolf-pan-verify-r1` ha riletto le due parti (`vcc-kolf-pan-p0of2-r2`,
  `vcc-kolf-pan-p1of2-r1`): 2.659.209 cellule, 133 shard, 18,39 GB, 7.872.183.461 valori come nella sorgente, sha256
  uguali. Ricevute in [kolf/esito_verifica_r1/](kolf/esito_verifica_r1/). Dall'inventario: 11.687 bersagli, mediana
  218 cellule per bersaglio, 3 guide e 30 librerie per bersaglio; con tetto 32, 64, 128 restano 365.813, 716.099 e
  1.376.068 cellule bersagliate su 2.512.462, più 146.747 controlli.
- **In corso alle 19:52:** CD4 `D1_Rest` parte 0/2, HCT116 1/4 r3, il kernel KOLF lento `vcc-kolf-pan-p0of2-r1`
  (superfluo, non fermabile via API) e la sonda `vcc-rds-probe-r1`, che non ispeziona niente perché l'immagine non
  ha `/usr/bin/time`: la versione corretta è committata e **non spinta**.
- **Finiti e montabili:** Orion HEK293T 3/8–7/8, HCT116 0/4 e 2/4 (r3); CD4 `D1_Rest` 1/2 (finita in 39 minuti).
- **Fermo in coda (26 kernel):** HCT116 3/4, HEK293T 0/8, 1/8, 2/8, e 22 parti CD4. Poi le verifiche di linea di
  HCT116 e HEK293T (`build_orion_verify.py`) e quelle dei file CD4 (`build_parts_verify.py`).
- **DLD-1** ([dld1/esito_probe_r1/](dld1/esito_probe_r1/)): il tar ha 280 membri, 48 librerie di espressione (4 del
  pilota, 44 dell'esperimento grande in tre pool da 24, 12 e 8 canali) e 44 matrici di UMI delle guide (23.480
  guide). Gli oggetti elaborati dagli autori hanno i conteggi in HDF5 (`assay001`, 1.196.592 cellule × 36.601 geni
  per la MOI bassa) e la tabella delle cellule in un `_se.rds`: è la via più semplice, e la tabella si legge con la
  sonda RDS.
- **Colab:** `queue` è libera dalle 18:00; `queue2` porta ancora Southard (132).

## Prossimi passi, in ordine

1. **Orion**, quando le parti finiscono:
   - leggi `complete.json` e le ricevute di ogni parte: le cellule devono essere uguali al campione;
   - misura la dimensione degli shard;
   - pubblica su Kaggle con `publish_kaggle.py` (`reports/sorgenti/corpus_cellulare_2026-09-30/`) sull'account dei
     dati `davidmaisterx`. La quota privata è di 200 GB, di cui circa 108 usati il 2/10: se non basta, pubblica il
     campione del training e lascia tutto il resto su Drive;
   - fai rileggere gli shard da un altro runtime (`verify_resume.py` o `verify_drive.py`).
2. **KOLF pan-genome e CD4**, appena Codex consegna gli adattatori:
   - rivedi i suoi test e integra in una copia tua;
   - costruisci i job sullo schema di `orion/build_orion_job.py`: KOLF diviso per intervalli di cellule su due code,
     CD4 un job per file (12 file su S3, 1,74 TB). Le code sono 1–4.
3. **DLD-1** (GSE337988, `RAW.tar` da 26,5 GB):
   - un adattatore per le matrici 10x h5 per canale, con la chiamata della guida da `crispr.umi_correct.h5`;
   - la MOI bassa per prima, perché è a guida singola;
   - job: scaricare il tar sul runtime, estrarre canale per canale, convertire.
4. **Mixscale, VIPerturb e PerturbFate** (RDS): il brief è [agenti/brief_claude2_rds.md](agenti/brief_claude2_rds.md).
   Tu hai la shell, quindi puoi scriverlo e provarlo. R su Colab: `apt-get install -y r-base r-cran-matrix`.
5. **Microglia** (GSE335887): piccola, matrici 10x h5 più le guide del CROP-seq.
6. Dopo ogni passo aggiorna lo stato riprendibile nella scheda R-LAB e committa con i percorsi.

## Non è priorità, ma non toccare

La rete ancorata di R-LEAD: i training Kaggle `davideferrante11/rcell-anchored-train-h1-r1` e `-hepg2-r1` sono in
corso dalle 16:09, con un budget di circa 3 ore. RPE1 va spinto quando una delle due sessioni GPU si libera: il
comando è nella scheda R-LEAD (`docs/piani/strategia-scientifica.md`). Dopo la spinta si rilegge la quota con
`kaggle quota` e il token `~/.kaggle-davideferrante11`. Il protocollo è congelato con un emendamento
(`reports/modelli/rete_ancorata_2026-10-03/PROTOCOLLO.md` §9). Se l'ingestione ti lascia tempo, spingi RPE1 una volta
sola e annotalo in `lancio_train_r1.json` o in un file nuovo.

## Autorizzazioni, già date dal proprietario in chat

- download e acquisizione di tutti i dataset per intero;
- Colab e Kaggle, anche su più code;
- agenti dell'hub quando servono.

Non autorizzati senza chiedere: push su GitHub, invii alla gara, dataset pubblici, cancellazioni. Niente segreti nella
repo; il test di H1 2025 resta chiuso.

## Trappole già incontrate

- `scripts/py.cmd` passa da cmd.exe, che spezza un argomento con `|`: in quel caso usa
  `C:/Users/ferra/vcc2026-data/.venv/Scripts/python.exe` direttamente.
- Un heredoc di Git Bash passato a `py` dimezza i backslash: per stringhe con backslash usa l'editor.
- `G:` mostra il disco del portatile, non la quota di Drive.
- Il `.started` non è atomico su Drive: due dispatcher non leggono mai la stessa coda.
- In modalità `read` dell'hub Grok si ferma al piano. I run claude2 dell'hub condividono i limiti dell'account Claude
  che li lancia.
- Dopo ogni spinta di un kernel GPU si rilegge la quota; non si lanciano cicli che spingono da soli (incidente
  E-20261003-001).
