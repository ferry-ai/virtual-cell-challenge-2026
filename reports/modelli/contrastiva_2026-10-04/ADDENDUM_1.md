# Addendum 1: la copia del banco non è la copia del t31

4 ottobre 2026, verso le 15:55, ora del PC. Scritto **prima** del conto che descrive. Il commit che aggiunge questo
file ne fissa l'ora.

## Che cosa ho trovato esportando A, B, C (misurato)

Fonte: `vcc2026-data/processed/effects_contr_2026-10-04/export.json` più un controllo eseguito a mano.

- **Due copie diverse.** Il banco confronta tutto nello spazio bulk-lognorm `d`. Il braccio `k562` è quindi «lo stesso
  spostamento `d` misurato in K562», calcolato con il basale di K562. Il t31, invece, trasferisce **lo stesso log fold
  change**, che nello spazio `d` di una linea si scrive `to_d(lfc_K562, basale della linea)`. Sono due copie diverse.
  - Riportata in lfc con il basale di A, la copia `d` ha coseno mediano **0,286** con l'lfc del t31.
- **L'esportazione è sbilanciata.** Riportata in lfc, l'86% della norma sta sui geni che K562 non misura. Piccole
  correzioni `d` su geni poco espressi in A diventano lfc grandi: 9.398 geni su 18.533 hanno 5e4 · p < 0,5 in A.
  Uguagliare la norma per bersaglio a quella del t31 in lfc schiaccia così la parte misurata, e il coseno con il t31
  scende a 0,10.
- **Conclusione:** l'esportazione di `effects_contr_2026-10-04` **non è un candidato**. Né il confronto «un solo fattore
  contro il t31» né la regola d'ampiezza valgono così come sono.
- **Correzione di quanto scritto nei protocolli** (r1, r2, r3, denoiser, contrastiva): la tabella dei bracci dice che
  `k562` è «la forma del t31». Lo è per le sorgenti e i bersagli, non per la semantica dell'effetto: è una copia nello
  spazio `d`.

## Il controllo, fissato ora (prima di calcolarlo)

Si aggiunge un braccio di confronto `k562_lfc` = `to_d(lfc_K562, basale della linea di test)`, cioè la copia nella
semantica del t31, sulle stesse coppie di test delle cinque pieghe della contrastiva (divisione con il seme 4). Si
rileggono i checkpoint `contr_<piega>.pt` già salvati, senza riaddestrare.

- **Regola:** la contrastiva resta candidabile solo se la macro `contr − k562_lfc` ≥ **+0,01**, con il limite inferiore
  dell'IC 95% sopra 0 (bootstrap come nel protocollo), e la discriminazione di `contr` non scende più di 0,01 sotto
  quella di `k562_lfc`.
- **Si riporta anche, senza che decida,** `k562_lfc − k562`: dice quale copia è la base migliore.
- **Se la regola passa:** il candidato si esporta nello spazio `d` del contesto (`d_to_lfc` con il basale del
  contesto). L'ampiezza si fissa in `d`, non in lfc, e i geni con 5e4 · p < 0,5 nel contesto restano a 0 e non
  osservati. La regola d'ampiezza e la previsione si registrano a parte, prima di generare.
- **Se non passa:** il guadagno del banco era sopra una base sbagliata, e la contrastiva non va in gara in questa forma.
