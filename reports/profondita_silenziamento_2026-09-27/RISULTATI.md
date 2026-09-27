# La risposta a valle cresce con la profondità del silenziamento?

## Perché

Il controllo sul bersaglio dei sei universi
([universo_nuovi](../universo_nuovi_2026-09-27/RISULTATI.md)) mostra che la profondità mediana del silenziamento va
da −1,81 (K562) a −0,62 (HEK293T) in log naturale. Il t22 media le sorgenti a pesi uguali, quindi mescola
silenziamenti profondi e poco profondi. Prima di proporre una normalizzazione per profondità, si misura se la
risposta a valle ne dipende davvero. È un'esplorazione, senza regola di decisione.

## Il calcolo (`depth_energy.py`, uscite in `r1/`)

**Grandezze, per ogni universo e bersaglio:**
- profondità d = −raw sul gene del bersaglio, con il suo z;
- energia a valle E = media degli shrunk² su G*: 5.665 geni con CPM ≥ 10 in tutti e cinque i contesti, esclusi il
  gene del bersaglio e i geni entro 5 kb dal suo TSS.

**Confronto, per ogni coppia di universi:**
- bersagli con silenziamento chiaro in entrambi (z ≤ −3);
- pendenza e correlazione di log(E_a/E_b) su log(d_a/d_b), con bootstrap sui bersagli.

**Lettura della pendenza:** se la risposta fosse proporzionale alla profondità, l'energia andrebbe col quadrato e la
pendenza sarebbe vicina a 2. Il rumore sulla profondità spinge la pendenza verso 0, quindi è un limite inferiore.

## Esito (misurato)

| Universo | Bersagli | Profondità mediana | Energia mediana |
|---|---|---|---|
| K562 | 7.420 | 1,81 | 0,0033 |
| CD4 a riposo | 9.454 | 1,77 | 0,0026 |
| HCT116 | 9.561 | 1,00 | 0,0021 |
| HEK293T | 11.141 | 0,62 | 0,0014 |
| KOLF2.1J | 8.372 | 0,83 | 0,0072 |

| Coppia | Bersagli | Pendenza (IC 95 %) | Correlazione |
|---|---|---|---|
| K562 – CD4 | 4.398 | 0,11 (0,07…0,16) | 0,08 |
| K562 – HCT116 | 4.099 | 0,20 (0,14…0,25) | 0,11 |
| K562 – HEK293T | 4.504 | 0,18 (0,13…0,24) | 0,10 |
| K562 – KOLF | 2.793 | 0,30 (0,25…0,34) | 0,23 |
| CD4 – HCT116 | 4.328 | 0,09 (0,05…0,14) | 0,06 |
| CD4 – HEK293T | 4.876 | 0,15 (0,11…0,20) | 0,10 |
| CD4 – KOLF | 3.000 | 0,17 (0,12…0,22) | 0,12 |
| HCT116 – HEK293T | 5.325 | 0,22 (0,17…0,26) | 0,13 |
| HCT116 – KOLF | 2.651 | 0,46 (0,41…0,52) | 0,31 |
| HEK293T – KOLF | 2.965 | 0,48 (0,43…0,54) | 0,31 |

**Misurato:**
- in tutte e dieci le coppie, dove un bersaglio è silenziato di più la sua risposta a valle è più grande: pendenza
  positiva con l'intervallo sopra zero, ma debole (da 0,09 a 0,48, correlazioni da 0,06 a 0,31);
- fra sorgenti la relazione non tiene: KOLF2.1J ha l'energia mediana più alta con una profondità intermedia, e il K562,
  silenziato più a fondo, ha meno energia di KOLF.

**Interpretazione, non verificata:**
- la profondità è una covariata reale ma modesta della risposta, bersaglio per bersaglio, e non spiega la scala
  complessiva di una sorgente. Su quella pesano altro: il tipo cellulare, il rumore, la profondità di sequenziamento
  e lo stimatore;
- normalizzare ogni sorgente per la sua profondità mediana non ha sostegno qui;
- conviene invece dare alla rete la profondità per (bersaglio, sorgente) come ingresso. Per un contesto nuovo andrebbe
  prevista, ad esempio dall'espressione del bersaglio nei controlli, come fa il cancello s del modello a cancelli.

**Cautele:**
- l'energia degli shrunk contiene ancora rumore, che varia fra sorgenti (cellule per bersaglio, profondità);
- i bersagli sono selezionati su un silenziamento chiaro in entrambe le linee;
- il K562 passa per un altro stimatore.
