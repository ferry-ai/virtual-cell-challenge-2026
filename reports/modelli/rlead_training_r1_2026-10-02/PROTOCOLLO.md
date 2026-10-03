# Training R-LEAD r1: protocollo registrato prima del lancio

2 ottobre 2026, sera. Claude Code per Alfredo, sessione `42343bb9-c8d1-4b93-a9cc-2008dd008900`. Scritto e committato
**prima** di inviare il kernel; la regola non si sposta dopo i numeri (CP-0030).

## Il run

- **Kernel:** `alfredo2003bit/rlead-training-r1`, privato, senza internet, GPU T4 ×2 (un braccio per GPU).
- **Codice:** il dataset `alfredo2003bit/rlead-cellnet-code`, cioè `cellnet_rlead_2026-10-01` al commit `3062380`, con
  gli SHA256 ricontrollati dal kernel.
- **Stato del prepass:** `--prepass-from rlead-prepass-r1`. È il prepass del 2/10
  ([rlead_prepass_r1](../rlead_prepass_r1_2026-10-02/README.md)), lo stato con SHA256 `8dfa413c…`. Il training ne
  ricontrolla gli shard.
- **Bracci:**
  - `ident=identity`: un embedding per bersaglio;
  - `gen=generic`: la riga senza bersaglio, addestrata, con la stessa lettura del contesto.

  I descrittori non ci sono: il dataset `rlab-cellnet-code` non è condiviso.
- **Argomenti:** quelli del training r2 di Davide (`cellnet_esteso_2026-10-01/esito/training_r2/train/config.json`):
  `--epochs 10 --batch 256 --ctrl-k 64 --buffer-shards 4 --dim 128 --rank 128 --lr 0.001 --seed 0 --workers 3
  --roles 3 --prefetch 8 --budget-minutes 150 --reserve-export-minutes 5 --checkpoint-minutes 15 --keep-checkpoints 3
  --measure-steps 300 --eval-chunk 512 --eval-reserve-seconds 120 --log-every 100 --eval-workers 3 --eval-partial 0.08`.
  In più ci sono i default corretti, `--loss-norm global --mixture logits` con `pi_floor` 0, e il ciclo di ripresa
  `--cycle 100 200`.

## Che cosa misura la valutazione

È la valutazione interna di `train_cellnet.py`, non uno score VCC. Per ogni gruppo (chiave, bersaglio) del contesto
tenuto fuori, HepG2, calcola il coseno fra lo spostamento previsto e quello osservato sui 200 geni con lo spostamento
osservato più grande. Il gene bersaglio è incluso: la versione trans non esiste ancora.

## Regole di lettura

Lo script è `read_training.py` di questa cartella, scritto prima dei numeri. Le differenze sono appaiate per gruppo
`(key, symbol)` sui gruppi valutati da entrambi i termini. L'intervallo è bootstrap al 95%, con 10.000 ricampionamenti
dei gruppi e seme 0.

**Verdetto per ogni confronto:**
- **meglio:** il limite basso dell'intervallo è sopra 0;
- **peggio:** il limite alto è sotto 0;
- **non distinguibile:** in tutti gli altri casi.

**Cancello tecnico.** Se fallisce, nessun confronto viene letto. Deve valere tutto quanto segue:
- il kernel finisce con codice 0;
- `resume_check.json` ha `passed` vero;
- la valutazione è completa per entrambi i bracci;
- nel braccio `ident`, la mediana di `pi_mean` sui gruppi C è sopra 0,05: il cancello non è collassato, come era
  successo in r3.

| # | Confronto | Classe | Previsione registrata |
|---|---|---|---|
| Q1 | `cos_model` di ident − `cos_model` di gen | C | meglio |
| Q2 | `cos_model` di ident − `cos_transfer`, cioè l'effetto osservato dello stesso bersaglio in altri contesti | C | peggio (in r2: 0,266 contro 0,390) |
| Q3 | `cos_model` di ident − `cos_model` di gen | J | non distinguibile (sui J il braccio ident non ha la riga del bersaglio) |
| Q4 | `cos_model` di gen − `cos_generic`, cioè la media degli spostamenti di training della chiave | C | solo riportato |

**Cosa si potrà dire, a seconda dell'esito:**
- **Q1 «meglio»:** l'identità del bersaglio aggiunge qualcosa alla risposta generica sui bersagli già visti.
- **Q1 non «meglio»:** la rete non sa usare l'identità oltre la risposta media, per questo braccio, in questo
  budget.
- **Q2 «peggio»:** la rete resta sotto il trasferimento diretto, come in r2.

Nessun esito dice qualcosa sulle linee D, E e F.
