# Esito di `ta 43` (peso 0,5) e che cosa ci dice sul banco

16 ottobre 2026, 01:25 CEST. Claude Code per Alfredo.

**Ordine delle registrazioni:**
- previsione nel commit `3f7d749`, pushata prima di generare;
- valori in [comparison.json](../../invii/prediction_ta43_2026-10-16/comparison.json) e nello
  [status](../../invii/trial_rlead_2026-10-16/status_6OQa2pNmeeXgUznSYVbT.json).

## Risultato (misurato)

**`ta 43` = 0,158746, rango 446.** Entry `6OQa2pNmeeXgUznSYVbT`.
- `ta 43` − `ta 42` = **−0,0006**: ramo b, non conclusivo.
- Il segno vota debolmente per il banco, che preferiva 0,7, e contro la parabola del sito, che dava 0,52.
- Rispetto a `td 38`: +0,0098.

**Membri scalati, `ta 43` − `ta 42`:**

| Membro | Δ |
|---|---|
| PDS | **−0,013** |
| reach | +0,008 |
| fedeltà | +0,006 |
| Jaccard | +0,001 |
| nMAE | −0,005 |
| MSE | 0 |

**La curva del peso sul sito** (peso di T3; il punto a 0 è `ta 40`, a norma più bassa):

| Peso | Punteggio |
|---|---|
| 0 | 0,1467 |
| 0,5 | 0,1587 |
| 0,7 | 0,1594 |
| 1 | 0,1489 |

**Parabola per i tre punti alla stessa norma** (0,5, 0,7, 1): massimo a peso **0,62**, valore 0,1599, cioè +0,0005 su
`ta 42`. **La cima è piatta fra 0,5 e 0,7.**

## Banco e sito sulle due variazioni di peso (interpretazione)

**Conversioni:** il grezzo del sito vale metà dell'indice del banco, e lo scalato è il grezzo diviso 0,447.

| Variazione | Banco: indice PDS | Banco, convertito in scalato | Sito: PDS scalato | Rapporto sito / banco |
|---|---|---|---|---|
| `ens_0.7` contro T3 (`ta 42` contro `td 38`) | +0,012 | +0,013 | circa +0,06 (se tutto PDS) | circa 5 |
| `ens_0.5` contro `ens_0.7` (`ta 43` contro `ta 42`) | −0,0064 | −0,007 | −0,013 | circa 2 |

1. **Il banco prende il segno giusto** sulle miscele, due casi su due, e **sottostima l'ampiezza** del PDS sul sito
   di 2–5 volte. Va letto come un indicatore prudente di direzione, non come una stima della misura.
2. **Sui membri DE il banco è tarato anche qui:** la fedeltà grezza del sito è salita di +0,0017, il banco prevedeva
   +0,0016.
3. **La parabola tracciata con un punto a norma diversa** (`ta 40`) aveva spostato l'ottimo verso la rete: l'errore
   era previsto nella registrazione, ma nel verso opposto a quello atteso. Alla stessa norma l'ottimo sta a 0,62.
4. **Che cosa ha funzionato bene:** mescolare due predittori di qualità simile e poco correlati. Il peso, una volta
   vicino all'ottimo, non è più una leva (±0,001).
