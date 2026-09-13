# CP-0006 — Prima sottomissione: il server accetta, e il punteggio è 0,046

- **Data:** 2026-09-13
- **Tipo:** esperimento
- **Redatto da:** agente (Claude Opus 5)
- **Revisione umana:** no — ma **l'invio è stato autorizzato esplicitamente** dal
  proprietario del progetto, dopo che gli erano state esposte le conseguenze
  (pubblicazione su classifica pubblica, consumo di quota, punteggio atteso basso)
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Due domande che nessuna misura locale poteva chiudere.

1. Il servizio di scoring **accetta** un archivio prodotto dal nostro packager in
   streaming? Fino a ieri era dimostrato solo che lo accetta il validatore ufficiale
   del *contenitore*, che controlla il tar e nient'altro.
2. Quanto vale, **sulla scala della gara**, il modello di trasferimento calibrato?
   Tutte le misure del progetto erano proxy in spazio pseudobulk su K562 e RPE1, con
   l'avvertenza ripetuta che non si convertono in un punteggio VCC.

## 2. Cosa è stato fatto

Una sola sottomissione di leaderboard, del solo `trial-01-transfer`.
`trial-00-controls` **non** è stato inviato (D-017).

```powershell
.\scripts\vcc.cmd submit C:\Users\ferra\vcc2026-data\artifacts\k01pack\prediction.vcc `
    -m "trial-01-transfer k01pack a=0.197 sd=4" -d "<descrizione del metodo>" `
    --json --wait --poll-interval 30
.\scripts\vcc.cmd status PNn227rxP3bVByS37W41 --json
```

Prima dell'invio: verificati sha256 dell'archivio (`681b0aac…a1a2a6`, identico a quello
registrato da CP-0005) e stato dell'account (`can_submit: true`, `blockers: []`).

Evidenza grezza, salvata verbatim:
[`reports/trial_2026-09-13/submit_PNn227rxP3bVByS37W41.json`](../../reports/trial_2026-09-13/submit_PNn227rxP3bVByS37W41.json),
[`status_PNn227rxP3bVByS37W41.json`](../../reports/trial_2026-09-13/status_PNn227rxP3bVByS37W41.json).
Lettura ordinata in
[`submission_PNn227rxP3bVByS37W41.md`](../../reports/trial_2026-09-13/submission_PNn227rxP3bVByS37W41.md).

## 3. Cosa si è osservato

### 3.1 Il server ha accettato e valutato

| Campo | Valore |
|---|---|
| entry id | `PNn227rxP3bVByS37W41` |
| stato | `published`, `is_terminal: true`, `error_info: null` |
| byte caricati | 4.203.520.000 — identici al file locale |
| md5 verificato dal server | sì |
| partizione / pannello | `val` / `vcc2026-val-1` |
| ancore | `vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4` |
| inviata / letta | 2026-09-13T01:12:02Z / 2026-09-13T01:44:48Z |

**Questo chiude la riserva che CP-0005 dichiarava esplicitamente.** Il `.vcc` prodotto
dal packager in streaming — quello che copia gli array CSR dataset a dataset invece di
ricostruire la matrice — è stato letto e valutato dal servizio di scoring senza errori.
La trasformazione dell'indice di `obs`, l'unica applicata, non ha impedito nulla.

### 3.2 Il punteggio: 0,046, posizione 446 su 920

Scala ufficiale: **0 = media del contesto**, **1 = un replicato reale**. Il complessivo
è la media non pesata delle sei metriche sui tre contesti — verificato: la media dei sei
valori è 0,045929396372906744, identica al campo `score_avg`.

| Metrica | Grezza | Scalata |
|---|---:|---:|
| `pds` discriminazione | 0,687016 | **0,413315** |
| `mse` accuratezza di espressione | 1,231260 | **0,000000** |
| `nmae` errore sui log-FC | 0,984886 | 0,026833 |
| `fid` fedeltà di direzione | 0,457982 | **−0,182476** |
| `reach` profondità di direzione | 0,097961 | 0,021322 |
| `jac` sovrapposizione DE | 0,029141 | −0,003417 |

