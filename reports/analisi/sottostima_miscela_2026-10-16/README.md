# Perché il banco sui fold ha sottostimato il guadagno di `ta 42` sul sito

16 ottobre 2026. Claude Code per Alfredo, che ha chiesto in chat di capire perché abbiamo sottostimato e che cosa ha
funzionato.

## Il fatto da spiegare (misurato)

**Le unità del banco e del sito sono diverse:**
- l'indice PDS del banco (`guadagno.measures`) vale 1 − 2 × (quota di altri bersagli più vicini): caso = 0;
- il PDS grezzo del sito è la quota degli altri più lontani: caso = 0,5;
- quindi un guadagno di indice sul banco corrisponde a **metà** guadagno grezzo sul sito, e il PDS scalato del sito
  è il grezzo diviso 0,447.

**Il confronto, in queste unità:**
- il banco prevedeva per `ens_0.7` − `t3` +0,012 di indice, cioè circa +0,006 di grezzo e **+0,013 scalato**;
- il sito ha dato `ta 42` − `td 38` = +0,0105 sulla media, cioè circa **+0,06 di PDS scalato** se il guadagno è tutto
  PDS (i membri di `td 38` non sono su GitHub);
- **la sottostima è di circa 5 volte.**

**I fold sono anche un regime più difficile:**
- l'indice medio di T3 sui fold è 0,355, cioè un grezzo di circa 0,68;
- sul sito i grezzi sono 0,77–0,80.

## Ipotesi (scritta prima dei numeri)

Il guadagno della miscela cresce con la forza della risposta vera:
- dove la verità è debole, nessun predittore discrimina e la media non può aiutare;
- i bersagli di A/B/C hanno risposte più forti, perché il PDS del sito è più alto;
- il banco, mediando molti bersagli deboli, comprime il guadagno.

**Che cosa si legge** con [sottostima.py](sottostima.py), sugli stessi fold, bersagli e semi del banco del 15/10:
- l'indice PDS e il coseno di `t3`, `rete_c`, `ens_0.5` ed `ens_0.7` per terzile di forza della verità;
- la forza è il rapporto segnale/rumore medio sui geni valutati.

**Regola di lettura:** l'ipotesi regge se il guadagno di `ens_0.7` su `t3` cresce dal terzile debole a quello forte, e
nel terzile forte è almeno il doppio della media. Non sposta nessuna decisione già presa.

## Esito (misurato, letto dopo il commit `5be1933`)

Valori in [result.json](result.json), log in [run.log](run.log). Terzili di forza della verità entro ciascun fold,
riuniti sui 4 fold (circa 355 bersagli per terzile). Indice PDS del banco:

| Terzile | `t3` | `rete_c` | `ens_0.7` − `t3` | `ens_0.5` − `t3` | coseno `ens_0.7` − `t3` |
|---|---|---|---|---|---|
| debole | 0,225 | 0,206 | +0,009 | +0,006 | +0,016 |
| medio | 0,404 | 0,361 | +0,014 | −0,005 | +0,009 |
| **forte** | 0,427 | **0,435** | +0,014 | **+0,017** | +0,015 |

**Regola di lettura: l'ipotesi regge solo in parte.** Il guadagno di `ens_0.7` cresce dal terzile debole a quello
forte, ma non arriva al doppio della media. La forza della verità da sola non spiega la sottostima di circa 5 volte.

## Che cosa si capisce (interpretazione)

1. **Una parte della sottostima è nelle unità:** il banco riporta un indice che vale il doppio del PDS grezzo, e il
   punteggio scala il grezzo di 1/0,447. Va sempre convertito prima di confrontare.
2. **Sui bersagli a risposta forte la rete da sola batte T3** (0,435 contro 0,427), e lì la miscela migliore è al 50%
   (+0,017), non al 70% (+0,014). Il sito ha PDS alti, cioè risposte forti.
3. **Tre indizi indipendenti vanno nella stessa direzione:**
   - questo terzile forte;
   - la parabola per i tre punti del sito (massimo a peso 0,52);
   - il banco che ha sottostimato la miscela.

   Insieme dicono che **sul sito la nostra rete vale più di quanto dica il banco**. È l'ipotesi che `ta 43` mette alla
   prova.
4. **Resta da spiegare** il grosso del fattore 5. Due candidati (**ipotesi**, non misurate):
   - in produzione la rete si condiziona sul basale dei controlli veri di A/B/C, mentre sui fold usa il basale del
     cubo;
   - i contesti A/B/C potrebbero essere più lontani dalle linee sorgente dei fold del cubo, e lì un modello appreso
     guadagna di più su un transfer.
