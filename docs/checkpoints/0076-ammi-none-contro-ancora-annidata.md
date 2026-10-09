# CP-0076 — AMMI none (seme 17): il ramo senza contesto non si distingue dalla propria ancora annidata su K562 e iPSC

- **Data:** 2026-10-09
- **Tipo:** esperimento
- **Redatto da:** Claude Code (sessione eace4d03, VALIDAZIONE)
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** S-016

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

I due fit AMMI `none` di MODELLI-ESTERNI (seme 17, due epoche) predicono l'ancora del transfer più un residuo
appreso dal solo bersaglio, senza contesto. Il residuo migliora, peggiora o lascia com'è la propria ancora sul
lignaggio escluso? E quanto costa l'ancora annidata rispetto al transfer del fold? Lettura nello spazio degli
effetti, prima dei fit `cells`.

## 2. Cosa è stato fatto

[Piano](../../reports/analisi/validazione_banco_eace4d03_2026-10-09/LETTURA_AMMI_NONE.md) committato alle 21:54
(`3f7e10fa`) prima di aprire un export. Con il consenso del proprietario delle 21:42
([autorizzazioni](../../reports/analisi/validazione_banco_eace4d03_2026-10-09/AUTORIZZAZIONI_r1.json)) i due
`query_000_native.npz` (36.281.758 byte) sono stati scaricati da `davidmaisterx`, verificati contro le ricevute del
produttore e caricati in un dataset privato di `davideferrante11`.
Lettore: `reports/analisi/validazione_banco_eace4d03_2026-10-09/ammi/lettura_esterni.py`, che chiama
`bench_core.measure` del banco congelato (verificato per sha256) e aggiunge copertura e vista del generatore;
quattro prove su fixture. Tre bracci per fold, tenuti distinti: `T0` (transfer del fold), `A0` (l'ancora annidata
del fit, senza K562, CD4T e HepG2 per C-K562 e senza iPSC, K562 e Jurkat per C-iPSC), `AN` (l'export `none`).
C-K562 letto sul portatile alle 22:04; i due fold nel kernel CPU privato
`davideferrante11/vcc-validazione-lettura-ammi-eace4d03-r2` (114 s); C-K562 coincide fra le due macchine a meno di
1e-16.

## 3. Cosa si è osservato

Misure nello spazio degli effetti su due lignaggi di sviluppo, un seme di training: non sono punteggi VCC.
[C-K562](../../reports/analisi/validazione_banco_eace4d03_2026-10-09/ammi/cloud_r2/completion/ammi_none_C-K562.json),
[C-iPSC](../../reports/analisi/validazione_banco_eace4d03_2026-10-09/ammi/cloud_r2/completion/ammi_none_C-iPSC.json).

**Controlli.** `disc95` di T0 uguale alla corsa di chiusura (differenza 0); `A0` e `AN` con gli sha256 delle
ricevute; `AN` e `A0` hanno la stessa maschera; `AN` si distingue dal proprio braccio a bersagli scambiati (`disc95`
+0,290 su C-K562, +0,069 su C-iPSC, risolti), come la sua ancora.

**`AN` − `A0`, il contributo del residuo** (3,8 e 3,7 milioni di coppie cambiate, a maschera identica; di quelle
che la verità può giudicare, il 99,6 % e il 95,4 % sta nel rango di `disc95`):

| Misura | C-K562 | C-iPSC |
|---|---|---|
| `disc95` | +0,0011 [−0,0015; +0,0038] | +0,0005 [−0,0012; +0,0023] |
| `r_spec` | −0,0001, non risolto | +0,0000, non risolto |
| `sign50` | +0,0015, non risolto | +0,0009, non risolto |
| `nmae_conf` (meno è meglio) | −0,0002, non risolto | **−0,0003** [−0,0004; −0,0001] |
| `mse_ratio` (meno è meglio) | **+0,0006** [+0,0002; +0,0010] | +0,0000, non risolto |

L'ampiezza della previsione non cambia (RMS 0,0795 e 0,1225 per entrambi i bracci).

**`A0` − `T0`, il costo dell'ancora annidata** (maschere diverse: 132.473 e 53.146 coppie previste solo da T0):
su C-K562 `disc95` −0,0016 [−0,019; +0,016], non risolto, con `r_spec` −0,003 e `mse_ratio` +0,06 risolti a
sfavore, e nella vista del generatore anche `sign50` −0,016; su C-iPSC `disc95` +0,004, non risolto, `reach`
+0,0007 risolto a favore e `mse_ratio` +0,006 a sfavore.

## 4. Interpretazione e incertezza

**Per le parole fissate prima:** su entrambi i fold il ramo senza contesto **non si distingue** dalla propria
ancora. Non la migliora e non la peggiora sulla misura primaria; le due differenze risolte sono dell'ordine di un
millesimo e di segno opposto fra i fold. Non si scrive che l'ancora annidata costa: `disc95` non è risolto.
**Interpretazione.** Era l'attesa dichiarata: dalle ricevute del produttore il residuo vale circa il 3 %
dell'ampiezza dell'ancora e la loss si muove dello 0,7 % in due epoche. Il sintomo di S-006 (una correzione che
peggiora la propria ancora) qui non c'è; non c'è nemmeno un beneficio.
**Che cosa non dice.** Nulla sui fit `cells`, che sono un altro braccio; nulla sui sei membri; nulla sulla
variabilità del training (un seme). Su C-K562 l'ancora annidata perde in misure secondarie rispetto a T0 perché le
manca CD4T fra le fonti: un confronto `cells` − `T0` porterebbe con sé quella differenza, quindi i contrasti da
leggere restano `cells` − `A0` e `cells` − `none`.

## 5. Spiegazione semplice

Il modello parte dalla risposta del transfer e prova a correggerla guardando solo quale gene è stato spento. La
correzione che ha imparato è così piccola che la previsione resta, in pratica, quella di partenza: né meglio né
peggio. Per sapere se guardare le cellule aiuta bisogna aspettare l'altro braccio.

## 6. Conseguenze

- Per i fit `cells`: stessi tre bracci più `none`, stessi contrasti, stesso lettore; l'ancora di confronto è `A0`.
  Guardie tecniche superate non sono beneficio, e una differenza a un seme resta un'osservazione.
- Nessuna decisione sulla consegna cambia. Nessun fit è stato fermato o chiesto.

## 7. Cosa corregge

Nessuna.

## 8. Domanda di comprensione

Perché confrontare l'export AMMI con T0, invece che con la sua ancora, darebbe la risposta a un'altra domanda?
