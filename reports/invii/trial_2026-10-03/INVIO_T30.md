# t30: decisione del proprietario e catena di invio

## Decisione (3/10, circa 16:20 ora italiana)

Alfredo ha scritto in chat: «escludi i passi di grading tuoi e appena possibile che hai qualcosa in mano passa al
grading». Cioè:
- **si invia il t30 appena esiste una rete addestrata,** senza aspettare il voto con lo scorer vero;
- **cadono tre condizioni** che la previsione elencava prima della generazione (`conditions_before_generation` in
  [prediction.json](../prediction_t30_2026-10-03/prediction.json)): il cancello tecnico, la lettura del voto e un ok
  separato al download. Le sostituisce questa decisione;
- **resta l'accordo sulla quota con il lato Davide:** prima dell'upload si controlla che la squadra non abbia un invio
  in volo.

**Che cosa non cambia:** la banda, la regola e i testi registrati alle 13:55 UTC restano come scritti. Il voto e la
strada C r2 continuano nel kernel `rete-sorgenti-r1`. Arriveranno dopo l'invio e lo valutano a posteriori, senza
spostare la regola.

## Come si ottiene la rete prima

`rete-sorgenti-r1` consegna i file solo a fine corsa, stimata verso le 22:30. Per questo un secondo kernel,
`alfredo2003bit/rete-sorgenti-r1-train`, rifà soltanto i passi 1–2:
- stesso dataset del codice (commit 23d6475), stesso seme, stessa divisione e stessa configurazione;
- scrive `consegna/` con le chiavi di addestramento, i file della corsa e un `manifest.json` con gli sha256.

Lo sha256 di `ckpt_best.pt` si confronta poi con quello del kernel completo. Se coincidono, il voto vale per la rete
inviata. Se no, lo si scrive qui come differenza.

## Catena locale, dopo il kernel

1. Scaricare solo `consegna/`, i log e `kernel_done.json`, e verificare gli sha256 contro `consegna/manifest.json`.
2. `esporta_abc.py`, che scrive gli effetti in `<data root>/processed/effects_t30_2026-10-03`.
3. Stadio 45: `--run-id t30gen --trial trial-ext-profile`, con le impostazioni del t22.
4. Stadio 48: `--run-id t30pack`.
5. Copiare manifest e diagnostiche qui, con i nomi di `reports/CLAUDE.md`.
6. Upload come processo Windows separato, con il PC tenuto sveglio. Lo lancia Alfredo, perché il classificatore dei
   permessi blocca gli invii dell'agente.

## Quota (3/10, scritto alle 16:45 ora italiana)

Alfredo ha scritto in chat: «ho l'ok per poi partire con il grading appena il corto finisce». L'accordo sulla quota
con il lato Davide è quindi preso, ed è riportato qui come lo ha scritto Alfredo, non verificato con Davide. Prima
dell'upload si controlla comunque con `vcc` che nessun invio della squadra sia in volo.

## Upload autorizzato all'agente (3/10, scritto alle 18:05 ora italiana)

Alfredo ha scritto in chat: «appena finisce manda da solo il grading che mi sto allontanando hai il mio si». L'agente
può quindi lanciare da solo la catena locale e l'upload del t30, appena finisce il kernel corto. Prima dell'upload
controlla con `vcc` che nessun invio della squadra sia in volo.

## Misurato dopo la registrazione e prima della generazione (3/10, scritto alle 18:08)

Kernel corto COMPLETE alle 16:05 UTC: 32 file, 510 MB, sha256 tutti uguali a `consegna/manifest.json`.
- **Addestramento:** 3.000 passi, nessun arresto anticipato, 25 chiavi di addestramento. Sulla validazione la rete
  batte la media a pesi uguali, `delta_loss` −0,018 al passo 3.000. Ma il coseno di validazione è basso per tutte e
  due: 0,056 contro 0,055.
- **Il fattore d'ampiezza appreso riduce gli effetti.** `ckpt_best.pt` (sha256 `76095f07…`) esporta per A/B/C
  ampiezze 0,13, 0,19 e 0,16, contro il norm-match di 1,14. Interpretazione: con un coseno così basso, la parte MSE
  della perdita premia effetti piccoli.
- **|lfc| medio sui geni osservati:** 0,0052, 0,0075 e 0,0064. È circa 20 volte sotto il t29 (0,113–0,130), che ha
  preso −0,029625.
- **Copertura:** 272 bersagli su 300 coperti, 28 a zero e non osservati; 14.916 geni osservati, il 39% delle coppie
  bersaglio × gene.

**Conseguenza dichiarata prima del punteggio:** il centro registrato (0,07) supponeva l'ampiezza naturale, e non vale
più. Ora mi aspetto un punteggio nella fascia c (sotto 0,06), vicino a quello di un invio a effetto quasi nullo. La
banda e le soglie restano quelle registrate. L'invio procede per decisione del proprietario, che ha chiesto di non
aspettare valutazioni preliminari; finché il punteggio non c'è, può annullarlo con `vcc cancel <entry>`.
