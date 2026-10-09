# Livello B per il fallback ESM2: quattro bracci sui due fold con cellule vere

9 ottobre 2026, VALIDAZIONE (Claude Code `eace4d03`). **Scritto prima che esista un numero a sei membri per un
braccio ESM2**: nessun banco di questo tipo è stato lanciato da nessun incarico (lettura delle 21:35). Non cambia
il §8 del [contratto v1](../validazione_indipendente_8a8ca58a_2026-10-08/PROTOCOLLO_v1.md) né
[LIVELLO_B.md](../validazione_indipendente_8a8ca58a_2026-10-08/LIVELLO_B.md): fissa bracci, coppie e parole per
questo confronto. **Non è lanciato:** attende la decisione del proprietario su esecutore e trasferimento dei file.

## Che cosa si esegue

Come i banchi a sei membri dell'8 ottobre: `bench_v2.py` senza modifiche, emissione t28, 400 cellule previste per
bersaglio, scorer `cell-eval2` 0.16.0, metà verità e metà replicato al seme 2026, cinque semi del generatore
(20260912, indici 0–4), un flusso casuale per (seme, bersaglio) condiviso fra i bracci.

| Fold | Cellule vere | Bersagli |
|---|---|---:|
| C-K562 | estrazione `davidmaisterx/vcc-validazione-celle-k562-8a8ca58a-r1` | 272 |
| C-iPSC | estrazione `davidmaisterx/vcc-validazione-celle-ipsc-8a8ca58a-r1` (libreria `strong`) | 55 |

**Bracci**, tutti nel formato dello stadio 100, verificati per sha256 nel runtime:

| Braccio | Che cos'è | Da dove viene |
|---|---|---|
| `T0` | il transfer del fold; le coppie non previste restano zero | livello A, già sul conto del banco |
| `E2f` | il fallback consegnato da MODELLI-ESTERNI, byte per byte | `esm2_closure_conversion_r1.json` |
| `E2gen` | le stesse coppie riempite con la parte generica del ridge, stessa ampiezza | [costruisci_bracci.py](esm2/costruisci_bracci.py) |
| `E2swap` | le stesse coppie riempite con il ridge di un altro bersaglio, stessa ampiezza, stessa permutazione dell'audit | idem |

I tre bracci riempiti hanno **una sola maschera** e i valori che il livello A ha già letto
([C-K562](esm2/bracci_C-K562_r1.json), [C-iPSC](esm2/bracci_C-iPSC_r1.json): dimensioni e sha256).

**Corse per fold:** *controllo*, T0 contro T0 a righe scambiate, un seme: il PDS locale deve cadere, altrimenti il
fold è invalido; *intero*, i quattro bracci, cinque semi, coppie `E2f:T0`, `E2gen:T0`, `E2swap:T0`, `E2f:E2swap`,
`E2f:E2gen`. Si riportano i sei membri grezzi e scalati locali con i denominatori, la media dei sei e dei cinque
senza JAC, i delta appaiati per seme, ogni fold e la macro a peso uguale. «Risolto» = |media| > 2·sd/√5.

## Come si legge

- **Esito del §8 per il candidato `E2f` contro `T0`** (contrasto K3): favorevole, sfavorevole o inconcludente con
  la regola com'è scritta. La lettera (c) è già soddisfatta: `disc95` non ha regressioni risolte.
- **Parole fissate ora, in più:**

| Affermazione | Si scrive solo se |
|---|---|
| «riempire aiuta i sei membri» | `E2f:T0` risolto positivo sulla media dei sei in almeno un fold e non risolto negativo nell'altro |
| «aiuta perché conosce il bersaglio» | in più, `E2f:E2swap` risolto positivo sulla media dei sei o sul PDS in almeno un fold |
| «è un effetto di copertura» | `E2f:T0` ed `E2swap:T0` risolti nello stesso verso ed `E2f:E2swap` non risolto |
| «riempire costa» | `E2f:T0` risolto negativo sulla media dei sei o sul PDS in un fold |

Se l'effetto è di copertura, il candidato non è il ridge ma un riempimento generico: avrebbe bisogno di un suo
protocollo, e non si promuove da qui. I numeri sono locali, su ancore locali e verità a metà profondità: danno il
verso, non l'entità (CP-0052).

## Limiti dichiarati

Due lignaggi di sviluppo. Su C-K562 le cellule vere misurano 7.679 geni: come per la tabella di verità, gran
parte delle coppie riempite cade su geni non misurati e non può contare. Su C-iPSC i bersagli sono 55. Un seme di
training del ridge: la variabilità del fit non è misurata. Il JAC locale ha denominatori piccoli: si legge anche la
media senza JAC.

## Precedenti

- **S-015**: il livello A non poteva giudicare il riempimento con la misura primaria e, dove lo vede, trova
  copertura senza specificità; questo banco è la condizione di riapertura scritta lì.
- **S-009**: il candidato valutato è esattamente il file consegnato (`E2f`, stesso sha256), con l'emissione della
  consegna; i due bracci di controllo hanno la stessa maschera e la stessa ampiezza.
- **S-006**, **S-013**: una parte comune può migliorare i membri d'ampiezza e di segno; per questo il confronto
  decisivo è con il braccio scambiato, non con T0.
- CP-0065: cinque semi e 400 cellule, guadagno appaiato; una differenza conta se risolta.

**Segnale precoce e arresto:** se il controllo non abbassa il PDS locale il fold non si legge. Se un file non ha lo
sha256 atteso nel runtime il kernel si ferma prima di generare. Se `E2f:T0` è risolto negativo sul PDS già nel
fold C-iPSC, che finisce per primo, lo si scrive subito a MODELLI-ESTERNI senza attendere C-K562.
