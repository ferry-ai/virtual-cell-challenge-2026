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
