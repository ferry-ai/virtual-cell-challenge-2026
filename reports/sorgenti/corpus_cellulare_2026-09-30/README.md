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

## 5. Che cosa aspetta il proprietario

Le cinque domande del [piano dei job](PIANO_JOB.md), § finale:
1. la destinazione persistente degli shard;
2. il via ai job J01–J03 in cloud;
3. il via ai download;
4. la regola sugli account;
5. la riserva.

## 6. Esecuzioni e file

- `p1_r1/`: la prima esecuzione dell'inventario. Classificava DLD-1 come «cellule remote» senza
  prova; resta come traccia.
- `p1_r2/`: con il campo `cellule_remote` in `sources.yaml`; dava ancora Mixscale «da verificare».
- `p1_r3/`: l'esecuzione valida, dopo la lettura dell'API di Zenodo che ha trovato le cellule di
  Mixscale.
- Gli script non scrivono sopra un'uscita esistente.
