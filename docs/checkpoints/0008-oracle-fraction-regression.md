# CP-0008 — Oracolo 0.2.0: frazioni esatte e tre regressioni della revisione

- **Data:** 2026-09-13
- **Tipo:** correzione
- **Redatto da:** agente (Grok 4.6)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

I tre problemi riprodotti sulla versione 0.1.0 — uguaglianza esatta fra
medie decimali arrotondate, intestazioni CSV duplicate accettate,
overflow non gestito — restano dopo il passaggio a frazioni esatte e
ai limiti di dimensione?

## 2. Cosa è stato fatto

Contratto portato a 0.2.0 (`docs/oracle/CONTRATTO.md`). Calcolo e
confronti su `fractions.Fraction`. Arrotondamento decimale del report
separato (half-even, max 18 cifre, solo visualizzazione). Limiti
applicati **prima** di costruire il valore: 80 caratteri, esponente
±24, 24 cifre significative. Intestazioni duplicate rifiutate.

I tre input della revisione, usati così com'erano:

```
case_id,loss_a,loss_b
c1,1,2
c2,0,0
c3,0,0
```

```
case_id,loss_a,loss_b,loss_a
c1,0.20,0.30,0.99
c2,0.40,0.35,0.99
c3,0.30,0.40,0.99
```

```
case_id,loss_a,loss_b
c1,1e1000000,0
```

```
.\scripts\py.cmd -m unittest tests.test_oracle_pairwise_loss -v
```

Nessuna modifica a `src/orchestrator/`. Il report
`reports/oracle/example_pass.json` della 0.1.0 non è stato
sovrascritto.

## 3. Cosa si è osservato

**Misura, 0.1.0, prima della correzione.** Sugli stessi tre input:

- `c1,1,2` / `c2,0,0` / `c3,0,0` → `recompute` in `error`:
  `mean(loss_a-loss_b)=-0.333…3333` diverso da
  `mean_a-mean_b=-0.333…3334`.
- intestazione `loss_a` duplicata → `csv_readable` in `pass`,
  media di A ricalcolata `0.99` (ultima colonna).
- `1e1000000` → eccezione `decimal.Overflow`, non un esito
  `error`.

**Misura, 0.2.0.** `tests.test_oracle_pairwise_loss`: 34 test, tutti
ok, 0,138 s. I tre test `ReviewRegression` usano gli input sopra.

- medie 1/3, 2/3, −1/3 esatte; `recompute` in `pass`; verdetto
  `pass` sul candidato con i float JSON della revisione.
- intestazioni duplicate → `csv_readable` in `error`; nessun
  ricalcolo.
- `1e1000000` → `finite_values` in `error` (esponente); nessuna
  eccezione.

**Calcolo a mano, indipendente dal verificatore.**
`(1+0+0)/3 = 1/3`, `(2+0+0)/3 = 2/3`, `1/3 − 2/3 = −1/3`.

**Non misurato.** Loss reali della gara. Chiamata dall'orchestratore.

## 4. Interpretazione e incertezza

**Interpretazione.** L'uguaglianza che falliva era un artefatto di
`Decimal` a precisione finita, non una proprietà delle medie. Le
frazioni la rendono identità. I limiti di dimensione impediscono di
costruire il valore che faceva scattare l'overflow.

**Non segue.** Che ogni overflow possibile sia coperto: i limiti
riguardano token ed esponente, non ogni allocazione del runtime.

## 5. Spiegazione semplice

Prima i conti si facevano con decimali arrotondati: un terzo meno
due terzi poteva non dare meno un terzo, una colonna ripetuta
veniva letta in silenzio, e un esponente enorme faceva saltare il
programma. Ora i conti sono frazioni; l'arrotondamento serve solo a
scrivere il report; i numeri troppo grandi si rifiutano prima di
esistere.

## 6. Conseguenze

Il verificatore è 0.2.0. D-020 resta: l'oracolo è autonomo e il
candidato non è fidato. La riga "aritmetica decimale" in D-020 è
stata aggiornata a frazioni esatte.

## 7. Cosa corregge

I tre difetti della 0.1.0, non coperti dai 31 test di
[CP-0007](0007-oracle-pairwise-loss.md). CP-0007 non si riscrive:
le sue misure sull'esempio a tre decimi restano vere per quella
versione. Il report `reports/oracle/example_pass.json` documenta
ancora la 0.1.0.

## 8. Domanda di comprensione

Perché `1e1000000` deve essere rifiutato **prima** di costruire una
`Fraction`, e non dopo averla usata per scrivere il report?
