# Corpus di singole cellule: inventario, contratto, prima QC e primi job (R-LAB, P0–P1)

30 settembre 2026 sera, Claude (Claude Code, sessione `a1ec75f0`), dalle 19:08; orari letti con
`date`. Scheda [R-LAB](../../../docs/piani/piano-giorno-2026-09-30.md), su richiesta del proprietario
(«Esegui questo piano»). **È la prima consegna del §10 del piano.** Nessun download, nessun job in
cloud e nessun training: aspettano il via (§5 sotto). Tipi di affermazione: dove non è detto
altrimenti, **misurato** con gli script di questa cartella.

## 1. Da leggere per primo

| File | Che cosa |
|---|---|
| [PIANO_JOB.md](PIANO_JOB.md) | I job proposti, con byte misurati, runtime, uscite stimate e le domande al proprietario |
| [p1_r3/availability.csv](p1_r3/availability.csv) | Una riga per sorgente: stato, byte locali e su Drive, riferimento remoto, ostacolo, prossimo passo |
| [QC_MATRICE.md](QC_MATRICE.md) | Le prime misure per cellula e che cosa si può controllare su ogni sorgente |
| [sources.yaml](sources.yaml) | L'inventario curato delle 26 sorgenti del §3, con le fonti |
| [../../modelli/risposta_biologica_2026-09-30/holdout_registry.json](../../modelli/risposta_biologica_2026-09-30/holdout_registry.json) | Le letture di esito già fatte per dataset, e i ruoli proposti |

## 2. Lo stato delle sorgenti (misurato, `inventory.py`, esecuzione `p1_r3/`)

| Stato | Sorgenti |
|---|---|
| **Cellule in locale** | HIPSCI genome-wide fitness (322.746 cellule), non-fitness (396.458), mirato su 19 linee (1.161.865): CSV geni × cellule; Jurkat GSE249595: MTX non filtrate, con guide e hashing per canale; HepG2 Nadig (145.473 × 9.624, densa, conteggi interi); controlli di gara A/B/C (18.400 × 18.533 ciascuno); Tahoe: un solo shard su 3.388 |
| **Cellule su Drive** | K562 GWPS di Replogle, 65,8 GB |
| **Da recuperare: cellule solo remote** | K562 essential e RPE1 di Replogle (locatore non registrato); VIPerturb (Zenodo, 17,3 GB); CD4 Marson 2025 (12 file, 1.735,8 GB); Orion HCT116 e HEK293T (Hugging Face, 128,4 GB); KOLF2.1J (Figshare+, 250,6 GB, di cui 189,4 GB il pannello genomico); A549 (GEO, 23 GB in h5ad o 10 GB di MTX grezzo); Southard (Zenodo, 131,6 GB con le uscite di cellranger); **Mixscale** (Zenodo, oggetti Seurat per cellula, circa 20 GB: prima erano noti solo i DE); H1 della gara 2025 (locatore da verificare) |
| **Solo effetti o bulk** | DLD-1 (LFC e SE; cellule da verificare), DepMap 24Q4 (bulk) |
| **Non acquisite** | microglia GSE335887, PerturbFate GSE291147, scBaseCount (bucket a pagamento per chi legge) e le accessioni del catalogo del 26/09 da riconciliare |
| **Riserva proposta** | H1 della gara 2025: mai scaricata, esiti mai letti. Fra i dati già sul disco nessun grande schermo CRISPRi a livello di cellula è intatto |

I byte remoti vengono dai metadati pubblici ([remote_sizes.json](remote_sizes.json)): API di Zenodo
e Figshare, elenco FTP del GEO, HEAD su S3, API di Hugging Face. Nessun dato è stato scaricato.

## 3. P0: l'ambiente

[validate_runtime.py](validate_runtime.py) gira uguale in locale, su Colab e su Kaggle. Sul
portatile ([environment_manifest_portatile.json](environment_manifest_portatile.json)):
- lo scorer `cell-eval2` 0.16.0 si importa, compresa l'API privata che usa il banco;
- la prova di andata e ritorno di una matrice sparsa conserva conteggi interi, identità della
  cellula, maschera dei geni misurati e lettura a blocchi;
- mancano pertpy, scvi-tools, harmonypy e decoupler: servono solo più avanti (P3–P5);
- risorse: 8 CPU, 7,8 GB di RAM di cui 0,9 GB liberi, **1,7 GB liberi su C:**.

## 4. Contratto, pilota e QC

