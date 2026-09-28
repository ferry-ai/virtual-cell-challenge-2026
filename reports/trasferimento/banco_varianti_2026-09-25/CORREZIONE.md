# Correzione del banco del 25 settembre, dopo due revisioni indipendenti

25 settembre 2026, verso le 03:35 (ora italiana). [RISULTATI.md](RISULTATI.md), scritto alle
00:50 e committato in `2308ee7`, **non si riscrive**: questa pagina dice che cosa ne resta
valido, che cosa no, e che cosa misurano le esecuzioni corrette. Scheda R-017 nel registro;
esito in CP-0039.

## 1. Il difetto

Trovato da claude2 e, senza sapere dell'altro, da grok (rapporti in [revisioni/](revisioni/)).
`cd4_mix` salva l'errore standard tutto NaN: è la media delle tre condizioni CD4, e l'SE non
viene propagato (già notato in CP-0034). `shrink_sweep.table`, usata anche da `noise_sim.py`,
`controls.py` e `noise_sim2.py`, ricalcolava z²/(z² + k) con z = 0 dove l'SE non è finito: ogni
effetto CD4 diventava 0, e `mix` lo contava come un voto per zero a peso pieno. I bersagli
coperti solo da CD4 davano righe nulle ed erano scartati, per cui le varianti erano valutate su
insiemi di bersagli diversi. La prima versione dell'opzione `zshrink` dello stadio 100, nello
stesso commit, aveva lo stesso difetto; non è mai stata usata per generare.

**Verificato da Claude:** l'SE di `cd4_mix` è non finito sul 100% delle coppie misurate; le altre
sei sorgenti della cache r5 hanno SE finito e positivo ovunque. La ricostruzione di `cd4_mix` dalle
tre condizioni riproduce l'effetto grezzo della cache con differenza 0,0 e lo `shrunk` della cache
entro 2,4·10⁻⁷: lo `shrunk` della cache era già la restrizione corretta a k 4.

## 2. Che cosa resta valido e che cosa no

| Materiale | Stato |
|---|---|
| r1 (`analyze.py`): tutte le righe, compreso `shrunk_g1` | valido: usa lo `shrunk` della cache |
| r3 (`gating.py`): filtro dei bersagli difficili respinto | valido, per la stessa ragione |
| righe grezze di r2 e r4, calibrazione sul t11 → t15, previsione per il t16 | valide: non usano l'SE |
| righe ristrette di r2 (k 1–64 e media a varianza inversa), di r4 e di r5 | **non valide** |
| r6 (`noise_sim2.py`) | completata alle 01:05 nonostante la richiesta di arresto: righe ristrette **non valide** (stesso difetto), righe grezze valide |
| tabelle 2 e 4 di RISULTATI.md per le colonne ristrette, «+0,026 / +0,042 / +0,058 / +0,080», la proposta di k 64 con la regola del q99 | **non valide** |
| «Raddoppiare quel q99 non aggiunge nulla» | falsa già nei numeri difettosi per K562 (grok) |
| Spearman 0,46–0,70 fra sorgenti | ora in un output: `r9/` dà 0,456–0,695 |

## 3. Le esecuzioni corrette

**r7 (`sweep_v2.py`).** Carica le sorgenti con il `load_table` dello stadio 100, che ricostruisce
`cd4_mix` dalle condizioni ristrette e rifiuta ogni altra sorgente senza SE
(`multisource.zshrink_table`, `zshrink_mixture`, test in `tests/test_multisource.py`); un solo
insieme di bersagli per sorgente esclusa; differenze appaiate con IC95 bootstrap sui bersagli.
PDS proxy senza rumore, restrizione meno grezzi: k 4 da +0,011 a +0,022, k 16 da +0,017 a
+0,033, k 64 da +0,017 a +0,036; intervalli sopra zero salvo HCT116 a k 16 e k 64. Qui CD4
entra con le sue condizioni ristrette, quindi il guadagno non viene dal toglierlo. Il braccio
"grezzi senza CD4" è una domanda diversa, con esiti di segno opposto: K562 −0,031, HCT116
+0,002, HEK293T +0,052 (per HEK293T togliere CD4 aiuta più della restrizione).

Con il modello del generatore (taglio a 6 log2, spostamento compositivo, Poisson di 400
cellule): gli effetti ristretti all'ampiezza 0,394 perdono (−0,03…−0,13); riscalati al q99 del
t15 con tetto |ln fc| 2 battono i grezzi a 0,394 (+0,014…+0,036) e a 0,788 (+0,003…+0,013),
ma muovono circa 600 geni invece dei circa 2.600 dei grezzi a 0,788.

**r8 (`sweep_v3.py`), dopo il punteggio del t16.** Stesso impianto, più un conteggio dei geni
"rilevabili" (|ln fc| realizzato oltre 4/√(400 μ), ≥ 5 CPM) e la precisione dei loro segni
contro la sorgente esclusa. Rispetto ai grezzi a 0,788 (il t16):

| Sorgente esclusa | t16: rilevabili, PDS | grezzi 1,576 (t18): rilevabili, ΔPDS | k 4 a 1,576: rilevabili, ΔPDS, Δprecisione | k 16 a 3,152: rilevabili, ΔPDS |
|---|---|---|---|---|
| CD4 | 461, 0,663 | 1.797, −0,001 | 351, +0,009, +0,008 | 271, +0,015 |
| K562 | 335, 0,735 | 1.246, +0,002 | 321, +0,019, +0,006 | 319, +0,025 |
| HCT116 | 522, 0,673 | 1.692, −0,005 | 492, +0,004, +0,004 | 473, +0,003 |
| HEK293T | 525, 0,651 | 1.701, +0,002 | 495, +0,014, +0,003 | 478, +0,016 |

Il modello non simula le chiamate spurie del generatore né il Wilcoxon, e ha sovrastimato il
guadagno di PDS del t16 (CP-0037): i numeri indicano una direzione, non un'entità.

## 4. Che cosa se ne ricava

- **Proposta, al posto di quella di RISULTATI.md:** il secondo candidato è il t16 con lo
  `shrunk` della cache (k 4) all'ampiezza 1,576, che nel modello muove circa quanti geni il
  t16. Stessa ampiezza del t18: t19 − t18 isola la forma degli effetti, t19 − t16 la confronta
  a rilevabilità simile. Usa un'opzione dello stadio 100 già in uso, non `zshrink`.
- k 16 a 3,152 fa appena meglio nel modello, ma con ampiezze più estreme; resta un passo
  successivo, se k 4 regge sul punteggio ufficiale.
