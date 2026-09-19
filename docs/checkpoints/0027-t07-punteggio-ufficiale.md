# CP-0027 — Il t07 in classifica: −0,016; la previsione del banco non regge per una famiglia di modelli diversa

- **Data:** 2026-09-19
- **Tipo:** esperimento
- **Redatto da:** agente
- **Revisione umana:** no. L'invio è avvenuto su autorizzazione notturna del proprietario, citata sotto.
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Un modello appreso fra contesti migliora il punteggio ufficiale rispetto alla ricetta fissa del
t03? E lo stadio 84, che aveva previsto il t03 all'1-3% sui membri principali
([CP-0022](0022-previsione-verificata-t03.md)), regge su una famiglia di modelli diversa?

## 2. Cosa è stato fatto

- **Autorizzazione.** Il proprietario ha scritto intorno all'01:40 del 19: «Hai l'ok automatico
  a trainare e inviare in consegna qualsiasi modello tu voglia in qualsiasi modo, non chiedere
  autorizzazioni».
- **Piano scritto prima dei risultati di test**, con criteri di invio:
  `reports/conditioned_2026-09-18/PIANO_INVIO_t06.md`. L'aggiunta delle 02:40 sostituisce il
  t06 (la rete) con il t07 (il modello lineare), perché la rete riaddestrata non riproduceva
  quella giudicata ([CP-0026](0026-predittore-neurale-condizionato.md)).
- **Il t07** è il `ConditionedRidge` dello split C (alpha 1.000), identico a quello dei banchi
  a 1e-7, su A, B e C.
  - Ampiezza 2,0, scelta dallo stadio 93 sulla validazione.
  - Nessun termine cis, stesso generatore del t03.
  - Generato dal job 043: il job 042 era morto durante l'impacchettamento con la perdita del
    runtime.
  - Verificato dallo stadio 48: validatore ufficiale del contenitore superato, contenuto
    identico bit per bit, sha256 `e8854f6f…`.
- **Previsione registrata** alle 01:22 UTC: +0,0101 (`reports/prediction_t07_2026-09-19/prediction.json`).
- **Invio** alle 09:42:58 UTC; risposta alle 10:22 UTC. Output verbatim in
  `reports/trial_2026-09-19/submit_BV1gqrIYuy2KMVZSGmN4.json` e
  `status_BV1gqrIYuy2KMVZSGmN4.json`.
- **Confronto** in `reports/prediction_t07_2026-09-19/comparison.json`.

## 3. Cosa si è osservato

**Misurato — il punteggio.** Media **−0,016004**, rango 671, entry `BV1gqrIYuy2KMVZSGmN4`.
Il t03 aveva +0,019692, trial-01 +0,045929.

**Misurato — previsione contro risultato:**

| membro | grezzo previsto | grezzo ufficiale | errore | scalato previsto | scalato ufficiale | t03, scalato |
|---|---|---|---|---|---|---|
| `pds_cosine` | 0,4874 | 0,5268 | +8,1% | −0,033 | **+0,059** | +0,325 |
| `de_wilcoxon_lfc_nmae` | 0,9435 | 1,0179 | +7,9% (peggio) | +0,095 | **−0,028** | +0,043 |
| fedeltà direzionale | 0,4959 | 0,4770 | −3,8% | −0,055 | **−0,120** | −0,301 |
| `reach` | 0,1722 | 0,0881 | −48,9% | +0,105 | **+0,010** | +0,074 |
| Jaccard | 0,0118 | 0,0243 | +105% | −0,051 | **−0,017** | −0,023 |
| `mse` | 2,255 | 4,530 | +101% | 0 (tosato) | 0 | 0 |
| **media** | | | | **+0,0101** | **−0,0160** | +0,0197 |

**Misurato — le ancore reggono su un quarto punto.** Applicate ai grezzi del t07 riproducono
gli scalati pubblicati con uno scarto massimo di 0,0038 (su `pds_cosine`).

**Misurato — i rapporti fra ufficiale e banco cambiano con la famiglia di modelli.** Per il
t07 rispetto al t03:

| membro | t07 | t03 |
|---|---|---|
| `reach` | 0,177 | 0,346 |
| Jaccard | 0,361 | 0,176 |
| `nmae` | 1,095 | 1,015 |
| `pds_cosine` | 0,931 | 0,861 |
| fedeltà | 0,769 | 0,800 |

**Misurato — la fedeltà direzionale grezza sale a 0,477**, contro lo 0,423 del t03, ma resta
sotto la base ufficiale di 0,5123. `pds_cosine` grezzo scende a 0,527 (t03 0,649), vicino
alla base di 0,502.

## 4. Interpretazione e incertezza

**Interpretazione.**
- **Il modello lineare condizionato peggiora il punteggio ufficiale** rispetto alla ricetta
  del t03 (−0,016 contro +0,020).
- **Lo scambio previsto dal banco si è verificato nel verso**: più fedeltà direzionale, molto
  meno discriminazione fra bersagli. **Non nelle grandezze**: `reach` e `nmae` sono andati
  molto peggio di quanto previsto, e il saldo è negativo.
- **Lo stadio 84, calibrato con un solo punto di un'altra famiglia, non è uno strumento
  affidabile per famiglie nuove.** Errore sulla media −0,026, contro −0,014 sul t03; errori
  per membro fino a ±50-100% sui membri piccoli.

**Incertezza.** Un solo punto: non si separa quanto dell'errore venga dalla famiglia di
modelli e quanto dal regime diverso fra il banco HepG2 (geni essenziali) e i contesti
ufficiali.

## 5. Spiegazione semplice

Avevamo scritto, prima di consegnare, che il nuovo compito avrebbe preso poco più di zero. Ha
preso poco meno di zero. Dove il modello nuovo è diverso dai precedenti, il nostro metodo per
prevedere il voto sbaglia di più, perché era stato tarato su un compito di un altro tipo.

## 6. Conseguenze

- **Il t07 è ora la voce visibile in classifica**, sotto il t03. Il migliore resta trial-01
  (+0,0459).
- **Il modello lineare condizionato non va in un'altra sottomissione** senza un fatto nuovo.
- **Lo stadio 84 va ricalibrato per famiglia di modelli.** Per ogni famiglia nuova serve
  almeno un punto ufficiale, oppure una calibrazione a più punti, prima di usarlo per scegliere.
  Ora esistono quattro punti ufficiali: trial-01, t02, t03, t07.
- **L'autorizzazione notturna del proprietario è stata usata per questo solo invio.** Il
  secondo slot del giorno non è stato usato.

## 7. Cosa corregge

- **Qualifica [CP-0022](0022-previsione-verificata-t03.md) §4**, «da qui in avanti una
  configurazione si può valutare senza spendere una sottomissione». Vale per configurazioni
  della stessa famiglia del punto di calibrazione. Per una famiglia diversa l'errore misurato è
  quasi il doppio, e il segno della previsione si è invertito. CP-0022 aveva segnalato questo
  dubbio come non dimostrato; qui è misurato.
- **Conferma**, con un quarto punto, le ancore di
  [CP-0021](0021-ancore-ufficiali-e-troppe-chiamate.md).

## 8. Domanda di comprensione

Perché un rapporto ufficiale/banco misurato su un solo punto può essere esatto per le
configurazioni vicine a quel punto e sbagliato per un modello di tipo diverso, anche se
generatore e scorer sono gli stessi?
