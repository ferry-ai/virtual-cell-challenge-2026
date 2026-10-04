# CP-0064 — t30: l'ibrido selettivo sul sito, −0,005 contro il t25; che cosa del banco non si è trasferito

- **Data:** 2026-10-04
- **Tipo:** esperimento
- **Redatto da:** Claude Code (Opus 5.5), sessione ba9b8bcb, su R-LEAD
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** S-009, S-006

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

L'ibrido selettivo D-056 v1, che sul banco locale batteva il transfer su cinque linee escluse
([CP-0062](0062-d056-ibrido-selettivo-esito-banco.md)), migliora il t25 sui contesti ufficiali A, B, C? E, letto il
numero, che cosa aveva provato davvero il banco rispetto a ciò che è stato inviato?

## 2. Cosa è stato fatto

- **Invio (sessione `2b35612c`):** t30 = effetti t25 + w · R, con R la correzione della rete del fold HepG2 e w il
  selettore congelato; generazione e pacchetto con gli argomenti del t25. Previsione e regola registrate prima della
  generazione: `reports/invii/prediction_t30_2026-10-04/prediction.json` (banda 0,125–0,160; regola a ±0,005 contro il
  t25). Entry `lDMSYUZU5cFYHcRqI0lq`, upload 09:13–09:30 UTC, registro in `reports/invii/trial_2026-10-04/INVIO_T30.md`.
- **Lettura:** `read_t30_score.py`, scritto prima dell'upload, ha prodotto
  `reports/invii/prediction_t30_2026-10-04/comparison.json` dallo status pubblicato
  `reports/invii/trial_2026-10-04/status_lDMSYUZU5cFYHcRqI0lq.json`. Nessuno score è stato richiesto di nuovo.
- **Chiusura e diagnosi (questa sessione, `ba9b8bcb`):** quattro riletture locali su file esistenti, in
  `reports/modelli/diagnosi_t30_2026-10-04/`: catena dell'invio (`chain_t30.py`), membri del banco
  (`bench_members.py`), correzione esportata contro righe del banco (`export_vs_rows.py`), procedura di esportazione
  sui controlli di tre linee del banco (`export_on_line_controls.py`, lettura scritta prima dell'esecuzione nel §7 di
  `PROTOCOLLO_CONFRONTI.md`). Nessun job cloud, download, invio o push.

## 3. Cosa si è osservato

**Punteggio ufficiale** (status e `comparison.json`; rilettura in
`reports/modelli/diagnosi_t30_2026-10-04/esito/chain_t30_r2.json`):

- t30 = **0,135248601985599**, rango 460; la media dei sei scalati coincide con `score_avg`; stesso pannello e stessa
  versione delle ancore di t25 e t28.
- t30 − t25 = **−0,004989458929**; soglia inferiore 0,135238060915; il t30 la supera di 0,0000105: **ramo b**, non
  conclusivo. t30 − t28 = −0,009596603.

| Membro | t30 scalato | t25 scalato | t30 − t25 | t30 grezzo | t25 grezzo |
|---|---|---|---|---|---|
| PDS | 0,581325 | 0,623562 | −0,042237 | 0,763058 | 0,782092 |
| MSE | 0 | 0 | 0 | 3,168231 | 3,017171 |
| NMAE | 0,116091 | 0,117985 | −0,001894 | 0,929128 | 0,928019 |
| Fedeltà | −0,044402 | −0,058129 | +0,013726 | 0,499278 | 0,495220 |
| Reach | 0,142214 | 0,144052 | −0,001838 | 0,204634 | 0,206572 |
| Jaccard | 0,016264 | 0,013958 | +0,002306 | 0,036404 | 0,035571 |

**Catena dell'invio** (`esito/chain_t30_r2.json`): ricevuta, modello, selettore, effetti, argomenti dello stadio 45 e
pacchetto coincidono con quanto registrato. Il profilo previsto dei 70 bersagli non corretti è identico al t25 in 210
blocchi su 210; le loro cellule lo sono in 1 blocco su 210, perché lo stadio 45 usa un solo flusso casuale.

**Banco contro invio** (`esito/bench_members_r1.json`, `esito/export_vs_rows_r1.json`):

- Sul fold esportato (HepG2) la corsia B perdeva PDS, −0,093, e la corsia A −0,039; la media saliva di +0,063 per
  NMAE, fedeltà, reach e Jaccard. È l'unica linea su cinque in cui il segno del PDS coincide con quello ufficiale.
- Quota comune di R: 0,62 (A), 0,69 (B), 0,66 (C) contro 0,07–0,24 sulle righe delle cinque linee e 0,17 nelle
  guardie interne del training; la guardia del trainer ferma oltre 0,5.
- RMS(R)/RMS(T) mediano 0,71 (A), 0,96 (B), 0,96 (C) contro 0,24–0,42; il 45 % dei bersagli di B e il 44 % di C ha
  l'ingresso di ampiezza del selettore fuori dalla fascia 1–99 % delle righe di stima; w resta fra 0,09 e 0,49.
- La baseline dell'invio (t25) e l'ancora rispetto a cui R è definita hanno coseno mediano 0,71; il banco non ha mai
  valutato `T_prod + w · R`.
- Il +0,074 di K562 viene per il 77 % dal JAC locale, il cui denominatore vale 0,047; senza JAC è +0,020. La MSE
  scalata vale 0 per ogni braccio su ogni linea. Il banco usa 32 cellule per bersaglio e 7.679–9.023 geni su quattro
  linee su cinque, contro 400 e 18.533.

