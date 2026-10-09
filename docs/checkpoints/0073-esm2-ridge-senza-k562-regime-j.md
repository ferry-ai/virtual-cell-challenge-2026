# CP-0073 — ESM2 + ridge senza K562: nel regime J nessun segnale specifico, e togliere K562 non cambia le previsioni

- **Data:** 2026-10-09
- **Tipo:** esperimento
- **Redatto da:** Claude Code (Opus 5.5), sessione 8a8ca58a
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** S-013

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Lo stesso ridge ESM2 senza contesto, addestrato senza il lignaggio K562 e senza i bersagli nascosti, riconosce i
bersagli nascosti in K562 (regime J)? E togliere K562 dal training cambia le sue previsioni?

## 2. Cosa è stato fatto

In [validazione_indipendente_8a8ca58a_2026-10-08](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/README.md); orari da `date`, commit e `launch.json`.

1. File nativo del fit `davideferrante11/esm2-j-k562-01a11c35-r1` di MODELLI-ESTERNI letto senza modifiche: sha256
   `cedca755…405a`, uguale alla ricevuta; esame tecnico superato ([esame](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/esm2_jk562_r1/esame.json)).
2. Confronto con il fit T senza leggere verità ([confronto](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/esm2_jk562_r1/confronto_con_T.json)).
3. Aggiunta al [piano](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/LETTURA_ESM2_T.md) con l'attesa scritta prima, commit `f8990eeb` delle 02:39:20.
4. Corsa r7 del livello A (02:43–02:54): i 66 bersagli nascosti contro sei verità; solo quella di K562 è regime J.

## 3. Cosa si è osservato

- **Senza verità:** le previsioni di questo fit e del fit T hanno correlazione per bersaglio mediana 0,996 e minima
  0,990.
- **Regime J su K562** ([tabelle](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/TABELLE_ESM2_JK562_contrasti_r7.md)): `disc95` 0,516 contro 0,500 della
  parte generica, 0,531 dello stesso ridge a previsioni scambiate e 0,543 della testa cis. `E2jk − E2jkg` +0,016
  [−0,046; +0,080]; controllo a previsioni scambiate −0,015 [−0,087; +0,062]. Nessun contrasto risolto.
- **Togliere K562:** `E2jk − E2` −0,005 [−0,029; +0,020] su K562 e non risolto in nessun lignaggio; contro la
  verità iPSC il ridge resta a 0,628.
- **Esito della regola:** nessun segnale specifico del bersaglio nel regime J su K562. Era l'attesa registrata.

## 4. Interpretazione e incertezza

- **Misura:** il lignaggio tenuto fuori non è previsto meglio del caso, e la sua assenza dal training non sposta
  le previsioni. **Interpretazione:** K562 pesa poco in un modello dominato da altri lignaggi; questo non è una
  prova di generalizzazione.
- **Che cosa manca:** il test simmetrico, il fit senza iPSC letto contro la verità iPSC, che direbbe se lo 0,63
  del regime T è memoria del lignaggio. Sessantadue bersagli, un lignaggio, un proxy.

## 5. Spiegazione semplice

Si è tolta dal materiale di studio una delle cellule e si è chiesto al modello di indovinare, proprio in quella,
l'effetto di geni mai visti. Non ci riesce. Ma non ci riusciva nemmeno quando quella cellula era nel materiale:
toglierla non ha cambiato le sue risposte. Vuol dire che quella cellula contava poco per lui fin dall'inizio.

## 6. Conseguenze

- Per i contesti non staminali questo ridge non porta, finora, un segnale sui bersagli nuovi, né in T né in J.
- La lettura che decide resta quella dei fit C (bersagli visti altrove, contesto nuovo), in corsa.
- Per chi possiede il modello: il fit senza iPSC è il prossimo test informativo, più di altri fit senza un
  lignaggio poco rappresentato.

## 7. Cosa corregge

Nessun checkpoint. Completa [CP-0072](0072-esm2-ridge-regime-t.md).

## 8. Domanda di comprensione

Perché un modello le cui previsioni non cambiano togliendo un lignaggio dal training non ha per questo dimostrato
di generalizzare a quel lignaggio?
