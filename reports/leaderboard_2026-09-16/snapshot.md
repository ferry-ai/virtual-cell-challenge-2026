# Classifica pubblica — fotografia del 16 settembre 2026

**Fonte:** pagina *Leaderboard* di https://virtualcellchallenge.org, letta dal lead
scientist (agente Claude, Opus 5) nel browser integrato, senza login. Orologio della
macchina subito dopo la lettura: **2026-09-16T11:31:37Z** (13:31 in Italia).
**Tipo:** evidenza grezza trascritta a mano (prime dieci righe e la nostra), più una
stima derivata. Nessuna sottomissione, nessuna azione sull'account.

I valori sono in `rows.csv`, nell'ordine in cui la pagina li mostra: per ogni metrica,
prima il valore **scalato** e poi il **grezzo**, arrotondati a tre decimali. I nomi
delle squadre non sono trascritti, perché alcuni sono nomi di persona e al progetto non
servono: la riga si identifica con rango e nome del modello.

## 1. Che cosa dice la pagina

- La pagina dichiara il rango in base alla **sottomissione più recente** di ogni squadra,
  non alla migliore. Una sottomissione diagnostica peggiore sposta quindi il rango
  visibile. La classifica finale dipende solo dal set di test del 22 ottobre.
- Squadre dichiarate: **996** alla prima lettura, **990** alla seconda, pochi minuti
  dopo. La differenza non è spiegata dalla pagina.
- Prime dieci: punteggio complessivo da **0,2246 a 0,2916**, con **17–53 sottomissioni**
  ciascuna.
- Noi (`Mandolino`, `trial-01-transfer k01pack a=0.197 sd=4`): **rango 493**, 0,0459,
  una sottomissione, valori scalati identici a quelli del 13 settembre
  (`reports/trial_2026-09-13/status_PNn227rxP3bVByS37W41.json`). Le ancore della
  partizione `val` quindi non sono cambiate da allora (`vcc2026-val*-r4`).

| Metrica | noi, scalato | prime dieci, scalato (min – mediana – max) | noi, grezzo | prime dieci, grezzo |
|---|---:|---|---:|---|
| PDS | 0,413 | 0,719 – 0,761 – 0,830 | 0,687 | 0,824 – 0,874 |
| MSE | 0,000 | 0,150 – 0,252 – 0,354 | 1,231 | 0,652 – 0,845 |
| JAC | −0,003 | −0,009 – 0,008 – 0,046 | 0,029 | 0,027 – 0,048 |
| NMAE | 0,027 | 0,120 – 0,165 – 0,281 | 0,985 | 0,833 – 0,927 |
| FID | −0,182 | −0,024 – 0,012 – 0,085 | 0,458 | 0,505 – 0,538 |
| REACH | 0,021 | 0,203 – 0,232 – 0,347 | 0,098 | 0,259 – 0,386 |

## 2. Stima delle ancore (interpretazione, non misura ufficiale)

Modello assunto: `scalato = (grezzo − b) / (r − b)`, con `b` = punto 0 (media del
contesto) e `r` = punto 1 (replicato). Per ogni metrica, minimi quadrati lineari di
`grezzo = b + scalato · (r − b)` sulle dieci righe arrotondate più la nostra riga
esatta (esclusa per MSE, dove il nostro scalato è tagliato a 0). Calcolo una tantum del
lead in un file temporaneo; va rifatto con uno script numerato e con più righe.

| Metrica | b (punto 0) | r (punto 1) | residuo massimo sul grezzo | righe | punti complessivi per unità di grezzo |
|---|---:|---:|---:|---:|---:|
| PDS | 0,5019 | 0,9503 | 0,0007 | 11 | 0,37 |
| MSE (più basso è meglio) | 0,9864 | 0,0415 | 0,0008 | 10 | 0,18 |
| JAC | 0,0304 | 0,4111 | 0,0006 | 11 | 0,44 |
| NMAE (più basso è meglio) | 0,9988 | 0,4059 | 0,0020 | 11 | 0,28 |
| FID | 0,5124 | 0,8111 | 0,0006 | 11 | 0,56 |
| REACH | 0,0792 | 0,9644 | 0,0010 | 11 | 0,19 |

L'ultima colonna è `1 / (6 · |r − b|)`: di quanto sale il punteggio complessivo se il
grezzo di quella metrica migliora di un'unità, fermo il resto.

**Limiti.** I valori mostrati sono già aggregati sui tre contesti, mentre la scala
ufficiale si applica per contesto: un buon adattamento lineare sull'aggregato non prova
che le ancore dei tre contesti coincidano. La configurazione installata dichiara per MSE
una penalità `boxcox` (`reports/scorer_2026-09-12/vcc2026_contract.json`); in questo
intervallo di valori l'adattamento lineare regge, fuori non è stato verificato.
L'arrotondamento a tre decimali pesa soprattutto su JAC e FID, dove l'intervallo
osservato è stretto. La stima preliminare di CP-0006 (b ≈ 0,996, r ≈ 0,022 per MSE, da due righe)
è compatibile per ordine di grandezza ma non coincide.

## 3. Dove stanno i punti (interpretazione)

Divario fra la nostra riga e la **mediana** delle prime dieci, per metrica, diviso per
sei (cioè in punti del punteggio complessivo):

| PDS | MSE | REACH | FID | NMAE | JAC | totale |
|---:|---:|---:|---:|---:|---:|---:|
| 0,058 | 0,042 | 0,035 | 0,032 | 0,023 | 0,002 | 0,192 |

0,046 + 0,192 = 0,238, contro una mediana delle prime dieci di 0,240: la scomposizione
torna. Nessuna squadra fra le prime dieci si stacca da zero su JAC, e su FID la migliore
arriva a 0,085: i loro punti vengono da PDS, MSE, REACH e NMAE. Noi siamo **sotto zero**
su FID, cioè sotto la media del contesto.
