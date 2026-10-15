# Miscela di `ta 42`: il peso e ESM2 come terzo ingrediente, sui fold

16 ottobre 2026. Claude Code per Alfredo, che ha chiesto in chat di provare sul banco il peso 0,5 ed ESM2.

## Dati di ESM2 (dataset pubblici di Davide, misurato sui file prima del banco)

**Da dove vengono:** `davideferrante11/vcc-p3-esm2b-j-k562-c2-r1` e `-ipsc-c2-r1`, file `J-<fold>_E2b.npz`, cioè la
variante E2b usata come riempimento in `td 40`.

**Che cosa contengono:**
- previsioni ESM2 + ridge in **regime J**: il bersaglio è nascosto all'addestramento;
- **solo 66 bersagli** del pannello e **solo i fold K562 e iPSC**;
- direzione quasi ortogonale a T3f: coseno mediano 0,008 su K562 e 0,009 su iPSC; norma circa 0,4 volte T3f.

**Precedente:** Davide aveva già misurato che ESM2 riconosce un segnale specifico del bersaglio solo contro la verità
iPSC (CP-0072 sul `main`).

**Limite:** la parte B si regge su 2 fold × 66 bersagli. È un campione piccolo.

## Protocollo e regola (fissati prima dei numeri)

[banco_esm2.py](banco_esm2.py) riprende [banco_t3.py](../rete_su_t3_2026-10-15/banco_t3.py): stessi fold, bersagli,
semi della rete e misure.

| Parte | Fold e bersagli | Bracci |
|---|---|---|
| **A, peso** | 4 fold, tutti i bersagli | `ens_w` = w × T3 + (1 − w) × rete, w = 0,4 … 0,8 |
| **B, ESM2** | K562 e iPSC, i 66 bersagli | `e2b` da solo; `mix3e_w` = T3 : rete : E2b = 0,7(1−w) : 0,3(1−w) : w, con w = 0,1, 0,2 e 0,3 |

In entrambe le parti il riferimento è `ens_0.7`, la ricetta di `ta 42`.

**Regola, per ciascuna parte:** un braccio diventa una proposta per il sito se, in media sui suoi fold:
- l'indice PDS è ≥ quello di `ens_0.7` + 0,005;
- il coseno è ≥ quello di `ens_0.7`.

Fra quelli che passano si propone quello con l'indice PDS più alto. **Il banco non invia nulla.**

**Nota per la lettura, da non usare per spostare la regola:** per `ta 42` il banco aveva previsto +0,012 di indice PDS,
e il sito ha dato +0,064 di PDS scalato. Sulle miscele il banco può essere prudente.

## Esito (misurato, letto dopo il commit `982b8f6` della regola)

**Una prima corsa è fallita** perché puntava a una cartella ESM2 non ancora creata. Il suo log resta in
`processed/miscela_pesi_esm2_2026-10-16/`. La corsa valida è `processed/miscela_pesi_esm2_2026-10-16_r2/`, con gli
stessi file E2b copiati in una cartella sola:
- valori in [result_banco.json](result_banco.json);
- log in [run_banco.log](run_banco.log).

I bracci `t3`, `rete_c` ed `ens_0.5`/`ens_0.7` riproducono esattamente i banchi del 15/10.

### Parte A, il peso (4 fold, tutti i bersagli)

| Peso di T3 | Coseno | Indice PDS | Fedeltà | nMAE |
|---|---|---|---|---|
| 0,4 | 0,1003 | 0,3553 | 0,519 | 1,009 |
| 0,5 | **0,1005** | 0,3598 | 0,518 | 1,010 |
| 0,6 | 0,0996 | 0,3631 | 0,517 | 1,011 |
| **0,7** (`ta 42`) | 0,0974 | **0,3662** | 0,516 | 1,011 |
| 0,8 | 0,0940 | 0,3661 | 0,515 | 1,012 |

**Regola: nessun peso batte 0,7.**
- L'indice PDS è piatto fra 0,7 e 0,8; con 0,5 perde 0,006.
- Il coseno ha il massimo a 0,5, ma per poco (+0,003).

### Parte B, ESM2 come terzo ingrediente (K562 e iPSC, 64 + 59 bersagli con verità)

| Braccio | Coseno | Indice PDS | Fedeltà | nMAE |
|---|---|---|---|---|
| `t3` | 0,118 | 0,460 | 0,518 | 0,983 |
| `e2b` da solo | 0,056 | **0,106** | 0,515 | 0,999 |
| `ens_0.7` (`ta 42`) | 0,120 | 0,473 | 0,521 | 0,982 |
| `mix3e_0.1` | 0,127 | **0,478** | 0,523 | 0,978 |
| `mix3e_0.2` | **0,131** | 0,442 | 0,525 | 0,974 |
| `mix3e_0.3` | 0,130 | 0,380 | 0,526 | 0,971 |

**Regola: non passa per poco.** `mix3e_0.1` guadagna +0,0047 di indice PDS, sotto la soglia di +0,005, e +0,007 di
coseno.
- Il segno cambia fra i fold: K562 −0,009, iPSC +0,019.
- Con più ESM2 il coseno e i membri DE migliorano un poco (fedeltà +0,005, nMAE −0,011 a w = 0,3), ma il PDS crolla.

### Che cosa si capisce (interpretazione)

- **0,7 resta il peso giusto** per il PDS, che è il membro su cui la miscela guadagna.
- **ESM2 è quasi ortogonale a T3,** con coseno circa 0 con i suoi bersagli, e da solo discrimina pochissimo. Al 10% è
  al limite: un guadagno dentro il rumore, con segno opposto sui due fold, su un campione di circa 120 bersagli.
- **Nessuno dei due giustifica un invio.**