- **[contracts.py](contracts.py)**: il contratto dello shard (§4 del piano) come codice, con un
  validatore. Uno shard ha:
  - i conteggi grezzi interi sull'asse nativo;
  - una chiave unica per cellula;
  - i metadati con valori mancanti espliciti;
  - la profondità prima del filtro dei geni e quella sull'asse del file;
  - la mappatura all'asse ufficiale, senza somme silenziose;
  - la provenienza e la parità.
- **Pilota HepG2** ([shard_writer.py](shard_writer.py), [pilota_hepg2_r1.json](pilota_hepg2_r1.json)).
  1.000 cellule in 10,4 MB, accettate dal validatore:
  - parità esatta dei conteggi (19.075.455 prima e dopo);
  - 9.023 dei 9.624 geni sull'asse ufficiale, 601 assenti;
  - profondità sull'asse del file pari al 99,1 % del totale pubblicato (mediana).

  Lo shard sta nella radice dati, `processed/corpus_cellulare_2026-09-30/pilot_hepg2_r1/`. Da lì
  vengono le stime di spazio del piano dei job: circa 2,5 byte per valore non nullo.
- **QC** ([QC_MATRICE.md](QC_MATRICE.md), [qc_sample.py](qc_sample.py), misure in `qc_r1/`). Profili
  molto diversi fra saggi:
  - la frazione mitocondriale mediana va dallo 0,3 % dei controlli Flex al 9,4 % di HepG2 e al 16 %
    del canale Jurkat;
  - il contesto B ha una coda di cellule povere;
  - solo Jurkat ha le gocce vuote per stimare l'RNA ambientale.

  Una soglia unica sarebbe sbagliata.

## 5. Le risposte del proprietario

Le cinque domande del [piano dei job](PIANO_JOB.md) hanno avuto risposta in chat, trascritta con
gli orari in [AUTORIZZAZIONI.md](AUTORIZZAZIONI.md):
1. gli shard vanno su Google Drive;
2. via a J01–J03;
3. via ai download di J02 (Figshare) e J03 (GEO);
4. più account Colab e Kaggle: il proprietario conferma che l'uso rispetta i termini;
5. H1 2025: scaricato dopo J02; lo split di test fa da riserva, train e validation vanno nel training.

La sessione che ha ripreso il lavoro (`ec2e5b07`) ha fatto riconfermare le autorizzazioni prima di usarle.

## 6. Esecuzioni e file

- `p1_r1/`: la prima esecuzione dell'inventario. Classificava DLD-1 come «cellule remote» senza
  prova; resta come traccia.
- `p1_r2/`: con il campo `cellule_remote` in `sources.yaml`; dava ancora Mixscale «da verificare».
- `p1_r3/`: l'esecuzione valida, dopo la lettura dell'API di Zenodo che ha trovato le cellule di
  Mixscale.
- Gli script non scrivono sopra un'uscita esistente.

## 7. P2: i job J01–J03 e il download di H1 (30/09 sera, sessione `ec2e5b07`)

**Stato alle 20:47 del 30/09:** i quattro job sono **in coda** in `runs/queue/` su Drive. Nessuno è
ancora partito: il dispatcher Colab è fermo dal 29/09, e lo avvia solo il proprietario (celle 1 e 2
del notebook). Quello che segue è **implementato e provato in locale**, non ancora eseguito su Colab.

| Coda | Job | Che cosa fa | Dove scrive |
|---|---|---|---|
| 086 | `j01_hepg2_r1` | HepG2 dal Drive, h5ad denso, 145.473 cellule | `data/processed/corpus_cellulare_2026-09-30/j01_hepg2_r1/` su Drive |
| 087 | `j03_jurkat_r1` | Jurkat dal GEO, 16 canali (144 file, 3,75 GB) | `…/j03_jurkat_r1/` |
| 088 | `j02_hipsci_r1` | HIPSCI da Figshare, tre schermi (7,70 GB) | `…/j02_hipsci_r1/` |
| 089 | `h1_vcc2025_r1` | H1 2025 dal bucket Arc (34,36 GB), dopo il `.done` di 088 | `data/raw/vcc2025_h1_2026-09-30/` |

