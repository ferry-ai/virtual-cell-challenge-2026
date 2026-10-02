# Training r1: la misura di discriminazione, registrata prima del risultato

2 ottobre 2026, 22:30 CEST (20:30 UTC). Il training `alfredo2003bit/rlead-training-r1` versione 2 è in corso dalle
20:42 e nessun suo numero è noto. Questa pagina aggiunge una lettura **descrittiva**. **Non cambia** la regola del
[protocollo](PROTOCOLLO.md): controllo tecnico e Q1–Q4 si leggono come registrato, con `read_training.py`.

## Perché

Il t29 ha preso −0,030 sulla classifica, con PDS grezzo 0,503 (il caso): i 300 bersagli previsti erano
indistinguibili. Lo dicono il CP-0055 di Davide e la [diagnosi](../../analisi/t29_diagnosi_2026-10-02/README.md). Le
misure del protocollo non vedono questo difetto: il coseno sui 200 geni più mossi confronta ogni gruppo solo con sé
stesso.

## La misura

`train_cellnet.discrimination`, in `cellnet_rlead_2026-10-01`; prove in `test_rlead_fixes.DiscriminationMeasure` e
`test_kaggle_launcher`.
- **Coseno:** per due gruppi g e h dello stesso key, s_gh è il coseno fra lo spostamento previsto per g e quello
  osservato per h, su tutti i geni dove entrambi sono definiti.
- **Rango di g:** la quota degli altri gruppi h con s_gh > s_gg (i pari contano metà).
- **Punteggio:** 1 − rango, mediato sui gruppi. 1 vuol dire che il proprio gruppo è sempre il più vicino; 0,5 è il
  caso.
- **Key esclusi:** quelli con meno di 5 gruppi.

È nello spirito del PDS ufficiale, ma non è il PDS: niente pseudobulk dei conteggi generati, niente pannello
ufficiale. **Non è un punteggio VCC.**

Per classe (C, T, J) si riportano:
- il braccio sui suoi gruppi;
- il braccio e il **trasferimento** sugli stessi gruppi, quelli che hanno un trasferimento.

## Come si calcola

Il kernel in corso usa il codice caricato prima di questa misura e non la scrive. Si calcola con un secondo kernel:

```
kaggle_train.py kernel ... --slug rlead-eval-r1 --prepass-from rlead-prepass-r1 --eval-from rlead-training-r1 \
    --arm ident=identity --arm gen=generic --train-args="<gli stessi del training>"
```

Il kernel riparte dall'ultimo checkpoint del training **senza nessun passo di addestramento** (`--eval-only`).
- **Che cosa scrive:** rifà la valutazione e scrive `eval.json` ed `eval_discrimination.json` per braccio.
- **Prova sui dati sintetici:** l'`eval.json` così ottenuto è identico a quello del training.
- **Il costo:** è un nuovo job e consuma quota (circa la durata della valutazione, più il caricamento). Serve l'ok
  in chat prima del lancio.

## Che cosa ci si aspetta, scritto prima

| Voce | Attesa | Perché |
|---|---|---|
| `gen`, ogni classe | vicino a 0,5 | il braccio generico dà lo stesso profilo a ogni bersaglio dello stesso key: è il controllo della misura |
| trasferimento, classe C | sopra 0,6 | sui contesti A, B, C il trasferimento dà un PDS grezzo di 0,79 (t22); qui contesti e geni sono altri |
| `ident`, classe C | **non so**: fra 0,5 e il trasferimento | r2 `ident`: guadagno specifico positivo solo nel 5,5% dei gruppi C. Le correzioni del passo A e 10 epoche possono cambiarlo |

**Come si legge `ident` sulla classe C:**
- **≤ 0,55:** come il t29, la rete non distingue i bersagli. Nessun export verso un invio.
- **0,55–0,65:** distingue poco.
- **> 0,65, ma sotto il trasferimento:** distingue, ma meno della ricetta. Ha senso provarla come correzione del
  trasferimento, non al suo posto.
- **≥ trasferimento, sugli stessi gruppi:** è il segnale che il t29 non aveva. Serve comunque il banco locale a sei
  membri prima di un invio (CP-0055, ramo c).

**Se `gen` non sta vicino a 0,5** (fuori da 0,45–0,55), la misura ha un difetto e non si legge.
