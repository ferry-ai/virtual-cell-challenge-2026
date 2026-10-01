# Secondo training della rete cellulare, sul corpus supervisionabile completo: protocollo e regola di lettura

1 ottobre 2026, 02:40 CEST, Claude Code (sessione `07ebf08b`), scheda
[R-LAB](../../../docs/piani/piano-giorno-2026-09-30.md). **Scritto prima di vedere qualunque numero del primo training**
([cellnet_tecnico_2026-10-01](../cellnet_tecnico_2026-10-01/PROTOCOLLO.md), in corso a quest'ora) **e prima di lanciare
questo**. Codice: [risposta_biologica_2026-09-30](../risposta_biologica_2026-09-30/), al commit scritto in
`lancio_training.json` di questa cartella.

## 1. Che cosa è

Ancora una **verifica tecnica**, non un risultato: un solo seme, un solo contesto tenuto fuori (HepG2), nessuna riserva
aperta, nessun confronto a sei membri. Rispetto al primo training cambia solo il corpus: entrano K562 genome-wide,
K562 essenziali e RPE1, riletti dopo l'incidente E-20260930-003. Il resto (regole dei dati, rete, bracci, regola di
lettura) è identico, salvo il budget.

## 2. Dati

Pre-passo `rlab-prepass-r4` (CPU) con `--holdout-context HepG2 --same-experiment
h1_vcc2025=h1_vcc2025_train,h1_vcc2025_val`, sui dataset di `davidmaisterx`: `rlab-hepg2-nadig` (tenuto fuori),
`rlab-jurkat-nadig`, `rlab-h1-vcc2025-trainval`, `rlab-hipsci-gwfit`, `rlab-hipsci-gwnonfit`, `rlab-hipsci-targeted19`,
`rlab-k562-gwps-r2`, `rlab-k562-essential`, `rlab-rpe1`. Fuori, con il motivo: il dataset `rlab-k562-gwps` del 30/09
(codici al posto dei bersagli); Jurkat GSE249595 (nessuna chiamata delle guide); lo split di test di H1 2025 (la
riserva); la seconda ondata (in ingestione stanotte, job 116-120); tutto ciò che il
[catalogo](../../sorgenti/corpus_cellulare_2026-09-30/catalogo_r2/CATALOGO.md) segna come non ancora ingerito.

## 3. Disegno e budget

Kernel GPU T4×2 `rlab-cellnet-r2`, bracci in parallelo `desc` (cuda:0, `--target-code descriptors`) e `ident` (cuda:1,
`--target-code identity`), comuni: `--epochs 10 --workers 2 --budget-minutes 150 --checkpoint-minutes 15
--eval-reserve-seconds 120`, il resto di default come nel primo training. Nessun ciclo di ripresa: il primo training lo
verifica su CUDA (se non passa, questo lancio non parte). Quota: circa 2 ore e 45 minuti delle circa 4 rimaste.

## 4. Regola di lettura, fissata ora

**A. Esito tecnico, voce per voce:** kernel con codice 0; `verify.json` di ogni braccio senza shard diversi;
`coverage.json` con non-contaminazione passata e, se `epochs_done` ≥ 1, ogni cellula di training ammessa vista;
`eval.json` completo entro il budget; throughput, frazione di attesa dei dati e memoria riportati.

**B. Lettura descrittiva, che non decide nulla sulla rete:** per classe (C, T, J) e per braccio, le stesse misure del
primo training. **Attese scritte ora:** (i) guadagno di log-verosimiglianza rispetto a nessun effetto positivo in media su
C e T in entrambi i bracci; (ii) su J il braccio `identity` non ha informazione sul bersaglio nuovo (quota di guadagno
specifico positivo vicina o sotto 0,5), `descriptors` sopra `identity` è ciò che l'ipotesi dei descrittori prevede;
(iii) nessuna attesa che la rete batta il trasferimento su C. Il confronto con il primo training (più dati, stesso
resto) è descrittivo: un seme per training, e i gruppi di valutazione cambiano con il corpus.

Con un seme e un contesto tenuto fuori nessuna di queste attese, vera o falsa, è una prova; i numeri non entrano in
PROGETTO §0 come risultati.