**Il codice.**
- [adapters.py](adapters.py): i tre schemi. Aggiunte di questa sessione:
  - HIPSCI si legge in passate su intervalli di 600.000 cellule, così i secchi temporanei restano
    sotto circa 21 GB sul disco del runtime (108 GB, 83–88 GB liberi nei job passati);
  - Jurkat verifica che le liste di barcode di trascrittoma, guide e hashing siano identiche
    (misurato sui canali 1 e 16);
  - Jurkat non inventa chiamate delle guide: `guides` è `MISSING`, e le matrici grezze degli UMI di
    guide e hashing stanno in `obsm`;
  - la condizione (`untreated` o `activated`) viene dall'oligo di hashing più forte, secondo la
    tabella S6.
- [rlab_job.py](rlab_job.py): scrive uno shard alla volta sul disco del runtime, rilegge la somma dal
  file, lo valida col contratto, lo copia su Drive, ri-hasha la copia e scrive la ricevuta. A fine
  unità controlla la parità che lo schema consente: somma letta dal CSV contro somma degli shard
  (HIPSCI), cellule tenute più RNA ambientale contro totale della matrice (Jurkat), tutte le righe
  del file (HepG2). `complete.json` si scrive per ultimo. `--reuse` riprende dopo un runtime perso.
- [fetch.py](fetch.py) scarica e verifica ogni byte: sha256 dai manifest dei download precedenti sul
  portatile, crc32c del bucket per H1. [publish.py](publish.py) copia i file grezzi di H1 e scrive il
  manifest per ultimo, senza aprirli.
- [build_jobs.py](build_jobs.py) genera spec, liste di download, manifest di preflight e launcher
  ([jobs_r1/](jobs_r1/), [jobs_r2/](jobs_r2/)). I launcher seguono `docs/ERRORI.md`:
  1. attendono i file di setup per hash;
  2. misurano il runtime con [validate_runtime.py](validate_runtime.py), compreso lo spazio di Drive;
  3. portano gli input sul disco del runtime;
  4. eseguono il preflight comune sul runtime;
  5. solo allora avviano il calcolo.

  Incidenti considerati: E-20260929-002, -003, -005, -007.

**Le prove.**
- **Misurato:** il preflight locale passa per tutti e quattro i manifest (`jobs_r*/receipts_local/`).
  Gli input sul portatile hanno gli hash dichiarati: fra questi l'HepG2, uguale al record del Drive.
- **Misurato:** la prova locale ([smoke_test.py](smoke_test.py), esito in [smoke.json](smoke.json))
  gira su ritagli dei file veri e passa per i tre schemi:
  - le parità sono esatte;
  - HIPSCI si legge in tre passate;
  - il secondo tentativo HepG2 riusa tutti gli shard.

  La prima esecuzione si era fermata sulla guardia del disco del portatile: la guardia funziona.
- **Misurato:** i CSV H1 già sul portatile dall'11/09 hanno il crc32c degli oggetti del bucket.
  L'elenco del bucket è in [h1_bucket_listing.json](h1_bucket_listing.json).
- **Non ancora verificato:** che `/usr/bin/python3` sia il Python del runtime con anndata. Se non lo
  è, il job si ferma al primo controllo. Non ancora verificato nemmeno lo spazio libero su Drive: J02
  chiede 32 GB e H1 36,5 GB, e ogni job si rifiuta di partire se non li trova.

**Limiti dichiarati.**
- La copia su Drive si ri-hasha attraverso il mount, che può servire la cache locale del runtime: un
  hash uguale non prova che Drive abbia già sincronizzato il file (E-20260929-005).
- Gli script `.sh` in `jobs_r1/` hanno fine riga LF su disco, e l'hash in `build.json` si riferisce a
  quella versione. Un checkout con `core.autocrlf` li riscrive in CRLF: per rimetterli in coda si
  rigenerano con `build_jobs.py`.
- Chimica di HIPSCI: `MISSING` negli shard, perché la fonte non la dichiara nel file letto.

**Due sorgenti mancano dall'inventario di P1**, anche se la repo le conosce. Le elenca la pagina dei
dati della gara (virtualcellchallenge.org/datasets, letta il 30/09):
- il Jurkat di Nadig et al. 2025, GSE264667: 262.956 cellule, già descritto in
  `docs/storico/candidate_adversarial_review_2026-09-12.md` e mai acquisito; è diverso da GSE249595;
- Jiang et al. 2025, sei linee: in D-031 risulta `metadata_verified` e mai acquisito.

Vanno aggiunte a `sources.yaml` in una prossima esecuzione dell'inventario. La stessa pagina dice che
H1 2025 si può usare per il training.

## 8. Dalle 21:40: la rete sulle singole cellule (sessione `ec2e5b07`)

