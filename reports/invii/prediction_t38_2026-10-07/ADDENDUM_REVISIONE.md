# Addendum al t38: una prova contraria trovata in revisione, prima del punteggio

7 ottobre 2026, circa 01:35 CEST. È scritto prima del caricamento e prima di qualsiasi punteggio del t38. **La regola
di [prediction.json](prediction.json) non cambia.**

## Che cosa è emerso

La griglia di sviluppo del generatore del 29 settembre
([selection.json](../../analisi/lead_scientist_2026-09-29/generator_development_r3/development/selection.json)) non
era stata letta quando ho registrato il t38. Il banco usa HepG2 pubblico, la sorgente K562, 48 bersagli e un seme; è
una proiezione locale, non un punteggio VCC. Il confronto che interessa è ampiezza 1,5 contro 1,0 a dispersione 1,0
(voce `amplitude_at_fixed_dispersion`):

| Confronto locale | Δ proiettato | fedeltà | reach | nMAE | Jaccard | PDS |
|---|---|---|---|---|---|---|
| 1,5/1,0 − 1,0/1,0 | **+0,0228** | +0,0190 | +0,0037 | −0,0066 | +0,0037 | +0,0031 |
| 1,0/1,0 − 1,0/0,0 | −0,0038 | +0,0068 | +0,0029 | −0,0008 | −0,0086 | −0,0040 |

## Che cosa ne segue (interpretazione)

- **Sul banco, l'ipotesi del t38 è contraddetta:** la fedeltà la porta soprattutto l'ampiezza ×1,5, non la
  dispersione. La dispersione da sola, ad ampiezza 1,0, perde.
- **Stima per il sito:** il rapporto sito/banco del t28 era 0,0046 / 0,0289 ≈ 0,16. Applicato qui dà
  t38 − t36 ≈ **−0,004**, cioè ramo b, vicino al ramo c.
- **Il t38 resta una misura utile:** il banco ha già sbagliato sul sito (R nel t30, la base `all` nel t36), e per lo
  stesso cambio del t28 (1,0/0,0 → 1,5/1,0) la perdita di nMAE sul sito è stata più grande che sul banco (−0,0115
  contro −0,0075 sulla media).
- **La griglia non dice nulla** sui generatori `bins` con dispersione o ad ampiezza 1,5: quelle combinazioni non sono
  state provate.
