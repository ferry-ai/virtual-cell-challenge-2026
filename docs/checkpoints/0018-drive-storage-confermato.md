# CP-0018 — Grezzi pesanti già su Google Drive: si collegano, non si scaricano

- **Data:** 2026-09-16
- **Tipo:** osservazione
- **Redatto da:** agente Claude (Opus 5)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il proprietario del progetto riferisce che i due file grezzi più pesanti del catalogo
remoto sono già sul suo Google Drive. Che cosa cambia per l'ingestione e per la
criticità C8 del [workflow 2](../PIANO_COMPRENSIONE_2026-09-16.md)? E che cosa manca
perché un runtime remoto li usi senza scaricarli?

## 2. Cosa è stato fatto

Nessun run remoto, nessun download, nessuna lettura dei file su Drive. Su questa
macchina Google Drive non è montato: `Get-PSDrive` mostra la sola unità `C:` e non gira
alcun processo `GoogleDriveFS`. L'agente, quindi, non ha visto le copie su Drive.

1. Trascritta la dichiarazione del proprietario, fatta in chat il 16 settembre.
2. Confrontate le dimensioni dichiarate con i byte registrati in
   `configs/remote_catalog.yaml` e in `src/vcc2026/external.py`, con
   1 GiB = 1.073.741.824 byte e 1 MiB = 1.048.576 byte.
3. Ricontrollata la copia HepG2 locale con
   `ls -la C:/Users/ferra/vcc2026-data/raw/nadig_hepg2/`.
4. Letto, senza eseguirlo, il codice che decide dove cercare un file e quando
   considerarlo completo: `colab_default_roots` e `resolve_paths` in
   `src/vcc2026/remote_ingest.py`; `dest_for`, `file_matches`, `recommend_fetch_ids`
   e `run_catalog` in `src/vcc2026/remote_catalog.py`; le celle 1, 5 e 7 di
   `notebooks/remote_ingest_hepg2.ipynb`.

Checkpoint creato con:

```bash
python scripts/30_new_checkpoint.py --slug drive-storage-confermato --title "Grezzi pesanti già su Google Drive: si collegano, non si scaricano" --type osservazione --author "agente Claude (Opus 5)"
```

## 3. Cosa si è osservato

### 3.1 La dichiarazione (non misurata dal progetto)

Il proprietario riferisce che il suo account Google Drive ha 5 TB di spazio e che vi
sono già caricati `K562_gwps_raw_singlecell_01.h5ad` (61,31 GB) e
`NadigOConner2024_hepg2.h5ad` (811,2 MB), con le dimensioni che mostra Drive. Non ha
comunicato né il percorso delle copie su Drive né il loro md5.

### 3.2 Le dimensioni tornano, in unità binarie (misura, aritmetica)

| File | Byte nel catalogo | In unità binarie | In unità decimali | Mostrato da Drive |
|---|---|---|---|---|
| `K562_gwps_raw_singlecell_01.h5ad` | 65.830.941.948 | 61,31 GiB | 65,83 GB | 61,31 GB |
| `NadigOConner2024_hepg2.h5ad` | 850.590.740 | 811,19 MiB | 850,59 MB | 811,2 MB |

Entrambe le cifre dichiarate coincidono con i byte del catalogo letti in unità binarie,
nessuna con gli stessi byte letti in unità decimali. La copia HepG2 locale ha gli
stessi 850.590.740 byte, con l'md5 `af2be47f…` già verificato il 15 settembre
(`reports/remote_catalog_2026-09-15/catalog_run.json`, blocco `nadig_hepg2`).

### 3.3 Il «61,3 GB» del profilo è la stessa grandezza (misura, aritmetica)

Il catalogo tratta il «61,3 GB» del profilo della gara come un numero diverso dalla
dimensione del file: `advertised_bytes: 61300000000`, con la nota «Profile '61.3 GB'
is not this file's byte count». Ma le tre cifre del profilo per i file Replogle a
singola cellula, 61,3 / 9,9 / 8,1 GB
(`reports/source_cards_2026-09-15/replogle_k562_gwps_singlecell.json`, campo
`remote_bytes`), coincidono al decimale, una per una, con i byte dei tre file figshare
espressi in GiB:

| File figshare | Byte (`src/vcc2026/external.py`) | GiB |
|---|---|---|
| `K562_gwps_raw_singlecell_01.h5ad` | 65.830.941.948 | 61,31 |
| `K562_essential_raw_singlecell_01.h5ad` | 10.661.879.995 | 9,93 |
| `rpe1_raw_singlecell_01.h5ad` | 8.700.873.216 | 8,10 |

