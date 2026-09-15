# Come aprire il notebook su Colab (catalogo multi-sorgente)

Ricarica **zip e notebook nuovi** dal Desktop. Lo zip precedente non contiene
`recommend_fetch_ids`.

Il run Colab `catalog_2026-09-15T143641Z` **ha funzionato come piano**:
`FETCH_BLOCKS` era `[]`, quindi `plan_only=True` e nessun download. Non è un
fallimento del fetcher.

| File | Ruolo |
|---|---|
| `C:\Users\ferra\OneDrive\Desktop\vcc2026-colab.ipynb` | notebook unico |
| `C:\Users\ferra\OneDrive\Desktop\vcc2026-colab.zip` | codice + `gene_names.csv` + catalogo. Niente matrici |

1. File → Carica notebook → `vcc2026-colab.ipynb` **nuovo**
2. Runtime CPU (il file da 65,8 GiB è I/O, non GPU). Se la VM è quella del piano, cancella
   `/content/vcc-bundle` e `/content/vcc2026-colab.zip` **prima** della prima cella,
   altrimenti riestrae lo zip vecchio
3. Prima cella: accetta il mount di Drive, poi carica `vcc2026-colab.zip`
4. Preflight: legge RAM e disco **adesso** (il 87,25 GiB del pilot è storico)
5. `FETCH_BLOCKS = None` sceglie da solo dopo il preflight:
   HepG2 se manca (e l'md5/size non coincide), poi K562 GW se Drive è montato
   e il disco lascia il pavimento
6. Senza Drive il persist è `/content/vcc-persist` (muore con la VM): HepG2
   si può rifare, il file da 65,8 GiB **non** parte
7. HepG2: se la dimensione coincide, **non** si riscarica
8. Se Drive è montato, matrici e report stanno in
   `/content/drive/MyDrive/vcc2026/`. Altrimenti scarica `catalog_<timestamp>`
   **prima** che la VM muoia

Override: `FETCH_BLOCKS = ['k562_gwps_raw_singlecell']` dopo il preflight.
`DRY_RUN = True` ristampa solo il piano. `ALLOW_EPHEMERAL_LARGE = True`
sblocca i 65,8 GiB sul disco della VM (si perdono alla morte del runtime).

K562 GW single-cell misurato: **65.830.941.948 byte**, non «61,3 GB».
Il piano locale (`reports/remote_catalog_2026-09-15/`) **non** è una prova Colab.