Posizione **446 su 920 squadre**, letta dalla pagina *Leaderboard* alle
2026-09-13T01:45Z. La prima squadra aveva 0,2629 in quel momento.

### 3.3 Una sola metrica batte la media del contesto, e una è sotto

**`pds` = 0,413.** Il grezzo 0,687 va letto contro 0,5, che è il caso: la previsione è
più vicina al proprio effetto vero che a quello delle altre 299 perturbazioni. Il
modello porta segnale **specifico della perturbazione**.

**`mse` = 0 esatto**, cioè al pavimento del suo clamp (è l'unica delle sei limitata a
0–1). L'accuratezza di espressione non batte la media del contesto.

**`fid` = −0,182**, sotto la media del contesto: fra i geni che la previsione chiama
significativi, la proporzione che si muove nella direzione giusta è **peggiore** di
quella che si otterrebbe non prevedendo alcun effetto. `nmae`, `reach` e `jac` sono
praticamente a zero, cioè indistinguibili dalla media del contesto.

### 3.4 Nessuna contraddizione con le misure locali

CP-0003 e CP-0004 misuravano una riduzione dell'**1,01%** di MSE pseudobulk rispetto al
nullo, su K562 → RPE1, ripetendo a ogni occasione che non era convertibile in un
punteggio VCC. Il punteggio VCC è 0,046. Le due affermazioni convivono senza attrito, e
la cautela con cui la prima è sempre stata riportata si è rivelata giusta: un guadagno
dell'1% in un esperimento esterno non diventa un punteggio alto sui contesti della gara.

Il proxy non ha **ingannato** — non prometteva molto e non ha consegnato molto — ma non
ha nemmeno **predetto**: non c'era modo, da quel numero, di anticipare che `pds`
sarebbe stato 0,41 e `fid` negativa.

### 3.5 Le ancore potrebbero essere ricavabili dalla classifica pubblica

La pagina *Leaderboard* mostra, per ogni squadra e per ogni metrica, **il valore grezzo
e quello scalato**. Con `punteggio = (u − b) / (r − b)`, due righe con grezzi diversi
danno due equazioni in `b` e `r`.

**Derivazione preliminare, da verificare su più righe.** Da `mse` grezzo 0,926 →
scalato 0,072 e 0,661 → 0,344 (righe 1 e 2 della classifica al 2026-09-13T01:45Z) si
ottiene `b ≈ 0,996` e `r ≈ 0,022`. Applicata al nostro grezzo 1,231 dà −0,241, che
clampato è 0 — il valore osservato.

**Non è una misura**, è un'aritmetica su due righe lette da una pagina web, con
l'ipotesi non verificata che la formula sia esattamente quella e che i valori mostrati
siano già mediati sui tre contesti nello stesso modo. Va rifatta su molte righe, e per
tutte e sei le metriche, prima di essere usata.

## 4. Interpretazione e incertezza

**Misura.** Il punteggio, le sei componenti, il rango e l'accettazione del server.
Tutto verbatim nei due JSON.

**Interpretazione.** Il quadro è coerente con α = 0,197: la risposta è compressa a un
quinto, quindi il profilo predetto resta vicino al basale. È esattamente il regime in
cui ci si aspetta una `pds` positiva — l'ordinamento fra perturbazioni sopravvive alla
compressione, perché la compressione è un fattore comune — e metriche di ampiezza al
pavimento. La compressione che D-006 e D-012 prescrivono protegge dal fare peggio del
nullo, e per costruzione impedisce di fare molto meglio.

**Ipotesi, non misura.** Che `fid` negativa sia un difetto correggibile del generatore
e non assenza di segnale direzionale. Il candidato è l'artefatto misurato in CP-0004
§3.8: le cellule generate rilevano il 4–6% di geni in più dei controlli reali **anche a
effetto previsto zero**, il che gonfia il numero di geni chiamati significativi e quindi
il denominatore della fedeltà. Verificabile: rigenerare con `--overdispersion` e
rimisurare. **Non fatto.**

**Ipotesi, non misura.** Che alzare α migliori il punteggio. `pds` è invariante di
scala, quindi non ne beneficerebbe; `mse` è già al pavimento e a piena ampiezza
peggiorerebbe (misurato: 1,162 volte il nullo in pseudobulk). Non c'è ragione di
aspettarsi un guadagno, e c'è una ragione misurata di aspettarsi un peggioramento.

