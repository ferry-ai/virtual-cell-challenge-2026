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
| `adattatori_codex/` | Compito di Codex: `h5csc` compatto a intervalli (KOLF) e `h5rows` con filtro di idoneità (CD4) |
| `orion/` | Orion completo: copia del codice corretto da Codex, spec `orion_full_v1.json` (k = 10⁹, π = 1), `--part i/n`, test (27), `build_orion_job.py` e i job 135–142 in `jobs/` |
| `notebooks/colab_dispatcher_queue3.ipynb`, `notebooks/colab_dispatcher_queue4.ipynb` (nella cartella `notebooks/` della repo) | Dispatcher delle code 3 e 4, una copia anche su Drive in `vcc2026/notebooks/`, con log `dispatcher_q3.log` e `dispatcher_q4.log` |
| `GEO_METADATI.md` | Dimensioni e formati per cellula di DLD-1, microglia e PerturbFate, letti direttamente da GEO |
| `HANDOFF_CLAUDE2.md` | Passaggio di consegne a claude2 delle 16:25: stato, code, prossimi passi, autorizzazioni e trappole; aggiornamenti delle 16:38 e delle 17:16 |
| `DIMENSIONAMENTO.md` | Quanto del corpus entra in un training: velocità misurata dei training r3, quota e limiti di Kaggle, peso degli shard, stime del corpus convertito, proposta (corpus ridotto con tutti i contesti, CD4 a tranche) e prezzi di altri cloud |
| `kaggle_cpu/` | Ingestione su kernel CPU di Kaggle al posto del secondo Colab: prova di rete (`nettest_run.py`, `esito_nettest_r1/`), costruttore Orion r1 e log del suo errore (`build_orion_kaggle.py`, `esito_orion_r1/`), costruttore Orion r2 con il controllo del codice per sha256 e, con `--part-rule`, la regola che giudica una parte come parte (`build_orion_kaggle_r2.py`), registro delle spinte (`lancio_orion_r2.jsonl`), costruttore del dataset del codice e dei kernel di KOLF (`build_kolf_kaggle.py`) |
| `kolf/` | KOLF pan-genome per intervalli di cellule: `kolf_job.py` (parti contigue tagliate ai multipli del blocco, parità della parte, conteggio delle letture HTTP), `complete_adapters.py` (copia identica dell'adattatore di Codex delle 16:14, sha256 `8b937e66…`), spec `kolf_pan_v1.json`, test su una fixture (`test_kolf_job.py`, 3 test) |
| `agenti/` | Brief e rapporti degli agenti dell'hub, lanciati con l'autorizzazione del proprietario del 3/10: claude2 per la conversione RDS (run `20261003-155531-vcc-rds-conversion`, worktree isolato), Grok per i metadati GEO (run `20261003-155552-vcc-geo-metadata`, sola lettura) |
