# Adattatore di contesto r2: esito secondo la regola registrata

4 ottobre 2026, corse fra 02:10 e 02:16, ora del PC. Protocollo: [PROTOCOLLO_R2.md](PROTOCOLLO_R2.md), commit 4d0296b.
Codice: [adattatore_r2.py](adattatore_r2.py), commit 1c39d9c. I bersagli di test sono nuovi (divisione con il seme 1).
I `result.json` sono in [esito_r2/](esito_r2/). **Sono coseni di un banco locale, non punteggi VCC.**

## 1. Esito

| Regola | Esito |
|---|---|
| Cancello tecnico | **passa:** 538 bersagli di test nella piega R; nessun NaN |
| **Un braccio ibrido passa** (piega R ≥ +0,01, IC sopra 0; T e H positive) | **no.** Il migliore, `hyb_adapterU − k562` = **+0,0032 [+0,0027; +0,0037]**, è sotto +0,01 |
| Fase 2 (t32) | **nessuna** |
| Strada dell'adattatore | **si ferma**, come scritto nella regola |

## 2. Numeri (coseno medio, bulk-lognorm a 50.000)

| Piega (bersagli) | `k562` | `hyb_ridge` | `hyb_adapter` | `hyb_adapterU` | Miglior differenza [IC 95%] |
|---|---|---|---|---|---|
| R, RPE1 (538) | 0,1064 | 0,1093 | 0,1091 | 0,1096 | `hyb_adapterU` +0,0032 [+0,0027; +0,0037] |
| T, Tian 2021 (35) | 0,0185 | 0,0183 | 0,0186 | 0,0185 | `hyb_adapter` +0,0001 [−0,0011; +0,0013] |
| H, HipSci (90) | 0,0598 | 0,0635 | 0,0663 | 0,0603 | `hyb_adapter` +0,0065 [+0,0036; +0,0098] |

- **β scelto:** 4, l'estremo della griglia, in tutti i bracci e in tutte le pieghe. In validazione il coseno saliva
  ancora a β = 4. Le uscite dei modelli sui geni U sono piccole: è il restringimento della perdita già visto nel t30.
- **Coseno dei modelli sui soli geni U (piega R):** 0,055–0,059.

## 3. Lettura

- **Misurato:** tenere la copia di K562 sui geni misurati e aggiungere il modello sugli altri non peggiora mai e
  migliora poco. Il guadagno è positivo con IC sopra 0 nelle pieghe R e H, nullo in T.
- **Misurato:** la grandezza, +0,003–0,007 di coseno, è molto sotto quella che servirebbe (la soglia di +0,01, e per l'MSE
  un coseno di almeno 0,22).
- **Interpretazione:** β al bordo dice che una griglia più larga darebbe un po' di più. È però un ritocco scelto dopo
  aver visto i numeri, e in validazione questo banco ha già sovrastimato i guadagni sulle linee nuove (r1). Non lo
  faccio senza una nuova registrazione e bersagli nuovi.
- **Previsioni registrate:**

  | Previsione | Atteso | Esito |
  |---|---|---|
  | Miglior ibrido − `k562` (R) | da 0,00 a +0,03, centro +0,01 | +0,0032: dentro la banda, sotto il centro |
  | Un braccio passa | fiducia 0,45 | no |
  | β di `hyb_adapter` | da 0,5 a 2 | 4: fuori |

## 4. Che cosa dice per i modelli

Con i dati in locale (K562 come ingresso, linee d'addestramento dominate da 19 HipSci molto simili), un modello appreso
non trasforma l'effetto di K562 meglio della copia su una linea nuova. Al più aggiunge un po' sui geni che K562 non
misura.

Per un modello di contesto servono linee d'addestramento varie e genome-wide, come le sorgenti della ricetta (CD4,
HCT116, HEK293T, nelle cache r9 di Davide) e Jurkat e HepG2 (su Kaggle). Questa è una proposta, non una cosa misurata.
