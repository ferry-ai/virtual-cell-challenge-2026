# Terzo ingrediente per la miscela di `ta 42`: RSB di Davide sui fold

15 ottobre 2026, 23:50 CEST. Claude Code per Alfredo, che ha chiesto in chat di provare la miscela con `td 41` come
terzo ingrediente e di riferire prima di decidere se inviarla.

## Che cosa si può misurare, e che cosa no (misurato sui file, prima del banco)

**Previsioni sui fold:** sono nel dataset pubblico `davidmaisterx/vcc-rsb-effects-70dc-r1` (`RSB__C-K562`, `C-iPSC`,
`C-HCT116`, `C-HEK293`; `C-iPSC-pg` ha gli stessi valori di `C-iPSC`). Si chiamano **RSB**.

**Gli effetti di produzione di `td 41`** (`vcc-td41-effects-70dc-r1`) si chiamano **RS**. I due non hanno le stesse
proprietà:

| | Norma rispetto a T3 | Coseno con T3 (mediana) |
|---|---|---|
| RSB sui fold | 1,00 | 0,16–0,23 |
| RS di produzione (`td 41`) | 0,12 | 0,52 |

**Quindi questo banco misura RSB come terzo ingrediente, non `td 41` così com'è stato inviato.** Che RSB e RS siano lo
stesso modello in due configurazioni è un'**ipotesi** da chiedere a Davide.

## Protocollo e regola (fissati prima dei numeri)

[banco_rs.py](banco_rs.py) riprende [banco_t3.py](../rete_su_t3_2026-10-15/banco_t3.py) senza cambiare fold, bersagli,
semi della rete o misure.

**Bracci:**

| Braccio | Che cos'è |
|---|---|
| `t3`, `rete_c`, `rsb` | i singoli predittori |
| `ens_0.7` | la ricetta di `ta 42`, riferimento |
| `mix3_w` | T3 : rete : RSB = 0,7(1−w) : 0,3(1−w) : w, con w = 0,1, 0,2 e 0,3 |

Ogni ingrediente è preso a norma unitaria; la miscela è poi riportata alla norma di T3.

**Regola:** un braccio `mix3` diventa una proposta per il sito se, in media sui quattro fold:
- l'indice PDS è ≥ quello di `ens_0.7` + 0,005;
- il coseno è ≥ quello di `ens_0.7`.

Fra quelli che passano si propone quello con l'indice PDS più alto. **Il banco non invia nulla:** la decisione di
inviare è di Alfredo.

## Esito (misurato, letto dopo il commit `d2b087e` della regola)

Valori in [result_banco.json](result_banco.json), log in [run_banco.log](run_banco.log). I bracci `t3`, `rete_c` ed
`ens_0.7` riproducono esattamente i numeri di
[rete_su_t3_2026-10-15](../rete_su_t3_2026-10-15/README.md): stessi fold, stessi semi.

**Media sui quattro fold:**

| Braccio | Coseno | Indice PDS | Fedeltà | nMAE |
|---|---|---|---|---|
| `t3` | 0,085 | 0,355 | 0,512 | 1,012 |
| `rete_c` | 0,092 | 0,334 | 0,518 | 1,004 |
| `rsb` | 0,012 | **0,105** | 0,503 | **0,970** |
| `ens_0.7` (`ta 42`) | **0,097** | **0,366** | 0,516 | 1,011 |
| `mix3_0.1` | 0,093 | 0,366 | 0,516 | 1,007 |
| `mix3_0.2` | 0,086 | 0,330 | 0,515 | 1,002 |
| `mix3_0.3` | 0,077 | 0,286 | 0,514 | 0,995 |

**Regola: nessun braccio passa.** Il migliore, `mix3_0.1`, pareggia l'indice PDS di `ens_0.7` (0,3658 contro 0,3662)
e ha meno coseno.

**Che cosa si capisce (interpretazione):**
- **RSB da solo discrimina poco i bersagli** del pannello: indice PDS 0,105 contro 0,355 di T3. Il coseno è negativo
  su K562, HCT116 e HEK293T, e alto (0,321) solo su iPSC.
  - **Ipotesi da chiedere a Davide:** il fold iPSC di RSB potrebbe non escludere tutte le tabelle staminali.
- **RSB è poco correlato** con T3 (0,19–0,26) e con la rete (0,07–0,10), ma non aggiunge segnale utile, quindi la
  media lo diluisce. Per la miscela non basta essere poco correlati: serve anche qualità.
- **RSB ha l'nMAE migliore di tutti** (0,970): sulle magnitudini dei geni DE è buono, sulla direzione no.

**Proposta:** non inviare una miscela con RSB. Per `td 41` (RS di produzione) il banco non dice nulla, perché le sue
proprietà sono diverse da RSB (vedi sopra). Serve sapere da Davide che cos'è RS e il punteggio di `td 41`.
