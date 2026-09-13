Prima sottomissione — trial-01-transfer
=======================================

Inviata il 2026-09-13, valutata e pubblicata. Evidenza grezza, verbatim:
[`submit_PNn227rxP3bVByS37W41.json`](submit_PNn227rxP3bVByS37W41.json) (output di
`vcc submit`) e [`status_PNn227rxP3bVByS37W41.json`](status_PNn227rxP3bVByS37W41.json)
(output di `vcc status`). Questa pagina non aggiunge numeri: li ordina.

## 1. Identificazione

| Campo | Valore |
|---|---|
| entry id | `PNn227rxP3bVByS37W41` |
| model name | `trial-01-transfer k01pack a=0.197 sd=4` |
| squadra | `Mandolino` |
| tipo | leaderboard entry (`is_final: false`) |
| inviata | 2026-09-13T01:12:02.671719Z |
| stato letto | 2026-09-13T01:44:48Z |
| stato | `published`, `is_terminal: true`, `error_info: null` |
| byte caricati | 4.203.520.000 — identici al file locale |
| md5 verificato dal server | sì |
| file sorgente | `artifacts/k01pack/prediction.vcc`, sha256 `681b0aac…a1a2a6` |
| previsione di partenza | `artifacts/q01full/prediction.h5ad`, sha256 `1b7e15f4…c091e2` |
| partizione | `val` |
| pannello | `vcc2026-val-1` |
| insieme di ancore | `vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4` |
| job di scoring | `projects/vcc-prod/locations/us-east1/jobs/vcc-metrics-prod-pnn227rxp3bvbys37w41` |

## 2. Punteggio

**Punteggio complessivo: 0,045929.** Posizione **446 su 920 squadre**, letta dalla
pagina *Leaderboard* alle 2026-09-13T01:45Z. La prima squadra in classifica in quel
momento aveva 0,2629.

La scala è quella ufficiale: **0 = la media del contesto**, cioè predire lo stesso
profilo medio per ogni perturbazione; **1 = un replicato reale**. Il complessivo è la
media non pesata delle sei metriche sui tre contesti — verificato aritmeticamente: la
media dei sei valori qui sotto è 0,045929396372906744, identica al campo `score_avg`.

| Metrica | Grezza | Scalata | Lettura |
|---|---:|---:|---|
| `pds` discriminazione | 0,687016 | **0,413315** | l'unica chiaramente positiva |
| `mse` accuratezza di espressione | 1,231260 | **0,000000** | al pavimento; è l'unica metrica limitata a 0–1 |
| `nmae` errore sui log-FC | 0,984886 | 0,026833 | praticamente alla media del contesto |
| `fid` fedeltà di direzione | 0,457982 | **−0,182476** | **peggio** della media del contesto |
| `reach` profondità di direzione | 0,097961 | 0,021322 | praticamente alla media del contesto |
| `jac` sovrapposizione DE | 0,029141 | −0,003417 | praticamente alla media del contesto |

## 3. Che cosa dicono questi numeri

**Misura.** Il modello batte «predire la media del contesto per ogni perturbazione»
soltanto sulla **discriminazione**: `pds` scalato 0,413, cioè il 41% della distanza fra
la media del contesto e un replicato reale. Il grezzo 0,687 va letto contro 0,5, che è
il caso: la previsione è più vicina al proprio effetto vero che a quello delle altre
perturbazioni, e di parecchio.

**Misura.** Su tutto il resto è alla media del contesto o sotto. `mse` è esattamente 0,
cioè al pavimento del suo clamp: l'accuratezza di espressione non batte la media del
contesto. `fid` è **negativa**: fra i geni che la previsione chiama significativi, la
proporzione che si muove nella direzione giusta è peggiore di quella che si otterrebbe
non prevedendo alcun effetto.

**Interpretazione.** Il quadro è coerente: il trasferimento porta un segnale
*specifico della perturbazione* — abbastanza da distinguere una perturbazione
dall'altra — ma non abbastanza, e non abbastanza ben orientato, da migliorare
l'ampiezza o la direzione dei singoli geni. Con α = 0,197 la risposta è compressa a un
quinto, quindi il profilo predetto resta molto vicino al basale: è esattamente il
regime in cui ci si aspetta `pds` positivo e le metriche di ampiezza al pavimento.

**Nessuna sorpresa rispetto alle misure locali.** CP-0003 e CP-0004 misuravano una
riduzione dell'1,01% di MSE pseudobulk rispetto al nullo, con l'avvertenza ripetuta che
non era convertibile in un punteggio VCC. Il punteggio VCC è 0,046. Le due cose non si
contraddicono, e la cautela era giustificata: un guadagno dell'1% in un esperimento
esterno non diventa un punteggio alto sui contesti della gara.

**Ipotesi, non misura.** Che `fid` negativa indichi un difetto correggibile del
generatore piuttosto che l'assenza di segnale direzionale. L'artefatto misurato in
CP-0004 §3.8 — le cellule generate rilevano il 4–6% di geni in più dei controlli reali
anche a effetto previsto zero — è un candidato plausibile, perché gonfia il numero di
geni chiamati significativi. **Non è stato verificato.**

## 4. Che cosa questa sottomissione ha stabilito, oltre al punteggio

**L'accettazione da parte del server.** Fino a ieri il progetto poteva dire soltanto
«il validatore ufficiale del contenitore accetta l'archivio». Ora il servizio di
scoring ha preso il `.vcc` prodotto dal packager in streaming, lo ha letto, e lo ha
valutato fino a `published` senza errori: `md5_verified: true`, `error_info: null`,
`is_terminal: true`. Il percorso di packaging a memoria limitata di
[CP-0005](../../docs/checkpoints/0005-packaging-streaming-trial01.md) è confermato
end-to-end, e la riserva che quella scheda dichiarava — «nessun server ha accettato
niente» — è chiusa.

**Che la previsione è arrivata intera.** I byte caricati coincidono con il file locale
e l'md5 è stato verificato dal server. La trasformazione dell'indice di `obs`, l'unica
applicata, non ha impedito la valutazione.

## 5. Che cosa resta aperto

- **Le ancore restano ignote a noi**, ma potrebbero non esserlo a lungo: la
  leaderboard pubblica mostra, per ogni squadra, il valore **grezzo e quello scalato**
  di ciascuna metrica. Due righe con grezzi diversi bastano a risolvere `b` e `r` di
  `(u − b) / (r − b)`. **Derivazione preliminare, da verificare su più righe**: da
  `mse` grezzo 0,926 → scalato 0,072 e 0,661 → 0,344 si ottiene `b ≈ 0,996` e
  `r ≈ 0,022`, che riproduce il nostro 1,231 → 0 (clampato). Se regge, chiude
  l'incertezza 1 di `docs/PROGETTO.md` e rende calcolabile un punteggio locale sulla
  scala della gara. **Non è ancora una misura.**
- **Una sola sottomissione della quota giornaliera è stata usata.** Ne resta una fino
  a mezzanotte UTC.
- `trial-00-controls` **non è stato inviato** e non va inviato: D-017.