**Quello che questa sottomissione non dice.** Niente sul set finale D/E/F: contesti
diversi, pannello diverso, e `pds` è un rango dentro il proprio pannello. La pagina
*Evaluation* lo dice esplicitamente, e il rango 446 su 920 è una fotografia di questo
momento su questa partizione.

## 5. Spiegazione semplice

Abbiamo consegnato per la prima volta, e il pacco è stato accettato e valutato. Due
risultati distinti, ed è importante non confonderli.

Il primo è tecnico e completamente riuscito: il modo in cui impacchettiamo — senza mai
caricare in memoria una matrice da diciassette gigabyte — produce un file che il
servizio ufficiale legge e valuta senza storcere il naso. Quella strada è aperta.

Il secondo è il voto, ed è basso: 0,046 su una scala dove 0 significa «hai predetto la
stessa cosa media per tutte le perturbazioni» e 1 significa «bravo quanto rifare
l'esperimento in laboratorio». Siamo appena sopra lo zero, 446esimi su 920.

Un dettaglio però è interessante. Delle sei misure, una sola va bene davvero: quella che
chiede «riesci a distinguere una perturbazione dall'altra?». Lì siamo al 41% della
strada. Le altre, che chiedono «di quanto cambia questo gene, e in che direzione»,
stanno a zero o sotto. Tradotto: il modello sa *quale* perturbazione sta guardando, ma
non sa dire *quanto* e *in che verso* muove i singoli geni.

Non è una sorpresa. Avevamo misurato che copiare la risposta da un altro tipo di cellula
funziona così poco che conviene ridurla a un quinto, e una risposta ridotta a un quinto
assomiglia molto al non fare niente. Il voto dice esattamente questo.

## 6. Conseguenze

- `docs/PROGETTO.md`: lo stato passa da «nessuna sottomissione e nessun punteggio» a
  «una sottomissione valutata, 0,046». **È il primo numero del progetto sulla scala
  della gara.** L'incertezza 1 («quanto vale un punto») passa da aperta a
  *potenzialmente risolvibile*, con il metodo di §3.5 da verificare.
- `docs/REGISTRO.md`: chiusa la riserva di [R-012](../REGISTRO.md#r-012--reportstrial_2026-09-13)
  sull'accettazione del server; nuove voci per l'evidenza della sottomissione.
- `docs/SOTTOMISSIONE.md`: la sezione 4 non è più una procedura ipotetica, è compilata.
- **D-006 e D-012 non cambiano.** La compressione resta la scelta giusta per non fare
  peggio del nullo, e il punteggio non dà motivo di riaprirla; dà motivo di cercare
  segnale altrove, che è R-1 e R-3 della roadmap.
- Resta una sottomissione di quota per oggi. Non è stata usata.

## 7. Cosa corregge

Non corregge nessun checkpoint. **Chiude** una riserva che CP-0005 §4 dichiarava come
aperta e non aggirabile localmente: «l'accettazione da parte del server — nessuna
sottomissione è stata inviata; il servizio di scoring applica i propri controlli, e solo
una sottomissione valutata dimostra che accetta questo artefatto». Ora ne esiste una.

Conferma, senza modificarle: tutte le misure locali di CP-0003, CP-0004 e CP-0005,
compresa la riduzione dell'1,01% di MSE pseudobulk, che resta vera di ciò che misurava e
che **non** era un punteggio VCC.

Corregge una cosa in questo repository, non in un checkpoint: ogni documento che
dichiarava «nessuna sottomissione è stata inviata e non esiste alcun punteggio di
leaderboard» è ora falso e va aggiornato. La frase era vera fino alle 01:12Z del
13 settembre 2026.

## 8. Domanda di comprensione

Il punteggio complessivo è 0,046, ma `pds` da solo vale 0,413. Un collega propone di
alzare α per «sfruttare» la discriminazione che evidentemente c'è. Quali due numeri di
questo checkpoint gli mostri per spiegargli che non funzionerebbe, e quale proprietà di
`pds` rende la sua proposta irrilevante proprio per la metrica che lo ha convinto?
