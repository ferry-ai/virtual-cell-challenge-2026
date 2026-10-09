# t38: esito e commento per Davide

9 ottobre 2026. Lettura col lettore registrato prima del punteggio
([comparison.json](../../invii/prediction_t38_2026-10-07/comparison.json)); il ragionamento scritto prima è in
[ARGOMENTO_T38.md](ARGOMENTO_T38.md).

## Risultato (misurato)

**t38 = 0,131078, rango 555.** È entrato in tempo: data di invio 23:37:39 UTC del 6/10, entry `5GhXxaCDRuPnHv4UwU8S`.

- **t38 − t36 = −0,0103:** ramo **c** della regola (≤ −0,005). È dentro la banda registrata (−0,012…+0,015), vicino
  al bordo basso, e oltre la stima dell'addendum (−0,004).
- **t38 − t28 = −0,0138.**

| Membro scalato | t36 (ampiezza 1,5) | t38 (ampiezza 1,0) | Δ | Peso sulla media |
|---|---|---|---|---|
| fedeltà | −0,006 | −0,089 | −0,083 | **−0,0139** |
| reach | 0,185 | 0,166 | −0,019 | −0,0031 |
| Jaccard | 0,004 | −0,001 | −0,005 | −0,0008 |
| PDS | 0,591 | 0,590 | −0,002 | −0,0003 |
| nMAE | 0,074 | 0,120 | +0,046 | **+0,0077** |
| MSE | 0 | 0 | 0 | 0 |

**Grezzi:**
- nMAE: 0,954 → 0,927;
- fedeltà: 0,511 → 0,486;
- reach: 0,243 → 0,227;
- MSE grezza: 5,20 → 2,77, ma la scalata resta 0;
- coseno PDS invariato (0,767).

## Commento (interpretazione)

1. **L'ampiezza 1,5 resta.** Sul sito l'ampiezza fa quello che diceva il banco: alzarla compra fedeltà e reach e
   paga in nMAE, e il saldo è a favore di 1,5. La fedeltà da sola pesa quasi il doppio di quello che l'nMAE restituisce.
2. **Il banco qui è stato prudente, non ottimista.** Sull'ampiezza il sito ha reso circa 0,45 del banco
   (0,0103 su 0,0228), contro circa 0,16 per il cambio intero del t28. Il rapporto sito/banco non è una costante:
   va misurato per tipo di cambio.
3. **La mia ipotesi registrata era sbagliata.** Fedeltà e reach del t28 venivano dall'ampiezza, non dalla
   dispersione. L'avevo registrata senza aver letto la griglia del 29/09; l'addendum, scritto prima del punteggio,
   aveva il segno giusto.
4. **Il PDS non dipende dall'ampiezza** (−0,0015 scalato): la direzione resta il limite, come previsto.
5. **La MSE grezza scende molto (5,2 → 2,8) senza uscire da zero.** Conferma che sulla MSE l'ampiezza non basta:
   all'ampiezza ottima la grezza vale 1 − c², e serve un coseno più alto.

## Che cosa cambia per la banca estesa

- **Emissione:** quella del t28 (`--effects-scale 1.5 --gene-dispersion --gene-dispersion-scale 1.0`), ora
  sostenuta sul sito e non solo sul banco.
- **Non scendere sotto 1,5** per guadagnare nMAE: costa più fedeltà di quanta nMAE restituisca.
- **Ipotesi da non provare alla cieca:** salire sopra 1,5. Il banco dava 2,0 peggio di 1,5 di 0,016, ma su questo
  cambio il banco si è rivelato prudente. Se si prova, va registrato come esplorativo, con la stessa base e lo
  stesso seme.
- **R:** con t30 e t36 è il secondo invio in cui R non aiuta il PDS. Se lo 0,1472 è davvero la base senza R,
  togliere R è la scelta coerente coi numeri del sito.

**Non dice:** nulla su D, E, F; un solo seme per lato (rumore fra semi circa 0,0016, una sola coppia).
