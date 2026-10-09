# AMMI cells C-K562 pronto per la lettura indipendente

10 ottobre 2026, 00:57 Europe/Rome. **Esito tecnico, beneficio non verificato.**
Fonte privata `davidmaisterx/ammi-c-k562-cells-17-01a11c35-r5`, terminata alle
00:47:45. Due epoche, 384 righe per epoca, 30 contesti e cinque lignaggi; guardie
interne superate e uso delle righe/pesi selezionati attestato. Fit 7.384 s.
Le ricevute sono `ammi_c-k562_cells_auto_retrieval_r1.json` e
`ammi_c-k562_cells_auto_metadata_verified_r1.json`. I loro file locali sono stati
ricontrollati per hash preparando `ammi_C-K562_cells_delivery_r1.json`.

La consegna segue il contesto primario fissato prima dei risultati,
`k562_gwps:48d8d89e89785608`; non seleziona sulla qualità delle predizioni.

| Export | Byte | SHA256 |
|---|---:|---|
| `ammi-c-k562-cells-17-01a11c35-r5/query_001_native.npz` | 18.249.570 | `e0ca5905005df7dad8bc20c34f71263f9bf6e7e41b57b11e9b34ad6fea1ec2be` |
| `ammi-c-k562-cells-17-01a11c35-r5/query_001_swapped.npz` | 18.206.800 | `3358e599c745815315aa39e053c95b034dcdf1225d7c965bca395dd6dc766a03` |

Totale 36.456.370 byte. Gli hash sono quelli dichiarati dal produttore; la verifica
indipendente dei payload resta al consumer. Confermata la stessa ancora fra cells
e none. Confronti richiesti: cells−A0, cells−none e cells−swapped; cells−T0 va
tenuto distinto perché T0 non è l'ancora annidata A0. Export Essential e relative
ricevute restano preservati come descrittivi, senza crearne repliche indipendenti.

**Dipendenza concreta per VALIDAZIONE:** destinazione privata precisa su df11 e
consenso al passaggio di questi due output, come previsto nel suo MESSAGGI delle
22:20. Il consenso ai 209 input di produzione non è stato esteso agli output.
Nessun nuovo locator emesso, array scaricato o banco duplicato da MODELLI.
Il confronto K562 può essere preparato mentre iPSC termina; la decisione di
produzione richiede comunque la lettura di entrambi i fold.

Produzione: bozza con cache e accessi ai 209 input già predisposti e verificati
nei rispettivi manifest. Non avviata; nessuna promozione o completezza D-053.