L'etichetta «65,8 GiB» che diversi documenti usano per il file K562 è quindi un errore
di unità: sono 65,8 GB, cioè 61,3 GiB. I byte del catalogo, che sono quelli che il
codice usa, sono giusti.

### 3.4 Dove un runtime remoto cerca i file (letto nel codice)

Su Colab con Drive montato la radice dati predefinita è
`/content/drive/MyDrive/vcc2026/data` (`colab_default_roots`), e si può cambiare con
`VCC2026_DATA_ROOT`. Il catalogo cerca i due file in
`<radice>/raw/replogle/K562_gwps_raw_singlecell_01.h5ad` e
`<radice>/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad` (`dest_for`, campo `relpath`).
Per il codice, un file che sta altrove su Drive non esiste.

### 3.5 Quando un blocco conta come completo (letto nel codice)

I controlli sono due, e non sono uguali.

- **La selezione automatica** (cella 5 del notebook; `run_catalog` con `auto_fetch`)
  confronta **solo la dimensione** con `bytes`.
- **`skip_complete` in `run_catalog`** richiede un checkpoint `complete` nella cartella
  di uscita **del run in corso**, oppure dimensione **e** md5 coincidenti
  (`file_matches`). Ma la cartella di uscita è nuova a ogni run (`catalog_<timestamp>`;
  il run rifiuta una cartella che contiene già `catalog_run.json`), e il ramo
  `skip_complete` non scrive checkpoint. Per un file caricato a mano, quindi,
  `skip_complete` passa sempre dal calcolo dell'md5 sull'intero file: a ogni
  esecuzione, anche in modalità solo-piano, 61,31 GiB letti attraverso il mount di
  Drive. Il tempo che richiede non è misurato.

### 3.6 La selezione automatica non si ferma ai due file (letto nel codice, non eseguito)

Con `FETCH_BLOCKS = None` e i due file nel posto atteso, `recommend_fetch_ids` li salta
come completi e passa al blocco successivo di `default_order`, `rpe1_raw_singlecell`
(8.700.873.216 byte). Se lo spazio libero che il mount di Drive riporta (non misurato)
lascia il pavimento remoto di 2 GiB, sceglie quel blocco e lo scarica. Se invece i due
file stanno in un'altra cartella, la stessa selezione riscarica HepG2 e poi il K562 da
61,31 GiB dentro Drive, accanto alle copie già presenti.

### 3.7 Il file K562 non è mai stato aperto (misura di un'assenza)

Nella scheda sorgente il numero di bersagli, le cellule per bersaglio e i geni misurati
sono `missing`; la copertura 272/300 è quella del pseudobulk locale, non di questo
file; la decisione è `defer`
(`reports/source_cards_2026-09-15/replogle_k562_gwps_singlecell.json`). Dopo il pilot
Colab del 15 settembre l'utente riportava circa 11 GiB di RAM
(`reports/remote_catalog_2026-09-15/catalog_run.json`, campo
`colab_pilot.ram_available_user_report_gib`). `qc_h5ad` legge soltanto `obs`, `var` e
le prime 64 righe di `X`.

## 4. Interpretazione e incertezza

- **Interpretazione.** Drive mostra le dimensioni in unità binarie, con l'etichetta GB
  e MB: lo indicano due file indipendenti che coincidono al decimale. Questo non prova
  che le copie siano integre. Una copia a cui mancano pochi megabyte mostrerebbe le
  stesse cifre arrotondate; solo l'md5 lo esclude.
- **Interpretazione.** Per questi due file non serve più alcun download, né sul
  portatile né in remoto. Il portatile era già escluso: D-005 lo vieta, e `run_catalog`
  ignora `auto_fetch` in locale. Cambia il lato remoto: niente trasferimento da figshare
  o Zenodo, niente ore di download, nessun file grande sul disco effimero della VM.
- **Cosa resta di C8.** C8 descrive questa macchina: 7,81 GiB di RAM e disco
  oscillante. Resta vera per tutto ciò che gira qui, cioè generazione, packaging e
  benchmark (il [workflow 1](../PIANO_IMPLEMENTATIVO_2026-09-16.md), §3, registra
  0,69 GiB disponibili alle 13:31). La prova di chiusura indicata dal piano, «job
  pesanti solo su runtime remoto misurato (I-6)», non esiste ancora: nessun runtime ha
  letto questi file da Drive. Per questo C8 è registrata come **declassata per
  l'ingestione**, non come chiusa.
