# HIPSCI CRISPRi: dallo scaricamento agli universi

## Fatto (misurato)

- **Scaricamento:** record Figshare 26819743 e 27989294 (MIT, 17 GB), verificati con md5 (`download.py`).
- **Somme (`hipsci_sums.py`, codex, autoverifica 12 su 12 dopo le aggiunte del 27/09 notte):** i conteggi,
  geni × cellule, sono letti a righe senza caricarli interi, nel formato di `kolf_sums`, con la chiave `context`.

## I due schermi, e le scelte che impongono (misurato dai metadati, 27/09 notte)

- **Schermo genome-wide** (due librerie: geni di fitness al giorno 3, gli altri al giorno 6; linee mescolate in
  pool di otto):
  - cellule per bersaglio: mediana 41 (fitness) e 22 (le altre);
  - **cellule con guida non mirata: solo 36 e 12.**
  - Con 8 gruppi di lotti e questi controlli gli universi `gwfit_me1` e `gwnonfit_me1` hanno effetti per 950 bersagli
    su 2.252 e 253 su 4.954, stimati contro una decina di cellule di controllo per gruppo. **Non sono affidabili e
    non si usano.** Restano su disco come traccia della corsa.
  - Gli autori usano come controlli le cellule non mirate **più quelle senza guida assegnata**: nei loro script
    ricorre `control_tag <- c("unassigned", "NonTarget")`, per esempio `13b_01_calc_lfcs_...` in
    `external/hipsci/authors_scripts/`.
  - **Scelta:** la stessa, con `--unassigned-as-control` e un solo gruppo di lotti (`_ua1`), in corso.
  - **Cautela:** fra le cellule senza guida ci possono essere cellule perturbate con la guida non rilevata; il loro
    peso, sparso su migliaia di bersagli, è piccolo per ciascuno, ma può spingere gli effetti verso zero.
- **Schermo mirato:**
  - 19 linee (non 34), 444 bersagli, circa 61.000 cellule per linea, tutte al giorno 3;
  - controlli non mirati: mediana 488 per linea (minimo 86);
  - cellule per (linea, bersaglio): mediana 74; il 97 % ha almeno 10 cellule.
  - Nel file dei conteggi gli identificativi delle cellule perdono il giorno: `PC-P4-D3_I73_…` dei metadati è
    `P4_I73_…`. La corrispondenza è corretta nel codice e registrata nel manifest (`id_rule`); 1.161.864 cellule su
    1.161.865 trovano i metadati.
  - **Scelta:** controlli solo non mirati, per confrontare le linee in modo pulito. Gli 8 gruppi della corsa in corso
    si riducono a 2 con `../universo_nuovi_2026-09-27/repool_sums.py`, senza rileggere i conteggi, perché con 8
    gruppi restano circa 9 cellule per gruppo.

## Perché conta

Lo schermo mirato mette gli stessi 444 bersagli in 19 linee dello stesso tipo cellulare, che differiscono per
genotipo. È la prova più pulita dell'interazione bersaglio × contesto (E2), perché elimina tipo cellulare,
laboratorio e protocollo. Gli autori stimano la varianza dovuta alla linea negli script `14c`, `14d` e `14f`.
