# Esito del terzo training su GPU (`rlab-cellnet-r3`), letto con la regola del protocollo

1 ottobre 2026, 14:40 CEST, Claude Code (sessione `07ebf08b`). Regola: [PROTOCOLLO.md](PROTOCOLLO.md) §4, fissata
alle 03:59, con lo [scostamento](SCOSTAMENTI.md) delle 07:24 (Tian 2019 fuori), entrambi precedenti al lancio.
Output in [esito/training_r3/](esito/training_r3/manifest.json), riepilogo in
[esito/training_r3/outcome.json](esito/training_r3/outcome.json). **È una verifica tecnica, non un risultato.**

Il kernel è partito alle 12:49 CEST, con budget 110 minuti per la regola del protocollo (quota restante meno margine,
avvio e ciclo), ed è finito dopo 6.263,5 s. Pre-passo r7: 6.322.833 cellule, 4.382.321 di training ammesse, HepG2
tenuto fuori.

## A. Esito tecnico, voce per voce (misurato)

| Voce | Esito | Dato |
|---|---|---|
| 1. Codice 0 | passa | `return_code` 0 |
| 2. Ciclo di ripresa su CUDA, due bracci | passa | passi 50 e 100: sequenza identica, differenza massima dei parametri 0,0 |
| 3. `verify.json` | passa | 402 shard, nessuno diverso (811 s) |
| 4. `coverage.json` | passa | 1,857 epoche, 31.808 passi; 4.382.321 cellule viste su 4.382.321; non-contaminazione passata |
| 5. `eval.json` | passa, per entrambi i bracci | completa: 225.194 cellule in 516,5 s con 3 processi; corsa intera 6.090 s su un budget di 6.600 |
| 6. Piano e log | riportati | a regime (dal passo 1.727): 1.783 cellule/s per braccio, attesa 0,59; sull'intera corsa 1.470 e 0,64 |

## B. Lettura descrittiva

| Braccio | Classe | Gruppi | Guadagno rispetto a nessun effetto | Guadagno rispetto a nessun bersaglio | Quota con guadagno specifico > 0 | Coseno della rete | Coseno del trasferimento | Coseno della perturbazione generica |
|---|---|---|---|---|---|---|---|---|
| `desc` | C | 400 | +0,0306 | +0,0019 | 0,708 | 0,303 | 0,405 | −0,076 |
| `desc` | T | 400 | +0,0050 | +0,0017 | 0,868 | 0,069 | — | 0,198 |
| `desc` | J | 206 | +0,0280 | +0,0013 | 0,718 | 0,194 | — | −0,177 |
| `ident` | C | 400 | 0,0000 | 0,0000 | 0,000 | 0,001 | 0,405 | −0,076 |
| `ident` | T | 400 | 0,0000 | 0,0000 | 0,000 | 0,000 | — | 0,198 |
| `ident` | J | 206 | 0,0000 | 0,0000 | 0,000 | 0,010 | — | −0,177 |

Le attese scritte prima del lancio:
- (i) Guadagno positivo su C e T in entrambi i bracci. Vero per `desc` (+0,0306 e +0,0050); **falso per `ident`**,
  che vale esattamente zero.
- (ii) Su J `identity` sta sotto 0,5 (0,000) e `descriptors` sopra `identity` (0,718): come previsto.
- (iii) Nessuna attesa che la rete batta il trasferimento su C: non lo batte (0,303 contro 0,405).
- (iv) Confronto descrittivo con il secondo training (più dati e più modalità, meno epoche: 1,86 contro 3,83).
  `desc` sale su C (coseno da 0,266 a 0,303, quota da 0,52 a 0,71) e su J (quota da 0,52 a 0,72, coseno da 0,108
  a 0,194).

**Il braccio `ident` è collassato.** Misurato, dal [log](esito/training_r3/train/train_log.jsonl): la quota media di
rispondenti `pi` del braccio vale 0,46 al passo 6.200, 7·10⁻⁵ al passo 9.300 e circa 10⁻¹⁰ alla fine. Da lì la
miscela coincide con il modello senza effetto, e il gradiente verso lo spostamento si annulla. È un difetto di
ottimizzazione della miscela, non una lettura biologica. Nel secondo training lo stesso braccio non era collassato.
Correzione proposta, non ancora implementata né provata: un pavimento su `pi` o una penalità che lo tenga lontano da
0, da provare su CPU prima di un nuovo training.

Con un seme e un contesto tenuto fuori nessuna di queste attese, vera o falsa, è una prova (protocollo §4).
