# Corsia A per numero di linee che insegnano il bersaglio, con H1 (descrittivo)

3 ottobre 2026, dopo le 14:28 CEST (ora letta con `date`). `support_strata.py` unisce le righe C della corsia A r3 con
la matrice di [`matrix_r1`](../matrix_r1/LETTURA.md). È la lettura su H1 che quella nota rimandava a fine training. Ci
sono due conteggi:
- `groups_any`: ogni modalità, basta una cellula ammessa. È il conteggio della lettura originale, e su HepG2 e RPE1 ne
  riproduce i numeri.
- `groups_crispri`: solo CRISPRi, almeno 20 cellule per coppia bersaglio/linea. È la sensibilità di Codex, di cui
  riproduce i 125 e 143 bersagli con al più due linee.

Tutto misurato in [`strata.csv`](strata.csv).

**H1** (72 righe C del cubo; la valutazione della rete ne ha 151, quindi la composizione degli strati è diversa da
quella della matrice):

| Linee (`groups_any`) | Bersagli | PDS `cells` | PDS transfer | `cells` − transfer | `cells` − `mean` |
|---|---:|---:|---:|---:|---:|
| 1 | 14 | 0,382 | 0,848 | −0,467 | −0,085 |
| 2 | 6 | 0,576 | 0,968 | −0,392 | +0,009 |
| 3 | 1 | 0,194 | 1,000 | −0,806 | −0,597 |
| 4 | 13 | 0,617 | 0,892 | −0,275 | +0,004 |
| 5+ | 38 | 0,632 | 0,972 | −0,340 | +0,099 |

Con il conteggio stretto la forma è la stessa: 1 linea −0,467 (14 bersagli), 4 linee −0,313 (26), 5+ −0,358 (21).

**Lettura (interpretazione):**
- Su H1 i bersagli insegnati da una sola linea sono i peggiori per la rete: PDS 0,38 contro 0,62–0,63 con quattro o più
  linee. Sono anche gli unici in cui `cells` perde contro `mean`.
- Lo scarto dal transfer resta grande anche con quattro o più linee, da −0,28 a −0,36.
- Gli strati confrontano bersagli diversi. Anche il transfer è più basso sui bersagli di una linea (0,85 contro 0,97),
  quindi difficoltà del bersaglio e supporto sono confusi.
- Gli strati sono piccoli: uno strato ha un solo bersaglio.

Vale la formulazione della [nota dopo Codex](../matrix_r1/NOTA_CODEX.md): la scarsità di linee non spiega da sola lo
scarto, e il beneficio di più contesti si isola solo con un confronto annidato sugli stessi bersagli.
