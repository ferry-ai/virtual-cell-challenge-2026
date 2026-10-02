# Strada C: preparare le fonti dello stesso tipo cellulare per D, E, F

3 ottobre 2026, notte, stessa sessione. Alfredo chiede se esiste un'altra strada oltre ad A (caduta, vedi la
[correzione](CORREZIONE_STRADA_A.md)) e B ([protocollo](../../trasferimento/strada_b_2026-10-02/PROTOCOLLO.md)).
**Proposta, nessuna misura nuova.**

## Due fatti delle regole che cambiano il gioco (letti dalla pagina ufficiale)

Fonte: [le regole](https://virtualcellchallenge.org/rules), versione rivista il 16 settembre 2026, lette alle 00:10 CEST
del 3/10 nel browser.

1. **La fase finale è cieca.** Le regole dicono:
   - «There will be no leaderboard displayed for final entries from October 22, 2026 to November 5, 2026»;
   - «Only the last final entry you make will be considered».

   Nessuna taratura su D/E/F è possibile: ciò che si sceglie prima del 22 ottobre, e la regola per scegliere, decide.
2. **«Machine Learning Predictions Only», versione del 16/09.** Non si possono inserire nella previsione risultati
   sperimentali o pubblicati, né usarli per correggere le previsioni del modello. Si possono usare per addestrarlo.
   - **Ai vincitori** si chiede di descrivere anche le componenti «non apprese» mescolate al modello: il trasferimento
     da altre linee sembra ammesso come componente dichiarata.
   - **Copiare gli effetti pubblicati della stessa linea** per gli stessi bersagli sarebbe invece molto vicino al caso
     vietato.
   - **Da chiarire con gli organizzatori prima di dipenderne** (help@virtualcellchallenge.org). È coerente con la
     cautela già scritta in PROGETTO §0 («stessa linea» solo come esperimento dichiarato).

## L'idea

- **Il trasferimento fra linee di tipo diverso porta poca direzione.**
  - Fra linee e laboratori diversi il coseno mediano vale 0,02–0,03.
  - Vale 0,07 fra linee dello stesso laboratorio, 0,16 fra due esperimenti della stessa linea, 0,20–0,25 fra stati
    delle stesse cellule CD4.
  - Fonte: [atlante](../../trasferimento/atlante_2026-09-26/RISULTATI.md); misure su proxy.
- **Pesare le fonti per somiglianza basale** fra linee diverse non ha battuto i pesi uguali, né da noi né
  nell'entrata pubblica che l'ha provato. Il guadagno atteso sta solo dove esiste una fonte **dello stesso tipo
  cellulare**, non semplicemente «più simile».
- **D/E/F probabilmente comprendono un tipo staminale** (ipotesi):
  - Arc dice che le sei linee comprendono cellule staminali, linee immortalizzate e tumorali;
  - i marcatori di A/B/C non mostrano pluripotenza ([contesti](../../gara/contexts_2026-09-17/));
  - Arc ha condotto la gara 2025 su H1 in CRISPRi.
- **Per un contesto pluripotente** abbiamo già tre fonti dello stesso tipo:
  - KOLF2.1J genome-scale (10.985 bersagli);
  - HipSci (444 bersagli in 19 linee);
  - l'H1 della gara 2025, stesso laboratorio di Arc, il cui download aspetta il proprietario.
- **La ricetta di oggi le ignora:** usa K562, CD4, HCT116 e HEK293T per ogni contesto.

## Che cosa va misurato prima del 22 ottobre (proposta, da registrare)

1. **Trasferimento dentro il tipo pluripotente,** lasciando fuori una linea alla volta:
   - KOLF2.1J predetto da HipSci (e da H1, se autorizzato), contro la ricetta t22 sugli stessi bersagli;
   - una linea HipSci predetta dalle altre 18 più KOLF.

   Misure: coseno con la verità e, dove le cellule ci sono, il banco con lo scorer vero.
2. **Lo stesso per il tipo linfoide T,** dove A dà già un indizio: Jurkat (Nadig) predetto da CD4 contro le altre
   fonti. È il controllo che la regola regge oltre le staminali.
3. **Una regola di scelta registrata prima del 22:**
   - le impronte degli stadi 85 e 99 assegnano a ogni contesto nuovo un tipo (pluripotente, linfoide, mieloide,
     epiteliale, epatico, …);
   - se le misure 1–2 mostrano un guadagno, quel contesto usa le fonti del suo tipo, a peso fissato prima;
   - altrimenti si usa la ricetta generale.

   Nessuna fonte della **stessa linea** entra senza un chiarimento scritto degli organizzatori (punto 2 sopra).

## Perché vale la pena

Se il trasferimento dentro il tipo dà un coseno vicino a quello «stesse cellule, stati diversi» (0,20–0,25, contro lo
0,02–0,07 di oggi), su quel contesto si supera la soglia di direzione che serve alla MSE (circa 0,12, vedi la
correzione). PDS e membri DE salgono con la direzione. È un guadagno su un contesto su tre, ma potenzialmente più
grande di tutte le varianti A e B messe insieme. **È un'ipotesi:** la misura 1 la conferma o la chiude.

## Che cosa serve

- Gli universi KOLF2.1J e HipSci (stadio 98/106), sul PC di Davide.
- La decisione del proprietario sull'H1 della gara 2025: è fra i download aspettati in PROGETTO §0.
- Il file Jurkat di Nadig, se c'è, sul disco D:.
- Una mail agli organizzatori sul punto 2, da mandare solo con l'ok di Alfredo.
