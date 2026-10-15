# Esito di `ta 42`: T3 e la rete centrata insieme, sul sito

15 ottobre 2026, 19:50 CEST. Claude Code per Alfredo; da leggere anche per Davide.

**Ordine delle registrazioni:**
- regola del banco nel commit `a88497a`;
- previsione del sito in `671854d`, pushata prima di generare;
- valori in [comparison.json](../../invii/prediction_ta42_2026-10-15/comparison.json) e nello
  [status](../../invii/trial_rlead_2026-10-15/status_wAUBxckeaH0Ab8bMXYaM.json).

## Risultato (misurato)

**`ta 42` = 0,159396, rango 437.** Entry `wAUBxckeaH0Ab8bMXYaM`. Il caricamento è stato interrotto da un riavvio e
ripreso sulla stessa entry ([NOTA_RIPRESA](../../invii/trial_rlead_2026-10-15/NOTA_RIPRESA.md)).

| Confronto | Δ | Lettura |
|---|---|---|
| `ta 42` − `td 38` (0,148922) | **+0,0105** | **ramo a** della regola registrata; dentro la banda −0,004…+0,012, sopra il centro previsto +0,004 |
| `ta 42` − `ta 41` | +0,0120 | |
| `ta 42` − `ta 40` | +0,0127 | |
| `ta 42` − `td 28` | +0,0146 | |

**Membri scalati:**

| Membro | `td 28` | `ta 40` | `ta 42` | `ta 42` − `ta 40` |
|---|---|---|---|---|
| PDS | 0,622 | 0,590 | **0,654** | **+0,064** (+0,0107 sulla media) |
| reach | 0,199 | 0,187 | 0,199 | +0,012 |
| nMAE | 0,049 | 0,078 | 0,083 | +0,005 |
| fedeltà | −0,007 | 0,019 | 0,014 | −0,005 |
| Jaccard | 0,006 | 0,007 | 0,007 | +0,001 |
| MSE | 0 | 0 | 0 | 0 |

**Coseno PDS grezzo:** 0,7955 per `ta 42`, 0,7814 per `td 28`, 0,7666 per `ta 40`. È il valore più alto mai misurato dal
team.

I membri di `td 38` non sono su GitHub: il confronto per membro è con `ta 40` e `td 28`.

## Che cosa si capisce (interpretazione)

1. **Combinare i predittori dei due autori è la leva più grande trovata finora,** e quasi tutto il guadagno è
   discriminazione fra bersagli (PDS). `ta 40` e T3 avevano punteggi vicini e direzioni a coseno 0,48: errori in parte
   indipendenti, che la media cancella.
2. **Il banco sui fold ha visto la direzione giusta, ma non la misura:** prevedeva +0,012 di indice PDS, il sito ha
   dato +0,064 di PDS scalato su `ta 40`. È la prima volta che un cambio di direzione supera sul sito la stima del
   banco, invece di restarne sotto.
3. **I membri DE restano dove erano:** la miscela non cambia le magnitudini (norma di T3).

## Proposte (non eseguite)

- **Per la finale (D, E, F dal 22/10):** costruire il candidato come miscela dei predittori dei due autori, e non come
  un singolo modello.
- **Da esplorare, una variabile alla volta e con regola registrata:**
  - il peso della miscela (sul banco 0,5 aveva più coseno, 0,7 più PDS);
  - aggiungere un terzo predittore poco correlato (`td 41` "RS" ha coseno 0,51 con T3 e 0,22 con `ta 40`; il suo
    punteggio non è noto da qui).
