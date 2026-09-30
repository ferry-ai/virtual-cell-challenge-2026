# Lancio del training su GPU (primo training su dati reali)

Scritto prima del lancio del kernel GPU, dopo il [protocollo](PROTOCOLLO.md) e prima di vedere qualunque numero di
questo training. Sessione `07ebf08b`.

## Kernel e dati

- **Kernel:** `davidmaisterx/rlab-cellnet-r1`, GPU T4×2, senza internet.
- **Pre-passo:** l'output del kernel CPU indicato in `lancio_training.json` (r3, quattro processi; stessi dati e
  argomenti di r2, e lo stato non dipende dal numero di processi). Argomenti: `--holdout-context HepG2
  --same-experiment h1_vcc2025=h1_vcc2025_train,h1_vcc2025_val`, il resto di default (QC, identità, 10% di bersagli
  nascosti con seme 20260930, pool di 2.048 controlli per chiave, 2.048 geni d'ingresso, almeno 30 controlli per chiave).
- **Dati:** `rlab-hepg2-nadig` (tenuto fuori), `rlab-jurkat-nadig`, `rlab-h1-vcc2025-trainval`, `rlab-hipsci-gwfit`,
  `rlab-hipsci-gwnonfit`, `rlab-hipsci-targeted19`.
- **Scostamenti dal protocollo, decisi prima di ogni numero di questo training:** K562 genome-wide fuori (incidente
  E-20260930-003: gli shard del 30/09 hanno codici al posto dei bersagli e nessun controllo; è in rilettura con il job
  115 ed entra nel training successivo); H1 train e validation letti come un solo esperimento (stessi 38.176 controlli
  per conteggio nei manifest del job 108).

## Bracci e budget

Due bracci in parallelo, uno per GPU, stessi argomenti salvo il codice del bersaglio:

| Braccio | Dispositivo | Argomenti |
|---|---|---|
| `desc` | cuda:0 | `--target-code descriptors` |
| `ident` | cuda:1 | `--target-code identity` |

Comuni: `--epochs 10 --batch 256 --dim 128 --rank 128 --lr 1e-3 --ctrl-k 64 --buffer-shards 4 --workers 2
--budget-minutes 100 --checkpoint-minutes 15 --reserve-export-minutes 5 --eval-reserve-seconds 120`, seme 0.
Il training si ferma alla prima fra dieci epoche e la scadenza del budget meno le riserve (valutazione stimata sul
posto, esportazione 5 minuti).

Prima dei bracci, su cuda:0 con gli argomenti di `desc`: il **ciclo di ripresa su GPU** (arresto al passo 50, ripresa
fino al 100, corsa diretta al 100; `resume_check.json`, regola: sequenza dei dati identica, parametri entro 1e-3 del
massimo).

**Quota:** 6 ore di GPU disponibili la notte del 30/09 (proprietario). Questo kernel ne usa circa 1 ora e 55 minuti
(ciclo circa 8 minuti, bracci 100 minuti in parallelo, avvio e chiusura); il resto resta per il training successivo con
K562 genome-wide, K562 essenziali e RPE1.