**Controllo locale sui controlli delle linee** (`esito/export_on_line_controls_r2.json`):

- Controllo positivo passato: la R di A si riproduce identica. Lettura registrata nel §7 del protocollo prima
  dell'esecuzione: quota comune **non distinto**; ampiezza **segue la procedura o i bersagli del pannello**.
- Con la procedura di esportazione e i bersagli del pannello, sui controlli di HepG2 (linea non di gara, esclusa dal
  training di questa rete) la quota comune di R è 0,61 e RMS(R)/RMS(s(A)) 0,88; su A/B/C, sugli stessi geni, 0,65–0,72 e
  0,95–1,28. Sulle due linee di training: H1 0,30 e 0,39, RPE1 0,32 e 0,74. Sul banco, stessa rete e stessa linea
  HepG2: 0,23 e 0,42.
- I bersagli del pannello non sono fra quelli del banco: 0 su 300 nelle righe e nelle corsie di HepG2, RPE1 e Jurkat,
  15 su H1, 72 nelle righe e 6 nella corsia di K562; 15 righe su 3.604 nella stima del selettore
  (`esito/panel_vs_rows_targets_r1.json`, esplorativo).

## 4. Interpretazione e incertezza

- **Misura:** il guadagno del banco non è comparso sul sito; la perdita è nel PDS. La correzione esportata è per due
  terzi comune ai bersagli e più ampia di quella valutata; l'invio differiva dal braccio del banco per baseline,
  stimatore di R e regime degli ingressi.
- **Interpretazione:** il banco ha promosso un candidato che non aveva valutato. Sul fold esportato la perdita di
  discriminazione era già visibile e la regola sulla media la compensava con membri DE che, a 32 cellule per bersaglio
  e con ancore locali instabili, sul sito non si sono mossi.
- **Interpretazione del controllo sui controlli delle linee:** la quota comune alta non richiede i controlli di gara;
  compare su una linea nuova quando R si calcola come nell'invio e sui bersagli del pannello, che il banco non
  conteneva. Procedura e bersagli cambiano insieme e la linea esclusa è una sola: non sono separati.
- **Ipotesi, non isolate:** quale differenza abbia prodotto la perdita (baseline, parte comune, procedura e bersagli
  dell'invio, selettore fuori intervallo) e quanta parte del −0,005 sia realizzazione del rumore. I confronti che le separano sul
  banco sono scritti e congelati (`PROTOCOLLO_CONFRONTI.md`), non eseguiti.
- **Incertezza:** un invio, una rete, un seme. La soglia ±0,005 è operativa, non un intervallo statistico; il t30 sta
  a un centomillesimo dal ramo c. Il banco non contiene un contesto del dominio di gara.

## 5. Spiegazione semplice

Avevamo un correttore che, provato su cinque linee, migliorava le previsioni. Ma lo avevamo provato montato su un
motore, e lo abbiamo inviato montato su un altro. In più, sulle cellule della gara il correttore ha fatto quasi la
stessa mossa per tutti i bersagli corretti: una mossa uguale per tutti non aiuta a dire quale gene è stato spento, che
è ciò che la gara premia di più. E sulla linea da cui veniva proprio quel correttore, la prova locale mostrava già che
distingueva peggio: lo copriva una media.

## 6. Conseguenze

- **Regola registrata, ramo b:** non conclusivo; t25/t28 restano i riferimenti, il t28 il massimo osservato. Nessuna
  promozione. PROGETTO §0 cambia nello stato, non nel massimo né nel riferimento.
- **D-056 resta la direzione**, ma il suo v1 non è un candidato per D/E/F. Il prossimo ibrido richiede: un solo
  contratto di baseline fra fit, banco ed esportazione; le guardie del trainer applicate all'esportazione; una guardia
  per membro su ogni linea; flusso casuale per blocco e più semi. Elenco completo e misure in
  `reports/modelli/diagnosi_t30_2026-10-04/README.md` §3 e §5, coordinato con il piano di Codex in
  `reports/analisi/prossimo_ibrido_2026-10-04/PIANO_TRAINING.md`.
- **Le cinque linee sono sviluppo:** Jurkat e K562 non sono più una conferma intatta.
- **Prossimo passo:** i confronti del protocollo su Kaggle CPU, con il via del proprietario.

## 7. Cosa corregge

Delimita [CP-0062](0062-d056-ibrido-selettivo-esito-banco.md), senza cambiarne le misure locali:
- il punteggio di banco 0,134 contro 0,090 non si è trasferito al sito, e la soglia 0,100 non era una previsione;
- «batte il transfer su cinque linee» vale per la media dei sei membri: sul fold esportato il PDS scendeva;
- il guadagno di K562 dipende per tre quarti dall'amplificazione del JAC locale;
- il candidato inviato non era un braccio del banco, e i bersagli del pannello non erano fra quelli valutati.

Corregge anche la diagnostica di `reports/invii/trial_2026-10-04/INVIO_T30.md`, che riportava l'ampiezza relativa di R
per la sola A (0,70): su B e C vale 0,96.

## 8. Domanda di comprensione

Perché una correzione che aggiunge lo stesso spostamento a tutti i bersagli può alzare la fedeltà della direzione e
abbassare il punteggio di discriminazione?
