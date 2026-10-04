# Adattatore di contesto r1: esito secondo la regola registrata

4 ottobre 2026, verso le 2:10, ora del PC (log delle corse fra 02:04 e 02:08). Protocollo: [PROTOCOLLO.md](PROTOCOLLO.md),
commit 13a2d2b. Codice: [adattatore.py](adattatore.py), commit 221167b, entrambi prima di ogni corsa. Corse locali sulla
RTX 4080, seme 0. Uscite in `vcc2026-data/processed/adattatore_2026-10-04/fold_<F>_seed0/`; i `result.json` sono copiati
in [esito_r1/](esito_r1/), con gli sha256 dei checkpoint. **Sono coseni di un banco locale, non punteggi VCC.**

## 1. Esito

| Regola | Esito |
|---|---|
| Cancello tecnico | **passa:** 539 bersagli di test nella piega R; nessun NaN; coseno di validazione di `adapter` 0,0658 contro 0,0613 di `k562` |
| **Un modello appreso passa** | **no.** Nella piega R `adapter − k562` = **−0,016 [−0,023; −0,010]**, `ridge − k562` = **−0,033 [−0,040; −0,025]** |
| Candidato per la fase 2 | **nessuno**: niente esportazione né t32 |

## 2. Numeri (coseno medio sulle coppie di test, spazio bulk-lognorm a 50.000)

| Piega (bersagli di test) | `k562` | `ridge` | `adapter` | `adapter_swap` | `adapter − k562` [IC 95%] |
|---|---|---|---|---|---|
| R, RPE1 (539) | **0,106** | 0,074 | 0,090 | 0,093 | −0,016 [−0,023; −0,010] |
| T, neuroni Tian 2021 (40) | **0,014** | −0,002 | 0,004 | 0,003 | −0,010 [−0,015; −0,006] |
| H, 2 donatori HipSci (91) | **0,051** | 0,037 | 0,048 | 0,048 | −0,002 [−0,010; +0,005] |

**Per gruppo di geni,** dove M sono i geni che K562 misura e U quelli che non misura:

| Piega | `k562` su M | `adapter` su M | `adapter` su U (`k562` vale 0) | `ridge` su U |
|---|---|---|---|---|
| R | 0,120 | 0,096 | **0,064** | **0,069** |
| T | 0,019 | 0,005 | 0,001 | −0,002 |
| H | 0,064 | 0,055 | **0,034** | 0,028 |

**Validazione** (linee d'addestramento, bersagli nuovi), `adapter` contro `k562`: R 0,066 contro 0,061; T 0,116 contro
0,073; H 0,129 contro 0,075.

## 3. Lettura

- **Misurato:** su una linea mai vista nessun modello appreso batte la copia di K562, in nessuna delle tre pieghe.
  `adapter` batte `ridge` in R e H.
- **Misurato:** i modelli danno un coseno positivo sui geni che K562 non misura (R 0,06–0,07; H 0,03), dove la copia
  vale zero. Però peggiorano la direzione sui geni che K562 misura (R da 0,120 a 0,096), e il saldo è negativo.
- **Misurato:** `adapter_swap` (il basale di un'altra linea) non è peggio di `adapter`. Il modello non usa il contesto
  in modo utile.
- **Interpretazione:** sulle linee d'addestramento il modello guadagna molto (fino a +0,054 in validazione), su una
  linea nuova no. Ha imparato schemi propri delle linee viste, soprattutto delle 19 HipSci che dominano
  l'addestramento, non una regola che passa a una linea nuova.
- **Previsioni registrate:**

  | Previsione | Atteso | Esito |
  |---|---|---|
  | `adapter − k562` (R) | da 0,00 a +0,06 | −0,016: fuori, sotto |
  | `ridge − k562` (R) | da −0,01 a +0,04 | −0,033: fuori, sotto |
  | Un modello passa | fiducia 0,45 | no |
  | `adapter − adapter_swap` (R) | da −0,005 a +0,02 | −0,003: dentro |

## 4. Limiti

- La verità è rumorosa: la piega T ha 40 bersagli e un coseno di base di 0,014.
- Il contesto entra solo dal basale medio.
- Un seme.
- I `ridge` contano i NaN della verità come 0 in addestramento.

## 5. Che cosa segue (proposta, non decisa)

Il segnale sui geni U esiste, ma i modelli lo pagano sui geni M. Un braccio ibrido terrebbe la copia di K562 sui
geni M e userebbe il modello solo sui geni U, con un peso scelto in validazione. È un'idea nata **dopo** aver visto
questi numeri, quindi va registrata come r2 e provata su bersagli di test nuovi (un'altra divisione, seme 1), non su
questi.
