# P4 a dieci gruppi: bracci semplici e rete sul pseudobulk, letti con le regole congelate

3 ottobre 2026. Il banco esteso a dieci gruppi di linea (i sette di P3 più Jurkat, H1 train/val e i neuroni di Tian
2021, dalle somme calcolate su Kaggle) è stato caricato come dataset privato `davideferrante11/rlead-bench-cube-r2`
(cubo `cube_r2`, 13.425 geni, 4.212 chiavi) e letto da due kernel con lo stesso codice di P3/P4:

- **CPU** `davideferrante11/rlead-bench-cpu-r1`: `p3_run.py` (C), `decide.py`, `p3_run_j.py` (J), `decide.py`. Le due
  decisioni, calcolate nel kernel, sono copiate senza modifiche in [`p4_decision_c_r3/`](../p4_decision_c_r3/decision.json) e
  [`p4_decision_cj_r3/`](../p4_decision_cj_r3/decision.json); gli output completi sono in
  `processed/generalizzazione_contesti_2026-10-02/kaggle_cpu_r1/`.
- **GPU** `davideferrante11/rlead-bench-nn-r1`: `nn_residual.py`, 34 minuti; output in `kaggle_nn_r1/`. Regola della
  rete applicata in locale con i riferimenti `p3_c_r3` del kernel CPU: questa cartella (`decision.json`, scritto alle
  03:21:56 UTC).

Tutti numeri **misurati**, su linee già lette (sviluppo); indici sugli effetti, non punteggi VCC.

| Regime | Confronto | Media sui gruppi | Gruppi positivi | Esito |
|---|---|---:|---:|---|
| C | `m1` − `tm0` (coseno) | 0,0000 | 6 su 10 | miglior nullo −0,0005; non passa |
| C | `m2` − `m2_0` | −0,0005 | 4 su 10 | miglior nullo +0,0068; non passa |
| C | `tm0` − transfer | +0,044 | 10 su 10 | PDS −0,101: non passa |
| C | `m2_0` − transfer | +0,0098 | 9 su 10 | PDS −0,0004: non passa |
| J | `jm1` − `jm1_0` | +0,0010 | 6 su 10 | miglior nullo +0,0003; non passa |
| J | riferimento senza memoria − generico (PDS) | +0,0084 | — | riferimento valido |
| C | rete `nn` − `nn0` (coseno specifico) | −0,0037 (bootstrap −0,0069…−0,0004) | 2 su 10 | nulli −0,0034, −0,0042, −0,0058; non passa |
| C | rete `nn0` − transfer | +0,0117 | 5 su 10 | PDS −0,162: non passa |

Esito delle tre regole: `no_benefit` in C e in J per i bracci semplici, `no_benefit` per la rete.

**Interpretazione.** Tre linee in più non fanno emergere un beneficio dal contesto letto dai controlli medi, né con
guadagni per gene, né con la correzione bilineare, né con la rete non lineare: nella rete il contesto peggiora di poco,
con un intervallo tutto negativo. L'ipotesi di P4 («più linee collegate, non più capacità»), con queste tre linee, non
trova sostegno. La calibrazione senza contesto `m2_0` è l'unica a non perdere quasi nulla in PDS (−0,0004) pur alzando
il coseno in 9 gruppi su 10: è un'osservazione descrittiva, non una regola passata. Da qui il programma passa alla rete
cellulare ([pilot](../../../modelli/rete_cellulare_2026-10-03/PROTOCOLLO.md)), per richiesta del proprietario; questi
numeri ne sono la baseline.
