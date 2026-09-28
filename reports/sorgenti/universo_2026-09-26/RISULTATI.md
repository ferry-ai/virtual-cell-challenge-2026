# Cache "universo" del K562 genome-wide: tutti i bersagli, non solo i 300

26 settembre 2026, notte. Filone F1 della scheda [R-V2](../../docs/piani/modello-v2.md).
Script `k562_universe.py`, uscite in `C:/Users/ferra/vcc2026-data/processed/universe_k562_2026-09-26/`
(17 blocchi npz nel formato dello stadio 98, `index.csv`, `manifest.json`); copia dell'indice e
del manifest in `r1/`.

## Che cosa contiene (misurato, `r1/manifest.json`)

- **9.866 bersagli** del pseudobulk K562 genome-wide (Replogle 2022), 585 righe di controllo;
  272 sono bersagli del pannello attuale, 9.510 sono anche geni dell'asse ufficiale.
- Mediana di 178 cellule per bersaglio.
- Stessa stima dello stadio 98 (`k562_table`): log fold change naturale, errore standard
  quasi-Poisson, restrizione locale `z_shrink`. 973 MB su disco, 255 secondi.

## A che cosa serve

- **Addestrare** modelli per bersagli nuovi su migliaia di knockdown invece che su 300
  ([esperimento](../bersagli_nuovi_2026-09-26/)).
- **Il 22 ottobre:** per i 300 bersagli nuovi di D/E/F la parte K562 è già calcolata; resta da
  estrarre CD4 e Orion, che richiedono letture remote (stadi 97 e 102) e il via del proprietario.

## Limiti

Una sola sorgente; per le altre il 26 settembre la cache copre ancora solo il pannello. Nessuna
verifica oltre la parità con lo stadio 98, di cui usa la funzione.
