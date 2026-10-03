# Brief per claude2: conversione RDS (Mixscale e VIPerturb) in shard di contratto

Da: regia dell'ingestione completa (Claude Code, sessione `22d21f`), 3/10/2026. Lanciato con l'autorizzazione del
proprietario in chat. Lavori in un worktree isolato: le tue modifiche tornano come `diff.patch` e le applica la regia.
Leggi prima `CLAUDE.md` alla radice, poi `reports/sorgenti/ingestione_completa_2026-10-03/README.md` e
`reports/sorgenti/archivio_cloud_2026-10-02/INGESTIONE.md` §4–5.

## Il compito: solo codice e test

Nell'hub non hai shell né rete, quindi niente download, niente job e niente esecuzione: i test li esegue la regia.

Due sorgenti, da portare nel contratto degli shard del corpus (`reports/sorgenti/corpus_cellulare_2026-09-30/`:
`contracts.py`, `shard_writer.py`, `adapters.py` per lo stile delle etichette):
- **Jiang 2025 = Mixscale**, Zenodo 14518762: 5 `Seurat_object_*_Perturb_seq.rds`, 20,14 GB in tutto, md5
  pubblicati. CRISPRi in sei linee (A549, MCF7, HT29, HAP1, BxPC3, K562) con stimoli (IFNG, IFNB, INS, TGFB,
  TNFA).
- **VIPerturb**, Zenodo 18460279: `genome_wide_filtered.rds` (3,61 GB) più tre file bin (10,23 GB). K562, chimica
  Flex.

Scrivi in `reports/sorgenti/ingestione_completa_2026-10-03/rds/`:
1. `rds_inspect.R`, che legge un RDS con R base e il pacchetto `Matrix`, **senza** Seurat. Accede agli slot S4 sia
   di Seurat v3/v4 (`obj@assays$RNA@counts`) sia di v5 (`obj@assays$RNA@layers$counts`, con i nomi delle celle e
   delle feature nei relativi slot). Stampa in JSON: forma, tipo della matrice, colonne di `meta.data` con tipo ed
   esempi, e le prime righe.
2. `rds_to_parts.R`, che scrive conteggi interi a blocchi di cellule (per esempio 20.000), in un formato che
   Python legge senza R: CSC o CSR binario con `writeBin` più un JSON di forma e tipi, oppure Matrix Market a
   blocchi. Scrive anche barcode, feature e `meta.data` in CSV, e un manifest con lo sha256 di ogni parte.
   Controlla la memoria: non converte l'intera matrice in denso.
3. `rds_adapter.py`, guidato da una specifica JSON, nello stile delle spec di `wave2_specs.py`:
   - legge le parti, mappa le feature sull'asse ufficiale (`_official` di `adapters.py`) e scrive shard di
     contratto;
   - le etichette sono colonna del bersaglio, valori dei controlli, guide, libreria, condizione o stimolo, e linea
     cellulare come contesto;
   - conta le esclusioni per motivo;
   - la linea cellulare resta un'etichetta per cellula: quattro linee di Mixscale sono candidate alla riserva, e
     il ruolo lo decide R-LEAD, non l'ingestione.
4. `test_rds_adapter.py`, con fixture scritte in Python nel formato delle parti (niente R nei test): mappatura
   dell'asse, controlli, esclusioni contate, parità fra righe lette e scritte, riletture degli shard con il
   validatore del contratto.
5. `build_rds_job.py`, che costruisce il launcher Colab nello stile di
   `reports/sorgenti/corpus_cellulare_2026-09-30/colab_job.py` e delle regole di `docs/ERRORI.md`: manifest con
   sha256 di tutti gli input, preflight sul runtime, `apt-get install -y r-base r-cran-matrix`, download da Zenodo
   con controllo dell'md5 pubblicato, conversione, shard su Drive in una cartella nuova, ricevute. Le colonne di
   `meta.data` non le conosciamo ancora: il primo job è solo ispezione, e la spec della conversione si scrive dopo.
6. Un `README.md` della cartella, che dica che cosa è scritto, che cosa è provato e che cosa no.

## Non toccare

- `reports/sorgenti/corpus_cellulare_2026-09-30/`;
- `reports/sorgenti/ingestione_completa_2026-10-03/adattatori_codex/`;
- `reports/modelli/`;
- `docs/`;
- `G:/`.

Niente commit: li fa la regia dopo la revisione.

## Consegna

Il rapporto finale elenca:
- i file scritti;
- le scelte fatte, per esempio il formato delle parti e la gestione di Seurat v5;
- che cosa resta da verificare su un runtime con R;
- i punti in cui non eri sicuro della struttura di un oggetto Seurat.

Tutto ciò che non hai eseguito va dichiarato come «scritto, non eseguito».
