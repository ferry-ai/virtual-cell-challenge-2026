# Registro previsione → punteggio

Scritto da `invii/registro.py rapporto` dal registro costruito alle 2026-10-09 19:13 UTC; nessun numero è ricopiato a mano. Punteggi ufficiali: classifica di validazione sui contesti A, B, C. Le previsioni di banco sono numeri locali, mai punteggi VCC. Soglia operativa per un delta «indistinto»: 0,005.

## 1. Ogni invio: che cosa era registrato, che cosa è uscito

| Invio | Data | Ufficiale | PDS | MSE | NMAE | FID | REACH | JAC | Banda registrata | Esito | Riferimento | Delta ufficiale | Banda del delta | Registrazione |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---:|---|---|
| t01 | 2026-09-13 | +0,045929 | +0,413 | +0,000 | +0,027 | -0,182 | +0,021 | -0,003 | — | — | — | — | — | nessuna previsione |
| t02 | 2026-09-17 | -0,092774 | +0,240 | +0,000 | +0,047 | -0,870 | +0,067 | -0,040 | — | — | — | — | — | nessuna previsione |
| t03 | 2026-09-17 | +0,019692 | +0,325 | +0,000 | +0,043 | -0,301 | +0,074 | -0,023 | — | — | — | — | — | dichiarata nel file |
| t07 | 2026-09-19 | -0,016004 | +0,059 | +0,000 | -0,028 | -0,120 | +0,010 | -0,017 | — | — | — | — | — | verificata dal commit |
| t08 | 2026-09-22 | +0,060370 | +0,466 | +0,000 | +0,039 | -0,178 | +0,035 | -0,000 | 0,030 … 0,060 | fuori di +0,0004 | — | — | — | verificata dal commit |
| t10 | 2026-09-23 | +0,050191 | +0,428 | +0,000 | +0,035 | -0,172 | +0,014 | -0,003 | 0,040 … 0,060 | dentro | — | — | — | verificata dal commit |
| t11 | 2026-09-23 | +0,070777 | +0,530 | +0,000 | +0,039 | -0,182 | +0,038 | -0,002 | 0,055 … 0,075 | dentro | — | — | — | verificata dal commit |
| t14 | 2026-09-24 | +0,064892 | +0,402 | +0,000 | +0,103 | -0,217 | +0,121 | -0,020 | 0,020 … 0,120 | dentro | — | — | — | verificata dal commit |
| t15 | 2026-09-24 | +0,107533 | +0,607 | +0,000 | +0,084 | -0,119 | +0,067 | +0,006 | 0,060 … 0,095 | fuori di +0,0125 | — | — | — | verificata dal commit |
| t16 |  | +0,137627 | +0,617 | +0,000 | +0,122 | -0,032 | +0,107 | +0,012 | 0,080 … 0,140 | dentro | t15 | +0,0301 | fuori di +0,0001 | data dell'invio non salvata |
| t17 | 2026-09-25 | +0,108774 | +0,597 | +0,000 | +0,087 | -0,125 | +0,088 | +0,005 | 0,095 … 0,125 | dentro | t15 | +0,0012 | dentro | verificata dal commit |
| t20 | 2026-09-26 | +0,139676 | +0,642 | +0,000 | +0,087 | -0,035 | +0,130 | +0,014 | 0,115 … 0,170 | dentro | — | — | — | verificata dal commit |
| t22 | 2026-09-26 | +0,141250 | +0,634 | +0,000 | +0,120 | -0,052 | +0,131 | +0,014 | 0,125 … 0,152 | dentro | t20 | +0,0016 | dentro | verificata dal commit |
| t23 | 2026-09-28 | +0,141868 | +0,659 | +0,000 | +0,103 | -0,042 | +0,122 | +0,009 | 0,120 … 0,165 | dentro | t22 | +0,0006 | dentro | verificata dal commit |
| t24 | 2026-09-27 | +0,142897 | +0,636 | +0,000 | +0,124 | -0,054 | +0,137 | +0,014 | 0,137 … 0,146 | dentro | t22 | +0,0016 | dentro | verificata dal commit |
| t25 | 2026-09-27 | +0,140238 | +0,624 | +0,000 | +0,118 | -0,058 | +0,144 | +0,014 | 0,133 … 0,152 | dentro | t22 | -0,0010 | dentro | verificata dal commit |
| t26 | 2026-09-29 | +0,138721 | +0,619 | +0,000 | +0,117 | -0,056 | +0,138 | +0,014 | 0,134 … 0,156 | dentro | t25 | -0,0015 | dentro | verificata dal commit |
| t28 | 2026-09-29 | +0,144845 | +0,622 | +0,000 | +0,049 | -0,007 | +0,199 | +0,006 | 0,135 … 0,180 | dentro | t25 | +0,0046 | dentro | dichiarata nel file |
| t29 | 2026-10-01 | -0,029625 | +0,007 | +0,000 | -0,157 | -0,011 | -0,026 | +0,009 | -0,020 … 0,100 | fuori di -0,0096 | t22 | -0,1709 | — | verificata dal commit |
| t30 | 2026-10-04 | +0,135249 | +0,581 | +0,000 | +0,116 | -0,044 | +0,142 | +0,016 | 0,125 … 0,160 | dentro | t25 | -0,0050 | — | verificata dal commit |
| t36 | 2026-10-05 | +0,147249 | +0,631 | +0,000 | +0,072 | -0,010 | +0,187 | +0,004 | — | — | — | — | — | verificata dal commit |
| t38 | 2026-10-09 | +0,148922 | +0,639 | +0,000 | +0,076 | -0,013 | +0,189 | +0,003 | 0,132 … 0,162 | dentro | t36 | +0,0017 | — | verificata dal commit |

