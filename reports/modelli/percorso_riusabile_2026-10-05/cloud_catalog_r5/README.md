# ARCHIVIO DATI â€” indice corrente r5

Percorso principale: archivio â†’ banca/campioni â†’ training esteso.
Manifest `manifest.json`, SHA256 `88ff456055dc50dd67cc8ddc9636ee3b15167596f255ebb0c2e7b783e019455e`; usare account/versioni/percorsi/hash,
mai un archivio storico per somiglianza del nome o un fallback al pilot r2.

- Grezzi perturbazionali conservati: **395,75 GB**. [Tabella delle fonti](../DATI_DISPONIBILI_r2.md).
- CD4, KOLF, HCT116 e **HEK293T** chiusi nei campioni; HEK ha tutte le sei parti
  e unione verificata, **27,26 GB** (`snapshot_parts_r5`), senza riscaricare matrici.
- Oltre a HepG2, verificate otto chiusure di job: Jurkat, H1 train/val, RPE1,
  K562 essenziale, SCP Tcells (3 unitÃ ), SCP K562/HEK (4 unitÃ ), KOLF piccoli
  (2 unitÃ ) e KOLF forte. Prove in `archive_completion_batch_r1`.
- Norman Ã¨ giÃ  chiuso dentro il job Tian fallito; iPSC ha banca salvata.
  `tian_partial_r1` conserva i riferimenti. Il problema dei campioni sono righe
  con popolazione misurata zero: restano in banca, non generano cellule fittizie.
- HIPSCI genome-wide richiede partizione per capienza output: `hipsci_partition_r1`.
  Le parti conservano gruppi BIO/target interi; momento, maschera e campione
  uguali alla versione non partizionata nella fixture. Unione reale ancora aperta.
- Cinque input pubblici autorizzati, altri archivi e nuovi derivati privati.
  Accesso del trainer da verificare; gli output di un job fallito possono essere
  recuperabili via API e comunque rifiutati come input notebook. Riparare accesso
  salvando solo gli artefatti necessari, non rifacendo ingestion o banca.

**Training esteso non ancora avviato.** Riconciliazione del catalogo, QC/ruoli,
controlli per tutte le parti, reader nel trainer, split D-053 e ricevute effettive
di consumo/loss restano necessari. Questo indice non certifica quei passi.
