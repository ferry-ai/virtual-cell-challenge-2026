# Margini all'orizzonte: quanto può chiudere il solo generatore

4 ottobre 2026, verso l'1:30, ora del PC. Su richiesta del proprietario: «continua a provare la strada e vedere se ci
sono all'orizzonte importanti margini di cambiamento». È il passo 1 della proposta del 3/10 sera: il disaccoppiamento
dell'ampiezza fra i membri basati sulle medie (MSE, nMAE) e quelli basati sui ranghi (Wilcoxon), con la ricetta del
t28 come base.

**Nessuna corsa nuova.** Solo il codice dello scorer installato (cell_eval2 0.16.0) e numeri ufficiali già nel
repository. Conti in [conti.py](conti.py), uscita in [conti.json](conti.json).

## 1. Che cosa fa lo scorer (letto nel codice)

Percorso: `vcc2026-data/.venv/Lib/site-packages/cell_eval2/`.

- **Wilcoxon contro i controlli veri.** `competition.py`: `CONTROL_SOURCE_SCORED = "real"`. `run.py`, riga 900: il
  riferimento del DE è il controllo reale, non quello inviato. Il test è `sc.tl.rank_genes_groups(method="wilcoxon")`
  su log1p dei CPM per cellula (`de_compute.py`, righe 167 e 871). Conseguenza: ogni differenza di forma fra le nostre
  cellule e i controlli veri (zeri, dispersione, profondità) diventa una chiamata, anche senza effetto.
- **nMAE sui logFC delle medie aritmetiche dei CPM per cellula** (`configs/vcc2026.yaml`: `mean_calc: arithmetic`),
  sui soli geni DE veri, con il cancello `filter_gene_min_cpm_cell: 5` calcolato sul riferimento.
- **MSE sulle composizioni aggregate** (`bulk_target_sum` 50.000, comparatore `bulk_lognorm`), senza il gene del
  bersaglio, normalizzata così che 1,0 = «ho previsto il controllo». La correzione di campionamento della previsione è
  limitata due volte (#247 e #348, `metrics/delta.py`, `mse_unbiased_capped`): gli autori hanno chiuso le scorciatoie
  sulla dispersione delle cellule inviate. Il disaccoppiamento non può passare da lì.

## 2. MSE: il margine è chiuso per la nostra direzione attuale

**Misurato:** il t30, generatore del t22 con effetti circa 20 volte più piccoli, ha MSE grezza **1,038**. È il punto a
effetto zero del generatore (`u0`): già sopra la base delle ancore (circa 0,99), quindi scalato 0.

**Calcolo** (modello di AUDIT_SCIENTIFICO §2.5, `u(a) = u0 + P a² − 2 C a`, minimo `u0 − cos²`), con t25 (3,017) e
t28 (effetti t25 ×1,5, 5,800):

| `u0` | coseno stimato | MSE grezza all'ampiezza ottima | MSE scalata |
|---|---|---|---|
| 1,038 (misurato, t30) | 0,133 | 1,020 | **0** |
| 1,000 (ipotesi favorevole) | 0,113 | 0,987 | 0,003 |

- **Per avere MSE scalata sopra zero** serve un coseno di almeno **0,22**; per la mediana delle prime 100 squadre
  (grezza 0,77) almeno **0,52**.
- **Limite del calcolo:** due punti per due incognite, con `u0` preso da un altro invio; il t28 cambia anche la
  dispersione. Il segno della conclusione regge in entrambe le ipotesi su `u0`.
- **Correzione di quanto detto in chat il 3/10 sera:** avevo stimato per l'MSE «da 0 a +0,012» sulla media. Con `u0`
  misurato il contributo è **0** (al più +0,0005 nell'ipotesi favorevole).

## 3. Dove sta il distacco, membro per membro (t28 contro le mediane della classifica del 28/09)

Contributo alla media (scalato / 6):

| Membro | t28 | Mediana prime 100 | Distacco sulla media | Leva | Raggiungibile col solo generatore? |
|---|---|---|---|---|---|
| MSE | 0 | 0,227 | **0,038** | direzione (coseno ≥ 0,52) | no |
| PDS | 0,622 | 0,759 | **0,023** | direzione specifica del bersaglio | no |
| nMAE | 0,049 | 0,139 | 0,015 | ampiezza sulle medie | in parte: il t25 aveva 0,118, cioè **+0,0115** |
| reach | 0,199 | 0,211 | 0,002 | ranghi | già vicino |
| fedeltà | −0,007 | 0,001 | 0,001 | ranghi | già vicino |
| Jaccard | 0,006 | 0,003 | sopra | — | — |

## 4. Lettura

- **Misurato:** sui membri a ranghi il t28 è già vicino alla mediana delle prime 100.
- **Interpretazione:** il generatore da solo può valere circa **+0,01** (tenere i guadagni Wilcoxon del t28 con la
  nMAE del t25), cioè circa 0,155. Sono 2–6 volte il rumore del seme, ma restano lontani dalle prime 100 (0,219).
- **Interpretazione:** circa 0,06 dei 0,074 di distacco (MSE e PDS) chiede direzioni migliori, con un coseno da circa
  0,1 a 0,3–0,5. Nessuna delle strade provate l'ha dato: la rete sulle sorgenti (t30), le linee pubbliche (t31), il
  modello condizionato (t07), la rete cellulare (t29).
- **Ipotesi per il disaccoppiamento sulla nMAE:** a media fissa, il Wilcoxon vede più o meno zeri a seconda della
  dispersione per gene. Si potrebbe quindi tenere la media al livello del t25 e spostare i ranghi con la forma della
  distribuzione nel verso dell'effetto. Il rischio è creare chiamate false sui geni senza effetto, perché il
  confronto è con i controlli veri. Va misurato solo su un banco.
- **Non dice:** nulla su D, E, F; le mediane della classifica sono del 28/09 e aggregate fra A, B, C.