**La richiesta del proprietario, in chat, trascritta:** «Voglio una rete addestrata direttamente sulle singole
cellule, usando tutti i dataset utilizzabili, non un'estensione della rete sugli effetti pseudobulk. Non limitarti
alle sorgenti più facili o a quelle integrabili stanotte. Completa l'inventario, includendo scPerturb e tutti i
dataset già individuati nella repo, e organizza un'ingestione progressiva con streaming e shard. Formati diversi
richiedono adattatori; modalità diverse richiedono una gestione esplicita, non esclusioni automatiche. I conteggi
cellulari originali devono essere la supervisione principale, con maschere per i geni non misurati, controlli
appropriati e QC documentato. Conserva il raw immutabile e separa le trasformazioni necessarie al modello. Non
sostituire le cellule con medie, LFC o valori shrunk. Il pseudobulk può restare soltanto come baseline o controllo
ausiliario. Le sorgenti disponibili esclusivamente come aggregati devono essere dichiarate e trattate separatamente.
Un primo training su un sottoinsieme è accettabile come verifica tecnica, ma non come risultato finale. Mostrami
quali dataset e quante cellule entrano realmente nel training, quali restano fuori e perché. Restano escluse le
riserve concordate. Se la rete cellulare non esiste ancora, costruiscila.»

**Come è organizzato (implementato, 30/09 sera):**
- `adapters.h5rows` legge h5ad a righe (CSR o denso), in locale o **a intervalli di byte via HTTP** con un controllo
  dell'ETag su ogni intervallo: KOLF (189 GB) e CD4 (1,7 TB) non vanno scaricati interi. `inspect_remote.py` misura
  la struttura di un h5ad remoto senza leggerne la matrice (72 dei 77 file di `urls_r4.json` misurati, in
  `p1_r4/remote/`).
- Colab ingerisce (due dispatcher, `runs/queue` e `runs/queue2`; il secondo notebook è
  `notebooks/colab_dispatcher_queue2.ipynb`), gli shard stanno su Drive, e `publish_kaggle.py` li pubblica come
  dataset privati dell'account Kaggle con GPU (`davidmaisterx`), dove gira il training. `colab_job.py` costruisce
  i job (preflight comune, ingestione, pubblicazione), `wave1_specs.py` gli spec della prima ondata (`jobs_colab/`).
