# CP-0052 — T28 nuovo migliore osservato, sotto la soglia di miglioramento registrata

- **Data:** 2026-09-30
- **Tipo:** osservazione
- **Redatto da:** Codex lead
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Gli effetti t25 moltiplicati per 1,5, insieme alla dispersione per gene alla scala 1,
superano il t25 secondo la regola congelata prima della generazione?

## 2. Cosa è stato fatto

Una richiesta `vcc --json status ZvrYZ4UazadAyuq4AsDB` ha restituito `published`.
Il [JSON originale](../../reports/invii/trial_2026-09-29/status_ZvrYZ4UazadAyuq4AsDB_20260929T2305.json)
è conservato senza modifiche. Il lettore congelato
[read_t28_score.py](../../reports/analisi/lead_scientist_2026-09-29/candidate_generation_remote/recovery_r2/read_t28_score.py)
ha prodotto il [confronto](../../reports/invii/prediction_t28_2026-09-29/comparison.json)
legando entry, ricevuta, registrazione e riferimento t25. Tutti i sei membri grezzi e
scalati sono finiti; la loro media pubblicata coincide esattamente con lo score.
Pannello e versione delle ancore coincidono con t25. Nessuna ricostruzione dagli aggregati.

## 3. Cosa si è osservato

**Misurato nello status e nel confronto citati:** score **0,14484520500645978**, rango
359 al controllo, delta t25 **+0,004607144091624243**; delta sul precedente massimo
t24 **+0,001948344056439566**. Nuovo migliore osservato fra i riferimenti registrati.

| Membro scalato pubblicato | t25 | t28 | Delta |
|---|---:|---:|---:|
| PDS | 0,623562176 | 0,622307079 | −0,001255096 |
| MSE | 0 | 0 | 0 |
| NMAE | 0,117984841 | 0,049201956 | −0,068782885 |
| Fedeltà | −0,058128727 | −0,007408907 | +0,050719820 |
| Reach | 0,144052152 | 0,198712650 | +0,054660498 |
| Jaccard | 0,013957924 | 0,006258452 | −0,007699472 |

La MSE grezza peggiora da 3,017171491 a 5,800207145, pur lasciando invariato lo
scalato a zero. Valori completi, contributi alla media e hash sono nel confronto.

## 4. Interpretazione e incertezza

**Esito della regola:** non conclusivo. Lo score è inferiore alla soglia congelata
0,14523806091483554 richiesta per promuovere il miglioramento; il nuovo massimo
non modifica quella soglia. La ricetta esistente resta il riferimento.

**Interpretazione:** fedeltà e reach compensano NMAE e Jaccard peggiori; PDS varia
poco. La media nasconde il deterioramento della MSE grezza. Le direzioni previste
si verificano, ma il delta ufficiale non conferma la grandezza dell'indice locale
(+0,028918). Quell'indice non era una previsione calibrata; 95/96 target pubblici
erano già stati valutati nello storico. La banda soggettiva contiene lo score,
senza diventare per questo un intervallo validato. L'intervento congiunto non
identifica separatamente ampiezza e dispersione, né dimostra generalizzazione.

## 5. Spiegazione semplice

Il numero finale sale, ma guadagni e perdite fra le sei misure quasi si compensano.
Il vantaggio resta sotto il minimo che avevamo deciso prima di vedere il risultato.

## 6. Conseguenze

Nessuna promozione automatica e nessun altro invio. Chiuso il seguito t28; fermare
il monitoraggio e l'inibizione della sospensione. Il [piano R-COMP](../piani/modello-competitivo.md)
prosegue, quando ripreso, dall'inventario dei dati e da una riserva indipendente;
mantiene controlli sui sei membri e separa gli effetti del generatore.

## 7. Cosa corregge

Nessuna misura precedente viene modificata. Chiude l'attesa ufficiale di t28
registrata in [CP-0047](0047-conferma-generatore-t28.md) e in
[INVIO_T28.md](../../reports/invii/trial_2026-09-29/INVIO_T28.md).
Restano validi i limiti della conferma documentati in [CP-0050](0050-credibilita-score-e-riserva.md).

## 8. Domanda di comprensione

Perché il nuovo massimo osservato non basta a promuovere la ricetta, e quale
peggioramento resta invisibile guardando soltanto la MSE scalata?
