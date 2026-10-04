# Fonti del transfer: più tabelle aggregate contro le fonti della ricetta, su linee nuove

**Stato: congelato** con il commit che contiene questo testo, il 4/10/2026 notte, prima che esista qualunque uscita
delle linee di confronto. Scritto da Claude Code, sessione `2b35612c`, programma
[R-LEAD](../../../docs/piani/strategia-scientifica.md), su richiesta del proprietario del 4/10 («confronto secondario»).

## 1. Domanda e che cosa si sapeva già

Il transfer dello stesso bersaglio con più fonti batte quello delle fonti della ricetta inviata (t22/t25)? Si misura
a parità di bersagli, generatore, supporto e sei membri.

**Indizio esplorativo, già letto, che questo protocollo non conferma da solo.** Nelle corsie B del pilot v4 (media dei
sei membri, scala locale) `transfer_cells_J` e `transfer_all_J` superano `transfer_prod_J` su H1 (0,280 e 0,272
contro 0,248) e su HepG2 (0,245 e 0,212 contro 0,141). Fonti: `esito/laneB_h1_r1/bench/scaled_local.csv` e
`esito/lanes_hepg2_r1_kaggle/laneB/bench/scaled_local.csv` del [pilot v4](../../modelli/rete_ancorata_v4_2026-10-03/README.md).
Su RPE1 le corsie v4 erano in corsa al congelamento. Questo testo non usa quei numeri per scegliere soglie e non le
chiama conferma.

## 2. Confronto

- **Bracci** (regole di fonti di `anchors.py` della v4, medie delle tabelle nel regime J, ampiezza t25):
  `transfer_prod_J` (le tabelle della ricetta t22/t25: K562 GWPS, CD4T, HCT116, HEK293T), `transfer_cells_J` (i gruppi
  con cellule del corpus pilot) e `transfer_all_J` (tutte le tabelle aggregate del cubo r2). La linea esclusa non è mai
  fra le fonti.
- **Linee:** Jurkat e K562, le linee di conferma del
  [protocollo D-056](../../modelli/ibrido_selettivo_2026-10-04/PROTOCOLLO.md), nessuna delle quali ha contribuito
  all'indizio. Bersagli: le righe C scelte da `choose_targets.py` (150, sale `six-member`). Cellule vere da
  `kaggle_extract.py`, generatore trial-01 con seme 20260912. I tre bracci sono già nella corsia B di `hybrid_lanes.py`
  (`transfer`, cioè `transfer_all_J`, poi `transfer_cells_J` e `transfer_prod_J`): stesse cellule, stessi bersagli,
  stesso generatore. Non serve un calcolo in più.
- Con K562 esclusa, la regola `production` perde K562 GWPS e resta con CD4T, HCT116 e HEK293T. È il confronto
  coerente con la domanda: quali fonti aiutano una linea che non è fra le fonti.

## 3. Regola

**Primaria (corsia B, media dei sei membri in scala locale):** per X in {`transfer_cells_J`, `transfer_all_J`},
`X − transfer_prod_J`. «Più fonti meglio» per X se la differenza è > 0 su entrambe le linee, e quindi anche in media.
Con una sola linea valutata l'esito è «indizio su una linea», non conferma.
**Secondarie, senza soglia:** i membri uno per uno; la corsia A (PDS, coseno, coseno specifico, rapporto MSE sulle
righe C); `transfer_cells_J − transfer_all_J`.

## 4. Invio di un candidato di solo transfer (regola del proprietario del 4/10)

Un candidato «transfer con più fonti» per A/B/C è ammesso al grading se:
- il suo punteggio di banco, cioè la media dei sei membri scalati, macro-media a peso uguale su Jurkat e K562 (regime
  C), è ≥ 0,100;
- la regola primaria qui sopra passa per quel braccio.

Il candidato inviato usa le stesse regole di fonti, con le medie delle tabelle su tutte le righe ammesse, perché per
A/B/C nessun bersaglio è nascosto. Usa poi l'ampiezza t25, il generatore e il seme del t22, e i controlli dei contesti
di gara. Prima dell'invio servono la previsione registrata con la regola di lettura (PROCEDURE §1–2) e una prova di
parità: con le sole fonti della ricetta, la stessa catena deve riprodurre gli effetti del t25. Si descrive come
transfer, non come modello appreso.

## 5. Precedenti

- **S-003** (miscele a posteriori): qui non si mescolano previsioni; si confrontano regole di fonti fissate prima.
  Il rischio comune è scegliere dopo aver visto: la regola sopra fissa bracci, linee e soglia prima di ogni uscita.
- **S-007** (correzioni dai controlli medi): non c'entra il contesto della linea nuova; cambiano solo le fonti.

**Segnale precoce e arresto:** se nella prima linea completata `transfer_prod_J` batte entrambi i bracci con più
fonti, l'esito si scrive come «indizio non replicato» e nessun candidato di solo transfer si prepara per A/B/C prima
della seconda linea.
