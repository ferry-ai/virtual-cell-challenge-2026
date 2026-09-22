# Regola della ricetta t08, scritta prima dei risultati — 22 settembre 2026

Scritta alle 22:55 locali del 22 settembre, **prima** che lo stadio 98 abbia prodotto un
qualunque numero su CD4. L'estrazione di stadio 97 era ancora in corso. Autore: agente
(Claude), su mandato del proprietario ("inizia ad implementare"). Revisione umana: no.

## Che cosa cambia rispetto a trial-01, e che cosa no

Il t08 cambia **un solo fattore** rispetto a trial-01 (+0,0459, il migliore finora): gli
effetti. Il generatore resta quello di trial-01, senza modifiche (stadio 45, trial
`trial-ext-profile`): profilo basale del contesto, spostamento compositivo sui geni
supportati, conteggi di Poisson a librerie ricampionate dai controlli, seme 20260912.

In trial-01 gli effetti venivano da K562 genome-wide da solo, α = 0,197. Nel t08 vengono
dalla media pesata delle sorgenti che hanno perturbato lo **stesso** bersaglio: K562
genome-wide e CD4 (le tre condizioni di coltura mediate, `cd4_mix`).

## Regola

1. **Sorgenti:** `k562` e `cd4_mix` (stadio 98). Nessun'altra.
2. **γ** (quota della risposta media di ogni sorgente che si toglie): fra {0; 0,5; 1} si
   sceglie quello con la `pds_proxy_mean` più alta. La media è su due direzioni: K562 → ognuna
   delle tre condizioni CD4 (mediate) e `cd4_mix` → K562. A parità entro 0,005 vince il γ
   più alto.
3. **Pesi:** gli stessi per A, B e C. Sono i pesi ottimi per un contesto "equidistante"
   secondo `shared_signal(k562, cd4_mix)` al γ scelto. Il vantaggio di lignaggio di CD4 per A
   non entra nel t08: è un fattore da provare da solo, dopo.
4. **Ampiezza:** l'`amplitude` di `shared_signal` al γ scelto, uguale per i tre contesti.
5. **Affidabilità:** n/(n+100) sulle cellule della sorgente per quel bersaglio.
6. Un bersaglio che nessuna sorgente copre riceve effetto nullo, con la maschera registrata
   (D-009). CD4 copre 297 bersagli su 300 in libreria; i mancanti si leggono dallo stadio 97.

Se lo stadio 98 mostra che K562 e CD4 **non** condividono segnale (`corr` di `shared_signal`
≤ 0,02 a ogni γ), il t08 non si costruisce: si scrive perché e ci si ferma.

## Che cosa mi aspetto (previsione, non misura)

- PDS più alta di trial-01 (0,687 grezzo), se il segnale condiviso con CD4 esiste.
  Due sorgenti mediate hanno meno rumore specifico di una sola.
- MSE ancora tosata a 0: il generatore di trial-01 porta da solo circa 1,15 di MSE a effetto
  nullo (CP-0013). Il t08 non lo corregge di proposito.
- Fedeltà e reach vicine a trial-01, perché il generatore e il regime di chiamate sono gli
  stessi, a meno che l'ampiezza scelta non sia molto diversa da 0,197.
- Punteggio complessivo: fra +0,03 e +0,10. È una banda larga, e lo dico: lo stadio 84 non
  vale per una famiglia nuova (CP-0027), quindi non lo uso.

## Che cosa si impara in ogni caso

Il confronto con trial-01 isola l'effetto delle sorgenti a generatore fisso:
- se il t08 migliora, CD4 serve e si procede con i pesi di lignaggio e con altre sorgenti;
- se peggiora, la miscela o l'ampiezza sono sbagliate, e il generatore non c'entra.
