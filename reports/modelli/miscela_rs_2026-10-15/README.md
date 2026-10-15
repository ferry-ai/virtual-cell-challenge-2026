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
