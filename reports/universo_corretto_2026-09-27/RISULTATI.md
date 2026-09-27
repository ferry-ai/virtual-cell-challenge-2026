# Universi ricostruiti con lo stimatore corretto

`rebuild.py` riesegue gli script del 26/09 (`../universo_2026-09-26/orion_universe.py` e `cd4_universe.py`),
invariati, con `effects_from_pseudobulk(..., min_expected=1)`. Questo scarta, gene per gene, un donatore i cui
controlli prevedono meno di un conteggio nel gruppo del bersaglio
([pseudoconteggio](../pseudoconteggio_2026-09-27/RISULTATI.md)). Controllo di parità: sui bersagli del pannello
l'universo nuovo deve coincidere con la cache del pannello r9, costruita dallo stadio 98 con lo stesso stimatore.

## Esito (misurato, 27/09)

| Sorgente | Bersagli con effetti | Pezzi | Parità con r9 (bersagli del pannello) | Fine (UTC) |
|---|---|---|---|---|
| HCT116 | 16.438 su 18.293 | 28 (2.300 MB) | 268 su 268; raw, SE e shrunk identici (0 valori diversi) | 15:23 |
| HEK293T | 17.270 su 18.311 | 29 (2.619 MB) | 281 su 281; raw, SE e shrunk identici (0 valori diversi) | 15:54 |
| CD4 | in corso | | | |

Uscite: `processed/universe_orion_hct116_2026-09-27_me1` e `processed/universe_orion_hek293t_2026-09-27_me1` nella
radice dei dati; qui `index.csv`, `manifest.json` e `correzione.json` di ogni sorgente. Il K562 non si ricostruisce:
passa per `effects_from_bulk`, che non ha l'artefatto.
