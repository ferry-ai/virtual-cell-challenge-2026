# Archivio cloud dei dati: inventario, migrazione su Drive e Kaggle, verifiche (2–3 ottobre 2026)

Claude Code, sessione `096065` («vcc2026-0b»), dalle 22:20 CEST del 2/10; orari letti con `date`.
Richiesta del proprietario in chat: spostare l'archiviazione dei dati pesanti dal portatile a Google
Drive (archivio principale) e Kaggle (dataset per i training), verificare le copie remote, preparare
l'ingestione dei dati mancanti nel cloud. **Autorizzati:** copia e caricamento su Drive e Kaggle dei dati
già disponibili, verifica delle copie remote, adattamento di percorsi e strumenti. **Non autorizzati:**
nuovi training, nuovi download dalle sorgenti, acquisti, cancellazioni locali (il proprietario le
autorizza dopo aver visto l'elenco con le prove). Dove non è detto altrimenti, ogni numero è
**misurato** con gli script di questa cartella; gli stati pesanti stanno nella radice dati, in
`processed/archivio_cloud_2026-10-02/r1/`.

**Stato alla scrittura:** caricamento su Drive in corso (processo separato, notte fra il 2 e il 3/10);
verifica Kaggle conclusa; verifica Colab delle copie su Drive in coda, parte quando il proprietario avvia
il dispatcher; nessuna cancellazione.

## 1. Da leggere per primo

| File | Che cosa |
|---|---|
| questo README, §2–§6 | inventario, migrazione, verifiche, portatile leggero, ostacoli |
| [INGESTIONE.md](INGESTIONE.md) | flusso nel cloud, riconciliazione del catalogo, campionamenti di CD4 e Orion, ruoli, nuovi download |
| `r1/eliminabili_*.json` nella radice dati | l'elenco delle copie locali eliminabili, rigenerato a ogni nuova prova con [eliminabili.py](eliminabili.py) |

## 2. Inventario reale

**Portatile** (2/10, 22:22–23:03). Disco C: 476 GB, **14–15 GB liberi** all'inizio (98 % usato), 7,8 GB
di RAM con 0,8 GB liberi. Radice dati `C:/Users/ferra/vcc2026-data`: **219,00 GiB unici** in 4.644 file
fisici, 226,56 GiB contando i percorsi: 22 file hanno più percorsi (hard link), per esempio
`kaggle/rete_data_r1/` ↔ `processed/rete_contesti_r1/` (6,41 GiB), per cui la ricognizione precedente che
sommava le cartelle (kaggle 16,2 + processed 54,4 GiB) contava due volte lo stesso spazio.

| Cartella | GiB (per percorso) | Natura prevalente |
|---|---|---|
| `external/` | 64,50 | originali scaricati: CD4 pseudobulk 41,51 (un solo file), HIPSCI 15,88, Jurkat GSE249595 3,50, DepMap 1,77, altri piccoli |
| `interim/` | 59,03 | derivati intermedi: somme per gli universi (KOLF 12,65, HIPSCI 10,18, Orion 26,56, VIPerturb 5,02, Southard 1,27), bundle, piloti; anche materiale privato sui contesti |
| `processed/` | 54,35 | derivati: universi degli effetti (input dei banchi e della produzione), cache dello stadio 98, effetti degli invii, dataset delle reti r1/r2, cartella attiva di R-LEAD |
| `artifacts/` | 37,38 | uscite: previsioni e pacchetti degli invii t22–t28 (circa 3,9 GiB ciascuno), corse del 12–16/09 |
| `kaggle/` | 9,78 (+6,41 in hard link) | uscite scaricate dai kernel, staging dei dataset |
| `raw/` | 1,85 | originali della gara: zip dei controlli, controlli A/B/C, HepG2 di Nadig; prova con D/E/F rinominati |

Esclusi perché non sono dati: `.venv`, `orch-venv`, `orchestrator`, `ciclo`, `archivio_repo`,
`__pycache__`. Duplicati esatti fra file fisici diversi: 360 insiemi, 3,87 GiB (`r1/duplicati_esatti.json`).

Per natura (gruppi a due livelli, [gruppi_r4_prima_di_colab.json](gruppi_r4_prima_di_colab.json), con destinazione, dataset Kaggle, impronta sha256 e stato di copia di ogni gruppo; lettura dei
nomi e del registro, non dei contenuti): originali scaricati 64,50 GiB; originali della gara 2,03; derivati
intermedi 58,20; effetti per bersaglio 28,16; dataset di training della rete 14,53; cache dello stadio 98
2,91; effetti degli invii 0,92; previsioni e pacchetti degli invii 27,51; checkpoint, metriche e previsioni
dei training su Kaggle 5,65; uscite e checkpoint delle corse del 12–16/09 1,99; staging per Kaggle (copie e
hard link) 8,00; lavoro attivo R-LEAD 4,35.

**Google Drive.** Cartella `MyDrive/vcc2026`: **206,51 GiB** in 3.481 file (dati 174,37, `runs/` 32,13),
elenco dei soli metadati in 40 s. Ci sono già: shard del corpus (100,64 GiB, 17 job completi), K562 GWPS a
singola cellula (61,31 GiB), `rete_contesti_r1`, controlli, HepG2, uscite dei job Colab. **La quota libera non
è misurabile da qui:** il volume G: riporta lo spazio del disco locale che fa da cache, i log di Drive per
desktop non riportano valori di quota, e nessun client API di Drive è installato. Va letta dal proprietario
(drive.google.com o one.google.com) o con un client autorizzato (§6).

**Kaggle** (API, 2/10 sera). Tutti i dataset sono **privati**: `davidmaisterx` (account con GPU) 27 dataset,
108,16 GB; `davideferrante11` 4 dataset, 16,37 GB; `davideferante` 2 dataset, 1,97 GB. La quota dei dataset
privati dichiarata da Kaggle è di 200 GB per utente. Su `davidmaisterx` quattro dataset superati da incidenti
(`rlab-k562-gwps`, `-r2`, `rlab-k562-essential`, `rlab-rpe1`) occupano 30,8 GB; su `davideferrante11` stanno
copie anteriori dello stesso corpus.

## 3. Migrazione

- **Specchio a percorsi invariati:** `<radice dati>/<rel>` → `MyDrive/vcc2026/data/<rel>`, la stessa radice
  che i job Colab usano già (`VCC2026_DATA_ROOT=/content/drive/MyDrive/vcc2026/data`). Nessun archivio
  monolitico; un file già presente con la stessa dimensione non si ricarica; nessuna sovrascrittura.
- **Piano** (`r1/plan_r1.json`): 43 file (8,35 GiB) erano già su Drive allo stesso percorso; 4.623 assenti.
- **Lotti** ([run_upload_r1.ps1](run_upload_r1.ps1)): t1 input dei banchi (universi in uso, basali), t2
  originali (`external/`, zip dei controlli), t3 `processed/`, `kaggle/`, `raw/`, t4 `artifacts/`, t5 `interim/`.
  Restano fuori dal giro r1: il CD4 da 41,51 GiB (§6) e la cartella attiva di R-LEAD.
- **Come:** copia sul mount di Drive per desktop, un file alla volta, con lo sha256 e l'md5 calcolati sui byte
  copiati (`r1/copy_receipts.jsonl`, in sola aggiunta). Drive per desktop tiene un file nella cache locale
  finché non l'ha caricato, e la cache è limitata al 20 % dello spazio libero solo per i file già caricati:
  il copiatore aspetta quando lo spazio libero scende sotto la dimensione del file più un margine (9 GiB, poi
  6,5 GiB dalle 00:11 del 3/10, quando R-LEAD ha finito le sue scritture grandi). Velocità di rete misurata
  4,1–5,2 MB/s in Wi-Fi.
- **Avanzamento alle 00:27 del 3/10:** 18,18 GiB in 613 file copiati sul mount; **0 discordanze** fra lo sha256
  dei byte copiati e quello dell'hash locale. La coda di Drive per desktop non accumulava arretrato (alle
  23:42 UTC un caricamento attivo e 4 operazioni in coda).
