# Ablazione della parte JEPA della rete ponte

10 ottobre 2026. Claude Code per Alfredo, che ha chiesto in chat «fai l'ablazione del JEPA sul banco».
**Registrato prima di ogni numero di questa ablazione.**

## Domanda

La perdita JEPA (predizione nel latente con stop-gradient, più SIGReg di LeJEPA come anti-collasso) contribuisce al
guadagno della rete sul banco del cubo, o è decorativa?

## Bracci

Stesso codice, dati, banco e misure di r3/r4. Ogni braccio è l'insieme di 10 reti (semi 2–11, gli stessi in tutti i
bracci, come nel t39).

| Braccio | W_JEPA | LAMBDA_SIG | Che cosa toglie o cambia |
|---|---|---|---|
| `ref` | 0,1 | 0,05 | niente: la configurazione di r3/r4/t39 |
| `nojepa` | 0 | — | tutta la parte JEPA |
| `nosig` | 0,1 | 0 | solo SIGReg: predizione latente senza anti-collasso |
| `jepa03` | 0,3 | 0,05 | la parte JEPA pesata il triplo |

## Misure e confronto

- **Per ogni linea tenuta fuori** (H1, HepG2, RPE1, Jurkat, K562): coseno e indice PDS del braccio `rete` per
  bersaglio.
- **Differenze appaiate sui bersagli** (`ref − nojepa`, `ref − nosig`, `jepa03 − ref`), con bootstrap a 2.000
  ricampionamenti e IC 90% ([confronta_ablazione.py](confronta_ablazione.py)).

## Regola

**La parte JEPA serve** se `ref − nojepa` soddisfa tutte e tre:
1. coseno medio sulle 5 linee ≥ **+0,005**;
2. almeno 3 linee col limite inferiore dell'IC 90% del coseno sopra 0;
3. PDS medio ≥ −0,005.

Altrimenti la parte JEPA non contribuisce in modo misurabile su questo banco, e il guadagno è del resto della rete
(attenzione, residuo, coseno, InfoNCE e media dei semi).

`nosig` e `jepa03` si riportano senza che decidano.

## Previsione (soggettiva)

| Grandezza | Previsione |
|---|---|
| `ref − nojepa`, coseno | fra −0,005 e +0,010, centro +0,002 |
| Probabilità che la parte JEPA «serva» secondo la regola | 0,25 |

Il peso 0,1 è piccolo rispetto al coseno e all'InfoNCE, e l'encoder riceve già gradiente dall'uscita.

**Limite:** è il banco del cubo, che sul t39 ha sovrastimato il sito.
