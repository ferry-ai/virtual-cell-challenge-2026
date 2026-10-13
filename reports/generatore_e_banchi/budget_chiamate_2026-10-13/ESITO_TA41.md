# Esito di `ta 41`: il tetto sulle magnitudini, sul sito

14 ottobre 2026, 01:40 CEST. Claude Code per Alfredo; da leggere anche per Davide.

**Ordine delle registrazioni:**
- previsione e regola nel commit `09938cb`, pushato prima di generare;
- valori in [comparison.json](../../invii/prediction_ta41_2026-10-13/comparison.json) e nello
  [status](../../invii/trial_rlead_2026-10-13/status_gktdLzGUa0o0fq5G3HG0.json).

## Risultato (misurato)

**`ta 41` = 0,147376, rango 535.** Entry `gktdLzGUa0o0fq5G3HG0`, caricata fra le 22:11 e le 23:25 UTC del 13/10.

| Confronto | Δ | Lettura |
|---|---|---|
| `ta 41` − `ta 40` | **+0,0007** | **ramo b**, non conclusivo; dentro la banda −0,004…+0,006 (centro previsto +0,002) |
| `ta 41` − `td 38` (0,148922) | −0,0015 | non registrato |

**Membri scalati, `ta 41` − `ta 40`, contro la previsione del banco:**

| Membro | Banco (previsto) | Sito |
|---|---|---|
| nMAE | +0,021 | **+0,019** |
| PDS | −0,012 | **−0,010** |
| fedeltà | 0 | −0,002 |
| reach | circa 0 | −0,002 |
| Jaccard | 0 | −0,000 |
| MSE | 0 | 0 |

## Che cosa si capisce (interpretazione)

1. **Il banco del cubo è tarato per le magnitudini.** Sul sito i due membri che il tetto muove si sono spostati
   come previsto, per segno e per entità (nMAE +0,019 contro +0,021, PDS −0,010 contro −0,012). È la seconda
   conferma, dopo l'ampiezza 1,0 → 1,5 (nMAE +0,027 sul sito contro +0,026 sul banco).
   - **Vale per le magnitudini.** Per la direzione e il PDS il banco ha sopravvalutato il sito in cinque casi su
     cinque.
   - **Da qui in poi** le scelte d'emissione per D, E, F si possono decidere sul banco, senza spendere quote.
2. **Il tetto è quasi neutro sul totale** (+0,0007): scambia nMAE contro PDS quasi alla pari, come previsto. È
   l'invio più alto di Alfredo, ma la differenza da `ta 40` sta nel rumore di seme.
3. **Si conferma la mappa della [README](README.md):** l'emissione è vicina al suo ottimo. Il margine grande
   (MSE e PDS delle prime dieci) richiede una direzione migliore, cioè più dati sorgente.

## Proposta (non eseguita)

**La rete centrata di `ta 40` sopra la banca estesa di `td 38`.** Sul banco, più gruppi sorgente danno un PDS più alto
in modo monotono, e la rete centrata vale circa +0,005 sulla sua base sul sito (`ta 40` − `ta 36`). Che le due leve si
sommino è un'**ipotesi**. Servono gli effetti della banca di Davide, che oggi stanno nei suoi dataset Kaggle privati.
