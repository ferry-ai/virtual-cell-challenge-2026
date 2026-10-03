# Ingestione completa dei dataset cellulari (dal 3 ottobre 2026)

**Mandato del proprietario in chat, 3/10 dopo le 15:28 CEST:** portare a termine l'ingestione in fretta, anche in
parallelo su più account Colab, e prendere **tutti i dataset per intero**, con 5 TB dichiarati su Drive.

**Regia:** Claude Code, sessione «R-LEAD implementazione vcc2026» (`22d21f`); assegnazioni nella scheda
[R-LAB](../../../docs/piani/piano-giorno-2026-09-30.md). Il piano di partenza è
[INGESTIONE.md](../archivio_cloud_2026-10-02/INGESTIONE.md), con il §5 dei download, e la
[revisione di Codex](../revisione_ingestion_2026-10-03/README.md), con le quattro correzioni provate e i limiti aperti.

Ci sono tre livelli distinti, come nella revisione:
- **archivio delle sorgenti**: le sorgenti restano sui loro host, con locatori, ETag e checksum registrati;
- **corpus idoneo**: tutte le cellule idonee in shard di contratto su Drive, con le esclusioni contate per motivo;
- **campione del training**: lo decide R-LEAD dopo, con split congelati e ruoli registrati (H1 test e D/E/F chiusi).

«Per intero» vale per il corpus idoneo, non per il training.

## Sorgenti

Lo stato si legge ai file citati, non da questa tabella, che è un indice.

| Sorgente | Dimensione e formato | Codice | Chi | Stato al 3/10, 15:45 |
|---|---|---|---|---|
| Southard RPE1 e Hs27 (CRISPRa) | 29,75 + 9,72 GB h5ad, Zenodo | spec `j09` r3, `h5rows` del corpus | Claude | in coda: job 132, `queue2` (r1 e r2 persi con i runtime) |
| KOLF2.1J pan-genome | 189,4 GB h5ad CSC, Figshare+; 2.659.209 cellule, 7,87 miliardi di valori | `h5csc` con bucket compatti e intervalli di cellule | Codex (adattatore), Claude (job) | da fare |
| CD4, Marson 2025 | 12 h5ad CSR su S3, 1.735,8 GB; 33,6 milioni di cellule | `h5rows` con filtro di idoneità ed esclusioni contate | Codex (adattatore), Claude (job) | da fare |
| Orion, HCT116 e HEK293T | 109 + 223 parquet, 126,3 GB, Hugging Face | `orion_job.py` corretto da Codex, in modalità completa | Claude | da fare |
| Jiang 2025 = Mixscale | 5 RDS Seurat, 20,14 GB, Zenodo | conversione con R sul runtime | Claude | da fare |
| VIPerturb (K562, Flex) | RDS 3,61 GB più tre bin, Zenodo | conversione con R | Claude | da fare |
| microglia GSE335887, PerturbFate GSE291147, DLD-1 GSE337988 | da misurare | solo metadati, poi decisione | Claude | da fare |
| Verifica dell'archivio | 816 + 4.334 file su Drive | `verify_resume.py` | Claude | in coda: job 133–134, `queue`, che riprendono da 130–131 |

## Parallelismo, con i vincoli misurati

- **Colab, stesso account:** i dispatcher sono due, `runs/queue` e `runs/queue2`, ognuno con il proprio log; li
  avvia il proprietario dal browser. Il 3/10 il runtime di `queue` si è perso dopo le 13:21 UTC: battito fermo, e
  il proprietario vede Colab scollegato. I job interrotti si rimettono in coda con numero e output nuovi.
- **Colab, altri account:** su un Drive personale un file creato da un altro account in una cartella condivisa
  conta sulla quota di quell'account, non sui 5 TB. Gli altri account possono quindi convertire e pubblicare su
  Kaggle, ma non archiviare in massa su Drive.
- **Quota di Drive:** `G:` mostra lo spazio del disco del portatile, non la quota. La quota si misura dal runtime,
  con `df -h /content/drive`, che i job nuovi stampano all'avvio.
- **Kaggle:** ogni account ha 200 GB di dataset privati. `davidmaisterx` ne usava circa 108 il 2/10. Su Kaggle va
  il campione del training, non tutto il corpus idoneo di CD4.

## File

| File | Che cosa |
|---|---|
| `verify_resume.py` | Copia di `archivio_cloud_2026-10-02/verify_drive.py` che salta i file già verificati con lo stesso sha256 da ricevute precedenti (`--already`); test: `test_verify_resume.py` |
| `requeue_verify.py` | Rimette in coda 130 e 131 come 133 e 134: stesso setup r1 in sola lettura, setup r2 e output nuovi, preflight locale |
