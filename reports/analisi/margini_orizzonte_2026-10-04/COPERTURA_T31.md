# Il t31 era il solo K562 travestito da media di più linee

4 ottobre 2026, verso le 2, ora del PC. Conteggio in [copertura_t31.py](copertura_t31.py), uscita in
[copertura_t31.json](copertura_t31.json). Solo conteggi: nessun nome di bersaglio, perché `pert_counts.csv` è privato.

## Misurato

Sulle 25 chiavi usate dall'esportazione del t31 e sui 300 bersagli del pannello ufficiale:

| Gruppo | Bersagli del pannello coperti | Coperti solo da questo gruppo |
|---|---|---|
| K562 (gwps; essential 0) | 272 | **260** |
| Tian (neuroni e iPSC) | 7 + 1 | 0 |
| HipSci (19 chiavi) | 5 | 0 |
| RPE1 | **0** | 0 |

- **Copertura:** 272 bersagli coperti, 28 a zero. Per **260 su 272** l'unica sorgente è K562 gwps.
- **Geni:** K562 gwps misura 7.681 geni dei 18.533 dell'asse. Da qui la quota osservata di 0,388 nell'esportazione: per
  il 61% delle coppie bersaglio–gene l'effetto previsto è zero.
- **Contesti:** gli effetti di A, B e C hanno lo stesso sha256 (`export_abc.json`). La media a pesi uguali non dipende
  dal contesto, e lo stesso vale per l'ampiezza del norm-match.

## Che cosa cambia

- **Il t31 non ha misurato la «media di più linee».** Sul pannello ufficiale è il trasferimento del solo K562
  ×2, con il generatore del t22. Il punteggio (+0,079) sta fra il K562 solo del t10 (+0,050, ampiezza naturale,
  generatore del trial-01) e le tre sorgenti genomiche ×2 del t15 (+0,108). È coerente con questa lettura.
- **Perché il banco HepG2 non lo poteva vedere.** Il pannello del banco richiede bersagli coperti da ogni braccio, cioè
  geni essenziali misurati da molte linee; i bersagli ufficiali non lo sono (RPE1 ed essential ne coprono 0). È lo
  stesso limite di regime già scritto in CP-0027: banco su geni essenziali, gara no.
- **Lezione per la taratura banco–gara:** prima di trasferire un risultato del banco, contare le sorgenti per bersaglio
  **sul pannello ufficiale**.
- **Per D, E, F (interpretazione):** se i 300 bersagli restano questi, i dati di effetto che li coprono vengono quasi
  solo da schermi genome-wide: K562 gwps e, nella ricetta, CD4, HCT116 e HEK293T. Le linee rlab non aggiungono
  copertura.