- **Il vincolo di memoria cambia sede, non scompare.** 61,31 GiB non entrano negli
  11 GiB circa di un runtime Colab: tutto ciò che va oltre `obs`, `var` e poche righe
  di `X` va letto a blocchi. È un vincolo del runtime remoto, non di C8.
- **Ipotesi non verificata.** Che leggere 61,31 GiB attraverso il mount di Drive, per
  l'md5 o per estrarre cellule, sia abbastanza veloce e stabile da stare in una
  sessione Colab.
- **Incertezza sul percorso.** Non sappiamo dove stiano le copie su Drive. Se non
  coincidono con il percorso atteso, il catalogo non le vede (§3.4 e §3.6).

## 5. Spiegazione semplice

Prima il piano era questo: accendere un computer in prestito (Colab), fargli scaricare
da internet un file da 61 GiB e metterlo su Drive, per poi lavorarci. Ora il file è già
su Drive, e al computer remoto basta aprire il cassetto giusto. Ci sono due avvertenze.
Il cassetto deve essere quello che il codice si aspetta, altrimenti il codice non trova
il file e ricomincia a scaricarlo. E prima di fidarsi del file bisogna controllarne
l'impronta, l'md5: la dimensione mostrata da Drive dice che il file è grande quanto
deve, non che è identico all'originale. Il portatile resta piccolo come prima: cambia
il viaggio del file, non la macchina su cui lavoriamo.

## 6. Conseguenze

- **C8** ([workflow 2](../PIANO_COMPRENSIONE_2026-09-16.md), §4): declassata per
  l'ingestione dei due file, su indicazione del proprietario. Resta aperta per il
  lavoro locale.
- **Nessuna decisione cambia.** D-005 riguarda questa macchina e resta attiva. D-031
  non cambia. La scheda del K562 a singola cellula resta `defer`: avere il file a
  portata di mano non vuol dire adottarlo, e `configs/sources.yaml` non cambia. Se
  l'account da 5 TB comporta una spesa, spetta al proprietario registrarla come
  autorizzazione di spesa cloud, che è una delle condizioni di riapertura di D-005:
  questo checkpoint non lo presume.
- **Procedura per un run che collega senza scaricare** (proposta, non ancora provata):
  1. sistemare le copie, oppure impostare `VCC2026_DATA_ROOT`, in modo che stiano in
     `<radice>/raw/replogle/` e `<radice>/raw/nadig_hepg2/`;
  2. nel notebook impostare `FETCH_BLOCKS = []`, oppure
     `SELECT_BLOCKS = ['nadig_hepg2', 'k562_gwps_raw_singlecell']`;
  3. conservare il `catalog_run.json` del primo run: sarà la prima misura
     dell'integrità delle copie su Drive e del tempo di lettura attraverso il mount.
- **Incarichi del 16 settembre** ([workflow 1](../PIANO_IMPLEMENTATIVO_2026-09-16.md)):
  in I-6 il fetch del K562 diventa collegamento e verifica dell'md5. In I-5 l'audit di
  copertura del file K562 non richiede download, ma richiede comunque di aprire `obs`
  sulla copia. Questo checkpoint non avvia nessuno dei due.
- **Codice** (proposta, non fatta qui): una modalità «solo collegamento» che non passi
  al blocco successivo; un marcatore persistente dell'md5 verificato, fuori dalla
  cartella del singolo run, per non rileggere 61,31 GiB a ogni esecuzione; la
  correzione delle etichette «65,8 GiB» e di `advertised_bytes`.

## 7. Cosa corregge

Nessun checkpoint. Corregge due affermazioni che compaiono in documenti,
configurazioni e commenti di codice, elencati nella scheda
[R-013](../REGISTRO.md#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb)
del registro:

1. «65,8 GiB» per `K562_gwps_raw_singlecell_01.h5ad`: sono 65,8 GB, cioè 61,31 GiB.
2. «il 61,3 GB del profilo non è la dimensione di questo file»: è la stessa
   dimensione, espressa in GiB.

## 8. Domanda di comprensione

Drive mostra 61,31 GB e il catalogo dice 65.830.941.948 byte. Perché questo accordo
non basta a dire che la copia è integra? E che cosa succede se un run parte con
`FETCH_BLOCKS = None` e la copia sta in una cartella diversa da quella attesa?
