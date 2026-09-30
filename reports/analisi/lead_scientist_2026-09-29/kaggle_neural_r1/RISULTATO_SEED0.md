# Seed 0: esecuzione completa, soglia scientifica non superata

**Misurato, 29 settembre 2026.** I cinque fold hanno completato con codice di
uscita zero. `completion.json` registra l'ultimo fold concluso alle 19:24:12 UTC e
`all_five_completed=true`. Lo stato Kaggle ERROR deriva dal solo aggregatore finale:
`cross_family.log` mostra `KeyError: 'null'`, già spiegato nell'emendamento del reader.
Il training non è stato riavviato né modificato.

Sono stati recuperati 61 piccoli report, 14.190.933 byte, con hash in
`results_small_r1/download_manifest.json`. I 12 export NPZ e 10 checkpoint rimangono
negli output remoti. Il servizio statico `list_kernel_session_output` li espone;
il servizio `kernels files` risultava ancora vuoto. Non è prova di output perduti.

Il comando `read_neural_verified.py` ha verificato identità del codice e dei dati,
coerenza delle opzioni, esclusione dei fold, disgiunzione delle righe e copertura
appaiata di contesti/target/bracci. Ha quindi letto tutti e cinque i fold con la
correzione meccanica `keep_default_na=False`. Evidenza primaria:
`readout_verified_r1/provenance.json` e `readout_verified_r1/verdict.json`.

| Famiglia esclusa | Rango medio rete − transfer |
|---|---:|
| CD4 | +0,00515737 |
| iPSC | +0,00327814 |
| K562 | −0,00722898 |
| Orion | −0,00131291 |
| RPE1 | +0,01121805 |
| Macro, uguale peso alle famiglie | **+0,00222233** |

Il CI95 preregistrato della differenza macro è `[+0,00055605; +0,00390661]`.
Il punto medio è inferiore alla soglia fissata `+0,01`, quindi
`eligible_for_cell_scorer=false`. Nessuna famiglia viola il limite `−0,01`, ma
questo non compensa il mancato requisito sul miglioramento medio.

Rete − rete cieca: `−0,00041611`, CI95 `[−0,00104444; +0,00021331]`.
Rete − contesto scambiato: `−0,00022283`, CI95 `[−0,00043760; −0,00001679]`.
Rete − prior permutati: `−0,00023188`, CI95 `[−0,00050340; +0,00003096]`.
Il reader restituisce `evidence_for_context_use=false`.

**Interpretazione:** questo esperimento non dimostra il vantaggio biologico della
condizionalità introdotta, né un incremento sufficiente della baseline. La rete
testata e il suo criterio di training non vengono promossi. Il risultato non
dimostra che ogni modello neurale o ogni uso di fonti multiple sia inefficace.
I CI sono condizionati alle cinque famiglie osservate; la sensibilità cluster
rimane distinta e non cambia la soglia primaria.

Il proxy copre 12 contesti e 6.144 occorrenze di target fuori pannello, sei bracci
appaiati. Non è uno score VCC e non è validazione cellulare. La replica seed 1 era
stata autorizzata e avviata prima di questa lettura; prosegue integralmente come
da emendamento, anche dopo l'esito negativo di seed 0. Nessun fit di produzione
o selezione del seme favorevole è stato eseguito.