- **Riavvii puliti:** alle 23:14 (margine) e alle 00:11 (margine, e il copiatore non leggeva il file `STOP`
  mentre attendeva spazio: corretto). Il riavvio delle 00:11 ha sovrascritto il log `.out.log` del lotto t1;
  le ricevute sono complete. Da allora ogni avvio scrive log con data e ora.
- **File grandi (dalle 00:43 del 3/10):** con circa 7 GB liberi e 6,5 GiB di margine un file di qualche GiB
  non entra mai e bloccava i più piccoli dietro di sé. Ora un file sopra 1 GiB che non entra passa in fondo al
  suo lotto; se dopo 20 minuti non entra ancora resta registrato come `deferred_no_space` e non viene inviato.
  Il margine non si abbassa. Questi file (e il CD4) aspettano spazio libero, cioè le prime cancellazioni
  approvate, oppure un client che carichi senza cache (§6). Tre test in [test_archivio_copy.py](test_archivio_copy.py).
- **Fine del caricamento:** quando il lanciatore termina, la sentinella [watch_upload_r1.ps1](watch_upload_r1.ps1)
  costruisce il manifest A (`archivio.py manifest`) e scrive su Drive il segnale `UPLOAD_COMPLETE_r1.json`.

## 4. Verifiche delle copie remote

