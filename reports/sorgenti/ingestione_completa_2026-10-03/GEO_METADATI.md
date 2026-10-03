# Tre serie GEO: che cosa si scarica a livello di cellula e quanto pesa

3 ottobre 2026, dopo le 16:18 CEST (ora letta con `date`), regia dell'ingestione (sessione `22d21f`). Grok ci ha
provato due volte (run `20261003-155552-vcc-geo-metadata` e `20261003-160553-vcc-geo-metadata-r2`), ma si è fermato
all'annuncio della ricerca: il fetch web non legge il testo di GEO, e le richieste HTTP dirette gli servirebbero
dalla shell, negata nell'hub. Questa nota viene da richieste dirette a GEO:
- il riassunto della serie, `acc.cgi?acc=<GSE>&targ=self&form=text&view=brief`;
- l'elenco dei supplementari, `ftp.ncbi.nlm.nih.gov/geo/series/<GSEnnn>/<GSE>/suppl/`, con il `filelist.txt` del
  tar.

Misurato: dimensioni e nomi come GEO li dichiara. Non è stato scaricato nessun file di dati.

| Serie | Esperimento (dal riassunto GEO) | File per cellula | Peso | Valore per il corpus |
|---|---|---|---|---|
| **GSE337988**, DLD-1 | CRISPRi (Zim3-dCas9 inducibile) a più MOI: pilota con 35 geni in 4 canali e sei MOI; esperimento grande con sottolibreria di **5.000 geni** a MOI bassa (~0,3), media (~3) e alta (~10), in 44 canali | `GSE337988_RAW.tar` (26.495.651.840 byte): per canale `filtered_feature_bc_matrix.h5`, `raw_feature_bc_matrix.h5`, `crispr.umi_correct.h5` (UMI delle guide per cellula), `hashing.umi_correct.h5`, metriche; più oggetti elaborati per MOI (`sublib2_processed_objects_<Low/Med/High>_assays.h5`, 4,3/1,7/1,1 GB, e `_se.rds`), matrici DE, fogli dei campioni | circa 26,5 GB il tar, circa 10 GB gli oggetti elaborati | **alto:** linea nuova, CRISPRi, 5.000 bersagli. Le cellule a MOI alta portano più guide: per la supervisione a bersaglio singolo vale la MOI bassa, o le cellule con una sola guida chiamata |
| **GSE335887**, microglia | CRISPRi in microglia derivate da iPSC (due protocolli di differenziamento, iTF-MG e iMG), pool CROP-seq su **31 geni**, 8 campioni | `*_filtered_feature_bc_matrix.h5` (105 e 139 MB), `*_raw_feature_bc_matrix.h5`, `GSE335887_iTF_processed_merged_crop.h5ad` (2,7 GB), `*_processed_cite_crop.h5mu` (520 e 778 MB) | circa 4,4 GB | **basso per numero di bersagli**, ma è un tipo cellulare nuovo; riserva candidata secondo INGESTIONE §4 |
| **GSE291147**, PerturbFate | Melanoma: 143 coppie di guide su **143 geni** più controlli, con DMSO o vemurafenib; piattaforma a indicizzazione combinatoria (non 10x), RNA più ATAC; 320 campioni | RNA: `*_RNA_gene_count_matrix.RDS` (302, 403 e 663 MB), sgRNA in RDS, metadati in CSV; ATAC in h5ad (2,3 e 3,8 GB) | circa 1,4 GB l'RNA | **medio-basso:** farmaco come fattore confuso, chimica diversa, RDS che richiede R (lo stesso convertitore di Mixscale) |

**Sintesi:**
- **DLD-1** è la sola che vale un'acquisizione per intero subito. Il tar va letto canale per canale: si estrae dal
  tar sul runtime e si converte con un adattatore per 10x h5 più la chiamata delle guide da `crispr.umi_correct.h5`.
  Gli oggetti elaborati per MOI servono da confronto per l'assegnazione.
- **Microglia:** piccola, va presa per intero perché costa poco; il ruolo lo decide R-LEAD.
- **PerturbFate:** dopo Mixscale, con lo stesso convertitore R.
- Licenze: GEO non le dichiara nel riassunto; vanno verificate negli articoli prima dell'uso negli invii.
