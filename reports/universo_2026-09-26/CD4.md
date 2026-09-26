# Cache "universo" di CD4 genome-wide: tutti i bersagli, non solo i 300

26 settembre 2026, sera. Filone F1 della scheda [R-V2](../../docs/piani/modello-v2.md), parte CD4,
dopo il via del proprietario al download (pseudobulk genome-wide, 44,6 GB, bucket S3 pubblico).
Script `cd4_universe.py`; uscite in `C:/Users/ferra/vcc2026-data/processed/universe_cd4_2026-09-26/`
(336 blocchi npz, 5,8 GB, `index.csv`, `manifest.json` con byte e sha256 di ogni blocco); copia
dell'indice e del manifest in `r2/`.

## Sorgente

`GWCD4i.pseudobulk_merged.h5ad` (GSE314342, Marson 2025), 44.566.657.140 byte, scaricato il 26/09 dalle
13:26 alle 14:16 UTC con richieste HTTP a intervalli in parallelo, dimensione controllata contro
`Content-Length`. URL, byte e sha256 del file locale nel `.manifest.json` accanto al file (l'etag S3 è
multiparte e non si confronta con lo sha256).

## Come

Lo stesso percorso degli stadi 97 e 98, esteso a ogni bersaglio:
- righe come le sceglie lo stadio 97 per il pannello: tutte le righe mirate di un bersaglio, tutte le
  guide, senza i filtri degli autori sull'efficacia osservata (selezionerebbero sull'esito), e le stesse
  2.400 righe non mirate (200 per donatore × condizione, seme 2026); ogni riga controllata contro il
  proprio `total_counts`;
- effetti come lo stadio 98: `effects_from_pseudobulk` per condizione di coltura (Rest, Stim8hr,
  Stim48hr) contro i controlli dello stesso donatore, `AxisTable.from_source` sull'asse ufficiale, e
  `cd4_mix` = media pesata per affidabilità delle tre condizioni (gamma 0; ristretti e grezzi mescolati a
  parte; SE lasciato vuoto come nella cache).

## Che cosa contiene (misurato, `r2/manifest.json`)

- **12.238 bersagli**, 293 del pannello attuale, 11.602 geni dell'asse ufficiale; mediana di 1.554,5
  cellule per bersaglio (somma delle condizioni); 84 gruppi di bersagli, il primo è il pannello.
- **Parità con la cache del pannello** (`multisource_2026-09-23_r5`) sui 293 bersagli del pannello:
  grezzi, ristretti e SE identici (differenza massima 0) nelle tre condizioni, stesso schema dei valori
  mancanti; su `cd4_mix` differenza massima 1,5 × 10⁻⁸ (arrotondamento float32).
- Sette bersagli del pannello non sono in nessuna delle due: ABCD1, C5orf22, EEF1A2, EPHB2, FZD2,
  LENG1, NICN1.
- 2.926 secondi.

## Limiti

La parità è controllata sui bersagli del pannello; sugli altri vale perché il codice è lo stesso, non per
un confronto indipendente. Il SE di `cd4_mix` si ricostruisce dalle condizioni (`mixture_se`) quando
serve; il banco dell'atlante lo fa così.
