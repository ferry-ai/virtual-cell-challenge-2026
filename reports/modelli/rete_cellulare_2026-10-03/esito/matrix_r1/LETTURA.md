# Bersagli per linea di training, e gli errori della corsia A per numero di linee (descrittivo)

3 ottobre 2026, kernel CPU `davideferrante11/rcell-matrix-r1` (`target_matrix.py` sugli stati dei tre prepass). È la
domanda di Codex: sette gruppi di linea non vogliono dire sette contesti per bersaglio. Analisi descrittiva, fuori dalla
regola del pilot. Misurato.

**Quante linee di training vedono ogni bersaglio.** Le cellule contate sono quelle ammesse, dopo QC ed esclusioni, di
etichette a bersaglio singolo; si conta ogni modalità (CRISPRi, CRISPRa, KO).

| Linea esclusa | Bersagli addestrati | in 1 linea | in 2 | in 3 | in 4 | in 5+ |
|---|---:|---:|---:|---:|---:|---:|
| H1 | 8.380 | 5.281 | 1.081 | 68 | 1.004 | 946 |
| HepG2 | 8.388 | 5.223 | 1.118 | 1.083 | 772 | 192 |
| RPE1 | 8.388 | 5.223 | 1.117 | 1.085 | 771 | 192 |

Il 63% dei bersagli è insegnato da una sola linea, quasi sempre K562 genome-wide.

**I bersagli valutati (classe C).**
- HepG2 e RPE1: tutti visti in almeno 3 linee (HepG2: 892 in 3, 688 in 4, 168 in 5–6; RPE1: 900, 714, 180).
- H1: 66 su 151 in una sola linea, 31 in due, 54 in 3 o più.

**Corsia A per numero di linee** (r3, PDS sulle righe C del cubo, `cells` contro il transfer con le stesse
informazioni):

| Linea | Linee per bersaglio | PDS `cells` | PDS transfer | Scarto | `cells` − `mean` |
|---|---|---:|---:|---:|---:|
| HepG2 | 3 / 4 / 5–6 | 0,587 / 0,649 / 0,603 | 0,871 / 0,875 / 0,897 | −0,28 / −0,23 / −0,30 | +0,02 / +0,07 / +0,10 |
| RPE1 | 3 / 4 / 5–6 | 0,516 / 0,534 / 0,509 | 0,852 / 0,875 / 0,904 | −0,34 / −0,34 / −0,40 | −0,05 / −0,03 / −0,00 |

**Lettura.** Su HepG2 e RPE1 lo scarto della rete dal transfer non si riduce con il supporto: anche i bersagli insegnati da
4–6 linee restano molto sotto. Qui il limite sta nell'apprendimento della risposta del bersaglio da parte della rete, non
nel numero di contesti. Su H1, dove il 64% dei bersagli ha al più due linee, la stessa lettura si fa quando il suo
training r3 è finito.