**Identità di ogni riga.**

| Invio | Candidato, come registrato | Entry | Pannello | Ancore | Stato salvato |
|---|---|---|---|---|---|
| t01 | trial-01-transfer k01pack a=0.197 sd=4 | `PNn227rxP3bVByS37W41` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-13/status_PNn227rxP3bVByS37W41.json` |
| t02 | trial-02 sc-generator + K562 x1 + cis | `49Gvtu504clN1mIu8T2V` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-17/status_49Gvtu504clN1mIu8T2V.json` |
| t03 | t03 = trial-03 sc-generator + K562 x2 + cis | `0TbVAwhVTj6UYpaU2v9d` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-17/status_0TbVAwhVTj6UYpaU2v9d.json` |
| t07 | t07 = conditioned linear model (split C, alpha 1000) x2.0, sc-generator, no cis | `BV1gqrIYuy2KMVZSGmN4` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-19/status_BV1gqrIYuy2KMVZSGmN4.json` |
| t08 | t08 = trial-01 generator unchanged + effects K562 (0.433) + CD4 pseudobulk (0.567), raw x 0.197, gamma 1 | `NNUXtdhV4ByiETbolCKJ` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-22/status_NNUXtdhV4ByiETbolCKJ.json` |
| t10 | t10 = t08 without CD4: K562 only, raw x 0.197, gamma 1, trial-01 generator, seed 20260912 | `JvksJS5r08YNOP6jfP4Q` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-23/status_JvksJS5r08YNOP6jfP4Q.json` |
| t11 | t11 = t08 + Orion HCT116: K562, CD4, HCT116 at equal weights, raw x 0.197, gamma 1, trial-01 generator | `FEBhtilNLpSm2kGiHB71` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-23/status_FEBhtilNLpSm2kGiHB71.json` |
| t14 | t14 = ControlModel (stage 76, defaults, --keep-effects-target) + t08 effects x 2.5 (a-effects chosen by the pilot rule) | `QiuBir8wNfqDnVdDxqTB` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-23/status_QiuBir8wNfqDnVdDxqTB.json` |
| t15 | t15 = t11 with amplitude 0.394 (2 x 0.197): K562, CD4, HCT116 at equal weights, raw, gamma 1, trial-01 generator | `U1K3SZuq7w5cef9lBKsn` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-24/status_U1K3SZuq7w5cef9lBKsn.json` |
| t16 | t16 = t15 with amplitude 0.788 (2 x 0.394): K562, CD4, HCT116 at equal weights, raw, gamma 1, trial-01 generator | `qUV1D6QZh2tZ5Z9Vx185` | — | — | `reports/invii/prediction_t16_2026-09-24/comparison.json` (solo `comparison.json`: lo stato completo non fu salvato) |
| t17 | t17 = t15 + Orion HEK293T at equal weight, amplitude 0.4285 so that median q99 |ln fc| equals t15's | `4su3dF6Up12QhdCfnNgE` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-24/status_4su3dF6Up12QhdCfnNgE.json` |
| t20 | t20 = t19 plus the CRISPRi cis head: 2 x the K562 median repression by TSS distance (panel targets excluded) added within 5 kb, outside the amplitu… | `I8FX2yQabjKjPPDTYnaW` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-26/status_I8FX2yQabjKjPPDTYnaW.json` |
| t22 | t22 = t20 plus the fourth genome-scale source, HEK293T from X-Atlas/Orion, at equal weight (K562, CD4, HCT116, HEK293T; shrunk effects, gamma 1, am… | `hOy1AirAxJsFvpQAHH15` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-26/status_hOy1AirAxJsFvpQAHH15.json` |
| t23 | t23 = t22 with the transferred part weighted gene by gene by the share of the knockdown response the lines have in common (sigma2 / (sigma2 + tau2)… | `JvKSI2yE5zdnw4Agghvy` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-27/status_JvKSI2yE5zdnw4Agghvy.json` |
| t24 | t24 = t22 regenerated with another generator seed (20260927 instead of 20260912): same effects files, recipe, trial and packaging; a replicate that… | `EZGjM8uKHlF1WokKrY2p` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-27/status_EZGjM8uKHlF1WokKrY2p.json` |
| t25 | t25 = t22 built on the stage-98 cache r9: in the CD4 and Orion sources a donor or pool whose controls predict under one count of a gene in the targ… | `ekxW6wo83Csum25pkddl` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-27/status_ekxW6wo83Csum25pkddl.json` |
| t26 | t26 = t25 with every effect on a gene below 5 CPM in the context's own controls set to 0 (stage 100 expression_gate, cis head included); trial-01 g… | `RKxWmAu7DfInW7j6haeZ` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-29/status_RKxWmAu7DfInW7j6haeZ.json` |
| t28 | t28: t25 external effects x1.5, control-fitted gene dispersion x1 | `ZvrYZ4UazadAyuq4AsDB` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-09-29/status_ZvrYZ4UazadAyuq4AsDB_20260929T2305.json` |
| t29 | t29: single-cell network R-LAB r2, descriptors arm, exported effects with the t22 generator | `K6Q36uGCaEwQ1wRLmBLp` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-10-01/status_K6Q36uGCaEwQ1wRLmBLp_final.json` |
| t30 | t30: D-056 selective hybrid, t25 effects plus the weighted correction of the HepG2-fold cell network | `lDMSYUZU5cFYHcRqI0lq` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-10-04/status_lDMSYUZU5cFYHcRqI0lq.json` |
| t36 | t36 - transfer t28 banca estesa | `JLcMRGExhXKk77XVds7x` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/invii/trial_2026-10-06/status_JLcMRGExhXKk77XVds7x_0138.json` |
| t38 | T3-CRISPRi-KO | `LJmnhqqh1WTrx1JcoRlr` | vcc2026-val-1 | vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4 | `reports/analisi/validazione_banco_eace4d03_2026-10-09/invii/stati/status_LJmnhqqh1WTrx1JcoRlr_20261009T190948Z.json` |

Banchi e scorer locale: **B0** 17–19 settembre 2026, scorer cell-eval2 0.16.0; **B2** 26–29 settembre 2026, scorer cell-eval2 0.16.0; **B3** 4 ottobre 2026, scorer cell-eval2 0.16.0; **B4** 8–9 ottobre 2026, scorer cell-eval2 0.16.0; **B5** dal 9 ottobre 2026, scorer cell-eval2 0.16.0.

Membri: valori scalati pubblicati. «Registrazione»: *verificata dal commit* se il file della previsione è entrato nel repository prima della creazione dell'entry; *dichiarata nel file* se lo dice solo il file.

## 2. Previsioni con un verso: direzione, ampiezza, incertezza

| Invio | Fonte della previsione | Banco | Previsto | Ufficiale | Direzione | Ufficiale − previsto | Ufficiale / previsto | Incertezza registrata | Il candidato era un braccio del banco? |
|---|---|---|---:|---:|---|---:|---:|---|---|
| t03 | banco, punteggio | B0 | +0,0338 | +0,0197 | — | -0,0141 | 0,58 | — | sì |
| t07 | banco, punteggio | B0 | +0,0101 | -0,0160 | — | -0,0261 | -1,58 | — | sì |
| t28 | centro di lavoro (contro t25) | — | +0,0148 | +0,0046 | indistinta | -0,0102 | 0,31 | banda del delta: dentro | — |
| t28 | banco, delta contro t25 | B2 | +0,0289 | +0,0046 | indistinta | -0,0243 | 0,16 | entro due deviazioni standard dei semi del banco: no; nell'intervallo registrato dal banco: no | sì |
| t29 | centro di lavoro (contro t22) | — | -0,1013 | -0,1709 | giusta | -0,0696 | 1,69 | — | — |
| t30 | centro di lavoro (contro t25) | — | +0,0028 | -0,0050 | indistinta | -0,0078 | -1,81 | — | — |
| t30 | banco, delta contro t25 | B3 | +0,0441 | -0,0050 | indistinta | -0,0490 | -0,11 | — | **no** |
| t38 | delta atteso (contro t36) | — | +0,0000 | +0,0017 | attesa nulla confermata | +0,0017 | — | — | — |
| t38 | banco, delta contro t36 | B4 | +0,0000 | +0,0017 | attesa nulla confermata | +0,0017 | — | nella banda registrata: sì | **no** |

## 3. Dove il banco ha sbagliato membro per membro

**t03, banco B0** — livello scalato previsto per membro.

| Membro | Banco | Ufficiale | Ufficiale − banco |
|---|---:|---:|---:|
| PDS | +0,3705 | +0,3254 | -0,0451 |
| MSE | — | +0,0000 | — |
| NMAE | +0,0628 | +0,0432 | -0,0196 |
| FID | -0,2854 | -0,3008 | -0,0154 |
| REACH | +0,1016 | +0,0738 | -0,0278 |
| JAC | -0,0466 | -0,0234 | +0,0233 |

**t07, banco B0** — livello scalato previsto per membro.

| Membro | Banco | Ufficiale | Ufficiale − banco |
|---|---:|---:|---:|
| PDS | -0,0329 | +0,0590 | +0,0918 |
| MSE | — | +0,0000 | — |
| NMAE | +0,0950 | -0,0284 | -0,1233 |
| FID | -0,0552 | -0,1200 | -0,0648 |
| REACH | +0,1048 | +0,0099 | -0,0949 |
| JAC | -0,0509 | -0,0165 | +0,0343 |

**t28, banco B2** — contributo alla media (ufficiale: un sesto del delta scalato del membro).

| Membro | Banco | Ufficiale | Direzione | Ufficiale / banco |
|---|---:|---:|---|---:|
| PDS | -0,0000 | -0,0002 | giusta | 15,36 |
| MSE | — | +0,0000 | — | — |
| NMAE | -0,0033 | -0,0115 | giusta | 3,50 |
| FID | +0,0283 | +0,0085 | giusta | 0,30 |
| REACH | +0,0077 | +0,0091 | giusta | 1,19 |
| JAC | -0,0038 | -0,0013 | giusta | 0,34 |

**t30, banco B3** — delta scalato del membro. La scomposizione per membro è stata riletta **dopo** l'invio da uscite del banco che esistevano prima: serve alla diagnosi, non conta come previsione registrata.

| Membro | Banco | Ufficiale | Direzione | Ufficiale / banco |
|---|---:|---:|---|---:|
| PDS | +0,0075 | -0,0422 | sbagliata | -5,66 |
| MSE | +0,0000 | +0,0000 | nessun movimento | — |
| NMAE | +0,0895 | -0,0019 | sbagliata | -0,02 |
| FID | +0,0418 | +0,0137 | giusta | 0,33 |
| REACH | +0,0467 | -0,0018 | sbagliata | -0,04 |
| JAC | +0,0789 | +0,0023 | giusta | 0,03 |

## 4. Spiegazioni degli errori, con il loro stato di prova

| Invio | Spiegazione | Stato | Fonte |
|---|---|---|---|
| t07 | La taratura a un punto per membro veniva da un invio di un'altra famiglia di modelli: la previsione del banco non regge per una famiglia nuova (+0,010 previsto, −0,016 ufficiale) | **ipotizzata** | `reports/invii/README.md` |
| t15 | Sopra la banda: raddoppiare l'ampiezza valeva più di quanto la banda prevedesse; l'invio successivo (t16, ampiezza quadrupla) ha confermato il verso con +0,030 | **verificata** | `docs/checkpoints/0037-t16-ampiezza-quadrupla.md` |
| t28 | Il delta locale +0,0289 non era una previsione tarata: 95 dei 96 bersagli della conferma erano già stati valutati in un banco precedente, quindi la conferma non era indipendente | **verificata** | `docs/checkpoints/0050-credibilita-score-e-riserva.md` |
| t28 | Quanto dello scarto venga dalla riserva non indipendente e quanto dalla differenza fra HepG2 e i contesti di gara non è separato | **ignota** | `docs/checkpoints/0052-t28-punteggio-ufficiale.md` |
| t28 | Verso giusto su tutti i membri previsti, ampiezza sbagliata in due: il guadagno di fedeltà è circa un terzo del previsto e la perdita di NMAE circa tre volte e mezza (tabella del §3) | **verificata** | `reports/invii/prediction_t28_2026-09-29/comparison.json` |
| t29 | La rete distingue poco i bersagli: PDS grezzo 0,50 contro 0,79 della ricetta; risposta comune, calibrazione, apprendimento ed esportazione restano da separare | **ipotizzata** | `docs/checkpoints/0055-t29-rete-cellulare-punteggio.md` |
| t30 | Il candidato inviato non era un braccio del banco: baseline, stimatore della correzione e regime degli ingressi diversi da quelli valutati | **verificata** | `reports/modelli/diagnosi_t30_2026-10-04/TABELLA_CATENA.md` |
| t30 | All'esportazione la correzione era per circa due terzi comune ai bersagli (0,62–0,69) contro 0,17 nel training: una guardia del training non applicata all'inferenza | **verificata** | `reports/modelli/diagnosi_t30_2026-10-04/esito/export_vs_rows_r1.json` |
| t30 | Il guadagno di banco era letto a un seme e 32 cellule per bersaglio: su cinque semi e 400 cellule la media delle cinque linee scende da +0,044 a +0,013, e il +0,074 di K562 veniva per il 77 % da un JAC locale con denominatore 0,047 | **verificata** | `docs/checkpoints/0065-d056-confronti-e-rumore-del-banco.md` |
| t30 | La media del banco copriva la perdita del membro che pesa di più: sul sito il PDS scende di 0,042, mentre il banco lo dava in lieve salita in media | **verificata** | `docs/checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md` |

## 5. Che cosa si può dire, e che cosa no

- Invii con punteggio: **22**; con una previsione registrata: **20**. Senza alcuna previsione: t01, t02. Registrati senza previsione numerica: t36. Queste assenze restano assenze.
- Bande del punteggio: **14 su 17** contengono l'esito; fuori: t08, t15, t29. Bande del delta: **7 su 8**.
- Delta ufficiali contro il riferimento registrato: 11 letti, **9 sotto la soglia di 0,005**: su quelli il verso ufficiale non si distingue e non conta né giusto né sbagliato.
- Previsioni con un verso (centro di lavoro o delta atteso): attesa nulla confermata 1; giusta 1; indistinta 2.
- Previsioni puntuali di un banco su un delta, con esito: t28 (B2) previsto +0,0289, ufficiale +0,0046; t30 (B3) previsto +0,0441, ufficiale -0,0050.
- Membri con il verso giusto, dove il banco aveva un membro: t28 5 su 5; t30 2 su 5.

| Banco | Previsioni con esito | Di cui delta con segno | Direzione | Taratura numerica |
|---|---:|---:|---|---|
| B0 — stadio 84: banco K562→HepG2 riportato alla scala ufficiale con una taratura a un punto per membro | 2 (t03, t07) | 0 | — | non sostenuta: 0 previsioni puntuali con segno, ne servono almeno 8 |
| B2 — banco HepG2 v2 con lo scorer vero, conferma del generatore r3 (96 bersagli, tre semi) | 1 (t28) | 1 | indistinta 1 | non sostenuta: 1 previsioni puntuali con segno, ne servono almeno 8 |
| B3 — cubo r2, corsia B a sei membri su cinque linee escluse (protocollo D-056) | 1 (t30) | 1 | indistinta 1 | non sostenuta: 1 previsioni puntuali con segno, ne servono almeno 8 |
| B4 — validazione indipendente v1/v2: lignaggio escluso sul pannello, livello A su sei fold e sei membri su K562 e iPSC | 1 (t38) | 0 | — | non sostenuta: 0 previsioni puntuali con segno, ne servono almeno 8 |

## 6. In attesa

Nessun invio in attesa di punteggio.
