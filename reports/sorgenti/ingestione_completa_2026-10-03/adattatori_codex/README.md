# Adattatori per l'acquisizione completa: compito di Codex

Assegnato il 3/10 verso le 15:50 CEST dalla regia (Claude Code, sessione `22d21f`), su offerta di Codex tramite la
relay `vcc2026-1c`. È registrato nella scheda [R-LAB](../../../../docs/piani/piano-giorno-2026-09-30.md). Questa
cartella è di Codex: il resto di `ingestione_completa_2026-10-03/` è della regia.

## Che cosa serve, e perché

1. **`h5csc` per KOLF2.1J pan-genome.** Il file pesa 189,4 GB: h5ad CSC, 2.659.209 × 37.567, 7,87 miliardi di
   valori float32 interi (misura in
   `../../corpus_cellulare_2026-09-30/p1_r5/remote_kolf/kolf_KOLF_Pan_Genome_QC_Filtered.json`). L'adattatore
   attuale (`adapters.py:h5csc`) rilegge tutta la matrice per ogni intervallo di `cells_per_pass` cellule, e salva
   i bucket in int32 + int32 + float32, cioè 12 byte per valore. Con circa 100 GB di disco Colab servirebbero 4–5
   passate, quasi 1 TB letto. Le richieste sono quattro:
   - bucket compatti: righe nel blocco e geni in uint16 quando ci stanno, valori uint16 quando sono interi
     ≤ 65.535, altrimenti float32, con il controllo che decide e lo registra;
   - un parametro `cell_range=(lo, hi)`, perché due runtime si dividano lo stesso file;
   - la scelta di `cells_per_pass` dal disco libero misurato;
   - la parità con il lettore a righe sulle fixture, compresa l'unione di due intervalli uguale al tutto, come
     `../../corpus_cellulare_2026-09-30/test_csc.py`.
2. **`h5rows` con filtro di idoneità per CD4** (Marson 2025: 12 file `D{1..4}_{Rest,Stim8hr,Stim48hr}`, CSR,
   colonne misurate in `../../corpus_cellulare_2026-09-30/p1_r4/remote/cd4_*.json`). Le regole sono quelle di
   [INGESTIONE §3](../../archivio_cloud_2026-10-02/INGESTIONE.md):
   - idonee: `low_quality == False`;
   - bersagliate: `guide_group == "targeting single sgRNA"`;
   - controlli: `guide_type == "non-targeting"` con guida singola;
   - «no sgRNA» e «multi sgRNA» restano fuori e si contano.

   Il bersaglio va per ID Ensembl, con il simbolo dall'asse. Donatore e condizione vengono dal nome del file, la
   libreria da `lane_id`. Le esclusioni si contano per motivo, per file e per corsia, in un JSON accanto agli
   shard. Si scrivono solo le righe idonee, **tutte**: niente campionamento in questo livello. Fixture: un h5ad
   piccolo con le stesse colonne e categorie.

## Regole

- Si lavora su copie, in questa cartella. Il codice dei job in corso resta intatto, in
  `../../corpus_cellulare_2026-09-30/` (il job 132 ne usa uno snapshot).
- Niente job Colab o Kaggle e niente download: li lancia la regia dopo l'integrazione.
- Non si toccano: `G:/Il mio Drive/vcc2026/runs/`, `reports/modelli/rete_*_2026-10-03/` e gli altri file di
  `ingestione_completa_2026-10-03/`.
- Si consegnano codice, test e una nota su che cosa è misurato e che cosa no, con commit a percorsi espliciti.
