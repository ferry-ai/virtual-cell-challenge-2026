# Esito del secondo training su GPU (`rlab-cellnet-r2`), letto con la regola del protocollo

1 ottobre 2026, 12:55 CEST, Claude Code (sessione `07ebf08b`). Regola: [PROTOCOLLO.md](PROTOCOLLO.md) §4, fissata
alle 02:40, con gli [scostamenti](SCOSTAMENTI.md) delle 03:33 e delle 04:22, tutti precedenti al lancio. Output
scaricati in [esito/training_r2/](esito/training_r2/manifest.json): solo JSON e log, con sha256; checkpoint e modelli
restano nell'output del kernel. Riepilogo calcolato con `read_outcome.py` in
[esito/training_r2/outcome.json](esito/training_r2/outcome.json). **È una verifica tecnica, non un risultato.**

Il kernel è partito alle 05:57 CEST ed è finito alle 08:22:56, dopo 8.687,9 s. Pre-passo r5: 5.157.575 cellule,
3.354.670 di training ammesse, HepG2 tenuto fuori.

## A. Esito tecnico, voce per voce (misurato)

| Voce | Esito | Dato |
|---|---|---|
| 1. Codice 0 | passa | `return_code` 0 |
| 2. Ciclo di ripresa su CUDA, due bracci | passa | passi 50 e 100: sequenza dei dati identica, differenza massima dei parametri 0,0 su 75,0, per `desc` e `ident` |
| 3. `verify.json` | passa | 340 shard, nessuno diverso (451 s, in parallelo al training) |
| 4. `coverage.json` | passa | 3,828 epoche, 50.172 passi; 3.354.670 cellule ammesse viste su 3.354.670; nessuna cellula di classe diversa da train estratta |
| 5. `eval.json` | passa, per entrambi i bracci | completa: 199.349 cellule in 383,6 s con 3 processi di caricamento; riserva stimata 581 s; corsa intera 8.524 s su un budget di 9.000 |
| 6. Piano e log | riportati | dal passo 1.600 (a regime): 1.626 cellule/s per braccio, attesa dei dati 0,56. Sull'intera corsa: 1.583 cellule/s e 0,58. Memoria: picco del processo 6,1 GB, almeno 17,8 GB liberi; GPU 1,8 GB per braccio |

A passa per intero. Rispetto al primo training ogni braccio riceve circa 2,5 volte le cellule al secondo: 1.583
contro circa 630. Nessun processo è stato ucciso, e la valutazione legge 244 shard in 6 minuti e mezzo. L'attesa
scritta prima della corsa era di circa 3.000 cellule/s per braccio e **non è raggiunta**: la GPU aspetta ancora i dati
per il 58% del tempo. Resta un limite aperto del caricatore: 4 CPU che decomprimono gzip.

## B. Lettura descrittiva (entrambi i bracci, stessi lotti)

Le misure di `eval.json`: log-verosimiglianza per gene; coseni sui 200 geni con lo spostamento osservato più grande.

| Braccio | Classe | Gruppi | Guadagno rispetto a nessun effetto | Guadagno rispetto a nessun bersaglio | Quota con guadagno specifico > 0 | Coseno della rete | Coseno del trasferimento | Coseno della perturbazione generica |
|---|---|---|---|---|---|---|---|---|
| `desc` | C | 400 | +0,0248 | +0,0037 | 0,523 | 0,266 | 0,390 | −0,019 |
| `desc` | T | 400 | +0,0044 | +0,0016 | 0,933 | −0,062 | — | 0,033 |
| `desc` | J | 226 | +0,0207 | +0,0023 | 0,522 | 0,108 | — | −0,101 |
| `ident` | C | 400 | +0,0012 | −0,0079 | 0,055 | 0,051 | 0,390 | −0,019 |
| `ident` | T | 400 | +0,0002 | −0,0015 | 0,020 | 0,011 | — | 0,033 |
| `ident` | J | 226 | +0,0004 | −0,0080 | 0,009 | 0,032 | — | −0,101 |

Le attese scritte prima del lancio:
- (i) Guadagno rispetto a nessun effetto positivo in media su C e T in entrambi i bracci. Vero: `desc` +0,0248 e
  +0,0044, `ident` +0,0012 e +0,0002 (quasi nulli).
- (ii) Su J il braccio `identity` non ha informazione sul bersaglio nuovo: quota 0,009, sotto 0,5 come atteso. Il
  braccio `descriptors` sta sopra `identity` su J (quota 0,522 contro 0,009, guadagno specifico +0,0023 contro
  −0,0080): è ciò che prevede l'ipotesi dei descrittori.
- (iii) Nessuna attesa che la rete batta il trasferimento su C: non lo batte (coseno 0,266 contro 0,390).

Interpretazione, non misura. Il braccio `identity` impara poco anche su C e T, dove il bersaglio ha un suo vettore
libero: in 3,8 epoche un vettore per simbolo riceve pochi aggiornamenti, mentre i descrittori sono condivisi fra
simboli. Su T il braccio `desc` ha una quota di guadagno specifico positivo di 0,93, ma un coseno negativo (−0,06):
la verosimiglianza sui conteggi e la direzione dello spostamento medio sui 200 geni più mossi non dicono la stessa
cosa, e qui non si sa quale delle due regga su altri contesti. Con un seme e un contesto tenuto fuori nessuna di queste
attese, vera o falsa, è una prova (protocollo §4): i numeri non entrano in PROGETTO §0.

## Che cosa ne segue

- Il terzo training ([cellnet_completo_2026-10-01](../cellnet_completo_2026-10-01/PROTOCOLLO.md)) parte con lo stesso
  codice alle 12:49, sul pre-passo r7 (4.382.321 cellule di training).
- Il caricatore resta il collo di bottiglia: la prossima leva sono shard senza gzip o una lettura con più core. Non
  serve un ritocco della rete per arrivarci.
