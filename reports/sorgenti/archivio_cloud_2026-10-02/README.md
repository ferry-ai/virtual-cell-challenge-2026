# Archivio cloud dei dati: inventario, migrazione su Drive e Kaggle, verifiche (2 ottobre 2026)

Claude Code, sessione `096065` («vcc2026-0b»), dalle 22:20 CEST del 2/10; orari letti con `date`.
Richiesta del proprietario in chat: spostare l'archiviazione dei dati pesanti dal portatile a Google
Drive (archivio principale) e Kaggle (dataset per i training), verificare le copie remote, preparare
l'ingestione dei dati mancanti nel cloud. **Autorizzati:** copia e caricamento su Drive e Kaggle dei dati
già disponibili, verifica delle copie remote, adattamento di percorsi e strumenti. **Non autorizzati:**
nuovi training, nuovi download dalle sorgenti, acquisti, cancellazioni locali (il proprietario le
autorizza dopo aver visto l'elenco con le prove).

**Stato: in corso.** Questa pagina viene completata a fine sessione con gli esiti delle verifiche.

## File

| File | Che cosa |
|---|---|
| [archivio.py](archivio.py) | Inventario per file (con identificativo NTFS: gli hard link contano una volta), hash sha256 e md5, piano rispetto a Drive, copia regolata sul mount di Drive per desktop con ricevute |
| [run_upload_r1.ps1](run_upload_r1.ps1) | Lanciatore dei lotti di caricamento r1, in sequenza, riprendibile, fermabile con un file `STOP` |
| [list_drive.ps1](list_drive.ps1) | Elenco dei soli metadati (percorso, byte, data) della cartella `vcc2026` su Drive: nessun contenuto letto |
| [kaggle_check.py](kaggle_check.py), [kaggle_list_account.py](kaggle_list_account.py) | Confronto lato server fra ogni dataset Kaggle del corpus e la sua ricevuta di pubblicazione; elenco dei dataset di un account |
| [kaggle_verify/](kaggle_verify/) | Kernel CPU Kaggle che ricalcola sha256 e apre un campione di shard sui dataset montati da Kaggle |
| [verify_drive.py](verify_drive.py) | Verifica su Colab delle copie su Drive: sha256 letto dal runtime e apertura di file rappresentativi |

Gli stati di lavoro pesanti (inventario, piano, hash, ricevute di copia, log) stanno nella radice dati,
`processed/archivio_cloud_2026-10-02/r1/`; qui vanno i riassunti e i manifest compatti.

## Regole seguite

- Lo specchio su Drive conserva i percorsi relativi: `<radice dati>/<rel>` → `MyDrive/vcc2026/data/<rel>`.
  Su Colab un manifest scritto per la radice dati vale con `VCC2026_DATA_ROOT=/content/drive/MyDrive/vcc2026/data`,
  già la radice predefinita dei job (`notebooks/colab_jobs/common.sh`).
- Nessun file su Drive si sovrascrive; una copia sul mount di Drive per desktop **non** prova il
  caricamento: la prova è la lettura dal runtime Colab (`verify_drive.py`) o dal server Kaggle.
- Esclusi come non-dati: `.venv`, `orch-venv`, `orchestrator`, `ciclo`, `archivio_repo`, `__pycache__`;
  nessuna credenziale si carica.
- La cartella di lavoro della sessione R-LEAD attiva (`processed/generalizzazione_contesti_2026-10-02/`)
  non si copia finché la sessione la sta scrivendo.
