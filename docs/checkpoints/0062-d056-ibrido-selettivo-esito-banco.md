# CP-0062 — D-056 v1: l'ibrido selettivo batte il transfer su cinque linee escluse, in sviluppo e in conferma

- **Data:** 2026-10-04
- **Tipo:** esperimento
- **Redatto da:** Claude Code (Opus 5.5), sessione 2b35612c, su R-LEAD
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** S-009, S-010, S-006

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il primo candidato D-056 migliora il transfer su linee mai viste? È `ibrido = T + w · R`: T è il transfer congelato,
R la correzione di una rete sulle singole cellule (regolarizzata, testa comune esclusa dalla previsione, arresti
preregistrati) e w il peso di un selettore stimato fuori fold. Si legge con le regole congelate del §8 (sviluppo e
conferma) e del §9 (punteggio di banco degli invii) del
[protocollo](../../reports/modelli/ibrido_selettivo_2026-10-04/PROTOCOLLO.md), congelato a `817f42a` prima di ogni
training. Ci sono tre emendamenti, ciascuno scritto prima delle uscite che tocca: §12 per l'obiettivo del selettore,
§13 per il candidato A/B/C e §14 per l'esportazione.

## 2. Cosa è stato fatto

- **Codice:** trainer v5 e rete (`train_cellnet.py`, `cellnet.py`), guardie (`guards.py`), righe e corsie
  (`hybrid_lanes.py`), selettore (`selector.py`), regole (`decide_hybrid.py`) e accettazione (`accept_training.py`),
  con 27 test (`test_hybrid_train.py`, `test_guards.py`, `test_selector.py`, `test_train_v4.py`). Tutti nella cartella
  `reports/modelli/ibrido_selettivo_2026-10-04/`.
- **Training su Kaggle GPU:** cinque linee escluse intere sul corpus pilot a 8 gruppi.
  - Sviluppo, account principale: H1, HepG2, RPE1.
  - Conferma, account di replica con i dataset copiati byte per byte e il cubo condiviso in lettura: Jurkat, K562.
  - Ricevute in `esito/train_<linea>_r1/`.
- **Righe e corsie su Kaggle CPU:**
  - righe C per il selettore (`esito/rows_<linea>_r1/`);
  - corsia A sugli indici del cubo e corsia B sui sei membri in scala locale, con `cell-eval2` 0.16.0
    (`esito/lanes_<linea>_r1/`).
- **Selettore:**
  - leave-one-line-out sulle tre linee di sviluppo (`esito/selector_lolo_r1/`);
  - sistema congelato su tutte e tre (`esito/selector_final_r1/selector_final.json`, sha256 `00758778…`), committato
    in `833ee20` prima di ogni uscita di Jurkat e K562;
  - pesi delle linee di conferma da quel file, senza leggerne l'esito (`esito/selector_apply_{k562,jurkat}_r1/`,
    commit `61841e0` e `5caa638`).
- **Regole:** `decide_hybrid.py` sulle cinque linee
  ([decision.json](../../reports/modelli/ibrido_selettivo_2026-10-04/esito/decision_full_r1/decision.json), commit
  `b3a1918`).

## 3. Cosa si è osservato

- **Accettazione tecnica (§10): cinque linee su cinque.**
  - Gemelli verificati, nessuna cellula non di training, esposizione passata.
  - Nessuna cellula di validazione con peso nella loss.
  - Nessun arresto per guardia; parità `ibrido_w0` esatta in ogni corsia B (0 voci diverse).
  - Stato esportato e beneficio interno: H1 passo 20.000, +0,140; HepG2 20.000, +0,143; RPE1 25.000, +0,133;
    Jurkat 12.500, +0,142; K562 12.500, +0,114 (`esito/train_<linea>_r1/train/val.json`).
- **Medie locali dei sei membri della corsia B** (`lines` di decision.json):

  | Linea | Ruolo | `transfer` | `rete` (w = 1) | `miscela_fissa` | `ibrido_selettivo` | w medio |
  |---|---|---:|---:|---:|---:|---:|
  | H1 | sviluppo | 0,272 | 0,273 | 0,275 | 0,278 | 0,29 |
  | HepG2 | sviluppo | 0,212 | 0,268 | 0,241 | 0,275 | 0,59 |
  | RPE1 | sviluppo | 0,192 | 0,192 | 0,246 | 0,232 | 0,33 |
  | Jurkat | conferma | 0,176 | 0,166 | 0,179 | 0,213 | 0,33 |
  | K562 | conferma | −0,403 | −0,329 | −0,409 | −0,329 | 0,31 |

- **Sviluppo (§8):** `ibrido_selettivo − transfer` vale +0,006, +0,063 e +0,040: 3 linee su 3, media +0,037, peso
  medio ≥ 0,05 ovunque. Esito: **«contributo neurale nello sviluppo»**.
- **Conferma (§8):** +0,037 (Jurkat) e +0,074 (K562). La guardia della corsia A (PDS delle righe C,
  `ibrido_selettivo − transfer`) vale +0,006 e +0,002 contro la soglia −0,02. Esito: **«confermato»** su due linee.
