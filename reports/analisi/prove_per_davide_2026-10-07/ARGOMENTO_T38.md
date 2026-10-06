# t38: perché è stato inviato così e che cosa decide (scritto prima del punteggio)

7 ottobre 2026, circa 02:00 CEST. Claude Code per Alfredo, che ha chiesto di scegliere la forma più utile del t38 e di
argomentarla anche per Davide. Il t38 è caricato (entry `5GhXxaCDRuPnHv4UwU8S`, data di invio 23:37:39 UTC del 6/10,
md5 verificato) e il punteggio non è ancora noto.

## Che cosa è il t38

È il t36 con un solo cambio: `--effects-scale` da 1,5 a 1,0. Restano uguali tutte le altre cose:
- gli effetti: `effects_t36_2026-10-06`, stessi sha256;
- la dispersione per gene accesa a 1,0;
- il seme 20260912;
- lo stadio 48.

La differenza t38 − t36 misura quindi **solo l'ampiezza**, sul sito.

**Registrazioni fatte prima del punteggio:**
- la regola ([prediction.json](../../invii/prediction_t38_2026-10-07/prediction.json));
- l'addendum con la prova contraria ([ADDENDUM_REVISIONE.md](../../invii/prediction_t38_2026-10-07/ADDENDUM_REVISIONE.md));
- il lettore ([leggi_t38.py](../../invii/prediction_t38_2026-10-07/leggi_t38.py)).

## Perché proprio l'ampiezza (argomento)

- **È il parametro dell'emissione che il candidato finale eredita.** Qualunque base userai per D, E, F (la banca
  estesa compresa), lo stadio 45 la moltiplica per l'ampiezza del t28, cioè 1,5.
- **Quel valore è stato scelto sul banco, non sul sito.** La griglia del 29/09
  ([selection.json](../../analisi/lead_scientist_2026-09-29/generator_development_r3/development/selection.json)) usa
  HepG2, la sorgente K562, 48 bersagli e un seme. Sul sito, il cambio intero del t28 (ampiezza e dispersione
  insieme) ha reso circa un sesto del banco: +0,0046 contro +0,0289.
- **Il banco ha già sbagliato due volte sul sito:** con R sopra `prod` (t30) e con la base `all` più R (t36). Una
  misura diretta dell'ampiezza sul sito vale più di un'altra prova sul banco.
- **La perdita di nMAE è più forte sul sito che sul banco** (−0,0115 contro −0,0075 sulla media, per lo stesso
  cambio del t28). Se è l'ampiezza a pagarla, l'ottimo sul sito potrebbe stare sotto 1,5.
- **1,0 e non 1,25:** il segnale atteso è più grande e si separa meglio dal rumore del seme (circa 0,0016, una sola
  coppia t22/t24).

## Che cosa è stato scartato e perché

| Alternativa | Motivo |
|---|---|
| t37 (`all` senza R, emissione t28) | già misurato, secondo Alfredo |
| `--depth-bins` | lo stadio 45 non lo accetta insieme a `--gene-dispersion`; sul banco guadagna solo ad ampiezza 1,0 senza dispersione (+0,011), quasi nulla a 2,0 (+0,0015) |
| dispersione per gene sopra 1,0 | sul banco il guadagno sale fino a 1,0 ma si appiattisce; sul sito, al rapporto di un sesto, varrebbe meno di 0,001 |
| ampiezza 2,0 | sul banco perde 0,016 rispetto a 1,5 (a dispersione 1,0) |

## Che cosa decide ogni esito (regola registrata, soglia ±0,005 contro il t36)

| Ramo | Esito | Per la banca estesa |
|---|---|---|
| a | t38 − t36 ≥ +0,005 | ampiezza 1,0 con dispersione: il banco sopravvaluta anche l'ampiezza |
| b | \|t38 − t36\| < 0,005 | resta l'emissione del t28; fra 1,0 e 1,5 il sito non distingue con un seme |
| c | t38 − t36 ≤ −0,005 | resta 1,5: sull'ampiezza la direzione del banco regge sul sito |

**Stima prima del punteggio:** il banco dà +0,023 a favore di 1,5. Al rapporto di un sesto sono circa **−0,004** per
il t38, cioè ramo b vicino al c. È una stima, non un valore registrato nella regola.

## Che cosa aggiungere quando c'è il punteggio

Il lettore scrive `comparison.json` con i sei membri contro t36 e t28. Il commento all'esito va in un file nuovo
accanto a questo; questo non si modifica.
