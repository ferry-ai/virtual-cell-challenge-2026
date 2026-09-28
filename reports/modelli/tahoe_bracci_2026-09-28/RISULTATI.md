# Bracci farmacologici di Tahoe: estrazione e prova T1 ridotta

28 settembre 2026, notte. Codice e disegno di codex ([DISEGNO.md](DISEGNO.md), esecuzione
`20260928-032819-v2-tahoe-arms`, rivisti e applicati dal lead). Qui scrive il lead (Claude, sessione del
proprietario); orari letti da `date`.

Etichette: **misurato**, **interpretazione**, **ipotesi**, **proposta**. Nessun numero qui è un punteggio VCC.

## Estrazione (misurato, in corso)

Kernel Kaggle privato su CPU `vcc-tahoe-arms-s5`, con internet, revisione del dataset
`2dc57900b7981cfcf5e211527169a0b006546a95`.
- **Farmaci:** i 73 di `selection/drugs.csv` più il DMSO.
- **Frammenti:** uno ogni cinque (678), gli stessi dell'estrazione dei soli DMSO.
- **Uscita:** somme per linea × piastra × farmaco × dose sull'asse ufficiale, più una colonna con il resto dei
  conteggi, in float32.

Cronologia:
- la versione 1 si è fermata dopo 22 s per un 503 del server;
- `extract_arms.py` ora ritenta gli errori transitori;
- la versione 2 alle 04:22 aveva letto 304 frammenti su 678, con 1.612.560 cellule selezionate.

## Prova T1 ridotta: fissata alle 04:23 del 28/09, prima di stimare qualunque effetto dei farmaci

**La domanda.** Lo stato basale di una linea (i suoi DMSO) predice come la sua risposta a un farmaco si discosta
dalla risposta media delle altre linee? È la domanda della rete (il contesto letto dai controlli), posta su circa
48 linee invece che su 4–7 contesti CRISPRi, con perturbazioni farmacologiche. È una versione ridotta e concreta
del T1 del disegno di codex, non il banco completo.

**Dati.**
- **Risposte:** gli effetti per (linea, farmaco, dose) di `arms_effects.py` (stimatore degli universi, DMSO della
  stessa piastra), valori ristretti, logaritmo naturale, asse ufficiale.
- **Stato basale:** per linea, la somma dei profili DMSO di tutte le piastre del corpus
  `processed/corpus_basale_2026-09-28/tahoe_s5u`.
- Entrano le linee presenti in entrambi.

**Disegno.** Una linea tenuta fuori alla volta (L). Per ogni farmaco e dose d misurati in L e in almeno 10 altre linee:
- **cieco:** la media, gene per gene, delle risposte a d delle altre linee;
- **vicini (k = 5):** la media delle risposte a d delle 5 linee di training più simili a L nello stato basale.
  Similarità = correlazione di Pearson dei log1p CPM standardizzati sui 2.000 geni più variabili fra le linee di
  training. La media per gene e la scelta dei geni si calcolano senza L;
- **scambio:** gli stessi vicini, ma scelti con lo stato basale di un'altra linea L′, estratta a caso con seme fisso
  (L′ ≠ L; i vicini escludono L).

Geni valutati: quelli finiti nella verità e in tutti e tre i bracci. Per coppia (L, d):
- MSE di ogni braccio;
- MSE del prevedere 0;
- skill = 1 − Σ MSE / Σ MSE₀ sulle coppie.

**Contrasti:** vicini − cieco e vicini − scambio, come differenza di skill. Intervallo al 95 % con bootstrap sulle
linee: si ricampionano le linee tenute fuori con tutti i loro farmaci, 2.000 volte, seme 0.

**Regola.** Passa se entrambe le condizioni valgono:
1. vicini − cieco ha l'intervallo sopra zero;
2. vicini − scambio ha l'intervallo sopra zero.

Lettura:
- **passa:** lo stato basale predice, nei farmaci e su molte linee, come una linea si discosta dalla risposta media.
  È un'indicazione che l'idea della rete può funzionare con abbastanza contesti; non dice nulla sul CRISPRi;
- **non passa la 1:** con questa lettura semplice dello stato basale, nemmeno 48 linee bastano a battere la
  risposta media;
- **passa la 1 ma non la 2:** conta la forma della media dei vicini, non lo stato giusto.

**Descrittivo, non decide:**
- k = 3 e k = 10;
- per dose;
- lo strato delle coppie (L, d) con la risposta media più forte (quartile alto della norma della risposta cieca).

**Limiti dichiarati prima:**
- un braccio sta di solito su una sola piastra, quindi l'effetto di piastra non si separa da quello della linea;
- le 48 linee sono tutte tumorali, di pochi tessuti;
- i farmaci non sono knockdown: un esito positivo qui non è un esito sul CRISPRi.

## Esito di T1 ridotto (misurato, Kaggle CPU, kernel `vcc-tahoe-t1`, 28/09 mattina)

Estrazione finita:
- 678 frammenti in 3.458 s;
- 13.508 gruppi linea × piastra × farmaco × dose;
- 10.325 bracci con effetti sull'asse ufficiale (18.150 geni).

T1 su 48 linee, 218 farmaci × dose, 10.312 coppie (linea, braccio). Numeri stampati dallo script a fine corsa, in
`t1_r1/summary_printed.json`:

| Braccio | Skill |
|---|---|
| cieco (media di tutte le altre linee) | **0,194** |
| vicini, k = 5 | 0,057 |
| scambio, k = 5 | −0,003 |
| vicini, k = 3 / scambio, k = 3 | −0,060 / −0,134 |
| vicini, k = 10 / scambio, k = 10 | 0,143 / 0,100 |

**Regola:** vicini − cieco −0,137 [−0,147; −0,128]; vicini − scambio +0,060 [+0,045; +0,075]. **Non passa**: fallisce
la condizione 1.

**Lettura (interpretazione).**
- Lo stato basale porta informazione sulla risposta: i vicini giusti battono quelli di un'altra linea a ogni k
  (+0,07 con k = 3, +0,06 con k = 5, +0,04 con k = 10).
- Mediare poche linee costa più di quanto quell'informazione rende: la risposta di una singola linea (una piastra) è
  rumorosa, e più linee si mediano meglio va (k = 3 < 5 < 10 < tutte).
- Copiare il comportamento delle linee simili, quindi, perde anche con 48 contesti. Un modello deve usare tutte le
  linee e imparare solo una correzione ristretta verso lo stato del contesto.
- I sei limiti dichiarati prima restano validi.