- **Punteggio di banco del §9** (macro sulle cinque linee, scala locale, non uno score VCC):

  | Braccio | Punteggio |
  |---|---:|
  | `ibrido_selettivo` | 0,134 (≥ 0,100: ammesso al grading) |
  | `rete` | 0,114 |
  | `miscela_fissa` | 0,106 |
  | `transfer` | 0,090 |
  | `transfer_prod_J` | 0,021 |

- **Secondarie** (`secondary` di decision.json):
  - `selettivo − miscela_fissa` è positivo in 4 linee su 5 (RPE1 −0,014);
  - `rete − transfer` è +0,001…+0,074 tranne Jurkat (−0,009);
  - `ibrido − ibrido_mean` (contributo dello stato delle cellule) vale +0,002, +0,017, −0,013, −0,051 e +0,062: non
    coerente.
- **Su K562 tutti i bracci sono sotto il baseline in scala locale.** La causa è il membro JAC: −4,3…−4,9, contro 1 del
  replicato (`esito/lanes_k562_r1/laneB/bench/scaled_local.csv`). Il membro MSE è 0 per ogni braccio su ogni linea,
  perché la scala locale lo tronca a [0, 1] (`vcc2026.bench.scale`).
- **Confronto delle fonti del transfer**, con la regola congelata in
  `reports/trasferimento/fonti_transfer_2026-10-04/PROTOCOLLO.md`, dalle stesse corsie B:
  - `transfer_cells_J − transfer_prod_J` vale +0,113 (Jurkat) e +0,105 (K562);
  - `transfer_all_J − transfer_prod_J` vale +0,073 e +0,142;
  - «più fonti meglio» passa per entrambi i bracci;
  - nessun candidato di solo transfer è ammesso: il punteggio di banco su Jurkat e K562 è −0,112 (cells) e −0,114
    (all), sotto 0,100 per il JAC di K562.

## 4. Interpretazione e incertezza

- **Misura:** su cinque linee escluse intere la correzione neurale, pesata dal selettore, migliora il transfer nella
  media locale dei sei membri, anche sulle due linee su cui nessun componente era stato tarato. È il primo esito
  positivo di una rete sulle cellule in questo progetto (S-001, S-002, S-006 erano negativi).
- **Interpretazione:** il disegno toglie il meccanismo ipotizzato di S-006. Lo indicano la quota comune della
  correzione nelle guardie interne (0,12–0,20 contro la soglia 0,5) e il rapporto d'ampiezza 0,55–0,72. Anche il PDS
  delle righe C (corsia A) non scende più sotto il transfer. Non è un isolamento causale: cambiano insieme testa
  comune, guadagno fisso, penalità e selettore.
- **Il selettore aiuta, ma non in modo uniforme.** Batte la miscela fissa in 4 linee su 5. I guadagni fuori fold sulle
  righe (errore quadratico pesato) sono però piccoli: +0,4 %, −1,8 % e +0,4 % per il selettore, +0,3…+0,9 % per la
  miscela (`esito/selector_lolo_r1/summary.json`). Il guadagno sui sei membri è più grande di quanto quell'obiettivo
  faccia prevedere.
- **Limiti:**
  - un seme;
  - corpus pilot a 8 gruppi: D-053 chiede tutte le linee, e questo non è il percorso completo;
  - due linee di conferma, una delle quali (K562) è in scala locale negativa per tutti i bracci;
  - il punteggio di banco è in scala locale e non si traduce numericamente nel sito;
  - la scala locale di K562 è dominata dal JAC.
- **Fonti del transfer:** su linee nuove le tabelle aggregate in più battono quelle della ricetta inviata. È la regola
  passata, non ancora un candidato inviabile.

## 5. Spiegazione semplice

Il transfer prevede l'effetto di un intervento su una linea nuova facendo la media di quanto lo stesso intervento fa
nelle linee già misurate. La rete guarda le cellule di controllo della linea nuova e propone un ritocco per ciascun
intervento. Un piccolo arbitro, allenato solo su linee che la rete non aveva visto, decide quanto ritocco tenere: in
media un terzo. Su cinque linee mai viste il risultato è migliore del transfer da solo. Due di queste linee sono state
lette solo alla fine, a regole già fissate.

## 6. Conseguenze

- Il candidato A/B/C del §13–§14 (t30: effetti t25 + w · R della rete del fold HepG2) è ammesso al grading dal §9. La
  sua previsione e la regola di lettura sono registrate in `reports/invii/prediction_t30_2026-10-04/prediction.json`
  prima della generazione.
- Per D/E/F: se il t30 conferma sul sito, il passo dopo è un refit su tutti i gruppi, che richiede una modifica del
  pre-passo, e il corpus completo D-053. In ogni caso le fonti del transfer vanno riconsiderate (S-010).
- STRADE: nuove voci S-009 (questo ibrido) e S-010 (fonti del transfer); S-006 cita l'esito del primo disegno che la
  riapriva.

## 7. Cosa corregge

Nessuna conclusione precedente è corretta. Il CP-0061 resta valido per il disegno v4. Questo checkpoint mostra che un
disegno diverso, con la parte comune esclusa e un peso fuori fold, supera il transfer sulle stesse tre linee e su due
nuove.

## 8. Domanda di comprensione

Perché il punteggio di banco del §9 di `ibrido_selettivo` (0,134) è molto più basso delle sue medie sulle linee di
sviluppo (0,23–0,28)? Risposta: la macro include K562, dove in scala locale tutti i bracci sono negativi per il
membro JAC.