- **Kaggle (concluso).** Kernel CPU privato `davidmaisterx/archivio-verify-corpus-r1`
  ([kaggle_verify/](kaggle_verify/)), due versioni: 758 file, 79,79 GiB letti sui server Kaggle senza errori;
  le due esecuzioni danno gli stessi 758 sha256. **557 shard su 557** coincidono, per sha256 e byte, con le
  ricevute di pubblicazione su Drive, in 17 dataset `rlab-*`; nessun file delle ricevute manca. I dataset
  `vcc-rete-contesti-r1` (19/19), `vcc-rete-contesti-r2` (19/19), `vcc-corpus-basale-r1` (10/10) e
  `vcc-corpus-tahoe-r1` (3/3) coincidono con i file locali da cui erano stati pubblicati. Apertura: la
  versione 1 non apriva gli h5ad per un mio errore (l'indice di `obs` è un gruppo codificato); la versione 2
  apre 60/60 shard, uno per unità: CSR coerente, conteggi interi, dimensioni lette con h5py. anndata non è
  nell'immagine Kaggle: la prova con anndata resta ai job Colab.
- **Drive (in coda).** Su `MyDrive/vcc2026/runs/archivio_verify_2026-10-02_r1/` e in `runs/queue/`:
  - job **130**: rilegge subito da Colab i dati che erano già solo su Drive, manifest B: 816 file, 157,02 GiB
    (shard dei 17 job con gli sha256 scritti alla creazione, compresi gli shard riusati da tentativi
    precedenti; K562 GWPS e HepG2 grezzi con lo sha256 del loro record di download);
  - job **131**: aspetta il segnale di fine caricamento, poi rilegge lo specchio (manifest A) con 24 tentativi
    a 15 minuti per i caricamenti ancora in volo, e apre campioni di ogni tipo.

  Preflight locale **PASS** per entrambi, sugli stessi file letti dal mount. Una copia sul mount non conta
  come prova: conta solo lo sha256 letto dal runtime Colab.
- **Coerenza locale.** Durante l'hash (72 minuti, 235.149.795.799 byte) sono cambiati solo due log della
  sessione R-LEAD attiva, la cui cartella è esclusa.

## 5. Portatile leggero

- **Restano sul portatile** (dipendenze attive, 36,02 GiB): tutti gli universi `processed/universe_*` e
  `processed/multisource_2026-09-27_r9` (letti da R-LEAD, che lo ha chiesto esplicitamente; la produzione
  D/E/F usa gli universi del preset `me1` dello stadio 106), `processed/multisource_2026-09-23_r5` (cache del
  t22), `processed/generalizzazione_contesti_2026-10-02/`, i basali, `raw/controls/`, `raw/nadig_hepg2/`,
  `external/annotation/`, `external/vcc2025/`, più i tre gruppi piccoli che il codice vivo nomina
  (`external/K562_gwps_raw_bulk_01.h5ad` per lo stadio 98, `external/cd4/` per il 97, `interim/orion_hct116/`
  per il 102) e i gruppi sotto 100 MB.
- **Riferimenti:** [dipendenze.py](dipendenze.py) cerca nei file tracciati ogni gruppo candidato. Oltre ai tre
  sopra, solo codice di ricerca nei report e documenti li nominano. Per quel codice non serve cambiare la
  radice globale: su Colab vale lo specchio con `VCC2026_DATA_ROOT`; sul portatile [riporta.py](riporta.py)
  riporta i file da Drive controllando lo sha256 del manifest e senza sovrascrivere.
- **Eliminabili:** [eliminabili.py](eliminabili.py) propone un gruppo solo quando **ogni** suo file ha una copia
  remota letta da un ambiente indipendente con lo stesso sha256, e conta lo spazio liberato per file fisico
  (un hard link libera spazio solo se se ne vanno tutti i suoi percorsi). Con le sole prove Kaggle, alle 00:20
  del 3/10, **nessun gruppo è ancora eliminabile**; 181,7 GiB aspettano la lettura da Colab (`gruppi_r2_prima_di_colab.json`).

### Proiezione dello spazio recuperabile (stima dal piano, 3/10 00:50)

| Fase | Che cosa la sblocca | Gruppi | GiB |
|---|---|---|---|
| A | fine del giro r1 (file fino a 1 GiB) e lettura da Colab del job 131 | 44 gruppi piccoli e medi: Jurkat GSE249595, uscite Kaggle, `ipsc_replica`, cache multisource superate, previsioni dei banchi, zip dei controlli, … | circa 21,2, più 6,4 di `rete_contesti_r1` con il suo staging in hard link |
| B | archiviazione dei file sopra 1 GiB (44 file, circa 95 GiB senza gli hard link) | HIPSCI originali e somme, somme KOLF, pool Orion, `rete_contesti_r2`, previsioni e pacchetti t22–t28, somme VIPerturb e Southard, DepMap | circa 119 |
| C | archiviazione del CD4 | `external/cd4_gw` | 41,5 |

**Piano senza strumenti nuovi:** dopo il via sulla fase A lo spazio libero sale a circa 35 GB, abbastanza per
caricare tutti i file della fase B attraverso la cache (il più grande è 6,4 GiB) con un giro r2 e un job di
verifica nuovo; dopo il via sulla fase B entra anche il CD4. **Più rapido:** un client che carica senza cache
(rclone) fa B e C subito, se il proprietario lo autorizza e firma l'accesso a Drive.

## 6. Ostacoli e decisioni per il proprietario

1. **Avviare il dispatcher Colab** (notebook `notebooks/colab_sc_training.ipynb`, celle 1 e 2): fa partire i job
   130 e 131. I dispatcher sono muti dal 1/10 alle 06:29 UTC.
2. **Quota di Drive:** leggerla e annotarla; stima, non misura: a specchio completo `vcc2026` arriva a circa
   380 GiB (206,5 presenti più circa 170 da caricare senza il CD4).
3. **CD4 pseudobulk, 41,51 GiB, unica copia locale:** non passa dalla cache di Drive per desktop con questo
   disco. Due vie: un job Colab che lo rilegge dal bucket S3 pubblico direttamente su Drive e ne confronta lo
   sha256 con quello del `.manifest.json` locale (è un download dalla sorgente: serve il via), oppure un client
   che carica senza cache (per esempio rclone: va installato e autorizzato dal proprietario nel browser).
4. **Lettura del database di Drive per desktop:** il controllo dei permessi l'ha rifiutata (contiene token).
   Non serve: la prova viene dai job Colab.
5. **Southard (job 125) interrotto** il 1/10: completarlo richiede di rileggere Zenodo, cioè un download.
6. **Spazio su C:** durante la notte è sceso fino a 6,7 GB per una scrittura temporanea di R-LEAD, rientrata
   alle 00:09; le scratchpad di sessioni chiuse occupano circa 5,3 GB (una, `76a3a45e`, contiene evidenze che
   stanno solo lì): decide il proprietario.

## File

| File | Che cosa |
|---|---|
| [archivio.py](archivio.py) | inventario per file fisico, hash sha256 e md5, piano rispetto a Drive, copia regolata con ricevute, manifest per la verifica |
| [run_upload_r1.ps1](run_upload_r1.ps1), [watch_upload_r1.ps1](watch_upload_r1.ps1) | lanciatore dei lotti e sentinella di fine caricamento |
| [list_drive.ps1](list_drive.ps1) | elenco dei soli metadati della cartella `vcc2026` su Drive |
| [manifest_drive_preesistente.py](manifest_drive_preesistente.py) | manifest B dei dati che erano già solo su Drive |
| [verify_drive.py](verify_drive.py), [build_verify_jobs.py](build_verify_jobs.py) | verifica su Colab e costruzione dei job 130–131 |
| [kaggle_check.py](kaggle_check.py), [kaggle_list_account.py](kaggle_list_account.py), [kaggle_privacy.py](kaggle_privacy.py) | confronto lato server con le ricevute, elenco e privacy dei dataset |
| [kaggle_verify/](kaggle_verify/) | kernel di verifica, lanci e confronto |
| [eliminabili.py](eliminabili.py), [dipendenze.py](dipendenze.py), [riporta.py](riporta.py) | copie eliminabili, riferimenti nel codice, ripristino verificato |
| [INGESTIONE.md](INGESTIONE.md), [campionamento.py](campionamento.py) con test, [ruoli_ingestione_r1.json](ruoli_ingestione_r1.json) | piano per i dati mancanti, campioni di CD4 e Orion, ruoli registrati prima dell integrazione |
