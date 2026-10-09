# Aggiunta al contratto v3: due diagnosi in più sul riempimento

9 ottobre 2026, VALIDAZIONE (Claude Code `eace4d03`). Scritta **dopo** aver letto i numeri della corsa r1 sul fold
C-K562 ([esito](esm2/supporto_C-K562_r1.json), commit `1d9b4523` delle 20:55) e **prima di qualunque numero sul
fold C-iPSC**, la cui verità non è sul portatile. Non cambia le parole fissate al §2 del
[contratto v3](PROTOCOLLO_v3.md) né le soglie del §8: aggiunge due letture descrittive. Per C-K562 sono a
posteriori e si riportano come tali; per C-iPSC sono registrate prima.

**Perché.** Su C-K562 l'errore quadratico delle coppie riempite è peggiore di zero per tutti e tre i riempimenti,
ma lo è anche per T0 sul proprio supporto (`mse_ratio` 1,19): l'ampiezza 1,576 è nata sul punteggio ufficiale, non
sull'errore. Un rapporto d'errore sopra 1 non distingue «direzione sbagliata» da «direzione giusta, troppo ampia».
E nella vista del generatore `sign50` sale di 0,02 con ogni riempimento, anche quello a bersagli scambiati: con
circa 35 geni confidenti per bersaglio i «primi 50» sono tutti, e una coppia non prevista conta come segno
sbagliato; avere una previsione qualunque alza la misura.

**Che cosa si aggiunge** (stesso codice, schema 2, [supporto_fallback.py](esm2/supporto_fallback.py)):

1. **Accordo senza ampiezza sulle coppie riempite:** per bersaglio, coseno fra riempimento e verità grezza
   (`cos`) e moltiplicatore che adatterebbe il riempimento alla verità (`amp_star`), per `esm2`, `generico` e
   `scambiato`; contrasti `esm2` − `scambiato` e `esm2` − `generico` con lo stesso bootstrap.
2. **Segno separato dalla copertura,** sui geni confidenti della verità: quota di quei geni che il braccio prevede
   (`coverage_conf`), accordo di segno fra i soli previsti (`sign_predicted`), accordo su tutti con il non previsto
   contato come errore (`sign_all`).

**Lettura, fissata ora per C-iPSC:** «il riempimento ha una direzione giusta» si scrive solo se `cos` di `esm2` è
risolto sopra zero; «specifica del bersaglio» solo se `cos` di `esm2` − `scambiato` è risolto positivo. Un guadagno
di `sign50` o di `sign_all` che compare uguale nel braccio scambiato si chiama copertura, non accuratezza.

## Precedenti

- **S-013**: il ridge senza contesto dava un segnale solo contro la verità iPSC nel regime T, e lo perdeva
  togliendo il lignaggio; per questo le due letture sono registrate prima dei numeri di C-iPSC, il fold dove un
  esito favorevole è più plausibile e dove sarebbe più facile leggerlo a posteriori.
- **S-006**, **S-012**: una riga comune può migliorare misure di segno e d'errore senza informazione sul
  bersaglio; il braccio scambiato e quello generico restano il confronto.

**Segnale precoce e arresto:** come al §5 del contratto v3; in più, su un fold dove meno di 30 bersagli hanno
almeno 5 coppie riempite confidenti le letture di segno sul solo riempimento si riportano come «non giudicabili».
