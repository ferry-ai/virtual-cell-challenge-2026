# Ingestione generica di schermi scaricati, e il controllo sul bersaglio

## Gli strumenti

- **`h5ad_sums.py`.** Somme dei conteggi grezzi per (bersaglio, gruppo di lotti) da un h5ad a righe per cellula, nel
  formato di `../universo_kolf_2026-09-27/kolf_sums.py`. La stima passa poi per `kolf_effects.py` (opzioni `--name` e
  `--context`, aggiunte da codex il 27/09).
  - Opzioni aggiunte il 27/09 sera: l'indice dei geni si legge dall'attributo `_index` di anndata (il job 047 era
    fallito lì); `--inspect` stampa layers e colonne; `--keep COL=VALORE` tiene solo le cellule che rispettano la
    condizione.
  - Provato su dati sintetici: somme, cellule, librerie e geni assenti coincidono con il calcolo diretto.
- **`on_target_check.py`.** L'effetto del bersaglio sul proprio gene, per ogni bersaglio di un universo.

## Usi del 27/09 (misurato)

| Sorgente | Dove | Esito |
|---|---|---|
| A549, knockout Cas9 di 1.000 geni (GSE345058) | Colab, job 048 | 606.075 cellule, 45.320 controlli, 8.008 gruppi, 17.156 geni dell'asse nel file; somme in `interim/a549_sums_r2/` |
| Southard, CRISPRa di 1.836 fattori di trascrizione, fibroblasti Hs27 | Colab, job 049 | in corso: solo cellule con una guida (`num_cells` = 1: 220.403 di 447.301) |
| Southard, stesso schermo in RPE-1 | Colab, job 050 | in corso: 321.770 cellule con una guida su 850.225 |

La struttura dei file è stata letta a intervalli di byte prima di scaricarli: GEO per A549, Zenodo per Southard.

## Controllo sul bersaglio: quanto scende il gene silenziato (misurato)

`controlli_bersaglio/` e `../universo_kolf_2026-09-27/effetti_me1/controllo_bersaglio.json`. Log-fold-change naturale
del gene bersaglio, bersagli con il proprio gene misurato:

| Universo | Bersagli | Mediana | Sotto −0,5 | z ≤ −3 |
|---|---|---|---|---|
| K562 (`effects_from_bulk`) | 7.420 | −1,81 | 91 % | 81 % |
| CD4 a riposo | 9.454 | −1,77 | 86 % | 79 % |
| CD4 stimolato 48 h | 9.599 | −1,68 | 85 % | 81 % |
| HCT116 | 9.561 | −1,00 | 81 % | 64 % |
| KOLF2.1J (nuovo) | 8.372 | −0,83 | 75 % | 47 % |
| HEK293T | 11.141 | −0,62 | 64 % | 64 % |

**Misurato:**
- in ogni universo il gene bersaglio scende: i gruppi sono assegnati bene, anche nel nuovo KOLF2.1J;
- la profondità mediana del silenziamento va da circa l'84 % (K562, CD4) al 46 % (HEK293T).

**Ipotesi, da provare con una regola sua:** la media a pesi uguali del t22 mescola silenziamenti profondi e poco
profondi. Riportare la risposta di ogni sorgente a una profondità comune, dividendola per il suo effetto mediano sul
bersaglio o per quello del singolo bersaglio, potrebbe ridurre il rumore del trasferimento. L'ampiezza verrebbe poi
fissata dalla profondità attesa nel contesto di gara, che non si misura: si sa solo che le perturbazioni sono state
scelte forti.

**Cautele:**
- l'effetto sul proprio gene dipende dallo stimatore (il K562 ne usa un altro) e dall'espressione del gene;
- i bersagli senza misura (gene poco espresso, nessun donatore con evidenza) sono esclusi dal conteggio.

## Aggiunte della sera del 27/09 (misurato)

- **A549 (knockout Cas9) stimato:** 1.000 bersagli su 1.000 con effetti (`kolf_effects.py --name a549`; indice e
  manifest in `a549_me1/`). Controllo sul bersaglio (`controlli_bersaglio/a549.json`): gene proprio misurato in 827
  bersagli, mediana −0,54 (quartili −0,79 e −0,28), z ≤ −3 nell'83 %. Il knockout abbassa l'mRNA meno del CRISPRi, ma
  i gruppi sono assegnati bene.
- **`basal_from_sums.py`:** il CPM dei controlli di una sorgente dalle sue somme, con la stessa definizione della
  tabella del 26/09. Ne esce `processed/basal_sources_2026-09-27.csv`: le colonne del 26/09 più `kolf` (146.747 cellule
  di controllo) e `a549` (45.320).
- **Ipotesi della profondità, messa alla prova:** la normalizzazione per profondità mediana della sorgente non ha
  sostegno ([profondità del silenziamento](../profondita_silenziamento_2026-09-27/RISULTATI.md)). Bersaglio per
  bersaglio la relazione c'è, ma è debole.
