# CP-0061 — Pilot v4: la rete ancorata peggiora la propria ancora su tre linee su tre

- **Data:** 2026-10-04
- **Tipo:** esperimento
- **Redatto da:** Claude Code (Opus 5.5), sessione 2b35612c, su R-LEAD
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** S-006

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

La rete ancorata v4 (basale dai controlli + guadagno × ancora del transfer + correzione appresa sulle cellule) prevede
meglio della propria ancora sulle linee escluse intere H1, HepG2 e RPE1? Si legge con la regola congelata del §7 del
[protocollo v4](../../reports/modelli/rete_ancorata_v4_2026-10-03/PROTOCOLLO.md) e con il requisito di promozione
del §10.4.

## 2. Cosa è stato fatto

- Tre training su Kaggle GPU (`rcell-v4-train-{h1,hepg2,rpe1}-r1`), i primi due dalle 23:06 del 3/10 e RPE1 dalle 00:42
  del 4/10. Le ricevute tecniche sono state scaricate senza i file di valutazione e accettate secondo il §5 prima di
  generare; sono in `esito/train_<linea>_r1/` della cartella v4.
- Generazione delle cellule (`rcell-v4-gen-<linea>-r1`) e corsie A e B. Per H1 le corsie sono girate in locale
  (`laneA_h1_r1`, `laneB_h1_r1`); la parità con Kaggle è verificata a 4·10⁻¹⁶. Per HepG2 e RPE1 sono girate su Kaggle CPU
  (`rcell-v4-lanes-{hepg2,rpe1}-r1`, stesso pacchetto di codice `de729e47…`, scorer `cell-eval2` 0.16.0).
- Regola: `decide_anchored.py --line H1 … --line HepG2 … --line RPE1 …` eseguito il 4/10 alle 03:47, uscita
  [decision.json](../../reports/modelli/rete_ancorata_v4_2026-10-03/esito/decision_r1/decision.json).

## 3. Cosa si è osservato

- **Accettazione tecnica (§5): tre linee su tre** (`accepted` in decision.json). Per RPE1: uscita 0, 365 gemelli
  verificati, nessuna cellula non di training, esposizione passata in 60 finestre su 60 con 7 gruppi a 1/7, salute al
  passo 5.000 passata, valutazione completa in 590 s, ancore a regime J. Sono 30.375 passi (2,0 epoche) in 6.147 s,
  1.265 cellule/s, attesa dei dati 0,634 (`esito/train_rpe1_r1/train/`).
- **Primaria, corsia B (`ancorata_shift − transfer_all_J`, media locale dei sei membri):** H1 −0,214, HepG2 −0,050,
  RPE1 −0,131; macro −0,132; 0 linee positive su 3. **Non passa.**
- **Guardia, corsia A (PDS delle righe C, `ancorata − transfer_all_J`):** H1 −0,418, HepG2 −0,248, RPE1 −0,255; media
  −0,307 contro la soglia −0,02. **Non passa.**
- **Requisito di promozione (§10.4), contro `transfer_prod_J`:** corsia B H1 −0,191, HepG2 +0,021, RPE1 −0,095, macro
  −0,088; corsia A −0,284. **Non soddisfatto.**
- **Medie locali dei sei membri** (`local_avg`; per RPE1
  [scaled_local.csv](../../reports/modelli/rete_ancorata_v4_2026-10-03/esito/lanes_rpe1_r1_kaggle/laneB/bench/scaled_local.csv)):

  | Braccio | H1 | HepG2 | RPE1 |
  |---|---:|---:|---:|
  | `transfer_all_J` (l'ancora) | 0,272 | 0,212 | 0,192 |
  | `transfer_cells_J` | 0,280 | 0,245 | 0,233 |
  | `transfer_prod_J` | 0,248 | 0,141 | 0,156 |
  | `ancora_sola_shift` (l'ancora passata per la rete) | 0,275 | 0,216 | 0,191 |
  | `ancorata_shift` | 0,057 | 0,162 | 0,061 |
  | `ancorata_mean_shift` | 0,042 | 0,107 | 0,052 |
  | `ancorata_cells` (cellule generate dalla rete) | −0,079 | −0,374 | −0,187 |

- Membro PDS della corsia B, `ancorata_shift − transfer_all_J`: −0,837, −0,511 e −0,424. La perdita è soprattutto di
  discriminazione fra bersagli (`secondary.laneB_by_member` di decision.json).

## 4. Interpretazione e incertezza

- **Misura:** su tre linee escluse intere, tecnicamente accettate, la correzione appresa peggiora sempre la propria
  ancora. L'ancora passata per la rete (`ancora_sola_shift`) riproduce il transfer: il danno viene dalla correzione.
- **Interpretazione, ipotizzata, non isolata (S-006):** la correzione impara uno spostamento comune ai bersagli delle
  linee di training. Il log di H1 mostra `shift_minus_anchor_rms` 0,33 contro 0,13 dell'ancora già al passo 100. Su una
  linea nuova quello spostamento copre il segnale specifico. Togliere la media sui bersagli recupera gran parte ma non
  tutto il PDS (studio esplorativo di H1 e HepG2, S-006).
- **Secondario, già noto come indizio:** lo stato delle cellule aiuta rispetto al profilo medio (`ancorata` −
  `ancorata_mean` +0,015, +0,055 e +0,009), ma resta molto sotto il transfer. `transfer_cells_J` supera
  `transfer_prod_J` su tutte e tre le linee. Queste tre linee sono quelle dell'indizio: un confronto con regola propria
  è congelato in `reports/trasferimento/fonti_transfer_2026-10-04/PROTOCOLLO.md` su Jurkat e K562.
- Limite: tre linee, un seme, un corpus pilot a 8 gruppi (D-053: non è il percorso completo).

## 5. Spiegazione semplice

Si voleva insegnare a una rete a «ritoccare» una previsione già buona, il transfer, guardando le cellule di controllo
della linea nuova. La rete ha imparato un ritocco uguale per tutti i geni spenti, tipico delle linee di addestramento.
Su una linea nuova quel ritocco somiglia a una vernice stesa su tutto: i diversi interventi diventano più difficili da
distinguere, e il risultato è peggiore del punto di partenza.

## 6. Conseguenze

- Il candidato v4 è chiuso con esito negativo. La famiglia non è bocciata: il §7 del protocollo vieta di ritararlo
  su queste tre linee, ormai lette.
- La direzione D-056 (ibrido selettivo) parte da questo meccanismo. Il protocollo
  `reports/modelli/ibrido_selettivo_2026-10-04/PROTOCOLLO.md` (congelato a `817f42a`) separa la risposta comune con una
  testa che non entra nella previsione, fissa il guadagno, penalizza la correzione e si ferma su guardie interne. Un
  selettore fuori fold decide il peso, che può anche essere zero.
- Nessun invio neurale da questo candidato; il transfer t22/t25 resta il riferimento di produzione.

## 7. Cosa corregge

Nessuna conclusione precedente. Chiude il pilot v4 aperto in [CP-0060](0060-direzione-x-transfer-pilot-v4.md), che
riportava due linee su tre e RPE1 in corso.

## 8. Domanda di comprensione

Perché l'ancora passata per la rete (`ancora_sola_shift`) segna quasi quanto il transfer, mentre la rete completa no?
(Perché il danno viene dalla correzione appresa, non dal modo in cui la rete applica l'ancora.)
