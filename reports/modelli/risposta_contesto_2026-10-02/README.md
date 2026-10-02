# risposta_contesto_2026-10-02 — codice di R-LEAD P0–P3

Codice di ricerca di [R-LEAD](../../../docs/piani/strategia-scientifica.md), sessione Claude `22d21f`,
2 ottobre 2026. Le misure, i manifest, il protocollo e la decisione stanno in
[generalizzazione_contesti_2026-10-02](../../analisi/generalizzazione_contesti_2026-10-02/README.md);
i dati pesanti nella radice dati, `processed/generalizzazione_contesti_2026-10-02/`.
Nessun file qui è importato da altri banchi; ogni corsa scrive in una cartella nuova.

| File | Passo | Che cosa fa |
|---|---|---|
| `registry.py` | P0 | Le tabelle di effetti leggibili, con linea, gruppo, donatore, stato, studio, saggio, modalità, disponibilità delle cellule e fonte di ogni attributo; sorgenti non locali |
| `hepg2_universe.py` | P0 | Universo HepG2 dalle cellule locali con lo stimatore vivo (`min_expected` 1) e due metà indipendenti |
| `p0_inventory.py` | P0 | Preflight (git, interprete, scorer `vcc2026`, risorse), manifest degli input con hash, matrice contesto × bersaglio × studio, alias, collegamenti, confondimenti |
| `splits.py` | P1 | Fold per hash della chiave Ensembl, esclusioni C/J/T, regime dopo QC, controllo di leakage |
| `p1_splits.py` | P1 | Manifest degli split con prova di stabilità, esposizioni (r2/r3 dai loro prepass, transfer di produzione), storia delle riserve |
| `cube.py` | P2 | Il cubo del banco: bersagli collegati × geni comuni per tabella, basali dai controlli |
| `arms.py` | P3 | Bracci: generico, transfer t25, guadagni per gene con e senza contesto, bilineare a basso rango, scambio, permutazioni |
| `metrics.py` | P2 | Indici sugli effetti (coseno pesato, PDS a blocchi di 300, parte specifica, segno, MSE relativo) |
| `p3_run.py` | P3 | Corsa del regime C su tutti i gruppi, con audit delle letture |
| `decide.py` | P3 | Applica la regola congelata di `PROTOCOLLO.json` e scrive `decision.json` |
| `test_splits.py`, `test_p3_synthetic.py` | P1–P3 | Fixture di alias, studi della stessa linea, QC, corpus che cresce; controllo positivo e negativo dell'intera catena |

Esecuzione: `.\scripts\py.cmd reports\modelli\risposta_contesto_2026-10-02\<file>.py --help`.
Test: `.\scripts\py.cmd -m unittest discover -s reports/modelli/risposta_contesto_2026-10-02 -p "test_*.py"`.
