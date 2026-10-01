# Esito del primo training su GPU (`rlab-cellnet-r1`), letto con la regola del protocollo

1 ottobre 2026, 03:20 CEST, Claude Code (sessione `07ebf08b`). Regola: [PROTOCOLLO.md](PROTOCOLLO.md) §4, fissata
prima del lancio. Output scaricati in [esito/training_r1/](esito/training_r1/manifest.json) (solo JSON e log, con
sha256). I checkpoint e il modello restano nell'output del kernel. **È una verifica tecnica, non un risultato.**

Il kernel è partito alle 02:05 CEST ed è finito in errore dopo 3.728,6 s (circa 62 minuti di quota GPU, più
l'avvio).

## A. Esito tecnico, voce per voce (misurato)

| Voce | Esito | Dato |
|---|---|---|
| 1. Codice 0 | **non passa** | Pre-passo r3: 0. Training: `[0, 1]` (`kernel_done.json`): il braccio `ident` muore |
| 2. `resume_check.json` | passa | `cuda:0`, passi 50 e 100: sequenza dei dati identica, differenza massima dei parametri 0,0 su 75,0 |
| 3. `verify.json` dei bracci | passa | 183 shard (31,9 GB), nessuno diverso, circa 344 s per braccio, in parallelo al training |
| 4. `coverage.json` | `desc` passa, **`ident` non passa** | `desc`: 1,117 epoche, 1.066.336 cellule ammesse viste su 1.066.336, nessuna cellula di classe diversa da train estratta. `ident`: nessun file, perché il braccio muore al passo 2.800 circa |
| 5. `eval.json` | `desc` passa, **`ident` non passa** | `desc`: completa, 124.553 cellule in 1.621,5 s, fine alle 01:07:52 UTC, 3.450 s di un budget di 6.000 |
| 6. Piano e log | riportati; **il piano non rappresenta la corsa** | Piano: 3.763 cellule/s e attesa dei dati 0,025, misurati sui passi 20-80. In corsa, dal passo 100: 510-650 cellule/s, attesa 0,87-0,92. Memoria: processo 3,1 GB, caricatori 8,1 GB per braccio, GPU 1,6 GB; disponibile sulla macchina fino a 6,3 GB |

A non passa per intero. Il braccio `ident` è morto con `DataLoader worker (pid 120) is killed by signal: Killed`
([ident.log](esito/training_r1/ident.log)). La GPU ha aspettato i dati per quasi nove decimi del tempo. Tutto questo è
registrato nell'incidente `E-20261001-001` (03:18 CEST, prima di ogni nuovo lancio), nel registro
`reports/analisi/lead_scientist_2026-09-29/learning/incidents/`.

## B. Lettura descrittiva (solo il braccio `desc`)

Le misure di [eval.json](esito/training_r1/desc/eval.json): log-verosimiglianza per gene; coseni sui 200 geni con lo
spostamento osservato più grande.

| Classe | Gruppi | Guadagno rispetto a nessun effetto | Guadagno rispetto a nessun bersaglio | Quota con guadagno specifico > 0 | Coseno della rete | Coseno del trasferimento | Coseno della perturbazione generica |
|---|---|---|---|---|---|---|---|
| C | 400 | −0,00019 | −0,000038 | 0,078 | 0,080 | 0,222 (399 gruppi) | −0,054 |
| T | 400 | +0,0041 | −0,000021 | 0,338 | −0,322 | — | 0,495 |
| J | 208 | −0,00017 | −0,000046 | 0,067 | 0,185 | — | −0,111 |

Le attese scritte prima del lancio:
- (i) Guadagno rispetto a nessun effetto positivo in media su C e T in entrambi i bracci. Per `desc` è vero su T
  (+0,0041) e falso su C (−0,00019). Per `ident` non è valutabile.
- (ii) Il confronto `descriptors` contro `identity` su J non è valutabile: manca `ident`.
- (iii) Su C la rete non batte il trasferimento: coseno 0,080 contro 0,222. Nessuna attesa contraria era scritta.

Interpretazione, non misura: con 1,1 epoche e la GPU quasi sempre in attesa dei dati, questi numeri descrivono una rete
appena avviata. Non dicono se l'architettura impari. Con un seme e un contesto tenuto fuori nessuna attesa, vera o
falsa, è una prova (protocollo §4), e nulla di questo entra in PROGETTO §0.

## Che cosa ne segue

- Il secondo training ([cellnet_esteso_2026-10-01](../cellnet_esteso_2026-10-01/PROTOCOLLO.md)) chiedeva solo la
  ripresa su CUDA, che è passata. Il caricatore però va corretto prima: lo stesso disegno ridarebbe la GPU in attesa e
  lo stesso rischio di memoria con un corpus due volte più grande.
- La profilazione del caricatore gira su un kernel CPU (`rlab-loader-profile-r1`), che non consuma quota GPU:
  [caricatore/](../cellnet_esteso_2026-10-01/caricatore/).
