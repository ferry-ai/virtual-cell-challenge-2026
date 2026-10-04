# Rete contrastiva sugli effetti: esito secondo la regola registrata

4 ottobre 2026, corsa fra 15:45 e 15:47, ora del PC. Protocollo e codice nel commit c31c4b3, prima della corsa.
Il `result.json` e gli sha256 dei checkpoint sono in [esito/](esito/). **Sono coseni di un banco locale, non punteggi
VCC: un banco locale ha già sovrastimato la gara tre volte.**

## 1. Esito

| Regola | Esito |
|---|---|
| Cancello tecnico | **passa:** da 56 a 524 bersagli di test per piega; nessun NaN |
| Macro `contr − k562` ≥ +0,01 con IC sopra 0 | **sì:** **+0,0151 [+0,0137; +0,0164]** |
| Almeno 3 pieghe positive su 5 | **sì:** 4 su 5. In H1 l'arresto torna alla copia (0) |
| Macro della discriminazione ≥ −0,01 | **sì:** −0,0066 |
| **Passa** | **sì.** Si passa alla fase 2 del protocollo: esportazione A, B, C e quota comune; l'invio resta al proprietario |

## 2. Numeri per piega

| Piega (bersagli di test) | Passo `contr` | `contr − k562` [IC 95%] | `cosloss − k562` | Discriminazione `k562` → `contr` (→ `cosloss`) |
|---|---|---|---|---|
| H1 (56) | 0 (copia) | 0 | 0 | 0,975 → 0,975 |
| KOLF (377) | 200 | **+0,009 [+0,006; +0,012]** | −0,008 | 0,871 → 0,828 (→ 0,705) |
| RPE1 (524) | 200 | **+0,032 [+0,028; +0,037]** | +0,031 | 0,856 → **0,866** (→ 0,790) |
| HepG2 (524) | 100 | **+0,029 [+0,025; +0,033]** | 0 (copia) | 0,892 → **0,900** |
| Jurkat (523) | 100 | **+0,005 [+0,003; +0,007]** | 0 (copia) | 0,925 → 0,918 |

- **`contr − cosloss` (macro):** +0,011. L'obiettivo fa la differenza: con la perdita della r3 la discriminazione crolla
  (KOLF 0,705, RPE1 0,790), con quella contrastiva tiene o sale.
- **Quota comune della correzione sulle linee di test:** 0,005–0,065.
- **`contr ≈ contr_swap`** in ogni piega: il guadagno non viene dal basale del contesto.
- **Bersagli del pannello fra quelli di test (descrittivo):** KOLF, 15 bersagli, coseno da 0,066 a **0,086**. H1, 2
  bersagli, invariato.

## 3. Lettura

- **Misurato:** è il primo modello appreso a livello di effetti che batte la copia di K562 su linee tenute fuori senza
  perdere discriminazione: 4 pieghe su 5, e sui bersagli del pannello presenti in KOLF.
- **Misurato:** la perdita contrastiva è la causa del passaggio. La stessa rete con la perdita precedente, sulla stessa
  divisione, non passa e distrugge la discriminazione.
- **Misurato:** l'arresto sceglie passi molto precoci (100–200). La correzione resta piccola e vicina alla copia.
- **Interpretazione:** il modello non impara il contesto (il basale non conta). Impara una trasformazione generale
  degli effetti K562 che li rende più vicini agli effetti veri in altre linee, preservando ciò che distingue i
  bersagli.
- **Previsioni registrate:**

  | Previsione | Atteso | Esito |
  |---|---|---|
  | Macro `contr − k562` | da −0,005 a +0,02, centro +0,005 | +0,015: dentro, sopra il centro |
  | Passa | fiducia 0,25 | sì |
  | Discriminazione | da −0,02 a +0,02 | −0,007: dentro |
  | `contr − cosloss` | da −0,01 a +0,01 | +0,011: fuori, sopra |
  | Pieghe che tornano alla copia | 1–3 | 1: dentro |

## 4. Limiti

- È un banco locale, e il coseno non è lo scorer. Il guadagno (+0,015 di coseno su una base di circa 0,1) è piccolo
  rispetto alla soglia di 0,22 che servirebbe per l'MSE.
- Un seme.
- H1 non è stata letta: l'arresto è tornato alla copia.
- Le linee di test non sono A, B, C né D, E, F.