- Prima ondata: H1 train e validation (il test è la riserva e non si scarica per il training), HepG2 e Jurkat di
  Nadig, K562 genome-wide, K562 essenziali e RPE1 di Replogle; HIPSCI (J02) e Jurkat GSE249595 (J03, senza chiamate
  delle guide: non supervisionabile finché l'assegnazione non è provata).
- Il job 090 (archivio di H1 su Drive) è fallito per un mio controllo dello spazio sbagliato: il mount di Drive su
  Colab riporta il disco del runtime. Tutti i file sono stati scaricati e verificati (crc32c, sha256 in
  `runs/rlab_setup_2026-09-30_r2/receipts/h1_vcc2025_r2/fetch.json`); le copie temporanee sono state tolte dal
  job 091 per non riempire il disco. L'archivio va rifatto su un runtime con disco libero.

Stato dei job e passaggio di consegne: scheda R-LAB, voce del 30/09 alle 22:55.

## 9. La notte fra il 30/09 e l'1/10 (sessione `07ebf08b`)

**Misurato.** I job che hanno finito, con parità ok nei loro `complete.json` su Drive:
- H1 2025 train e validation (job 108): 221.273 e 98.927 cellule;
- HIPSCI in tre schermi (job 088): 1.881.069 cellule;
- Jurkat di Nadig (job 103): 262.956 cellule;
- K562 genome-wide (job 115): 1.989.578 cellule;
- K562 essenziali e RPE1 (job 114): 310.385 e 247.914 cellule.

Tutti pubblicati su `davidmaisterx`. Gli shard di Replogle di 115 e 114, però, non si usano (incidente -004, sotto).

**Quattro difetti trovati e corretti, ognuno con un incidente e un test** (registro in
`reports/analisi/lead_scientist_2026-09-29/learning/incidents/`, evidenze in `incidenti/`):
- E-20260930-001: il lettore a intervalli teneva in memoria ogni byte letto (job 100 e 105 uccisi su H1). Cache LRU;
  verificato dal job 108;
- E-20260930-002: Figshare firma gli URL S3 per 10 secondi e il lettore aspettava dopo il rinnovo (job 104 e 109).
  Rinnovo e richiesta immediata; verificato dal job 114;
- E-20260930-003: le categorie AnnData vecchie (`obs/__categories`) si leggevano come codici, e gli shard di Replogle
  non avevano controlli né bersagli leggibili. Decodifica e test; verificato dai job 114 e 115;
- E-20260930-004: gli shard di Replogle hanno ID Ensembl come simboli dei geni, quindi nessun gene sta sull'asse.
  Spec con `var/gene_name`, guardia in `rlab_job` che ferma un'unità senza geni sull'asse; job 121 e 122 in corso.

**Codice nuovo.**
- `adapters.h5csc_shards`: matrici CSC (scPerturb, KOLF), a passate per intervalli di cellule; test contro la lettura a
  righe sugli stessi dati.
- `rlab_job`: riuso da più tentativi; parità per passata dell'adattatore CSC.
- `colab_job`: preflight locale prima della coda, `--reuse` multiplo, `--stop`.
- `catalogo.py`: il catalogo; versione corrente [catalogo_r2](catalogo_r2/CATALOGO.md).

**Seconda ondata in coda** (job 116-120, poi 123), con i suoi spec in `wave2_specs.py`: KOLF piccoli e forte, Southard
RPE1 e Hs27 (CRISPRa), A549 (KO), Tian 2019 e 2021 e Norman 2019. Le colonne e le etichette dei controlli vengono dalle
misure remote. Le prime cellule di Southard, A549 e Tian sono state lette in locale con il loro spec prima della coda.

I training che usano questi dati sono in `reports/modelli/cellnet_tecnico_2026-10-01/` e
`reports/modelli/cellnet_esteso_2026-10-01/`.

## 10. Dopo le 02:50 dell'1/10 (sessione `07ebf08b`)

**Misurato.**
- **Coda 1 persa.** Il dispatcher 1 non dà più battiti dopo le 02:29 CEST (`runs/jobs/dispatcher.log`). Il job 116
  aveva scritto gli shard di KOLF cromatina, ma non quelli di KOLF metabolico; il 117 (Southard) nessuno shard. I
  `.started` non ripartono. Il lavoro è passato alla coda 2 come job nuovi, il 123 è ritirato prima di partire:
  - 124: KOLF piccoli, con `--reuse` degli shard di cromatina del 116;
  - 125: Southard RPE1 e Hs27;
  - 126: KOLF forte.
- **Seconda ondata finita**, con parità ok nei `complete.json`, e pubblicata su `davidmaisterx`:
  - A549 KO (job 118, `rlab-a549`): 606.075 cellule;
  - job 119 (`rlab-tian-norman`), 623.436 cellule in tutto: Tian 2019 iPSC 275.708 e neuroni 182.790, Tian 2021
    CRISPRi 32.300 e CRISPRa 21.193, Norman 2019 111.445.
- **Replogle riletto con `gene_name`** (incidente `E-20260930-004`). Il job 121 (K562 essenziali 310.385 cellule in
  32 shard, RPE1 247.914 in 25, parità ok) è pubblicato come `rlab-k562-essential-r2` e `rlab-rpe1-r2`. Nessuno shard
  è stato fermato dalla guardia dell'asse. Il job 122 (K562 genome-wide, `rlab-k562-gwps-r3`) è in corso.

I training che usano questi dati: `reports/modelli/cellnet_esteso_2026-10-01/` (il secondo, con le riletture di
Replogle) e `reports/modelli/cellnet_completo_2026-10-01/` (il terzo, con la seconda ondata).

**Più tardi, fino alle 06:15.**
- Il job 122 finisce con parità ok (1.989.578 cellule in 100 shard) ed è pubblicato come `rlab-k562-gwps-r3`.
- KOLF piccoli (124) e KOLF forte (126, 232.438 cellule) sono finiti e pubblicati. Southard (125) legge da Zenodo a
  circa uno shard ogni 9 minuti.
- **Terza ondata** in coda (job 127-129), con `wave3_specs.py`: sorgenti scPerturb umane con bersagli su geni
  singoli. Le loro etichette sono state lette in remoto prima della coda (`smoke_labels.py`, esiti in `smoke_w3/`).
  Il catalogo dice perché restano fuori Adamson, Papalexi pooled, Wessels, gli schermi di enhancer, i topi e i farmaci.
- **Catalogo**, versione corrente: [catalogo_r3](catalogo_r3/CATALOGO.md). CD4 (33,6 milioni di cellule, circa 1,7 TB)
  è segnato «da campionare»: il disegno del campione spetta al proprietario.
