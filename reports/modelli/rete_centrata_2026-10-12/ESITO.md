# Esito di `ta 40`: la rete centrata sul sito

12 ottobre 2026, 23:20 CEST. Claude Code per Alfredo; da leggere anche per Davide.

**Ordine delle registrazioni:**
- previsione e regola nel commit `351cfce`, prima di generare;
- push alle 23:07 CEST, prima del punteggio.

**Valori:**
- [comparison.json](../../invii/prediction_ta40_2026-10-12/comparison.json), scritto dal lettore registrato;
- [status](../../invii/trial_rlead_2026-10-12/status_D4DVVnBo4I3xn2aU59eN.json).

## Risultato (misurato)

**`ta 40` = 0,146722, rango 533.** Entry `D4DVVnBo4I3xn2aU59eN`, caricata fra le 20:51 e le 21:07 UTC del 12/10.

| Confronto | Δ | Lettura |
|---|---|---|
| `ta 40` − `ta 39` | **+0,0059** | **ramo a** della regola registrata; dentro la banda −0,006…+0,012 (centro previsto +0,003) |
| `ta 40` − `td 28` | +0,0019 | non registrato |
| `ta 40` − `ta 36` | +0,0053 | non registrato |
| `ta 40` − `td 38` (0,148922) | −0,0022 | non registrato; `td 38` resta il riferimento del team |

**Membri scalati:**

| Membro | `td 28` | `ta 36` | `ta 39` | `ta 40` | `ta 40` − `ta 39` |
|---|---|---|---|---|---|
| PDS | 0,622 | 0,591 | 0,568 | **0,590** | **+0,022** |
| nMAE | 0,049 | 0,074 | 0,076 | 0,078 | +0,002 |
| fedeltà | −0,007 | −0,006 | 0,013 | **0,019** | +0,006 |
| reach | 0,199 | 0,185 | 0,181 | 0,187 | +0,005 |
| Jaccard | 0,006 | 0,004 | 0,006 | 0,007 | +0,000 |
| MSE | 0 | 0 | 0 | 0 | 0 |

**Lettura:**
- Rispetto a `ta 39` nessun membro scende.
- Il PDS sale come previsto, e la previsione di segno (probabilità 0,65) è verificata.
- Il coseno PDS grezzo è 0,767, come in `ta 36`; `ta 39` era a 0,757 e `td 28` a 0,781.

**La parte comune nelle previsioni** (quota dell'energia dei bersagli coperti, A/B/C; calcolata il 12/10 sui file
degli effetti):

| Effetti | Parte comune |
|---|---|
| `all` | 0,012 / 0,012 / 0,012 |
| rete del `ta 39` | 0,134 / 0,074 / 0,073 |
| rete centrata del `ta 40` | 0,011 / 0,011 / 0,011 |

Il residuo della rete aveva il 32% della sua energia in comune su A e il 17% su B e C
([export_centrata.json](export_centrata.json)).

## Che cosa si capisce (interpretazione)

1. **L'ipotesi della risposta comune regge sul sito.** Togliere al residuo la sua parte comune, e soltanto quella,
   restituisce tutto il PDS perso dal `ta 39` rispetto a `ta 36`. Tiene anche i guadagni della rete sui membri DE:
   - fedeltà: +0,025 su `ta 36` e +0,026 su `td 28`;
   - nMAE: +0,029 su `td 28`.
2. **È il miglior invio di Alfredo,** il primo che batte `td 28`. Resta sotto `td 38` (0,1489) e `td 36` (0,1472),
   che usano la banca estesa di Davide.
3. **Quello che resta fra `ta 40` e `td 28` è il PDS** (−0,032 scalato), cioè la base: cubo `all` contro la base del
   `td 28`. Non lo spiega la rete.
4. **Il banco del cubo, da solo, non prevedeva questo esito:** sul cubo il centramento toglieva coseno. La misura
   decisiva è la parte comune delle previsioni confrontata con quella del sito (circa 1%). Da qui in avanti va
   controllata prima di ogni invio.

## Proposte (non eseguite)

- **Per Davide:** la stessa rete, centrata, sopra la banca estesa di `td 38`. Le due leve sono diverse:
  - più linee sorgente migliorano la base e il PDS;
  - il residuo centrato migliora i membri DE.

  Che si sommino è un'**ipotesi**; il tetto plausibile è circa 0,152–0,155. Va registrata prima.
- **Test pulito della rete contro la sua base:** `ta 37` (cubo `all` senza R, la stessa emissione) è pronto in
  `artifacts/allt28pack_r2`. `ta 40` − `ta 37` misura quanto vale la rete centrata rispetto alla sua stessa base.
  Serve il via di Alfredo e una quota.
- **Regola pratica per i prossimi candidati:** la parte comune delle previsioni sul pannello deve stare vicino all'1%,
  come nel sito.
