# t39: transfer congelato con riempimento ESM2

**Decisione del Lead, 10 ottobre 2026:** invio esplorativo autorizzato dal
proprietario con «ok decidi tu, vai e inviamo», dopo la proposta di usare il
candidato già fittato. Nessun nuovo training; AMMI continua separatamente.

La [previsione](prediction.json) fissa artefatto, generatore, banda soggettiva
0,125–0,170 e regola ±0,005 contro t36 prima della generazione. Il confronto
con t38 è descrittivo: il candidato usa T0, non T3. La ricetta di T0 e la
parità numerica con lo storico vanno documentate, non dedotte dai nomi.

Gli [effetti consegnati](../../analisi/modelli_esterni_01a11c35_2026-10-08/esm2_production_delivery_r1.json)
riempiono 390.819 coppie bersaglio-gene, lasciando T0 invariato sul suo supporto.
La scala 1,576 è già applicata al riempimento; la scala di emissione 1,5 resta
quella del generatore di riferimento e non è una seconda applicazione di 1,576.

## Precedenti

- [S-013](../../../docs/STRADE.md#s-013--ridge-sugli-embedding-esm2-del-bersaglio-senza-contesto-regime-t):
  il ridge nativo non sostituisce il transfer; qui interviene soltanto sui vuoti.
- [S-015](../../../docs/STRADE.md#s-015--riempire-con-il-ridge-esm2-le-coppie-che-il-transfer-non-prevede-fallback):
  la vecchia discriminazione vedeva meno del 4% del riempimento giudicabile.
  L'errore quadratico peggiora; il primo fold a sei membri distingue il vero
  bersaglio da quello scambiato, ma non dimostra un beneficio rispetto a T0.
- [CP-0064](../../../docs/checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md):
  non cambiare baseline, ampiezza o export fra banco e invio. I controlli precoci
  sono hash, parità di T0 sul supporto, maschere e scalatura. Nessuna miscela con T3.

Il mandato autorizza un tentativo sul sito; non equivale a promozione scientifica,
copertura D-053 completa o generalizzazione dimostrata. La lettura del banco K562
prosegue senza duplicazioni. DATI-TRANSFER è l'unico uploader. Testi e ricevute
del percorso vivono in [trial_2026-10-10](../trial_2026-10-10/).
