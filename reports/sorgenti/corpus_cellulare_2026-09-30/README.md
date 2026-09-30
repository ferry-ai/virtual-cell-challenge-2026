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
