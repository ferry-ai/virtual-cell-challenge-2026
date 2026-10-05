# Esito dell'addendum A549: la regola non passa, A549 resta fuori

5 ottobre 2026, 18:24–18:30 CEST. Claude Code per Alfredo.

Riferimenti:
- addendum [ADDENDUM_A549.md](ADDENDUM_A549.md), commit `1d9872e`;
- codice [tabella_a549.py](tabella_a549.py) e [confronto_a549.py](confronto_a549.py), committati prima delle corse;
- valori in [esito/a549_r1.json](esito/a549_r1.json) e [esito/a549_tabella_r1.json](esito/a549_tabella_r1.json).

## La tabella

| Grandezza | Valore |
|---|---|
| Chiavi del cubo misurate | 641 |
| Cellule di controllo | 45.320 |
| Cellule per bersaglio (mediana) | 540 |
| Geni utilizzabili | 11.301 |
| Durata della lettura dei 31 frammenti | 517 s |

## Il confronto

| Linea | Bersagli coperti da A549 | `all_a549 − all`, coseno [IC 90%] | Indice PDS | A549 da solo, coseno sui coperti |
|---|---|---|---|---|
| H1 | 14 / 96 | −0,0009 [−0,0025; +0,0008] | +0,0015 | 0,010 |
| HepG2 | 93 / 400 | **+0,0059** [+0,0028; +0,0088] | +0,0027 | 0,146 |
| RPE1 | 93 / 400 | +0,0027 [−0,0005; +0,0059] | −0,0016 | 0,064 |
| Jurkat | 96 / 400 | −0,0005 [−0,0018; +0,0008] | −0,0007 | 0,097 |
| K562 | 74 / 400 | +0,0004 [−0,0009; +0,0019] | −0,0012 | 0,098 |

**La regola:**
- media delle differenze di coseno: +0,0015, ne serviva almeno +0,005;
- linee con il limite inferiore sopra 0: 1, ne servivano 3;
- PDS: condizione rispettata.

**Non passa: A549 non entra nel candidato.**

**Previsione registrata** («da +0,000 a +0,012, media +0,005; fiducia 0,4»): dentro la banda, sotto la media prevista.

**Lettura.**
- A549 copre solo circa un quarto dei bersagli valutati, perché lo schermo non è genome-wide sulle chiavi del cubo.
- Da sola trasferisce come i gruppi più deboli: fra 0,01 e 0,15, contro 0,05–0,20 del §3.2 dell'[ESITO](ESITO.md).
- Una linea in più aiuta quando misura gli stessi bersagli; una linea che ne copre un quarto, con un'altra modalità,
  sposta poco.
