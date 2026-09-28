# Tahoe-100M, controlli DMSO: le due estrazioni

28 settembre 2026. Scrive Claude (app desktop, sessione `f4f38e58`). Codice:
- `extract_dmso.py`, di codex, legge tutti i frammenti con un piano preliminare;
- `extract_dmso_subset.py`, del lead, legge un frammento ogni k.

Contratti del dataset in [LAYOUT.md](LAYOUT.md). Etichette: **misurato**, **interpretazione**.

## Sottoinsieme, un frammento ogni cinque (misurato, portatile, 28/09 03:26–03:41)

| Voce | Valore |
|---|---|
| frammenti letti | 678 su 3.388, 2,69 GB con richieste a intervalli di byte, 12 connessioni |
| cellule DMSO (`DMSO_TF`) | 434.966 |
| gruppi linea × piastra | 700 (50 linee, 14 piastre) |
| tempo | 904 s |

- **Verifica:** sul frammento 1031 le somme sono identiche al bit a quelle di un ciclo per cellula sul file scaricato
  intero (1.364 cellule DMSO, 49 gruppi).
- **Nel frammento 1031** le cellule DMSO stanno in 3 gruppi di righe consecutivi su 29: il piano per gruppi di righe
  evita di leggere il resto.
- **Uscite nella radice dati:**
  - `interim/tahoe_dmso_subset_s5_u/`, con le stringhe in unicode;
  - `interim/tahoe_dmso_subset_s5/`, la stessa estrazione salvata con array di oggetti.
- **Da qui** il corpus `tahoe` dell'encoder (650 profili in 48 linee, `../corpus_basale_2026-09-28/`).

## Estrazione completa (misurato, Kaggle CPU, kernel `vcc-tahoe-dmso`, dal 27/09 sera)

| Voce | Valore |
|---|---|
| frammenti pianificati | tutti i 3.388 |
| frammenti con cellule DMSO | 1.850 |
| gruppi di righe letti | 4.048 |
| cellule DMSO in tutto | **2.205.786** |
| byte letti per l'estrazione | 13,7 GB (`extraction_column_bytes`), contro 338 GB del dataset intero |
| tempo | 40.787 s, di cui 26.665 s per il piano; appena sotto il limite di 12 ore di Kaggle |
| campione per linea | fino a 3.000 cellule (144.955 in tutto; due linee ne hanno meno) |

`complete: true`.

- **Le uscite** restano nell'uscita del kernel sul conto Kaggle del proprietario:
  - `pseudobulk.npz` con tutte le cellule DMSO per linea × piastra;
  - `cells.npz` con il campione;
  - il manifest.

  Sul portatile c'è solo il manifest (`kaggle/out_tahoe_dmso_full/`).
- **Rispetto al sottoinsieme:** il sottoinsieme ha circa un quinto delle cellule (434.966 contro 2.205.786), in
  proporzione ai frammenti letti.

**Interpretazione.** Per i profili linea × piastra il sottoinsieme bastava; l'estrazione completa serve se un giorno
servono più cellule per linea (sottoinsiemi di cellule, profili per piastra con più cellule).
