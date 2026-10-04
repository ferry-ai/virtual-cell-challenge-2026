# Adattatore di contesto r3: esito secondo la regola registrata

4 ottobre 2026, corsa fra 15:37 e 15:39, ora del PC. Protocollo: [PROTOCOLLO_R3.md](PROTOCOLLO_R3.md), commit b1905d8.
Codice: [adattatore_r3.py](adattatore_r3.py), commit 644a31f. Entrambi prima della corsa. Il `result.json` e gli sha256
dei checkpoint sono in [esito_r3/](esito_r3/). **Sono coseni di un banco locale, non punteggi VCC.**

## 1. Esito

| Regola | Esito |
|---|---|
| Cancello tecnico | **passa:** da 50 a 530 bersagli di test per piega; nessun NaN. In tre pieghe su cinque (H1, HepG2, Jurkat) l'arresto non trova un passo migliore della copia nel gruppo interno, quindi quelle pieghe usano la copia (guadagno 0) |
| Macro `adapter3 − k562` ≥ +0,01 con IC sopra 0 | **no:** +0,0027 [+0,0008; +0,0045] |
| Almeno 3 pieghe positive su 5 | **no:** 1 su 5 (RPE1) |
| Discriminazione non sotto −0,01 | **no:** macro −0,053 |
| **Passa** | **no.** Fase 2 non eseguita. La strada dell'adattatore a livello di effetti **si chiude** |

## 2. Numeri per piega

| Piega (bersagli di test) | Passo scelto | Coseno `k562` | Coseno `adapter3` | Differenza [IC 95%] | Discriminazione `k562` → `adapter3` | Quota comune prima della centratura |
|---|---|---|---|---|---|---|
| H1 (50) | 0 (copia) | 0,169 | 0,169 | 0 | 0,961 → 0,961 | — |
| KOLF (356) | 500 | 0,042 | 0,026 | **−0,015 [−0,020; −0,010]** | 0,841 → **0,647** | 0,007–0,069 |
| RPE1 (530) | 500 | 0,108 | 0,136 | **+0,028 [+0,021; +0,036]** | 0,882 → **0,809** | 0,024 |
| HepG2 (530) | 0 (copia) | 0,101 | 0,101 | 0 | 0,911 → 0,911 | — |
| Jurkat (530) | 0 (copia) | 0,147 | 0,147 | 0 | 0,930 → 0,930 | — |

- **Gruppo interno (arresto anticipato):**
  - nella piega KOLF, il coseno interno su RPE1 sale da 0,106 a 0,273, mentre KOLF scende;
  - nella piega RPE1, l'interno HepG2 sale da 0,101 a 0,117.
- **Bersagli del pannello fra quelli di test (descrittivo):** KOLF 15 bersagli, da 0,041 a 0,033; H1 3 bersagli,
  invariato.
- **`adapter3 − adapter3_swap` (macro):** −0,0002.

## 3. Lettura

- **Misurato:** il modello impara qualcosa che aiuta sugli schermi di geni essenziali (RPE1 +0,028; l'interno HepG2 o
  RPE1 sale), ma peggiora le linee pluripotenti (KOLF −0,015) e non aiuta H1.
- **Misurato:** dove cambia qualcosa, la discriminazione fra bersagli scende molto (KOLF −0,19, RPE1 −0,07).
- **Misurato:** la quota comune della correzione è bassa (≤ 0,07), quindi il vincolo di media zero non è stato
  stringente. La perdita di discriminazione non viene dalla media sui bersagli, ma da una risposta condivisa a bassa
  dimensione.
- **Misurato:** il contesto letto dal basale non conta (`adapter3 ≈ adapter3_swap`).
- **Interpretazione:** la correzione appresa avvicina i bersagli fra loro. Insegue la risposta generica degli schermi
  di geni essenziali (comune a K562, RPE1, HepG2 e Jurkat) a spese di ciò che distingue un bersaglio dall'altro. È lo
  stesso modo di sbagliare del denoiser (discriminazione −0,056) e, per altra via, del PDS del t30 di Davide
  (−0,042). I bersagli ufficiali non sono essenziali, quindi questa risposta generica non li riguarda.
- **Previsioni registrate:**

  | Previsione | Atteso | Esito |
  |---|---|---|
  | Macro `adapter3 − k562` | da −0,005 a +0,03, centro +0,008 | +0,0027: dentro |
  | Passa | fiducia 0,35 | no |
  | Pieghe positive | 2–4 su 5 | 1: fuori |
  | Quota comune sulle linee di test | da 0,1 a 0,4 | 0,007–0,069: fuori, sotto |
  | `adapter3 − adapter3_swap` | da −0,005 a +0,01 | −0,0002: dentro |

## 4. Che cosa resta

- **Interpretazione:** tutti i modelli appresi a livello di effetti provati qui hanno barattato specificità per
  bersaglio contro segnale generico: r1, r2, il denoiser e la r3. La perdita usata (coseno più errore relativo)
  premia questo baratto, perché la risposta generica è la parte più prevedibile della verità.
- **Proposta, non decisa e da registrare a parte:** una perdita che premi esplicitamente la discriminazione, cioè
  contrastiva come il PDS. Il bersaglio previsto deve stare più vicino al proprio vero che ai veri degli altri
  bersagli della stessa linea.
